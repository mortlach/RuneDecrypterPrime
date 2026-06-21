from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is importable when running this file directly
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import Direction, KeySpec, NormalizedInput, RunSpec, SolverSpec, define_map, print_rdp_result, run
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

"""
Tutorial variant: Vigenere via the General Map API with the standard RDP printer.

The original tutorial remains unchanged; this variant proves the printer facade.
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

N = 29
TUTORIAL_SEED = 12345


def vigenere_map(pt: int, k: int) -> int:
    return (pt + k) % N


def main() -> None:
    pt_en = plaintext_english_string
    encoding_dir = Direction.RTL
    pt_idx, wli, _pt_runes = Runeglish.encode_english_to_runes(pt_en, direction=encoding_dir.value)

    cipher = define_map(function=vigenere_map, N=N)
    key_nums = [3, 1, 4, 1, 5, 6]
    stream = [key_nums[i % len(key_nums)] for i in range(len(pt_idx))]
    ct_idx = [vigenere_map(p, k) for p, k in zip(pt_idx, stream)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    print("Vigenere general-map problem")
    print(f"direction: {encoding_dir.value}")
    print(f"ciphertext length: {len(ct_idx)}")
    print(f"key period: {len(key_nums)}")
    print(f"ciphertext preview: {ct_runes[:160]}{'...' if len(ct_runes) > 160 else ''}")

    scorer_params = dict(
        char_weights={2: 0.3},
        wli_weights={2: 0.7},
        include_char=True,
        use_word_breaks=True,
        encoding_dir=encoding_dir,
    )
    display_scorer_params = {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "encoding_dir": encoding_dir.value,
        "char_order_2_weight": 0.3,
        "wli_order_2_weight": 0.7,
    }

    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=encoding_dir,
        margin=0.02,
        min_score=0.50,
        fallback=0.54,
    )
    print_stop_summary("Vigenere Beam", stop)

    key_spec = KeySpec.repeat(len=len(key_nums))
    solve_spec = SolverSpec.beam(
        beam_width=24,
        stop_score=stop.stop_score,
        plateau_rounds=6,
        plateau_min_delta=1e-4,
        max_children_per_parent=16,
        verbose=True,
        progress_pct=1,
        print_progress=True,
        seed=TUTORIAL_SEED,
    )
    display_spec = RunSpec(
        problem_input=NormalizedInput(ct_idx=ct_idx, wli=wli),
        cipher=cipher,
        key=key_spec,
        solver=solve_spec,
        scorer="rune",
        scorer_params=display_scorer_params,
        encoding_dir=encoding_dir,
        telemetry_on=True,
    )

    result = run(
        text=ct_runes,
        cipher=cipher,
        key=key_spec,
        solver=solve_spec,
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=encoding_dir,
        telemetry_on=True,
        return_solver_report=True,
    )

    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_Vigenere_GeneralMap_PrettyPrint.py",
            "title": "Vigenere via General Map API pretty-print variant",
            "gate": "v1_release_pretty_print",
            "acceptance_kind": "min_match_ratio",
            "min_match_ratio": 1.0,
            "uses_oracle_stop_score": True,
        },
    )


if __name__ == "__main__":
    main()
