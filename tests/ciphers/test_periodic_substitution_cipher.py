import numpy as np
import pytest
from rdp.core.config.cipher import CipherConfig
from rune_decrypter_prime.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
pytestmark = pytest.mark.tier_a

def _ref_periodic_decrypt(ct: np.ndarray, key: np.ndarray, period: int, A: int) -> np.ndarray:
    out = np.empty_like(ct)
    for i, c in enumerate(ct.tolist()):
        out[i] = key[i % period * A + int(c)]
    return out

def test_periodic_substitution_roundtrip():
    period = 3
    A = 7
    key_len = period * A
    cfg = CipherConfig(ciphertext=[0], wli_data=[], key_length=key_len, name='periodic_substitution', period=period, alphabet_size=A, keyops_hints={'period': period, 'A': A})
    cipher = PeriodicSubstitutionCipher(cfg)
    rng = np.random.default_rng(0)
    keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=period, A=A)
    key = keyops.random(rng)
    pt = np.array([0, 1, 2, 3, 4, 5, 6, 0, 2, 4, 6, 1], dtype=np.uint8)
    ct = cipher.encrypt_single(plaintext=pt, key=key)
    pt_out = cipher.decrypt_single(ciphertext=ct, key=key)
    assert np.array_equal(pt_out, pt)
    assert np.array_equal(_ref_periodic_decrypt(ct, key, period, A), pt_out)

def test_periodic_substitution_bad_key_length():
    period = 2
    A = 5
    key_len = period * A
    cfg = CipherConfig(ciphertext=[0], wli_data=[], key_length=key_len, name='periodic_substitution', period=period, alphabet_size=A, keyops_hints={'period': period, 'A': A})
    cipher = PeriodicSubstitutionCipher(cfg)
    key = np.arange(key_len - 1, dtype=np.int16)
    with pytest.raises(ValueError):
        cipher.decrypt_single(ciphertext=np.array([0, 1, 2], dtype=np.uint8), key=key)

def test_periodic_substitution_rejects_non_permutation_blocks():
    period = 2
    A = 5
    key_len = period * A
    cfg = CipherConfig(ciphertext=[0], wli_data=[], key_length=key_len, name='periodic_substitution', period=period, alphabet_size=A, keyops_hints={'period': period, 'A': A})
    cipher = PeriodicSubstitutionCipher(cfg)
    bad = np.array([0, 1, 1, 3, 4, 0, 1, 2, 3, 4], dtype=np.int16)
    with pytest.raises(ValueError):
        cipher.decrypt_single(ciphertext=np.array([0, 1, 2], dtype=np.uint8), key=bad)
    bad2 = np.array([0, 1, 2, 3, 5, 0, 1, 2, 3, 4], dtype=np.int16)
    with pytest.raises(ValueError):
        cipher.encrypt_single(plaintext=np.array([0, 1, 2], dtype=np.uint8), key=bad2)

@pytest.mark.tier_a
@pytest.mark.parametrize('length', [1, 2, 6, 7, 8, 15])
def test_periodic_substitution_encrypt_decrypt_roundtrip_random(length):
    period = 3
    A = 7
    key_len = period * A
    cfg = CipherConfig(ciphertext=[0], wli_data=[], key_length=key_len, name='periodic_substitution', period=period, alphabet_size=A, keyops_hints={'period': period, 'A': A})
    cipher = PeriodicSubstitutionCipher(cfg)
    rng = np.random.default_rng(123)
    keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=period, A=A)
    key = keyops.random(rng)
    pt = rng.integers(0, A, size=length, dtype=np.uint8)
    ct = cipher.encrypt_single(plaintext=pt, key=key)
    pt_out = cipher.decrypt_single(ciphertext=ct, key=key)
    assert np.array_equal(pt_out, pt)
