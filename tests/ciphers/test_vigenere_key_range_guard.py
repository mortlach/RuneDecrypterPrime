import numpy as np
import pytest
from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.ciphers.vigenere_cipher import RuneVigenereCipher
from rdp.core.types import Direction
pytestmark = pytest.mark.tier_a

def _mk_cipher():
    cfg = CipherConfig(ciphertext=[0, 1, 2], wli_data=[[0, 3], [1, 3], [2, 3]], key_length=1, name='vigenere', encoding_dir=Direction.LTR)
    return RuneVigenereCipher(cfg)

def test_vigenere_rejects_out_of_range_key_values():
    cipher = _mk_cipher()
    pt = np.array([0, 1, 2], dtype=np.uint8)
    ct = np.array([0, 1, 2], dtype=np.uint8)
    with pytest.raises(ValueError):
        cipher.encrypt_single(plaintext=pt, key=np.array([30], dtype=np.int16))
    with pytest.raises(ValueError):
        cipher.decrypt_single(ciphertext=ct, key=np.array([-1], dtype=np.int16))
