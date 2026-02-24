from __future__ import annotations

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    BatchEvalStats,
    decrypt_and_score_keys_chunked,
    score_plaintexts_chunked,
)


pytestmark = pytest.mark.tier_a


class _DummyCipher:
    def decrypt(self, *, ciphertext, key, interrupt_idx=None, interrupt_sym=None):  # noqa: ARG002
        ct = np.asarray(ciphertext, dtype=np.uint8).reshape(-1)
        k = np.asarray(key, dtype=np.int16)
        if k.ndim != 2:
            raise ValueError("key must be rank-2")
        shifts = (k[:, 0] % 29).astype(np.uint8)[:, None]
        return (ct[None, :] + shifts) % np.uint8(29)


class _BatchScorer:
    def __init__(self) -> None:
        self.batch_calls = 0

    def batch_score(self, pts, wli):  # noqa: ARG002
        self.batch_calls += 1
        arr = np.asarray(pts, dtype=np.uint8)
        return arr.sum(axis=1).astype(np.float64)

    def score(self, pt, wli):  # noqa: ARG002
        return float(np.asarray(pt, dtype=np.uint8).sum())


class _ScalarOnlyScorer:
    def score(self, pt, wli):  # noqa: ARG002
        return float(np.asarray(pt, dtype=np.uint8).sum())


def test_decrypt_and_score_keys_chunked_batch_path():
    cipher = _DummyCipher()
    scorer = _BatchScorer()
    ciphertext = np.asarray([1, 2, 3, 4], dtype=np.uint8)
    keys = [[0], [1], [2], [3], [4]]

    pts, scores, stats = decrypt_and_score_keys_chunked(
        cipher=cipher,
        ciphertext=ciphertext,
        keys=keys,
        scorer=scorer,
        wli=None,
        chunk_size=2,
        require_batch=True,
        stats=BatchEvalStats(),
    )

    assert pts.shape == (5, 4)
    expected_scores = np.asarray([10, 14, 18, 22, 26], dtype=np.float64)
    np.testing.assert_allclose(scores, expected_scores)
    assert scorer.batch_calls >= 1
    assert stats.batch_calls >= 1
    assert stats.scalar_fallback_calls == 0
    assert stats.candidates == 5


def test_score_plaintexts_chunked_respects_require_batch():
    plaintexts = np.asarray([[1, 2, 3], [4, 5, 6]], dtype=np.uint8)
    scalar = _ScalarOnlyScorer()

    with pytest.raises(RuntimeError):
        score_plaintexts_chunked(
            scorer=scalar,
            plaintexts=plaintexts,
            wli=None,
            chunk_size=2,
            require_batch=True,
        )

    scores, stats = score_plaintexts_chunked(
        scorer=scalar,
        plaintexts=plaintexts,
        wli=None,
        chunk_size=2,
        require_batch=False,
        stats=BatchEvalStats(),
    )
    np.testing.assert_allclose(scores, np.asarray([6.0, 15.0], dtype=np.float64))
    assert stats.scalar_fallback_calls >= 1
