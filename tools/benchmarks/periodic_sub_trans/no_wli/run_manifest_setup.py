from __future__ import annotations

import platform
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, MutableMapping, Sequence


def initialize_run_state(
    *,
    tiers: Sequence[Any],
    text_offsets: Sequence[int],
    key_seeds: Sequence[int],
    audit_prev_chain_hash: str,
    run_dir: Path,
    root: Path,
    direction_value: str,
    order: str,
    profile: str,
    pipeline_run_mode: str,
    canonical_run_mode_fn: Callable[[str | None], str],
    oracle_mode: str,
    oracle_decision_paths_enabled: bool,
    oracle_consulted_in_decisions: bool,
    oracle_assist_selection_requested: bool,
    oracle_assist_selection_effective: bool,
    scoring_experiment_meta: Mapping[str, Any],
    scoring_meta_for_output_fn: Callable[..., Dict[str, Any]],
    non_scoring_lock_hash: str,
    scoring_lock_hash: str,
    run_config_hash: str,
    span_assets_rel_path: str,
    span_combined_calibration_hash: str,
    span_ecdf_audit_hash: str,
    run_config_path: Path,
    hist_path: Path,
    final_dir: Path,
    audit_csv: Path,
    audit_jsonl: Path,
    audit_enabled: bool,
    audit_chain_seed: str,
    git_short_fn: Callable[[], str],
    git_commit_fn: Callable[[], str],
    git_dirty_fn: Callable[[], bool],
    write_json_fn: Callable[[Path, Any], None],
    init_progress_state_fn: Callable[..., Dict[str, Any]],
    build_and_write_initial_run_manifest_fn: Callable[..., Mapping[str, Any]],
) -> Dict[str, Any]:
    stages: list[dict[str, Any]] = []
    instances: list[dict[str, Any]] = []
    total = len(tiers) * len(text_offsets) * len(key_seeds)
    t0_all = time.time()
    progress = init_progress_state_fn(
        total=int(total),
        t0_all=float(t0_all),
        audit_prev_chain_hash=str(audit_prev_chain_hash),
    )

    run_manifest_path = run_dir / "run_manifest.json"
    run_manifest = dict(
        build_and_write_initial_run_manifest_fn(
            run_manifest_path=run_manifest_path,
            write_json_fn=write_json_fn,
            kwargs=dict(
                run_dir=run_dir,
                profile=str(profile),
                mode=str(canonical_run_mode_fn(str(pipeline_run_mode))),
                oracle_mode=str(oracle_mode),
                oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
                oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
                oracle_assist_selection_requested=bool(
                    oracle_assist_selection_requested
                ),
                oracle_assist_selection_effective=bool(
                    oracle_assist_selection_effective
                ),
                direction=str(direction_value),
                order=str(order),
                python_version=str(sys.version.split()[0]),
                platform_name=str(platform.platform()),
                git_short=str(git_short_fn()),
                git_commit=str(git_commit_fn()),
                git_dirty=bool(git_dirty_fn()),
                scoring_experiment=scoring_meta_for_output_fn(
                    dict(scoring_experiment_meta), root=root
                ),
                non_scoring_lock_hash=str(non_scoring_lock_hash),
                scoring_lock_hash=str(scoring_lock_hash),
                run_config_hash=str(run_config_hash),
                span_assets_dir=str(span_assets_rel_path),
                span_combined_calibration_hash=str(span_combined_calibration_hash),
                span_ecdf_audit_hash=str(span_ecdf_audit_hash),
                run_config_rel_path=str(run_config_path.relative_to(root)),
                history_log_rel_path=str(hist_path.relative_to(root)),
                final_instances_rel_path=str(final_dir.relative_to(root)),
                audit_csv_rel_path=str(audit_csv.relative_to(root)),
                audit_jsonl_rel_path=str(audit_jsonl.relative_to(root)),
                audit_enabled=bool(audit_enabled),
                audit_chain_seed=str(audit_chain_seed),
                total_units=int(total),
            ),
        )
    )

    return dict(
        stages=stages,
        instances=instances,
        total=int(total),
        t0_all=float(t0_all),
        progress=progress,
        run_manifest_path=run_manifest_path,
        run_manifest=run_manifest,
    )


def build_commit_iteration_callback(
    *,
    progress: MutableMapping[str, Any],
    run_manifest: MutableMapping[str, Any],
    get_oracle_consulted_in_decisions_fn: Callable[[], bool],
    commit_iteration_with_checkpoint_fn: Callable[..., None],
    commit_iteration_outputs_fn: Callable[..., Mapping[str, Any]],
    update_run_manifest_progress_fn: Callable[..., Mapping[str, Any]],
    run_dir: Path,
    final_dir: Path,
    root: Path,
    hist_path: Path,
    tiers: Sequence[Any],
    instances: list[dict[str, Any]],
    stages: list[dict[str, Any]],
    heartbeat_seconds: float,
    audit_enabled: bool,
    audit_csv: Path,
    audit_jsonl: Path,
    run_manifest_path: Path,
    write_json_fn: Callable[[Path, Any], None],
) -> Callable[..., None]:
    def _commit_iteration_with_checkpoint(
        *,
        inst_row: Dict[str, Any],
        artifact_payload: Dict[str, Any],
        status_key: str,
        bridge_state: Mapping[str, Any] | None = None,
    ) -> None:
        commit_iteration_with_checkpoint_fn(
            progress=progress,
            run_manifest=run_manifest,
            status_key=str(status_key),
            oracle_consulted_in_decisions=bool(
                get_oracle_consulted_in_decisions_fn()
            ),
            commit_iteration_outputs_fn=commit_iteration_outputs_fn,
            update_run_manifest_progress_fn=update_run_manifest_progress_fn,
            run_dir=run_dir,
            final_dir=final_dir,
            root=root,
            hist_path=hist_path,
            tiers=tiers,
            instances=instances,
            stages=stages,
            inst_row=dict(inst_row),
            artifact_payload=artifact_payload,
            bridge_state=bridge_state,
            heartbeat_seconds=float(heartbeat_seconds),
            audit_enabled=bool(audit_enabled),
            audit_csv=audit_csv,
            audit_jsonl=audit_jsonl,
        )
        write_json_fn(run_manifest_path, run_manifest)

    return _commit_iteration_with_checkpoint
