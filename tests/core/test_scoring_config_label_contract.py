from __future__ import annotations
from rdp import api
import pytest
from rdp.core.component_contracts import ScoringLane
from rune_decrypter_prime.core.config.scoring import (
    HammingTextDirectionMode,
    SpanHammingBucketPolicy,
    SpanHammingCombineMode,
    SpanHammingGateFailurePolicy,
    SpanHammingLanguageModelProfileSource,
    SpanHammingMode,
    ensure_hamming_text_direction_mode,
    ensure_span_hamming_bucket_policy,
    ensure_span_hamming_combine_mode,
    ensure_span_hamming_gate_failure_policy,
    ensure_span_hamming_language_model_profile_source,
    ensure_span_hamming_mode,
)


def test_scoring_config_stores_d7_owned_modes_as_enums() -> None:
    cfg = api.ScoringConfig(
        hamming_text_direction_mode=api.advanced.HammingTextDirectionMode.BOTH,
        span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED,
        span_hamming_bucket_policy=api.advanced.SpanHammingBucketPolicy.NEAREST_SMALLER_ON_TIE,
        span_hamming_combine_mode=api.advanced.SpanHammingCombineMode.WEIGHTED_SUM,
        span_hamming_gate_failure_policy=api.advanced.SpanHammingGateFailurePolicy.CHARACTER_ONLY,
        span_hamming_language_model_profile_source=api.advanced.SpanHammingLanguageModelProfileSource.CHARACTERS_COVERED_BY_LENGTH,
    )
    assert cfg.hamming_text_direction_mode is HammingTextDirectionMode.BOTH
    assert cfg.span_hamming_mode is SpanHammingMode.CALIBRATED
    assert (
        cfg.span_hamming_bucket_policy is SpanHammingBucketPolicy.NEAREST_SMALLER_ON_TIE
    )
    assert cfg.span_hamming_combine_mode is SpanHammingCombineMode.WEIGHTED_SUM
    assert (
        cfg.span_hamming_gate_failure_policy
        is SpanHammingGateFailurePolicy.CHARACTER_ONLY
    )
    assert (
        cfg.span_hamming_language_model_profile_source
        is SpanHammingLanguageModelProfileSource.CHARACTERS_COVERED_BY_LENGTH
    )


def test_exported_scoring_mode_normalisers_preserve_enum_domains() -> None:
    assert (
        ensure_hamming_text_direction_mode(HammingTextDirectionMode.BOTH)
        is HammingTextDirectionMode.BOTH
    )
    assert (
        ensure_span_hamming_mode(SpanHammingMode.RAW_BONUS) is SpanHammingMode.RAW_BONUS
    )
    assert (
        ensure_span_hamming_bucket_policy(
            SpanHammingBucketPolicy.NEAREST_SMALLER_ON_TIE
        )
        is SpanHammingBucketPolicy.NEAREST_SMALLER_ON_TIE
    )
    assert (
        ensure_span_hamming_combine_mode(SpanHammingCombineMode.WEIGHTED_SUM)
        is SpanHammingCombineMode.WEIGHTED_SUM
    )
    assert (
        ensure_span_hamming_gate_failure_policy(
            SpanHammingGateFailurePolicy.CHARACTER_ONLY
        )
        is SpanHammingGateFailurePolicy.CHARACTER_ONLY
    )
    assert (
        ensure_span_hamming_language_model_profile_source(
            SpanHammingLanguageModelProfileSource.CHARACTERS_COVERED_BY_LENGTH
        )
        is SpanHammingLanguageModelProfileSource.CHARACTERS_COVERED_BY_LENGTH
    )
    assert (
        ensure_span_hamming_mode(SpanHammingMode.CALIBRATED)
        is SpanHammingMode.CALIBRATED
    )


def test_scoring_config_asdict_preserves_public_strings() -> None:
    cfg = api.ScoringConfig(
        hamming_text_direction_mode=api.advanced.HammingTextDirectionMode(
            HammingTextDirectionMode.BOTH
        ),
        span_hamming_mode=api.advanced.SpanHammingMode(SpanHammingMode.CALIBRATED),
        span_hamming_bucket_policy=api.advanced.SpanHammingBucketPolicy(
            SpanHammingBucketPolicy.NEAREST_SMALLER_ON_TIE
        ),
        span_hamming_combine_mode=api.advanced.SpanHammingCombineMode(
            SpanHammingCombineMode.WEIGHTED_SUM
        ),
        span_hamming_gate_failure_policy=api.advanced.SpanHammingGateFailurePolicy(
            SpanHammingGateFailurePolicy.CHARACTER_ONLY
        ),
        span_hamming_language_model_profile_source=api.advanced.SpanHammingLanguageModelProfileSource(
            SpanHammingLanguageModelProfileSource.CHARACTERS_COVERED_BY_LENGTH
        ),
    )
    payload = cfg.asdict()
    assert payload["hamming_text_direction_mode"] == "both"
    assert payload["span_hamming_mode"] == "calibrated"
    assert payload["span_hamming_bucket_policy"] == "nearest_smaller_on_tie"
    assert payload["span_hamming_combine_mode"] == "weighted_sum"
    assert payload["span_hamming_gate_failure_policy"] == "character_only"
    assert (
        payload["span_hamming_language_model_profile_source"]
        == "characters_covered_by_length"
    )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("hamming_text_direction_mode", "sideways"),
        ("span_hamming_mode", "maybe"),
        ("span_hamming_bucket_policy", "nearest_larger"),
        ("span_hamming_combine_mode", "mean"),
        ("span_hamming_gate_failure_policy", "ignore"),
        ("span_hamming_language_model_profile_source", "raw"),
    ],
)
def test_scoring_config_rejects_invalid_d7_owned_modes(
    field_name: str, bad_value: str
) -> None:
    with pytest.raises(ValueError):
        api.ScoringConfig.from_dict({**{field_name: bad_value}})

def test_requested_scorer_lanes_uses_enum_backed_span_mode() -> None:
    raw_cfg = api.ScoringConfig(
        span_hamming_mode=api.advanced.SpanHammingMode(SpanHammingMode.RAW_BONUS)
    )
    calibrated_cfg = api.ScoringConfig(
        span_hamming_mode=api.advanced.SpanHammingMode(SpanHammingMode.CALIBRATED),
        span_hamming_enabled=True,
        span_hamming_weight=0.5,
    )
    assert raw_cfg.requested_scorer_lanes() == (ScoringLane.SPAN_HAMMING_RAW,)
    assert calibrated_cfg.requested_scorer_lanes() == (
        ScoringLane.SPAN_HAMMING_CALIBRATED,
    )
