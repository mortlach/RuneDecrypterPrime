from __future__ import annotations

import importlib
import json

from rdp import api
from rune_decrypter_prime.core.config.solution import Solution


def _solution() -> Solution:
    value = Solution(key=[1], plaintext=[0, 1], score=3.5)
    value.stop_reason = "max_rounds_reached"
    return value


def _spec(*, logging: api.LoggingConfig | None = None) -> api.RunSpec:
    return api.RunSpec(
        problem_input=api.RuneIndexInput(indices=(0, 1)),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=1),
        solver=api.SolverSpec.beam_search(width=1, rounds=0),
        logging=logging,
        telemetry_enabled=False,
    )


def test_solver_report_sidecar_is_opt_in(monkeypatch, tmp_path) -> None:
    run_module = importlib.import_module("rdp.api.run")
    monkeypatch.setattr(run_module, "execute_run", lambda **_kwargs: _solution())
    monkeypatch.setattr(run_module, "get_run_dir", lambda: tmp_path)

    result = api.run(_spec())
    assert isinstance(result, api.RunResult)
    assert not (tmp_path / "artifacts" / "solver_report.json").exists()

    result = api.run(
        _spec(logging=api.LoggingConfig(write_event_log=False, write_solver_report=True))
    )
    payload = json.loads(
        (tmp_path / "artifacts" / "solver_report.json").read_text(encoding="utf-8")
    )
    assert payload == result.solver_report.to_json_dict()


def test_logging_config_requires_exact_bool() -> None:
    try:
        api.LoggingConfig(write_solver_report=1)
    except TypeError:
        return
    raise AssertionError("write_solver_report must be bool")
