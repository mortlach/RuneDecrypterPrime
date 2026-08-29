from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from rune_decrypter_prime.api.run_spec import RuneIndexInput, RunSpec
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec, SolverSpec
from rune_decrypter_prime.ciphers import cipher_runtime_registry
from rune_decrypter_prime.core.config.interruptor import InterruptorConfig
from rune_decrypter_prime.core.config.cipher import (
    expected_concrete_key_length,
    materialize_cipher_config,
    validate_concrete_key,
)
from rune_decrypter_prime.core.config.logging_config import LoggingConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig, ScoringObjective
from rune_decrypter_prime.core.engine.builders import build_cipher
from rune_decrypter_prime.core.component_contracts import (
    CipherKeyMismatchError,
    InvalidConcreteKeyError,
)
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


@pytest.mark.parametrize(
    ("cipher", "key_space", "length"),
    (
        (CipherSpec.vigenere(), KeySpec.repeating(length=3), 3),
        (CipherSpec.autokey(), KeySpec.repeating(length=4), 4),
        (CipherSpec.columnar(columns=5), KeySpec.permutation(length=5), 5),
        (CipherSpec.rail_fence(), KeySpec.scalar(minimum=2, maximum=8), 1),
        (CipherSpec.substitution(), KeySpec.permutation(length=29), 29),
        (
            CipherSpec.periodic_substitution(period=2),
            KeySpec.periodic_substitution(period=2),
            58,
        ),
        (
            CipherSpec.periodic_columnar(period=2, columns=5),
            KeySpec.periodic_columnar(period=2, columns=5),
            63,
        ),
        (CipherSpec.two_period_vigenere(first_period=2, second_period=3), KeySpec.repeating(length=5), 5),
        (CipherSpec.periodic_with_fixed_stream((1, 2, 3), period=4), KeySpec.repeating(length=4), 4),
        (CipherSpec.periodic_with_prime_stream(period=4), KeySpec.repeating(length=4), 4),
        (CipherSpec.two_period_streams(first_period=2, second_period=3), KeySpec.repeating(length=5), 5),
    ),
)
def test_all_v1_cipher_key_bindings_have_one_exact_length(
    cipher: CipherSpec,
    key_space: KeySpec,
    length: int,
) -> None:
    assert expected_concrete_key_length(cipher, key_space) == length
    cfg = materialize_cipher_config(
        cipher=cipher,
        key_space=key_space,
        ciphertext=(1, 2, 3, 4),
        word_lengths=None,
        text_direction=TextDirection.RIGHT_TO_LEFT,
        compute_device=ComputeDevice.CPU,
    )
    assert cfg.key_length == length
    assert cipher_runtime_registry.has(cfg.name)
    assert build_cipher(cfg).key_length == length


def test_binding_rejects_repeated_dimension_conflicts() -> None:
    with pytest.raises(CipherKeyMismatchError, match="columns"):
        expected_concrete_key_length(
            CipherSpec.periodic_columnar(period=2, columns=5),
            KeySpec.periodic_columnar(period=2, columns=4),
        )
    with pytest.raises(CipherKeyMismatchError, match="derived key length 5"):
        expected_concrete_key_length(
            CipherSpec.two_period_vigenere(first_period=2, second_period=3),
            KeySpec.repeating(length=4),
        )


def test_concrete_key_validation_preserves_semantic_values() -> None:
    rail_cipher = CipherSpec.rail_fence(minimum_rails=2, maximum_rails=8)
    rail_space = KeySpec.scalar(minimum=2, maximum=8)
    assert validate_concrete_key(rail_cipher, rail_space, (7,)) == (7,)
    with pytest.raises(InvalidConcreteKeyError, match="rail count"):
        validate_concrete_key(rail_cipher, rail_space, (1,))

    substitution = CipherSpec.substitution(alphabet_size=5)
    substitution_space = KeySpec.permutation(length=5)
    assert validate_concrete_key(substitution, substitution_space, (4, 3, 2, 1, 0)) == (4, 3, 2, 1, 0)
    with pytest.raises(InvalidConcreteKeyError, match="permutation segment"):
        validate_concrete_key(substitution, substitution_space, (0, 0, 1, 2, 3))


@pytest.mark.parametrize(
    ("cipher", "key_space", "operation"),
    (
        (
            CipherSpec.two_period_vigenere(first_period=2, second_period=3),
            KeySpec.repeating(length=5),
            "add",
        ),
        (
            CipherSpec.periodic_with_fixed_stream((1, 2, 3), period=4),
            KeySpec.repeating(length=4),
            "add",
        ),
        (
            CipherSpec.periodic_with_prime_stream(period=4, prime_offset=2),
            KeySpec.repeating(length=4),
            "add",
        ),
        (
            CipherSpec.two_period_streams(
                first_period=2,
                second_period=3,
                operation=ScheduledStreamOperation.SUBTRACT_ADD,
            ),
            KeySpec.repeating(length=5),
            "sub_add",
        ),
    ),
)
def test_scheduled_presets_materialize_one_truthful_runtime(
    cipher: CipherSpec,
    key_space: KeySpec,
    operation: str,
) -> None:
    cfg = materialize_cipher_config(
        cipher=cipher,
        key_space=key_space,
        ciphertext=(1, 2, 3, 4),
        word_lengths=None,
        text_direction=TextDirection.RIGHT_TO_LEFT,
        compute_device=ComputeDevice.CPU,
    )

    assert cfg.name == "scheduled_stream_lookup"
    assert cfg.key_length == expected_concrete_key_length(cipher, key_space)
    assert cfg.operation == operation
    assert cfg.spec is cipher
    runtime = build_cipher(cfg)
    assert type(runtime).__name__ == "ScheduledStreamLookupCipher"
    assert runtime.key_length == cfg.key_length


def test_cipher_runtime_registry_has_only_exact_runtime_identities() -> None:
    assert cipher_runtime_registry.available() == (
        "autokey",
        "columnar",
        "generic_map",
        "periodic_columnar",
        "periodic_substitution",
        "rail_fence",
        "scheduled_stream_lookup",
        "substitution",
        "vigenere",
    )


def test_mask_schedule_is_bound_to_the_run_input_length() -> None:
    cipher = CipherSpec.two_period_vigenere(
        first_period=2,
        second_period=3,
        schedule=ScheduledStreamSchedule.MASK,
        mask=(1, 2),
    )
    with pytest.raises(ValueError, match="mask length"):
        materialize_cipher_config(
            cipher=cipher,
            key_space=KeySpec.repeating(length=5),
            ciphertext=(1, 2, 3),
            word_lengths=None,
            text_direction=TextDirection.RIGHT_TO_LEFT,
            compute_device=ComputeDevice.CPU,
        )
