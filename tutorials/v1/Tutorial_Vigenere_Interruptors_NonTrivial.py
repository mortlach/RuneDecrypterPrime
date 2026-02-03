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
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

"""
Tutorial: Vigenere with interruptors (non-trivial)
Tag: non_trivial

This walkthrough:
1) Uses canonical plaintext1 from the data folder (long text, real WLI).
2) Chooses interruptors by symbol value (27) at two positions.
3) Builds a candidate pool by scanning ciphertext for symbol 27.
4) Solves for both the Vigenere key and interruptor positions.
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TUTORIAL_SEED = 2027
INTERRUPTOR_SYMBOL = 27
INTERRUPTOR_TRUE_COUNT = 2
INTERRUPTOR_MIN = 0
INTERRUPTOR_MAX = 3
INTERRUPTOR_SENTINEL = -1
KEY_NUMS = [7, 0, 13, 2, 5, 21, 8]


def _preview(text: str, limit: int = 120) -> str:
    return text[:limit] + ("..." if len(text) > limit else "")


def main() -> None:
    direction = Direction.LTR
    pt_idx = list(plaintext1)
    wli = list(word_breaks1)

    interruptors = [i for i, v in enumerate(pt_idx) if v == INTERRUPTOR_SYMBOL]
    if len(interruptors) != INTERRUPTOR_TRUE_COUNT:
        raise ValueError(
            f"Expected {INTERRUPTOR_TRUE_COUNT} interruptors with symbol {INTERRUPTOR_SYMBOL}, "
            f"found {len(interruptors)}"
        )

    pt_arr = np.asarray(pt_idx, dtype=np.uint8)
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
    ct_idx_list = ct_idx.tolist()

    pool = sorted({i for i, v in enumerate(ct_idx_list) if v == INTERRUPTOR_SYMBOL})
    if not set(interruptors).issubset(set(pool)):
        raise ValueError("Interruptor positions not found in symbol-derived pool")

    pt_runes = Runeglish.to_rune(pt_idx, wli)
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)

    print("Interruptor symbol:", INTERRUPTOR_SYMBOL)
    print("Interruptor positions (true):", interruptors)
    print("Interruptor count range:", f"{INTERRUPTOR_MIN}..{INTERRUPTOR_MAX}")
    print("Interruptor pool size:", len(pool))
    print("Interruptor pool preview:", pool[:12])
    print("Plaintext preview:", _preview(pt_runes))
    print("Ciphertext preview:", _preview(ct_runes))

    interrupt_cfg = InterruptorConfig(
        mode="pool",
        pool=pool,
        min_count=INTERRUPTOR_MIN,
        max_count=INTERRUPTOR_MAX,
    )

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
        min_score=0.50,
        fallback=0.55,
    )
    print_stop_summary("Vigenere Interruptors (non-trivial)", stop)

    solver = SolverSpec.beam(
        beam_width=64,
        expand_mode="sweep",
        plateau_rounds=8,
        plateau_min_delta=1e-4,
        stop_score=stop.stop_score,
        progress_pct=5,
        seed=TUTORIAL_SEED,
    )

    solution = run(
        text=ct_idx,
        cipher=by_name.cipher("vigenere"),
        key=KeySpec.repeat(len=len(KEY_NUMS)),
        solver=solver,
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        interruptors=interrupt_cfg,
    )

    print_run_report(
        title="Vigenere with Interruptors (non-trivial)",
        cipher="vigenere",
        solution=solution,
        match_ok=None,
        app_version="tutorial-1.0",
        key_idx=KEY_NUMS + interruptors + [INTERRUPTOR_SENTINEL],
        key_len=len(KEY_NUMS) + INTERRUPTOR_MAX,
        ct_idx=ct_idx_list,
        ct_rune=ct_runes,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
        wli=wli,
        interruptors_ref=interruptors,
    )


if __name__ == "__main__":
    main()
