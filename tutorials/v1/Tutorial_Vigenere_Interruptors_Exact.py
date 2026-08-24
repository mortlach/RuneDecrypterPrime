from __future__ import annotations

"""Known-position Vigenere interruptor interface demonstration.

This is the tiny, explicit-position interruptor example. It demonstrates the
mechanics of removing/reinserting interruptors and prints the final run through
the standard RDP printer facade.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, NormalizedInput, RunSpec, SolverSpec, by_name, cipher_instance, print_rdp_result, run
from rune_decrypter_prime.utils.interrupter import InterruptorManager
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALPHABET = 29
KEY = [7, 0, 13, 2, 0]
INTERRUPTORS = [2, 7, 13]
TUTORIAL_SEED = 2025
MIN_MATCH_RATIO = 1.0


def _make_wli(length: int, word_len: int = 5) -> list[list[int]]:
    return [[i % word_len, word_len] for i in range(length)]


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name='Vigenere known-position interruptor interface demonstration',
        cipher='vigenere interruptors',
        solver='beam',
        direction='ltr',
        expected_result='exact solve',
        uses_reference_stop_score=True,
    )
    direction = Direction.LTR
    pt_idx = np.array(
        [4, 20, 1, 3, 14, 25, 6, 8, 9, 10, 12, 17, 18, 2, 5, 7, 11, 13, 15, 19],
        dtype=np.uint8,
    )
    pt_idx_list = [int(v) for v in pt_idx.tolist()]
    wli = _make_wli(int(pt_idx.size), word_len=5)
    pt_runes = Runeglish.to_rune(pt_idx_list, wli)

    key_arr = np.asarray(KEY, dtype=np.uint8)
    key_len = int(key_arr.size)
    encrypt_cipher = cipher_instance(
        "vigenere",
        key_length=key_len,
        text_transposition=direction.value,
    )

    ct_idx = encrypt_cipher.encrypt_single(
        plaintext=pt_idx,
        key=key_arr,
        interrupt_idx=INTERRUPTORS,
    )
    ct_idx_list = [int(v) for v in ct_idx.tolist()]
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)

    intr_values_pt = [int(pt_idx[i]) for i in INTERRUPTORS]
    intr_values_ct = [int(ct_idx[i]) for i in INTERRUPTORS]
    if intr_values_pt != intr_values_ct:
        raise ValueError("Interruptor symbols changed during encryption")

    intr_mgr = InterruptorManager()
    pt_core, info = intr_mgr.remove_from(pt_idx, possible_idx=INTERRUPTORS)
    ct_core, _ = intr_mgr.remove_from(ct_idx, possible_idx=INTERRUPTORS)

    print("Vigenere known-position interruptor interface demonstration")
    print("This is not unknown-position solver qualification.")
    print(f"encoding direction: {direction.value}")
    print("Interruptor positions:", INTERRUPTORS)
    print("Interruptor symbols:", intr_values_ct)
    print("Plaintext (runes):", pt_runes)
    print("Ciphertext (runes):", ct_runes)
    print("Core length:", int(pt_core.size), "->", int(ct_core.size))
    print_tutorial_debug_preview(label="plaintext", idx=pt_idx_list, wli=wli, direction=direction)
    print_tutorial_debug_preview(label="ciphertext", idx=ct_idx_list, wli=wli, direction=direction)
    print("Core interruptors removed:", info.idx.tolist())

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
        pt_idx_list,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.45,
        fallback=0.5,
    )
    print_stop_summary("Vigenere Interruptors exact", stop)

    solver = SolverSpec.beam(
        beam_width=1,
        test_key=key_arr.tolist(),
        stop_score=stop.stop_score,
        plateau_rounds=4,
        plateau_min_delta=1e-4,
        progress_pct=1,
        print_progress=True,
        progress_preview_chars=120,
        seed=TUTORIAL_SEED,
    )
    cipher_spec = by_name.cipher("vigenere")
    key_spec = KeySpec.repeat(len=key_len)
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
        interruptors_exact=INTERRUPTORS,
        return_solver_report=True,
    )

    pretty.print_summary_spacer()
    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=pt_idx_list,
        tutorial_entry={
            "path": "Tutorial_Vigenere_Interruptors_Exact.py",
            "title": "Vigenere known-position interruptor interface demonstration",
            "gate": "v1_smoke_pretty_print",
            "acceptance_kind": "exact",
            "min_match_ratio": MIN_MATCH_RATIO,
            "uses_oracle_stop_score": True,
        },
    )


if __name__ == "__main__":
    main()
