from __future__ import annotations

import math
from pathlib import Path

import pytest

from rune_decrypter_prime.api import SolverReport as ExportedSolverReport
from rune_decrypter_prime.api.solver_report import SolverReport


def test_constructs_minimal_solver_report() -> None:
    report = SolverReport(solver_name="beam")

    assert report.solver_name == "beam"
    assert report.requested_seed is None
    assert report.effective_seed is None
    assert report.normalized_params == {}
    assert report.details == {}


def test_to_json_dict_returns_json_safe_compact_shape() -> None:
    report = SolverReport(
        solver_name="beam",
        requested_seed=None,
        effective_seed=0,
        normalized_params={"beam_width": 4, "flags": ["fast", True], "nested": {"alpha": 1.5}},
        stop_reason="max_steps",
        best_score=12.5,
        best_key=[3, 1, 4],
        step=9,
        evals=10,
        tokens_processed=11,
        wall_time_s=0.25,
        decrypt_time_s=0.1,
        score_time_s=0.15,
        details={"notes": ("ok", None)},
    )

    assert report.to_json_dict() == {
        "solver_name": "beam",
        "requested_seed": None,
        "effective_seed": 0,
        "normalized_params": {
            "beam_width": 4,
            "flags": ["fast", True],
            "nested": {"alpha": 1.5},
        },
        "stop_reason": "max_steps",
        "best_score": 12.5,
        "best_key": [3, 1, 4],
        "step": 9,
        "evals": 10,
        "tokens_processed": 11,
        "wall_time_s": 0.25,
        "decrypt_time_s": 0.1,
        "score_time_s": 0.15,
        "details": {"notes": ["ok", None]},
    }


def test_requested_seed_and_effective_seed_can_differ() -> None:
    report = SolverReport(solver_name="beam", requested_seed=None, effective_seed=0)

    assert report.requested_seed is None
    assert report.effective_seed == 0


def test_known_key_like_effective_seed_none_is_allowed() -> None:
    report = SolverReport(solver_name="known_key", requested_seed=None, effective_seed=None)

    assert report.effective_seed is None


def test_best_key_is_copied_and_serializes_as_list() -> None:
    key = [1, 2, 3]
    report = SolverReport(solver_name="beam", best_key=key)
    key.append(4)

    assert report.best_key == (1, 2, 3)
    assert report.to_json_dict()["best_key"] == [1, 2, 3]


@pytest.mark.parametrize("best_key", [[1, True], [1, "2"]])
def test_best_key_rejects_bool_and_non_int_entries(best_key) -> None:
    with pytest.raises(TypeError):
        SolverReport(solver_name="beam", best_key=best_key)


def test_normalized_params_rejects_path_values() -> None:
    with pytest.raises(TypeError):
        SolverReport(solver_name="beam", normalized_params={"artifact": Path("out/result.json")})


def test_normalized_params_rejects_path_keys() -> None:
    with pytest.raises(TypeError):
        SolverReport(solver_name="beam", normalized_params={Path("key"): "value"})


def test_normalized_params_rejects_arbitrary_object_values() -> None:
    with pytest.raises(TypeError):
        SolverReport(solver_name="beam", normalized_params={"value": object()})


def test_normalized_params_rejects_non_string_mapping_keys() -> None:
    with pytest.raises(TypeError):
        SolverReport(solver_name="beam", normalized_params={1: "value"})


def test_details_uses_same_json_path_policy() -> None:
    with pytest.raises(TypeError):
        SolverReport(solver_name="beam", details={"nested": {"artifact": Path("out/result.json")}})


@pytest.mark.parametrize("best_score", [math.nan, math.inf, -math.inf])
def test_best_score_rejects_nan_and_inf(best_score) -> None:
    with pytest.raises(ValueError):
        SolverReport(solver_name="beam", best_score=best_score)


def test_best_score_rejects_numeric_string() -> None:
    with pytest.raises(TypeError):
        SolverReport(solver_name="beam", best_score="1.0")


@pytest.mark.parametrize("field_name", ["wall_time_s", "decrypt_time_s", "score_time_s"])
def test_timing_fields_reject_nan_and_inf(field_name) -> None:
    with pytest.raises(ValueError):
        SolverReport(solver_name="beam", **{field_name: math.inf})


def test_counter_fields_reject_bool() -> None:
    with pytest.raises(TypeError):
        SolverReport(solver_name="beam", step=True)


def test_caller_owned_mappings_and_sequences_are_copied() -> None:
    params = {"items": [1, {"name": "alpha"}]}
    details = {"trail": ["start"]}
    report = SolverReport(
        solver_name="beam",
        normalized_params=params,
        details=details,
        best_key=[1, 2],
    )

    params["items"].append(2)
    details["trail"].append("end")

    assert report.normalized_params["items"] == (1, {"name": "alpha"})
    assert report.details["trail"] == ("start",)
    assert report.to_json_dict()["normalized_params"]["items"] == [1, {"name": "alpha"}]
    with pytest.raises(TypeError):
        report.normalized_params["new"] = "value"


def test_solver_report_is_exported_from_api_package() -> None:
    assert ExportedSolverReport is SolverReport


@pytest.mark.parametrize("solver_name", ["", Path("solver")])
def test_solver_name_must_be_non_empty_string(solver_name) -> None:
    with pytest.raises((TypeError, ValueError)):
        SolverReport(solver_name=solver_name)


def test_stop_reason_rejects_empty_string() -> None:
    with pytest.raises(ValueError):
        SolverReport(solver_name="beam", stop_reason="")
