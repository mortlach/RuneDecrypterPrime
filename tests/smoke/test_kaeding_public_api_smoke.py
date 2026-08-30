"""Bounded public-API preflight for the long Kaeding tutorial routes.

These cases deliberately start from a known valid key so they test interface,
structured mutation, scoring, telemetry, and result reporting in milliseconds.
They are not solver-quality qualifications and must not replace the long runs.
"""

from __future__ import annotations

import json

import pytest

from rdp import api
from rune_decrypter_prime.utils.runeglish import Runeglish


pytestmark = pytest.mark.tier_a

_TEXT = (
    "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE AND THE "
    "MARCH HARE WAS HAVING TEA"
)
_DIRECTION = api.TextDirection.LEFT_TO_RIGHT
_IDENTITY = tuple(range(29))
_ROTATED = tuple(range(1, 29)) + (0,)


def _scoring() -> api.ScoringConfig:
    return api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )


def _run_smoke(
    *,
    cipher: api.CipherSpec,
    key_space: api.KeySpec,
    concrete_key: tuple[int, ...],
    column_interval: int,
    column_batch_size: int,
) -> tuple[api.RunResult, tuple[int, ...]]:
    plaintext, word_lengths, _ = Runeglish.encode_english_to_runes(
        _TEXT, direction=_DIRECTION
    )
    plaintext = tuple(int(value) for value in plaintext)
    ciphertext = api.encrypt(plaintext, cipher=cipher, key=concrete_key)
    assert api.decrypt(ciphertext, cipher=cipher, key=concrete_key) == plaintext

    solver = api.SolverSpec.kaeding(
        steps=2,
        restarts=1,
        inner_batch_size=4,
        block_schedule=api.advanced.KaedingBlockSchedule.ROUND_ROBIN,
        column_interval=column_interval,
        column_batch_size=column_batch_size,
        slip_blocks=1,
        slip_interval=1,
        slip_policy=api.advanced.KaedingSlipPolicy.FIXED_INTERVAL,
        slip_swaps=1,
        plateau_rounds=1,
        seed=24680,
    )
    result = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(
                indices=ciphertext, word_lengths=word_lengths
            ),
            cipher=cipher,
            key_space=key_space,
            solver=solver,
            scoring=_scoring(),
            initial_keys=(concrete_key,),
            telemetry_enabled=True,
            text_direction=_DIRECTION,
            compute_device=api.ComputeDevice.CPU,
        )
    )

    assert result.plaintext == plaintext
    assert result.key == concrete_key
    assert result.solver_report.steps == 2
    assert result.solver_report.evaluations > 0
    assert result.solver_report.tokens_processed > 0
    assert result.solver_report.wall_time_seconds > 0.0
    assert result.solver_report.score_time_seconds > 0.0
    assert result.status.stop_reason is not None
    assert result.reproducibility.effective_seed == 24680
    json.dumps(dict(result.telemetry), sort_keys=True)
    span_result = result.telemetry["solver_spans"]["kaeding"]["result"]
    assert result.solver_report.steps == span_result["steps"]
    assert result.solver_report.evaluations == span_result["evals"]
    assert result.solver_report.tokens_processed == span_result["tokens"]
    assert result.solver_report.wall_time_seconds == span_result["wall_time_s"]
    return result, plaintext


def test_periodic_substitution_kaeding_public_route() -> None:
    result, _ = _run_smoke(
        cipher=api.CipherSpec.periodic_substitution(period=2),
        key_space=api.KeySpec.periodic_substitution(period=2),
        concrete_key=_IDENTITY + _ROTATED,
        column_interval=0,
        column_batch_size=0,
    )

    kaeding = result.telemetry["kaeding"]
    assert set(kaeding["per_phase"]) == {"0", "1"}
    assert kaeding["slip_count"] == 2
    assert all(event["col_moves"] == 0 for event in result.telemetry["solver_progress"])


def test_periodic_columnar_kaeding_public_route_and_column_moves() -> None:
    result, _ = _run_smoke(
        cipher=api.CipherSpec.periodic_columnar(
            period=2,
            columns=3,
            order=api.advanced.PeriodicColumnarOrder.COLUMNAR_THEN_SUBSTITUTION,
        ),
        key_space=api.KeySpec.periodic_columnar(period=2, columns=3),
        concrete_key=_IDENTITY + _ROTATED + (2, 0, 1),
        column_interval=1,
        column_batch_size=4,
    )

    progress = result.telemetry["solver_progress"]
    assert len(progress) == 2
    assert all(event["col_moves"] == 4 for event in progress)
    assert set(result.telemetry["kaeding"]["per_phase"]) == {"0", "1"}
