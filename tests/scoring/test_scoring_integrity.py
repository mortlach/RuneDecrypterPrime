from __future__ import annotations
import numpy as np
import pytest
from rdp.core.engine.builders import build_scorer
from rdp.core.types import ScorerImpl
from rdp import api
from tests._helpers.configs import _mk_cfgs
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
pytestmark = pytest.mark.tier_a

def _make_char_only_scorer(*, impl: ScorerImpl, dtype: str):
    c_cfg, s_cfg = _mk_cfgs(
        device="cpu",
        encoding_dir="ltr",
        scorer_overrides={
            "backend": api.advanced.ScorerBackend(impl.value),
            "compute_dtype": api.advanced.FloatDType(dtype),
            "word_length_lane_enabled": False,
            "character_lane_enabled": True,
            "character_order_weights": {2: 1.0},
            "word_length_order_weights": {},
        },
    )
    return build_scorer(c_cfg, s_cfg)

def _make_candidates(L: int, n: int, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    return [rng.integers(0, 29, size=L, dtype=np.uint8) for _ in range(n)]

def _find_near_tie(scores: np.ndarray):
    if scores.size < 2:
        return None
    diff = np.abs(scores[:, None] - scores[None, :])
    np.fill_diagonal(diff, np.inf)
    idx = np.unravel_index(np.argmin(diff), diff.shape)
    if not np.isfinite(diff[idx]):
        return None
    i, j = (int(idx[0]), int(idx[1]))
    if i == j:
        return None
    return (i, j, float(diff[idx]))

def test_batch_vs_scalar_ordering_near_ties():
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(2,))
    scorer = _make_char_only_scorer(impl=ScorerImpl.NUMPY, dtype='float32')
    pts = _make_candidates(L=48, n=32, seed=1)
    scores_scalar = np.asarray([scorer.score(pt) for pt in pts], dtype=np.float64)
    pair = _find_near_tie(scores_scalar)
    if pair is None:
        pytest.skip('no near-tie pair found')
    i, j, _ = pair
    delta_scalar = float(scores_scalar[i] - scores_scalar[j])
    if delta_scalar == 0.0:
        pytest.skip('near-tie pair has zero delta')
    scores_batch = scorer.batch_score([pts[i], pts[j]])
    delta_batch = float(scores_batch[0] - scores_batch[1])
    assert np.sign(delta_scalar) == np.sign(delta_batch)

def test_score_precision_near_tie():
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(2,))
    scorer64 = _make_char_only_scorer(impl=ScorerImpl.NUMPY, dtype='float64')
    scorer32 = _make_char_only_scorer(impl=ScorerImpl.NUMPY, dtype='float32')
    pts = _make_candidates(L=48, n=32, seed=2)
    scores64 = np.asarray([scorer64.score(pt) for pt in pts], dtype=np.float64)
    pair = _find_near_tie(scores64)
    if pair is None:
        pytest.skip('no near-tie pair found')
    i, j, _ = pair
    delta64 = float(scores64[i] - scores64[j])
    if delta64 == 0.0:
        pytest.skip('near-tie pair has zero delta')
    scores32 = scorer32.batch_score([pts[i], pts[j]])
    delta32 = float(scores32[0] - scores32[1])
    assert np.sign(delta64) == np.sign(delta32)

def test_ecdf_dtype_knob_is_real():
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(2,))
    scorer = _make_char_only_scorer(impl=ScorerImpl.NUMPY, dtype='float64')
    ecdf_obj = getattr(scorer, '_ecdf', None)
    if ecdf_obj is None and hasattr(scorer, '_ensure_ecdf'):
        ecdf_obj = scorer._ensure_ecdf()
    prefer = getattr(ecdf_obj, '_prefer_float32', None)
    assert prefer is False

def test_numpy_vs_torch_ranking_parity_fixed_candidates():
    torch = pytest.importorskip('torch')
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(2,))
    scorer_np = _make_char_only_scorer(impl=ScorerImpl.NUMPY, dtype='float32')
    scorer_torch = _make_char_only_scorer(impl=ScorerImpl.TORCH, dtype='float32')
    pts = _make_candidates(L=48, n=24, seed=3)
    scores_np = np.asarray(scorer_np.batch_score(pts), dtype=np.float64)
    scores_t = np.asarray(scorer_torch.batch_score(pts), dtype=np.float64)
    eps = 1e-06
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if abs(scores_np[i] - scores_np[j]) > eps:
                assert (scores_np[i] < scores_np[j]) == (scores_t[i] < scores_t[j])
