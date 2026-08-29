from __future__ import annotations
from rdp import api
import pytest
from rune_decrypter_prime.core.config.scoring import (
    HammingTextDirectionMode,
    SpanHammingCombineMode,
    SpanHammingGateFailurePolicy,
    SpanHammingLanguageModelProfileSource,
    SpanHammingMode,
)
from rune_decrypter_prime.core.types import FloatDType, ScorerBackend


def test_scoring_config_preserves_typed_public_enums() -> None:
    cfg = api.ScoringConfig(
        backend=api.advanced.ScorerBackend.TORCH,
        compute_dtype=api.advanced.FloatDType.FLOAT32,
        accumulator_dtype=api.advanced.FloatDType.FLOAT64,
        hamming_text_direction_mode=api.advanced.HammingTextDirectionMode.BOTH,
        span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED,
        span_hamming_combine_mode=api.advanced.SpanHammingCombineMode.WEIGHTED_SUM,
        span_hamming_gate_failure_policy=api.advanced.SpanHammingGateFailurePolicy.CHARACTER_ONLY,
        span_hamming_language_model_profile_source=api.advanced.SpanHammingLanguageModelProfileSource.CHARACTERS_COVERED_BY_LENGTH,
    )
    assert cfg.backend is ScorerBackend.TORCH
    assert cfg.compute_dtype is FloatDType.FLOAT32
    assert cfg.accumulator_dtype is FloatDType.FLOAT64
    assert cfg.hamming_text_direction_mode is HammingTextDirectionMode.BOTH
    assert cfg.span_hamming_mode is SpanHammingMode.CALIBRATED
    assert cfg.span_hamming_combine_mode is SpanHammingCombineMode.WEIGHTED_SUM
    assert (
        cfg.span_hamming_gate_failure_policy
        is SpanHammingGateFailurePolicy.CHARACTER_ONLY
    )
    assert (
        cfg.span_hamming_language_model_profile_source
        is SpanHammingLanguageModelProfileSource.CHARACTERS_COVERED_BY_LENGTH
    )


def test_scoring_config_rejects_unknown_core_enum_label() -> None:
    with pytest.raises(ValueError, match="not a valid"):
        api.advanced.SpanHammingCombineMode("quietly_guess")
