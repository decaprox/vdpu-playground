import pytest
from helpers import qemu, qemu_no_firmware

def test_dpi_present(qemu_no_firmware):
    """Verify the VDPU DPI device is present in the machine's device tree."""

    dpi = qemu_no_firmware.find_devices_by_type("vdpu-dpi")
    assert dpi, "VDPU DPI Engine not found in device tree"

def test_dpi_scan_matched(qemu):
    """A payload containing the signature reports MATCHED."""

    cmd = 'hwtest dpi evil "this is evil traffic"'
    result = "result=MATCHED"
    assert result in qemu.send_cmd(cmd)

def test_dpi_scan_pending(qemu):
    """A payload not containing the signature reports PENDING (no
    match found, no dead state reached, payload fully consumed)."""

    cmd = 'hwtest dpi evil "this is fine traffic"'
    result = "result=PENDING"
    assert result in qemu.send_cmd(cmd)

def test_dpi_scan_repeating_prefix(qemu):
    """A signature with a repeating prefix ("aaa") still matches
    correctly against input requiring a fail-transition partway
    through ("aaaa") -- this is the case a naive chain-without-fail
    automaton gets wrong."""

    cmd = 'hwtest dpi aaa aaaa'
    result = "result=MATCHED"
    assert result in qemu.send_cmd(cmd)

def test_dpi_scan_bytes_scanned_on_match(qemu):
    """bytes_scanned reflects early-exit at the match point, not the
    full payload length."""

    cmd = 'hwtest dpi evil "this is evil traffic"'
    result = "bytes_scanned=12"
    assert result in qemu.send_cmd(cmd)
