from __future__ import annotations

import csv
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
        "verify_candidate2_top_family_reinforce_shadow.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.family_views import (
    cluster_family_ids,
    find_family_view,
)


CASE_ARTIFACT_REL_PATHS = (
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/"
        "20260411T221348740692Z__bench_solve_pipeline_no_wli__9557c0f/"
        "final_instances/fixture_001__p9_c3_l1000__text0__seed1111__search7002.json"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/"
        "20260412T031328680128Z__bench_solve_pipeline_no_wli__9557c0f/"
        "final_instances/fixture_001__p9_c3_l1000__text0__seed1111__search7004.json"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/"
        "20260411T014510194326Z__bench_solve_pipeline_no_wli__9557c0f/"
        "final_instances/fixture_001__p9_c3_l1000__text0__seed611__search7005.json"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/"
        "20260413T183231813339Z__bench_solve_pipeline_no_wli__9557c0f/"
        "final_instances/fixture_001__p9_c3_l1000__text0__seed1511__search7002.json"
    ),
)
RUN_LABEL = "candidate2_top_family_reinforce_shadow_v1"
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
)
FAMILY_VIEW_ID = "prefix_hamming_le_24"
RESERVED_SLOTS = 2


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _candidate_hash(row: Mapping[str, Any], *, row_index: int) -> str:
    candidate_hash = str(row.get("candidate_hash", "") or "").strip()
    if candidate_hash:
        return candidate_hash
    key_vals = list(row.get("key_idx", row.get("key", [])) or [])
    if key_vals:
        return ",".join(str(int(v)) for v in key_vals)
    return f"row_{int(row_index)}"


def _family_counts_label(rows: Sequence[Mapping[str, Any]]) -> str:
    counts = Counter(str(row.get("family_id", "") or "") for row in rows if str(row.get("family_id", "") or ""))
    if not counts:
        return ""
    return ", ".join(
        f"{family_id}:{int(count)}"
        for family_id, count in sorted(counts.items(), key=lambda item: (-int(item[1]), str(item[0])))
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
                source_rank=_safe_int(row.get("source_rank")),
                lane=str(row.get("lane", "") or ""),
                selected_by_phasec_start=_safe_int(row.get("selected_by_phasec_start")),
                original_row=dict(row),
            )
        )
    assignments, _ = cluster_family_ids(
        normalized_rows,
        family_view=view,
        columns=int(columns),
    )
    annotated_rows: list[dict[str, Any]] = []
    for row in normalized_rows:
        annotated_rows.append(
            dict(
                row,
                family_id=str(assignments.get(str(row["row_id"]), "") or ""),
            )
        )
    return annotated_rows


def summarize_candidate2_shadow_from_annotated_rows(
    *,
    fixture_seed: int,
    search_seed: int,
    best_stage: str,
    best_match_ratio: float,
    phaseb_downstream_selected_count: int,
    phasec_start_keys_used: int,
    annotated_rows: Sequence[Mapping[str, Any]],
    reserved_slots: int,
    source_artifact_relpath: str = "",
) -> dict[str, Any]:
    rows = [dict(row) for row in annotated_rows]
    anchor_row = next(
        (
            row
            for row in rows
            if str(row.get("source", "")) == "stage3_best_phaseB"
            and int(row.get("source_rank", 0) or 0) == 1
        ),
        None,
    )
    if anchor_row is None:
        anchor_row = next(
            (
                row
                for row in rows
                if str(row.get("source", "")) == "phaseB_topk"
                and int(row.get("source_rank", 0) or 0) == 1
            ),
            None,
        )
    if anchor_row is None:
        anchor_row = next(iter(rows), None)

    anchor_candidate_hash = str(anchor_row.get("candidate_hash", "") or "") if anchor_row else ""
    anchor_family_id = str(anchor_row.get("family_id", "") or "") if anchor_row else ""

    def _unique_hashes(
        row_group: Sequence[Mapping[str, Any]],
        *,
        family_id: str | None = None,
    ) -> set[str]:
        hashes: set[str] = set()
        for row in row_group:
            if family_id is not None and str(row.get("family_id", "") or "") != str(family_id):
                continue
            candidate_hash = str(row.get("candidate_hash", "") or "")
            if candidate_hash:
                hashes.add(candidate_hash)
        return hashes

    pool_hashes = _unique_hashes(rows)
    phasea_selected_rows = [row for row in rows if str(row.get("source", "")) == "phaseA_selected"]
    phaseb_topk_rows = [row for row in rows if str(row.get("source", "")) == "phaseB_topk"]
    anchor_source_rows = [row for row in rows if str(row.get("source", "")) == "stage3_best_phaseB"]
    selected_start_rows = [
        row for row in rows if int(row.get("selected_by_phasec_start", 0) or 0) == 1
    ]

    phasea_selected_hashes = _unique_hashes(phasea_selected_rows)
    phaseb_topk_hashes = _unique_hashes(phaseb_topk_rows)
    selected_start_hashes = _unique_hashes(selected_start_rows)

    anchor_family_pool_hashes = _unique_hashes(rows, family_id=anchor_family_id)
    anchor_family_phasea_selected_hashes = _unique_hashes(
        phasea_selected_rows,
        family_id=anchor_family_id,
    )
    anchor_family_phaseb_topk_hashes = _unique_hashes(
        phaseb_topk_rows,
        family_id=anchor_family_id,
    )
    anchor_family_selected_start_hashes = _unique_hashes(
        selected_start_rows,
        family_id=anchor_family_id,
    )

    anchor_family_extra_hashes = set(anchor_family_pool_hashes) - set(
        anchor_family_phasea_selected_hashes
    )
    shadow_materializable_extra_anchor_rows = min(
        int(max(0, int(reserved_slots))),
        int(len(anchor_family_extra_hashes)),
    )
    target_selected_count = int(
        max(
            int(phaseb_downstream_selected_count),
            int(len(phasea_selected_hashes)),
        )
    )
    baseline_anchor_family_share = (
        float(len(anchor_family_phasea_selected_hashes)) / float(target_selected_count)
        if int(target_selected_count) > 0
        else 0.0
    )
    shadow_anchor_family_count_after = int(
        len(anchor_family_phasea_selected_hashes)
        + int(shadow_materializable_extra_anchor_rows)
    )
    shadow_anchor_family_share_after = (
        float(shadow_anchor_family_count_after) / float(target_selected_count)
        if int(target_selected_count) > 0
        else 0.0
    )

    room_label = "saved_room_available"
    if not anchor_family_id:
        room_label = "missing_anchor_family"
    elif int(shadow_materializable_extra_anchor_rows) <= 0:
        room_label = "no_saved_room"

    return {
        "source_artifact_relpath": str(source_artifact_relpath),
        "fixture_seed": int(fixture_seed),
        "search_seed": int(search_seed),
        "best_stage": str(best_stage),
        "best_match_ratio": float(best_match_ratio),
        "phaseb_downstream_selected_count": int(phaseb_downstream_selected_count),
        "phasec_start_keys_used": int(phasec_start_keys_used),
        "candidate_pool_unique_hash_count": int(len(pool_hashes)),
        "phasea_selected_unique_hash_count": int(len(phasea_selected_hashes)),
        "phaseb_topk_unique_hash_count": int(len(phaseb_topk_hashes)),
        "selected_start_unique_hash_count": int(len(selected_start_hashes)),
        "anchor_candidate_hash": str(anchor_candidate_hash),
        "anchor_family_id": str(anchor_family_id),
        "anchor_family_pool_unique_hash_count": int(len(anchor_family_pool_hashes)),
        "anchor_family_phasea_selected_unique_hash_count": int(
            len(anchor_family_phasea_selected_hashes)
        ),
        "anchor_family_phaseb_topk_unique_hash_count": int(
            len(anchor_family_phaseb_topk_hashes)
        ),
        "anchor_family_selected_start_unique_hash_count": int(
            len(anchor_family_selected_start_hashes)
        ),
        "anchor_family_extra_saved_unique_hash_count": int(
            len(anchor_family_extra_hashes)
        ),
        "shadow_materializable_extra_anchor_rows": int(
            shadow_materializable_extra_anchor_rows
        ),
        "shadow_anchor_family_unique_hash_count_after": int(
            shadow_anchor_family_count_after
        ),
        "baseline_anchor_family_share": float(baseline_anchor_family_share),
        "shadow_anchor_family_share_after": float(shadow_anchor_family_share_after),
        "room_label": str(room_label),
        "candidate_pool_family_counts": _family_counts_label(rows),
        "phasea_selected_family_counts": _family_counts_label(phasea_selected_rows),
        "selected_start_family_counts": _family_counts_label(selected_start_rows),
        "anchor_family_extra_saved_hashes": sorted(anchor_family_extra_hashes)[:5],
        "phasea_selected_source_rows_total": int(len(phasea_selected_rows)),
        "phaseb_topk_source_rows_total": int(len(phaseb_topk_rows)),
        "anchor_source_rows_total": int(len(anchor_source_rows)),
    }


def build_candidate2_shadow_case_summary(
    *,
    artifact_path: Path,
    family_view_id: str,
    reserved_slots: int,
) -> dict[str, Any]:
    artifact = _read_json(artifact_path)
    diag = dict(artifact.get("stage3_diagnostics", {}) or {})
    annotated_rows = annotate_candidate_pool_rows_with_families(
        list(diag.get("phaseC_candidate_pool_rows", []) or []),
        columns=int(artifact.get("columns", 0) or 0),
        family_view_id=str(family_view_id),
    )
    return summarize_candidate2_shadow_from_annotated_rows(
        fixture_seed=_safe_int(artifact.get("instance_source_key_seed")),
        search_seed=_safe_int(artifact.get("search_seed")),
        best_stage=str(artifact.get("best_stage", "") or ""),
        best_match_ratio=_safe_float(artifact.get("best_match_ratio")),
        phaseb_downstream_selected_count=_safe_int(
            diag.get("phaseB_downstream_selected_count")
        ),
        phasec_start_keys_used=_safe_int(diag.get("phaseC_start_keys_used")),
        annotated_rows=annotated_rows,
        reserved_slots=int(reserved_slots),
        source_artifact_relpath=_relative_path(artifact_path),
    )


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(dict(row), sort_keys=True))
            fh.write("\n")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    row_list = [dict(row) for row in rows]
    fieldnames: list[str] = []
    for row in row_list:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(str(key))
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in row_list:
            writer.writerow(row)


def _write_markdown(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    lines = [
        "# Candidate 2 Top-Family Reinforcement Shadow",
        "",
        "Question:",
        "- on retained fixed-panel cases, does the saved Phase-C candidate pool show real room for `reinforce_top_family_v1` to increase top-family carry-forward before any exact retained replay is attempted?",
        "",
        "Important scope note:",
        "- this is a saved-pool shadow check, not a full retained Stage-3 replay",
        "- it uses the saved `phaseC_candidate_pool_rows` surface because the exact retained Stage-3 replay is currently too expensive for a multi-case first pass",
        f"- shadow reserved slots: `{int(RESERVED_SLOTS)}`",
        f"- family view: `{FAMILY_VIEW_ID}`",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## `{int(row.get('fixture_seed', 0))}` / `search{int(row.get('search_seed', 0))}`",
                f"- source: `{str(row.get('source_artifact_relpath', '') or '')}`",
                f"- retained result: `{str(row.get('best_stage', '') or '')}` / `{float(row.get('best_match_ratio', 0.0)):.3f}`",
                f"- anchor family: `{str(row.get('anchor_family_id', '') or 'na')}` from `{str(row.get('anchor_candidate_hash', '') or 'na')}`",
                f"- baseline selected pool anchor-family share: `{float(row.get('baseline_anchor_family_share', 0.0)):.3f}`",
                f"- shadow anchor-family share after reinforcement: `{float(row.get('shadow_anchor_family_share_after', 0.0)):.3f}`",
                f"- extra saved top-family hashes outside baseline selected pool: `{int(row.get('anchor_family_extra_saved_unique_hash_count', 0))}`",
                f"- shadow materializable extra rows: `{int(row.get('shadow_materializable_extra_anchor_rows', 0))}`",
                f"- room label: `{str(row.get('room_label', '') or '')}`",
                f"- pool family counts: `{str(row.get('candidate_pool_family_counts', '') or 'na')}`",
                f"- selected-pool family counts: `{str(row.get('phasea_selected_family_counts', '') or 'na')}`",
                f"- selected-start family counts: `{str(row.get('selected_start_family_counts', '') or 'na')}`",
                "",
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_verification() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    rows = [
        build_candidate2_shadow_case_summary(
            artifact_path=REPO_ROOT / rel_path,
            family_view_id=FAMILY_VIEW_ID,
            reserved_slots=RESERVED_SLOTS,
        )
        for rel_path in CASE_ARTIFACT_REL_PATHS
    ]
    rows = sorted(
        rows,
        key=lambda row: (int(row.get("fixture_seed", 0)), int(row.get("search_seed", 0))),
    )
    _write_jsonl(output_dir / "candidate2_shadow_case_rows.jsonl", rows)
    _write_csv(output_dir / "candidate2_shadow_case_rows.csv", rows)
    _write_markdown(output_dir / "candidate2_shadow_readout.md", rows)
    summary = {
        "output_dir": _relative_path(output_dir),
        "case_count": int(len(rows)),
        "cases_with_saved_room": int(
            sum(1 for row in rows if str(row.get("room_label", "")) == "saved_room_available")
        ),
        "cases_without_saved_room": int(
            sum(1 for row in rows if str(row.get("room_label", "")) == "no_saved_room")
        ),
        "cases": [
            f"{int(row.get('fixture_seed', 0))}/search{int(row.get('search_seed', 0))}"
            for row in rows
        ],
    }
    _write_json(output_dir / "run_summary.json", summary)
    return summary


def main() -> None:
    summary = run_verification()
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
