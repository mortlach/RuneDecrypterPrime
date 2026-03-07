from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Mapping


def bootstrap_main_run(
    *,
    state: Mapping[str, Any],
    direction_ltr: Any,
    direction_rtl: Any,
    require_assets_fn: Callable[..., None],
    encode_long_plaintext_fn: Callable[[Any], tuple[Any, Any]],
    repo_root_fn: Callable[[], Path],
    make_flavor_run_dir_fn: Callable[..., Path],
    prepare_run_environment_fn: Callable[..., Dict[str, Any]],
    load_proven_index_fn: Callable[..., Mapping[Any, Any]],
    build_run_mode_info_fn: Callable[[str | None], Any],
    oracle_mode_normalized_fn: Callable[[], str],
    apply_run_mode_fn: Callable[[], None],
    apply_kaeding_progress_settings_fn: Callable[[], None],
    apply_scoring_experiment_profile_fn: Callable[[], Dict[str, Any]],
    build_run_config_fn: Callable[..., Dict[str, Any]],
    persist_run_config_with_locks_fn: Callable[..., Mapping[str, str]],
    resolve_repo_path_fn: Callable[[Path | str | None], Path | None],
    stage3_search_cfg_fn: Callable[..., Dict[str, Any]],
    build_setup_logging_payload_fn: Callable[..., Dict[str, Any]],
    emit_setup_logging_fn: Callable[..., None],
    scorer_objective_summary_fn: Callable[[Dict[str, Any]], str],
    weights_text_fn: Callable[[Dict[int, float]], str],
    scorer_cfg_for_output_fn: Callable[..., Dict[str, Any]],
    scoring_meta_for_output_fn: Callable[..., Dict[str, Any]],
    build_non_scoring_lock_payload_fn: Callable[[], Dict[str, Any]],
    build_scoring_lock_payload_fn: Callable[[], Dict[str, Any]],
    hash_payload_fn: Callable[[Dict[str, Any]], str],
    write_json_fn: Callable[[Path, Any], None],
    git_short_fn: Callable[[], str],
    git_commit_fn: Callable[[], str],
    git_dirty_fn: Callable[[], bool],
    sha256_file_fn: Callable[[Path], str],
    to_repo_rel_path_fn: Callable[[Path | str | None, Path], str],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    apply_run_mode_fn()
    apply_kaeding_progress_settings_fn()
    scoring_experiment_meta = dict(apply_scoring_experiment_profile_fn())

    env = prepare_run_environment_fn(
        encoding_dir=str(state["ENCODING_DIR"]),
        direction_ltr=direction_ltr,
        direction_rtl=direction_rtl,
        require_assets_fn=require_assets_fn,
        encode_long_plaintext_fn=encode_long_plaintext_fn,
        repo_root_fn=repo_root_fn,
        make_flavor_run_dir_fn=make_flavor_run_dir_fn,
        audit_csv_name=str(state["AUDIT_HASH_CHAIN_CSV"]),
        audit_jsonl_name=str(state["AUDIT_HASH_CHAIN_JSONL"]),
        audit_chain_seed=str(state["AUDIT_HASH_CHAIN_SEED"]),
        autoskip_proven=bool(state["AUTOSKIP_PROVEN"]),
        force_rerun_proven=bool(state["FORCE_RERUN_PROVEN"]),
        autoskip_proven_min_match=float(state["AUTOSKIP_PROVEN_MIN_MATCH"]),
        load_proven_index_fn=load_proven_index_fn,
        build_run_mode_info_fn=build_run_mode_info_fn,
        run_mode=str(state["PIPELINE_RUN_MODE"]),
        oracle_mode_normalized_fn=oracle_mode_normalized_fn,
        oracle_assist_selection_requested=bool(state["ORACLE_ASSIST_SELECTION"]),
    )

    direction = env["direction"]
    root = env["root"]
    run_dir = env["run_dir"]
    audit_csv = env["audit_csv"]
    audit_jsonl = env["audit_jsonl"]
    hist = env["hist"]
    mode_raw = str(env["mode_raw"])
    mode_canonical = str(env["mode_canonical"])
    mode_intent = str(env["mode_intent"])
    stage3_can_skip = bool(env["stage3_can_skip"])
    oracle_mode = str(env["oracle_mode"])
    oracle_decision_paths_enabled = bool(env["oracle_decision_paths_enabled"])
    oracle_assist_selection_effective = bool(env["oracle_assist_selection_effective"])
    autoskip_effective = bool(env["autoskip_effective"])
    proven_index = dict(env["proven_index"])

    run_config = build_run_config_fn(
        state=state,
        mode_canonical=str(mode_canonical),
        mode_raw=str(mode_raw),
        mode_intent=str(mode_intent),
        stage3_can_skip=bool(stage3_can_skip),
        scoring_experiment_meta=dict(scoring_experiment_meta),
        root=root,
        direction=direction,
        autoskip_effective=bool(autoskip_effective),
        proven_known=int(len(proven_index)),
        oracle_mode=str(oracle_mode),
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        is_adaptive_focus_mode_fn=state["_is_adaptive_focus_mode"],
        scorer_cfg_for_output_fn=scorer_cfg_for_output_fn,
        stage3_search_cfg_fn=stage3_search_cfg_fn,
        scoring_meta_for_output_fn=scoring_meta_for_output_fn,
    )
    run_config_path = run_dir / "run_config.json"
    run_config_meta = persist_run_config_with_locks_fn(
        run_config=run_config,
        run_config_path=run_config_path,
        build_non_scoring_lock_payload_fn=build_non_scoring_lock_payload_fn,
        build_scoring_lock_payload_fn=build_scoring_lock_payload_fn,
        hash_payload_fn=hash_payload_fn,
        write_json_fn=write_json_fn,
        git_short_fn=git_short_fn,
        git_commit_fn=git_commit_fn,
        git_dirty_fn=git_dirty_fn,
        sha256_file_fn=sha256_file_fn,
    )
    non_scoring_lock_hash = str(run_config_meta["non_scoring_lock_hash"])
    scoring_lock_hash = str(run_config_meta["scoring_lock_hash"])
    run_config_hash = str(run_config_meta["run_config_hash"])

    span_assets_dir = resolve_repo_path_fn(
        str(scoring_experiment_meta.get("span_assets_dir", "")).strip() or None
    )
    span_combined_calibration_hash = ""
    span_ecdf_audit_hash = ""
    if span_assets_dir is not None and span_assets_dir.exists():
        combined_fp = span_assets_dir / "combined_calibration.json"
        ecdf_audit_fp = span_assets_dir / "ecdf_audit.json"
        if combined_fp.exists():
            span_combined_calibration_hash = sha256_file_fn(combined_fp)
        if ecdf_audit_fp.exists():
            span_ecdf_audit_hash = sha256_file_fn(ecdf_audit_fp)

    stage3_search_cfg_preview = stage3_search_cfg_fn(direction=direction)
    emit_setup_logging_fn(
        **build_setup_logging_payload_fn(
            state=state,
            run_config=run_config,
            scoring_experiment_meta=dict(scoring_experiment_meta),
            mode_canonical=str(mode_canonical),
            mode_raw=str(mode_raw),
            mode_intent=str(mode_intent),
            stage3_can_skip=bool(stage3_can_skip),
            direction_value=str(direction.value),
            oracle_mode=str(oracle_mode),
            oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
            autoskip_effective=bool(autoskip_effective),
            proven_known=int(len(proven_index)),
            hist_rel_path=str(hist.relative_to(root)),
            non_scoring_lock_hash=str(non_scoring_lock_hash),
            scoring_lock_hash=str(scoring_lock_hash),
            run_config_hash=str(run_config_hash),
            reports_rel_path=str(run_dir.relative_to(root)),
            audit_csv_rel_path=str(audit_csv.relative_to(root)),
            audit_jsonl_rel_path=str(audit_jsonl.relative_to(root)),
            scorer_objective_summary_fn=scorer_objective_summary_fn,
            weights_text_fn=weights_text_fn,
            stage3_search_cfg_preview=stage3_search_cfg_preview,
            log_prefix=str(log_prefix),
        )
    )

    out = dict(env)
    out.update(
        scoring_experiment_meta=dict(scoring_experiment_meta),
        run_config=run_config,
        run_config_path=run_config_path,
        non_scoring_lock_hash=str(non_scoring_lock_hash),
        scoring_lock_hash=str(scoring_lock_hash),
        run_config_hash=str(run_config_hash),
        span_assets_dir=span_assets_dir,
        span_combined_calibration_hash=str(span_combined_calibration_hash),
        span_ecdf_audit_hash=str(span_ecdf_audit_hash),
        span_assets_rel_path=str(to_repo_rel_path_fn(span_assets_dir, root)),
    )
    return out
