from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import (
    Device,
    Direction,
    ObjectiveFamily,
    ObjectiveSpec,
    ScorerImpl,
    SeMode,
    Stat,
)
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets


pytestmark = pytest.mark.tier_a


class _StubLmRuntime:
    def __init__(self, *_, **__):
        pass

    def _score_batch_char(self, _dir, _se, _n, pt_windows):
        arr = np.asarray(pt_windows, dtype=np.float64)
        vals = np.mean(arr, axis=1, dtype=np.float64).astype(np.float32, copy=False)
        return vals, vals, vals

    def _score_batch_wli(self, _dir, _se, _n, pt_windows, _wli_windows):
        arr = np.asarray(pt_windows, dtype=np.float64)
        vals = np.mean(arr, axis=1, dtype=np.float64).astype(np.float32, copy=False)
        return vals, vals, vals


def _cipher_cfg(length: int = 48, *, device: Device = Device.CPU):
    return CipherConfig(
        ciphertext=[0] * int(length),
        wli_data=[],
        key_length=None,
        device=device,
        encoding_dir=Direction.LTR,
    ).asdict()


def _avg_cfg(*, impl: ScorerImpl, n_char: int = 1, win: int = 10):
    return ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.AVG, stat=Stat.LOGP, win=int(win)),
        se_mode=SeMode.NOSE,
        encoding_dir=Direction.LTR,
        include_char=True,
        use_word_breaks=False,
        char_weights={int(n_char): 1.0},
        wli_weights={},
        avg_window_policy="full_text",
        impl=impl,
        dtype="float32",
    ).asdict()


def test_numpy_avg_works_when_ecdf_constructor_would_fail(monkeypatch) -> None:
    from rune_decrypter_prime.scoring import rune_scorer as rs

    class _FailECDF:
        def __init__(self, *args, **kwargs):
            raise AssertionError("ECDFCache must not be constructed for AVG objective")

    monkeypatch.setattr(rs, "LmPrimeRuntime", _StubLmRuntime)
    monkeypatch.setattr(rs, "ECDFCache", _FailECDF)

    scorer = rs.RuneScorer(_cipher_cfg(length=24), _avg_cfg(impl=ScorerImpl.NUMPY, n_char=1, win=6))
    score = float(scorer.score(np.arange(24, dtype=np.uint8), None))
    assert np.isfinite(score)


def test_numpy_avg_does_not_call_ecdf_path(monkeypatch) -> None:
    from rune_decrypter_prime.scoring import rune_scorer as rs

    monkeypatch.setattr(rs, "LmPrimeRuntime", _StubLmRuntime)

    scorer = rs.RuneScorer(_cipher_cfg(length=24), _avg_cfg(impl=ScorerImpl.NUMPY, n_char=1, win=6))

    def _bomb(_self):
        raise AssertionError("_ensure_ecdf must not run for AVG objective")

    monkeypatch.setattr(rs.RuneScorer, "_ensure_ecdf", _bomb)
    score = float(scorer.score(np.arange(24, dtype=np.uint8), None))
    assert np.isfinite(score)


def test_torch_avg_does_not_construct_or_call_ecdf(monkeypatch) -> None:
    from rune_decrypter_prime.scoring import torch_rune_scorer as trs

    class _FailECDF:
        def __init__(self, *args, **kwargs):
            raise AssertionError("ECDFCache must not be constructed for AVG objective")

    def _raw_stub(self, pt_b: np.ndarray, _wli_b):
        pt = np.asarray(pt_b, dtype=np.float64)
        return np.mean(pt, axis=1, dtype=np.float64).astype(np.float64, copy=False)

    def _bomb(_self):
        raise AssertionError("_ensure_ecdf must not run for AVG objective")

    monkeypatch.setattr(trs, "ECDFCache", _FailECDF)
    monkeypatch.setattr(trs.RuneScorerTorch, "_score_raw_logp_win", _raw_stub)
    monkeypatch.setattr(trs.RuneScorerTorch, "_ensure_ecdf", _bomb)

    scorer = trs.RuneScorerTorch(_cipher_cfg(length=20), _avg_cfg(impl=ScorerImpl.TORCH, n_char=1, win=5))
    pts = (np.arange(40, dtype=np.uint8) % 29).reshape(2, 20)
    scores = np.asarray(scorer.batch_score(pts, None), dtype=np.float64)
    assert scores.shape == (2,)
    assert np.isfinite(scores).all()


def test_numpy_torch_avg_parity_without_ecdf_assets() -> None:
    pytest.importorskip("torch")
    require_full_lm_assets(
        models=("char",),
        modes=("ltr",),
        poses=("nose",),
        ns=(2,),
        ecdf_stats=(),
    )

    c_cfg = _cipher_cfg(length=64)
    s_cfg_np = _avg_cfg(impl=ScorerImpl.NUMPY, n_char=2, win=10)
    s_cfg_torch = _avg_cfg(impl=ScorerImpl.TORCH, n_char=2, win=10)

    scorer_np = build_scorer(c_cfg, s_cfg_np)
    scorer_torch = build_scorer(c_cfg, s_cfg_torch)

    rng = np.random.default_rng(20260222)
    pts = [rng.integers(0, 29, size=64, dtype=np.uint8) for _ in range(16)]
    scores_np = np.asarray(scorer_np.batch_score(pts), dtype=np.float64)
    scores_torch = np.asarray(scorer_torch.batch_score(pts), dtype=np.float64)

    assert np.allclose(scores_np, scores_torch, rtol=1e-4, atol=1e-5)


def test_avg_fulltext_mixed_order_ngram_counts() -> None:
    pytest.importorskip("torch")
    require_full_lm_assets(
        models=("char",),
        modes=("ltr",),
        poses=("nose",),
        ns=(3, 4),
        ecdf_stats=(),
    )

    length = 40
    cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.AVG, stat=Stat.LOGP, win=20),
        se_mode=SeMode.NOSE,
        encoding_dir=Direction.LTR,
        include_char=True,
        use_word_breaks=False,
        char_weights={3: 0.2, 4: 0.8},
        wli_weights={},
        avg_window_policy="full_text",
        impl=ScorerImpl.NUMPY,
        dtype="float32",
    ).asdict()
    scorer = build_scorer(_cipher_cfg(length=length), cfg)
    pt = np.arange(length, dtype=np.uint8) % 29
    _ = float(scorer.score(pt, None))
    stats = scorer.last_stats()
    by_model = dict(stats.get("stat.ngrams_total_by_model", {}))
    assert int(by_model.get("char_n3", -1)) == (length - 3 + 1)
    assert int(by_model.get("char_n4", -1)) == (length - 4 + 1)


def test_avg_fulltext_policy_visible_in_numpy_and_torch() -> None:
    pytest.importorskip("torch")
    require_full_lm_assets(
        models=("char",),
        modes=("ltr",),
        poses=("nose",),
        ns=(2,),
        ecdf_stats=(),
    )

    c_cfg = _cipher_cfg(length=32)
    cfg_np = _avg_cfg(impl=ScorerImpl.NUMPY, n_char=2, win=10)
    cfg_t = _avg_cfg(impl=ScorerImpl.TORCH, n_char=2, win=10)
    scorer_np = build_scorer(c_cfg, cfg_np)
    scorer_t = build_scorer(c_cfg, cfg_t)
    pt = np.arange(32, dtype=np.uint8) % 29
    _ = float(scorer_np.score(pt, None))
    _ = float(scorer_t.score(pt, None))
    assert scorer_np.telemetry().get("avg_window_policy") == "full_text"
    assert scorer_t.telemetry().get("avg_window_policy") == "full_text"
    assert scorer_np.telemetry().get("win_effective") == "full_text"
    assert scorer_t.telemetry().get("win_effective") == "full_text"
    assert scorer_np.last_stats().get("avg_window_policy") == "full_text"
    assert scorer_t.last_stats().get("avg_window_policy") == "full_text"
    assert scorer_np.last_stats().get("window.win_effective") == "full_text"
    assert scorer_t.last_stats().get("window.win_effective") == "full_text"


@pytest.mark.parametrize("family", [ObjectiveFamily.PCT, ObjectiveFamily.ENERGY])
def test_pct_energy_win10_lock_regression(family: ObjectiveFamily) -> None:
    with pytest.raises(ValueError, match="win=10"):
        ScoringConfig(
            objective=ObjectiveSpec(family=family, stat=Stat.LOGP, win=12),
            include_char=True,
            use_word_breaks=False,
            char_weights={2: 1.0},
            wli_weights={},
        )
