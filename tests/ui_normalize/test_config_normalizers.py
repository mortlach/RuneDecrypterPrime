from __future__ import annotations
import pytest
from rune_decrypter_prime.core.types import Direction, Device
from rune_decrypter_prime.api.normalize import normalize_encoding_dir, normalize_device

def test_normalize_direction_accepts_enum_and_strings():
    assert normalize_encoding_dir(Direction.LTR) is Direction.LTR
    assert normalize_encoding_dir(Direction.RTL) is Direction.RTL
    assert normalize_encoding_dir("ltr") is Direction.LTR
    assert normalize_encoding_dir("RTL") is Direction.RTL
    # API-only aliases (UI boundary)
    assert normalize_encoding_dir("LTR") is Direction.LTR
    assert normalize_encoding_dir("rtl") is Direction.RTL

@pytest.mark.parametrize("bad", [None, 123, "left", "right", object()])
def test_normalize_direction_rejects_bad_inputs(bad):
    with pytest.raises(ValueError):
        normalize_encoding_dir(bad)

def test_normalize_device_accepts_enum_and_strings():
    assert normalize_device(Device.CPU) is Device.CPU
    assert normalize_device(Device.CUDA) is Device.CUDA
    assert normalize_device("cpu") is Device.CPU
    assert normalize_device("cuda") is Device.CUDA
    assert normalize_device("gpu") is Device.CUDA  # alias

@pytest.mark.parametrize("bad", [None, 0, "tpu", "metal", object()])
def test_normalize_device_rejects_bad_inputs(bad):
    with pytest.raises(TypeError):
        normalize_device(bad)
