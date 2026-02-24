from __future__ import annotations

import types

import numpy as np
import pytest

from rune_decrypter_prime.core.types import SeMode


pytestmark = pytest.mark.tier_a


def _fake_torch_scorer():
    pytest.importorskip("torch")
    from rune_decrypter_prime.scoring.torch_rune_scorer import RuneScorerTorch

    scorer = object.__new__(RuneScorerTorch)
    scorer.se_mode = SeMode.NOSE

    def _score_batch_impl(self, pt_b, wli_b):  # noqa: ARG001
        return np.asarray(pt_b, dtype=np.float32).sum(axis=1)

    scorer._score_batch_impl = types.MethodType(_score_batch_impl, scorer)
    return scorer, RuneScorerTorch


def test_torch_batch_score_accepts_numpy_rank2():
    scorer, cls = _fake_torch_scorer()
    pts = np.asarray([[1, 2, 3], [4, 5, 6]], dtype=np.uint8)
    got = cls.batch_score(scorer, pts, None)
    np.testing.assert_allclose(got, np.asarray([6.0, 15.0], dtype=np.float64))


def test_torch_batch_score_accepts_numpy_rank1():
    scorer, cls = _fake_torch_scorer()
    pts = np.asarray([7, 8, 9], dtype=np.uint8)
    got = cls.batch_score(scorer, pts, None)
    np.testing.assert_allclose(got, np.asarray([24.0], dtype=np.float64))


def test_torch_batch_score_accepts_empty_numpy_batch():
    scorer, cls = _fake_torch_scorer()
    pts = np.empty((0, 5), dtype=np.uint8)
    got = cls.batch_score(scorer, pts, None)
    assert isinstance(got, np.ndarray)
    assert got.shape == (0,)
