from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from rdp.api.normalize import _assert_core_ready, normalize_rune_input
from rdp.api.run_spec import RuneInput, RunSpec, SourceReferenceInput
from rdp.api.source_resolution import resolve_source_input_ref
from rdp.core.config.logging_config import LoggingConfig


RUNTIME_LOGGING_KEYS = frozenset({"progress_callback", "log_interval"})


@dataclass(frozen=True, slots=True)
class MaterializedRunSpecInput:
    ciphertext: np.ndarray
    wli: Sequence[Sequence[int]] | None


@dataclass(frozen=True, slots=True)
class RunSpecLoggingRoute:
    config: LoggingConfig | None = None
    runtime_controls: dict[str, Any] = field(default_factory=dict)
    initialize_output: bool = False


def materialize_runspec_problem_input(spec: RunSpec) -> MaterializedRunSpecInput:
    if not isinstance(spec, RunSpec):
        raise TypeError("spec must be a RunSpec")

    problem_input = spec.problem_input
    if isinstance(problem_input, RuneInput):
        input_format = problem_input.format
        if input_format is None:
            raise RuntimeError("RuneInput format was not resolved")
        ciphertext, wli = normalize_rune_input(
            problem_input.value,
            input_format=input_format.value,
            direction=spec.text_direction,
            wli_data=problem_input.word_length_information,
        )
        return MaterializedRunSpecInput(ciphertext=ciphertext, wli=wli)

    if isinstance(problem_input, SourceReferenceInput):
        resolved = resolve_source_input_ref(problem_input)
        ciphertext = _ct_idx_to_uint8_array(resolved.ct_idx)
        _assert_core_ready(ciphertext, resolved.wli)
        return MaterializedRunSpecInput(ciphertext=ciphertext, wli=resolved.wli)

    raise TypeError("spec.problem_input must be RuneInput or SourceReferenceInput")


def route_runspec_logging(spec: RunSpec, outside_logging: Any = None) -> RunSpecLoggingRoute:
    if not isinstance(spec, RunSpec):
        raise TypeError("spec must be a RunSpec")

    runtime_controls: dict[str, Any] = {}
    if outside_logging is None:
        pass
    elif isinstance(outside_logging, dict):
        keys = frozenset(outside_logging)
        unsupported = sorted(keys - RUNTIME_LOGGING_KEYS)
        if unsupported:
            raise ValueError(f"logging has unsupported keys for spec path: {', '.join(unsupported)}")
        runtime_controls = dict(outside_logging)
    elif isinstance(outside_logging, LoggingConfig):
        raise TypeError("LoggingConfig outside spec is not allowed when spec is supplied")
    else:
        raise TypeError("logging must be None or a runtime-controls dict when spec is supplied")

    return RunSpecLoggingRoute(
        config=spec.logging,
        runtime_controls=runtime_controls,
        initialize_output=spec.logging is not None,
    )


def reject_runspec_mixed_inputs(inputs: Mapping[str, Any], *, unset: object) -> None:
    supplied = sorted(name for name, value in inputs.items() if value is not unset)
    if supplied:
        raise TypeError(f"run(request) does not accept outside durable inputs: {', '.join(supplied)}")


def _ct_idx_to_uint8_array(ct_idx: Sequence[int]) -> np.ndarray:
    array = np.asarray(tuple(ct_idx), dtype=np.uint8).reshape(-1)
    if not array.flags.c_contiguous:
        array = np.ascontiguousarray(array)
    return array


__all__ = [
    "MaterializedRunSpecInput",
    "RUNTIME_LOGGING_KEYS",
    "RunSpecLoggingRoute",
    "materialize_runspec_problem_input",
    "reject_runspec_mixed_inputs",
    "route_runspec_logging",
]
