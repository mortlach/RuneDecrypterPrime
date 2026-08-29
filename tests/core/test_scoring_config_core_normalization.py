from __future__ import annotations
from rdp import api
import pytest
from rune_decrypter_prime.core.config.scoring import HammingDirectionMode, ScoringConfig, SpanHammingCombineMode, SpanHammingGateFailPolicy, SpanHammingLmProfileSource, SpanHammingMode
from rune_decrypter_prime.core.types import Direction, FloatDType, ScorerImpl

def test_scoring_config_normalises_api_strings_to_core_enums() -> None:
    cfg = api.ScoringConfig(backend=api.advanced.ScorerBackend.TORCH, compute_dtype=api.advanced.FloatDType.FLOAT32, accumulator_dtype=api.advanced.FloatDType.FLOAT64, hamming_text_direction_mode=api.advanced.HammingTextDirectionMode.BOTH, span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED, span_hamming_combine_mode=api.advanced.SpanHammingCombineMode.WEIGHTED_SUM, span_hamming_gate_failure_policy=api.advanced.SpanHammingGateFailurePolicy.CHARACTER_ONLY, span_hamming_language_model_profile_source=api.advanced.SpanHammingLanguageModelProfileSource.CHARACTERS_COVERED_BY_LENGTH)
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
    with pytest.raises(ValueError, match='not a valid'):
        api.advanced.SpanHammingCombineMode('quietly_guess')
