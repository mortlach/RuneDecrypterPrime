"""Find a Vigenere key when the interruptor positions are already known.

We tell RDP which positions to leave unchanged, then search for the repeating
key and compare the recovered message with the original.
"""

from __future__ import annotations

import sys

import numpy as np

from rdp import api
from rdp.data.runeglish import Runeglish
from tutorials.v1.data.two_period_cribs_demo import encrypt_interruptor_fixture
from tutorials.v1.support import tutorial_pretty as pretty
from tutorials.v1.support.tutorial_output import print_tutorial_debug_preview
from tutorials.v1.support.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
KEY = [7, 0, 13, 2, 0]
INTERRUPTORS = [2, 7, 13]
TUTORIAL_SEED = 2025
MIN_MATCH_RATIO = 1.0
DEMO_TEXT = (
    "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE AND THE "
    "MARCH HARE AND THE HATTER WERE HAVING TEA AT IT"
)


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Vigenere known-position interruptor interface demonstration",
        cipher="vigenere interruptors",
        solver="beam",
        direction="ltr",
        expected_result="exact solve",
        uses_reference_stop_score=True,
    )
    direction = api.TextDirection.LEFT_TO_RIGHT
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        DEMO_TEXT, direction=direction
    )
    pt_idx_list = [int(v) for v in pt_idx]
    pt_arr = np.asarray(pt_idx_list, dtype=np.uint8)
    key_arr = np.asarray(KEY, dtype=np.uint8)
    key_len = int(key_arr.size)
    encrypt_cipher = api.CipherSpec.vigenere(alphabet_size=29)
    ct_idx = encrypt_interruptor_fixture(
        pt_arr,
        cipher=encrypt_cipher,
        key=tuple(int(_concrete_key_value) for _concrete_key_value in key_arr),
        interruptor_positions=INTERRUPTORS,
    )
    ct_idx_list = [int(v) for v in ct_idx.tolist()]
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)
    intr_values_pt = [int(pt_arr[i]) for i in INTERRUPTORS]
    intr_values_ct = [int(ct_idx[i]) for i in INTERRUPTORS]
    if intr_values_pt != intr_values_ct:
        raise ValueError("Interruptor symbols changed during encryption")
    print("Vigenere known-position interruptor interface demonstration")
    print("This is not unknown-position solver qualification.")
    print(
        "The reference key is used only to construct the fixture, not supplied to the solver."
    )
    print(f"encoding direction: {direction.value}")
    print("Interruptor positions:", INTERRUPTORS)
    print("Interruptor symbols:", intr_values_ct)
    print("Plaintext (runes):", pt_runes)
    print("Ciphertext (runes):", ct_runes)
    print("Core length:", len(pt_idx_list) - len(INTERRUPTORS))
    print_tutorial_debug_preview(
        label="plaintext", idx=pt_idx_list, wli=wli, direction=direction
    )
    print_tutorial_debug_preview(
        label="ciphertext", idx=ct_idx_list, wli=wli, direction=direction
    )
    print("Exact interruptors handled by RunSpec:", INTERRUPTORS)
    scorer_params = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )
    stop = oracle_stop_score(
        pt_idx_list,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.45,
        fallback=0.5,
    )
    print_stop_summary("Vigenere Interruptors exact", stop)
    solver = api.SolverSpec.beam_search(
        width=32,
        expansion=api.advanced.BeamExpansionMode.SWEEP,
        target_score=stop.stop_score,
        plateau_rounds=6,
        plateau_minimum_delta=0.0001,
        seed=TUTORIAL_SEED,
        rounds=0,
    )
    cipher_spec = api.CipherSpec.vigenere(alphabet_size=29)
    key_spec = api.KeySpec.repeating(length=key_len)
    interruptors = api.InterruptorConfig.exact(INTERRUPTORS)
    request = api.RunSpec(
        problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli),
        cipher=cipher_spec,
        key_space=key_spec,
        solver=solver,
        scoring=scorer_params,
        telemetry_enabled=True,
        text_direction=direction,
        interruptors=interruptors,
    )
    result = api.run(request)
    recovered = [int(value) for value in result.plaintext]
    match_ratio = sum(
        a == b for a, b in zip(recovered, pt_idx_list, strict=True)
    ) / len(pt_idx_list)
    print(f"Match ratio: {match_ratio:.3f}")
    pretty.print_summary_spacer()
    api.display.print_result(
        result, spec=request, options=api.display.SummaryOptions.for_tutorial()
    )
    if match_ratio < MIN_MATCH_RATIO:
        raise AssertionError(
            "known-position interruptor tutorial did not recover exact plaintext"
        )


if __name__ == "__main__":
    main()
