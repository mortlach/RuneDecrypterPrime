from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from rune_decrypter_prime.scoring.unified_rune_scorer import UnifiedRuneScorer


pytestmark = pytest.mark.tier_a


def _mk_unified(backend) -> UnifiedRuneScorer:
    scorer = object.__new__(UnifiedRuneScorer)
    scorer._backend = backend
    scorer._backend_name = "torch"
    scorer._out_dtype = np.float64
    scorer._dtype = "float64"
    scorer._compute_dtype = "float32"
    scorer._acc_dtype = "float64"
    scorer.cfg_cipher = SimpleNamespace(device="cpu", wli_data=[])
    scorer.cfg_scorer = {}
    return scorer


def test_batch_score_with_raw_propagates_backend_runtime_error() -> None:
    class _Backend:
        def batch_score_with_raw(self, pts, wlis=None):  # noqa: ARG002
            raise RuntimeError("backend raw failure")

        def batch_score(self, pts, wlis=None):  # noqa: ARG002
            return np.asarray([1.0], dtype=np.float64)

    scorer = _mk_unified(_Backend())
    with pytest.raises(RuntimeError, match="backend raw failure"):
        scorer.batch_score_with_raw([np.asarray([1, 2, 3], dtype=np.uint8)])


def test_batch_score_with_raw_falls_back_on_not_implemented() -> None:
    class _Backend:
        def batch_score_with_raw(self, pts, wlis=None):  # noqa: ARG002
            raise NotImplementedError("not wired")

        def batch_score(self, pts, wlis=None):  # noqa: ARG002
            return np.asarray([3.5, 4.5], dtype=np.float64)

    scorer = _mk_unified(_Backend())
    pct, raw = scorer.batch_score_with_raw([np.asarray([1], dtype=np.uint8), np.asarray([2], dtype=np.uint8)])
    np.testing.assert_allclose(pct, np.asarray([3.5, 4.5], dtype=np.float64))
    np.testing.assert_allclose(raw, pct)


def test_score_with_raw_propagates_backend_runtime_error() -> None:
    class _Backend:
        def score_with_raw(self, plaintext, wli_windows=None):  # noqa: ARG002
            raise RuntimeError("backend score failure")

        def score(self, plaintext, wli_windows=None):  # noqa: ARG002
            return 1.0

    scorer = _mk_unified(_Backend())
    with pytest.raises(RuntimeError, match="backend score failure"):
        scorer.score_with_raw(np.asarray([1, 2, 3], dtype=np.uint8))


def test_score_with_raw_falls_back_on_not_implemented() -> None:
    class _Backend:
        def score_with_raw(self, plaintext, wli_windows=None):  # noqa: ARG002
            raise NotImplementedError("raw not implemented")

        def score(self, plaintext, wli_windows=None):  # noqa: ARG002
            return 7.25

    scorer = _mk_unified(_Backend())
    pct, raw = scorer.score_with_raw(np.asarray([1, 2, 3], dtype=np.uint8))
    assert pct == pytest.approx(7.25)
    assert raw == pytest.approx(7.25)


def test_to_text_propagates_backend_runtime_error() -> None:
    class _Backend:
        def to_text(self, plaintext):  # noqa: ARG002
            raise RuntimeError("to_text failure")

    scorer = _mk_unified(_Backend())
    with pytest.raises(RuntimeError, match="to_text failure"):
        scorer.to_text(np.asarray([1, 2, 3], dtype=np.uint8))


def test_to_text_falls_back_on_not_implemented() -> None:
    class _Backend:
        def to_text(self, plaintext):  # noqa: ARG002
            raise NotImplementedError("not implemented")

    scorer = _mk_unified(_Backend())
    text = scorer.to_text(np.asarray([1, 2, 3], dtype=np.uint8))
    assert isinstance(text, str)
