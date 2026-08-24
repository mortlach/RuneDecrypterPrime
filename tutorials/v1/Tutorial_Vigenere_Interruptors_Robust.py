from __future__ import annotations

"""Qualification-derived Vigenere interruptor-pool Beam tutorial."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np

from rune_decrypter_prime.api import (
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
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.runeglish import Runeglish

DIRECTION = Direction.LTR
TRUE_KEY = [7, 0, 13, 2, 5, 21, 8]
TRUE_INTERRUPTORS = [190, 194]
INTERRUPTOR_COUNT = 2
INTERRUPTOR_POOL = [71, 108, 156, 190, 194, 231, 278, 315]
SOLVER_SEED = 20260822
BEAM_WIDTH = 64
RESTARTS = 3
SCORER_PARAMS = {
    "objective": "pct.logp.win10",
    "include_char": True,
    "use_word_breaks": True,
    "char_weights": {2: 0.30},
    "wli_weights": {2: 0.70},
}
DISPLAY_SCORER_PARAMS = {
    "objective": "pct.logp.win10",
    "include_char": True,
    "use_word_breaks": True,
    "encoding_dir": DIRECTION.value,
    "char_order_2_weight": 0.30,
    "wli_order_2_weight": 0.70,
}


def _ints(value: object) -> list[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [int(item) for item in value]  # type: ignore[arg-type]


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Vigenere interruptors robust three-restart Beam search",
        cipher="vigenere interruptors", solver="beam", direction=DIRECTION.value,
        expected_result="exact solve", uses_reference_stop_score=False,
    )
    pt_idx = [int(v) for v in plaintext1]
    wli = [list(pair) for pair in word_breaks1]
    if max(INTERRUPTOR_POOL) >= len(pt_idx):
        raise ValueError("interruptor tutorial fixture is shorter than its search pool")
    cipher_spec = by_name.cipher("vigenere", key_len=len(TRUE_KEY))
    cipher = cipher_instance(
        "vigenere", key_length=len(TRUE_KEY), text_transposition=DIRECTION.value
    )
    ciphertext = cipher.encrypt_single(
        plaintext=np.asarray(pt_idx, dtype=np.uint8),
        key=np.asarray(TRUE_KEY, dtype=np.uint8),
        interrupt_idx=TRUE_INTERRUPTORS,
    )
    solver = SolverSpec.beam(
        beam_width=BEAM_WIDTH,
        restarts=RESTARTS,
        expand_mode="sweep",
        plateau_rounds=10,
        seed=SOLVER_SEED,
    )
    search = InterruptorConfig(
        mode="pool",
        pool=INTERRUPTOR_POOL,
        min_count=INTERRUPTOR_COUNT,
        max_count=INTERRUPTOR_COUNT,
    )

    print("Robust Vigenere interruptor qualification-derived tutorial")
    print("recipe: vigenere_interruptors_char2_wli2_beam3_v1")
    print(f"Beam width / restarts: {BEAM_WIDTH} / {RESTARTS}")
    print("scorer: char2=0.30, WLI2=0.70")
    print(f"interruptor search pool: {INTERRUPTOR_POOL}")
    print(f"deterministic solver seed: {SOLVER_SEED}")

    result = run(
        text=_ints(ciphertext),
        cipher=cipher_spec,
        key=KeySpec.repeat(len=len(TRUE_KEY)),
        solver=solver,
        scorer="rune",
        scorer_params={**SCORER_PARAMS, "encoding_dir": DIRECTION},
        wli_data=wli,
        encoding_dir=DIRECTION,
        interruptors=search,
        telemetry_on=True,
        return_solver_report=True,
    )

    recovered_plaintext = _ints(result.solution.plaintext_idx)
    recovered_values = _ints(result.solution.key)
    recovered_key = recovered_values[: len(TRUE_KEY)]
    recovered_interruptors = sorted(recovered_values[len(TRUE_KEY) :])
    plaintext_match = sum(
        a == b for a, b in zip(recovered_plaintext, pt_idx, strict=True)
    ) / len(pt_idx)
    key_match = recovered_key == TRUE_KEY
    interruptor_match = recovered_interruptors == TRUE_INTERRUPTORS
    recovered_runes = Runeglish.to_rune(recovered_plaintext, wli)
    print(f"solver score: {float(result.solution.score):.6f}")
    print(f"stop reason: {result.solver_report.stop_reason}")
    print(f"recovered plaintext: {recovered_runes[:240]}{'...' if len(recovered_runes) > 240 else ''}")
    print(f"recovered key: {recovered_key}")
    print(f"plaintext match: {plaintext_match:.3f}")
    print(f"key match: {key_match}")
    print(f"interruptor match: {interruptor_match}")
    print(f"recovered interruptors: {recovered_interruptors}")
    print(f"Match ratio: {plaintext_match:.3f}")
    pretty.print_summary_spacer()
    print_rdp_result(
        result,
        spec=RunSpec(
            problem_input=NormalizedInput(ct_idx=_ints(ciphertext), wli=wli),
            cipher=cipher_spec,
            key=KeySpec.repeat(len=len(TRUE_KEY)),
            solver=solver,
            scorer="rune",
            scorer_params=DISPLAY_SCORER_PARAMS,
            encoding_dir=DIRECTION,
            telemetry_on=True,
        ),
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_Vigenere_Interruptors_Robust.py",
            "title": "Vigenere interruptors robust three-restart Beam search",
            "gate": "v1_extended",
            "acceptance_kind": "exact",
            "min_match_ratio": 1.0,
            "uses_oracle_stop_score": False,
        },
    )
    if len(TRUE_INTERRUPTORS) != INTERRUPTOR_COUNT:
        raise AssertionError("generated fixture does not contain the declared interruptor count")
    if plaintext_match != 1.0 or not key_match or not interruptor_match:
        raise AssertionError("robust interruptor tutorial did not recover exact truth")


if __name__ == "__main__":
    main()
