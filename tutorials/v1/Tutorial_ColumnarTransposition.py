from __future__ import annotations

import sys
from pathlib import Path
from typing import List

# Ensure repo root on sys.path so the package imports resolve when run directly
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import Direction, KeySpec, RawTextInput, RunSpec, SolverSpec, by_name, print_rdp_result, run
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

# -*- coding: utf-8 -*-
"""
Tutorial variant: Columnar Transposition with the standard RDP printer facade.

This file intentionally lives beside the original tutorial. The original remains
stable while this variant proves the new display/printer contract.
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TUTORIAL_SEED = 12345
PREVIEW_RUNES = 160
PREVIEW_IDX = 32


def encrypt_columnar(pt: str, key: List[int]) -> str:
    """Row-fill, then read columns in the order given by 'key' (no spaces)."""
    K = len(key)
    rows = (len(pt) + K - 1) // K
    table = [list(pt[i * K : i * K + K]) for i in range(rows)]
    out_chars: List[str] = []
    for col in key:
        for r in range(rows):
            if col < len(table[r]):
                out_chars.append(table[r][col])
    return "".join(out_chars)


def _preview_text(label: str, value: str, *, limit: int = PREVIEW_RUNES) -> None:
    suffix = "..." if len(value) > limit else ""
    print(f"{label} length: {len(value)}")
    print(f"{label} preview: {value[:limit]}{suffix}")


def _preview_idx(label: str, values: list[int], *, limit: int = PREVIEW_IDX) -> None:
    suffix = " ..." if len(values) > limit else ""
    print(f"{label} length: {len(values)}")
    print(f"{label} preview: {values[:limit]}{suffix}")


def main() -> None:
    direction = Direction.RTL
    pt_en = plaintext_english_string
    _pt_idx_with_spaces, _wli_pt, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction=direction.value)
    pt_runes_nosp = pt_runes.replace(" ", "")
    reference_idx = Runeglish.rune_to_pos(pt_runes_nosp)

    key_true = [3, 6, 1, 4, 2, 0, 5]
    ct_runes = encrypt_columnar(pt_runes_nosp, key_true)
    ct_idx = Runeglish.rune_to_pos(ct_runes)

    print("Columnar transposition problem")
    print(f"direction: {direction.value}")
    print(f"true key length: {len(key_true)}")
    _preview_text("plaintext runes", pt_runes_nosp)
    _preview_text("ciphertext runes", ct_runes)
    _preview_idx("ciphertext indices", ct_idx)

    cipher = by_name.cipher("columnar")
    key_spec = KeySpec.permutation(len=len(key_true))

    scorer_params = {
        "objective": "pct.logp.win10",
        "char_weights": {2: 1.0},
        "wli_weights": {},
        "use_word_breaks": False,
        "include_char": True,
        "encoding_dir": direction,
    }

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
        min_score=0.45,
        fallback=0.503,
    )
    print_stop_summary("Columnar Hybrid", stop)

    solve_spec = SolverSpec.hybrid(
        use_beam=True,
        beam_width=96,
        rounds=6,
        expand_mode="sample",
        sample_per_parent=48,
        top_parents_factor=0.4,
        progress_pct=2,
        print_progress=True,
        ga=dict(
            pop_size=96,
            generations=40,
            elite_frac=0.1,
            cx_frac=0.85,
            mut_prob=0.3,
            tournament_k=3,
            plateau_rounds=12,
            plateau_min_delta=1e-4,
            stop_score=stop.stop_score,
            print_progress=True,
        ),
        sa=dict(
            sa_iters=3000,
            sa_init_temp=0.95,
            sa_min_temp=1e-4,
            sa_cooling=0.997,
            plateau_rounds=300,
            plateau_min_delta=1e-4,
            local_improve_on_accept=True,
            stop_score=stop.stop_score,
            print_progress=True,
        ),
        seed=TUTORIAL_SEED,
        verbose=True,
        log_interval=10,
        plateau_rounds=8,
        plateau_min_delta=1e-4,
        stop_score=stop.stop_score,
    )
    display_spec = RunSpec(
        problem_input=RawTextInput(text=ct_runes),
        cipher=cipher,
        key=key_spec,
        solver=solve_spec,
        scorer="rune",
        scorer_params=display_scorer_params,
        encoding_dir=direction,
        telemetry_on=True,
    )

    result = run(
        text=ct_runes,
        cipher=cipher,
        key=key_spec,
        solver=solve_spec,
        device="cpu",
        scorer="rune",
        scorer_params=scorer_params,
        wli_data=None,
        force_no_wli=True,
        encoding_dir=direction,
        telemetry_on=True,
        return_solver_report=True,
    )

    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=reference_idx,
        options=None,
        tutorial_entry={
            "path": "Tutorial_ColumnarTransposition.py",
            "title": "Columnar transposition pretty-print variant",
            "gate": "v1_release_pretty_print",
            "acceptance_kind": "min_match_ratio",
            "min_match_ratio": 1.0,
            "uses_oracle_stop_score": True,
        },
    )


if __name__ == "__main__":
    main()
