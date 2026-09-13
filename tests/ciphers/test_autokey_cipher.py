from __future__ import annotations
from types import SimpleNamespace
import numpy as np
import pytest
from rdp.ciphers.autokey_cipher import AutokeyCipher
pytestmark = pytest.mark.tier_a

def _make_cfg(seed_len: int=3, alphabet_size: int=29):
    return SimpleNamespace(seed_length=seed_len, alphabet_size=alphabet_size, text_transposition='ltr', key_transposition='ltr')

def test_autokey_roundtrip_encrypt_decrypt():
    cipher = AutokeyCipher(_make_cfg(seed_len=4))
    seed = np.array([6, 1, 4, 2], dtype=np.uint8)
    plaintext = np.arange(40, dtype=np.uint8) % cipher.alphabet_size
    ciphertext = cipher.encrypt_single(plaintext=plaintext, key=seed)
    recovered = cipher.decrypt_single(ciphertext=ciphertext, key=seed)
    np.testing.assert_array_equal(recovered, plaintext)

def test_autokey_batch_keys_supported():
    cipher = AutokeyCipher(_make_cfg(seed_len=3))
    seed_bank = np.array([[6, 1, 4], [8, 5, 2]], dtype=np.uint8)
    plaintext = np.arange(15, dtype=np.uint8) % cipher.alphabet_size
    ciphertext = cipher.encrypt(plaintext=plaintext, key=seed_bank[0])
    assert ciphertext.shape == (1, plaintext.size)
    plains = cipher.decrypt(ciphertext=ciphertext[0], key=seed_bank)
    assert plains.shape == (seed_bank.shape[0], plaintext.size)
    np.testing.assert_array_equal(plains[0], plaintext)

def test_autokey_rejects_wrong_seed_length():
    cipher = AutokeyCipher(_make_cfg(seed_len=3))
    seed = np.array([1, 2], dtype=np.uint8)
    plaintext = np.arange(6, dtype=np.uint8) % cipher.alphabet_size
    with pytest.raises(ValueError):
        cipher.encrypt_single(plaintext=plaintext, key=seed)
    ciphertext = (plaintext + 1) % cipher.alphabet_size
    with pytest.raises(ValueError):
        cipher.decrypt_single(ciphertext=ciphertext, key=seed)
