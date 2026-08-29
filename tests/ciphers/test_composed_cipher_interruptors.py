from __future__ import annotations
import numpy as np
import pytest
from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import (
    PeriodicStructuredMatrixKeyOps,
)

pytestmark = pytest.mark.tier_a


def _make_cfg(period: int, A: int, columns: int, order: str) -> CipherConfig:
    return CipherConfig(
        ciphertext=[0],
        wli_data=[],
        key_length=period * A + columns,
        name="periodic_columnar",
        period=period,
        columns=columns,
        alphabet_size=A,
        order=order,
        keyops_hints={"period": period, "A": A, "columns": columns},
    )


def test_composed_cipher_with_interruptors_roundtrip():
    period = 2
    A = 5
    columns = 4
    key_len = period * A + columns
    rng = np.random.default_rng(5)
    keyops = PeriodicStructuredMatrixKeyOps(
        K=key_len, period=period, A=A, columns=columns
    )
    key = keyops.random(rng)
    pt = rng.integers(0, A, size=11, dtype=np.uint8)
    interrupt_idx = np.array([1, 6, 9], dtype=np.int64)
    cfg = _make_cfg(period, A, columns, "sub_then_col")
    cipher = PeriodicColumnarCipher(cfg)
    ct = cipher.encrypt_single(plaintext=pt, key=key, interrupt_idx=interrupt_idx)
    pt_out = cipher.decrypt_single(ciphertext=ct, key=key, interrupt_idx=interrupt_idx)
    assert np.array_equal(pt_out, pt)
