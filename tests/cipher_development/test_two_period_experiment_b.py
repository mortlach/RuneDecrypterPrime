from __future__ import annotations

import csv
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from cipher_development.two_period_overlay import candidate_words
from cipher_development.two_period_overlay.candidate_words import (
    CandidateWord,
    benchmark_for_candidate,
    build_nested_candidate_lists,
)
from cipher_development.two_period_overlay.config import CRIB_RUNES
from cipher_development.two_period_overlay.experiment_b import (
    OVERNIGHT_SECONDS,
    _progression_gate,
    _source_experiment_a,
    build_branch_starts,
)
from cipher_development.two_period_overlay.keyspace import crib_space
from cipher_development.two_period_overlay.review_pack import _required_artifacts
from cipher_development.two_period_overlay.scorer_profiles import S2
from cipher_development.two_period_overlay.staged_handoff import _run_stage


def _letters(index: int) -> str:
    chars = []
    value = index
    for _ in range(6):
        chars.append(chr(ord("a") + value % 26))
        value //= 26
    return "w" + "".join(reversed(chars))


def _runes(index: int) -> tuple[int, ...]:
    # Base-29 representation padded to eight symbols.
    values = []
    value = index + 1
    for _ in range(8):
        values.append(value % 29)
        value //= 29
    return tuple(values)


def test_candidate_word_requires_exact_eight_runes() -> None:
    with pytest.raises(ValueError, match="exactly eight"):
        CandidateWord(
            branch_id="branch_deadbeef",
            word="example",
            runes=(1, 2),
            frequency=1.0,
            source_file="x.csv",
            source_row=1,
            source_selected=True,
        )


def test_nested_lists_are_deterministic_distinct_and_nested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = []
    mapping: dict[str, tuple[int, ...]] = {}
    for index in range(1100):
        word = _letters(index)
        runes = _runes(index)
        mapping[word] = runes
        rows.append([word, str(100000 - index), "1", f"r{index}", "note"])
    # Add a duplicate rune spelling with lower frequency; it must collapse.
    mapping["wzzzzzz"] = _runes(5)
    rows.append(["wzzzzzz", "1", "1", "duplicate", "note"])

    path = tmp_path / "raw1grams_test.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows(rows)

    monkeypatch.setattr(candidate_words, "_encode_word", lambda word: mapping.get(word))
    reverse = {f"r{index}": _runes(index) for index in range(1100)}
    reverse["duplicate"] = _runes(5)
    monkeypatch.setattr(
        candidate_words.Runeglish,
        "rune_to_pos",
        staticmethod(lambda token: list(reverse[token])),
    )
    monkeypatch.setattr(candidate_words, "DORMOUSE_RUNES", _runes(20))
    monkeypatch.setattr(candidate_words, "DORMOUSE_WORD", _letters(20))

    first = build_nested_candidate_lists(tmp_path, ordering_seed=77)
    second = build_nested_candidate_lists(tmp_path, ordering_seed=77)
    assert [item.branch_id for item in first.candidates_100] == [
        item.branch_id for item in second.candidates_100
    ]
    assert len(first.candidates_10) == 10
    assert len(first.candidates_100) == 100
    assert len(first.candidates_1000) == 1000
    assert {item.runes for item in first.candidates_10} <= {
        item.runes for item in first.candidates_100
    } <= {item.runes for item in first.candidates_1000}
    assert len({item.runes for item in first.candidates_100}) == 100
    assert len({item.runes for item in first.candidates_1000}) == 1000
    assert first.required_occurred_naturally is True
    public = first.public_payload(10)
    assert not any("truth" in key or "reference" in key for key in public)
    assert all("controlled" not in row for row in public["candidates"])


def test_candidate_branch_benchmark_is_hypothetical_d8() -> None:
    # Use the real controlled sequence with a different label; hypothetical
    # branches are not required to match plaintext during search construction.
    candidate = CandidateWord(
        branch_id=candidate_words._branch_id(tuple(candidate_words.DORMOUSE_RUNES)),
        word="dormouse",
        runes=tuple(candidate_words.DORMOUSE_RUNES),
        frequency=1.0,
        source_file="test.csv",
        source_row=1,
        source_selected=True,
    )
    benchmark = benchmark_for_candidate(candidate)
    assert benchmark.additional_cribs_are_exact is False
    ciphertext = np.arange(benchmark.text_length, dtype=np.uint16) % 29
    particular, basis, free = crib_space(
        ciphertext.astype(np.uint8),
        np.asarray(CRIB_RUNES, dtype=np.uint8),
        benchmark,
    )
    assert particular.shape == (30,)
    assert basis.shape == (30, 8)
    assert len(free) == 8


def test_branch_starts_are_repeatable_and_shared() -> None:
    first = build_branch_starts(5)
    second = build_branch_starts(5)
    assert first == second
    assert len({row["seed"] for row in first}) == 5
    assert all(len(row["variables"]) == 8 for row in first)


def test_run_stage_preserves_branch_family_id() -> None:
    benchmark = SimpleNamespace(key_length=8, gauge_key_index=0, gauge_value=0, alphabet_size=29, benchmark_id="synthetic_branch")
    # The stage helper calls expand(), so provide an identity-like affine map
    # with gauge column zero.
    particular = np.zeros(8, dtype=np.uint8)
    basis = np.eye(8, dtype=np.uint8)
    basis[0, :] = 0

    class Case:
        def __init__(self) -> None:
            self.particular = particular
            self.basis = basis

        @staticmethod
        def evaluate_variables(values: np.ndarray) -> np.ndarray:
            array = np.asarray(values, dtype=np.float64)
            if array.ndim == 1:
                array = array[None, :]
            return -np.sum(array * array, axis=1)

    starts = ({"restart_index": 0, "seed": 1, "variables": [0] * 8},)
    outcome = _run_stage(
        stage_id="scout",
        profile=S2,
        search_case=Case(),
        inputs=starts,
        sweeps=1,
        benchmark=benchmark,
        archive_capacity=1,
        family_id="branch_test",
        stage_safety_seconds=10.0,
    )
    assert outcome.archive.records[0].family_id == "branch_test"


def test_candidate_branch_review_pack_uses_dynamic_inventory(tmp_path: Path) -> None:
    inventory = tmp_path / "artifacts/experiment_b/required_artifacts.json"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        json.dumps({
            "schema": "rdp.two_period_overlay.dynamic_required_artifacts.v1",
            "paths": ["artifacts/experiment_b/branches/branch_a/scout/attempts.json"],
        }),
        encoding="utf-8",
    )
    required = _required_artifacts("candidate_word_branches_b10_v1", tmp_path)
    assert "artifacts/experiment_b/required_artifacts.json" in required
    assert "artifacts/experiment_b/source_experiment_a_gate.json" in required
    assert "artifacts/experiment_b/branches/branch_a/scout/attempts.json" in required


def test_pack04_runs_b100_only_after_b10_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cipher_development.two_period_overlay import pack04

    calls: list[int] = []

    def fake_run(_repo_root: Path, *, list_size: int) -> Path:
        calls.append(list_size)
        path = tmp_path / f"b{list_size}.json"
        path.write_text(json.dumps({
            "decision": "promote",
            "result_summary": {"progression_gate_passed": list_size == 10},
        }), encoding="utf-8")
        return path

    monkeypatch.setattr(pack04, "run_candidate_word_branches", fake_run)
    monkeypatch.setattr(pack04, "RUN_B10", True)
    monkeypatch.setattr(pack04, "RUN_B100_WHEN_B10_GATE_PASSES", True)
    assert pack04.main() == 0
    assert calls == [10, 100]


def test_duplicate_representative_uses_highest_frequency_then_lexical_word(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shared = _runes(2)
    mapping = {"zword": shared, "aword": shared}
    rows = [
        ["zword", "100", "1", "z", "note"],
        ["aword", "100", "1", "a", "note"],
    ]
    # Supply enough independent candidates for the loader's minimum.
    reverse = {"z": shared, "a": shared}
    for index in range(1, 1002):
        word = _letters(index + 1000)
        runes = _runes(index + 1000)
        token = f"r{index}"
        mapping[word] = runes
        reverse[token] = runes
        rows.append([word, str(1000 - index), "1", token, "note"])

    path = tmp_path / "raw1grams_test.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows(rows)

    monkeypatch.setattr(candidate_words, "_encode_word", lambda word: mapping.get(word))
    monkeypatch.setattr(
        candidate_words.Runeglish,
        "rune_to_pos",
        staticmethod(lambda token: list(reverse[token])),
    )
    loaded, _assets = candidate_words.load_selected_eight_rune_words(tmp_path)
    representative = next(item for item in loaded if item.runes == shared)
    assert representative.word == "aword"


def test_progression_gates_match_the_predeclared_rules() -> None:
    within = {"safety_adjusted_elapsed_s": OVERNIGHT_SECONDS}
    over = {"safety_adjusted_elapsed_s": OVERNIGHT_SECONDS + 0.001}

    assert _progression_gate(
        list_size=10,
        survived=True,
        exact=False,
        final_rank=3,
        projection=within,
    )
    assert _progression_gate(
        list_size=10,
        survived=True,
        exact=True,
        final_rank=9,
        projection=within,
    )
    assert not _progression_gate(
        list_size=10,
        survived=False,
        exact=True,
        final_rank=1,
        projection=within,
    )
    assert not _progression_gate(
        list_size=10,
        survived=True,
        exact=False,
        final_rank=4,
        projection=within,
    )
    assert not _progression_gate(
        list_size=10,
        survived=True,
        exact=True,
        final_rank=1,
        projection=over,
    )

    assert _progression_gate(
        list_size=100,
        survived=True,
        exact=False,
        final_rank=10,
        projection={},
    )
    assert not _progression_gate(
        list_size=100,
        survived=True,
        exact=True,
        final_rank=11,
        projection={},
    )

    assert _progression_gate(
        list_size=1000,
        survived=True,
        exact=False,
        final_rank=25,
        projection={},
    )
    assert not _progression_gate(
        list_size=1000,
        survived=True,
        exact=True,
        final_rank=26,
        projection={},
    )


def test_candidate_branch_dynamic_inventory_rejects_unsafe_paths(tmp_path: Path) -> None:
    inventory = tmp_path / "artifacts/experiment_b/required_artifacts.json"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        json.dumps({
            "schema": "rdp.two_period_overlay.dynamic_required_artifacts.v1",
            "paths": ["../outside.json"],
        }),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsafe path"):
        _required_artifacts("candidate_word_branches_b10_v1", tmp_path)


def test_pack04_does_not_run_b100_when_b10_gate_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cipher_development.two_period_overlay import pack04

    calls: list[int] = []

    def fake_run(_repo_root: Path, *, list_size: int) -> Path:
        calls.append(list_size)
        path = tmp_path / f"b{list_size}.json"
        path.write_text(json.dumps({
            "decision": "refine",
            "result_summary": {"progression_gate_passed": False},
        }), encoding="utf-8")
        return path

    monkeypatch.setattr(pack04, "run_candidate_word_branches", fake_run)
    monkeypatch.setattr(pack04, "RUN_B10", True)
    monkeypatch.setattr(pack04, "RUN_B100_WHEN_B10_GATE_PASSES", True)
    assert pack04.main() == 0
    assert calls == [10]


def test_real_wrong_candidate_branch_constructs_d8_when_assets_are_installed() -> None:
    pytest.importorskip("zstandard")
    from cipher_development.two_period_overlay.benchmark import build_rdp_case

    wrong = list(candidate_words.DORMOUSE_RUNES)
    wrong[0] = (int(wrong[0]) + 1) % 29
    candidate = CandidateWord(
        branch_id=candidate_words._branch_id(tuple(wrong)),
        word="decoyword",
        runes=tuple(wrong),
        frequency=1.0,
        source_file="controlled_test",
        source_row=1,
        source_selected=True,
    )
    benchmark = benchmark_for_candidate(candidate)
    search_case, _reference = build_rdp_case(
        benchmark, scoring_contract=S2.scoring_contract()
    )
    assert search_case.basis.shape == (30, 8)
    assert len(search_case.free_columns) == 8

    from cipher_development.two_period_overlay.replay import (
        _context_benchmark,
        build_replay_evaluator,
        make_replay_context,
    )

    context = make_replay_context(
        search_case,
        run_id="dynamic_branch_replay_test",
        configuration_hash="a" * 40,
        evaluator_provenance={},
        scoring_contract=S2.scoring_contract(),
        decision_score=S2.score_name,
    )
    assert _context_benchmark(context) == benchmark
    assert callable(build_replay_evaluator(context))


def test_run_stage_inherits_branch_family_id_from_parent() -> None:
    benchmark = SimpleNamespace(
        key_length=8,
        gauge_key_index=0,
        gauge_value=0,
        alphabet_size=29,
        benchmark_id="synthetic_branch",
    )
    particular = np.zeros(8, dtype=np.uint8)
    basis = np.eye(8, dtype=np.uint8)
    basis[0, :] = 0

    class Case:
        def __init__(self) -> None:
            self.particular = particular
            self.basis = basis

        @staticmethod
        def evaluate_variables(values: np.ndarray) -> np.ndarray:
            array = np.asarray(values, dtype=np.float64)
            if array.ndim == 1:
                array = array[None, :]
            return -np.sum(array * array, axis=1)

    starts = ({"restart_index": 0, "seed": 1, "variables": [0] * 8},)
    scout = _run_stage(
        stage_id="scout",
        profile=S2,
        search_case=Case(),
        inputs=starts,
        sweeps=1,
        benchmark=benchmark,
        archive_capacity=1,
        family_id="branch_parent",
        stage_safety_seconds=10.0,
    )
    bridge = _run_stage(
        stage_id="bridge",
        profile=S2,
        search_case=Case(),
        inputs=scout.archive.records,
        sweeps=1,
        benchmark=benchmark,
        archive_capacity=1,
        stage_safety_seconds=10.0,
    )
    assert bridge.archive.records[0].family_id == "branch_parent"


def test_source_experiment_a_gate_does_not_return_terminal_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cipher_development.two_period_overlay import experiment_b

    run_dir = tmp_path / "run"
    result_path = run_dir / "artifacts/experiment_result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps({
            "decision": "promote",
            "result_summary": {"promotion_gate_passed": True},
            "reference_evaluation": {"known_plaintext": [1, 2, 3]},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        experiment_b,
        "latest_completed_experiment",
        lambda _repo_root, _experiment_id: run_dir,
    )
    gate = _source_experiment_a(tmp_path)
    assert gate["promotion_gate_passed"] is True
    assert gate["decision"] == "promote"
    assert "result_path" not in gate
    assert "reference_evaluation" not in gate
    assert "known_plaintext" not in json.dumps(gate)
