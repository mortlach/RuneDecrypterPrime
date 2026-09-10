from __future__ import annotations

import importlib
import inspect

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
    callback = lambda _event: None

    api.run(
        _spec(api.RuneInput("abc")),
        progress_callback=callback,
    )

    assert captured["logging_runtime"] == {"progress_callback": callback}


def test_progress_interval_is_not_in_public_signature() -> None:
    assert "progress_interval" not in inspect.signature(api.run).parameters


def test_word_length_policy_infer_derives_text_wli() -> None:
    materialized = materialize_runspec_problem_input(_spec(api.RuneInput("abc def")))

    assert materialized.wli is not None
    assert len(materialized.wli) == len(materialized.ciphertext)


def test_word_length_policy_infer_preserves_explicit_index_wli() -> None:
    supplied = ((0, 2), (1, 2))
    materialized = materialize_runspec_problem_input(
        _spec(api.RuneInput((1, 2), word_length_information=supplied))
    )

    assert tuple(map(tuple, materialized.wli or ())) == supplied


def test_word_length_policy_require_accepts_aligned_wli() -> None:
    base = _spec(api.RuneInput((1, 2), word_length_information=((0, 2), (1, 2))))
    request = api.RunSpec(
        problem_input=base.problem_input,
        cipher=base.cipher,
        key_space=base.key_space,
        solver=base.solver,
        word_length_policy=api.WordLengthPolicy.REQUIRE,
        telemetry_enabled=False,
    )

    assert materialize_runspec_problem_input(request).wli is not None


def test_word_length_policy_require_rejects_missing_wli() -> None:
    base = _spec(api.RuneInput((1, 2)))
    request = api.RunSpec(
        problem_input=base.problem_input,
        cipher=base.cipher,
        key_space=base.key_space,
        solver=base.solver,
        word_length_policy=api.WordLengthPolicy.REQUIRE,
        telemetry_enabled=False,
    )

    with pytest.raises(api.ConfigurationError, match="REQUIRE"):
        materialize_runspec_problem_input(request)


def test_word_length_policy_disabled_removes_available_wli() -> None:
    base = _spec(api.RuneInput("abc def"))
    request = api.RunSpec(
        problem_input=base.problem_input,
        cipher=base.cipher,
        key_space=base.key_space,
        solver=base.solver,
        scoring=api.ScoringConfig(wli_lane_enabled=False),
        word_length_policy=api.WordLengthPolicy.DISABLED,
        telemetry_enabled=False,
    )

    assert materialize_runspec_problem_input(request).wli is None


def test_word_length_policy_disabled_character_only_reaches_execution(monkeypatch) -> None:
    captured = _capture(monkeypatch)
    base = _spec(api.RuneInput("abc def"))
    request = api.RunSpec(
        problem_input=base.problem_input,
        cipher=base.cipher,
        key_space=base.key_space,
        solver=base.solver,
        scoring=api.ScoringConfig(wli_lane_enabled=False),
        word_length_policy=api.WordLengthPolicy.DISABLED,
        telemetry_enabled=False,
    )

    api.run(request)

    assert captured["wli"] is None


def test_word_length_policy_disabled_rejects_wli_required_scoring() -> None:
    base = _spec(api.RuneInput("abc def"))
    request = api.RunSpec(
        problem_input=base.problem_input,
        cipher=base.cipher,
        key_space=base.key_space,
        solver=base.solver,
        word_length_policy=api.WordLengthPolicy.DISABLED,
        telemetry_enabled=False,
    )

    with pytest.raises(api.advanced.UnsupportedConfigurationError, match="DISABLED"):
        api.run(request)
