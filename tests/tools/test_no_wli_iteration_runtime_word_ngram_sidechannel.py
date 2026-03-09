from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from rune_decrypter_prime.api import Direction
from tools.benchmarks.periodic_sub_trans.no_wli import iteration_runtime as runtime_mod


pytestmark = pytest.mark.tier_a


class _FakeKeyOps:
    def __init__(self, *, K: int, period: int, A: int, columns: int) -> None:
        _ = (period, A, columns)
        self._k = int(K)

    def random(self, rng: np.random.Generator) -> np.ndarray:
        _ = rng
        return np.zeros(self._k, dtype=np.int16)


class _FakeFullCipher:
    def __init__(self, cfg) -> None:
        _ = cfg

    def encrypt_single(self, *, plaintext: np.ndarray, key: np.ndarray) -> np.ndarray:
        _ = key
        return np.asarray(plaintext, dtype=np.uint8).reshape(-1)


class _FakeSubCipher:
    def __init__(self, cfg) -> None:
        _ = cfg

    def decrypt_single(self, *, ciphertext: np.ndarray, key: np.ndarray) -> np.ndarray:
        _ = key
        return np.asarray(ciphertext, dtype=np.uint8).reshape(-1)


def test_word_ngram_report_cfg_uses_span_capable_basin_judge_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_mod, "PeriodicStructuredMatrixKeyOps", _FakeKeyOps)
    monkeypatch.setattr(runtime_mod, "PeriodicColumnarCipher", _FakeFullCipher)
    monkeypatch.setattr(runtime_mod, "PeriodicSubstitutionCipher", _FakeSubCipher)
    monkeypatch.setattr(runtime_mod, "build_scorer", lambda *args, **kwargs: object())

    captured: dict[str, object] = {}

    def _build_word_ngram_report_cfg_fn(*, base_cfg, direction):
        captured["base_cfg"] = dict(base_cfg)
        captured["direction"] = direction
        return None

    runtime_mod.build_iteration_runtime(
        tier_period=1,
        tier_columns=1,
        pt_idx=np.asarray([1, 2, 3], dtype=np.uint8),
        key_seed=7,
        alphabet_size=2,
        order="row",
        direction=Direction.LTR,
        scorer_stage1_base=dict(
            objective="pct.logp.win10",
            include_char=True,
            use_word_breaks=False,
            char_weights={4: 1.0},
            wli_weights={},
            impl="numpy",
        ),
        scorer_stage2_base=dict(
            objective="avg.logp.win20",
            include_char=True,
            use_word_breaks=False,
            char_weights={4: 1.0},
            wli_weights={},
            impl="numpy",
        ),
        scorer_impl="numpy",
        pipeline_run_mode="fixed_seed",
        stage3_two_phase_enabled=False,
        scoring_experiment_profile="c_min_late",
        span_assets_dir=Path("assets/scoring/span_hamming_nose_assets_v1"),
        stage2_judge_policy_value="search_only",
        stage2_exact_max_columns=1,
        stage2_exact_two_pass=False,
        stage2_pass1_primary_char_weights={4: 1.0},
        stage2_pass1_fallback_char_weights={},
        canonical_run_mode_fn=lambda mode: str(mode or "fixed_seed"),
        is_adaptive_focus_mode_fn=lambda mode: str(mode or "") == "adaptive_focus_v1_p7c3_only",
        stage3_search_cfg_fn=lambda *, direction: dict(
            objective="avg.logp.win20",
            include_char=True,
            use_word_breaks=False,
            char_weights={4: 1.0},
            wli_weights={},
            impl="numpy",
            encoding_dir=direction,
        ),
        build_stage3_experiment_cfg_fn=lambda **kwargs: dict(
            objective="avg.logp.win20",
            include_char=True,
            use_word_breaks=False,
            char_weights={4: 1.0},
            wli_weights={},
            impl="numpy",
            encoding_dir=kwargs["direction"],
            span_hamming_enabled=True,
            span_hamming_mode="calibrated",
        ),
        build_word_ngram_report_cfg_fn=_build_word_ngram_report_cfg_fn,
        guard_no_ecdf_usage_fn=lambda **_: None,
    )

    base_cfg = dict(captured.get("base_cfg", {}))
    assert bool(base_cfg.get("span_hamming_enabled", False)) is True
    assert str(base_cfg.get("span_hamming_mode", "")) == "calibrated"
