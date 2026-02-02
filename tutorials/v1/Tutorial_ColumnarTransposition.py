from __future__ import annotations
import sys
from pathlib import Path

# Ensure repo root on sys.path so the package imports resolve when run directly
_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string

# -*- coding: utf-8 -*-
"""
Tutorial: Columnar Transposition (permutation key, no WLI)

- Classic row-fill / column-read transposition.
- Ciphertext has NO word-break info; the solver must work without WLI.
- Key is a permutation of column indices indicating READ ORDER of columns.
"""

from typing import List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345



def encrypt_columnar(pt: str, key: List[int]) -> str:
    """Row-fill, then read columns in the order given by 'key' (no spaces)."""
    K = len(key)
    rows = (len(pt) + K - 1) // K
    table = [list(pt[i * K : i * K + K]) for i in range(rows)]
    out_chars: List[str] = []
    for col in key:
        for r in range(rows):
            if col < len(table[r]):
                out_chars.append(table[r][col])
    return "".join(out_chars)


def main():
    # encoding direction
    direction = Direction.RTL

    # English plaintext ? runes (then strip spaces for columnar)
    pt_en = plaintext_english_string
    pt_idx, wli_pt, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction=direction.value)
    pt_runes_nosp = pt_runes.replace(" ", "")
    wli = None  # IMPORTANT: no WLI for this cipher

    print(f"pt_runes = {pt_runes_nosp}")

    # True key (read-order permutation)
    key_true = [3,6, 1, 4, 2, 0, 5]

    # Encrypt (no spaces)
    ct_runes = encrypt_columnar(pt_runes_nosp, key_true)
    print(f"ct_runes = {ct_runes}")
    ct_idx = Runeglish.rune_to_pos(ct_runes)
    print(f"ct_idx = {ct_idx}")

    # Build cipher + key spec
    cipher   = by_name.cipher("columnar")
    key_spec = KeySpec.permutation(len=len(key_true))

    # Hybrid config
    solve_spec = SolverSpec.hybrid(
        use_beam=True,
        beam_width=96,
        rounds=6,
        expand_mode="sample",
        sample_per_parent=48,
        top_parents_factor=0.4,
        progress_pct=2,
        print_progress=True,

        ga=dict(
            pop_size=96,
            generations=40,
            elite_frac=0.1,
            cx_frac=0.85,
            mut_prob=0.3,
            tournament_k=3,
            plateau_rounds=12,
            plateau_min_delta=1e-4,
            stop_score=0.503,
            print_progress=True,
        ),
        sa=dict(
            sa_iters=3000,
            sa_init_temp=0.95,
            sa_min_temp=1e-4,
            sa_cooling=0.997,
            plateau_rounds=300,
            plateau_min_delta=1e-4,
            local_improve_on_accept=True,
            stop_score=0.503,
            print_progress=True,
        ),

        seed=TUTORIAL_SEED,
        verbose=True,
        log_interval=10,
        plateau_rounds=8,
        plateau_min_delta=1e-4,
        stop_score=0.503,
    )

    # Scorer tuned for NO word-breaks
    scorer_params = {
        "objective": "pct.logp.win10",
        "char_weights": {2: 1.0},
        "wli_weights": {},
        "use_word_breaks": False,  # force no WLI
        "include_char": True,
        "encoding_dir": direction,
    }

    # Solve with the API
    sol = run(
        text=ct_runes,
        cipher=cipher,
        key=key_spec,
        solver=solve_spec,
        device="cpu",
        scorer="rune",
        scorer_params=scorer_params,
        wli_data=None,
        force_no_wli=True,
        encoding_dir=direction,
        telemetry_on=True,
    )

    # Pretty report
    recovered = getattr(sol, "plaintext_rune", "") or getattr(sol, "plaintext_str", "")
    snippet = str(recovered)
    preview = snippet[:120] + ("..." if len(snippet) > 120 else "")
    print("Recovered plaintext:", preview)
    print_run_report(
        title="Columnar Transposition",
        cipher="columnar",
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.0",
        key_idx=key_true,
        key_len=len(key_true),
        pt_rune_ref=pt_runes_nosp,
    )

if __name__ == "__main__":
    main()

