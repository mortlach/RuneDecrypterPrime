from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping


def build_initial_run_manifest(
    *,
    run_dir: Path,
    profile: str,
    mode: str,
    oracle_mode: str,
    oracle_decision_paths_enabled: bool,
    oracle_consulted_in_decisions: bool,
    oracle_assist_selection_requested: bool,
    oracle_assist_selection_effective: bool,
    direction: str,
    order: str,
    python_version: str,
    platform_name: str,
    git_short: str,
    git_commit: str,
    git_dirty: bool,
    scoring_experiment: Mapping[str, Any],
    non_scoring_lock_hash: str,
    scoring_lock_hash: str,
    run_config_hash: str,
    span_assets_dir: str,
    span_combined_calibration_hash: str,
    span_ecdf_audit_hash: str,
    run_config_rel_path: str,
    history_log_rel_path: str,
    final_instances_rel_path: str,
    audit_csv_rel_path: str,
    audit_jsonl_rel_path: str,
    audit_enabled: bool,
    audit_chain_seed: str,
    total_units: int,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return dict(
        kind="bench_solve_pipeline_no_wli",
        version=2,
        run_status="running",
        run_id=str(run_dir.name),
        generated_utc=str(now),
        updated_utc=str(now),
        completed_utc="",
        profile_id=str(profile),
        mode=str(mode),
        oracle_mode=str(oracle_mode),
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        oracle_assist_selection_requested=bool(oracle_assist_selection_requested),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        direction=str(direction),
        order=str(order),
        runtime=dict(
            python=str(python_version),
            platform=str(platform_name),
        ),
        git=dict(
            short=str(git_short),
            commit=str(git_commit),
            dirty=int(1 if bool(git_dirty) else 0),
        ),
        scoring_experiment=dict(scoring_experiment),
        lock_hashes=dict(
            non_scoring=str(non_scoring_lock_hash),
            scoring=str(scoring_lock_hash),
            run_config=str(run_config_hash),
        ),
        assets=dict(
            span_assets_dir=str(span_assets_dir),
            span_combined_calibration_sha256=str(span_combined_calibration_hash),
            span_ecdf_audit_sha256=str(span_ecdf_audit_hash),
        ),
        paths=dict(
            run_config=str(run_config_rel_path),
            history_log=str(history_log_rel_path),
            final_instances=str(final_instances_rel_path),
            audit_chain_csv=str(audit_csv_rel_path),
            audit_chain_jsonl=str(audit_jsonl_rel_path),
        ),
        audit=dict(
            enabled=int(1 if bool(audit_enabled) else 0),
            chain_algorithm="sha256(prev_chain_hash|row_hash)",
            chain_seed=str(audit_chain_seed),
        ),
        progress=dict(
            total_units=int(total_units),
            done_units=0,
            solved=0,
            stalled=0,
            unsolved=0,
            skipped_proven=0,
            history_rows_written=0,
            audit_rows_written=0,
            audit_last_chain_hash=str(audit_chain_seed),
        ),
    )


def build_and_write_initial_run_manifest(
    *,
    run_manifest_path: Path,
    write_json_fn: Callable[[Path, Any], None],
    kwargs: Mapping[str, Any],
) -> Dict[str, Any]:
    run_manifest = build_initial_run_manifest(**dict(kwargs))
    write_json_fn(run_manifest_path, run_manifest)
    return run_manifest


def update_run_manifest_progress(
    *,
    run_manifest: Dict[str, Any],
    done_units: int,
    total_units: int,
    solved: int,
    stalled: int,
    unsolved: int,
    skipped_proven: int,
    history_rows_written: int,
    audit_rows_written: int,
    audit_last_chain_hash: str,
    oracle_consulted_in_decisions: bool,
) -> Dict[str, Any]:
    run_manifest["updated_utc"] = datetime.now(timezone.utc).isoformat()
    run_manifest["oracle_consulted_in_decisions"] = bool(oracle_consulted_in_decisions)
    run_manifest["progress"] = dict(
        total_units=int(total_units),
        done_units=int(done_units),
        solved=int(solved),
        stalled=int(stalled),
        unsolved=int(unsolved),
        skipped_proven=int(skipped_proven),
        history_rows_written=int(history_rows_written),
        audit_rows_written=int(audit_rows_written),
        audit_last_chain_hash=str(audit_last_chain_hash),
    )
    return run_manifest
