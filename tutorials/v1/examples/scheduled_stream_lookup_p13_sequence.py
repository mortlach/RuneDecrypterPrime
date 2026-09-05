"""Find a period-13 key with a supplied stream sequence.

The sequence is part of the cipher we give RDP. It still has to find the
repeating key that goes with it.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from rdp import api
from tutorials.v1.data.plaintext_fixtures import plaintext_english_string
from tutorials.v1.support import tutorial_pretty as pretty
from tutorials.v1.support.scheduled_stream_lookup import (
    build_ciphertext,
    key_period13,
    sample_sequence,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _as_int_list(value: object) -> list[int] | None:
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value]
    return None


def _match_ratio(found: Sequence[int], expected: Sequence[int]) -> float:
    if len(found) != len(expected) or not expected:
        return 0.0
    return sum(
        int(actual) == int(wanted)
        for actual, wanted in zip(found, expected, strict=True)
    ) / len(expected)


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="ScheduledStreamLookup P13 plus supplied sequence",
        cipher="scheduled stream lookup",
        solver="beam",
        direction="rtl",
        expected_result="exact solve",
        uses_reference_stop_score=True,
    )
    # We supply the stream sequence here. RDP knows that part of the cipher;
    # it has to find the repeating key. Ordinary Vigenere doesn't have this
    # extra supplied sequence.
    sequence = sample_sequence(64)
    key_values = key_period13()
    expected_key_len = 13
    stop_score = 0.56
    direction = api.TextDirection.RIGHT_TO_LEFT
    cipher_spec = api.CipherSpec.periodic_with_fixed_stream(sequence, period=13)
    key_spec = api.KeySpec.repeating(length=expected_key_len)
    cipher_spec, key_spec, pt_idx, wli, _pt_runes, ct_idx_list, ct_runes, _key = (
        build_ciphertext(
            plaintext=plaintext_english_string,
            cipher_spec=cipher_spec,
            key_spec=key_spec,
            key_values=key_values,
            direction=direction,
        )
    )
    print("ScheduledStreamLookup real-solve problem")
    print(f"direction: {direction.value}")
    print(f"periodic key length: {expected_key_len}")
    print(f"sequence length: {len(sequence)}")
    print(f"ciphertext length: {len(ct_idx_list)}")
    print(
        f"ciphertext preview: {ct_runes[:160]}{('...' if len(ct_runes) > 160 else '')}"
    )
    # We'll score rune pairs and word-location pairs. Their weights decide how
    # much each contributes when comparing candidate plaintexts.
    scorer_params = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )
    # This stopping score was chosen for our constructed message. We don't
    # give the solver the key as a starting point. Width and plateau rounds
    # are useful settings to try when working with another message or
    # sequence.
    solver = api.SolverSpec.beam_search(
        width=72,
        rounds=0,
        target_score=stop_score,
        plateau_rounds=12,
        plateau_minimum_delta=0.0001,
        maximum_children_per_parent=29,
        seed=2026,
    )
    result = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli),
            cipher=cipher_spec,
            key_space=key_spec,
            solver=solver,
            scoring=scorer_params,
            initial_keys=None,
            telemetry_enabled=True,
            text_direction=direction,
            compute_device=api.ComputeDevice.CPU,
        )
    )
    found_key = _as_int_list(result.key or None)
    expected_key = [int(v) for v in key_values]
    if found_key is None:
        raise AssertionError("real solve did not return a key")
    key_ok = found_key == expected_key
    match_ratio = _match_ratio(result.plaintext, pt_idx)
    plaintext_ok = match_ratio == 1.0
    print(f"Expected key : {expected_key}")
    print(f"Found key    : {found_key}")
    print(f"Key accepted?: {key_ok}")
    print(f"Plaintext OK?: {plaintext_ok}")
    print(f"Match ratio: {match_ratio:.3f}")
    pretty.print_summary_spacer()
    api.display.print_result(result, options=api.display.SummaryOptions.for_tutorial())
    if not plaintext_ok:
        raise AssertionError("real solve did not recover the expected plaintext")
    if not key_ok:
        raise AssertionError("real solve did not recover the expected key")


if __name__ == "__main__":
    main()
