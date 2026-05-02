from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "verify_candidate3_phasec_phaseb_topk_anchor_shadow.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_fixed_instance_solver_development_v1 as base_mod,
)


RUN_LABEL = "candidate3_phasec_phaseb_topk_anchor_shadow_v1"
OUTPUT_BASE_DIR = base_mod.OUTPUT_BASE_DIR
PANEL_INVENTORY_CSV = base_mod.PANEL_INVENTORY_CSV
INPUT_EXTERNAL_REVIEW_PACK_DIR = base_mod.INPUT_EXTERNAL_REVIEW_PACK_DIR


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _stage3_diagnostics(best_instance: Mapping[str, Any]) -> Mapping[str, Any]:
    diagnostics = best_instance.get("stage3_diagnostics")
    if isinstance(diagnostics, Mapping):
        return diagnostics
    return {}


def _first_phaseb_topk_start(
    start_rows: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    for row in start_rows:
        if str(row.get("source", "") or "") == "phaseB_topk":
            return row
    return None


def _anchor_swap_label(
    *,
    anchor_match: float | None,
    phaseb_topk_match: float | None,
) -> str:
    if anchor_match is None or phaseb_topk_match is None:
        return "missing_match"
    if phaseb_topk_match > anchor_match:
        return "phaseb_topk_better"
    if phaseb_topk_match < anchor_match:
        return "anchor_better"
    return "equal"


def build_candidate3_anchor_shadow_row(
    *,
    panel_row: Mapping[str, Any],
    best_instance: Mapping[str, Any],
) -> dict[str, Any]:
    diagnostics = _stage3_diagnostics(best_instance)
    start_rows = [dict(row) for row in list(diagnostics.get("phaseC_start_summaries", []) or [])]
    anchor_row = dict(start_rows[0]) if start_rows else {}
    first_phaseb_topk = dict(_first_phaseb_topk_start(start_rows) or {})
    anchor_hash = base_mod._safe_str(anchor_row.get("candidate_hash"))
    phaseb_topk_hash = base_mod._safe_str(first_phaseb_topk.get("candidate_hash"))
    anchor_match = base_mod._safe_optional_float(anchor_row.get("final_match"))
    phaseb_topk_match = base_mod._safe_optional_float(first_phaseb_topk.get("final_match"))
    candidate_can_engage = int(
        bool(anchor_hash)
        and bool(phaseb_topk_hash)
        and anchor_hash != phaseb_topk_hash
    )
    return {
        "panel_job_index": base_mod._safe_int(panel_row.get("panel_job_index")),
        "fixture_seed": base_mod._safe_int(panel_row.get("fixture_seed")),
        "search_seed": base_mod._safe_int(panel_row.get("search_seed")),
        "benchmark_case_role": base_mod._benchmark_case_role(
            base_mod._safe_int(panel_row.get("fixture_seed"))
        ),
        "status": base_mod._safe_str(best_instance.get("status")),
        "best_stage": base_mod._safe_str(best_instance.get("best_stage")),
        "best_match_ratio": base_mod._safe_optional_float(
            best_instance.get("best_match_ratio")
        ),
        "phasec_start_policy": base_mod._safe_str(
            diagnostics.get("phaseC_start_policy")
        ),
        "phasec_start_keys_used": base_mod._safe_int(
            diagnostics.get("phaseC_start_keys_used")
        ),
        "anchor_source": base_mod._safe_str(anchor_row.get("source")),
        "anchor_candidate_hash": anchor_hash,
        "anchor_final_match": anchor_match,
        "first_phaseb_topk_source_rank": base_mod._safe_int(
            first_phaseb_topk.get("source_rank")
        ),
        "first_phaseb_topk_candidate_hash": phaseb_topk_hash,
        "first_phaseb_topk_final_match": phaseb_topk_match,
        "phaseb_topk_anchor_hash_differs": int(
            bool(anchor_hash)
            and bool(phaseb_topk_hash)
            and anchor_hash != phaseb_topk_hash
        ),
        "candidate3_anchor_swap_can_engage": candidate_can_engage,
        "phaseb_topk_minus_anchor_final_match": (
            float(phaseb_topk_match - anchor_match)
            if anchor_match is not None and phaseb_topk_match is not None
            else None
        ),
        "anchor_swap_match_label": _anchor_swap_label(
            anchor_match=anchor_match,
            phaseb_topk_match=phaseb_topk_match,
        ),
        "best_instance_relpath": base_mod._best_instance_rel_path(
            base_mod._safe_str(panel_row.get("copied_report_dir"))
        ),
    }


def build_candidate3_anchor_shadow_rows(
    panel_inventory_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for panel_row in sorted(panel_inventory_rows, key=base_mod._baseline_sort_key):
        best_instance_path = (
            INPUT_EXTERNAL_REVIEW_PACK_DIR
            / base_mod._best_instance_rel_path(
                base_mod._safe_str(panel_row.get("copied_report_dir"))
            )
        )
        best_instance = base_mod._read_json(best_instance_path)
        rows.append(
            build_candidate3_anchor_shadow_row(
                panel_row=panel_row,
                best_instance=best_instance,
            )
        )
    return rows


def build_candidate3_anchor_shadow_summary(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    engageable_rows = [
        row
        for row in rows
        if base_mod._safe_int(row.get("candidate3_anchor_swap_can_engage")) == 1
    ]
    fixture_seed_summary: list[dict[str, Any]] = []
    grouped: dict[int, list[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(base_mod._safe_int(row.get("fixture_seed")), []).append(row)
    for fixture_seed in sorted(grouped, key=base_mod._fixture_seed_order):
        seed_rows = grouped[fixture_seed]
        engageable_seed_rows = [
            row
            for row in seed_rows
            if base_mod._safe_int(row.get("candidate3_anchor_swap_can_engage")) == 1
        ]
        fixture_seed_summary.append(
            {
                "fixture_seed": int(fixture_seed),
                "benchmark_case_role": base_mod._benchmark_case_role(int(fixture_seed)),
                "run_count": int(len(seed_rows)),
                "runs_where_anchor_swap_can_engage": int(len(engageable_seed_rows)),
                "phaseb_topk_better_count": int(
                    sum(
                        int(base_mod._safe_str(row.get("anchor_swap_match_label")) == "phaseb_topk_better")
                        for row in engageable_seed_rows
                    )
                ),
                "anchor_better_count": int(
                    sum(
                        int(base_mod._safe_str(row.get("anchor_swap_match_label")) == "anchor_better")
                        for row in engageable_seed_rows
                    )
                ),
            }
        )
    return {
        "run_label": RUN_LABEL,
        "run_count": int(len(rows)),
        "runs_where_anchor_swap_can_engage": int(len(engageable_rows)),
        "phaseb_topk_better_count": int(
            sum(
                int(base_mod._safe_str(row.get("anchor_swap_match_label")) == "phaseb_topk_better")
                for row in engageable_rows
            )
        ),
        "equal_count": int(
            sum(
                int(base_mod._safe_str(row.get("anchor_swap_match_label")) == "equal")
                for row in engageable_rows
            )
        ),
        "anchor_better_count": int(
            sum(
                int(base_mod._safe_str(row.get("anchor_swap_match_label")) == "anchor_better")
                for row in engageable_rows
            )
        ),
        "candidate3_anchor_swap_shadow_live_on_panel": int(len(engageable_rows) > 0),
        "fixture_seed_summary": fixture_seed_summary,
    }


def build_candidate3_anchor_shadow_markdown(
    *,
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> str:
    lines = [
        "# Candidate 3 Phase-C PhaseB-Topk Anchor Shadow",
        "",
        "Question:",
        "",
        "- on the frozen fixed panel, does the saved Phase-C start surface suggest a real anchor-swap opportunity where the first actual `phaseB_topk` start should be tried in the anchor lane instead of the retained anchor row?",
        "",
        "Important scope note:",
        "",
        "- this is a saved-start shadow check, not an exact replay",
        "- it reasons over persisted `phaseC_start_summaries` only",
        "",
        "Top-line read:",
        "",
        f"- run count: `{base_mod._safe_int(summary.get('run_count'))}`",
        f"- runs where anchor swap can engage: `{base_mod._safe_int(summary.get('runs_where_anchor_swap_can_engage'))}`",
        f"- engageable runs where first phaseB_topk start is better on saved final match: `{base_mod._safe_int(summary.get('phaseb_topk_better_count'))}`",
        f"- engageable runs where retained anchor is better: `{base_mod._safe_int(summary.get('anchor_better_count'))}`",
        f"- candidate3 anchor-swap shadow live on panel: `{base_mod._safe_int(summary.get('candidate3_anchor_swap_shadow_live_on_panel'))}`",
        "",
        "Per-seed summary:",
        "",
        "| fixture_seed | role | run_count | engageable_runs | phaseb_topk_better | anchor_better |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary.get("fixture_seed_summary", []):
        fixture_row = dict(row)
        lines.append(
            f"| {base_mod._safe_int(fixture_row.get('fixture_seed'))} | "
            f"{base_mod._safe_str(fixture_row.get('benchmark_case_role'))} | "
            f"{base_mod._safe_int(fixture_row.get('run_count'))} | "
            f"{base_mod._safe_int(fixture_row.get('runs_where_anchor_swap_can_engage'))} | "
            f"{base_mod._safe_int(fixture_row.get('phaseb_topk_better_count'))} | "
            f"{base_mod._safe_int(fixture_row.get('anchor_better_count'))} |"
        )
    lines.extend(
        [
            "",
            "Per-run rows:",
            "",
            "| fixture_seed | search_seed | best_stage | anchor_source | anchor_match | first_phaseb_topk_match | delta | label | engageable |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        delta = row.get("phaseb_topk_minus_anchor_final_match")
        delta_text = "na" if delta is None else f"{float(delta):.3f}"
        anchor_match = row.get("anchor_final_match")
        phaseb_match = row.get("first_phaseb_topk_final_match")
        lines.append(
            f"| {base_mod._safe_int(row.get('fixture_seed'))} | "
            f"{base_mod._safe_int(row.get('search_seed'))} | "
            f"{base_mod._safe_str(row.get('best_stage'))} | "
            f"{base_mod._safe_str(row.get('anchor_source')) or 'na'} | "
            f"{base_mod._ratio_text(anchor_match)} | "
            f"{base_mod._ratio_text(phaseb_match)} | "
            f"{delta_text} | "
            f"{base_mod._safe_str(row.get('anchor_swap_match_label'))} | "
            f"{base_mod._safe_int(row.get('candidate3_anchor_swap_can_engage'))} |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- this candidate does not require new start hashes; it changes which already-selected row gets the anchor lane",
            "- if exact replay is attempted, it should include both a likely-positive retained case and a likely-negative guardrail case",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    base_mod._require_input_paths((PANEL_INVENTORY_CSV,))
    panel_inventory_rows = base_mod._read_csv_rows(PANEL_INVENTORY_CSV)
    base_mod._require_csv_columns(
        path=PANEL_INVENTORY_CSV,
        rows=panel_inventory_rows,
        required_columns=base_mod.REQUIRED_PANEL_INVENTORY_COLUMNS,
    )
    rows = build_candidate3_anchor_shadow_rows(panel_inventory_rows)
    summary = build_candidate3_anchor_shadow_summary(rows)
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    base_mod._write_jsonl(output_dir / "candidate3_anchor_shadow_rows.jsonl", rows)
    base_mod._write_csv(output_dir / "candidate3_anchor_shadow_rows.csv", rows)
    (output_dir / "candidate3_anchor_shadow_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "candidate3_anchor_shadow_readout.md").write_text(
        build_candidate3_anchor_shadow_markdown(rows=rows, summary=summary),
        encoding="utf-8",
    )
    print(
        "[candidate3-anchor-shadow] "
        f"output_dir={base_mod._relative_path(output_dir)}"
    )
    print(
        "[candidate3-anchor-shadow] "
        f"run_count={base_mod._safe_int(summary.get('run_count'))} "
        "engageable_runs="
        f"{base_mod._safe_int(summary.get('runs_where_anchor_swap_can_engage'))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
