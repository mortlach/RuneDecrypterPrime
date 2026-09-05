"""Vigenere general map.

See the example catalogue for assets, runtime and reference use.
"""

from __future__ import annotations

import sys

from rdp import api
from rdp.data.runeglish import Runeglish
from tutorials.v1.data.plaintext_fixtures import plaintext_english_string
from tutorials.v1.support import tutorial_pretty as pretty
from tutorials.v1.support.tutorial_output import print_tutorial_debug_preview
from tutorials.v1.support.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
N = 29
TUTORIAL_SEED = 12345
MIN_MATCH_RATIO = 1.0


def vigenere_map(pt: int, k: int) -> int:
    return (pt + k) % N


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Vigenere via General Map API",
        cipher="vigenere general map",
        solver="beam",
        direction="rtl",
        expected_result="exact solve",
        uses_reference_stop_score=True,
    )
    pt_en = plaintext_english_string
    encoding_dir = api.TextDirection.RIGHT_TO_LEFT
    pt_idx, wli, _pt_runes = Runeglish.encode_english_to_runes(
        pt_en, direction=encoding_dir
    )
    cipher = api.experimental.define_cipher_map(vigenere_map, alphabet_size=N)
    key_nums = [3, 1, 4, 1, 5, 6]
    stream = [key_nums[i % len(key_nums)] for i in range(len(pt_idx))]
    ct_idx = [vigenere_map(p, k) for p, k in zip(pt_idx, stream)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)
    print("Vigenere general-map problem")
    print(f"direction: {encoding_dir.value}")
    print(f"ciphertext length: {len(ct_idx)}")
    print(f"key period: {len(key_nums)}")
    print(
        f"ciphertext preview: {ct_runes[:160]}{('...' if len(ct_runes) > 160 else '')}"
    )
    print_tutorial_debug_preview(
        label="plaintext", idx=pt_idx, wli=wli, direction=encoding_dir
    )
    print_tutorial_debug_preview(
        label="ciphertext", idx=ct_idx, wli=wli, direction=encoding_dir
    )
    scorer_params = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
    )
    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=encoding_dir,
        margin=0.02,
        min_score=0.5,
        fallback=0.54,
    )
    print_stop_summary("Vigenere Beam", stop)
    key_spec = api.KeySpec.repeating(length=len(key_nums))
    solve_spec = api.SolverSpec.beam_search(
        width=24,
        target_score=stop.stop_score,
        plateau_rounds=6,
        plateau_minimum_delta=0.0001,
        maximum_children_per_parent=16,
        seed=TUTORIAL_SEED,
        rounds=0,
    )
    request = api.RunSpec(
        problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli),
        cipher=cipher,
        key_space=key_spec,
        solver=solve_spec,
        scoring=scorer_params,
        telemetry_enabled=True,
        text_direction=encoding_dir,
    )
    result = api.run(request)
    recovered = [int(value) for value in result.plaintext]
    match_ratio = sum(a == b for a, b in zip(recovered, pt_idx, strict=True)) / len(
        pt_idx
    )
    print(f"Match ratio: {match_ratio:.3f}")
    pretty.print_summary_spacer()
    api.display.print_result(
        result, spec=request, options=api.display.SummaryOptions.for_tutorial()
    )
    if match_ratio < MIN_MATCH_RATIO:
        raise AssertionError("general-map tutorial did not recover exact plaintext")


if __name__ == "__main__":
    main()
