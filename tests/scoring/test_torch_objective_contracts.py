from __future__ import annotations

import types

import numpy as np
import pytest

from rune_decrypter_prime.core.types import ObjectiveFamily, ObjectiveSpec, Stat
from rune_decrypter_prime.scoring.torch_rune_scorer import RuneScorerTorch


pytestmark = pytest.mark.tier_a


def _make_fake_scorer_with_objective(obj: ObjectiveSpec) -> RuneScorerTorch:
    scorer = object.__new__(RuneScorerTorch)
    scorer.objective = obj
    scorer.win = int(obj.win or 10)
    return scorer


def test_score_batch_impl_routes_avg_logp_to_raw_path() -> None:
    scorer = _make_fake_scorer_with_objective(
        ObjectiveSpec(family=ObjectiveFamily.AVG, stat=Stat.LOGP, win=20)
    )

    def _raw_stub(self, pt_b: np.ndarray, wli_b):  # noqa: ARG001
        return np.full((pt_b.shape[0],), 7.0, dtype=np.float64)

    scorer._score_raw_logp_win = types.MethodType(_raw_stub, scorer)

    out = RuneScorerTorch._score_batch_impl(
        scorer,
        np.zeros((3, 16), dtype=np.uint8),
        None,
    )
    np.testing.assert_allclose(out, np.asarray([7.0, 7.0, 7.0], dtype=np.float64))


def test_score_batch_impl_rejects_avg_non_logp() -> None:
    scorer = _make_fake_scorer_with_objective(
        ObjectiveSpec(family=ObjectiveFamily.AVG, stat=Stat.ZSUM, win=20)
    )
    with pytest.raises(ValueError, match="avg\\.logp"):
        RuneScorerTorch._score_batch_impl(
            scorer,
            np.zeros((1, 8), dtype=np.uint8),
            None,
        )


def test_score_batch_impl_rejects_pct_non_logp_before_backend_work() -> None:
    scorer = _make_fake_scorer_with_objective(
        ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.ZSUM, win=10)
    )
    with pytest.raises(ValueError, match="pct\\.logp|energy\\.logp"):
        RuneScorerTorch._score_batch_impl(
            scorer,
            np.zeros((1, 8), dtype=np.uint8),
            None,
        )


def test_score_batch_impl_routes_energy_logp_to_pct_path() -> None:
    scorer = _make_fake_scorer_with_objective(
        ObjectiveSpec(family=ObjectiveFamily.ENERGY, stat=Stat.LOGP, win=10)
    )

    def _pct_stub(self, pt_b: np.ndarray, wli_b):  # noqa: ARG001
        return np.full((pt_b.shape[0],), 0.25, dtype=np.float64)

    scorer._score_pct_logp_win = types.MethodType(_pct_stub, scorer)

    out = RuneScorerTorch._score_batch_impl(
        scorer,
        np.zeros((2, 8), dtype=np.uint8),
        None,
    )
    np.testing.assert_allclose(out, np.asarray([0.25, 0.25], dtype=np.float64))


def test_torch_ctor_rejects_pct_energy_non_win10() -> None:
    cfg_cipher = {"device": "cpu"}

    with pytest.raises(ValueError, match="win=10"):
        RuneScorerTorch(
            cfg_cipher,
            {"objective": ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=12)},
        )

    with pytest.raises(ValueError, match="win=10"):
        RuneScorerTorch(
            cfg_cipher,
            {"objective": ObjectiveSpec(family=ObjectiveFamily.ENERGY, stat=Stat.LOGP, win=12)},
        )
