from __future__ import annotations
import numpy as np
import pytest
from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.ciphers.vigenere_cipher import RuneVigenereCipher
from rdp.core.types import Direction
pytestmark = pytest.mark.tier_a

def test_variable_interruptors():
    ct = np.arange(6, dtype=np.uint8)
    wli = [[i, 6] for i in range(6)]
    perm = [4, 3, 2, 1, 0]
    cfg = CipherConfig(ciphertext=ct, wli_data=wli, key_length=1, name='vigenere', encoding_dir=Direction.LTR, initial_text_permutation_indices=perm)
    cipher = RuneVigenereCipher(cfg)
    key = np.array([0], dtype=np.uint8)
    with pytest.raises(ValueError):
        cipher.decrypt(ciphertext=ct, key=key, interrupt_idx=None)
