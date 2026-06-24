from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# Allow direct execution from the old tutorial folder without pip install.
_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import (
    run,
    KeySpec,
    SolverSpec,
    Direction,
    by_name,
    cipher_instance,
)
from rune_decrypter_prime.utils.interrupter import InterruptorManager
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

"""
Tutorial: Vigenere with interruptors (exact positions)

This walkthrough:
1) Defines a short plaintext (20 runes) and fixed interruptor positions.
2) Encrypts with Vigenere while removing interruptors and reinserting them unchanged.
3) Runs the pipeline with interruptors_exact and a known key (test_key).
4) Prints a compact report and verifies interruptor symbols were preserved.
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ALPHABET = 29
KEY = [7, 0, 13, 2, 0]
INTERRUPTORS = [2, 7, 13]
TUTORIAL_SEED = 2025


def _make_wli(length: int, word_len: int = 5) -> list[list[int]]:
    return [[i % word_len, word_len] for i in range(length)]


def main() -> None:
    direction = Direction.LTR
    pt_idx = np.array(
        [4, 20, 1, 3, 14, 25, 6, 8, 9, 10, 12, 17, 18, 2, 5, 7, 11, 13, 15, 19],
        dtype=np.uint8,
    )
    wli = _make_wli(int(pt_idx.size), word_len=5)
    pt_runes = Runeglish.to_rune(pt_idx.tolist(), wli)

    key_arr = np.asarray(KEY, dtype=np.uint8)
    key_len = int(key_arr.size)
    cipher = cipher_instance(
        "vigenere",
        key_length=key_len,
        text_transposition=direction.value,
    )

    ct_idx = cipher.encrypt_single(
        plaintext=pt_idx,
        key=key_arr,
        interrupt_idx=INTERRUPTORS,
    )
    ct_idx_list = ct_idx.tolist()
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)

    intr_values_pt = [int(pt_idx[i]) for i in INTERRUPTORS]
    intr_values_ct = [int(ct_idx[i]) for i in INTERRUPTORS]
    if intr_values_pt != intr_values_ct:
        raise ValueError("Interruptor symbols changed during encryption")

    intr_mgr = InterruptorManager()
    pt_core, info = intr_mgr.remove_from(pt_idx, possible_idx=INTERRUPTORS)
    ct_core, _ = intr_mgr.remove_from(ct_idx, possible_idx=INTERRUPTORS)

    print("Interruptor positions:", INTERRUPTORS)
    print("Interruptor symbols:", intr_values_ct)
    print("Plaintext (runes):", pt_runes)
    print("Ciphertext (runes):", ct_runes)
    print("Core length:", int(pt_core.size), "->", int(ct_core.size))
    print("Core interruptors removed:", info.idx.tolist())

    scorer_params = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={2: 0.3},
        wli_weights={2: 0.7},
        encoding_dir=direction,
    )

    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.45,
        fallback=0.5,
    )
    print_stop_summary("Vigenere Interruptors", stop)

    solver = SolverSpec.beam(
        beam_width=1,
        test_key=key_arr.tolist(),
        stop_score=stop.stop_score,
        plateau_rounds=4,
        plateau_min_delta=1e-4,
        progress_pct=1,
        seed=TUTORIAL_SEED,
    )
    solution = run(
        text=ct_idx,
        cipher=by_name.cipher("vigenere"),
        key=KeySpec.repeat(len=key_len),
        solver=solver,
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        interruptors_exact=INTERRUPTORS,
    )

    print_run_report(
        title="Vigenere with Interruptors (exact positions)",
        cipher="vigenere",
        solution=solution,
        match_ok=None,
        app_version="tutorial-1.0",
        key_idx=KEY,
        key_len=key_len,
        ct_idx=ct_idx_list,
        ct_rune=ct_runes,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx.tolist(),
        wli=wli,
    )


if __name__ == "__main__":
    main()
