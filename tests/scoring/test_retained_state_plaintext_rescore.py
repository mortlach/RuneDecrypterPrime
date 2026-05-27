from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from rune_decrypter_prime.core.types import Direction, ObjectiveFamily, ObjectiveSpec, Stat
from rune_decrypter_prime.scoring.retained_state import (
    PlaintextRetainedCandidate,
    score_plaintext_candidate,
)
from rune_decrypter_prime.scoring.scorer_report import ScorerReport


pytestmark = pytest.mark.tier_a


class _RecordingScorer:
    win = 10
    objective = ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10)

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[int, ...], tuple[tuple[int, int], ...] | None]] = []

    def score(self, plaintext, wli=None) -> float:
        self.calls.append((tuple(plaintext), None if wli is None else tuple(tuple(row) for row in wli)))
        return 0.75

    def telemetry(self):
        return {"impl": "test", "device": "cpu", "dtype": "float64"}

    def last_stats(self):
        return {"n_windows": 1.0}


def test_candidate_copies_mutable_plaintext_input_into_tuple() -> None:
    plaintext = [1, 2, 3]
    candidate = PlaintextRetainedCandidate(plaintext)
    plaintext[0] = 9

    assert candidate.plaintext_idx == (1, 2, 3)


def test_candidate_normalizes_numpy_list_and_tuple_plaintext_inputs() -> None:
    assert PlaintextRetainedCandidate(np.asarray([1, 2], dtype=np.uint8)).plaintext_idx == (1, 2)
    assert PlaintextRetainedCandidate([1, 2]).plaintext_idx == (1, 2)
    assert PlaintextRetainedCandidate((1, 2)).plaintext_idx == (1, 2)


def test_candidate_rejects_bool_tokens() -> None:
    with pytest.raises(TypeError, match="bool"):
        PlaintextRetainedCandidate([True])


def test_candidate_rejects_string_tokens() -> None:
    with pytest.raises(TypeError, match="integer token"):
        PlaintextRetainedCandidate(["1"])


def test_candidate_rejects_negative_tokens() -> None:
    with pytest.raises(ValueError, match=r"\[0\.\.28\]"):
        PlaintextRetainedCandidate([-1])


def test_candidate_rejects_tokens_above_28() -> None:
    with pytest.raises(ValueError, match=r"\[0\.\.28\]"):
        PlaintextRetainedCandidate([29])


def test_candidate_copies_wli_into_tuple_of_tuples() -> None:
    wli = [[0, 2], [1, 2]]
    candidate = PlaintextRetainedCandidate([1, 2], wli=wli)
    wli[0][0] = 1

    assert candidate.wli == ((0, 2), (1, 2))


def test_candidate_rejects_wli_length_mismatch() -> None:
    with pytest.raises(ValueError, match="length"):
        PlaintextRetainedCandidate([1, 2], wli=[[0, 2]])


def test_candidate_rejects_malformed_wli_pairs() -> None:
    with pytest.raises(TypeError, match="pair"):
        PlaintextRetainedCandidate([1], wli=[[0, 1, 2]])


def test_candidate_rejects_wli_bool_values() -> None:
    with pytest.raises(TypeError, match="bool"):
        PlaintextRetainedCandidate([1], wli=[[False, 1]])

    with pytest.raises(TypeError, match="bool"):
        PlaintextRetainedCandidate([1], wli=[[0, True]])


def test_candidate_rejects_wli_non_integer_values() -> None:
    with pytest.raises(TypeError, match="integer"):
        PlaintextRetainedCandidate([1], wli=[["0", 1]])


def test_candidate_rejects_pos_in_word_at_or_above_word_len() -> None:
    with pytest.raises(ValueError, match="pos_in_word"):
        PlaintextRetainedCandidate([1], wli=[[1, 1]])


def test_candidate_rejects_invalid_wli_bounds() -> None:
    with pytest.raises(ValueError, match=">= 0"):
        PlaintextRetainedCandidate([1], wli=[[-1, 2]])

    with pytest.raises(ValueError, match="> 0"):
        PlaintextRetainedCandidate([1], wli=[[0, 0]])


def test_candidate_normalizes_direction() -> None:
    candidate = PlaintextRetainedCandidate([1], direction="ltr")

    assert candidate.direction is Direction.LTR


def test_candidate_representation_must_be_plaintext_idx() -> None:
    with pytest.raises(ValueError, match="plaintext_idx"):
        PlaintextRetainedCandidate([1], candidate_representation="key_vector")  # type: ignore[arg-type]


def test_source_ref_is_not_accepted_by_first_dataclass() -> None:
    with pytest.raises(TypeError):
        PlaintextRetainedCandidate([1], source_ref="lp")  # type: ignore[call-arg]


def test_candidate_rejects_path_metadata_fields() -> None:
    with pytest.raises(TypeError, match="candidate_id"):
        PlaintextRetainedCandidate([1], candidate_id=Path("/tmp/private"))

    with pytest.raises(TypeError, match="alphabet"):
        PlaintextRetainedCandidate([1], alphabet=Path("/tmp/private"))

    with pytest.raises(TypeError, match="tokenization"):
        PlaintextRetainedCandidate([1], tokenization=Path("/tmp/private"))


def test_candidate_metadata_fields_must_be_strings() -> None:
    with pytest.raises(TypeError, match="alphabet"):
        PlaintextRetainedCandidate([1], alphabet=123)

    with pytest.raises(TypeError, match="tokenization"):
        PlaintextRetainedCandidate([1], tokenization=123)

    with pytest.raises(TypeError, match="candidate_id"):
        PlaintextRetainedCandidate([1], candidate_id=123)


def test_score_plaintext_candidate_calls_scorer_with_plaintext_and_wli() -> None:
    candidate = PlaintextRetainedCandidate([1, 2], wli=[[0, 2], [1, 2]])
    scorer = _RecordingScorer()

    report = score_plaintext_candidate(candidate, scorer)

    assert scorer.calls == [((1, 2), ((0, 2), (1, 2)))]
    assert isinstance(report, ScorerReport)
    assert report.score == pytest.approx(0.75)


def test_score_plaintext_candidate_does_not_require_solver_or_cipher_material() -> None:
    candidate = PlaintextRetainedCandidate([1])
    scorer = _RecordingScorer()

    report = score_plaintext_candidate(candidate, scorer)

    assert report.to_json_dict()["score"] == pytest.approx(0.75)
