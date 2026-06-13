from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pytest

from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.types import Direction, ObjectiveFamily, ObjectiveSpec, Stat
from rune_decrypter_prime.scoring import rune_scorer
from rune_decrypter_prime.scoring.span_hamming.calibrated_assets import SpanCalibratedAssets


pytestmark = pytest.mark.tier_a


def _make_torch_scorer():
    module = pytest.importorskip(
        "rune_decrypter_prime.scoring.torch_rune_scorer",
        reason="Torch backend required for Torch span-hamming tests",
    )
    return object.__new__(module.RuneScorerTorch)


class _StubECDF:
    def validate_clamp_range(self, **_kwargs):
        return None

    def load(self, **_kwargs):
        grid = np.array([0.0, 1.0], dtype=np.float64)
        q = np.array([0.0, 1.0], dtype=np.float64)
        return grid, q

    def interp_percentile(self, grid, q, x):
        x_arr = np.asarray(x, dtype=np.float64)
        return np.full_like(x_arr, 0.8, dtype=np.float64)

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


def _stub_ensure_ecdf(_self):
    return _StubECDF()


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


def _write_span_assets(root: Path, *, length_bucket: int = 3) -> Path:
    assets = root / "span_assets"
    ecdf_dir = assets / "ecdf" / "span_x"
    ecdf_dir.mkdir(parents=True, exist_ok=True)
    cal = {
        "version": "v1",
        "rows": [
            {
                "direction": "ltr",
                "length_bucket": int(length_bucket),
                "span_neg_ref": 0.2,
                "span_denom": 0.5,
                "span_valid": True,
                "char4_neg_ref": -11.0,
                "char4_denom": 1.0,
                "char4_valid": True,
            }
        ],
    }
    (assets / "combined_calibration.json").write_text(json.dumps(cal), encoding="utf-8")
    meta = {
        "model": "span",
        "stat": "x_span",
        "direction": "ltr",
        "length_bucket": int(length_bucket),
    }
    np.savez(
        ecdf_dir / f"ltr_nose_span_lb{int(length_bucket)}_fulltext_x_span.npz",
        grid=np.asarray([0.0, 1.0], dtype=np.float64),
        q=np.asarray([0.1, 0.9], dtype=np.float64),
        meta_json=np.array(json.dumps(meta), dtype=np.str_),
    )
    return assets


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
    scorer = _make_torch_scorer()
    scorer._span_hamming_mode = "raw_bonus"
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


def test_torch_calibrated_span_batch_pct_mode(tmp_path: Path):
    assets_dir = _write_span_assets(tmp_path, length_bucket=3)
    scorer = _make_torch_scorer()
    scorer.objective = ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10)
    scorer.direction = Direction.LTR
    scorer._score_dtype = np.float64
    scorer._span_hamming_backend = _DummySpanBackend(raw=0.45, coverage=0.6, quality=0.7)
    scorer._span_hamming_assets = SpanCalibratedAssets.load(assets_dir)
    scorer._span_hamming_ecdf_clamp_min = 1e-6
    scorer._span_hamming_ecdf_clamp_max = 1.0 - 1e-6
    scorer._span_hamming_coverage_min = 0.0
    scorer._span_hamming_quality_min = 0.0
    scorer._span_hamming_span_pct_min = None
    scorer._span_hamming_char_pct_min = None
    scorer._span_hamming_combine_mode = "min"
    scorer._span_hamming_weight_span = 1.0
    scorer._span_hamming_weight_char = 0.0
    scorer._span_hamming_use_char_channel = False
    scorer._span_hamming_gate_fail_policy = "score_floor"
    scorer._span_hamming_gate_score_floor = 0.123
    scorer._last_stats = {}
    scorer._telemetry = {}

    out = scorer._score_span_hamming_calibrated_batch(
        np.asarray([[1, 2, 3]], dtype=np.uint8),
        None,
    )
    assert out.tolist() == pytest.approx([0.5], rel=0, abs=1e-12)
    stats = scorer.last_stats()
    assert float(stats["span_hamming_pct"]) == pytest.approx(0.5, abs=1e-12)
    assert float(stats["span_hamming_combined_pct"]) == pytest.approx(0.5, abs=1e-12)
    assert bool(stats["span_hamming_gate_failed"]) is False


def test_torch_calibrated_span_batch_weighted_sum_and_char_gate(tmp_path: Path):
    assets_dir = _write_span_assets(tmp_path, length_bucket=3)
    scorer = _make_torch_scorer()
    scorer.objective = ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10)
    scorer.direction = Direction.LTR
    scorer._score_dtype = np.float64
    scorer._span_hamming_backend = _DummySpanBackend(raw=0.45, coverage=0.6, quality=0.7)
    scorer._span_hamming_assets = SpanCalibratedAssets.load(assets_dir)
    scorer._span_hamming_ecdf_clamp_min = 1e-6
    scorer._span_hamming_ecdf_clamp_max = 1.0 - 1e-6
    scorer._span_hamming_coverage_min = 0.0
    scorer._span_hamming_quality_min = 0.0
    scorer._span_hamming_span_pct_min = None
    scorer._span_hamming_char_pct_min = None
    scorer._span_hamming_combine_mode = "weighted_sum"
    scorer._span_hamming_weight_span = 1.0
    scorer._span_hamming_weight_char = 3.0
    scorer._span_hamming_use_char_channel = True
    scorer._span_hamming_gate_fail_policy = "score_floor"
    scorer._span_hamming_gate_score_floor = 0.222
    scorer._last_stats = {}
    scorer._telemetry = {}

    def _base_pct_stub(_pt_b, _wli_b):
        return np.asarray([0.8], dtype=np.float64), np.asarray([0.8], dtype=np.float64)

    scorer._score_base_channel_pct_batch = _base_pct_stub

    out = scorer._score_span_hamming_calibrated_batch(
        np.asarray([list(range(20))], dtype=np.uint8),
        None,
    )
    assert out.tolist() == pytest.approx([0.725], rel=0, abs=1e-12)
    stats = scorer.last_stats()
    assert float(stats["span_hamming_combined_pct"]) == pytest.approx(0.725, abs=1e-12)
    assert bool(stats["span_hamming_gate_failed"]) is False

    scorer._span_hamming_char_pct_min = 0.9
    out_floor = scorer._score_span_hamming_calibrated_batch(
        np.asarray([list(range(20))], dtype=np.uint8),
        None,
    )
    assert out_floor.tolist() == pytest.approx([0.222], rel=0, abs=1e-12)
    stats_floor = scorer.last_stats()
    assert bool(stats_floor["span_hamming_gate_failed"]) is True
    assert "char_pct_below_min" in list(stats_floor["span_hamming_gate_reasons"])

    scorer._span_hamming_gate_fail_policy = "char_only"
    out_char_only = scorer._score_span_hamming_calibrated_batch(
        np.asarray([list(range(20))], dtype=np.uint8),
        None,
    )
    assert out_char_only.tolist() == pytest.approx([0.8], rel=0, abs=1e-12)
    stats_char_only = scorer.last_stats()
    assert bool(stats_char_only["span_hamming_gate_failed"]) is True
    assert bool(stats_char_only["span_hamming_span_skipped"]) is True
    assert str(stats_char_only["span_hamming_gate_fail_policy"]) == "char_only"


def test_numpy_rune_scorer_calibrated_span_pct_mode(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)
    assets_dir = _write_span_assets(tmp_path, length_bucket=3)
    cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        include_char=True,
        use_word_breaks=False,
        span_hamming_enabled=True,
        span_hamming_mode="calibrated",
        span_hamming_assets_dir=assets_dir,
        span_hamming_coverage_min=0.0,
        span_hamming_quality_min=0.0,
        encoding_dir=Direction.LTR,
    )
    fake_cipher = type("C", (), {"device": "cpu"})
    scorer = rune_scorer.RuneScorer(fake_cipher, cfg)
    scorer._span_hamming_backend = _DummySpanBackend(raw=0.45, coverage=0.6, quality=0.7)

    out = scorer.score([1, 2, 3], None)
    # x=(0.45-0.2)/0.5=0.5 => pct=0.5 from linear ECDF [0.1..0.9]
    assert out == pytest.approx(0.5, rel=0, abs=1e-12)
    stats = scorer.last_stats()
    assert float(stats["span_hamming_x"]) == pytest.approx(0.5, abs=1e-12)
    assert float(stats["span_hamming_pct"]) == pytest.approx(0.5, abs=1e-12)
    assert bool(stats["span_hamming_gate_failed"]) is False


def test_numpy_rune_scorer_calibrated_span_gate_floor(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)
    assets_dir = _write_span_assets(tmp_path, length_bucket=3)
    cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        include_char=True,
        use_word_breaks=False,
        span_hamming_enabled=True,
        span_hamming_mode="calibrated",
        span_hamming_assets_dir=assets_dir,
        span_hamming_coverage_min=0.9,
        span_hamming_gate_score_floor=0.123,
        encoding_dir=Direction.LTR,
    )
    fake_cipher = type("C", (), {"device": "cpu"})
    scorer = rune_scorer.RuneScorer(fake_cipher, cfg)
    scorer._span_hamming_backend = _DummySpanBackend(raw=0.45, coverage=0.6, quality=0.7)

    out = scorer.score([1, 2, 3], None)
    assert out == pytest.approx(0.123, rel=0, abs=1e-12)
    assert bool(scorer.last_stats()["span_hamming_gate_failed"]) is True


def test_numpy_rune_scorer_calibrated_min_combine_with_char_pct(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)
    monkeypatch.setattr(rune_scorer.RuneScorer, "_ensure_ecdf", _stub_ensure_ecdf)
    assets_dir = _write_span_assets(tmp_path, length_bucket=3)
    cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        span_hamming_enabled=True,
        span_hamming_mode="calibrated",
        span_hamming_assets_dir=assets_dir,
        span_hamming_combine_mode="min",
        span_hamming_weight_char=1.0,
        span_hamming_coverage_min=0.0,
        span_hamming_quality_min=0.0,
        encoding_dir=Direction.LTR,
    )
    fake_cipher = type("C", (), {"device": "cpu"})
    scorer = rune_scorer.RuneScorer(fake_cipher, cfg)
    scorer._span_hamming_backend = _DummySpanBackend(raw=0.45, coverage=0.6, quality=0.7)

    out = scorer.score(list(range(20)), None)
    # span_pct=0.5, char_pct=0.8 => min=0.5
    assert out == pytest.approx(0.5, rel=0, abs=1e-12)
    stats = scorer.last_stats()
    assert float(stats["span_hamming_pct"]) == pytest.approx(0.5, abs=1e-12)
    assert float(stats["span_hamming_char_pct"]) == pytest.approx(0.8, abs=1e-12)
    assert float(stats["span_hamming_combined_pct"]) == pytest.approx(0.5, abs=1e-12)


def test_numpy_rune_scorer_calibrated_weighted_sum_combine_with_char_pct(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)
    monkeypatch.setattr(rune_scorer.RuneScorer, "_ensure_ecdf", _stub_ensure_ecdf)
    assets_dir = _write_span_assets(tmp_path, length_bucket=3)
    cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        span_hamming_enabled=True,
        span_hamming_mode="calibrated",
        span_hamming_assets_dir=assets_dir,
        span_hamming_combine_mode="weighted_sum",
        span_hamming_weight_span=1.0,
        span_hamming_weight_char=3.0,
        span_hamming_coverage_min=0.0,
        span_hamming_quality_min=0.0,
        encoding_dir=Direction.LTR,
    )
    fake_cipher = type("C", (), {"device": "cpu"})
    scorer = rune_scorer.RuneScorer(fake_cipher, cfg)
    scorer._span_hamming_backend = _DummySpanBackend(raw=0.45, coverage=0.6, quality=0.7)

    out = scorer.score(list(range(20)), None)
    # span_pct=0.5, char_pct=0.8 => (1*0.5 + 3*0.8)/4 = 0.725
    assert out == pytest.approx(0.725, rel=0, abs=1e-12)
    stats = scorer.last_stats()
    assert float(stats["span_hamming_combined_pct"]) == pytest.approx(0.725, abs=1e-12)


def test_numpy_rune_scorer_calibrated_char_gate_floor(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)
    monkeypatch.setattr(rune_scorer.RuneScorer, "_ensure_ecdf", _stub_ensure_ecdf)
    assets_dir = _write_span_assets(tmp_path, length_bucket=3)
    cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        span_hamming_enabled=True,
        span_hamming_mode="calibrated",
        span_hamming_assets_dir=assets_dir,
        span_hamming_combine_mode="min",
        span_hamming_weight_char=1.0,
        span_hamming_char_pct_min=0.9,
        span_hamming_gate_score_floor=0.222,
        span_hamming_coverage_min=0.0,
        span_hamming_quality_min=0.0,
        encoding_dir=Direction.LTR,
    )
    fake_cipher = type("C", (), {"device": "cpu"})
    scorer = rune_scorer.RuneScorer(fake_cipher, cfg)
    scorer._span_hamming_backend = _DummySpanBackend(raw=0.45, coverage=0.6, quality=0.7)

    out = scorer.score(list(range(20)), None)
    assert out == pytest.approx(0.222, rel=0, abs=1e-12)
    stats = scorer.last_stats()
    assert bool(stats["span_hamming_gate_failed"]) is True
    assert "char_pct_below_min" in list(stats["span_hamming_gate_reasons"])


def test_numpy_rune_scorer_calibrated_char_gate_char_only_fallback(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)
    monkeypatch.setattr(rune_scorer.RuneScorer, "_ensure_ecdf", _stub_ensure_ecdf)
    assets_dir = _write_span_assets(tmp_path, length_bucket=3)
    cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        span_hamming_enabled=True,
        span_hamming_mode="calibrated",
        span_hamming_assets_dir=assets_dir,
        span_hamming_combine_mode="min",
        span_hamming_weight_char=1.0,
        span_hamming_char_pct_min=0.9,
        span_hamming_gate_fail_policy="char_only",
        span_hamming_gate_score_floor=0.222,
        span_hamming_coverage_min=0.0,
        span_hamming_quality_min=0.0,
        encoding_dir=Direction.LTR,
    )
    fake_cipher = type("C", (), {"device": "cpu"})
    scorer = rune_scorer.RuneScorer(fake_cipher, cfg)
    scorer._span_hamming_backend = _DummySpanBackend(raw=0.45, coverage=0.6, quality=0.7)

    out = scorer.score(list(range(20)), None)
    assert out == pytest.approx(0.8, rel=0, abs=1e-12)
    stats = scorer.last_stats()
    assert bool(stats["span_hamming_gate_failed"]) is True
    assert bool(stats["span_hamming_span_skipped"]) is True
    assert str(stats["span_hamming_gate_fail_policy"]) == "char_only"


def test_numpy_rune_scorer_calibrated_rejects_char_channel_when_not_char4_only(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)
    assets_dir = _write_span_assets(tmp_path, length_bucket=3)
    cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        include_char=True,
        use_word_breaks=False,
        char_weights={3: 1.0},
        span_hamming_enabled=True,
        span_hamming_mode="calibrated",
        span_hamming_assets_dir=assets_dir,
        span_hamming_weight_char=1.0,
        encoding_dir=Direction.LTR,
    )
    fake_cipher = type("C", (), {"device": "cpu"})
    with pytest.raises(ValueError, match="char4-only base scorer"):
        _ = rune_scorer.RuneScorer(fake_cipher, cfg)


def test_numpy_rune_scorer_calibrated_rejects_avg_objective(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)
    assets_dir = _write_span_assets(tmp_path, length_bucket=3)
    cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.AVG, stat=Stat.LOGP, win=10),
        include_char=True,
        use_word_breaks=False,
        span_hamming_enabled=True,
        span_hamming_mode="calibrated",
        span_hamming_assets_dir=assets_dir,
        encoding_dir=Direction.LTR,
    )
    fake_cipher = type("C", (), {"device": "cpu"})
    with pytest.raises(ValueError, match="only supports ObjectiveFamily.PCT or ENERGY"):
        _ = rune_scorer.RuneScorer(fake_cipher, cfg)
