from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping


FINAL_INSTANCE_GLOB = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "*/final_instances/*.json"
)
OUTPUT_BASE_DIR = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit"
)
MAX_ARTIFACTS = 200
REQUIRE_SPACE_MAP_V1 = True


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _space_map_rows_for_artifact(path: Path) -> list[dict[str, Any]]:
    artifact = _read_json(path)
    stage3_diag = dict(artifact.get("stage3_diagnostics", {}) or {})
    payload = dict(stage3_diag.get("space_map_v1", {}) or {})
    if REQUIRE_SPACE_MAP_V1 and not payload:
        return []
    out: list[dict[str, Any]] = []
    for pool_row in list(payload.get("pool_summaries", []) or []):
        row = dict(pool_row)
        out.append(
            dict(
                artifact_path=str(path).replace("\\", "/"),
                period=int(artifact.get("period", 0) or 0),
                columns=int(artifact.get("columns", 0) or 0),
                key_seed=int(artifact.get("key_seed", 0) or 0),
                best_stage=str(artifact.get("best_stage", "") or ""),
                best_match_ratio=float(
                    artifact.get("best_match_ratio", float("nan"))
                ),
                stage35_baseline_selector=str(
                    stage3_diag.get("stage35_baseline_selector", "") or ""
                ),
                stage35_accept_passed=int(
                    stage3_diag.get("stage35_accept_passed", 0) or 0
                ),
                stage35_accept_reason=str(
                    stage3_diag.get("stage35_accept_reason", "") or ""
                ),
                stage35_best_candidate_hash=str(
                    stage3_diag.get("stage35_best_candidate_hash", "") or ""
                ),
                stage35_best_match=float(
                    stage3_diag.get("stage35_best_match", float("nan"))
                ),
                stage_boundary=str(row.get("stage_boundary", "") or ""),
                pool_id=str(row.get("pool_id", "") or ""),
                pool_status=str(row.get("pool_status", "") or ""),
                selection_policy=str(row.get("selection_policy", "") or ""),
                family_view_id=str(row.get("family_view_id", "") or ""),
                row_count=int(row.get("row_count", 0) or 0),
                eligible_row_count=int(row.get("eligible_row_count", 0) or 0),
                selected_row_count=int(row.get("selected_row_count", 0) or 0),
                family_count=int(row.get("family_count", 0) or 0),
                largest_family_share=float(
                    row.get("largest_family_share", float("nan"))
                ),
                unique_candidate_hash_count=int(
                    row.get("unique_candidate_hash_count", 0) or 0
                ),
                unique_end_hash_count=int(row.get("unique_end_hash_count", 0) or 0),
                anchor_candidate_hash=str(
                    row.get("anchor_candidate_hash", "") or ""
                ),
                selected_pairwise_distance_min=float(
                    row.get("selected_pairwise_distance_min", float("nan"))
                ),
                selected_pairwise_distance_mean=float(
                    row.get("selected_pairwise_distance_mean", float("nan"))
                ),
                next_stage_started_count=int(
                    row.get("next_stage_started_count", 0) or 0
                ),
                next_stage_admitted_count=int(
                    row.get("next_stage_admitted_count", 0) or 0
                ),
                next_stage_rejected_count=int(
                    row.get("next_stage_rejected_count", 0) or 0
                ),
                best_continued_candidate_hash=str(
                    row.get("best_continued_candidate_hash", "") or ""
                ),
                best_continued_match=float(
                    row.get("best_continued_match", float("nan"))
                ),
            )
        )
    return out


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["artifact_path"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def main() -> None:
    artifact_paths = sorted(Path().glob(str(FINAL_INSTANCE_GLOB)))[-int(MAX_ARTIFACTS) :]
    rows: list[dict[str, Any]] = []
    for artifact_path in artifact_paths:
        rows.extend(_space_map_rows_for_artifact(Path(artifact_path)))
    output_dir = OUTPUT_BASE_DIR / (
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        "__space_map_v1_audit"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "pool_summaries.csv", rows)
    summary = dict(
        artifact_glob=str(FINAL_INSTANCE_GLOB),
        artifacts_scanned=int(len(artifact_paths)),
        pool_summary_rows=int(len(rows)),
        output_dir=str(output_dir).replace("\\", "/"),
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "[space_map_v1_audit] "
        f"artifacts={summary['artifacts_scanned']} "
        f"pool_summary_rows={summary['pool_summary_rows']} "
        f"output_dir={summary['output_dir']}"
    )


if __name__ == "__main__":
    main()
