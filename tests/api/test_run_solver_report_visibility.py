from __future__ import annotations

import importlib

from rdp import api
from rune_decrypter_prime.core.config.solution import Solution


def _solution() -> Solution:
    value = Solution(key=[1, 2], plaintext=[0, 1], score=3.5)
    value.stop_reason = "max_rounds_reached"
    value.step = 4
    value.evals = 5
    return value


def _spec(*, seed: int | None = 7) -> api.RunSpec:
    return api.RunSpec(
        problem_input=api.RuneIndexInput(indices=(0, 1)),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=2),
        solver=api.SolverSpec.beam_search(width=2, rounds=0, seed=seed),
        telemetry_enabled=False,
    )


def test_run_always_returns_immutable_result_with_report(monkeypatch) -> None:
    run_module = importlib.import_module("rdp.api.run")
    monkeypatch.setattr(run_module, "execute_run", lambda **_kwargs: _solution())

    result = api.run(_spec())

    assert isinstance(result, api.RunResult)
    assert isinstance(result.solver_report, api.advanced.SolverReport)
    assert result.key == (1, 2)
    assert result.solver_report.requested_seed == 7
    assert result.solver_report.effective_seed == 7


def test_omitted_seed_has_reproducible_effective_seed(monkeypatch) -> None:
    run_module = importlib.import_module("rdp.api.run")
    monkeypatch.setattr(run_module, "execute_run", lambda **_kwargs: _solution())

    result = api.run(_spec(seed=None))

    assert result.solver_report.requested_seed is None
    assert result.solver_report.effective_seed == 0


def test_runspec_has_no_conditional_result_field() -> None:
    assert "return_solver_report" not in api.RunSpec.__dataclass_fields__
