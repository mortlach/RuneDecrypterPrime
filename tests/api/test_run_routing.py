from __future__ import annotations

import importlib

import pytest

from rdp import api


def _spec(problem_input: api.ProblemInput) -> api.RunSpec:
    return api.RunSpec(
        problem_input=problem_input,
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=1),
        solver=api.SolverSpec.beam_search(width=1, rounds=0),
        telemetry_enabled=False,
    )


def _capture(monkeypatch):
    captured: dict[str, object] = {}
    run_module = importlib.import_module("rdp.api.run")
    monkeypatch.setattr(
        run_module, "execute_run", lambda **kwargs: captured.update(kwargs)
    )
    return captured


@pytest.mark.parametrize(
    "problem_input",
    [
        api.RawTextInput("abc def"),
        api.RuneIndexInput(indices=(1, 2), word_lengths=((0, 1), (0, 1))),
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
        problem_input=api.RuneIndexInput(indices=(1, 2)),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=1),
        solver=api.SolverSpec.beam_search(width=1, rounds=0),
        telemetry_enabled=False,
    )

    assert isinstance(result, api.RunResult)
    assert tuple(captured["ciphertext"]) == (1, 2)


def test_run_spec_rejects_mixed_component_arguments(monkeypatch) -> None:
    _capture(monkeypatch)

    with pytest.raises(TypeError, match="cannot be combined"):
        api.run(_spec(api.RawTextInput("abc")), scoring=api.ScoringConfig())


def test_run_spec_accepts_only_runtime_progress_controls(monkeypatch) -> None:
    captured = _capture(monkeypatch)
    callback = lambda *_args, **_kwargs: None

    api.run(
        _spec(api.RawTextInput("abc")),
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
        api.run(_spec(api.RawTextInput("abc")), progress_interval=value)
