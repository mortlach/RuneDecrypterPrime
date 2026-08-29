from __future__ import annotations
from rune_decrypter_prime.core.component_contracts import ScoringLane
from rune_decrypter_prime.scoring.base_scorer import BaseScorer


def test_scorer_lane_registry_values_are_stable() -> None:
    assert tuple((lane.value for lane in ScoringLane)) == (
        "language_model_character_and_word_length",
        "hamming",
        "span_hamming_raw",
        "span_hamming_calibrated",
        "word_ngram_judge_report_only",
        "ngram_hamming_experimental_report_only",
    )


def test_base_scorer_remains_the_single_public_scorer_interface() -> None:
    required_methods = {
        "score",
        "batch_score",
        "score_with_raw",
        "batch_score_with_raw",
        "supports_raw",
        "last_stats",
        "telemetry",
        "impl_name",
        "dtype_name",
        "device_name",
    }
    assert required_methods <= set(BaseScorer.__dict__)
    assert not hasattr(BaseScorer, "score_no_wli")
    assert not hasattr(BaseScorer, "batch_score_no_wli")


def test_report_only_ngram_lane_is_not_production_lane_name() -> None:
    assert ScoringLane.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY.value.endswith(
        "experimental_report_only"
    )
    assert ScoringLane.NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY.value not in {
        "ngram_hamming",
        "ngram_hamming_production",
    }
