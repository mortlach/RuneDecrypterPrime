from __future__ import annotations

"""Vigenere non-trivial interruptor-search pretty-print tutorial."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np

from rune_decrypter_prime.api import Direction, InterruptorConfig, KeySpec, NormalizedInput, RunSpec, SolverSpec, by_name, cipher_instance, print_rdp_result, run
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TUTORIAL_SEED = 2027
INTERRUPTOR_SYMBOL = 27
INTERRUPTOR_TRUE_COUNT = 2
INTERRUPTOR_MIN = 0
INTERRUPTOR_MAX = 3
KEY_NUMS = [7, 0, 13, 2, 5, 21, 8]
MIN_MATCH_RATIO = 1.0


def _preview(text: str, limit: int = 160) -> str:
    return text[:limit] + ("..." if len(text) > limit else "")


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name='Vigenere interruptors non-trivial',
        cipher='vigenere interruptors',
        solver='hybrid',
        direction='ltr',
        expected_result='exact solve',
        uses_reference_stop_score=True,
    )
    direction = Direction.LTR
    pt_idx = [int(v) for v in plaintext1]
    wli = [list(pair) for pair in word_breaks1]

    interruptors = [i for i, v in enumerate(pt_idx) if v == INTERRUPTOR_SYMBOL]
    if len(interruptors) != INTERRUPTOR_TRUE_COUNT:
        raise ValueError(
            f"Expected {INTERRUPTOR_TRUE_COUNT} interruptors with symbol {INTERRUPTOR_SYMBOL}, "
            f"found {len(interruptors)}"
        )

    pt_arr = np.asarray(pt_idx, dtype=np.uint8)
    key_arr = np.asarray(KEY_NUMS, dtype=np.uint8)
    encrypt_cipher = cipher_instance(
        "vigenere",
        key_length=int(key_arr.size),
        text_transposition=direction.value,
    )

    ct_idx = encrypt_cipher.encrypt_single(
        plaintext=pt_arr,
        key=key_arr,
        interrupt_idx=interruptors,
    )
    ct_idx_list = [int(v) for v in ct_idx.tolist()]

    pool = sorted({i for i, v in enumerate(ct_idx_list) if v == INTERRUPTOR_SYMBOL})
    if not set(interruptors).issubset(set(pool)):
        raise ValueError("Interruptor positions not found in symbol-derived pool")

    pt_runes = Runeglish.to_rune(pt_idx, wli)
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)

    print("Vigenere non-trivial interruptor problem")
    print(f"encoding direction: {direction.value}")
    print("Interruptor symbol:", INTERRUPTOR_SYMBOL)
    print("Interruptor positions (true):", interruptors)
    print("Interruptor count range:", f"{INTERRUPTOR_MIN}..{INTERRUPTOR_MAX}")
    print("Interruptor pool size:", len(pool))
    print("Interruptor pool preview:", pool[:12])
    print("Plaintext preview:", _preview(pt_runes))
    print("Ciphertext preview:", _preview(ct_runes))
    print_tutorial_debug_preview(label="plaintext", idx=pt_idx, wli=wli, direction=direction)
    print_tutorial_debug_preview(label="ciphertext", idx=ct_idx_list, wli=wli, direction=direction)

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
    print_stop_summary("Vigenere Interruptors (non-trivial)", stop)

    solver = SolverSpec.beam(
        beam_width=64,
        expand_mode="sweep",
        plateau_rounds=8,
        plateau_min_delta=1e-4,
        stop_score=stop.stop_score,
        progress_pct=5,
        print_progress=True,
        progress_preview_chars=120,
        seed=TUTORIAL_SEED,
    )
    cipher_spec = by_name.cipher("vigenere")
    key_spec = KeySpec.repeat(len=len(KEY_NUMS))
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

    pretty.print_summary_spacer()
    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_Vigenere_Interruptors_NonTrivial.py",
            "title": "Vigenere non-trivial interruptor pretty-print variant",
            "gate": "v1_extended_pretty_print",
            "acceptance_kind": "exact",
            "min_match_ratio": MIN_MATCH_RATIO,
            "uses_oracle_stop_score": True,
        },
    )


if __name__ == "__main__":
    main()
