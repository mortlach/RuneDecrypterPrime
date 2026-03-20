from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Sequence


def finalize_run_outputs(
    *,
    run_dir: Path,
    final_dir: Path,
    best_dir: Path,
    root: Path,
    hist_path: Path,
    t0_all: float,
    oracle_consulted_in_decisions: bool,
    total: int,
    done: int,
    status_counts: Dict[str, int],
    history_rows_written: int,
    audit_rows_written: int,
    audit_prev_chain_hash: str,
    tiers: Sequence[Any],
    instances: Sequence[Dict[str, Any]],
    stages: Sequence[Dict[str, Any]],
    run_manifest: Dict[str, Any],
    run_manifest_path: Path,
    write_json_fn: Callable[[Path, Dict[str, Any]], None],
    write_pipeline_snapshot_files_fn: Callable[..., None],
    build_summary_fn: Callable[[Sequence[Any], Sequence[Dict[str, Any]]], Dict[str, Any]],
    sha256_file_fn: Callable[[Path], str],
    format_seconds_fn: Callable[[float], str],
    log_prefix: str = "[pipeline_no_wli]",
) -> None:
    summary = build_summary_fn(tiers, instances)
    write_pipeline_snapshot_files_fn(
        run_dir=run_dir,
        instances=instances,
        stages=stages,
        summary=summary,
    )

    if instances:
        best_instance_row = max(
            instances,
            key=lambda r: float(r.get("best_match_ratio", float("-inf"))),
        )
        best_instance = dict(best_instance_row)
        artifact_name = (
            f"{best_instance_row['tier']}__text{int(best_instance_row['text_id'])}"
            f"__seed{int(best_instance_row['key_seed'])}.json"
        )
        artifact_path = final_dir / artifact_name
        if artifact_path.exists():
            try:
                artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            except Exception:
                artifact_payload = None
            if isinstance(artifact_payload, dict):
                merged_best = dict(best_instance_row)
                merged_best.update(artifact_payload)
                best_instance = merged_best
        write_json_fn(best_dir / "best_instance.json", dict(best_instance))
        (best_dir / "best_preview.txt").write_text(
            str(best_instance_row.get("preview_best_latin", "")),
            encoding="utf-8",
        )

    elapsed_total = float(time.time() - float(t0_all))
    run_manifest["run_status"] = "completed"
    run_manifest["updated_utc"] = datetime.now(timezone.utc).isoformat()
    run_manifest["completed_utc"] = datetime.now(timezone.utc).isoformat()
    run_manifest["elapsed_seconds"] = float(elapsed_total)
    run_manifest["oracle_consulted_in_decisions"] = bool(
        oracle_consulted_in_decisions
    )
    run_manifest["artifacts"] = dict(
        summary_sha256=(
            sha256_file_fn(run_dir / "summary.json")
            if (run_dir / "summary.json").exists()
            else ""
        ),
        instances_sha256=(
            sha256_file_fn(run_dir / "instances.json")
            if (run_dir / "instances.json").exists()
            else ""
        ),
        stages_sha256=(
            sha256_file_fn(run_dir / "stages.json")
            if (run_dir / "stages.json").exists()
            else ""
        ),
    )
    run_manifest["progress"] = dict(
        total_units=int(total),
        done_units=int(done),
        solved=int(status_counts.get("solved", 0)),
        stalled=int(status_counts.get("stalled", 0)),
        unsolved=int(status_counts.get("unsolved", 0)),
        skipped_proven=int(status_counts.get("skipped_proven", 0)),
        history_rows_written=int(history_rows_written),
        audit_rows_written=int(audit_rows_written),
        audit_last_chain_hash=str(audit_prev_chain_hash),
    )
    write_json_fn(run_manifest_path, run_manifest)

    print(f"{log_prefix} completed in {format_seconds_fn(elapsed_total)}", flush=True)
    print(f"{log_prefix} reports: {run_dir.relative_to(root)}", flush=True)
    print(f"{log_prefix} final_artifacts: {final_dir.relative_to(root)}", flush=True)
    print(f"{log_prefix} manifest: {run_manifest_path.relative_to(root)}", flush=True)
    print(
        f"{log_prefix} best: {(best_dir / 'best_instance.json').relative_to(root)}",
        flush=True,
    )
    print(
        f"{log_prefix} history: {hist_path.relative_to(root)} rows={int(history_rows_written)}",
        flush=True,
    )
    print(
        f"{log_prefix} audit_chain: rows={int(audit_rows_written)} "
        f"last_chain_hash={str(audit_prev_chain_hash)}",
        flush=True,
    )
