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

from rune_decrypter_prime.api import Direction, KeySpec, RawTextInput, RunSpec, SolverSpec, by_name, print_rdp_result, run
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TUTORIAL_SEED = 4242
TRUE_RAILS = 3
MIN_MATCH_RATIO = 1.0


def encrypt_railfence(pt: str, rails: int) -> str:
    """Zig-zag write across rails, then read row-by-row."""
    if rails <= 1:
        return pt

    rows = [""] * rails
    r = 0
    step = 1
    for ch in pt:
        rows[r] += ch
        if r == 0:
            step = 1
        elif r == rails - 1:
            step = -1
        r += step
    return "".join(rows)


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
    direction = Direction.RTL
    pt_latin = plaintext_english_string
    pt_idx, _, pt_runes = Runeglish.encode_english_to_runes(pt_latin, direction=direction.value)
    pt_runes_nosp = pt_runes.replace(" ", "")
    reference_idx = Runeglish.rune_to_pos(pt_runes_nosp)

    ct_runes = encrypt_railfence(pt_runes_nosp, TRUE_RAILS)
    ct_idx = Runeglish.rune_to_pos(ct_runes)

    print("Railfence problem")
    print(f"encoding direction: {direction.value}")
    print(f"true rails: {TRUE_RAILS}")
    print("word boundaries: stripped before transposition")
    _preview_text("plaintext runes", pt_runes_nosp)
    _preview_text("ciphertext runes", ct_runes)
    print_tutorial_debug_preview(label="plaintext_no_spaces", idx=reference_idx, wli=None, direction=direction)
    print_tutorial_debug_preview(label="ciphertext_no_spaces", idx=ct_idx, wli=None, direction=direction)

    cipher_spec = by_name.cipher("railfence", min_rails=2, max_rails=6)
    key_spec = KeySpec.scalar(max_val=6)
    scorer_params = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=False,
        char_weights={2: 1.0},
        wli_weights={},
        encoding_dir=direction,
    )
    display_scorer_params = {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": False,
        "encoding_dir": direction.value,
        "char_order_2_weight": 1.0,
    }

    stop = oracle_stop_score(
        reference_idx,
        None,
        scorer_params,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.50,
        fallback=0.54,
    )
    print_stop_summary("Railfence Beam", stop)

    solver_spec = SolverSpec.beam(
        beam_width=64,
        log_interval=20,
        stop_score=stop.stop_score,
        plateau_rounds=40,
        plateau_min_delta=1e-4,
        seed=TUTORIAL_SEED,
    )
    display_spec = RunSpec(
        problem_input=RawTextInput(text=ct_runes),
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
        wli_data=None,
        force_no_wli=True,
        encoding_dir=direction,
        telemetry_on=True,
        return_solver_report=True,
    )

    recovered = getattr(result.solution, "plaintext_rune", "") or getattr(result.solution, "plaintext_str", "")
    print("Recovered plaintext preview:", recovered[:120] + ("..." if len(recovered) > 120 else ""))
    match_ratio = _match_ratio(result.solution.plaintext_idx, reference_idx)
    print(f"Match ratio: {match_ratio:.3f}")

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
            "uses_oracle_stop_score": True,
        },
    )


if __name__ == "__main__":
    main()
