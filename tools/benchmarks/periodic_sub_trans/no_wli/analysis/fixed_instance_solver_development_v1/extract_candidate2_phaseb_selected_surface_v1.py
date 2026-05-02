from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_candidate2_phaseb_selected_surface_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    extract_fixed_instance_solver_development_v1 as base_mod,
)


RUN_LABEL = "candidate2_phaseb_selected_surface_v1"
OUTPUT_BASE_DIR = base_mod.OUTPUT_BASE_DIR
PANEL_INVENTORY_CSV = base_mod.PANEL_INVENTORY_CSV
INPUT_EXTERNAL_REVIEW_PACK_DIR = base_mod.INPUT_EXTERNAL_REVIEW_PACK_DIR


def _utc_label() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _stage3_diagnostics(best_instance: Mapping[str, Any]) -> Mapping[str, Any]:
    diagnostics = best_instance.get("stage3_diagnostics")
    if isinstance(diagnostics, Mapping):
        return diagnostics
    return {}


def build_phaseb_selected_surface_row(
    *,
    panel_row: Mapping[str, Any],
    best_instance: Mapping[str, Any],
) -> dict[str, Any]:
    diagnostics = _stage3_diagnostics(best_instance)
    selected_count = base_mod._safe_int(
        diagnostics.get("phaseB_downstream_selected_count")
    )
    preserved_family_count = base_mod._safe_int(
        diagnostics.get("phaseB_family_preserved_count")
    )
    top_band_family_count = base_mod._safe_int(
        diagnostics.get("phaseB_family_count_in_top_band")
    )
    selected_unique_end_hash = base_mod._safe_int(
        diagnostics.get("phaseB_selected_unique_end_hash")
    )
    reservation_applied = base_mod._safe_int(
        diagnostics.get("phaseB_family_reservation_applied")
    )
    repeated_family_row_count = max(0, selected_count - preserved_family_count)
    selected_surface_all_unique_families = int(
        selected_count > 0 and selected_count == preserved_family_count
    )
    candidate2_current_lever_can_engage = int(repeated_family_row_count > 0)
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
        "phaseb_family_preservation_policy": base_mod._safe_str(
            diagnostics.get("phaseB_family_preservation_policy")
        ),
        "phaseb_family_view_id": base_mod._safe_str(
            diagnostics.get("phaseB_family_view_id")
        ),
        "phaseb_family_reserved_slots": base_mod._safe_int(
            diagnostics.get("phaseB_family_reserved_slots")
        ),
        "phaseb_family_count_in_top_band": top_band_family_count,
        "phaseb_family_preserved_count": preserved_family_count,
        "phaseb_family_reservation_applied": reservation_applied,
        "phaseb_selected_unique_end_hash": selected_unique_end_hash,
        "phaseb_downstream_selected_count": selected_count,
        "repeated_family_row_count": repeated_family_row_count,
        "selected_surface_all_unique_families": selected_surface_all_unique_families,
        "candidate2_current_lever_can_engage": candidate2_current_lever_can_engage,
        "best_instance_relpath": base_mod._best_instance_rel_path(
            base_mod._safe_str(panel_row.get("copied_report_dir"))
        ),
    }


def build_phaseb_selected_surface_rows(
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
            build_phaseb_selected_surface_row(
                panel_row=panel_row,
                best_instance=best_instance,
            )
        )
    return rows


def build_phaseb_selected_surface_summary(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    run_count = len(rows)
    runs_with_repeat_families = sum(
        int(base_mod._safe_int(row.get("repeated_family_row_count")) > 0) for row in rows
    )
    runs_all_unique = sum(
        int(base_mod._safe_int(row.get("selected_surface_all_unique_families")) > 0)
        for row in rows
    )
    runs_with_can_engage = sum(
        int(base_mod._safe_int(row.get("candidate2_current_lever_can_engage")) > 0)
        for row in rows
    )
    fixture_seed_summary: list[dict[str, Any]] = []
    grouped: dict[int, list[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(base_mod._safe_int(row.get("fixture_seed")), []).append(row)
    for fixture_seed in sorted(grouped, key=base_mod._fixture_seed_order):
        seed_rows = grouped[fixture_seed]
        fixture_seed_summary.append(
            {
                "fixture_seed": fixture_seed,
                "benchmark_case_role": base_mod._benchmark_case_role(fixture_seed),
                "run_count": len(seed_rows),
                "runs_with_repeat_families": sum(
                    int(base_mod._safe_int(row.get("repeated_family_row_count")) > 0)
                    for row in seed_rows
                ),
                "runs_all_unique_selected_families": sum(
                    int(
                        base_mod._safe_int(
                            row.get("selected_surface_all_unique_families")
                        )
                        > 0
                    )
                    for row in seed_rows
                ),
                "max_repeated_family_row_count": max(
                    base_mod._safe_int(row.get("repeated_family_row_count"))
                    for row in seed_rows
                ),
            }
        )
    return {
        "run_label": RUN_LABEL,
        "run_count": run_count,
        "runs_with_repeat_families": runs_with_repeat_families,
        "runs_all_unique_selected_families": runs_all_unique,
        "runs_where_current_candidate2_lever_can_engage": runs_with_can_engage,
        "current_candidate2_lever_structurally_blocked_on_panel": int(
            run_count > 0 and runs_with_can_engage == 0
        ),
        "fixture_seed_summary": fixture_seed_summary,
    }


def build_phaseb_selected_surface_markdown(
    *,
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> str:
    lines = [
        "# Candidate2 Phase-B Selected Surface Readout",
        "",
        "Question:",
        "",
        "- on the frozen fixed panel, does the actual Phase-B selected-row surface contain retained runs where the current `reinforce_top_family_v1` lever could engage?",
        "",
        "Top-line read:",
        "",
        f"- run count: `{base_mod._safe_int(summary.get('run_count'))}`",
        f"- runs with repeat families on the selected Phase-B surface: `{base_mod._safe_int(summary.get('runs_with_repeat_families'))}`",
        f"- runs where the current candidate2 lever could engage: `{base_mod._safe_int(summary.get('runs_where_current_candidate2_lever_can_engage'))}`",
        f"- structurally blocked on the frozen panel: `{base_mod._safe_int(summary.get('current_candidate2_lever_structurally_blocked_on_panel'))}`",
        "",
        "Per-seed summary:",
        "",
        "| fixture_seed | role | run_count | repeat_family_runs | all_unique_runs | max_repeated_family_row_count |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary.get("fixture_seed_summary", []):
        fixture_row = dict(row)
        lines.append(
            f"| {base_mod._safe_int(fixture_row.get('fixture_seed'))} | "
            f"{base_mod._safe_str(fixture_row.get('benchmark_case_role'))} | "
            f"{base_mod._safe_int(fixture_row.get('run_count'))} | "
            f"{base_mod._safe_int(fixture_row.get('runs_with_repeat_families'))} | "
            f"{base_mod._safe_int(fixture_row.get('runs_all_unique_selected_families'))} | "
            f"{base_mod._safe_int(fixture_row.get('max_repeated_family_row_count'))} |"
        )
    lines.extend(
        [
            "",
            "Per-run rows:",
            "",
            "| fixture_seed | search_seed | best_stage | best_match_ratio | selected_count | preserved_families | repeated_family_rows | candidate2_can_engage |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {base_mod._safe_int(row.get('fixture_seed'))} | "
            f"{base_mod._safe_int(row.get('search_seed'))} | "
            f"{base_mod._safe_str(row.get('best_stage'))} | "
            f"{base_mod._ratio_text(row.get('best_match_ratio'))} | "
            f"{base_mod._safe_int(row.get('phaseb_downstream_selected_count'))} | "
            f"{base_mod._safe_int(row.get('phaseb_family_preserved_count'))} | "
            f"{base_mod._safe_int(row.get('repeated_family_row_count'))} | "
            f"{base_mod._safe_int(row.get('candidate2_current_lever_can_engage'))} |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- this diagnostic reasons over the actual persisted Phase-B selected-row surface, not the later saved candidate-pool shadow surface",
            "- if `selected_count == preserved_families`, then each selected row belongs to a different family and the current top-family reinforcement lever has nothing to reallocate",
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
    rows = build_phaseb_selected_surface_rows(panel_inventory_rows)
    summary = build_phaseb_selected_surface_summary(rows)
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    base_mod._write_jsonl(output_dir / "phaseb_selected_surface_rows.jsonl", rows)
    base_mod._write_csv(output_dir / "phaseb_selected_surface_rows.csv", rows)
    (output_dir / "phaseb_selected_surface_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "phaseb_selected_surface_readout.md").write_text(
        build_phaseb_selected_surface_markdown(rows=rows, summary=summary),
        encoding="utf-8",
    )
    print(f"[candidate2-phaseb-selected-surface] output_dir={_relative_path(output_dir)}")
    print(
        "[candidate2-phaseb-selected-surface] "
        f"run_count={base_mod._safe_int(summary.get('run_count'))} "
        "engageable_runs="
        f"{base_mod._safe_int(summary.get('runs_where_current_candidate2_lever_can_engage'))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
