from __future__ import annotations

import math
from pathlib import Path

import pytest

from rune_decrypter_prime.api.run import RunAPI
from rune_decrypter_prime.api.solver_report import SolverReport, build_solver_report
from rune_decrypter_prime.core.config.solution import Solution


def test_build_solver_report_returns_solver_report() -> None:
    report = build_solver_report(
        solver_name="beam",
        requested_seed=123,
        effective_seed=123,
        normalized_params={"beam_width": 4},
        stop_reason="max_steps",
        best_score=10.5,
        best_key=[1, 2, 3],
        step=7,
        evals=8,
        tokens_processed=9,
        wall_time_s=0.5,
        decrypt_time_s=0.2,
        score_time_s=0.3,
        details={"route": "ordinary"},
    )

    assert isinstance(report, SolverReport)
    assert report.to_json_dict() == {
        "solver_name": "beam",
        "requested_seed": 123,
        "effective_seed": 123,
        "normalized_params": {"beam_width": 4},
        "stop_reason": "max_steps",
        "best_score": 10.5,
        "best_key": [1, 2, 3],
        "step": 7,
        "evals": 8,
        "tokens_processed": 9,
        "wall_time_s": 0.5,
        "decrypt_time_s": 0.2,
        "score_time_s": 0.3,
        "details": {
            "route": "ordinary",
            "report_contract": {"version": "api_solver_report_details.v1"},
            "oracle_use": "none",
            "truth_data_policy": "none",
            "reproducibility": {
                "deterministic_seed_policy": "explicit_or_default_zero",
                "requested_seed": 123,
                "effective_seed": 123,
                "solver_name": "beam",
            },
        },
    }


def test_build_solver_report_passes_seeds_unchanged() -> None:
    report = build_solver_report(
        solver_name="beam",
        requested_seed=None,
        effective_seed=0,
        normalized_params={"beam_width": 1},
    )

    assert report.requested_seed is None
    assert report.effective_seed == 0


def test_build_solver_report_allows_known_key_style_effective_seed_none() -> None:
    report = build_solver_report(
        solver_name="beam",
        requested_seed=None,
        effective_seed=None,
        normalized_params={"beam_width": 1, "test_key": [0, 1]},
    )

    assert report.effective_seed is None


def test_build_solver_report_passes_normalized_params_through_copy_validation() -> None:
    params = {"beam_width": 4, "nested": {"weights": [1, 2]}}
    report = build_solver_report(
        solver_name="beam",
        requested_seed=1,
        effective_seed=1,
        normalized_params=params,
    )
    params["nested"]["weights"].append(3)

    assert report.normalized_params["nested"]["weights"] == (1, 2)
    assert report.to_json_dict()["normalized_params"] == {
        "beam_width": 4,
        "nested": {"weights": [1, 2]},
    }


def test_build_solver_report_rejects_name_in_normalized_params() -> None:
    with pytest.raises(ValueError):
        build_solver_report(
            solver_name="beam",
            requested_seed=1,
            effective_seed=1,
            normalized_params={"name": "beam", "beam_width": 4},
        )


def test_build_solver_report_rejects_path_in_normalized_params() -> None:
    with pytest.raises(TypeError):
        build_solver_report(
            solver_name="beam",
            requested_seed=1,
            effective_seed=1,
            normalized_params={"artifact": Path("out/report.json")},
        )


def test_build_solver_report_rejects_non_string_normalized_params_key() -> None:
    with pytest.raises(TypeError):
        build_solver_report(
            solver_name="beam",
            requested_seed=1,
            effective_seed=1,
            normalized_params={1: "bad"},
        )


def test_build_solver_report_rejects_non_finite_float_in_details() -> None:
    with pytest.raises(ValueError):
        build_solver_report(
            solver_name="beam",
            requested_seed=1,
            effective_seed=1,
            normalized_params={"beam_width": 4},
            details={"bad": math.inf},
        )


def test_build_solver_report_best_key_uses_solver_report_validation() -> None:
    with pytest.raises(TypeError):
        build_solver_report(
            solver_name="beam",
            requested_seed=1,
            effective_seed=1,
            normalized_params={"beam_width": 4},
            best_key=[1, True],
        )


def test_build_solver_report_does_not_accept_solution_positional_shortcut() -> None:
    solution = Solution(key=[1], plaintext=[0], score=1.0)

    with pytest.raises(TypeError):
        build_solver_report(solution)  # type: ignore[misc]


def test_runapi_run_still_does_not_return_solver_report() -> None:
    assert "solver_report" not in RunAPI.run.__annotations__
