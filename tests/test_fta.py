import pytest
from helpers import qemu, qemu_no_firmware

def test_fta_present(qemu_no_firmware):
    """Verify the VDPU FTA device is present in the machine's device tree."""

    fta = qemu_no_firmware.find_devices_by_type("vdpu-fta")
    assert fta, "VDPU Flow Table Accelerator not found in device tree"

def test_fta_insert_flow_id_not_established(qemu):
    """A single lookup for a new 5-tuple allocates flow_id=0x1 and reports
    is_established=0."""

    cmd = "hwtest fta 1.1.1.1 2.2.2.2 60001 443 6"
    result = "flow_id=0x1 is_established=0"
    assert result in qemu.send_cmd(cmd)

def test_fta_insert_flow_id_established(qemu):
    """Repeating the same lookup for an already-inserted 5-tuple returns
    the same flow_id=0x1 with is_established=1."""

    cmd = "hwtest fta 1.1.1.1 2.2.2.2 60001 443 6"
    result = "flow_id=0x1 is_established=1"
    qemu.send_cmd(cmd)
    assert result in qemu.send_cmd(cmd)
