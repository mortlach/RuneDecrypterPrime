from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from cipher_development.shared.archive import candidate_id_for, read_candidate_archive
from cipher_development.shared.replay import read_candidate_batch
from cipher_development.two_period_overlay.config import (
    ALPHABET_SIZE,
    ARCHIVE_CAPACITY,
    CRIB_RUNES,
    CRIB_START,
    CRIB_WORD,
    DECISION_SCORE,
    PERIOD_A,
    PERIOD_B,
    TEXT_LENGTH,
    RunBudget,
)
from cipher_development.two_period_overlay.run import (
    ReferenceCase,
    SearchCase,
    campaign_decision,
    candidate_record,
    comparison_seed,
    comparison_summary,
    crib_space,
    deterministic_key,
    discover_archive,
    expand,
    normalise_baseline_result,
    run_search,
    write_search_artifacts,
)


def _linear_fixture():
    true_key = deterministic_key()
    crib = np.asarray(CRIB_RUNES, dtype=np.uint8)
    ciphertext = np.zeros(TEXT_LENGTH, dtype=np.uint8)
    for offset, plain in enumerate(crib):
        pos = CRIB_START + offset
        ciphertext[pos] = (
            int(plain) + int(true_key[pos % PERIOD_A]) + int(true_key[PERIOD_A + pos % PERIOD_B])
        ) % ALPHABET_SIZE
    particular, basis, free = crib_space(ciphertext, crib)
    variables = np.asarray([true_key[index] for index in free], dtype=np.uint8)
    return true_key, crib, ciphertext, particular, basis, free, variables


def _target_evaluator(target: np.ndarray):
    def evaluate(values: np.ndarray) -> np.ndarray:
        batch = np.asarray(values, dtype=np.int64)
        return -np.sum((batch - target[None, :]) ** 2, axis=1).astype(np.float64)
    return evaluate


def test_run_budget_rejects_invalid_counts_and_temperatures() -> None:
    with pytest.raises(ValueError):
        RunBudget(0, 1, 1, 1, 1)
    with pytest.raises(TypeError):
        RunBudget(True, 1, 1, 1, 1)
    with pytest.raises(ValueError, match="sa_tmin"):
        RunBudget(1, 1, 1, 1, 1, sa_t0=0.1, sa_tmin=0.2)


def test_benchmark_constants_are_frozen() -> None:
    assert (PERIOD_A, PERIOD_B) == (13, 17)
    assert TEXT_LENGTH == 308
    assert ALPHABET_SIZE == 29
    assert CRIB_WORD == "uncomfortable"
    assert CRIB_START == 188
    assert len(CRIB_RUNES) == 13


def test_crib_space_preserves_gauge_and_reconstructs_true_key() -> None:
    true_key, _crib, _ciphertext, particular, basis, free, variables = _linear_fixture()
    assert len(free) == 16
    expanded = expand(variables, particular, basis)
    assert expanded[PERIOD_A] == 0
    assert np.array_equal(expanded, true_key)
    assert np.array_equal(expand(variables, particular, basis), expanded)


def test_candidate_identity_is_expanded_key_and_payload_replays() -> None:
    _true_key, _crib, _ciphertext, particular, basis, _free, variables = _linear_fixture()
    record = candidate_record(
        variables, 1.25, particular, basis,
        source="coordinate_discovery", operation="coordinate_descent", evaluation_index=12,
    )
    payload = record.to_json_dict()
    assert payload["identity"] == {"expanded_key": payload["payload"]["expanded_key"]}
    assert record.candidate_id == candidate_id_for(payload["identity"])
    assert expand(np.asarray(payload["payload"]["variables"], dtype=np.uint8), particular, basis).tolist() == payload["payload"]["expanded_key"]
    assert set(payload["scores"]) == {DECISION_SCORE}


def test_discovery_and_handoff_are_deterministic() -> None:
    _true_key, _crib, _ciphertext, particular, basis, _free, variables = _linear_fixture()
    evaluate = _target_evaluator(variables)
    budget = RunBudget(4, 2, 2, 10, 1)
    first, first_evals = discover_archive(evaluate, particular, basis, budget)
    second, second_evals = discover_archive(evaluate, particular, basis, budget)
    assert first_evals == second_evals
    assert [record.candidate_id for record in first.records] == [record.candidate_id for record in second.records]
    assert [record.scores[DECISION_SCORE] for record in first.records] == sorted(
        (record.scores[DECISION_SCORE] for record in first.records), reverse=True
    )


def test_paired_run_uses_matched_seeds_and_parent_provenance() -> None:
    _true_key, _crib, _ciphertext, particular, basis, _free, variables = _linear_fixture()
    stages: list[str] = []
    outcome = run_search(
        _target_evaluator(variables), particular, basis,
        RunBudget(4, 2, 2, 12, 1),
        progress=lambda label, _metrics: stages.append(label),
    )
    assert 1 <= len(outcome.comparisons) <= 2
    assert len(outcome.comparisons) == len(outcome.handoff_batch.candidates)
    for index, row in enumerate(outcome.comparisons):
        assert row["matched_seed"] == comparison_seed(index)
        assert row["archive_diagnostics"]["sa_proposals_attempted"] == 12
        assert row["control_diagnostics"]["sa_proposals_attempted"] == 12
        if row["archive_final_id"] != row["archive_parent_id"] and row["archive_retained"]:
            improved = outcome.archive.get(row["archive_final_id"])
            assert improved.provenance.parent_ids == (row["archive_parent_id"],)
        else:
            assert row["archive_offer_action"] == "unchanged"
    assert len(outcome.archive.records) <= ARCHIVE_CAPACITY
    assert stages[0:2] == ["discovery_completed", "handoff_batches_prepared"]
    assert stages.count("paired_exploitation_result") == len(outcome.comparisons)



def test_full_paired_core_is_deterministic_for_fixed_configuration() -> None:
    _true_key, _crib, _ciphertext, particular, basis, _free, variables = _linear_fixture()
    budget = RunBudget(4, 2, 2, 12, 1)
    first = run_search(_target_evaluator(variables), particular, basis, budget)
    second = run_search(_target_evaluator(variables), particular, basis, budget)
    assert first.best_variables == second.best_variables
    assert first.best_score == second.best_score
    assert first.comparisons == second.comparisons
    assert [record.candidate_id for record in first.archive.records] == [
        record.candidate_id for record in second.archive.records
    ]

def test_search_case_has_no_truth_fields() -> None:
    assert set(SearchCase.__dataclass_fields__).isdisjoint({
        "plaintext", "true_key", "expected_plaintext", "reference", "truth",
    })
    assert {"plaintext", "true_key"}.issubset(ReferenceCase.__dataclass_fields__)


def test_canary_artifacts_round_trip(tmp_path: Path) -> None:
    _true_key, _crib, _ciphertext, particular, basis, _free, variables = _linear_fixture()
    outcome = run_search(
        _target_evaluator(variables), particular, basis,
        RunBudget(4, 2, 2, 8, 1),
    )
    names = write_search_artifacts(tmp_path, outcome)
    assert set(names) == {
        "coordinate_archive", "archive_handoff_batch", "control_start_batch", "final_archive",
    }
    restored = read_candidate_archive(tmp_path / names["final_archive"])
    handoff = read_candidate_batch(tmp_path / names["archive_handoff_batch"])
    control = read_candidate_batch(tmp_path / names["control_start_batch"])
    assert len(restored.records) >= len(handoff.candidates)
    assert 1 <= len(handoff.candidates) <= 2
    assert len(handoff.candidates) == len(control.candidates)
    assert handoff.selection_label == "coordinate_to_sa"


def test_comparison_decision_is_fixed_and_canary_refines() -> None:
    _true_key, _crib, _ciphertext, particular, basis, _free, variables = _linear_fixture()
    outcome = run_search(
        _target_evaluator(variables), particular, basis,
        RunBudget(4, 2, 2, 5, 1),
    )
    summary = comparison_summary(outcome)
    assert summary["comparison_count"] == len(outcome.comparisons)
    assert summary["archive_wins"] + summary["control_wins"] + summary["ties"] == len(outcome.comparisons)
    assert "archive_median_gain" in summary and "control_median_gain" in summary
    assert campaign_decision(summary, "canary") == "refine"


def test_baseline_import_separates_summary_and_reference() -> None:
    payload = {
        "schema": "rdp.two_period_crib_solver.plateau_comparison.v1",
        "status": "completed",
        "decision": "all_three_plateaued_on_p13_p17",
        "stop_reason": "campaign_wallclock_budget",
        "evaluations": 123,
        "elapsed_seconds": 25_200.0,
        "config": {
            "periods": [13, 17],
            "alphabet_size": 29,
            "text": {"length": 308},
            "crib": {"word": "uncomfortable", "compact_core_offset": 188},
        },
        "best_result": {
            "phase": "short_sa",
            "score": 1.5,
            "exact_plaintext": False,
            "rune_matches": 20,
            "canonical_key_equal": False,
        },
    }
    absolute_source = Path(Path.cwd().anchor) / "sensitive" / "latest_result.json"
    summary, reference = normalise_baseline_result(payload, "a" * 64, str(absolute_source))
    assert summary["source_filename"] == "latest_result.json"
    assert summary["source_sha256"] == "a" * 64
    assert str(absolute_source.parent) not in json.dumps(summary)
    assert "exact_plaintext" not in summary
    assert reference == {
        "exact_plaintext": False,
        "rune_matches": 20,
        "canonical_key_equal": False,
    }


def test_baseline_import_rejects_wrong_contract_or_hash() -> None:
    with pytest.raises(ValueError):
        normalise_baseline_result({"schema": "other"}, "a" * 64, "result.json")
    with pytest.raises(ValueError, match="source_sha256"):
        normalise_baseline_result({}, "bad", "result.json")


def test_campaign_source_uses_no_environment_or_cli_configuration() -> None:
    root = Path(__file__).resolve().parents[2]
    for relpath in (
        Path("cipher_development/two_period_overlay/config.py"),
        Path("cipher_development/two_period_overlay/keyspace.py"),
        Path("cipher_development/two_period_overlay/search.py"),
        Path("cipher_development/two_period_overlay/benchmark.py"),
        Path("cipher_development/two_period_overlay/run.py"),
    ):
        text = (root / relpath).read_text(encoding="utf-8")
        for token in ("os.environ", "os.getenv", "sys.argv", "argparse"):
            assert token not in text
