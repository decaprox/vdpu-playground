import json
import pytest
import re
import socket
import subprocess
import time


class SocketHelper:
    def _wait_for_port(self, host: str, port: int, timeout: float = 10.0):
        deadline = time.time() + timeout
        last_err = None
        while time.time() < deadline:
            try:
                with socket.create_connection((host, port), timeout=1):
                    return
            except OSError as e:
                last_err = e
                time.sleep(0.1)
        raise TimeoutError(f"{host}:{port} not reachable after {timeout}s ({last_err})")


class Qmp(SocketHelper):
    def __init__(self, host: str, port: int):
        self._wait_for_port(host, port)
        sock = socket.create_connection((host, port))
        self.sock_file = sock.makefile("rwb")
        _ = self.sock_file.readline()
        self._negotiate()

    def _negotiate(self):
        self._send({"execute": "qmp_capabilities"})
        resp = self._recv()
        if "error" in resp:
            raise RuntimeError(f"qmp_capabilities failed: {resp}")

    def _send(self, cmd: dict):
        self.sock_file.write((json.dumps(cmd) + "\n").encode())
        self.sock_file.flush()

    def _recv(self):
        line = self.sock_file.readline()
        return json.loads(line) if line else None

    def command(self, name: str, **args):
        cmd = {"execute": name}
        if args:
            cmd["arguments"] = args
        self._send(cmd)
        return self._recv()

    def hmp(self, command_line: str) -> str:
        resp = self.command("human-monitor-command", **{"command-line": command_line})
        if resp is None or "error" in resp:
            raise RuntimeError(f"HMP command {command_line!r} failed: {resp}")
        return resp["return"]

    def qom_list(self, path: str) -> list:
        resp = self.command("qom-list", path=path)
        if resp is None or "error" in resp:
            raise RuntimeError(f"qom-list {path!r} failed: {resp}")
        return resp["return"]

    def device_exists(self, path: str) -> bool:
        try:
            self.qom_list(path)
            return True
        except RuntimeError:
            return False

    def find_devices_by_type(self, type_name: str, base_path: str = "/machine/") -> list:
        try:
            children = self.qom_list(base_path)
        except RuntimeError:
            return []
        return [
            f"{base_path}/{c['name']}"
            for c in children
            if type_name in c.get("type", "")
        ]

    def stop(self):
        return self.command("stop")

    def quit(self):
        return self.command("quit")

    def close(self):
        self.sock_file.close()

class Shell(SocketHelper):
    PROMPT = b"> "

    def __init__(self, host: str, port: int):
        self._wait_for_port(host, port)
        sock = socket.create_connection((host, port))
        self.sock_file = sock.makefile("rwb")

    def _send(self, data: str):
        self.sock_file.write(data.encode())
        self.sock_file.flush()

    def _read_until(self, marker: bytes) -> bytes:
        buf = b""
        while not buf.endswith(marker):
            chunk = self.sock_file.read(1)
            if not chunk:
                raise ConnectionError("socket closed while waiting for prompt")
            buf += chunk
        return buf

    def send_cmd(self, cmd: str) -> str:
        self._send("\n")
        self._read_until(self.PROMPT)
        self._send(cmd + "\n")
        raw = self._read_until(self.PROMPT).strip()
        return raw.decode(errors="replace")

    def close(self):
        self.sock_file.close()

class GdbRemoteError(RuntimeError):
    """GDB remote returned an error reply (E<code>) or a malformed packet."""
    pass


class GdbRemoteError(RuntimeError):
    pass


class GdbRemote(SocketHelper):
    def __init__(self, host: str, port: int, timeout: float = 10.0):
        self._wait_for_port(host, port, timeout)
        self.sock = socket.create_connection((host, port))
        self.sock.settimeout(timeout)
        self._buf = b""
        self._phys_mode = None
        self._continue()

    @staticmethod
    def _checksum(data: bytes) -> int:
        return sum(data) & 0xFF

    def _send_packet(self, data: bytes):
        pkt = b"$" + data + b"#" + f"{self._checksum(data):02x}".encode()
        self.sock.sendall(pkt)

    def _recv_byte(self) -> bytes:
        if self._buf:
            b, self._buf = self._buf[:1], self._buf[1:]
            return b
        chunk = self.sock.recv(1)
        if not chunk:
            raise ConnectionError("gdbstub socket closed unexpectedly")
        return chunk

    def _recv_ack(self):
        b = self._recv_byte()
        if b == b"-":
            raise GdbRemoteError("gdbstub NACKed the packet (checksum mismatch on wire?)")
        if b != b"+":
            raise GdbRemoteError(f"expected ack '+', got {b!r}")

    def _recv_packet(self) -> bytes:
        while True:
            b = self._recv_byte()
            if b == b"$":
                break

        data = b""
        while True:
            b = self._recv_byte()
            if b == b"#":
                break
            data += b

        checksum_hex = self._recv_byte() + self._recv_byte()
        expected = int(checksum_hex, 16)
        actual = self._checksum(data)
        if actual == expected:
            self.sock.sendall(b"+")
        else:
            self.sock.sendall(b"-")
            raise GdbRemoteError(
                f"checksum mismatch: got {expected:02x}, computed {actual:02x}, data={data!r}"
            )
        return data

    def _execute(self, packet_body: bytes) -> bytes:
        self._send_packet(packet_body)
        self._recv_ack()
        reply = self._recv_packet()
        if reply.startswith(b"E") and len(reply) == 3:
            try:
                int(reply[1:], 16)
                raise GdbRemoteError(f"gdbstub returned error {reply.decode()}")
            except ValueError:
                pass
        return reply

    def _interrupt(self):
        self.sock.sendall(b"\x03")
        stop_reply = self._recv_packet()
        if not stop_reply:
            raise GdbRemoteError("no stop-reply after interrupt — VM may not have halted")
        return stop_reply

    def _continue(self):
        self._send_packet(b"vCont;c")
        self._recv_ack()

    class _Stopped:
        def __init__(self, remote: "GdbRemote"):
            self._remote = remote

        def __enter__(self):
            self._remote._interrupt()
            return self._remote

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._remote._continue()
            return False

    def stopped(self):
        return self._Stopped(self)

    def get_phys_mem_mode(self) -> bool:
        reply = self._execute(b"qqemu.PhyMemMode")
        if reply not in (b"0", b"1"):
            raise GdbRemoteError(f"unexpected PhyMemMode query reply: {reply!r}")
        self._phys_mode = reply == b"1"
        return self._phys_mode

    def set_phys_mem_mode(self, enabled: bool):
        reply = self._execute(b"Qqemu.PhyMemMode:" + (b"1" if enabled else b"0"))
        if reply != b"OK":
            raise GdbRemoteError(f"failed to set PhyMemMode={enabled}: {reply!r}")
        self._phys_mode = enabled

    def read_memory(self, addr: int, length: int) -> bytes:
        reply = self._execute(f"m{addr:x},{length:x}".encode())
        if len(reply) != length * 2:
            raise GdbRemoteError(
                f"read_memory({hex(addr)}, {length}) returned {len(reply)} hex chars, "
                f"expected {length * 2}: {reply!r}"
            )
        return bytes.fromhex(reply.decode())

    def write_memory(self, addr: int, data: bytes):
        payload = f"M{addr:x},{len(data):x}:".encode() + data.hex().encode()
        reply = self._execute(payload)
        if reply != b"OK":
            raise GdbRemoteError(f"write_memory({hex(addr)}, {data!r}) failed: {reply!r}")

    def read_mmio(self, addr: int, size: int = 4) -> int:
        with self.stopped():
            if self._phys_mode is not True:
                self.set_phys_mem_mode(True)
            raw = self.read_memory(addr, size)
        return int.from_bytes(raw, byteorder="little")

    def write_mmio(self, addr: int, value: int, size: int = 4):
        with self.stopped():
            if self._phys_mode is not True:
                self.set_phys_mem_mode(True)
            data = value.to_bytes(size, byteorder="little")
            self.write_memory(addr, data)

    def close(self):
        self.sock.close()

class Qemu:
    QMP_HOST = "127.0.0.1"
    QMP_PORT = 4444
    SHELL_HOST = "127.0.0.1"
    SHELL_PORT = 3333
    GDB_HOST = "127.0.0.1"
    GDB_PORT = 5555
    FIRMWARE = "../build/app-build/zephyr/zephyr.elf"
    QEMU_BIN = "../environment/qemu-vdpu/bin/qemu-system-aarch64"

    def __init__(self):
        self.proc = None
        self.qmp = None
        self.shell = None
        self.gdb = None

    def start(self, load_kernel: bool = True):
        cmd = [
            self.QEMU_BIN,
            "-cpu", "cortex-a53",
            "-nographic",
            "-machine", "virt,secure=on,gic-version=3",
            "-net", "none",
            "-chardev", f"socket,id=shell0,host=0.0.0.0,port={self.SHELL_PORT},server=on,wait=off",
            "-serial", "chardev:shell0",
            "-chardev", f"socket,id=qmp0,host=0.0.0.0,port={self.QMP_PORT},server=on,wait=off",
            "-object", "monitor-qmp,chardev=qmp0,id=qmp-mon",
            "-gdb", f"tcp::{self.GDB_PORT},server=on,wait=off",
            "-rtc", "clock=vm",
        ]

        if load_kernel:
            cmd.extend(["-kernel", self.FIRMWARE])

        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        try:
            self.gdb = GdbRemote(self.GDB_HOST, self.GDB_PORT)
            self.qmp = Qmp(self.QMP_HOST, self.QMP_PORT)
            self.shell = Shell(self.SHELL_HOST, self.SHELL_PORT)
        except (TimeoutError, ConnectionError, OSError):
            self._kill_proc()
            raise

    def stop(self):
        if self.qmp is not None:
            try:
                self.qmp.quit()
            except (OSError, BrokenPipeError):
                pass
            self.qmp.close()
            self.qmp = None

        if self.shell is not None:
            self.shell.close()
            self.shell = None

        if self.gdb is not None:
            self.gdb.close()
            self.gdb = None

        if self.proc is not None:
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._kill_proc()
            self.proc = None

    def _kill_proc(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=5)

    def send_cmd(self, cmd: str) -> str:
        return self.shell.send_cmd(cmd)

    def device_exists(self, path: str) -> bool:
        return self.qmp.device_exists(path)

    def find_devices_by_type(self, type_name: str) -> list:
        return self.qmp.find_devices_by_type(type_name)

    def read_mmio(self, addr: int, size: int = 4) -> int:
        return self.gdb.read_mmio(addr, size)

    def write_mmio(self, addr: int, value: int, size: int = 4):
        self.gdb.write_mmio(addr, value, size)

@pytest.fixture
def qemu():
    q = Qemu()
    q.start()
    yield q
    q.stop()

@pytest.fixture
def qemu_no_firmware():
    q = Qemu()
    q.start(load_kernel=False)
    yield q
    q.stop()
