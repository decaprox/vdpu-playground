import pytest

from helpers import qemu, qemu_no_firmware

def test_hello(qemu):
    """Verify the firmware responds to a basic command."""
    assert "hello" in qemu.send_cmd("hello")

def test_hello_log(qemu):
    """Verify the firmware logs a "hello" message at info level in
    response to the hello command."""
    qemu.log.clear()
    qemu.send_cmd("hello")

    line = qemu.wait_for_log(
        "hello",
        min_level="inf",
        timeout=3.0
    )

