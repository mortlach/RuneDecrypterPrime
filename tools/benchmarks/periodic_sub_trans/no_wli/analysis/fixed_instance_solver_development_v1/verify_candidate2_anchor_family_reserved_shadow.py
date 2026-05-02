from __future__ import annotations

import json
import sys
from collections import Counter
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
        "verify_candidate2_anchor_family_reserved_shadow.py"
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
from tools.benchmarks.periodic_sub_trans.no_wli.family_views import (  # noqa: E402
    cluster_family_ids,
    find_family_view,
)


RUN_LABEL = "candidate2_anchor_family_reserved_shadow_v1"
OUTPUT_BASE_DIR = base_mod.OUTPUT_BASE_DIR
PANEL_INVENTORY_CSV = base_mod.PANEL_INVENTORY_CSV
INPUT_EXTERNAL_REVIEW_PACK_DIR = base_mod.INPUT_EXTERNAL_REVIEW_PACK_DIR
FAMILY_VIEW_ID = "prefix_hamming_le_24"
RESERVED_SLOTS = 2


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def _candidate_hash(row: Mapping[str, Any], *, row_index: int) -> str:
    candidate_hash = str(row.get("candidate_hash", "") or "").strip()
    if candidate_hash:
        return candidate_hash
    key_vals = list(row.get("key_idx", row.get("key", [])) or [])
    if key_vals:
        return ",".join(str(int(v)) for v in key_vals)
    return f"row_{int(row_index)}"


def _dedupe_rows_by_hash(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    seen_hashes: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        row_hash = str(row.get("candidate_hash", "") or "").strip()
        if not row_hash or row_hash in seen_hashes:
            continue
        seen_hashes.add(row_hash)
        out.append(dict(row))
    return out


def _family_counts_label(rows: Sequence[Mapping[str, Any]]) -> str:
    counts = Counter(
        str(row.get("family_id", "") or "")
        for row in rows
        if str(row.get("family_id", "") or "")
    )
    if not counts:
        return ""
    return ", ".join(
        f"{family_id}:{int(count)}"
        for family_id, count in sorted(
            counts.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )
    )


def annotate_candidate_pool_rows_with_families(
    rows: Sequence[Mapping[str, Any]],
    *,
    columns: int,
    family_view_id: str,
) -> list[dict[str, Any]]:
    view = find_family_view(str(family_view_id))
    if view is None:
        raise ValueError(f"Unknown family view id: {family_view_id}")
    normalized_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        key_vals = list(row.get("key_idx", row.get("key", [])) or [])
        normalized_rows.append(
            dict(
                row_id=f"pool:{int(idx)}",
                key_idx=[int(v) for v in key_vals],
                candidate_hash=_candidate_hash(row, row_index=idx),
                source=str(row.get("source", "") or ""),
                source_rank=base_mod._safe_int(row.get("source_rank")),
                selected_by_phasec_start=base_mod._safe_int(
                    row.get("selected_by_phasec_start")
                ),
                original_row=dict(row),
            )
        )
    assignments, _ = cluster_family_ids(
        normalized_rows,
        family_view=view,
        columns=int(columns),
    )
    return [
        dict(
            row,
            family_id=str(assignments.get(str(row["row_id"]), "") or ""),
        )
        for row in normalized_rows
    ]


def _selected_start_hashes(
    *,
    start_rows: Sequence[Mapping[str, Any]],
    annotated_rows: Sequence[Mapping[str, Any]],
) -> set[str]:
    start_hashes = {
        str(row.get("candidate_hash", "") or "").strip()
        for row in start_rows
        if str(row.get("candidate_hash", "") or "").strip()
    }
    if start_hashes:
        return start_hashes
    return {
        str(row.get("candidate_hash", "") or "").strip()
        for row in annotated_rows
        if base_mod._safe_int(row.get("selected_by_phasec_start")) == 1
        and str(row.get("candidate_hash", "") or "").strip()
    }


def _anchor_candidate_hash(
    *,
    start_rows: Sequence[Mapping[str, Any]],
    unique_pool_rows: Sequence[Mapping[str, Any]],
) -> str:
    if start_rows:
        first_hash = str(start_rows[0].get("candidate_hash", "") or "").strip()
        if first_hash:
            return first_hash
    for source_name in ("stage3_best_phaseB", "stage3_best_phaseA", "stage3_best"):
        for row in unique_pool_rows:
            if (
                str(row.get("source", "") or "") == str(source_name)
                and base_mod._safe_int(row.get("source_rank")) == 1
            ):
                return str(row.get("candidate_hash", "") or "").strip()
    if unique_pool_rows:
        return str(unique_pool_rows[0].get("candidate_hash", "") or "").strip()
    return ""


def summarize_candidate2_anchor_family_shadow_from_annotated_rows(
    *,
    fixture_seed: int,
    search_seed: int,
    status: str,
    best_stage: str,
    best_match_ratio: float | None,
    phasec_start_policy: str,
    phasec_start_keys_used: int,
    annotated_rows: Sequence[Mapping[str, Any]],
    start_rows: Sequence[Mapping[str, Any]],
    reserved_slots: int,
    best_instance_relpath: str = "",
) -> dict[str, Any]:
    unique_pool_rows = _dedupe_rows_by_hash(annotated_rows)
    selected_start_hashes = _selected_start_hashes(
        start_rows=start_rows,
        annotated_rows=annotated_rows,
    )
    selected_start_rows = [
        row
        for row in unique_pool_rows
        if str(row.get("candidate_hash", "") or "") in selected_start_hashes
    ]
    start_count = int(
        max(
            0,
            int(phasec_start_keys_used),
        )
    )
    if start_count <= 0:
        start_count = int(len(selected_start_hashes))
    anchor_hash = _anchor_candidate_hash(
        start_rows=start_rows,
        unique_pool_rows=unique_pool_rows,
    )
    anchor_row = next(
        (
            row
            for row in unique_pool_rows
            if str(row.get("candidate_hash", "") or "") == str(anchor_hash)
        ),
        None,
    )
    anchor_family_id = str(anchor_row.get("family_id", "") or "") if anchor_row else ""
    anchor_family_pool_hashes = {
        str(row.get("candidate_hash", "") or "")
        for row in unique_pool_rows
        if str(row.get("family_id", "") or "") == str(anchor_family_id)
        and str(row.get("candidate_hash", "") or "")
    }
    anchor_family_selected_start_hashes = {
        str(row.get("candidate_hash", "") or "")
        for row in selected_start_rows
        if str(row.get("family_id", "") or "") == str(anchor_family_id)
        and str(row.get("candidate_hash", "") or "")
    }
    anchor_family_extra_pool_hashes = set(anchor_family_pool_hashes) - set(
        anchor_family_selected_start_hashes
    )
    selected_non_anchor_start_count = int(
        max(
            0,
            int(start_count) - int(len(anchor_family_selected_start_hashes)),
        )
    )
    shadow_materializable_extra_anchor_rows = int(
        min(
            max(0, int(reserved_slots)),
            int(len(anchor_family_extra_pool_hashes)),
            int(selected_non_anchor_start_count),
        )
    )
    shadow_anchor_family_count_after = int(
        min(
            int(start_count),
            int(len(anchor_family_selected_start_hashes))
            + int(shadow_materializable_extra_anchor_rows),
        )
    )
    baseline_anchor_family_start_share = (
        float(len(anchor_family_selected_start_hashes)) / float(start_count)
        if int(start_count) > 0
        else 0.0
    )
    shadow_anchor_family_start_share_after = (
        float(shadow_anchor_family_count_after) / float(start_count)
        if int(start_count) > 0
        else 0.0
    )

    if not unique_pool_rows:
        room_label = "no_phasec_candidate_pool"
    elif not selected_start_hashes:
        room_label = "no_phasec_start_rows"
    elif not anchor_family_id:
        room_label = "missing_anchor_family"
    elif int(shadow_materializable_extra_anchor_rows) <= 0:
        room_label = "no_saved_room"
    else:
        room_label = "saved_room_available"

    return {
        "fixture_seed": int(fixture_seed),
        "search_seed": int(search_seed),
        "benchmark_case_role": base_mod._benchmark_case_role(int(fixture_seed)),
        "status": str(status),
        "best_stage": str(best_stage),
        "best_match_ratio": best_match_ratio,
        "phasec_start_policy": str(phasec_start_policy),
        "phasec_candidate_pool_unique_hash_count": int(len(unique_pool_rows)),
        "phasec_selected_start_unique_hash_count": int(len(selected_start_hashes)),
        "phasec_start_keys_used": int(start_count),
        "anchor_candidate_hash": str(anchor_hash),
        "anchor_family_id": str(anchor_family_id),
        "anchor_family_pool_unique_hash_count": int(len(anchor_family_pool_hashes)),
        "anchor_family_selected_start_unique_hash_count": int(
            len(anchor_family_selected_start_hashes)
        ),
        "anchor_family_extra_pool_unique_hash_count": int(
            len(anchor_family_extra_pool_hashes)
        ),
        "selected_non_anchor_start_unique_hash_count": int(
            selected_non_anchor_start_count
        ),
        "shadow_materializable_extra_anchor_rows": int(
            shadow_materializable_extra_anchor_rows
        ),
        "shadow_anchor_family_unique_hash_count_after": int(
            shadow_anchor_family_count_after
        ),
        "baseline_anchor_family_start_share": float(
            baseline_anchor_family_start_share
        ),
        "shadow_anchor_family_start_share_after": float(
            shadow_anchor_family_start_share_after
        ),
        "room_label": str(room_label),
        "candidate_pool_family_counts": _family_counts_label(unique_pool_rows),
        "selected_start_family_counts": _family_counts_label(selected_start_rows),
        "anchor_family_extra_pool_hashes": sorted(anchor_family_extra_pool_hashes)[:5],
        "best_instance_relpath": str(best_instance_relpath),
    }


def build_candidate2_anchor_family_shadow_case_row(
    *,
    panel_row: Mapping[str, Any],
    best_instance: Mapping[str, Any],
) -> dict[str, Any]:
    diagnostics = _stage3_diagnostics(best_instance)
    annotated_rows = annotate_candidate_pool_rows_with_families(
        list(diagnostics.get("phaseC_candidate_pool_rows", []) or []),
        columns=base_mod._safe_int(best_instance.get("columns"), default=0),
        family_view_id=FAMILY_VIEW_ID,
    )
    return summarize_candidate2_anchor_family_shadow_from_annotated_rows(
        fixture_seed=base_mod._safe_int(panel_row.get("fixture_seed")),
        search_seed=base_mod._safe_int(panel_row.get("search_seed")),
        status=base_mod._safe_str(best_instance.get("status")),
        best_stage=base_mod._safe_str(best_instance.get("best_stage")),
        best_match_ratio=base_mod._safe_optional_float(
            best_instance.get("best_match_ratio")
        ),
        phasec_start_policy=base_mod._safe_str(
            diagnostics.get("phaseC_start_policy")
        ),
        phasec_start_keys_used=base_mod._safe_int(
            diagnostics.get("phaseC_start_keys_used")
        ),
        annotated_rows=annotated_rows,
        start_rows=list(diagnostics.get("phaseC_start_summaries", []) or []),
        reserved_slots=RESERVED_SLOTS,
        best_instance_relpath=base_mod._best_instance_rel_path(
            base_mod._safe_str(panel_row.get("copied_report_dir"))
        ),
    )


def build_candidate2_anchor_family_shadow_rows(
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
            build_candidate2_anchor_family_shadow_case_row(
                panel_row=panel_row,
                best_instance=best_instance,
            )
        )
    return rows


def build_candidate2_anchor_family_shadow_summary(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    run_count = len(rows)
    runs_with_phasec_candidate_pool = sum(
        int(base_mod._safe_int(row.get("phasec_candidate_pool_unique_hash_count")) > 0)
        for row in rows
    )
    runs_with_saved_room = sum(
        int(base_mod._safe_str(row.get("room_label")) == "saved_room_available")
        for row in rows
    )
    runs_without_saved_room = sum(
        int(base_mod._safe_str(row.get("room_label")) == "no_saved_room")
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
                "fixture_seed": int(fixture_seed),
                "benchmark_case_role": base_mod._benchmark_case_role(int(fixture_seed)),
                "run_count": int(len(seed_rows)),
                "runs_with_phasec_candidate_pool": int(
                    sum(
                        int(
                            base_mod._safe_int(
                                row.get("phasec_candidate_pool_unique_hash_count")
                            )
                            > 0
                        )
                        for row in seed_rows
                    )
                ),
                "runs_with_saved_room": int(
                    sum(
                        int(base_mod._safe_str(row.get("room_label")) == "saved_room_available")
                        for row in seed_rows
                    )
                ),
                "max_shadow_materializable_extra_anchor_rows": int(
                    max(
                        base_mod._safe_int(
                            row.get("shadow_materializable_extra_anchor_rows")
                        )
                        for row in seed_rows
                    )
                ),
            }
        )
    return {
        "run_label": RUN_LABEL,
        "run_count": int(run_count),
        "runs_with_phasec_candidate_pool": int(runs_with_phasec_candidate_pool),
        "runs_with_saved_room": int(runs_with_saved_room),
        "runs_without_saved_room": int(runs_without_saved_room),
        "replacement_candidate2_shadow_live_on_panel": int(
            run_count > 0 and runs_with_saved_room > 0
        ),
        "fixture_seed_summary": fixture_seed_summary,
    }


def build_candidate2_anchor_family_shadow_markdown(
    *,
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> str:
    lines = [
        "# Candidate2 Anchor-Family Reserved Shadow",
        "",
        "Question:",
        "",
        "- on the frozen fixed panel, does the saved Phase-C candidate-pool/start surface contain retained runs where `anchor_family_reserved_v1` could replace baseline starts with extra anchor-family rows?",
        "",
        "Important scope note:",
        "",
        "- this is a saved-surface shadow check, not an exact replay",
        "- it uses persisted `phaseC_candidate_pool_rows` and `phaseC_start_summaries` from the retained bundles",
        f"- reserved slots: `{int(RESERVED_SLOTS)}`",
        f"- family view: `{FAMILY_VIEW_ID}`",
        "",
        "Top-line read:",
        "",
        f"- run count: `{base_mod._safe_int(summary.get('run_count'))}`",
        f"- runs with saved Phase-C pool: `{base_mod._safe_int(summary.get('runs_with_phasec_candidate_pool'))}`",
        f"- runs with saved anchor-family room: `{base_mod._safe_int(summary.get('runs_with_saved_room'))}`",
        f"- replacement candidate2 shadow live on panel: `{base_mod._safe_int(summary.get('replacement_candidate2_shadow_live_on_panel'))}`",
        "",
        "Per-seed summary:",
        "",
        "| fixture_seed | role | run_count | runs_with_phasec_pool | runs_with_saved_room | max_materializable_extra_rows |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary.get("fixture_seed_summary", []):
        fixture_row = dict(row)
        lines.append(
            f"| {base_mod._safe_int(fixture_row.get('fixture_seed'))} | "
            f"{base_mod._safe_str(fixture_row.get('benchmark_case_role'))} | "
            f"{base_mod._safe_int(fixture_row.get('run_count'))} | "
            f"{base_mod._safe_int(fixture_row.get('runs_with_phasec_candidate_pool'))} | "
            f"{base_mod._safe_int(fixture_row.get('runs_with_saved_room'))} | "
            f"{base_mod._safe_int(fixture_row.get('max_shadow_materializable_extra_anchor_rows'))} |"
        )
    lines.extend(
        [
            "",
            "Per-run rows:",
            "",
            "| fixture_seed | search_seed | best_stage | best_match_ratio | start_policy | anchor_family | start_count | baseline_anchor_share | shadow_anchor_share_after | materializable_extra_rows | room_label |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {base_mod._safe_int(row.get('fixture_seed'))} | "
            f"{base_mod._safe_int(row.get('search_seed'))} | "
            f"{base_mod._safe_str(row.get('best_stage'))} | "
            f"{base_mod._ratio_text(row.get('best_match_ratio'))} | "
            f"{base_mod._safe_str(row.get('phasec_start_policy'))} | "
            f"{base_mod._safe_str(row.get('anchor_family_id')) or 'na'} | "
            f"{base_mod._safe_int(row.get('phasec_start_keys_used'))} | "
            f"{float(row.get('baseline_anchor_family_start_share', 0.0)):.3f} | "
            f"{float(row.get('shadow_anchor_family_start_share_after', 0.0)):.3f} | "
            f"{base_mod._safe_int(row.get('shadow_materializable_extra_anchor_rows'))} | "
            f"{base_mod._safe_str(row.get('room_label'))} |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- saved room means the retained Phase-C pool contains extra rows in the anchor family that were not already selected as baseline starts",
            "- this does not prove runtime utility, but it does test whether the replacement lever is structurally live on the frozen panel before exact replay work",
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
    rows = build_candidate2_anchor_family_shadow_rows(panel_inventory_rows)
    summary = build_candidate2_anchor_family_shadow_summary(rows)
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    base_mod._write_jsonl(output_dir / "candidate2_anchor_family_shadow_rows.jsonl", rows)
    base_mod._write_csv(output_dir / "candidate2_anchor_family_shadow_rows.csv", rows)
    (output_dir / "candidate2_anchor_family_shadow_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "candidate2_anchor_family_shadow_readout.md").write_text(
        build_candidate2_anchor_family_shadow_markdown(rows=rows, summary=summary),
        encoding="utf-8",
    )
    print(
        "[candidate2-anchor-family-shadow] "
        f"output_dir={_relative_path(output_dir)}"
    )
    print(
        "[candidate2-anchor-family-shadow] "
        f"run_count={base_mod._safe_int(summary.get('run_count'))} "
        "saved_room_runs="
        f"{base_mod._safe_int(summary.get('runs_with_saved_room'))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
