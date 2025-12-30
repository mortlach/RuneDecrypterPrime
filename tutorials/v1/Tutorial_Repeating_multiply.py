from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, define_map
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1_rev, word_breaks1_rev
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish

"""
Tutorial: Repeating Multiply (mod 29) via Generic Map

What it shows:
1) Use the reverse-encoded plaintext sample with WLI from data.
2) Define a multiplicative map: ct = (pt * k) % 29.
3) Encrypt with a repeating key of length 13 (values 1..28).
4) Solve with the generic map + repeating-key search.
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

N = 29
TUTORIAL_SEED = 12345
KEY_LEN = 13


def mult_map(pt: int, k: int) -> int:
    return (pt * k) % N


def main() -> None:
    rng = np.random.default_rng(TUTORIAL_SEED)
    key_nums = rng.integers(1, N, size=KEY_LEN).tolist()  # avoid 0 to keep the map invertible

    pt_idx = list(plaintext1_rev)
    wli = list(word_breaks1_rev)

    pt_runes = Runeglish.to_rune(pt_idx, wli)
    pt_preview = pt_runes[:120] + ("..." if len(pt_runes) > 120 else "")
    print("Plaintext preview:", pt_preview)

    stream = [key_nums[i % KEY_LEN] for i in range(len(pt_idx))]
    ct_idx = [(p * k) % N for p, k in zip(pt_idx, stream)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)
    ct_preview = ct_runes[:120] + ("..." if len(ct_runes) > 120 else "")
    print("Ciphertext preview:", ct_preview)

    cipher = define_map(function=mult_map, N=N)
    key_spec = KeySpec.repeat(len=KEY_LEN)

    solve_spec = SolverSpec.beam(
        beam_width=32,
        max_children_per_parent=24,
        plateau_rounds=8,
        plateau_min_delta=1e-4,
        stop_score=0.55,
        verbose=True,
        progress_pct=2,
        print_progress=True,
        seed=TUTORIAL_SEED,
    )

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
            encoding_dir=Direction.RTL,
        ),
        wli_data=wli,
        encoding_dir=Direction.RTL,
        telemetry_on=True,
    )

    recovered = getattr(sol, "plaintext_rune", "") or getattr(sol, "plaintext_str", "")
    rec_preview = str(recovered)
    rec_preview = rec_preview[:120] + ("..." if len(rec_preview) > 120 else "")
    print("Recovered plaintext preview:", rec_preview)

    print_run_report(
        title="Repeating Multiply (mod 29)",
        cipher="user_map2",
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.0",
        key_idx=key_nums,
        key_len=KEY_LEN,
        pt_rune_ref=Runeglish.to_rune(pt_idx, wli),
    )


if __name__ == "__main__":
    main()
