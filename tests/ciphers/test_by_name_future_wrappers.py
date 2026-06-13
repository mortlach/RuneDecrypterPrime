"""Smoke tests for by_name wrappers that back future presets."""
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import by_name, cipher_instance

pytestmark = pytest.mark.tier_a


@pytest.mark.parametrize(
    "name,kwargs,key_builder,text_len",
    [
        ("vigenere", {"key_length": 3}, lambda: np.array([3, 1, 4], dtype=np.uint8), 32),
        ("columnar", {"key_length": 4}, lambda: np.array([2, 0, 3, 1], dtype=np.uint8), 40),
        ("mono", {"key_length": 29}, lambda: np.arange(29, dtype=np.uint8), 29),
    ],
)
def test_by_name_cipher_instance_roundtrip(name, kwargs, key_builder, text_len):
    cipher = cipher_instance(name, **kwargs)
    key = key_builder()
    plaintext = (np.arange(text_len, dtype=np.uint8) * 3) % 29

    ciphertext = cipher.encrypt(plaintext=plaintext, key=key)
    ciphertext = np.asarray(
        ciphertext[0] if isinstance(ciphertext, tuple) or getattr(ciphertext, "ndim", 1) == 2 else ciphertext,
        dtype=np.uint8,
    )
    decrypted = cipher.decrypt(ciphertext=ciphertext, key=key)
    decrypted = np.asarray(
        decrypted[0] if isinstance(decrypted, tuple) or getattr(decrypted, "ndim", 1) == 2 else decrypted,
        dtype=np.uint8,
    )

    assert np.array_equal(decrypted, plaintext), f"{name} wrapper failed roundtrip"
