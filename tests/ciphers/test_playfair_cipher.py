from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from rune_decrypter_prime.ciphers.playfair_cipher import Playfair29Cipher


def _make_cipher(**overrides) -> Playfair29Cipher:
    cfg = SimpleNamespace(
        filler_idx29=overrides.get("filler_idx29", 0),
        reduction_map=overrides.get("reduction_map", None),
    )
    return Playfair29Cipher(cfg)


def test_playfair_roundtrip_identity_key():
    cipher = _make_cipher()
    key = np.arange(cipher.reduced_size, dtype=np.uint8)
    base = np.tile(cipher.rep25_in_29, 2)
    plaintext = base[:40].astype(np.uint8, copy=False)

    ct = cipher._core_encrypt_batch(plaintext, key)
    recovered = cipher._core_decrypt_batch(ct[0], key)[0]

    np.testing.assert_array_equal(recovered, plaintext)


def test_playfair_handles_duplicate_letters_with_filler():
    cipher = _make_cipher(filler_idx29=5)
    key = np.arange(cipher.reduced_size, dtype=np.uint8)
    plaintext = np.array([7, 7, 12], dtype=np.uint8)

    cipher._core_encrypt_batch(plaintext, key)  # should not raise


def test_playfair_rejects_wrong_key_length():
    cipher = _make_cipher()
    bad_key = np.arange(10, dtype=np.uint8)
    plaintext = np.arange(10, dtype=np.uint8)
    with pytest.raises(ValueError):
        cipher._core_encrypt_batch(plaintext, bad_key)
