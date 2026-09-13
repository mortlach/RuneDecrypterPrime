"""Known-key round trips for supported V1 cipher specifications."""
from __future__ import annotations
from rdp import api
import numpy as np
import pytest
pytestmark = pytest.mark.tier_a

@pytest.mark.parametrize('cipher,key_builder,text_len', [(api.CipherSpec.vigenere(), lambda: np.array([3, 1, 4], dtype=np.uint8), 32), (api.CipherSpec.columnar(columns=4), lambda: np.array([2, 0, 3, 1], dtype=np.uint8), 40), (api.CipherSpec.substitution(), lambda: np.arange(29, dtype=np.uint8), 29)])
def test_typed_cipher_roundtrip(cipher, key_builder, text_len):
    key = key_builder()
    plaintext = np.arange(text_len, dtype=np.uint8) * 3 % 29
    concrete_key = tuple(int(value) for value in key)
    ciphertext = api.encrypt(tuple(int(value) for value in plaintext), cipher=cipher, key=concrete_key)
    decrypted = api.decrypt(ciphertext, cipher=cipher, key=concrete_key)
    assert np.array_equal(decrypted, plaintext)
