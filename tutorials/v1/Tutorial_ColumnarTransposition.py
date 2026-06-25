from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Sequence

# Ensure repo root on sys.path so the package imports resolve when run directly
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import (
    Direction,
    KeySpec,
    RawTextInput,
    RdpPrintOptions,
    RunSpec,
    SolverSpec,
    by_name,
    format_rdp_banner,
    format_rdp_kv_block,
    format_rdp_preview_block,
    format_rdp_section,
    format_rdp_status_block,
    print_rdp_block,
    print_rdp_result,
    run,
)
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.scoring.language_model.load_status import LmLoadStatus
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_output import tutorial_debug_preview_block
from rune_decrypter_prime.utils.tutorial_utils import format_stop_summary, oracle_stop_score

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


def _preview_text(value: str, *, limit: int = PREVIEW_RUNES) -> str:
    suffix = "..." if len(value) > limit else ""
    return f"{value[:limit]}{suffix}"


def _preview_sequence(values: Sequence[int], *, limit: int = PREVIEW_IDX) -> str:
    clipped = list(values[:limit])
    suffix = " ..." if len(values) > limit else ""
    return f"{clipped}{suffix}"


def _model_loading_rows(events: Sequence[LmLoadStatus]) -> list[tuple[str, object]]:
    if not events:
        return [("status", "no model assets loaded")]
    if len(events) == 1:
        event = events[0]
        return [(event.asset_type, event.asset_id), ("status", event.status)]
    return [
        (f"{event.asset_type} {index}", f"{event.asset_id} ({event.status})")
        for index, event in enumerate(events, start=1)
    ]


def main() -> None:
    print_options = RdpPrintOptions.detailed()
    direction = Direction.RTL
    pt_en = plaintext_english_string
    _pt_idx_with_spaces, _wli_pt, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction=direction.value)
    pt_runes_nosp = pt_runes.replace(" ", "")
    reference_idx = Runeglish.rune_to_pos(pt_runes_nosp)

    key_true = [3, 6, 1, 4, 2, 0, 5]
    ct_runes = encrypt_columnar(pt_runes_nosp, key_true)
    ct_idx = Runeglish.rune_to_pos(ct_runes)

    print_rdp_block(format_rdp_banner(options=print_options))
    print_rdp_block(
        format_rdp_kv_block(
            "Initialising RDP",
            [
                ("display schema", "api_display_summary.v1"),
                ("encoding", "utf-8"),
                ("status", "ready"),
            ],
            options=print_options,
        )
    )
    print_rdp_block(
        format_rdp_kv_block(
            "Tutorial",
            [
                ("name", "Columnar transposition"),
                ("cipher", "columnar"),
                ("solver", "hybrid"),
                ("direction", direction.value),
                ("expected result", "exact solve"),
                ("truth/reference use", "stop-score calibration; not supplied to solver ranking"),
            ],
            options=print_options,
        )
    )
    print_rdp_block(
        format_rdp_kv_block(
            "Problem input",
            [
                ("plaintext runes length", len(pt_runes_nosp)),
                ("ciphertext runes length", len(ct_runes)),
                ("ciphertext indices length", len(ct_idx)),
                ("true key length", len(key_true)),
            ],
            options=print_options,
        )
    )
    print_rdp_block(
        format_rdp_preview_block(
            "Plaintext preview",
            [("runes", _preview_text(pt_runes_nosp))],
            options=print_options,
        )
    )
    print_rdp_block(
        format_rdp_preview_block(
            "Ciphertext preview",
            [
                ("runes", _preview_text(ct_runes)),
                ("indices", _preview_sequence(ct_idx)),
            ],
            options=print_options,
        )
    )
    print_rdp_block(
        tutorial_debug_preview_block(
            label="plaintext_no_spaces",
            idx=reference_idx,
            wli=None,
            direction=direction,
            options=print_options,
        )
    )
    print_rdp_block(
        tutorial_debug_preview_block(
            label="ciphertext_no_spaces",
            idx=ct_idx,
            wli=None,
            direction=direction,
            options=print_options,
        )
    )

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

    lm_load_events: list[LmLoadStatus] = []
    stop = oracle_stop_score(
        reference_idx,
        None,
        scorer_params,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.45,
        fallback=0.503,
        load_reporter=lm_load_events.append,
    )
    print_rdp_block(
        format_rdp_status_block(
            "Model loading",
            _model_loading_rows(lm_load_events),
            options=print_options,
        )
    )
    print_rdp_block(format_stop_summary("Columnar Hybrid", stop, options=print_options))

    solve_spec = SolverSpec.hybrid(
        use_beam=True,
        beam_width=96,
        rounds=6,
        expand_mode="sample",
        sample_per_parent=48,
        top_parents_factor=0.4,
        progress_pct=2,
        print_progress=True,
        progress_preview_chars=120,
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
            progress_preview_chars=120,
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
            progress_preview_chars=120,
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

    print_rdp_block(format_rdp_section("Run progress"))
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

    print()
    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=reference_idx,
        options=None,
        tutorial_entry={
            "path": "Tutorial_ColumnarTransposition.py",
            "title": "Columnar transposition pretty-print variant",
            "gate": "v1_release_pretty_print",
            "acceptance_kind": "exact",
            "min_match_ratio": 1.0,
            "uses_oracle_stop_score": True,
        },
    )


if __name__ == "__main__":
    main()
