from __future__ import annotations

import importlib

import pytest

from rdp import api
from rdp.api.run_spec_routing import materialize_runspec_problem_input


def _spec(problem_input: api.ProblemInput) -> api.RunSpec:
    return api.RunSpec(
        problem_input=problem_input,
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=1),
        solver=api.SolverSpec.beam_search(width=1, rounds=None),
        telemetry_enabled=False,
    )


def _capture(monkeypatch):
    captured: dict[str, object] = {}
    run_module = importlib.import_module("rdp.api.run")
    monkeypatch.setattr(run_module, "execute_run", lambda **kwargs: captured.update(kwargs))
    return captured


@pytest.mark.parametrize(
    "problem_input",
    [
        api.RuneInput("abc def"),
        api.RuneInput(value=(1, 2), word_length_information=((0, 1), (0, 1))),
    ],
)
def test_run_spec_materializes_supported_inputs(monkeypatch, problem_input) -> None:
    captured = _capture(monkeypatch)

    result = api.run(_spec(problem_input))

    assert isinstance(result, api.RunResult)
    assert captured["ciphertext"].dtype.name == "uint8"


def test_component_overload_builds_the_same_request(monkeypatch) -> None:
    captured = _capture(monkeypatch)

    result = api.run(
        problem_input=api.RuneInput(value=(1, 2)),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=1),
        solver=api.SolverSpec.beam_search(width=1, rounds=None),
        telemetry_enabled=False,
    )

    assert isinstance(result, api.RunResult)
    assert tuple(captured["ciphertext"]) == (1, 2)


@pytest.mark.parametrize(
    ("problem_input", "direction", "expected"),
    [
        (api.RuneInput("ᚦᛖ"), api.TextDirection.LTR, (2, 18)),
        (api.RuneInput("TH·E"), api.TextDirection.LTR, (2, 18)),
        (api.RuneInput("TH|E"), api.TextDirection.LTR, (2, 18)),
        (api.RuneInput("THE"), api.TextDirection.LTR, (2, 18)),
        (api.RuneInput("THE"), api.TextDirection.RTL, (16, 8, 18)),
    ],
)
def test_rune_input_materializes_each_format(problem_input, direction, expected) -> None:
    spec = _spec(problem_input)
    spec = api.RunSpec(
        problem_input=spec.problem_input,
        cipher=spec.cipher,
        key_space=spec.key_space,
        solver=spec.solver,
        text_direction=direction,
        telemetry_enabled=False,
    )

    materialized = materialize_runspec_problem_input(spec)

    assert tuple(materialized.ciphertext) == expected
    assert len(materialized.wli) == len(expected)


def test_run_spec_rejects_mixed_component_arguments(monkeypatch) -> None:
    _capture(monkeypatch)

    with pytest.raises(TypeError, match="cannot be combined"):
        api.run(_spec(api.RuneInput("abc")), scoring=api.ScoringConfig())


def test_run_spec_accepts_only_runtime_progress_controls(monkeypatch) -> None:
    captured = _capture(monkeypatch)
    callback = lambda *_args, **_kwargs: None

    api.run(
        _spec(api.RuneInput("abc")),
        progress_callback=callback,
        progress_interval=10,
    )

    assert captured["logging_runtime"] == {
        "progress_callback": callback,
        "log_interval": 10,
    }


@pytest.mark.parametrize("value", [0, True, "10"])
def test_progress_interval_is_strict(value) -> None:
    with pytest.raises((TypeError, ValueError)):
        api.run(_spec(api.RuneInput("abc")), progress_interval=value)
