from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
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
    InterruptorConfig,
)
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish

"""
Tutorial: Vigenere with interruptors (solver search)

This walkthrough:
1) Encode a short English plaintext into runes with WLI.
2) Insert interruptors at hidden positions; encrypt with Vigenere.
3) Provide a small interruptor pool and let beam search recover
   both the key and the interruptor positions.
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TUTORIAL_SEED = 2026
DEMO_TEXT = (
    "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE "
    "AND THE MARCH HARE AND THE HATTER WERE HAVING TEA AT IT"
)
KEY_NUMS = [7, 0, 13, 2]


def _make_interruptor_pool(length: int) -> list[int]:
    fractions = (0.12, 0.32, 0.52, 0.72)
    pool = sorted({int(length * frac) for frac in fractions})
    pool = [p for p in pool if 0 <= p < length]
    if len(pool) < 2:
        pool = list(range(min(length, 4)))
    return pool


def _pick_interruptors(pool: list[int]) -> list[int]:
    if len(pool) < 2:
        raise ValueError("Interruptor pool must include at least two positions")
    if len(pool) >= 4:
        picks = [pool[1], pool[-2]]
    else:
        picks = [pool[0], pool[-1]]
    return sorted(set(picks))


def main() -> None:
    direction = Direction.LTR
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        DEMO_TEXT,
        direction=direction.value,
    )
    pt_arr = np.asarray(pt_idx, dtype=np.uint8)

    pool = _make_interruptor_pool(len(pt_idx))
    interruptors = _pick_interruptors(pool)
    if len(interruptors) < 2:
        raise ValueError("Need at least two interruptors for this tutorial")

    key_arr = np.asarray(KEY_NUMS, dtype=np.uint8)
    cipher = cipher_instance(
        "vigenere",
        key_length=int(key_arr.size),
        text_transposition=direction.value,
    )

    ct_idx = cipher.encrypt_single(
        plaintext=pt_arr,
        key=key_arr,
        interrupt_idx=interruptors,
    )

    intr_values_pt = [int(pt_arr[i]) for i in interruptors]
    intr_values_ct = [int(ct_idx[i]) for i in interruptors]
    if intr_values_pt != intr_values_ct:
        raise ValueError("Interruptor symbols changed during encryption")

    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)

    print("Interruptor pool:", pool)
    print("Interruptor positions:", interruptors)
    print("Interruptor symbols:", intr_values_ct)
    print("Plaintext (preview):", pt_runes[:120] + ("..." if len(pt_runes) > 120 else ""))
    print("Ciphertext (preview):", ct_runes[:120] + ("..." if len(ct_runes) > 120 else ""))

    interrupt_cfg = InterruptorConfig(
        mode="pool",
        pool=pool,
        min_count=len(interruptors),
        max_count=len(interruptors),
    )

    solver = SolverSpec.beam(
        beam_width=32,
        expand_mode="sweep",
        plateau_rounds=6,
        plateau_min_delta=1e-4,
        stop_score=0.55,
        progress_pct=10,
        seed=TUTORIAL_SEED,
    )

    solution = run(
        text=ct_idx,
        cipher=by_name.cipher("vigenere"),
        key=KeySpec.repeat(len=len(KEY_NUMS)),
        solver=solver,
        scorer_params=dict(
            objective="pct.logp.win10",
            include_char=True,
            use_word_breaks=True,
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            encoding_dir=direction,
        ),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        interruptors=interrupt_cfg,
    )

    found_key = getattr(solution, "key", []) or []
    found_core = found_key[: len(KEY_NUMS)]
    found_intr = [int(v) for v in found_key[len(KEY_NUMS) :] if int(v) >= 0]
    if found_key:
        print("Found key (core):", found_core)
        print("Found interruptors:", found_intr)

    print_run_report(
        title="Vigenere with Interruptors (solver search)",
        cipher="vigenere",
        solution=solution,
        match_ok=None,
        app_version="tutorial-1.0",
        key_idx=KEY_NUMS + sorted(interruptors),
        key_len=len(KEY_NUMS) + len(interruptors),
        ct_idx=ct_idx.tolist(),
        ct_rune=ct_runes,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
        wli=wli,
    )


if __name__ == "__main__":
    main()
