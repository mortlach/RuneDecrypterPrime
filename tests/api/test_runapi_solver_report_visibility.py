from __future__ import annotations

import dataclasses
import importlib

import numpy as np

from rune_decrypter_prime.api import (
    CipherSpec,
    KeySpec,
    RawTextInput,
    RunAPI,
    RunResult,
    SolverSpec,
    define_cipher,
    define_map,
)
from rune_decrypter_prime.api.run_spec import RunSpec
from rune_decrypter_prime.api.solver_report import SolverReport
from rune_decrypter_prime.core.config.solution import Solution
from rune_decrypter_prime.core.types import Device, Direction, SolverName


def _solution(**overrides) -> Solution:
    solution = Solution(key=[1, 2], plaintext=[0, 1], score=3.5)
    solution.stop_reason = "direct_stop"
    solution.step = 4
    solution.evals = 5
    solution.tokens_processed = 6
    solution.wall_time_s = 0.7
    solution.decrypt_time_s = 0.2
    solution.score_time_s = 0.5
    solution.meta = {
        "stop_reason": "meta_stop",
        "telemetry": {
            "run": {
                "result": {"score": -999.0, "reason": "telemetry_stop"},
                "seed": 999,
            }
        },
    }
    for key, value in overrides.items():
        setattr(solution, key, value)
    return solution


def _minimal_spec() -> RunSpec:
    return RunSpec(
        problem_input=RawTextInput("abc"),
        cipher=CipherSpec.periodic_substitution(period=1),
        key=KeySpec.repeat(len=1),
        solver=SolverSpec.beam(beam_width=2, seed=7),
        telemetry_on=False,
    )


def _patch_execute_run(monkeypatch, solution):
    run_module = importlib.import_module("rune_decrypter_prime.api.run")
    calls = []

    def fake_execute_run(**kwargs):
        calls.append(kwargs)
        return solution

    monkeypatch.setattr(run_module, "execute_run", fake_execute_run)
    return calls


def test_default_non_spec_runapi_return_shape_stays_solution(monkeypatch) -> None:
    solution = _solution()
    _patch_execute_run(monkeypatch, solution)

    result = RunAPI.run(
        text=[0],
        cipher=CipherSpec.periodic_substitution(period=1),
        key=KeySpec.repeat(len=1),
        solver=SolverSpec.beam(beam_width=2, seed=7),
        telemetry_on=False,
    )

    assert result is solution


def test_default_spec_runapi_return_shape_stays_solution(monkeypatch) -> None:
    solution = _solution()
    _patch_execute_run(monkeypatch, solution)

    result = RunAPI.run(spec=_minimal_spec())

    assert result is solution


def test_non_spec_return_solver_report_returns_run_result(monkeypatch) -> None:
    solution = _solution()
    _patch_execute_run(monkeypatch, solution)

    result = RunAPI.run(
        text=[0],
        cipher=CipherSpec.periodic_substitution(period=1),
        key=KeySpec.repeat(len=1),
        solver=SolverSpec.beam(beam_width=2, seed=7),
        telemetry_on=False,
        return_solver_report=True,
    )

    assert isinstance(result, RunResult)
    assert result.solution is solution
    assert isinstance(result.solver_report, SolverReport)
    assert result.solver_report.solver_name == "beam"
    assert result.solver_report.requested_seed == 7
    assert result.solver_report.effective_seed == 7
    assert result.solver_report.normalized_params == {"beam_width": 2}


def test_spec_return_solver_report_returns_run_result(monkeypatch) -> None:
    solution = _solution()
    _patch_execute_run(monkeypatch, solution)

    result = RunAPI.run(spec=_minimal_spec(), return_solver_report=True)

    assert isinstance(result, RunResult)
    assert result.solution is solution
    assert result.solver_report.requested_seed == 7
    assert result.solver_report.effective_seed == 7


def test_ordinary_omitted_seed_reports_effective_seed_zero(monkeypatch) -> None:
    solution = _solution()
    _patch_execute_run(monkeypatch, solution)

    result = RunAPI.run(
        text=[0],
        cipher=CipherSpec.periodic_substitution(period=1),
        key=KeySpec.repeat(len=1),
        solver=SolverSpec.beam(beam_width=2),
        telemetry_on=False,
        return_solver_report=True,
    )

    assert result.solver_report.requested_seed is None
    assert result.solver_report.effective_seed == 0


def test_return_solver_report_requires_exact_bool() -> None:
    try:
        RunAPI.run(
            text=[0],
            cipher=CipherSpec.periodic_substitution(period=1),
            key=KeySpec.repeat(len=1),
            solver=SolverSpec.beam(beam_width=2),
            telemetry_on=False,
            return_solver_report=1,
        )
    except TypeError:
        return
    raise AssertionError("return_solver_report=1 should be rejected")


def test_solver_name_passed_to_report_is_string_not_enum(monkeypatch) -> None:
    solution = _solution()
    _patch_execute_run(monkeypatch, solution)
    run_module = importlib.import_module("rune_decrypter_prime.api.run")
    captured = {}
    real_build = run_module.build_solver_report

    def capture_build_solver_report(**kwargs):
        captured["solver_name"] = kwargs["solver_name"]
        return real_build(**kwargs)

    monkeypatch.setattr(
        run_module,
        "normalize_optimizer_spec",
        lambda _spec: {"name": SolverName.BEAM, "beam_width": 2},
    )
    monkeypatch.setattr(run_module, "build_solver_report", capture_build_solver_report)

    RunAPI.run(
        text=[0],
        cipher=CipherSpec.periodic_substitution(period=1),
        key=KeySpec.repeat(len=1),
        solver=SolverSpec.beam(beam_width=2),
        telemetry_on=False,
        return_solver_report=True,
    )

    assert captured["solver_name"] == "beam"
    assert isinstance(captured["solver_name"], str)


def test_known_key_report_policy_excludes_test_key(monkeypatch) -> None:
    solution = _solution(key=[0])
    _patch_execute_run(monkeypatch, solution)

    result = RunAPI.run(
        text=[0],
        cipher=CipherSpec.periodic_substitution(period=1),
        key=KeySpec.const(value=0),
        solver=SolverSpec.beam(beam_width=99, seed=123),
        telemetry_on=False,
        return_solver_report=True,
    )

    report = result.solver_report
    assert report.solver_name == "beam"
    assert report.requested_seed == 123
    assert report.effective_seed is None
    assert report.normalized_params == {"beam_width": 1}
    assert "test_key" not in report.normalized_params
    assert report.details["execution_route"] == "known_key_fastpath"


def test_report_uses_direct_solution_fields_not_meta_or_telemetry(monkeypatch) -> None:
    solution = _solution(
        key=[8, 9],
        score=42.0,
        stop_reason="direct",
        step=10,
        evals=11,
        tokens_processed=12,
        wall_time_s=1.5,
        decrypt_time_s=0.6,
        score_time_s=0.9,
    )
    _patch_execute_run(monkeypatch, solution)

    result = RunAPI.run(
        text=[0],
        cipher=CipherSpec.periodic_substitution(period=1),
        key=KeySpec.repeat(len=1),
        solver=SolverSpec.beam(beam_width=2),
        telemetry_on=False,
        return_solver_report=True,
    )

    report_json = result.solver_report.to_json_dict()
    assert report_json["stop_reason"] == "direct"
    assert report_json["best_score"] == 42.0
    assert report_json["best_key"] == [8, 9]
    assert report_json["step"] == 10
    assert report_json["evals"] == 11
    assert report_json["tokens_processed"] == 12
    assert report_json["wall_time_s"] == 1.5
    assert report_json["decrypt_time_s"] == 0.6
    assert report_json["score_time_s"] == 0.9


def test_unrepresentable_solution_key_fails_when_report_requested(monkeypatch) -> None:
    solution = _solution(key={"not": "flat"})
    _patch_execute_run(monkeypatch, solution)

    try:
        RunAPI.run(
            text=[0],
            cipher=CipherSpec.periodic_substitution(period=1),
            key=KeySpec.repeat(len=1),
            solver=SolverSpec.beam(beam_width=2),
            telemetry_on=False,
            return_solver_report=True,
        )
    except TypeError:
        return
    raise AssertionError("unrepresentable Solution.key should fail report construction")


def test_runspec_does_not_grow_return_report_field() -> None:
    assert "return_solver_report" not in {field.name for field in dataclasses.fields(RunSpec)}


def test_real_known_key_run_returns_solver_report_with_report_compatible_key() -> None:
    xor_spec = define_map(
        function=lambda pt, k: (pt ^ k) % 29,
        name="unit_test_solver_report_xor_smoke",
        degeneracy="forbid",
        per_pos_limit=29,
        resolver_limit=8193,
    )
    xor_spec.name = None
    cipher_spec, key_spec = define_cipher(spec=xor_spec, key=KeySpec.const(value=7))
    plaintext = np.array([0, 1, 2, 3], dtype=np.uint8)
    ciphertext = (plaintext ^ 7) % 29

    result = RunAPI.run(
        text=ciphertext,
        cipher=cipher_spec,
        key=key_spec,
        solver=SolverSpec.beam(beam_width=1, seed=314, stop_score=0.1),
        encoding_dir=Direction.LTR,
        device=Device.CPU,
        telemetry_on=False,
        initial_keys=[[7]],
        return_solver_report=True,
    )

    report = result.solver_report
    assert isinstance(result, RunResult)
    assert result.solution is not None
    assert report.solver_name == "beam"
    assert report.requested_seed == 314
    assert report.effective_seed is None
    assert report.normalized_params == {"beam_width": 1}
    assert report.details["execution_route"] == "known_key_fastpath"
    assert "test_key" not in report.normalized_params
    assert report.best_key == tuple(int(value) for value in result.solution.key)
    assert report.to_json_dict()["best_key"] == [int(value) for value in result.solution.key]
