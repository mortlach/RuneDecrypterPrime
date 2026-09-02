import numpy as np
import pytest
from rdp.core.config.cipher import CipherConfig
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rdp.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
pytestmark = pytest.mark.tier_a

def _make_cfg(period: int, A: int, columns: int, order: str) -> CipherConfig:
    return CipherConfig(ciphertext=[0], wli_data=[], key_length=period * A + columns, name='periodic_columnar', period=period, columns=columns, alphabet_size=A, order=order, keyops_hints={'period': period, 'A': A, 'columns': columns})

def test_periodic_columnar_roundtrip_both_orders():
    period = 2
    A = 5
    columns = 4
    key_len = period * A + columns
    rng = np.random.default_rng(0)
    keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=period, A=A, columns=columns)
    key = keyops.random(rng)
    pt = np.array([0, 1, 2, 3, 4, 0, 2, 4, 1, 3, 0, 4, 2], dtype=np.uint8)
    for order in ('sub_then_col', 'col_then_sub'):
        cfg = _make_cfg(period, A, columns, order)
        cipher = PeriodicColumnarCipher(cfg)
        ct = cipher.encrypt_single(plaintext=pt, key=key)
        pt_out = cipher.decrypt_single(ciphertext=ct, key=key)
        assert np.array_equal(pt_out, pt)

def test_periodic_columnar_columns_one():
    period = 3
    A = 7
    columns = 1
    key_len = period * A + columns
    rng = np.random.default_rng(1)
    keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=period, A=A, columns=columns)
    key = keyops.random(rng)
    pt = np.array([0, 1, 2, 3, 4, 5, 6, 0], dtype=np.uint8)
    cfg = _make_cfg(period, A, columns, 'sub_then_col')
    cipher = PeriodicColumnarCipher(cfg)
    ct = cipher.encrypt_single(plaintext=pt, key=key)
    pt_out = cipher.decrypt_single(ciphertext=ct, key=key)
    assert np.array_equal(pt_out, pt)

@pytest.mark.tier_a
@pytest.mark.parametrize('length, columns', [(7, 4), (10, 6), (13, 5)])
def test_periodic_columnar_roundtrip_lengths_not_multiple_of_columns(length, columns):
    period = 2
    A = 5
    key_len = period * A + columns
    rng = np.random.default_rng(4)
    keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=period, A=A, columns=columns)
    key = keyops.random(rng)
    pt = rng.integers(0, A, size=length, dtype=np.uint8)
    cfg = _make_cfg(period, A, columns, 'sub_then_col')
    cipher = PeriodicColumnarCipher(cfg)
    ct = cipher.encrypt_single(plaintext=pt, key=key)
    pt_out = cipher.decrypt_single(ciphertext=ct, key=key)
    assert np.array_equal(pt_out, pt)
