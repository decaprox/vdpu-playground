import pytest
from random import randint

from helpers import qemu_no_firmware

VDPU_FTA_REG_BASE            = 0x09100000

VDPU_FTA_REG_CTRL            = VDPU_FTA_REG_BASE + 0x00
VDPU_FTA_REG_STATUS          = VDPU_FTA_REG_BASE + 0x04  # Read only for guest
VDPU_FTA_REG_DESC_ADDR_LO    = VDPU_FTA_REG_BASE + 0x08
VDPU_FTA_REG_DESC_ADDR_HI    = VDPU_FTA_REG_BASE + 0x0c
VDPU_FTA_REG_IRQ_ENABLE      = VDPU_FTA_REG_BASE + 0x10
VDPU_FTA_REG_IRQ_STATUS      = VDPU_FTA_REG_BASE + 0x14  # RW1C
VDPU_FTA_REG_TABLE_SIZE      = VDPU_FTA_REG_BASE + 0x18  # # Read only for guest
VDPU_FTA_REG_TABLE_COUNT     = VDPU_FTA_REG_BASE + 0x1c  # Read only for guest

VDPU_FTA_REG_CTRL_ENABLE     = 1 << 0
VDPU_FTA_REG_CTRL_RESET      = 1 << 1

VDPU_FTA_REG_STATUS_DONE     = 1 << 0
VDPU_FTA_REG_STATUS_BUSY     = 1 << 1
VDPU_FTA_REG_STATUS_ERROR    = 1 << 2

VDPU_FTA_REG_IRQ_ENABLE_MASK = 1 << 0
VDPU_FTA_REG_IRQ_STATUS_DONE = 1 << 0

VDPU_FTA_TABLE_SIZE          = 4096


@pytest.mark.parametrize("reg", [
    VDPU_FTA_REG_DESC_ADDR_LO,
    VDPU_FTA_REG_DESC_ADDR_HI,
])
def test_vdpu_fta_mmio_read_write_32(qemu_no_firmware, reg):
    v = randint(0, 0xffffffff)
    qemu_no_firmware.write_mmio(reg, v)
    assert v == qemu_no_firmware.read_mmio(reg)


@pytest.mark.parametrize("reg", [
    VDPU_FTA_REG_STATUS,
])
def test_vdpu_fta_mmio_read_write_read_only_32(qemu_no_firmware, reg):
    v = randint(1, 0xffffffff)
    qemu_no_firmware.write_mmio(reg, v)
    assert 0 == qemu_no_firmware.read_mmio(reg)


def test_vdpu_fta_mmio_desc_addr_lo_hi_independent(qemu_no_firmware):
    """DESC_ADDR_LO and DESC_ADDR_HI are two separate 32-bit registers,
    not one contiguous 64-bit register — verify writes to one don't
    disturb the other."""
    lo = randint(0, 0xffffffff)
    hi = randint(0, 0xffffffff)

    qemu_no_firmware.write_mmio(VDPU_FTA_REG_DESC_ADDR_LO, lo)
    qemu_no_firmware.write_mmio(VDPU_FTA_REG_DESC_ADDR_HI, hi)

    assert lo == qemu_no_firmware.read_mmio(VDPU_FTA_REG_DESC_ADDR_LO)
    assert hi == qemu_no_firmware.read_mmio(VDPU_FTA_REG_DESC_ADDR_HI)


def test_vdpu_fta_mmio_table_size_within_capacity(qemu_no_firmware):
    assert VDPU_FTA_TABLE_SIZE == qemu_no_firmware.read_mmio(VDPU_FTA_REG_TABLE_SIZE)

def test_vdpu_fta_mmio_ctrl_reset_bit_self_clears(qemu_no_firmware):
    """RESET is a strobe bit: writing it triggers a reset and the bit
    reads back as 0 afterward, it does not stay latched."""
    qemu_no_firmware.write_mmio(VDPU_FTA_REG_CTRL, VDPU_FTA_REG_CTRL_RESET)
    ctrl = qemu_no_firmware.read_mmio(VDPU_FTA_REG_CTRL)
    assert 0 == (ctrl & VDPU_FTA_REG_CTRL_RESET)
