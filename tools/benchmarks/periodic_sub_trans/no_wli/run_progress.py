from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, MutableMapping, Sequence


def init_progress_state(
    *,
    total: int,
    t0_all: float,
    audit_prev_chain_hash: str,
) -> Dict[str, Any]:
    return dict(
        total=int(total),
        done=0,
        t0_all=float(t0_all),
        last_hb=float(t0_all),
        status_counts=dict(solved=0, stalled=0, unsolved=0, skipped_proven=0),
        history_rows_written=0,
        audit_rows_written=0,
        audit_prev_chain_hash=str(audit_prev_chain_hash),
        best_global=dict(
            match=float("-inf"),
            tier="",
            text_id=-1,
            key_seed=-1,
            stage="",
            preview="",
        ),
    )


def checkpoint_manifest(
    *,
    progress: MutableMapping[str, Any],
    status_key: str,
    run_manifest: MutableMapping[str, Any],
    oracle_consulted_in_decisions: bool,
    update_run_manifest_progress_fn: Callable[..., Mapping[str, Any]],
) -> None:
    sk = str(status_key)
    status_counts = dict(progress.get("status_counts", {}))
    if sk in status_counts:
        status_counts[sk] = int(status_counts[sk]) + 1
        progress["status_counts"] = status_counts
    update_run_manifest_progress_fn(
        run_manifest=run_manifest,
        done_units=int(progress["done"]),
        total_units=int(progress["total"]),
        solved=int(status_counts.get("solved", 0)),
        stalled=int(status_counts.get("stalled", 0)),
        unsolved=int(status_counts.get("unsolved", 0)),
        skipped_proven=int(status_counts.get("skipped_proven", 0)),
        history_rows_written=int(progress["history_rows_written"]),
        audit_rows_written=int(progress["audit_rows_written"]),
        audit_last_chain_hash=str(progress["audit_prev_chain_hash"]),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
    )


def commit_iteration_with_checkpoint(
    *,
    progress: MutableMapping[str, Any],
    run_manifest: MutableMapping[str, Any],
    status_key: str,
    oracle_consulted_in_decisions: bool,
    commit_iteration_outputs_fn: Callable[..., Mapping[str, Any]],
    update_run_manifest_progress_fn: Callable[..., Mapping[str, Any]],
    run_dir: Any,
    final_dir: Any,
    root: Any,
    hist_path: Any,
    tiers: Sequence[Any],
    instances: List[Dict[str, Any]],
    stages: List[Dict[str, Any]],
    inst_row: Dict[str, Any],
    artifact_payload: Dict[str, Any],
    heartbeat_seconds: float,
    audit_enabled: bool,
    audit_csv: Any,
    audit_jsonl: Any,
) -> None:
    commit_state = commit_iteration_outputs_fn(
        run_dir=run_dir,
        final_dir=final_dir,
        root=root,
        hist_path=hist_path,
        tiers=tiers,
        instances=instances,
        stages=stages,
        inst_row=dict(inst_row),
        artifact_payload=artifact_payload,
        done=int(progress["done"]),
        total=int(progress["total"]),
        t0_all=float(progress["t0_all"]),
        last_hb=float(progress["last_hb"]),
        heartbeat_seconds=float(heartbeat_seconds),
        best_global=dict(progress["best_global"]),
        history_rows_written=int(progress["history_rows_written"]),
        audit_rows_written=int(progress["audit_rows_written"]),
        audit_enabled=bool(audit_enabled),
        audit_csv=audit_csv,
        audit_jsonl=audit_jsonl,
        audit_prev_chain_hash=str(progress["audit_prev_chain_hash"]),
    )
    progress["done"] = int(commit_state["done"])
    progress["last_hb"] = float(commit_state["last_hb"])
    progress["best_global"] = dict(commit_state["best_global"])
    progress["history_rows_written"] = int(commit_state["history_rows_written"])
    progress["audit_rows_written"] = int(commit_state["audit_rows_written"])
    progress["audit_prev_chain_hash"] = str(commit_state["audit_prev_chain_hash"])
    checkpoint_manifest(
        progress=progress,
        status_key=str(status_key),
        run_manifest=run_manifest,
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        update_run_manifest_progress_fn=update_run_manifest_progress_fn,
    )
