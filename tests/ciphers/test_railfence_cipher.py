from __future__ import annotations
from types import SimpleNamespace
import numpy as np
import pytest
from rune_decrypter_prime.ciphers.railfence_cipher import RailFenceCipher

pytestmark = pytest.mark.tier_a


def _make_cipher(**overrides) -> RailFenceCipher:
    cfg_kwargs = dict(min_rails=2, max_rails=6)
    cfg_kwargs.update(overrides)
    return RailFenceCipher(SimpleNamespace(**cfg_kwargs))


def _key_for(cipher: RailFenceCipher, rails: int) -> np.ndarray:
    """Return the semantic rail count used by the canonical key contract."""
    return np.asarray([rails], dtype=np.uint8)


def test_railfence_encrypt_decrypt_roundtrip():
    cipher = _make_cipher()
    rails = 4
    key = _key_for(cipher, rails)
    plaintext = np.arange(45, dtype=np.uint8) % cipher.A
    ciphertext = cipher.encrypt(plaintext=plaintext, key=key)
    recovered = cipher.decrypt(ciphertext=ciphertext, key=key)
    assert ciphertext.shape == plaintext.shape
    assert recovered.shape == plaintext.shape
    np.testing.assert_array_equal(recovered, plaintext)


def test_railfence_batch_keys_support():
    cipher = _make_cipher()
    rails_values = [2, 5, 6]
    keys = np.vstack([_key_for(cipher, r) for r in rails_values])
    plaintext = np.arange(30, dtype=np.uint8) % cipher.A
    ciphertext = cipher.encrypt(plaintext=plaintext, key=keys)
    assert ciphertext.shape == (len(rails_values), plaintext.size)
    recovered = cipher.decrypt(ciphertext=ciphertext[1], key=keys[1])
    np.testing.assert_array_equal(recovered, plaintext)


def test_railfence_fixed_rails_must_be_in_range():
    with pytest.raises(ValueError):
        _make_cipher(rails_fixed=1)
    with pytest.raises(ValueError):
        _make_cipher(min_rails=2, max_rails=4, rails_fixed=6)
