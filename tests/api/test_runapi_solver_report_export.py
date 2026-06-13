from __future__ import annotations

import json
import os
import importlib
from pathlib import Path

import pytest

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
from rune_decrypter_prime.core.types import Device, Direction
from rune_decrypter_prime.api.run_spec import RunSpec
from rune_decrypter_prime.core.config.logging_config import LoggingConfig
from rune_decrypter_prime.core.config.solution import Solution


def _solution(**overrides) -> Solution:
    solution = Solution(key=[1, 2], plaintext=[0, 1], score=3.5)
    solution.stop_reason = "direct_stop"
    solution.step = 4
    solution.evals = 5
    solution.tokens_processed = 6
    solution.wall_time_s = 0.7
    solution.decrypt_time_s = 0.2
    solution.score_time_s = 0.5
    for key, value in overrides.items():
        setattr(solution, key, value)
    return solution


def _minimal_spec(*, logging=None) -> RunSpec:
    return RunSpec(
        problem_input=RawTextInput("abc"),
        cipher=CipherSpec.periodic_substitution(period=1),
        key=KeySpec.repeat(len=1),
        solver=SolverSpec.beam(beam_width=2, seed=7),
        logging=logging,
        telemetry_on=False,
    )


def _run_with_fake_execute(monkeypatch, tmp_path: Path, *, solution: Solution | None = None):
    run_module = importlib.import_module("rune_decrypter_prime.api.run")
    captured = {"execute": []}

    def fake_execute_run(**kwargs):
        captured["execute"].append(kwargs)
        return solution or _solution()

    monkeypatch.setattr(run_module, "execute_run", fake_execute_run)
    monkeypatch.setattr(run_module.logging_state, "get_run_dir", lambda: tmp_path)
    return captured


def _base_kwargs(**overrides):
    kwargs = {
        "text": [0],
        "cipher": CipherSpec.periodic_substitution(period=1),
        "key": KeySpec.repeat(len=1),
        "solver": SolverSpec.beam(beam_width=2, seed=7),
        "telemetry_on": False,
    }
    kwargs.update(overrides)
    return kwargs


def test_default_runapi_writes_no_solver_report_sidecar(monkeypatch, tmp_path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)

    result = RunAPI.run(**_base_kwargs())

    assert isinstance(result, Solution)
    assert not (tmp_path / "artifacts" / "solver_report.json").exists()


def test_return_solver_report_alone_writes_no_sidecar(monkeypatch, tmp_path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)

    result = RunAPI.run(**_base_kwargs(return_solver_report=True))

    assert isinstance(result, RunResult)
    assert not (tmp_path / "artifacts" / "solver_report.json").exists()


def test_logging_config_write_solver_report_writes_artifact(monkeypatch, tmp_path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)

    result = RunAPI.run(
        **_base_kwargs(
            logging=LoggingConfig(write_jsonl=False, write_solver_report=True),
        )
    )

    report_path = tmp_path / "artifacts" / "solver_report.json"
    assert isinstance(result, Solution)
    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["solver_name"] == "beam"
    assert payload["best_key"] == [1, 2]


def test_logging_dict_write_solver_report_initializes_durable_output(monkeypatch, tmp_path) -> None:
    captured = _run_with_fake_execute(monkeypatch, tmp_path)

    RunAPI.run(**_base_kwargs(logging={"write_solver_report": True, "write_jsonl": False}))

    assert captured["execute"][0]["initialize_logging"] is True
    assert isinstance(captured["execute"][0]["logging_config"], LoggingConfig)
    assert captured["execute"][0]["logging_config"].write_solver_report is True
    assert (tmp_path / "artifacts" / "solver_report.json").exists()


def test_write_solver_report_false_alone_does_not_initialize(monkeypatch, tmp_path) -> None:
    captured = _run_with_fake_execute(monkeypatch, tmp_path)

    RunAPI.run(**_base_kwargs(logging={"write_solver_report": False}))

    assert captured["execute"][0]["initialize_logging"] is False
    assert captured["execute"][0]["logging_config"] is None
    assert not (tmp_path / "artifacts" / "solver_report.json").exists()


@pytest.mark.parametrize("value", [1, 0, "true"])
def test_write_solver_report_requires_exact_bool(monkeypatch, value) -> None:
    _run_with_fake_execute(monkeypatch, Path("unused"))

    with pytest.raises(TypeError, match="write_solver_report"):
        RunAPI.run(**_base_kwargs(logging={"write_solver_report": value}))


def test_logging_config_rejects_non_bool_write_solver_report() -> None:
    with pytest.raises(TypeError, match="write_solver_report"):
        LoggingConfig(write_solver_report=1)


def test_sidecar_json_matches_returned_solver_report(monkeypatch, tmp_path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)

    result = RunAPI.run(
        **_base_kwargs(
            logging=LoggingConfig(write_jsonl=False, write_solver_report=True),
            return_solver_report=True,
        )
    )

    payload = json.loads((tmp_path / "artifacts" / "solver_report.json").read_text(encoding="utf-8"))
    assert isinstance(result, RunResult)
    assert payload == result.solver_report.to_json_dict()


def test_write_solver_report_true_can_still_return_solution(monkeypatch, tmp_path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)

    result = RunAPI.run(
        **_base_kwargs(logging=LoggingConfig(write_jsonl=False, write_solver_report=True))
    )

    assert isinstance(result, Solution)
    assert (tmp_path / "artifacts" / "solver_report.json").exists()


def test_runspec_logging_write_solver_report_writes_sidecar(monkeypatch, tmp_path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)
    spec = _minimal_spec(logging=LoggingConfig(write_jsonl=False, write_solver_report=True))

    result = RunAPI.run(spec=spec)

    assert isinstance(result, Solution)
    assert (tmp_path / "artifacts" / "solver_report.json").exists()


def test_runspec_rejects_outside_logging_write_solver_report(monkeypatch, tmp_path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="write_solver_report"):
        RunAPI.run(spec=_minimal_spec(), logging={"write_solver_report": True})


def test_sidecar_payload_contains_no_absolute_local_paths(monkeypatch, tmp_path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)

    RunAPI.run(
        **_base_kwargs(logging=LoggingConfig(write_jsonl=False, write_solver_report=True))
    )

    payload = json.loads((tmp_path / "artifacts" / "solver_report.json").read_text(encoding="utf-8"))
    strings = []

    def collect(value):
        if isinstance(value, str):
            strings.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(payload)
    assert not any(os.path.isabs(value) for value in strings)


def test_write_solver_report_failure_is_not_silently_dropped(monkeypatch, tmp_path) -> None:
    run_module = importlib.import_module("rune_decrypter_prime.api.run")
    _run_with_fake_execute(monkeypatch, tmp_path)

    def fail_writer(*_args, **_kwargs):
        raise RuntimeError("write failed")

    monkeypatch.setattr(run_module, "write_solver_report_json", fail_writer)

    with pytest.raises(RuntimeError, match="write failed"):
        RunAPI.run(
            **_base_kwargs(logging=LoggingConfig(write_jsonl=False, write_solver_report=True))
        )


def test_real_known_key_run_writes_solver_report_sidecar(tmp_path) -> None:
    xor_spec = define_map(
        function=lambda pt, k: (pt ^ k) % 29,
        name="unit_test_solver_report_export_xor_smoke",
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
        logging=LoggingConfig(
            repo_root=str(tmp_path),
            out_root=str(tmp_path / "out"),
            run_kind="tests",
            label="solver-report-export-smoke",
            write_jsonl=False,
            write_solver_report=True,
        ),
        return_solver_report=True,
    )

    run_dirs = list((tmp_path / "out" / "tests").iterdir())
    assert len(run_dirs) == 1
    report_path = run_dirs[0] / "artifacts" / "solver_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert isinstance(result, RunResult)
    assert payload == result.solver_report.to_json_dict()
    assert payload["details"]["execution_route"] == "known_key_fastpath"
    assert payload["normalized_params"] == {"beam_width": 1}
    assert payload["effective_seed"] is None
    assert payload["best_key"] == [int(value) for value in result.solution.key]
