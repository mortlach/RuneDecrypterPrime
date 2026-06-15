from __future__ import annotations

from typing import Iterable, Sequence, Any

import pytest

from rune_decrypter_prime.core.config.scoring import (
    SpanHammingCombineMode,
    SpanHammingGateFailPolicy,
    SpanHammingMode,
)
from rune_decrypter_prime.scoring.base_scorer import BaseScorer


class _ConcreteScorer(BaseScorer):
    def score(self, plaintext: Iterable[int], wli_windows: Any | None = None) -> float:
        return 0.0

    def batch_score(self, pts: Sequence[Iterable[int]], wlis: Any | None = None):
        return [0.0 for _ in pts]


def test_span_hamming_internal_enum_fields_normalise_string_assignments() -> None:
    scorer = _ConcreteScorer()

    scorer._span_hamming_mode = "calibrated"
    scorer._span_hamming_combine_mode = "min"
    scorer._span_hamming_gate_fail_policy = "char_only"

    assert scorer._span_hamming_mode is SpanHammingMode.CALIBRATED
    assert scorer._span_hamming_combine_mode is SpanHammingCombineMode.MIN
    assert scorer._span_hamming_gate_fail_policy is SpanHammingGateFailPolicy.CHAR_ONLY


def test_span_hamming_internal_enum_fields_reject_unknown_string_assignments() -> None:
    scorer = _ConcreteScorer()

    with pytest.raises(ValueError, match="span_hamming_combine_mode"):
        scorer._span_hamming_combine_mode = "not_a_combine_mode"
