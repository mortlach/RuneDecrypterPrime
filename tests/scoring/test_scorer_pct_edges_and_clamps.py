from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import (
    Device,
    Direction,
)
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets

def _mk_cipher_cfg(length: int) -> CipherConfig:
    ct = list(range(length))
    return CipherConfig(ciphertext=ct, wli_data=[], key_length=None, device=Device.CPU, encoding_dir=Direction.LTR)

def _mk_pct_scorer(*, ecdf_clamp_min: float | None=None, ecdf_clamp_max: float | None=None) -> object:
    s = api.ScoringConfig(objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10), character_lane_enabled=True, word_length_lane_enabled=False, character_order_weights={2: 1.0}, word_length_order_weights={}, compute_dtype=api.advanced.FloatDType.FLOAT32, ecdf_clamp_minimum=ecdf_clamp_min if ecdf_clamp_min is not None else 1e-06, ecdf_clamp_maximum=ecdf_clamp_max if ecdf_clamp_max is not None else 1.0 - 1e-06)
    return build_scorer(_mk_cipher_cfg(1000), s)

@pytest.mark.tier_a
def test_pct_short_text_returns_floor_and_reports_zero_windows() -> None:
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(2,), ecdf_stats=('logp',))
    scorer = _mk_pct_scorer()
    short = np.arange(9, dtype=np.uint8)
    score = float(scorer.score(short, None))
    tel = scorer.telemetry()
    assert score == pytest.approx(1e-06, abs=0.0)
    assert tel['objective_stats']['n_windows'] == 0
    assert tel['objective_stats']['pct_logp_mean_per_ngram_total'] == pytest.approx(1e-06, abs=0.0)

@pytest.mark.tier_a
def test_pct_clamping_applies_floor_and_ceiling() -> None:
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(2,), ecdf_stats=('logp',))
    scorer = _mk_pct_scorer(ecdf_clamp_min=0.2, ecdf_clamp_max=0.8)
    x = np.arange(200, dtype=np.uint8) % 29
    _ = float(scorer.score(x, None))
    tel = scorer.telemetry()
    win = tel['objective_stats']['windows']
    assert 0.2 <= win['p10'] <= 0.8
    assert 0.2 <= win['p50'] <= 0.8
    assert 0.2 <= win['p90'] <= 0.8
    assert 0.2 <= tel['objective_stats']['score_mean'] <= 0.8

@pytest.mark.tier_a
def test_pct_reports_both_raw_and_percentile_stats() -> None:
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(2,), ecdf_stats=('logp',))
    scorer = _mk_pct_scorer()
    x = np.arange(200, dtype=np.uint8) % 29
    _ = float(scorer.score(x, None))
    tel = scorer.telemetry()
    obj = tel['objective_stats']
    assert 'logp_mean_per_ngram_total' in obj
    assert 'pct_logp_mean_per_ngram_total' in obj
    assert obj['score_mean'] == obj['pct_logp_mean_per_ngram_total']
