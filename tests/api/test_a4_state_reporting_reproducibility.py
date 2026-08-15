from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import SimpleNamespace

import pytest

from rune_decrypter_prime.api.run import (
    _build_reproducibility_metadata,
    _portable_json_value,
    _scoring_report_summaries,
)
from rune_decrypter_prime.api.solver_report import (
    OracleMode,
    OracleReport,
    ReproducibilityMetadata,
    RequestedEffectiveConfig,
    RunConfigurationReport,
    build_solver_report,
)
from rune_decrypter_prime.api.stop_reason_contract import (
    RUN_STATUS_SCHEMA,
    CanonicalStopReason,
    ExecutionStatus,
    RecoveryStatus,
    RunStatus,
    StopCategory,
    build_run_status,
    canonical_stop_reason_for_legacy,
)
from rune_decrypter_prime.core.config import logging_config
from rune_decrypter_prime.core.config.logging_config import LoggingConfig


@pytest.mark.parametrize(
    ("legacy", "canonical", "category"),
    [
        ("done", CanonicalStopReason.UNKNOWN_RUNTIME_REASON, StopCategory.ERROR),
        ("success", CanonicalStopReason.UNKNOWN_RUNTIME_REASON, StopCategory.ERROR),
        ("target_score", CanonicalStopReason.TARGET_SCORE_REACHED, StopCategory.SUCCESS),
        ("max_evals", CanonicalStopReason.MAX_EVALUATIONS_REACHED, StopCategory.BUDGET),
        ("max_time", CanonicalStopReason.MAX_TIME_REACHED, StopCategory.BUDGET),
        ("budget", CanonicalStopReason.CONFIGURED_WORK_LIMIT_REACHED, StopCategory.BUDGET),
        ("patience", CanonicalStopReason.NO_IMPROVEMENT_BUDGET_REACHED, StopCategory.BUDGET),
        ("no_improve_24", CanonicalStopReason.NO_IMPROVEMENT_BUDGET_REACHED, StopCategory.BUDGET),
        ("max_rounds_reached", CanonicalStopReason.MAX_ROUNDS_REACHED, StopCategory.BUDGET),
        ("max_generations_reached", CanonicalStopReason.MAX_GENERATIONS_REACHED, StopCategory.BUDGET),
        ("max_iterations_reached", CanonicalStopReason.MAX_ITERATIONS_REACHED, StopCategory.BUDGET),
        ("max_steps_reached", CanonicalStopReason.MAX_STEPS_REACHED, StopCategory.BUDGET),
        ("test_key", CanonicalStopReason.ORACLE_TEST_KEY_USED, StopCategory.SUCCESS),
        ("blocked_before_run", CanonicalStopReason.BLOCKED_BEFORE_RUN, StopCategory.BLOCKED_BEFORE_RUN),
        (
            "all_rejected_by_hard_crib",
            CanonicalStopReason.ALL_CANDIDATES_REJECTED_BY_HARD_CRIB,
            StopCategory.BLOCKED_BEFORE_RUN,
        ),
    ],
)
def test_legacy_stop_reasons_map_to_typed_canonical_contract(
    legacy: str,
    canonical: CanonicalStopReason,
    category: StopCategory,
) -> None:
    assert canonical_stop_reason_for_legacy(legacy) is canonical
    execution_status = {
        StopCategory.BLOCKED_BEFORE_RUN: ExecutionStatus.BLOCKED_BEFORE_RUN,
        StopCategory.ERROR: ExecutionStatus.COMPLETED,
    }.get(category, ExecutionStatus.COMPLETED)
    status = build_run_status(legacy_reason=legacy, execution_status=execution_status)
    assert status.stop_reason is canonical
    assert status.stop_category is category
    assert status.recovery_status is RecoveryStatus.NOT_ASSESSED
    assert status.to_json_dict()["recovery"]["assessed"] is False


def test_completed_execution_without_a_producer_reason_is_not_silently_successful() -> None:
    status = build_run_status(legacy_reason=None, execution_status=ExecutionStatus.COMPLETED)
    assert status.execution_status is ExecutionStatus.COMPLETED
    assert status.stop_category is StopCategory.ERROR
    assert status.stop_reason is CanonicalStopReason.UNKNOWN_RUNTIME_REASON


def test_recovery_contract_rejects_inconsistent_typed_states() -> None:
    with pytest.raises(ValueError, match="not_assessed"):
        RunStatus(
            execution_status=ExecutionStatus.COMPLETED,
            stop_category=StopCategory.BUDGET,
            stop_reason=CanonicalStopReason.MAX_STEPS_REACHED,
            recovery_match_ratio=1.0,
        )
    with pytest.raises(ValueError, match="requires recovery_basis"):
        RunStatus(
            execution_status=ExecutionStatus.COMPLETED,
            stop_category=StopCategory.BUDGET,
            stop_reason=CanonicalStopReason.MAX_STEPS_REACHED,
            recovery_status=RecoveryStatus.EXACT,
            recovery_match_ratio=1.0,
        )
    with pytest.raises(ValueError, match="exact recovery"):
        RunStatus(
            execution_status=ExecutionStatus.COMPLETED,
            stop_category=StopCategory.BUDGET,
            stop_reason=CanonicalStopReason.MAX_STEPS_REACHED,
            recovery_status=RecoveryStatus.EXACT,
            recovery_match_ratio=0.9,
            recovery_basis="known_plaintext",
        )


def test_solver_report_reuses_june_run_status_contract_and_keeps_legacy_reason() -> None:
    status = build_run_status(
        legacy_reason="max_rounds_reached",
        execution_status=ExecutionStatus.COMPLETED,
    )
    config = RunConfigurationReport(
        solver=RequestedEffectiveConfig(
            requested={"name": "beam", "params": {"beam_width": 4}},
            effective={"name": "beam", "params": {"beam_width": 4, "plateau_rounds": 16}},
        ),
        scoring=RequestedEffectiveConfig(),
        cipher=RequestedEffectiveConfig(),
    )
    report = build_solver_report(
        solver_name="beam",
        requested_seed=None,
        effective_seed=0,
        normalized_params={"beam_width": 4},
        stop_reason="max_rounds_reached",
        run_status=status,
        configuration=config,
    )
    payload = report.to_json_dict()
    run_status = payload["details"]["run_status"]
    assert payload["stop_reason"] == "max_rounds_reached"
    assert run_status["schema"] == RUN_STATUS_SCHEMA
    assert run_status["execution_status"] == "completed"
    assert run_status["stop_category"] == "budget"
    assert run_status["stop_reason"] == "max_rounds_reached"
    assert run_status["legacy_stop_reason"] == "max_rounds_reached"
    assert run_status["oracle"] == payload["details"]["oracle"]
    assert run_status["reproducibility"] == payload["details"]["reproducibility"]
    assert "plateau_rounds" not in payload["details"]["configuration"]["solver"]["requested"]["params"]
    assert payload["details"]["configuration"]["solver"]["effective"]["params"]["plateau_rounds"] == 16


def test_test_key_oracle_contract_reports_stop_use_not_scoring_or_ranking() -> None:
    report = build_solver_report(
        solver_name="beam",
        requested_seed=1,
        effective_seed=1,
        normalized_params={"test_key": [1, 2]},
        stop_reason="test_key",
    )
    oracle = report.to_json_dict()["details"]["oracle"]
    assert oracle == {
        "available": True,
        "used_for_scoring": False,
        "used_for_ranking": False,
        "used_for_stop": True,
        "stop_reason": "oracle_test_key_used",
        "mode": "test",
    }


def test_oracle_report_rejects_impossible_combinations() -> None:
    with pytest.raises(ValueError, match="available=True"):
        OracleReport(used_for_stop=True, stop_reason="target", mode=OracleMode.TEST)
    with pytest.raises(ValueError, match="requires stop_reason"):
        OracleReport(available=True, used_for_stop=True, mode=OracleMode.TEST)
    with pytest.raises(ValueError, match="only valid"):
        OracleReport(available=True, stop_reason="target", mode=OracleMode.TEST)


def test_known_key_execution_preserves_explicit_v1_truth_reporting_contract() -> None:
    status = RunStatus(
        execution_status=ExecutionStatus.COMPLETED,
        stop_category=StopCategory.SUCCESS,
        stop_reason=CanonicalStopReason.KNOWN_KEY_EXECUTION_COMPLETED,
        legacy_reason="test_key",
    )
    report = build_solver_report(
        solver_name="beam",
        requested_seed=None,
        effective_seed=None,
        normalized_params={"beam_width": 1},
        stop_reason="test_key",
        details={"execution_route": "known_key_fastpath"},
        run_status=status,
    )
    payload = report.to_json_dict()["details"]
    assert payload["oracle_use"] == "known_key_fastpath"  # compatibility breadcrumb
    assert payload["truth_data_policy"] == "reported_test_or_tutorial_only"
    assert payload["run_status"]["stop_reason"] == "known_key_execution_completed"
    assert payload["oracle"] == OracleReport(
        available=True,
        used_for_scoring=False,
        used_for_ranking=False,
        used_for_stop=True,
        stop_reason="known_key_execution_completed",
        mode=OracleMode.UNKNOWN,
    ).to_json_dict()



def test_reproducibility_stop_fields_must_agree() -> None:
    with pytest.raises(ValueError, match="stop_category must match stop_reason"):
        ReproducibilityMetadata(
            stop_category=StopCategory.SUCCESS,
            stop_reason=CanonicalStopReason.MAX_STEPS_REACHED,
        )

def test_reproducibility_payload_contains_every_june_contract_field() -> None:
    status = build_run_status(
        legacy_reason="max_steps_reached",
        execution_status=ExecutionStatus.COMPLETED,
    )
    repro = ReproducibilityMetadata(
        run_id="run-1",
        created_at_utc="2026-08-11T00:00:00Z",
        git_branch="prelease/v1.0.0._h",
        git_commit="abc123",
        backend="numpy",
        device="cpu",
        dtype="float64",
        seed=4,
        stochastic=True,
        solver_config={"requested": {}, "effective": {}},
        scoring_config={"requested": {}, "effective": {}},
        objective={"family": "pct", "stat": "logp", "win": 10},
        cipher={"name": "vigenere"},
        asset_ids=None,
        asset_hashes=None,
        dictionary_policy="not_applicable",
        stop_category=status.stop_category,
        stop_reason=status.stop_reason,
    )
    payload = repro.to_json_dict()
    expected = {
        "run_id", "created_at_utc", "rdp_version", "git_branch", "git_commit",
        "python_version", "backend", "device", "dtype", "seed", "stochastic",
        "solver_config", "scoring_config", "objective", "cipher", "asset_ids",
        "asset_hashes", "dictionary_policy", "stop_category", "stop_reason",
    }
    assert set(payload) == expected
    json.dumps(payload)




def test_specialised_route_reuses_existing_profile_metadata_for_effective_scoring() -> None:
    solution = SimpleNamespace(
        meta={
            "two_period_solve": {
                "profiles": {
                    "S2": {"contract_hash": "s2", "role": "scout", "sweeps": 5}
                }
            }
        }
    )
    requested, effective = _scoring_report_summaries(None, {}, solution)
    assert requested == {}
    assert effective["profiles"]["S2"]["contract_hash"] == "s2"

def test_missing_runtime_timestamp_stays_null_instead_of_being_guessed() -> None:
    status = build_run_status(
        legacy_reason="max_rounds_reached",
        execution_status=ExecutionStatus.COMPLETED,
    )
    empty = RequestedEffectiveConfig()
    configuration = RunConfigurationReport(solver=empty, scoring=empty, cipher=empty)
    repro = _build_reproducibility_metadata(
        solution=SimpleNamespace(meta={}, device=None, stop_reason="max_rounds_reached"),
        run_status=status,
        configuration=configuration,
        scoring_cfg=None,
        effective_seed=0,
        known_key_fastpath=False,
        initialize_logging=False,
    )
    assert repro.created_at_utc is None

def test_external_logging_paths_are_labelled_not_serialised(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external = tmp_path / "private" / "elsewhere"
    cfg = LoggingConfig(
        repo_root=str(repo_root),
        out_root=str(external),
        run_kind="tests",
        label="portable",
        portable_output=True,
    )
    previous = logging_config.current_paths()
    try:
        run_dir = logging_config.init_logging(cfg)
        meta = json.loads((run_dir / "META.json").read_text(encoding="utf-8"))
        snapshot = json.loads((run_dir / "config" / "logging.json").read_text(encoding="utf-8"))
        assert meta["out_root"] == "<external:out_root>"
        assert snapshot["out_root"] == "<external:out_root>"
        assert isinstance(meta["created_at_utc"], str)
        assert meta["pointers"] == {"logs": "logs", "trace": "trace", "artifacts": "artifacts"}
        serialised = json.dumps({"meta": meta, "snapshot": snapshot})
        assert str(external) not in serialised
        assert "../" not in meta["out_root"]
    finally:
        logging_config._PATHS.clear()
        logging_config._PATHS.update(previous)


def test_portable_report_values_redact_absolute_and_parent_paths() -> None:
    posix_private = str(PurePosixPath("/", "home", "alice", "private", "model.bin"))
    windows_root = f"{chr(67)}:{chr(92)}"
    windows_private = str(PureWindowsPath(windows_root, "Users", "alice", "private", "model.bin"))
    unc_root = (chr(92) * 2) + "server" + chr(92) + "share"
    unc_private = str(PureWindowsPath(unc_root, "private", "model.bin"))
    parent_private = str(PurePosixPath("..", "private", "model.bin"))
    path_object = Path(PurePosixPath("/", "tmp", "private", "object.bin"))

    payload = _portable_json_value(
        {
            "posix": posix_private,
            "windows": windows_private,
            "unc": unc_private,
            "parent": parent_private,
            "label": "normal-model-id",
            "path_object": path_object,
        },
        field_name="report",
    )
    assert payload["label"] == "normal-model-id"
    for key in ("posix", "windows", "unc", "parent", "path_object"):
        assert str(payload[key]).startswith("<external:")
    serialised = json.dumps(payload)
    assert str(PurePosixPath("/", "home", "alice")) not in serialised
    assert windows_root[:2] not in serialised
    assert "server" not in serialised
    assert parent_private not in serialised


def test_manual_and_error_execution_states_remain_distinct() -> None:
    manual = build_run_status(
        legacy_reason="interrupted",
        execution_status=ExecutionStatus.MANUAL_STOP,
    )
    assert manual.stop_category is StopCategory.MANUAL
    assert manual.stop_reason is CanonicalStopReason.MANUAL_STOP

    error = build_run_status(
        legacy_reason="exception",
        execution_status=ExecutionStatus.ERROR,
        error_type="RuntimeError",
        stop_detail="boom",
    )
    assert error.stop_category is StopCategory.ERROR
    assert error.stop_reason is CanonicalStopReason.UNEXPECTED_EXCEPTION
    assert error.error_type == "RuntimeError"
