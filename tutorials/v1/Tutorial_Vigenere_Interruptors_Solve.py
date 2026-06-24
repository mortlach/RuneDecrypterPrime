from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import (  # noqa: E402
    Direction,
    InterruptorConfig,
    KeySpec,
    NormalizedInput,
    RunSpec,
    SolverSpec,
    by_name,
    cipher_instance,
    print_rdp_result,
    run,
)
from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview  # noqa: E402
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary  # noqa: E402

"""
Tutorial variant: Vigenere interruptor solver search with the standard RDP printer.

The original tutorial remains unchanged; this variant proves the printer facade.
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
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(DEMO_TEXT, direction=direction.value)
    pt_arr = np.asarray(pt_idx, dtype=np.uint8)

    pool = _make_interruptor_pool(len(pt_idx))
    interruptors = _pick_interruptors(pool)
    if len(interruptors) < 2:
        raise ValueError("Need at least two interruptors for this tutorial")

    key_arr = np.asarray(KEY_NUMS, dtype=np.uint8)
    encrypt_cipher = cipher_instance(
        "vigenere",
        key_length=int(key_arr.size),
        text_transposition=direction.value,
    )

    ct_idx = encrypt_cipher.encrypt_single(plaintext=pt_arr, key=key_arr, interrupt_idx=interruptors)
    intr_values_pt = [int(pt_arr[i]) for i in interruptors]
    intr_values_ct = [int(ct_idx[i]) for i in interruptors]
    if intr_values_pt != intr_values_ct:
        raise ValueError("Interruptor symbols changed during encryption")

    ct_idx_list = [int(v) for v in ct_idx.tolist()]
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)

    print("Vigenere interruptor problem")
    print(f"direction: {direction.value}")
    print("Interruptor pool:", pool)
    print("Interruptor positions:", interruptors)
    print("Interruptor symbols:", intr_values_ct)
    print("Plaintext (preview):", pt_runes[:120] + ("..." if len(pt_runes) > 120 else ""))
    print("Ciphertext (preview):", ct_runes[:120] + ("..." if len(ct_runes) > 120 else ""))
    print_tutorial_debug_preview(label="plaintext", idx=pt_idx, wli=wli, direction=direction)
    print_tutorial_debug_preview(label="ciphertext", idx=ct_idx_list, wli=wli, direction=direction)

    interrupt_cfg = InterruptorConfig(
        mode="pool",
        pool=pool,
        min_count=len(interruptors),
        max_count=len(interruptors),
    )

    scorer_params = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={2: 0.3},
        wli_weights={2: 0.7},
        encoding_dir=direction,
    )
    display_scorer_params = {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "encoding_dir": direction.value,
        "char_order_2_weight": 0.3,
        "wli_order_2_weight": 0.7,
    }

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
    print_stop_summary("Vigenere Interruptors (solve)", stop)

    solver = SolverSpec.beam(
        beam_width=32,
        expand_mode="sweep",
        plateau_rounds=6,
        plateau_min_delta=1e-4,
        stop_score=stop.stop_score,
        progress_pct=10,
        print_progress=True,
        progress_preview_chars=120,
        seed=TUTORIAL_SEED,
    )
    key_spec = KeySpec.repeat(len=len(KEY_NUMS))
    cipher_spec = by_name.cipher("vigenere")
    display_spec = RunSpec(
        problem_input=NormalizedInput(ct_idx=ct_idx_list, wli=wli),
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        scorer="rune",
        scorer_params=display_scorer_params,
        encoding_dir=direction,
        telemetry_on=True,
    )

    result = run(
        text=ct_idx_list,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        interruptors=interrupt_cfg,
        return_solver_report=True,
    )

    found_key = getattr(result.solution, "key", []) or []
    found_core = found_key[: len(KEY_NUMS)]
    found_intr = [int(v) for v in found_key[len(KEY_NUMS) :] if int(v) >= 0]
    if found_key:
        print("Found key (core):", found_core)
        print("Found interruptors:", found_intr)

    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_Vigenere_Interruptors_Solve.py",
            "title": "Vigenere interruptor solver search pretty-print variant",
            "gate": "v1_release_pretty_print",
            "acceptance_kind": "exact",
            "min_match_ratio": 1.0,
            "uses_oracle_stop_score": True,
        },
    )


if __name__ == "__main__":
    main()
