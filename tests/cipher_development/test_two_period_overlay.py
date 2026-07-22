from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from cipher_development.shared.archive import candidate_id_for, read_candidate_archive
from cipher_development.shared.replay import read_candidate_batch
from cipher_development.two_period_overlay.benchmark import (
    ReferenceCase,
    SearchCase,
    _scoring_kwargs,
    build_rdp_case,
    normalise_baseline_result,
)
from cipher_development.two_period_overlay.config import (
    ALPHABET_SIZE,
    CRIB_RUNES,
    CRIB_START,
    CRIB_WORD,
    DECISION_SCORE,
    PERIOD_A,
    PERIOD_B,
    SCORING_CONTRACT,
    TEXT_LENGTH,
    RunBudget,
)
from cipher_development.two_period_overlay.keyspace import (
    CampaignWallclockExceeded,
    anneal_and_polish,
    candidate_record,
    comparison_seed,
    coordinate_search,
    crib_space,
    deterministic_key,
    expand,
)
from cipher_development.two_period_overlay.run import (
    _budget_configuration,
    _resolve_source_path,
)
from cipher_development.two_period_overlay.search import (
    campaign_decision,
    comparison_summary,
    discover_archive,
    run_search,
    write_search_artifacts,
)


def _budget(**overrides) -> RunBudget:
    values = {
        "coordinate_restarts": 4,
        "coordinate_sweeps": 2,
        "handoff_candidates": 2,
        "minimum_comparisons": 1,
        "sa_steps": 12,
        "sa_cycles": 1,
        "sa_t0": 0.005,
        "sa_tmin": 0.0001,
        "wallclock_limit_s": 30.0,
    }
    values.update(overrides)
    return RunBudget(**values)


def _linear_fixture():
    true_key = deterministic_key()
    crib = np.asarray(CRIB_RUNES, dtype=np.uint8)
    ciphertext = np.zeros(TEXT_LENGTH, dtype=np.uint8)
    for offset, plain in enumerate(crib):
        pos = CRIB_START + offset
        ciphertext[pos] = (
            int(plain)
            + int(true_key[pos % PERIOD_A])
            + int(true_key[PERIOD_A + pos % PERIOD_B])
        ) % ALPHABET_SIZE
    particular, basis, free = crib_space(ciphertext, crib)
    variables = np.asarray([true_key[index] for index in free], dtype=np.uint8)
    return true_key, crib, ciphertext, particular, basis, free, variables


def _target_evaluator(target: np.ndarray):
    def evaluate(values: np.ndarray) -> np.ndarray:
        batch = np.asarray(values, dtype=np.int64)
        return -np.sum((batch - target[None, :]) ** 2, axis=1).astype(np.float64)
    return evaluate


def _baseline_payload() -> dict:
    return {
        "schema": "rdp.two_period_crib_solver.plateau_comparison.v1",
        "status": "completed",
        "decision": "all_three_plateaued_on_p13_p17",
        "stop_reason": "campaign_wallclock_budget",
        "evaluations": 123,
        "elapsed_seconds": 25_200.0,
        "config": {
            "periods": [13, 17],
            "alphabet_size": 29,
            "schedule": "overlay",
            "gauge": {"stream": "B", "index": 0, "value": 0},
            "text": {"length": 308},
            "crib": {"word": "uncomfortable", "compact_core_offset": 188},
            "scoring": {
                **SCORING_CONTRACT,
                "char_weights": {"3": 0.5, "4": 0.5},
                "wli_weights": {"3": 0.5, "4": 0.5},
            },
        },
        "phases": {
            "coordinate": {},
            "short_sa": {},
            "coordinate_beam": {},
        },
        "best_result": {
            "phase": "short_sa",
            "score": 1.5,
            "exact_plaintext": False,
            "rune_matches": 20,
            "complete_word_matches": 2,
            "complete_words_total": 70,
            "canonical_key_equal": False,
            "combined_shift_equal": False,
        },
    }


def test_run_budget_rejects_invalid_contract() -> None:
    with pytest.raises(ValueError):
        _budget(coordinate_restarts=0)
    with pytest.raises(TypeError):
        _budget(sa_steps=True)
    with pytest.raises(ValueError, match="minimum_comparisons"):
        _budget(handoff_candidates=1, minimum_comparisons=2)
    with pytest.raises(ValueError, match="sa_tmin"):
        _budget(sa_t0=0.1, sa_tmin=0.2)
    with pytest.raises(ValueError, match="wallclock_limit_s"):
        _budget(wallclock_limit_s=math.inf)


def test_budget_configuration_records_every_search_control() -> None:
    budget = _budget(sa_t0=0.02, sa_tmin=0.003, wallclock_limit_s=123.0)
    payload = _budget_configuration(budget)
    assert payload["minimum_comparisons"] == 1
    assert payload["sa_t0"] == 0.02
    assert payload["sa_tmin"] == 0.003
    assert payload["wallclock_limit_s"] == 123.0


def test_benchmark_constants_are_frozen() -> None:
    assert (PERIOD_A, PERIOD_B) == (13, 17)
    assert TEXT_LENGTH == 308
    assert ALPHABET_SIZE == 29
    assert CRIB_WORD == "uncomfortable"
    assert CRIB_START == 188
    assert len(CRIB_RUNES) == 13


def test_scoring_kwargs_are_derived_from_declared_contract() -> None:
    class Direction(str):
        pass

    marker = object()
    kwargs = _scoring_kwargs(Direction, marker)
    assert kwargs == {
        "objective": SCORING_CONTRACT["objective"],
        "include_char": SCORING_CONTRACT["include_char"],
        "use_word_breaks": SCORING_CONTRACT["use_word_breaks"],
        "n_char": SCORING_CONTRACT["n_char"],
        "n_wli": SCORING_CONTRACT["n_wli"],
        "char_weights": SCORING_CONTRACT["char_weights"],
        "wli_weights": SCORING_CONTRACT["wli_weights"],
        "encoding_dir": "ltr",
        "hard_crib": marker,
    }


def test_crib_space_preserves_gauge_and_reconstructs_true_key() -> None:
    true_key, _crib, _ciphertext, particular, basis, free, variables = _linear_fixture()
    assert len(free) == 16
    expanded = expand(variables, particular, basis)
    assert expanded[PERIOD_A] == 0
    assert np.array_equal(expanded, true_key)


def test_candidate_identity_is_expanded_key_and_payload_replays() -> None:
    _true_key, _crib, _ciphertext, particular, basis, _free, variables = _linear_fixture()
    record = candidate_record(
        variables,
        1.25,
        particular,
        basis,
        source="coordinate_discovery",
        operation="coordinate_descent",
        evaluation_index=12,
    )
    payload = record.to_json_dict()
    assert payload["identity"] == {"expanded_key": payload["payload"]["expanded_key"]}
    assert record.candidate_id == candidate_id_for(payload["identity"])
    assert expand(
        np.asarray(payload["payload"]["variables"], dtype=np.uint8), particular, basis
    ).tolist() == payload["payload"]["expanded_key"]


def test_discovery_evidence_is_deterministic_and_reports_collapse() -> None:
    _true_key, _crib, _ciphertext, particular, basis, _free, variables = _linear_fixture()
    evaluate = _target_evaluator(variables)
    first, first_evals, first_evidence = discover_archive(
        evaluate, particular, basis, _budget()
    )
    second, second_evals, second_evidence = discover_archive(
        evaluate, particular, basis, _budget()
    )
    assert first_evals == second_evals
    assert first_evidence == second_evidence
    assert first_evidence.generated_candidates == 4
    assert 1 <= first_evidence.unique_candidates <= 4
    assert first_evidence.retained_candidates == len(first.records)
    assert first_evidence.score_distribution == tuple(
        sorted(first_evidence.score_distribution, reverse=True)
    )


def test_paired_run_persists_both_final_arms_and_terminal_best(tmp_path: Path) -> None:
    _true_key, _crib, _ciphertext, particular, basis, _free, variables = _linear_fixture()
    stages: list[str] = []
    outcome = run_search(
        _target_evaluator(variables),
        particular,
        basis,
        _budget(),
        progress=lambda label, _metrics: stages.append(label),
    )
    assert len(outcome.comparisons) == len(outcome.handoff_batch.candidates)
    assert len(outcome.control_archive.records) >= 1
    for index, row in enumerate(outcome.comparisons):
        assert row["matched_seed"] == comparison_seed(index)
        assert row["control_final_id"]
        assert outcome.control_archive.get(row["control_final_id"])
        assert row["archive_diagnostics"]["sa_proposals_attempted"] == 12
        assert row["control_diagnostics"]["sa_proposals_attempted"] == 12
    selected_archive = outcome.archive if outcome.best_arm == "archive" else outcome.control_archive
    assert selected_archive.get(outcome.best_candidate_id)

    names = write_search_artifacts(tmp_path, outcome)
    assert set(names) == {
        "coordinate_archive",
        "archive_handoff_batch",
        "control_start_batch",
        "final_archive",
        "control_final_archive",
    }
    best_path = names["final_archive" if outcome.best_arm == "archive" else "control_final_archive"]
    restored_best = read_candidate_archive(tmp_path / best_path)
    assert restored_best.get(outcome.best_candidate_id)
    handoff = read_candidate_batch(tmp_path / names["archive_handoff_batch"])
    assert handoff.selection_label == "coordinate_to_sa"


def test_full_decision_refines_when_candidate_supply_is_underpowered() -> None:
    summary = {
        "underpowered": True,
        "archive_wins": 1,
        "control_wins": 0,
        "archive_best_final_score": 2.0,
        "control_best_final_score": 1.0,
    }
    assert campaign_decision(summary, "full") == "refine"
    assert campaign_decision({**summary, "underpowered": False}, "full") == "promote"


def test_comparison_summary_exposes_requested_actual_and_minimum() -> None:
    _true_key, _crib, _ciphertext, particular, basis, _free, variables = _linear_fixture()
    outcome = run_search(
        _target_evaluator(variables), particular, basis,
        _budget(handoff_candidates=2, minimum_comparisons=2),
    )
    summary = comparison_summary(outcome)
    assert summary["requested_comparisons"] == 2
    assert summary["minimum_comparisons"] == 2
    assert summary["comparison_count"] == len(outcome.comparisons)
    assert summary["underpowered"] is (len(outcome.comparisons) < 2)


def test_coordinate_polish_gain_uses_pre_polish_best(monkeypatch: pytest.MonkeyPatch) -> None:
    import cipher_development.two_period_overlay.keyspace as keyspace

    class FakeRng:
        def integers(self, low, high=None):
            if high is None:
                return 0
            return 0 if high == 1 else 1

        def random(self):
            return 0.0

    monkeypatch.setattr(keyspace.np.random, "default_rng", lambda _seed: FakeRng())
    monkeypatch.setattr(
        keyspace,
        "coordinate_search",
        lambda evaluate, rng, variables, sweeps, deadline=None: (
            np.asarray([0], dtype=np.uint8), 2.0, 1
        ),
    )

    def evaluate(values):
        return -np.asarray(values, dtype=float).sum(axis=1)

    _best, _score_value, diagnostics = anneal_and_polish(
        evaluate,
        np.asarray([0], dtype=np.uint8),
        _budget(coordinate_restarts=1, coordinate_sweeps=1, handoff_candidates=1,
                minimum_comparisons=1, sa_steps=1, sa_cycles=1, sa_t0=1.0, sa_tmin=1.0),
        seed=7,
    )
    assert diagnostics["coordinate_polish_gain"] == 2.0


def test_wallclock_guard_stops_before_new_evaluation() -> None:
    with pytest.raises(CampaignWallclockExceeded):
        coordinate_search(
            lambda values: np.zeros(len(values)),
            np.random.default_rng(1),
            np.zeros(2, dtype=np.uint8),
            1,
            deadline=0.0,
        )


def test_search_case_has_no_truth_fields() -> None:
    assert set(SearchCase.__dataclass_fields__).isdisjoint({
        "plaintext", "true_key", "expected_plaintext", "reference", "truth",
    })
    assert {"plaintext", "true_key"}.issubset(ReferenceCase.__dataclass_fields__)


def test_baseline_import_is_strict_and_separates_reference(tmp_path: Path) -> None:
    payload = _baseline_payload()
    result_source = (tmp_path / "sensitive" / "latest_result.json").resolve()
    runner_source = (tmp_path / "sensitive" / "two_period_crib_solver_runner.py").resolve()
    summary, reference = normalise_baseline_result(
        payload, "a" * 64, str(result_source),
        "b" * 64, str(runner_source),
    )
    assert summary["source_filename"] == "latest_result.json"
    assert summary["runner_filename"] == "two_period_crib_solver_runner.py"
    assert str(result_source.parent) not in json.dumps(summary)
    assert "exact_plaintext" not in summary
    assert set(reference) == {
        "exact_plaintext", "rune_matches", "complete_word_matches",
        "complete_words_total", "canonical_key_equal", "combined_shift_equal",
    }

    for mutation, match in (
        (("status", "failed"), "completed status"),
        (("config.schedule", "alternating"), "schedule"),
        (("config.gauge", None), "gauge"),
        (("config.scoring.n_char", 3), "n_char"),
        (("phases", {"coordinate": {}}), "three historical phases"),
    ):
        broken = _baseline_payload()
        path, value = mutation
        target = broken
        parts = path.split(".")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
        with pytest.raises(ValueError, match=match):
            normalise_baseline_result(broken, "a" * 64, "result.json", "b" * 64, "runner.py")


def test_baseline_path_is_resolved_from_repo_root(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    assert _resolve_source_path(root, Path("sources/result.json")) == root / "sources/result.json"
    absolute = (tmp_path / "external" / "result.json").resolve()
    assert _resolve_source_path(root, absolute) == absolute


def test_real_rdp_benchmark_builds_and_scores_known_key() -> None:
    pytest.importorskip("rune_decrypter_prime")
    search_case, reference = build_rdp_case()
    variables = np.asarray(
        [reference.true_key[index] for index in search_case.free_columns], dtype=np.uint8
    )
    scores = search_case.evaluate_variables(variables[None, :])
    assert search_case.sample_start >= 0
    assert len(search_case.ciphertext) == TEXT_LENGTH
    assert search_case.wli[CRIB_START: CRIB_START + len(CRIB_RUNES)] == tuple(
        (i, len(CRIB_RUNES)) for i in range(len(CRIB_RUNES))
    )
    assert scores.shape == (1,)
    assert np.isfinite(scores[0])


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
