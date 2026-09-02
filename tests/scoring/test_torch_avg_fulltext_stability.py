from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rdp.core.types import (
    Direction,
)
from rune_decrypter_prime.scoring.rune_scorer import RuneScorer
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
torch_scorer_module = pytest.importorskip('rune_decrypter_prime.scoring.torch_rune_scorer', reason='Torch backend required for Torch scorer tests')
RuneScorerTorch = torch_scorer_module.RuneScorerTorch
pytestmark = pytest.mark.tier_a

def _cipher_cfg(length: int) -> CipherConfig:
    return CipherConfig(ciphertext=[0] * int(length), wli_data=[], key_length=None, encoding_dir=Direction.LTR)

def _avg_fulltext_cfg(*, backend: api.advanced.ScorerBackend) -> api.ScoringConfig:
    return api.ScoringConfig(objective=api.advanced.ScoringObjective.average_log_probability(), character_lane_enabled=True, word_length_lane_enabled=False, character_order_weights={3: 0.2, 4: 0.8}, word_length_order_weights={}, average_window_policy=api.advanced.AverageWindowPolicy.FULL_TEXT, backend=backend, compute_dtype=api.advanced.FloatDType.FLOAT32)

@pytest.mark.full_assets
@pytest.mark.parametrize('length', [4, 40, 96, 240])
def test_torch_avg_fulltext_matches_numpy_across_lengths(length: int) -> None:
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(3, 4), ecdf_stats=())
    c_cfg = _cipher_cfg(length)
    scorer_np = build_scorer(c_cfg, _avg_fulltext_cfg(backend=api.advanced.ScorerBackend.NUMPY))
    scorer_torch = build_scorer(c_cfg, _avg_fulltext_cfg(backend=api.advanced.ScorerBackend.TORCH))
    assert isinstance(scorer_np, RuneScorer)
    assert isinstance(scorer_torch, RuneScorerTorch)
    rng = np.random.default_rng(20260225 + int(length))
    pts = [rng.integers(0, 29, size=length, dtype=np.uint8) for _ in range(8)]
    s_np = np.asarray(scorer_np.batch_score(pts), dtype=np.float64)
    s_t = np.asarray(scorer_torch.batch_score(pts), dtype=np.float64)
    np.testing.assert_allclose(s_t, s_np, rtol=0.0001, atol=1e-05)

@pytest.mark.full_assets
def test_torch_avg_fulltext_is_repeatable_and_reports_lookup_diagnostics() -> None:
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(3, 4), ecdf_stats=())
    length = 452
    scorer_torch = build_scorer(_cipher_cfg(length), _avg_fulltext_cfg(backend=api.advanced.ScorerBackend.TORCH))
    assert isinstance(scorer_torch, RuneScorerTorch)
    rng = np.random.default_rng(2026022501)
    pt = rng.integers(0, 29, size=length, dtype=np.uint8)
    vals = [float(scorer_torch.score(pt, None)) for _ in range(5)]
    np.testing.assert_allclose(np.asarray(vals, dtype=np.float64), np.full((5,), vals[0], dtype=np.float64), rtol=0.0, atol=1e-12)
    stats = scorer_torch.last_stats()
    assert stats.get('window.win_effective') == 'full_text'
    assert stats.get('avg_window_policy') == 'full_text'
    assert 'lut.fallback_hits_total' in stats
    assert 'lut.probe_exhausted' in stats
    assert 'lut.probe_exhausted_models' in stats
    assert stats.get('lut.max_probes') == 1024
