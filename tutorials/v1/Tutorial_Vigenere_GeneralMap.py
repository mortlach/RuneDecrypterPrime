import sys
from pathlib import Path

# Ensure repo root is importable when running this file directly
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, define_map
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string

# -*- coding: utf-8 -*-
"""
Tutorial: Vigenère via the General Map API

What it shows:
1. Define a Vigenère cell as a simple function: (pt, k) % 29.
2. Encode English text → rune indices (with spaces/WLI).
3. Encrypt with a short numeric key, repeat-to-length handled inline.
4. Tell the solver only the period, not the key.
5. Use the built-in pretty printer to show results.
"""
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


N = 29  # Rune alphabet
TUTORIAL_SEED = 12345

def vigenere_map(pt: int, k: int) -> int:
    return (pt + k) % N

def main():
    # Plaintext: a paragraph with spaces
    pt_en_sample = (
        "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE "
        "AND THE MARCH HARE AND THE HATTER WERE HAVING TEA AT IT "
        "A DORMOUSE WAS SITTING BETWEEN THEM FAST ASLEEP "
        "AND THE OTHER TWO WERE USING IT AS A CUSHION RESTING THEIR ELBOWS ON IT"
    )
    # test strgin from package
    pt_en = plaintext_english_string
    encoding_dir = Direction.RTL
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction=encoding_dir.value)

    # Cipher spec: Vigenère cell (pt,k) -> (pt+k)%29
    cipher = define_map(function=vigenere_map, N=N)

    # Encrypt with a short numeric key
    key_nums = [3, 1, 4, 1,5, 6]
    stream = [key_nums[i % len(key_nums)] for i in range(len(pt_idx))]
    ct_idx = [vigenere_map(p, k) for p, k in zip(pt_idx, stream)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    # Solver knows only the period (length of key), not the key itself
    key_spec   = KeySpec.repeat(len=len(key_nums))
    solve_spec = SolverSpec.beam(
        beam_width=24,
        stop_score=0.32,
        patience_rounds=6,
        patience_min_delta=1e-4,
        plateau_rounds=3,
        max_children_per_parent=16,
        verbose=True,
        progress_pct=1,
        print_progress=True,
        seed=TUTORIAL_SEED,
    )

    # Run solver (defaults handle wli from spaces in ct_runes)
    sol = run(
        text=ct_runes,
        cipher=cipher,
        key=key_spec,
        solver=solve_spec,
        scorer_params=dict(
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            include_char=True,
            use_word_breaks=True,
            encoding_dir=encoding_dir,
        ),
        wli_data=wli,
        encoding_dir=encoding_dir,
        telemetry_on=True,
    )

    recovered = getattr(sol, "plaintext_rune", "") or getattr(sol, "plaintext_str", "")
    snippet = str(recovered)
    preview = snippet[:120] + ("..." if len(snippet) > 120 else "")
    print("Recovered plaintext:", preview)

    # Pretty printer already formats everything (pt, ct, recovered, meta)
    print_run_report(
        title="Vigenere via General Map API",
        cipher="vigenere",
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.0",
        key_idx=key_nums,
        key_len=len(key_nums),
        pt_rune_ref=Runeglish.to_rune(pt_idx, wli),
    )

if __name__ == "__main__":
    main()
