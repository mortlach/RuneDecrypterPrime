# tests/scoring/test_scorer_pct_edges_and_clamps.py
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device, Direction, ObjectiveFamily, ObjectiveSpec, SeMode, Stat

from tests.scoring._helpers.lm_test_guard import require_full_lm_assets


def _mk_cipher_cfg(length: int) -> CipherConfig:
    ct = list(range(length))
    return CipherConfig(ciphertext=ct, wli_data=[], key_length=None, device=Device.CPU, encoding_dir=Direction.LTR)


def _mk_pct_scorer(*, ecdf_clamp_min: float | None = None, ecdf_clamp_max: float | None = None) -> object:
    # Keep requirements modest: char bigrams only.
    s = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        se_mode=SeMode.NOSE,
        encoding_dir=Direction.LTR,
        include_char=True,
        use_word_breaks=False,
        char_weights={2: 1.0},
        wli_weights={},
        dtype="float32",
        ecdf_clamp_min=ecdf_clamp_min if ecdf_clamp_min is not None else 1e-6,
        ecdf_clamp_max=ecdf_clamp_max if ecdf_clamp_max is not None else 1.0 - 1e-6,
    )

    return build_scorer(_mk_cipher_cfg(1000), s)


@pytest.mark.tier_a
def test_pct_short_text_returns_floor_and_reports_zero_windows() -> None:
    # Requires full LM (joint+ecdf for char2); skip cleanly if absent.
    require_full_lm_assets(models=("char",), modes=("ltr",), poses=("nose",), ns=(2,), ecdf_stats=("logp",))

    scorer = _mk_pct_scorer()
    short = np.arange(9, dtype=np.uint8)  # < win=10
    score = float(scorer.score(short, None))
    tel = scorer.telemetry()

    # This is the agreed "alias": if there are no windows, score_mean becomes ecdf_clamp_min.
    assert score == pytest.approx(1e-6, abs=0.0)
    assert tel["objective_stats"]["n_windows"] == 0
    assert tel["objective_stats"]["pct_logp_mean_per_ngram_total"] == pytest.approx(1e-6, abs=0.0)


@pytest.mark.tier_a
def test_pct_clamping_applies_floor_and_ceiling() -> None:
    require_full_lm_assets(models=("char",), modes=("ltr",), poses=("nose",), ns=(2,), ecdf_stats=("logp",))

    scorer = _mk_pct_scorer(ecdf_clamp_min=0.2, ecdf_clamp_max=0.8)
    x = np.arange(200, dtype=np.uint8) % 29
    _ = float(scorer.score(x, None))
    tel = scorer.telemetry()
    win = tel["objective_stats"]["windows"]

    # The stored window percentiles should respect the clamp.
    assert 0.2 <= win["p10"] <= 0.8
    assert 0.2 <= win["p50"] <= 0.8
    assert 0.2 <= win["p90"] <= 0.8

    # The final score_mean is also clamped.
    assert 0.2 <= tel["objective_stats"]["score_mean"] <= 0.8


@pytest.mark.tier_a
def test_pct_reports_both_raw_and_percentile_stats() -> None:
    require_full_lm_assets(models=("char",), modes=("ltr",), poses=("nose",), ns=(2,), ecdf_stats=("logp",))

    scorer = _mk_pct_scorer()
    x = np.arange(200, dtype=np.uint8) % 29
    _ = float(scorer.score(x, None))
    tel = scorer.telemetry()

    obj = tel["objective_stats"]

    # Terminology note:
    #   - logp_mean_per_ngram_total is the underlying log-probability statistic (units: log(p) per evaluated n-gram)
    #   - pct_logp_mean_per_ngram_total is the ECDF-normalised percentile in [0,1] used by the optimiser in PCT mode
    assert "logp_mean_per_ngram_total" in obj
    assert "pct_logp_mean_per_ngram_total" in obj
    assert obj["score_mean"] == obj["pct_logp_mean_per_ngram_total"]
