import pytest

from helpers import qemu

def test_hello(qemu):
    assert "hello" in qemu.send_cmd("hello")
