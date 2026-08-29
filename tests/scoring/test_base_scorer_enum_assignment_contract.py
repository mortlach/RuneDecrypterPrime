from __future__ import annotations
from typing import Iterable, Sequence, Any
from rune_decrypter_prime.core.config.scoring import (
    SpanHammingCombineMode,
    SpanHammingGateFailurePolicy,
    SpanHammingMode,
)
from rune_decrypter_prime.scoring.base_scorer import BaseScorer

class _ConcreteScorer(BaseScorer):

    def score(self, plaintext: Iterable[int], wli_windows: Any | None=None) -> float:
        return 0.0

    def batch_score(self, pts: Sequence[Iterable[int]], wlis: Any | None=None):
        return [0.0 for _ in pts]


def test_span_hamming_internal_fields_use_typed_enum_assignments() -> None:
    scorer = _ConcreteScorer()
    scorer._span_hamming_mode = SpanHammingMode.CALIBRATED
    scorer._span_hamming_combine_mode = SpanHammingCombineMode.MINIMUM
    scorer._span_hamming_gate_fail_policy = SpanHammingGateFailurePolicy.CHARACTER_ONLY
    assert scorer._span_hamming_mode is SpanHammingMode.CALIBRATED
    assert scorer._span_hamming_combine_mode is SpanHammingCombineMode.MINIMUM
    assert (
        scorer._span_hamming_gate_fail_policy
        is SpanHammingGateFailurePolicy.CHARACTER_ONLY
    )
