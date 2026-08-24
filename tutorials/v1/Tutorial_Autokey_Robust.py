from __future__ import annotations

"""Qualification-derived Autokey Beam tutorial.

The solver receives the ciphertext and seed length, but never the true seed.
Truth is inspected only after the solver has returned.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np

from rune_decrypter_prime.api import (
    Direction,
    KeySpec,
    NormalizedInput,
    RunSpec,
    SolverSpec,
    by_name,
    cipher_instance,
    print_rdp_result,
    run,
)
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty

DIRECTION = Direction.RTL
TRUE_SEED = [6, 1, 4, 17, 3, 22, 9, 12]
SOLVER_SEED = 20260822
BEAM_WIDTH = 96
ROUNDS = 32
RESTARTS = 3
SCORER_PARAMS = {
    "objective": "pct.logp.win10",
    "include_char": False,
    "use_word_breaks": True,
    "char_weights": {},
    "wli_weights": {1: 0.30, 2: 0.70},
}
DISPLAY_SCORER_PARAMS = {
    "objective": "pct.logp.win10",
    "include_char": False,
    "use_word_breaks": True,
    "encoding_dir": DIRECTION.value,
    "wli_order_1_weight": 0.30,
    "wli_order_2_weight": 0.70,
}


def _ints(value: object) -> list[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [int(item) for item in value]  # type: ignore[arg-type]


def _match(found: list[int], expected: list[int]) -> float:
    return sum(a == b for a, b in zip(found, expected, strict=True)) / len(expected)


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Autokey robust Beam solve", cipher="autokey", solver="beam",
        direction=DIRECTION.value, expected_result="exact solve",
        uses_reference_stop_score=False,
    )
    plaintext = plaintext_english_string
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(plaintext, direction=DIRECTION.value)
    seed_length = len(TRUE_SEED)
    cipher_spec = by_name.cipher("autokey", seed_len=seed_length, alphabet_size=29)
    cipher = cipher_instance("autokey", seed_length=seed_length, alphabet_size=29)
    ciphertext = cipher.encrypt_single(
        plaintext=np.asarray(pt_idx, dtype=np.uint8),
        key=np.asarray(TRUE_SEED, dtype=np.uint8),
    )
    solver = SolverSpec.beam(
        beam_width=BEAM_WIDTH,
        rounds=ROUNDS,
        restarts=RESTARTS,
        expand_mode="sweep",
        plateau_rounds=0,
        seed=SOLVER_SEED,
    )

    print("Robust Autokey qualification-derived tutorial")
    print("recipe: autokey_wli12_beam_v1")
    print(f"direction: {DIRECTION.value}")
    print(f"seed length: {seed_length}")
    print(f"Beam width / rounds / restarts: {BEAM_WIDTH} / {ROUNDS} / {RESTARTS}")
    print("scorer: WLI1=0.30, WLI2=0.70; character lane disabled")
    print(f"deterministic solver seed: {SOLVER_SEED}")

    result = run(
        text=_ints(ciphertext),
        cipher=cipher_spec,
        key=KeySpec.repeat(len=seed_length),
        solver=solver,
        scorer="rune",
        scorer_params={**SCORER_PARAMS, "encoding_dir": DIRECTION},
        wli_data=wli,
        encoding_dir=DIRECTION,
        telemetry_on=True,
        return_solver_report=True,
    )

    recovered_plaintext = _ints(result.solution.plaintext_idx)
    recovered_seed = _ints(result.solution.key)[:seed_length]
    plaintext_match = _match(recovered_plaintext, [int(v) for v in pt_idx])
    seed_match = recovered_seed == TRUE_SEED
    recovered_runes = Runeglish.to_rune(recovered_plaintext, wli)
    print(f"solver score: {float(result.solution.score):.6f}")
    print(f"stop reason: {result.solver_report.stop_reason}")
    print(f"recovered plaintext: {recovered_runes[:240]}{'...' if len(recovered_runes) > 240 else ''}")
    print(f"recovered seed: {recovered_seed}")
    print(f"plaintext match: {plaintext_match:.3f}")
    print(f"seed match: {seed_match}")
    print(f"Match ratio: {plaintext_match:.3f}")
    pretty.print_summary_spacer()
    print_rdp_result(
        result,
        spec=RunSpec(
            problem_input=NormalizedInput(ct_idx=_ints(ciphertext), wli=wli),
            cipher=cipher_spec,
            key=KeySpec.repeat(len=seed_length),
            solver=solver,
            scorer="rune",
            scorer_params=DISPLAY_SCORER_PARAMS,
            encoding_dir=DIRECTION,
            telemetry_on=True,
        ),
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_Autokey_Robust.py",
            "title": "Autokey robust Beam solve",
            "gate": "v1_extended",
            "acceptance_kind": "exact",
            "min_match_ratio": 1.0,
            "uses_oracle_stop_score": False,
        },
    )
    if plaintext_match != 1.0 or not seed_match:
        raise AssertionError("robust Autokey tutorial did not recover exact truth")


if __name__ == "__main__":
    main()
