import pytest
from random import randint

from helpers import qemu_no_firmware

# VDPU FTA

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

# VDPU DPI

VDPU_DPI_REG_BASE                       = 0x09101000

VDPU_DPI_REG_DFA_TABLE_BASE_LO           = VDPU_DPI_REG_BASE + 0x00
VDPU_DPI_REG_DFA_TABLE_BASE_HI           = VDPU_DPI_REG_BASE + 0x04
VDPU_DPI_REG_DFA_NUM_STATES              = VDPU_DPI_REG_BASE + 0x08
VDPU_DPI_REG_DFA_ACCEPT_THRESHOLD        = VDPU_DPI_REG_BASE + 0x0c
VDPU_DPI_REG_DFA_PATTERN_ID_BASE_LO      = VDPU_DPI_REG_BASE + 0x10
VDPU_DPI_REG_DFA_PATTERN_ID_BASE_HI      = VDPU_DPI_REG_BASE + 0x14
VDPU_DPI_REG_DFA_DEAD_BITMAP_BASE_LO     = VDPU_DPI_REG_BASE + 0x18
VDPU_DPI_REG_DFA_DEAD_BITMAP_BASE_HI     = VDPU_DPI_REG_BASE + 0x1c
VDPU_DPI_REG_DFA_DESC_ADDR_LO            = VDPU_DPI_REG_BASE + 0x20
VDPU_DPI_REG_DFA_DESC_ADDR_HI            = VDPU_DPI_REG_BASE + 0x24
VDPU_DPI_REG_DFA_CONTROL                 = VDPU_DPI_REG_BASE + 0x28
VDPU_DPI_REG_DFA_STATUS                  = VDPU_DPI_REG_BASE + 0x2c  # RW1C
VDPU_DPI_REG_DFA_MAX_PAYLOAD_LEN         = VDPU_DPI_REG_BASE + 0x30  # Read only for guest

VDPU_DPI_CTRL_START      = 1 << 0
VDPU_DPI_CTRL_RESET      = 1 << 1

VDPU_DPI_STATUS_BUSY     = 1 << 0
VDPU_DPI_STATUS_DONE     = 1 << 1
VDPU_DPI_STATUS_ERROR    = 1 << 2

VDPU_DPI_MAX_PAYLOAD     = 0x800


@pytest.mark.parametrize("reg", [
    VDPU_DPI_REG_DFA_TABLE_BASE_LO,
    VDPU_DPI_REG_DFA_TABLE_BASE_HI,
    VDPU_DPI_REG_DFA_NUM_STATES,
    VDPU_DPI_REG_DFA_ACCEPT_THRESHOLD,
    VDPU_DPI_REG_DFA_PATTERN_ID_BASE_LO,
    VDPU_DPI_REG_DFA_PATTERN_ID_BASE_HI,
    VDPU_DPI_REG_DFA_DEAD_BITMAP_BASE_LO,
    VDPU_DPI_REG_DFA_DEAD_BITMAP_BASE_HI,
    VDPU_DPI_REG_DFA_DESC_ADDR_LO,
    VDPU_DPI_REG_DFA_DESC_ADDR_HI,
])
def test_vdpu_dpi_mmio_read_write_32(qemu_no_firmware, reg):
    v = randint(0, 0xffffffff)
    qemu_no_firmware.write_mmio(reg, v)
    assert v == qemu_no_firmware.read_mmio(reg)


@pytest.mark.parametrize("reg", [
    VDPU_DPI_REG_DFA_MAX_PAYLOAD_LEN,
])
def test_vdpu_dpi_mmio_read_write_read_only_32(qemu_no_firmware, reg):
    before = qemu_no_firmware.read_mmio(reg)
    v = randint(1, 0xffffffff)
    qemu_no_firmware.write_mmio(reg, v)
    assert before == qemu_no_firmware.read_mmio(reg)


@pytest.mark.parametrize("lo, hi", [
    (VDPU_DPI_REG_DFA_TABLE_BASE_LO, VDPU_DPI_REG_DFA_TABLE_BASE_HI),
    (VDPU_DPI_REG_DFA_PATTERN_ID_BASE_LO, VDPU_DPI_REG_DFA_PATTERN_ID_BASE_HI),
    (VDPU_DPI_REG_DFA_DEAD_BITMAP_BASE_LO, VDPU_DPI_REG_DFA_DEAD_BITMAP_BASE_HI),
    (VDPU_DPI_REG_DFA_DESC_ADDR_LO, VDPU_DPI_REG_DFA_DESC_ADDR_HI),
])
def test_vdpu_dpi_mmio_lo_hi_independent(qemu_no_firmware, lo, hi):
    """LO and HI are two separate 32-bit registers, not one contiguous
    64-bit register — verify writes to one don't disturb the other."""
    v_lo = randint(0, 0xffffffff)
    v_hi = randint(0, 0xffffffff)
    qemu_no_firmware.write_mmio(lo, v_lo)
    qemu_no_firmware.write_mmio(hi, v_hi)
    assert v_lo == qemu_no_firmware.read_mmio(lo)
    assert v_hi == qemu_no_firmware.read_mmio(hi)


def test_vdpu_dpi_mmio_max_payload_len_matches_device(qemu_no_firmware):
    assert VDPU_DPI_MAX_PAYLOAD == qemu_no_firmware.read_mmio(VDPU_DPI_REG_DFA_MAX_PAYLOAD_LEN)


def test_vdpu_dpi_mmio_ctrl_start_bit_self_clears(qemu_no_firmware):
    """START is a strobe bit: writing it triggers a scan and the bit
    reads back as 0 afterward, it does not stay latched."""
    qemu_no_firmware.write_mmio(VDPU_DPI_REG_DFA_CONTROL, VDPU_DPI_CTRL_START)
    ctrl = qemu_no_firmware.read_mmio(VDPU_DPI_REG_DFA_CONTROL)
    assert 0 == (ctrl & VDPU_DPI_CTRL_START)


def test_vdpu_dpi_mmio_ctrl_reset_bit_self_clears(qemu_no_firmware):
    """RESET is a strobe bit: writing it triggers a reset and the bit
    reads back as 0 afterward, it does not stay latched."""
    qemu_no_firmware.write_mmio(VDPU_DPI_REG_DFA_CONTROL, VDPU_DPI_CTRL_RESET)
    ctrl = qemu_no_firmware.read_mmio(VDPU_DPI_REG_DFA_CONTROL)
    assert 0 == (ctrl & VDPU_DPI_CTRL_RESET)


def test_vdpu_dpi_mmio_status_busy_bit_read_only(qemu_no_firmware):
    """BUSY is RO within the STATUS register: a guest write to STATUS
    must not be able to set or clear BUSY directly, only DONE/ERROR
    are writable (RW1C)."""
    before = qemu_no_firmware.read_mmio(VDPU_DPI_REG_DFA_STATUS) & VDPU_DPI_STATUS_BUSY
    qemu_no_firmware.write_mmio(VDPU_DPI_REG_DFA_STATUS, VDPU_DPI_STATUS_BUSY)
    after = qemu_no_firmware.read_mmio(VDPU_DPI_REG_DFA_STATUS) & VDPU_DPI_STATUS_BUSY
    assert before == after


def test_vdpu_dpi_mmio_status_done_error_write_1_to_clear(qemu_no_firmware):
    """DONE and ERROR are RW1C: after RESET (which clears the whole
    device, including STATUS) they read as 0, and writing 1 to them
    while already 0 is a no-op, not an error."""
    qemu_no_firmware.write_mmio(VDPU_DPI_REG_DFA_CONTROL, VDPU_DPI_CTRL_RESET)
    status = qemu_no_firmware.read_mmio(VDPU_DPI_REG_DFA_STATUS)
    assert 0 == (status & (VDPU_DPI_STATUS_DONE | VDPU_DPI_STATUS_ERROR))

    qemu_no_firmware.write_mmio(VDPU_DPI_REG_DFA_STATUS,
                                 VDPU_DPI_STATUS_DONE | VDPU_DPI_STATUS_ERROR)
    status = qemu_no_firmware.read_mmio(VDPU_DPI_REG_DFA_STATUS)
    assert 0 == (status & (VDPU_DPI_STATUS_DONE | VDPU_DPI_STATUS_ERROR))


def test_vdpu_dpi_mmio_reset_clears_config_registers(qemu_no_firmware):
    """RESET zeroes the config-base registers, not just CONTROL/STATUS."""
    qemu_no_firmware.write_mmio(VDPU_DPI_REG_DFA_TABLE_BASE_LO, randint(1, 0xffffffff))
    qemu_no_firmware.write_mmio(VDPU_DPI_REG_DFA_NUM_STATES, randint(1, 0xffffffff))
    qemu_no_firmware.write_mmio(VDPU_DPI_REG_DFA_DESC_ADDR_LO, randint(1, 0xffffffff))

    qemu_no_firmware.write_mmio(VDPU_DPI_REG_DFA_CONTROL, VDPU_DPI_CTRL_RESET)

    assert 0 == qemu_no_firmware.read_mmio(VDPU_DPI_REG_DFA_TABLE_BASE_LO)
    assert 0 == qemu_no_firmware.read_mmio(VDPU_DPI_REG_DFA_NUM_STATES)
    assert 0 == qemu_no_firmware.read_mmio(VDPU_DPI_REG_DFA_DESC_ADDR_LO)
