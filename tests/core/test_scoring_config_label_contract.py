from __future__ import annotations
from rdp import api
import pytest
from rune_decrypter_prime.core.component_contracts import ScorerLaneName
from rune_decrypter_prime.core.config.scoring import HammingDirectionMode, ScoringConfig, SpanHammingBucketPolicy, SpanHammingCombineMode, SpanHammingGateFailPolicy, SpanHammingLmProfileSource, SpanHammingMode, ensure_hamming_direction_mode, ensure_span_hamming_bucket_policy, ensure_span_hamming_combine_mode, ensure_span_hamming_gate_fail_policy, ensure_span_hamming_lm_profile_source, ensure_span_hamming_mode

def test_scoring_config_stores_d7_owned_modes_as_enums() -> None:
    cfg = api.ScoringConfig(hamming_text_direction_mode=api.advanced.HammingTextDirectionMode.BOTH, span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED, span_hamming_bucket_policy=api.advanced.SpanHammingBucketPolicy.NEAREST_SMALLER_ON_TIE, span_hamming_combine_mode=api.advanced.SpanHammingCombineMode.WEIGHTED_SUM, span_hamming_gate_failure_policy=api.advanced.SpanHammingGateFailurePolicy.CHARACTER_ONLY, span_hamming_language_model_profile_source=api.advanced.SpanHammingLanguageModelProfileSource.CHARACTERS_COVERED_BY_LENGTH)
    assert cfg.hamming_direction_mode is HammingDirectionMode.BOTH
    assert cfg.span_hamming_mode is SpanHammingMode.CALIBRATED
    assert cfg.span_hamming_bucket_policy is SpanHammingBucketPolicy.NEAREST_SMALLER_TIE
    assert cfg.span_hamming_combine_mode is SpanHammingCombineMode.WEIGHTED_SUM
    assert cfg.span_hamming_gate_fail_policy is SpanHammingGateFailPolicy.CHAR_ONLY
    assert cfg.span_hamming_lm_profile_source is SpanHammingLmProfileSource.CHARS_COVERED_BY_LEN

def test_exported_scoring_mode_normalisers_preserve_enum_domains() -> None:
    assert ensure_hamming_direction_mode('both') is HammingDirectionMode.BOTH
    assert ensure_span_hamming_mode('raw_bonus') is SpanHammingMode.RAW_BONUS
    assert ensure_span_hamming_bucket_policy('nearest_smaller_tie') is SpanHammingBucketPolicy.NEAREST_SMALLER_TIE
    assert ensure_span_hamming_combine_mode('weighted_sum') is SpanHammingCombineMode.WEIGHTED_SUM
    assert ensure_span_hamming_gate_fail_policy('char_only') is SpanHammingGateFailPolicy.CHAR_ONLY
    assert ensure_span_hamming_lm_profile_source('chars_covered_by_len') is SpanHammingLmProfileSource.CHARS_COVERED_BY_LEN
    assert ensure_span_hamming_mode(SpanHammingMode.CALIBRATED) is SpanHammingMode.CALIBRATED

def test_scoring_config_asdict_preserves_public_strings() -> None:
    cfg = api.ScoringConfig(hamming_text_direction_mode=api.advanced.HammingTextDirectionMode(HammingDirectionMode.BOTH), span_hamming_mode=api.advanced.SpanHammingMode(SpanHammingMode.CALIBRATED), span_hamming_bucket_policy=api.advanced.SpanHammingBucketPolicy(SpanHammingBucketPolicy.NEAREST_SMALLER_TIE), span_hamming_combine_mode=api.advanced.SpanHammingCombineMode(SpanHammingCombineMode.WEIGHTED_SUM), span_hamming_gate_failure_policy=api.advanced.SpanHammingGateFailurePolicy(SpanHammingGateFailPolicy.CHAR_ONLY), span_hamming_language_model_profile_source=api.advanced.SpanHammingLanguageModelProfileSource(SpanHammingLmProfileSource.CHARS_COVERED_BY_LEN))
    payload = cfg.asdict()
    assert payload['hamming_direction_mode'] == 'both'
    assert payload['span_hamming_mode'] == 'calibrated'
    assert payload['span_hamming_bucket_policy'] == 'nearest_smaller_tie'
    assert payload['span_hamming_combine_mode'] == 'weighted_sum'
    assert payload['span_hamming_gate_fail_policy'] == 'char_only'
    assert payload['span_hamming_lm_profile_source'] == 'chars_covered_by_len'

@pytest.mark.parametrize(('field_name', 'bad_value'), [('hamming_direction_mode', 'sideways'), ('span_hamming_mode', 'maybe'), ('span_hamming_bucket_policy', 'nearest_larger'), ('span_hamming_combine_mode', 'mean'), ('span_hamming_gate_fail_policy', 'ignore'), ('span_hamming_lm_profile_source', 'raw')])
def test_scoring_config_rejects_invalid_d7_owned_modes(field_name: str, bad_value: str) -> None:
    with pytest.raises(ValueError, match=field_name):
        api.ScoringConfig.from_dict({**{field_name: bad_value}})

def test_requested_scorer_lanes_uses_enum_backed_span_mode() -> None:
    raw_cfg = api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode(SpanHammingMode.RAW_BONUS))
    calibrated_cfg = api.ScoringConfig(span_hamming_mode=api.advanced.SpanHammingMode(SpanHammingMode.CALIBRATED), span_hamming_enabled=True, span_hamming_weight=0.5)
    assert raw_cfg.requested_scorer_lanes() == (ScorerLaneName.SPAN_HAMMING_RAW,)
    assert calibrated_cfg.requested_scorer_lanes() == (ScorerLaneName.SPAN_HAMMING_CALIBRATED,)
