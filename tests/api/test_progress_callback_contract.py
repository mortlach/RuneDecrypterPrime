from __future__ import annotations

import importlib
import json

import pytest

from rdp import api
from rdp.core.config.solution import Solution


def _generic_specs() -> tuple[api.SolverSpec, ...]:
    ga = api.SolverSpec.genetic_algorithm(population_size=4, generations=1)
    sa = api.SolverSpec.simulated_annealing(iterations=1)
    return (
        api.SolverSpec.beam_search(width=1, rounds=1),
        ga,
        sa,
        api.SolverSpec.hybrid(
            genetic_algorithm=ga,
            simulated_annealing=sa,
            use_beam_search=True,
            beam_width=1,
            beam_rounds=1,
        ),
        api.SolverSpec.kaeding(steps=1, restarts=1, inner_batch_size=1),
    )


def _request(solver: api.SolverSpec) -> api.RunSpec:
    return api.RunSpec(
        problem_input=api.RuneInput('a'),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=1),
        solver=solver,
    )


@pytest.mark.parametrize('solver', _generic_specs())
def test_public_run_delivers_callback_to_generic_solver_route(monkeypatch, solver) -> None:
    run_module = importlib.import_module('rdp.api.run')
    events = []

    def fake_execute_run(**kwargs):
        kwargs['logging_runtime']['progress_callback']({
            'solver': kwargs['solver'].name,
            'pct': 100,
            'best_key': [0],
        })
        return Solution(key=[0], plaintext=[0], score=0.0, stop_reason='max_rounds')

    monkeypatch.setattr(run_module, 'execute_run', fake_execute_run)

    result = api.run(_request(solver), progress_callback=events.append)

    assert isinstance(result, api.RunResult)
    assert len(events) == 1
    assert isinstance(events[0], dict)
    json.dumps(events[0], allow_nan=False)


def test_public_run_delivers_callback_to_two_period_stage_route(monkeypatch) -> None:
    from rdp.solvers import two_period_cribs as staged

    events = []

    def fake_run_two_period_stages(**kwargs):
        for stage_id in ('S2', 'B1', 'F1', 'final_union'):
            kwargs['progress_callback']({'stage_id': stage_id, 'complete': True})
        return Solution(
            key=[0, 0],
            plaintext=[0],
            score=0.0,
            stop_reason='configured_work_limit_reached',
        )

    monkeypatch.setattr(staged, 'run_two_period_stages', fake_run_two_period_stages)
    result = api.run(
        problem_input=api.RuneInput('a'),
        cipher=api.CipherSpec.two_period_vigenere(first_period=1, second_period=1),
        key_space=api.KeySpec.repeating(length=2),
        solver=api.SolverSpec.two_period_cribs(fixed_cribs=(('a', 0),), starts=1),
        progress_callback=events.append,
    )

    assert isinstance(result, api.RunResult)
    assert [event['stage_id'] for event in events] == ['S2', 'B1', 'F1', 'final_union']
    json.dumps(events, allow_nan=False)


def test_public_callback_error_propagates(monkeypatch) -> None:
    run_module = importlib.import_module('rdp.api.run')

    def fake_execute_run(**kwargs):
        kwargs['logging_runtime']['progress_callback']({'pct': 1})
        raise AssertionError('unreachable')

    def fail(_event):
        raise RuntimeError('caller callback failed')

    monkeypatch.setattr(run_module, 'execute_run', fake_execute_run)

    with pytest.raises(RuntimeError, match='caller callback failed'):
        api.run(_request(api.SolverSpec.beam_search(width=1, rounds=1)), progress_callback=fail)
