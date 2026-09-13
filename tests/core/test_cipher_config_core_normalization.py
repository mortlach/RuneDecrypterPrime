from __future__ import annotations
import pytest
from rdp.core.config.cipher import CipherConfig
from rdp.core.types import Device, Direction, KeyOpsFamily

def test_cipher_config_normalises_api_strings_to_core_enums() -> None:
    cfg = CipherConfig(ciphertext=[0, 1, 2], wli_data=[], key_length=3, device='cuda:0', encoding_dir='fwd', keyops_family='vector')
    assert cfg.device is Device.CUDA
    assert cfg.encoding_dir is Direction.LTR
    assert cfg.keyops_family is KeyOpsFamily.VECTOR

def test_cipher_config_rejects_unknown_keyops_family() -> None:
    with pytest.raises(ValueError, match='keyops family'):
        CipherConfig(ciphertext=[0, 1, 2], wli_data=[], key_length=3, keyops_family='quietly_guess')
