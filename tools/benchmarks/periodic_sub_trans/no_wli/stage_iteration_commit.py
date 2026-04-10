from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence

from tools.benchmarks.periodic_sub_trans.no_wli.iteration_identity import (
    build_iteration_identity_fields_from_row,
)


def commit_iteration_outputs(
    *,
    run_dir: Path,
    final_dir: Path,
    root: Path,
    hist_path: Path,
    tiers: Sequence[Any],
    instances: List[Dict[str, Any]],
    stages: List[Dict[str, Any]],
    inst_row: Dict[str, Any],
    artifact_payload: Dict[str, Any],
    done: int,
    total: int,
    t0_all: float,
    last_hb: float,
    heartbeat_seconds: float,
    best_global: Dict[str, Any],
    history_rows_written: int,
    audit_rows_written: int,
    audit_enabled: bool,
    audit_csv: Path,
    audit_jsonl: Path,
    audit_prev_chain_hash: str,
    write_json_fn: Callable[[Path, Dict[str, Any]], None],
    build_summary_fn: Callable[[Sequence[Any], Sequence[Dict[str, Any]]], Dict[str, Any]],
    write_pipeline_snapshot_files_fn: Callable[..., None],
    append_csv_row_fn: Callable[[Path, Dict[str, Any]], None],
    append_iteration_audit_row_fn: Callable[..., str],
    hash_payload_fn: Callable[[Dict[str, Any]], str],
    sha256_file_fn: Callable[[Path], str],
    format_seconds_fn: Callable[[float], str],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    identity = build_iteration_identity_fields_from_row(inst_row)
    artifact_name = str(identity["artifact_basename"])
    artifact_path = final_dir / artifact_name
    write_json_fn(artifact_path, artifact_payload)

    # Per-instance checkpoint (crash-safe): preserve completed units immediately.
    summary_ckpt = build_summary_fn(tiers, instances)
    write_pipeline_snapshot_files_fn(
        run_dir=run_dir,
        instances=instances,
        stages=stages,
        summary=summary_ckpt,
    )

    hist_row = dict(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        run_id=run_dir.name,
        profile_id=artifact_payload["profile_id"],
        fixture_id=str(identity["history_fixture_id"]),
        text_id=inst_row["text_id"],
        key_seed=inst_row["key_seed"],
        instance_input_mode=str(identity["instance_input_mode"]),
        instance_fixture_id=str(identity["instance_fixture_id"]),
        instance_source_key_seed=int(identity["instance_source_key_seed"]),
        search_seed=int(identity["search_seed"]),
        period=inst_row["period"],
        columns=inst_row["columns"],
        length=inst_row["length"],
        status=inst_row["status"],
        outcome_code=inst_row["outcome_code"],
        solve_threshold=inst_row["solve_threshold"],
        best_match_ratio=inst_row["best_match_ratio"],
        best_stage=inst_row["best_stage"],
        stage1_sub_key_match=inst_row["stage1_sub_key_match"],
        stage2_match_ratio=inst_row["stage2_match_ratio"],
        stage3_match_ratio=inst_row["stage3_match_ratio"],
        total_seconds=inst_row["total_seconds"],
        total_evals=inst_row["total_evals"],
        notes=inst_row["stop_reason"],
    )
    append_csv_row_fn(hist_path, hist_row)
    history_rows_written = int(history_rows_written) + 1

    if bool(audit_enabled):
        audit_prev_chain_hash = append_iteration_audit_row_fn(
            audit_csv=audit_csv,
            audit_jsonl=audit_jsonl,
            prev_chain_hash=str(audit_prev_chain_hash),
            payload=dict(
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                iteration_index=int(done + 1),
                run_id=str(run_dir.name),
                fixture_id=str(identity["history_fixture_id"]),
                text_id=int(inst_row["text_id"]),
                key_seed=int(inst_row["key_seed"]),
                instance_input_mode=str(identity["instance_input_mode"]),
                instance_fixture_id=str(identity["instance_fixture_id"]),
                instance_source_key_seed=int(identity["instance_source_key_seed"]),
                search_seed=int(identity["search_seed"]),
                status=str(inst_row["status"]),
                best_stage=str(inst_row["best_stage"]),
                best_match_ratio=float(inst_row["best_match_ratio"]),
                stop_reason=str(inst_row["stop_reason"]),
                total_seconds=float(inst_row["total_seconds"]),
                total_evals=int(inst_row["total_evals"]),
                history_row_hash=str(hash_payload_fn(hist_row)),
                artifact_relpath=str(artifact_path.relative_to(root)),
                artifact_sha256=str(sha256_file_fn(artifact_path)),
            ),
        )
        audit_rows_written = int(audit_rows_written) + 1

    if float(inst_row["best_match_ratio"]) > float(best_global["match"]):
        best_global.update(
            match=float(inst_row["best_match_ratio"]),
            tier=str(inst_row["tier"]),
            text_id=int(inst_row["text_id"]),
            key_seed=int(inst_row["key_seed"]),
            stage=str(inst_row["best_stage"]),
            preview=str(inst_row["preview_best_latin"]),
        )

    done = int(done) + 1
    elapsed = float(time.time() - float(t0_all))
    eta = (elapsed / float(done)) * float(total - done) if done else 0.0
    print(
        f"{log_prefix} {done}/{total} tier={inst_row['tier']} status={inst_row['status']} "
        f"best_match={float(inst_row['best_match_ratio']):.3f} "
        f"run={format_seconds_fn(float(inst_row['total_seconds']))} "
        f"elapsed={format_seconds_fn(elapsed)} eta={format_seconds_fn(eta)}",
        flush=True,
    )
    preview_best = str(inst_row["preview_best_latin"])
    if preview_best:
        if str(identity["instance_input_mode"]) == "fixed_ciphertext":
            print(
                f"{log_prefix} best-instance-preview fixture={identity['instance_fixture_id']} "
                f"search_seed={identity['search_seed']} text=\"{preview_best}\"",
                flush=True,
            )
        else:
            print(
                f"{log_prefix} best-instance-preview tier={inst_row['tier']} text={inst_row['text_id']} "
                f"key_seed={inst_row['key_seed']} text=\"{preview_best}\"",
                flush=True,
            )

    now = float(time.time())
    if (now - float(last_hb)) >= float(heartbeat_seconds):
        print(
            f"{log_prefix} heartbeat elapsed={format_seconds_fn(now - float(t0_all))} done={done}/{total} "
            f"global_best_match={float(best_global['match']):.3f} tier={best_global['tier']} "
            f"text={best_global['text_id']} key_seed={best_global['key_seed']} stage={best_global['stage']} "
            f"preview=\"{best_global['preview']}\"",
            flush=True,
        )
        last_hb = now

    return dict(
        done=int(done),
        last_hb=float(last_hb),
        best_global=dict(best_global),
        history_rows_written=int(history_rows_written),
        audit_rows_written=int(audit_rows_written),
        audit_prev_chain_hash=str(audit_prev_chain_hash),
    )
