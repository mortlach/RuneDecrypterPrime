from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from rune_decrypter_prime.api.run_spec import RuneIndexInput, RunSpec
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec, SolverSpec
from rune_decrypter_prime.core.config.interruptor import InterruptorConfig
from rune_decrypter_prime.core.config.logging_config import LoggingConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig, ScoringObjective
from rune_decrypter_prime.core.types import (
    BeamExpansionMode,
    ComputeDevice,
    ScheduledStreamOperation,
    ScheduledStreamSchedule,
    TextDirection,
    WordLengthPolicy,
)


@pytest.mark.parametrize(
    ("typed", "parsed"),
    (
        (CipherSpec.vigenere(), CipherSpec.from_name("vigenere")),
        (
            CipherSpec.periodic_columnar(period=13, columns=7),
            CipherSpec.from_name("periodic_columnar", parameters={"period": 13, "columns": 7}),
        ),
        (
            CipherSpec.two_period_streams(
                first_period=13,
                second_period=31,
                operation=ScheduledStreamOperation.ADD,
                schedule=ScheduledStreamSchedule.OVERLAY,
            ),
            CipherSpec.from_name(
                "two_period_streams",
                parameters={
                    "first_period": 13,
                    "second_period": 31,
                    "operation": "add",
                    "schedule": "overlay",
                },
            ),
        ),
        (KeySpec.repeating(length=13), KeySpec.from_name("repeating", parameters={"length": 13})),
        (
            KeySpec.repeating_range(minimum_length=3, maximum_length=13),
            KeySpec.from_name(
                "repeating_range",
                parameters={"minimum_length": 3, "maximum_length": 13},
            ),
        ),
        (
            SolverSpec.beam_search(
                width=64,
                rounds=20,
                expansion=BeamExpansionMode.SWEEP,
                seed=7,
            ),
            SolverSpec.from_name(
                "beam_search",
                parameters={"width": 64, "rounds": 20, "expansion": "sweep", "seed": 7},
            ),
        ),
        (
            InterruptorConfig.search((1, 3, 5), maximum_count=2),
            InterruptorConfig.from_dict(
                {
                    "mode": "search",
                    "parameters": {
                        "candidate_positions": [1, 3, 5],
                        "minimum_count": 0,
                        "maximum_count": 2,
                        "strategy": "auto",
                        "maximum_combinations": 5000,
                    },
                }
            ),
        ),
    ),
)
def test_typed_and_parser_construction_are_equivalent(typed: object, parsed: object) -> None:
    assert typed == parsed
    assert hash(typed) == hash(parsed)
    assert copy.copy(typed) is typed
    assert copy.deepcopy(typed) is typed
    assert typed.replay_key == parsed.replay_key  # type: ignore[attr-defined]
    assert typed.to_dict() == parsed.to_dict()  # type: ignore[attr-defined]


def test_spec_parameters_are_frozen_and_readable() -> None:
    spec = CipherSpec.periodic_columnar(period=13, columns=7)

    assert dict(spec.parameters) == {
        "period": 13,
        "columns": 7,
        "order": "substitution_then_columnar",
        "alphabet_size": 29,
    }
    with pytest.raises(TypeError):
        spec.parameters["period"] = 31  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        spec.kind = spec.kind  # type: ignore[misc]


def test_scoring_and_logging_are_exact_immutable_configs() -> None:
    scoring = ScoringConfig(
        language_model_root=Path("models"),
        objective=ScoringObjective.average_log_probability(),
        character_order_weights={3: 0.4, 4: 0.6},
        word_length_lane_enabled=False,
    )
    restored = ScoringConfig.from_dict(scoring.to_dict())

    assert restored == scoring
    assert hash(restored) == hash(scoring)
    assert scoring.effective_lm_model_weights() == (
        ("char", 3, 0.4),
        ("char", 4, 0.6),
    )
    assert LoggingConfig().write_event_log is False
    assert LoggingConfig().portable_output is True


def test_runspec_owns_the_complete_request() -> None:
    request = RunSpec(
        problem_input=RuneIndexInput((1, 2, 3), ((0, 1), (0, 1), (0, 1))),
        cipher=CipherSpec.vigenere(),
        key_space=KeySpec.repeating(length=3),
        solver=SolverSpec.beam_search(width=4, rounds=2, seed=11),
        initial_keys=((1, 2, 3),),
        word_length_policy=WordLengthPolicy.REQUIRE,
        text_direction=TextDirection.RIGHT_TO_LEFT,
        compute_device=ComputeDevice.CPU,
        interruptors=InterruptorConfig.disabled(),
    )

    assert request.problem_input.indices == (1, 2, 3)
    assert request.key_space.parameters["length"] == 3
    assert request.solver.seed == 11
    assert request.initial_keys == ((1, 2, 3),)


def test_direct_typed_constructors_reject_raw_enum_strings() -> None:
    with pytest.raises(TypeError):
        CipherSpec.two_period_streams(operation="add")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        SolverSpec.beam_search(width=4, rounds=2, expansion="sweep")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        InterruptorConfig.search((1, 2), strategy="bruteforce")  # type: ignore[arg-type]
