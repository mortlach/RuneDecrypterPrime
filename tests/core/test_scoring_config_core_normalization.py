from __future__ import annotations

import pytest

from rune_decrypter_prime.core.config.scoring import (
    HammingDirectionMode,
    ScoringConfig,
    SpanHammingCombineMode,
    SpanHammingGateFailPolicy,
    SpanHammingLmProfileSource,
    SpanHammingMode,
)
from rune_decrypter_prime.core.types import Direction, FloatDType, ScorerImpl


def test_scoring_config_normalises_api_strings_to_core_enums() -> None:
    cfg = ScoringConfig(
        encoding_dir="rtl",
        impl="torch",
        dtype="float32",
        compute_dtype="float32",
        acc_dtype="float64",
        hamming_direction_mode="both",
        span_hamming_mode="calibrated",
        span_hamming_combine_mode="weighted_sum",
        span_hamming_gate_fail_policy="char_only",
        span_hamming_lm_profile_source="chars_covered_by_len",
    )

    assert cfg.encoding_dir is Direction.RTL
    assert cfg.impl is ScorerImpl.TORCH
    assert cfg.dtype is FloatDType.FLOAT32
    assert cfg.compute_dtype is FloatDType.FLOAT32
    assert cfg.acc_dtype is FloatDType.FLOAT64
    assert cfg.hamming_direction_mode is HammingDirectionMode.BOTH
    assert cfg.span_hamming_mode is SpanHammingMode.CALIBRATED
    assert cfg.span_hamming_combine_mode is SpanHammingCombineMode.WEIGHTED_SUM
    assert cfg.span_hamming_gate_fail_policy is SpanHammingGateFailPolicy.CHAR_ONLY
    assert cfg.span_hamming_lm_profile_source is SpanHammingLmProfileSource.CHARS_COVERED_BY_LEN


def test_scoring_config_rejects_unknown_core_enum_label() -> None:
    with pytest.raises(ValueError, match="span_hamming_combine_mode"):
        ScoringConfig(span_hamming_combine_mode="quietly_guess")
