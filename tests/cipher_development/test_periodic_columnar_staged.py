from __future__ import annotations

import math
import inspect
import time
from pathlib import Path

import pytest
from rdp import api

from cipher_development.periodic_columnar_staged.qualification import (
    QUALIFICATION,
    RECIPE_ID,
    SMOKE,
    QualificationClock,
    QualificationProgress,
    QualificationTimeLimit,
    _configuration,
    _deduplicate_per_head_candidates,
    _final_scoring,
    _final_solver,
    _head_scoring,
    _ranking_scoring,
    _search_candidates,
    _tail_permutations,
    config_for_mode,
)


def test_profiles_are_one_smoke_and_one_bounded_qualification() -> None:
    assert config_for_mode("smoke") is SMOKE
    assert config_for_mode("qualification") is QUALIFICATION
    assert config_for_mode("development") is QUALIFICATION
    assert (SMOKE.period, SMOKE.columns) == (1, 2)
    assert (QUALIFICATION.period, QUALIFICATION.columns) == (7, 7)
    assert QUALIFICATION.maximum_seconds == 60 * 60
    with pytest.raises(ValueError, match="mode must be"):
        config_for_mode("diagnostic")


def test_qualification_has_the_evidence_backed_candidate_reduction() -> None:
    assert RECIPE_ID == "periodic_columnar_decomposed_v2"
    assert QUALIFICATION.head_seed == 12_348
    assert QUALIFICATION.head_pool_size == 384
    assert QUALIFICATION.head_block_seeds == 24
    assert QUALIFICATION.head_swaps_per_block == 2
    assert QUALIFICATION.retained_heads == 1
    assert QUALIFICATION.fast_shortlist_per_scorer == 192
    assert QUALIFICATION.complete_keys_per_head == 1
    assert QUALIFICATION.solver_seed == 12_446


def test_head_and_tail_rankers_use_the_intended_lane_sequence() -> None:
    head = _head_scoring()
    ranking = _ranking_scoring()
    final = _final_scoring(QUALIFICATION)
    smoke_final = _final_scoring(SMOKE)

    assert dict(head.character_order_weights) == {1: 0.75, 2: 0.25}
    assert not head.word_length_lane_enabled
    assert dict(ranking.character_order_weights) == {3: 0.2, 4: 0.8}
    assert dict(ranking.word_length_order_weights) == {2: 0.3, 4: 0.7}
    assert ranking.word_length_lane_enabled
    assert dict(final.character_order_weights) == {3: 0.5, 4: 0.5}
    assert not final.word_length_lane_enabled
    assert smoke_final.word_length_lane_enabled
    assert dict(smoke_final.word_length_order_weights) == {2: 0.3, 4: 0.7}


def test_final_solver_is_one_real_column_aware_kaeding_run() -> None:
    values = _final_solver(QUALIFICATION).to_dict()["parameters"]

    assert values["steps"] == 12_000
    assert values["restarts"] == 1
    assert values["column_interval"] == 1
    assert values["column_batch_size"] == 384
    assert values["target_score"] is None
    assert values["slip_policy"] == api.advanced.KaedingSlipPolicy.ON_STALL.value


def test_tail_enumeration_is_complete_and_unique() -> None:
    tails = _tail_permutations(7)

    assert tails.shape == (math.factorial(7), 7)
    assert len({tuple(int(value) for value in row) for row in tails}) == 5_040


def test_complete_candidate_selection_preserves_per_head_handoff_order() -> None:
    rows = [
        {"candidate_id": "head-one-best", "decision_score": 0.5},
        {"candidate_id": "head-two-best", "decision_score": 0.9},
        {"candidate_id": "head-one-best", "decision_score": 1.0},
    ]

    selected = _deduplicate_per_head_candidates(rows)

    assert [row["candidate_id"] for row in selected] == [
        "head-one-best",
        "head-two-best",
    ]


def test_progress_persists_latest_candidate_before_enforcing_time_limit(
    tmp_path: Path,
) -> None:
    path = tmp_path / "progress.json"
    clock = QualificationClock(maximum_seconds=60)
    clock.deadline = time.perf_counter() - 1
    callback = QualificationProgress(clock=clock, progress_path=path)

    with pytest.raises(QualificationTimeLimit, match="time limit reached"):
        callback(
            {"pct": 12, "step": 34, "evals": 56, "best_score": 0.78},
            tuple(range(7)),
        )

    assert callback.latest_key == tuple(range(7))
    assert callback.latest_score == pytest.approx(0.78)
    text = path.read_text(encoding="utf-8")
    assert '"stage": "integrated_refinement"' in text
    assert '"evaluations": 56' in text


def test_search_configuration_contains_no_benchmark_truth() -> None:
    payload = _configuration(QUALIFICATION)

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return {str(key).lower() for key in value} | set().union(
                *(keys(item) for item in value.values())
            )
        if isinstance(value, (list, tuple)):
            return set().union(*(keys(item) for item in value))
        return set()

    assert payload["tail_permutations_per_head"] == 5_040
    assert keys(payload).isdisjoint(
        {"true_key", "known_key", "oracle", "match_ratio", "reference"}
    )


def test_candidate_search_has_no_plaintext_key_or_oracle_input() -> None:
    parameters = set(inspect.signature(_search_candidates).parameters)

    assert parameters == {
        "cfg",
        "ciphertext",
        "word_lengths",
        "cipher_spec",
        "key_space",
        "clock",
        "artifact_root",
    }
    assert parameters.isdisjoint(
        {"plaintext", "benchmark_key", "known_key", "oracle", "target_score"}
    )


def test_qualification_source_has_one_public_run_and_no_exploratory_names() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "cipher_development/periodic_columnar_staged/qualification.py"
    ).read_text(encoding="utf-8")
    entry_point = (
        root / "cipher_development/run_experiment.py"
    ).read_text(encoding="utf-8")

    assert source.count("result = api.run(") == 1
    assert "oracle_stop_score" not in source
    assert "run_overnight" not in source
    assert "minimal" not in source.lower()
    assert "contextlib.chdir(REPO_ROOT)" in entry_point


def test_readme_declares_public_solve_and_terminal_truth_boundary() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (
        root / "cipher_development/periodic_columnar_staged/README.md"
    ).read_text(encoding="utf-8")

    assert "one-start char3/4 Kaeding refinement through api.run" in text
    assert "all 5,040 C7 tails" in text
    assert "only after\nthe single solver run has completed" in text
    assert "60-minute wall-clock" in text
    assert "one seed to one solver restart" in text
    assert "exact plaintext recovery: yes (2,489 of 2,489 symbols)" in text
    assert "it had no expected plaintext, expected key, oracle score, crib or target score" in text
