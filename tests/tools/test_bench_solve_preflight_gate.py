from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.types import Device, Direction
from tools.benchmarks.bench_solve_periodic_columnar_kaeding import _preflight_known_key_roundtrip


class _FakeRawScorer:
    def score(self, pt):
        arr = np.asarray(pt, dtype=np.float64).reshape(-1)
        if arr.size == 0:
            return float("-inf")
        return float(np.mean(arr))


class _FakePctScorer:
    def score_with_raw(self, pt, _wli):
        arr = np.asarray(pt, dtype=np.float64).reshape(-1)
        s = float(np.sum(arr))
        return s, s + 1.0


def _make_cipher(period: int = 2, columns: int = 1) -> PeriodicColumnarCipher:
    cfg = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        wli_data=[],
        key_length=period * 29 + columns,
        period=period,
        columns=columns,
        alphabet_size=29,
        order="col_then_sub",
        encoding_dir=Direction.LTR,
        device=Device.CPU,
    )
    return PeriodicColumnarCipher(cfg)


def _identity_key(period: int = 2, columns: int = 1) -> np.ndarray:
    blocks = [np.arange(29, dtype=np.int16) for _ in range(period)]
    tail = np.arange(columns, dtype=np.int16)
    return np.concatenate(blocks + [tail], axis=0).astype(np.int16, copy=False)


def test_preflight_known_key_roundtrip_passes_on_consistent_instance():
    period, columns = 2, 1
    cipher = _make_cipher(period=period, columns=columns)
    key = _identity_key(period=period, columns=columns)
    pt_true = np.asarray([0, 1, 2, 3, 4, 5, 6, 7], dtype=np.uint8)
    wli = [[i, len(pt_true)] for i in range(len(pt_true))]
    ct = cipher.encrypt_single(plaintext=pt_true, key=key)

    out = _preflight_known_key_roundtrip(
        cipher=cipher,
        ct_idx=ct,
        key_true=key,
        pt_true=pt_true,
        wli_list=wli,
        raw_full_scorer=_FakeRawScorer(),
        pct_scorer=_FakePctScorer(),
        tier_name="unit",
        text_id=0,
        key_seed=0,
    )
    assert out["preflight_roundtrip_ok"] == 1
    assert abs(float(out["preflight_score_delta_raw_full"])) < 1e-12
    assert abs(float(out["preflight_score_delta_pct"])) < 1e-12
    assert abs(float(out["preflight_score_delta_raw_native"])) < 1e-12


def test_preflight_known_key_roundtrip_raises_on_decrypt_mismatch():
    period, columns = 2, 1
    cipher = _make_cipher(period=period, columns=columns)
    key = _identity_key(period=period, columns=columns)
    pt_true = np.asarray([0, 1, 2, 3, 4, 5, 6, 7], dtype=np.uint8)
    pt_bad = pt_true.copy()
    pt_bad[0] = np.uint8(9)
    wli = [[i, len(pt_true)] for i in range(len(pt_true))]
    ct = cipher.encrypt_single(plaintext=pt_true, key=key)

    with pytest.raises(RuntimeError, match="known-key decrypt mismatch"):
        _preflight_known_key_roundtrip(
            cipher=cipher,
            ct_idx=ct,
            key_true=key,
            pt_true=pt_bad,
            wli_list=wli,
            raw_full_scorer=_FakeRawScorer(),
            pct_scorer=_FakePctScorer(),
            tier_name="unit",
            text_id=0,
            key_seed=0,
        )
