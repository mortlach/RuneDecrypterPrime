from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.scoring import rune_scorer
from rune_decrypter_prime.scoring.torch_rune_scorer import RuneScorerTorch


pytestmark = pytest.mark.tier_a


class _StubECDF:
    def validate_clamp_range(self, **_kwargs):
        return None

    def load(self, **_kwargs):
        grid = np.array([0.0, 1.0], dtype=np.float64)
        q = np.array([0.0, 1.0], dtype=np.float64)
        return grid, q

    def interp_percentile(self, grid, q, x):
        return np.zeros_like(np.asarray(x, dtype=np.float64))

    @staticmethod
    def energy(p: np.ndarray) -> np.ndarray:
        p = np.asarray(p, dtype=np.float64)
        return (-np.log1p(-np.clip(p, 0.0, 1.0))).astype(np.float64, copy=False)

    def asset_id(self, **_kwargs):
        return "stub"

    def meta_hash(self, **_kwargs):
        return "stub"

    def interp_dtype(self, **_kwargs):
        return "float64"

    def meta(self, **_kwargs):
        return {}


class _StubRt:
    def __init__(self, *_, **__):
        self.ecdf = _StubECDF()

    def _score_batch_char(self, _dir, _se, _n, pt_windows):
        nwin = int(pt_windows.shape[0]) if hasattr(pt_windows, "shape") else len(pt_windows or [])
        zeros = np.zeros((nwin,), dtype=np.float64)
        return zeros, zeros, zeros

    def _score_batch_wli(self, _dir, _se, _n, pt_windows, _wli_windows):
        nwin = int(pt_windows.shape[0]) if hasattr(pt_windows, "shape") else len(pt_windows or [])
        zeros = np.zeros((nwin,), dtype=np.float64)
        return zeros, zeros, zeros


@dataclass(frozen=True)
class _DummySpanStats:
    span_raw: float
    coverage: float
    quality: float
    length_bins: tuple[int, ...] = (3, 4)
    span_raw_by_len: tuple[float, ...] = (0.1, 0.2)
    coverage_by_len: tuple[float, ...] = (0.1, 0.1)
    quality_by_len: tuple[float, ...] = (1.0, 2.0)


class _DummySpanBackend:
    def __init__(self, raw: float, coverage: float = 0.5, quality: float = 0.8):
        self._raw = float(raw)
        self._cov = float(coverage)
        self._q = float(quality)

    def score(self, _text_idx):
        return _DummySpanStats(
            span_raw=self._raw,
            coverage=self._cov,
            quality=self._q,
        )


def test_numpy_rune_scorer_applies_span_bonus(monkeypatch):
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)
    cfg = ScoringConfig(
        include_char=True,
        use_word_breaks=False,
        span_hamming_enabled=True,
        span_hamming_weight=0.5,
        encoding_dir=Direction.LTR,
    )
    fake_cipher = type("C", (), {"device": "cpu"})
    scorer = rune_scorer.RuneScorer(fake_cipher, cfg)
    scorer._span_hamming_backend = _DummySpanBackend(raw=0.4)
    scorer._span_hamming_weight = 0.5

    out = scorer.score([1, 2, 3], None)
    # pct short-text floor 1e-6 + span bonus (0.5 * 0.4)
    assert out == pytest.approx(0.200001, rel=0, abs=1e-9)
    stats = scorer.last_stats()
    assert float(stats["span_hamming_bonus"]) == pytest.approx(0.2)
    assert float(stats["stat.mean_per_ngram_penalized"]) == pytest.approx(0.2)


def test_torch_span_bonus_batch_adjusts_score_and_raw():
    scorer = object.__new__(RuneScorerTorch)
    scorer._span_hamming_backend = _DummySpanBackend(raw=0.2)
    scorer._span_hamming_weight = 1.5
    scorer._score_dtype = np.float64
    scorer._last_stats = {}
    scorer._telemetry = {}
    scorer._last_raw_batch = np.asarray([10.0, 20.0], dtype=np.float64)

    scores = np.asarray([1.0, 2.0], dtype=np.float64)
    pt_b = np.asarray([[1, 2, 3], [4, 5, 6]], dtype=np.uint8)
    out = scorer._apply_span_hamming_bonus_batch(scores, pt_b)

    # bonus = 1.5 * 0.2 = 0.3 per row
    assert np.allclose(out, np.asarray([1.3, 2.3], dtype=np.float64))
    assert np.allclose(scorer._last_raw_batch, np.asarray([10.3, 20.3], dtype=np.float64))
    assert scorer._last_stats["span_hamming_bonus_batch"] == pytest.approx([0.3, 0.3])

