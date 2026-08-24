from __future__ import annotations

"""Railfence pretty-print tutorial.

This variant keeps the original railfence teaching path but reports through the
standard RDP printer contract.
"""

import sys
from pathlib import Path
from typing import Sequence

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, NormalizedInput, RunSpec, SolverSpec, by_name, cipher_instance, print_rdp_result, run
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TUTORIAL_SEED = 4242
MIN_RAILS = 4
MAX_RAILS = 10
TRUE_RAILS = 7
MIN_MATCH_RATIO = 1.0


def _match_ratio(recovered: Sequence[int], reference: Sequence[int]) -> float:
    limit = min(len(recovered), len(reference))
    if limit == 0:
        return 0.0
    matches = sum(1 for i in range(limit) if int(recovered[i]) == int(reference[i]))
    return matches / float(limit)


def _preview_text(label: str, value: str, *, limit: int = 160) -> None:
    suffix = "..." if len(value) > limit else ""
    print(f"{label} length: {len(value)}")
    print(f"{label} preview: {value[:limit]}{suffix}")


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name='Railfence beam solve',
        cipher='railfence',
        solver='beam',
        direction='rtl',
        expected_result='exact solve',
        uses_reference_stop_score=False,
    )
    direction = Direction.RTL
    pt_latin = plaintext_english_string
    reference_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_latin, direction=direction.value)
    cipher_spec = by_name.cipher("railfence", min_rails=MIN_RAILS, max_rails=MAX_RAILS)
    rail_key = [TRUE_RAILS - MIN_RAILS]
    ct = cipher_instance("railfence", min_rails=MIN_RAILS, max_rails=MAX_RAILS).encrypt(
        plaintext=np.asarray(reference_idx, dtype=np.uint8),
        key=np.asarray(rail_key, dtype=np.uint8),
    )
    ct_idx = [int(v) for v in ct.tolist()]
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    print("Railfence problem")
    print(f"encoding direction: {direction.value}")
    print(f"true rails: {TRUE_RAILS}")
    print(f"qualified rail range: {MIN_RAILS}..{MAX_RAILS}")
    _preview_text("plaintext runes", pt_runes)
    _preview_text("ciphertext runes", ct_runes)
    print_tutorial_debug_preview(label="plaintext", idx=reference_idx, wli=wli, direction=direction)
    print_tutorial_debug_preview(label="ciphertext", idx=ct_idx, wli=wli, direction=direction)

    key_spec = KeySpec.scalar(max_val=MAX_RAILS - MIN_RAILS + 1)
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

    solver_spec = SolverSpec.beam(
        beam_width=64,
        log_interval=20,
        plateau_rounds=40,
        seed=TUTORIAL_SEED,
    )
    display_spec = RunSpec(
        problem_input=NormalizedInput(ct_idx=ct_idx, wli=wli),
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        scorer="rune",
        scorer_params=display_scorer_params,
        encoding_dir=direction,
        telemetry_on=True,
    )

    result = run(
        text=ct_runes,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        device="cpu",
        scorer="rune",
        scorer_params=scorer_params,
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        return_solver_report=True,
    )

    recovered = getattr(result.solution, "plaintext_rune", "") or getattr(result.solution, "plaintext_str", "")
    print("Recovered plaintext preview:", recovered[:120] + ("..." if len(recovered) > 120 else ""))
    match_ratio = _match_ratio(result.solution.plaintext_idx, reference_idx)
    print(f"Match ratio: {match_ratio:.3f}")

    pretty.print_summary_spacer()
    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=reference_idx,
        tutorial_entry={
            "path": "Tutorial_Railfence.py",
            "title": "Railfence pretty-print variant",
            "gate": "v1_smoke_pretty_print",
            "acceptance_kind": "exact",
            "min_match_ratio": MIN_MATCH_RATIO,
            "uses_oracle_stop_score": False,
        },
    )


if __name__ == "__main__":
    main()
