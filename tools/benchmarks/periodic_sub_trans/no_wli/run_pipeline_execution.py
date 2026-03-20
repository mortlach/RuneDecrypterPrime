from __future__ import annotations

from typing import Any, Dict, Mapping

from tools.benchmarks.periodic_sub_trans.no_wli.iteration_matrix_builder import (
    build_iteration_matrix_config,
    build_iteration_matrix_fns,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_matrix_flow import (
    run_iteration_matrix,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_outcome import (
    build_stage2_diagnostics,
    build_stage3_diagnostics,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_post_stage3 import (
    finalize_iteration_post_stage3,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_pre_stage3 import (
    run_iteration_pre_stage3,
)
from tools.benchmarks.periodic_sub_trans.no_wli.oracle_floor_guard import (
    build_oracle_floor_guard_result,
)
from tools.benchmarks.periodic_sub_trans.no_wli.oracle_floor_guard_flow import (
    handle_oracle_floor_guard_if_triggered,
)
from tools.benchmarks.periodic_sub_trans.no_wli.oracle_precheck import (
    evaluate_oracle_precheck,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_completion import (
    finalize_run_outputs,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_iteration_wiring import (
    build_iteration_wiring,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_manifest import (
    build_and_write_initial_run_manifest,
    update_run_manifest_progress,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_manifest_setup import (
    build_commit_iteration_callback,
    initialize_run_state,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_progress import (
    commit_iteration_with_checkpoint,
    init_progress_state,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_summary import (
    derive_outcome_code,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage_engine_contract import (
    write_stage_engine_contract_artifacts,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage_engine_trace import (
    make_stage_engine_trace_emitter,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_bridges import (
    build_iteration_payloads_bridge,
    build_iteration_runtime_bridge,
    build_stage3_runtime_call_context_bridge,
    evaluate_stage3_entry_policy_bridge,
    finalize_stage2_archive_bridge,
    prepare_stage3_refine_inputs_bridge,
    run_stage1_substitution_bridge,
    run_stage2_search_bridge,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage12_pipeline import (
    run_stage12_pipeline,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_iteration_flow import (
    run_stage3_iteration_flow,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_span_summary import (
    summarize_stage3_span,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_finalize import (
    finalize_iteration_and_commit,
)
from tools.benchmarks.periodic_sub_trans.no_wli.autoskip_proven import (
    handle_autoskip_proven_iteration,
)


def execute_pipeline_from_startup(
    *,
    state: Mapping[str, Any],
    startup: Mapping[str, Any],
) -> None:
    direction = startup["direction"]
    pt_base = startup["pt_base"]
    wli_base = startup["wli_base"]
    root = startup["root"]
    run_dir = startup["run_dir"]
    best_dir = startup["best_dir"]
    final_dir = startup["final_dir"]
    audit_csv = startup["audit_csv"]
    audit_jsonl = startup["audit_jsonl"]
    audit_prev_chain_hash = str(startup["audit_prev_chain_hash"])
    hist = startup["hist"]
    autoskip_effective = bool(startup["autoskip_effective"])
    proven_index = dict(startup["proven_index"])
    oracle_mode = str(startup["oracle_mode"])
    oracle_decision_paths_enabled = bool(startup["oracle_decision_paths_enabled"])
    oracle_assist_selection_effective = bool(startup["oracle_assist_selection_effective"])
    oracle_consulted_in_decisions = bool(startup["oracle_consulted_in_decisions"])
    scoring_experiment_meta = dict(startup["scoring_experiment_meta"])
    run_config_path = startup["run_config_path"]
    non_scoring_lock_hash = str(startup["non_scoring_lock_hash"])
    scoring_lock_hash = str(startup["scoring_lock_hash"])
    run_config_hash = str(startup["run_config_hash"])
    span_assets_dir = startup["span_assets_dir"]
    span_combined_calibration_hash = str(startup["span_combined_calibration_hash"])
    span_ecdf_audit_hash = str(startup["span_ecdf_audit_hash"])
    span_assets_rel_path = str(startup["span_assets_rel_path"])

    def _mark_oracle_decision_use() -> None:
        nonlocal oracle_consulted_in_decisions
        if bool(oracle_decision_paths_enabled):
            oracle_consulted_in_decisions = True

    run_state = initialize_run_state(
        tiers=state["TIERS"],
        text_offsets=state["TEXT_OFFSETS"],
        key_seeds=state["KEY_SEEDS"],
        audit_prev_chain_hash=str(audit_prev_chain_hash),
        run_dir=run_dir,
        root=root,
        direction_value=str(direction.value),
        order=str(state["ORDER"]),
        profile=str(state["PROFILE"]),
        pipeline_run_mode=str(state["PIPELINE_RUN_MODE"]),
        canonical_run_mode_fn=state["_canonical_run_mode"],
        oracle_mode=str(oracle_mode),
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        oracle_assist_selection_requested=bool(state["ORACLE_ASSIST_SELECTION"]),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        scoring_experiment_meta=dict(scoring_experiment_meta),
        scoring_meta_for_output_fn=state["_scoring_meta_for_output"],
        non_scoring_lock_hash=str(non_scoring_lock_hash),
        scoring_lock_hash=str(scoring_lock_hash),
        run_config_hash=str(run_config_hash),
        span_assets_rel_path=str(span_assets_rel_path),
        span_combined_calibration_hash=str(span_combined_calibration_hash),
        span_ecdf_audit_hash=str(span_ecdf_audit_hash),
        run_config_path=run_config_path,
        hist_path=hist,
        final_dir=final_dir,
        audit_csv=audit_csv,
        audit_jsonl=audit_jsonl,
        audit_enabled=bool(state["AUDIT_HASH_CHAIN_ENABLED"]),
        audit_chain_seed=str(state["AUDIT_HASH_CHAIN_SEED"]),
        git_short_fn=state["_git_short"],
        git_commit_fn=state["_git_commit"],
        git_dirty_fn=state["_git_dirty"],
        write_json_fn=state["write_json"],
        init_progress_state_fn=init_progress_state,
        build_and_write_initial_run_manifest_fn=build_and_write_initial_run_manifest,
    )
    stages = run_state["stages"]
    instances = run_state["instances"]
    total = int(run_state["total"])
    t0_all = float(run_state["t0_all"])
    progress = run_state["progress"]
    run_manifest_path = run_state["run_manifest_path"]
    run_manifest = run_state["run_manifest"]

    # Emit concrete StageSpec/PolicySpec artifacts for this run configuration.
    write_stage_engine_contract_artifacts(
        run_dir=run_dir,
        state=state,
        write_json_fn=state["write_json"],
    )

    runner_state = state
    commit_iteration_outputs_fn = lambda **kwargs: state[
        "_commit_iteration_outputs_bridge_external"
    ](state=runner_state, **kwargs)

    def _get_oracle_consulted_in_decisions() -> bool:
        return bool(oracle_consulted_in_decisions)

    commit_iteration_callback = build_commit_iteration_callback(
        progress=progress,
        run_manifest=run_manifest,
        get_oracle_consulted_in_decisions_fn=_get_oracle_consulted_in_decisions,
        commit_iteration_with_checkpoint_fn=commit_iteration_with_checkpoint,
        commit_iteration_outputs_fn=commit_iteration_outputs_fn,
        update_run_manifest_progress_fn=update_run_manifest_progress,
        run_dir=run_dir,
        final_dir=final_dir,
        root=root,
        hist_path=hist,
        tiers=state["TIERS"],
        instances=instances,
        stages=stages,
        heartbeat_seconds=float(state["HEARTBEAT_SECONDS"]),
        audit_enabled=bool(state["AUDIT_HASH_CHAIN_ENABLED"]),
        audit_csv=audit_csv,
        audit_jsonl=audit_jsonl,
        run_manifest_path=run_manifest_path,
        write_json_fn=state["write_json"],
    )

    handlers: Dict[str, Any] = dict(
        slice_word_aligned_fn=state["base"]._slice_word_aligned,
        handle_autoskip_proven_iteration_fn=handle_autoskip_proven_iteration,
        run_iteration_pre_stage3_fn=run_iteration_pre_stage3,
        run_stage3_iteration_flow_fn=run_stage3_iteration_flow,
        finalize_iteration_post_stage3_fn=finalize_iteration_post_stage3,
        evaluate_oracle_precheck_fn=evaluate_oracle_precheck,
        handle_oracle_floor_guard_if_triggered_fn=handle_oracle_floor_guard_if_triggered,
        run_stage12_pipeline_fn=run_stage12_pipeline,
        build_oracle_floor_guard_result_fn=build_oracle_floor_guard_result,
        summarize_stage3_span_fn=summarize_stage3_span,
        build_stage2_diagnostics_fn=build_stage2_diagnostics,
        build_stage3_diagnostics_fn=build_stage3_diagnostics,
        finalize_iteration_and_commit_fn=finalize_iteration_and_commit,
        safe_preview_latin_fn=state["base"]._safe_preview_latin,
        stage_engine_trace_emit_fn=make_stage_engine_trace_emitter(run_dir=run_dir),
    )
    wiring = build_iteration_wiring(
        state=runner_state,
        run_dir=run_dir,
        oracle_mode=str(oracle_mode),
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        get_oracle_consulted_in_decisions_fn=_get_oracle_consulted_in_decisions,
        build_iteration_payloads_bridge_fn=build_iteration_payloads_bridge,
        derive_outcome_code_fn=derive_outcome_code,
        commit_iteration_with_checkpoint_fn=commit_iteration_callback,
        build_iteration_runtime_bridge_fn=build_iteration_runtime_bridge,
        scorer_objective_summary_fn=state["_scorer_objective_summary"],
        oracle_score_for_stage_fn=state["_oracle_score_for_stage"],
        weights_text_fn=state["_weights_text"],
        mark_oracle_decision_use_fn=_mark_oracle_decision_use,
        print_stage_preview_fn=state["_print_stage_preview"],
        run_stage1_substitution_bridge_fn=run_stage1_substitution_bridge,
        run_stage2_search_bridge_fn=run_stage2_search_bridge,
        finalize_stage2_archive_bridge_fn=finalize_stage2_archive_bridge,
        evaluate_stage3_entry_policy_bridge_fn=evaluate_stage3_entry_policy_bridge,
        prepare_stage3_refine_inputs_bridge_fn=prepare_stage3_refine_inputs_bridge,
        fmt_finite_float_fn=state["_fmt_finite_float"],
        build_stage3_runtime_call_context_bridge_fn=build_stage3_runtime_call_context_bridge,
        build_iteration_matrix_config_fn=build_iteration_matrix_config,
        build_iteration_matrix_fns_fn=build_iteration_matrix_fns,
        handlers=handlers,
    )
    stage3_runtime_call_ctx = wiring["stage3_runtime_call_ctx"]
    iteration_config = wiring["iteration_config"]
    iteration_fns = wiring["iteration_fns"]

    run_iteration_matrix(
        tiers=state["TIERS"],
        text_offsets=state["TEXT_OFFSETS"],
        key_seeds=state["KEY_SEEDS"],
        pt_base=pt_base,
        wli_base=wli_base,
        direction=direction,
        span_assets_dir=span_assets_dir,
        scoring_experiment_meta=dict(scoring_experiment_meta),
        autoskip_effective=bool(autoskip_effective),
        proven_index=proven_index,
        instances=instances,
        stages=stages,
        stage3_runtime_call_ctx=stage3_runtime_call_ctx,
        config=iteration_config,
        fns=iteration_fns,
        log_prefix="[pipeline_no_wli]",
    )

    finalize_run_outputs(
        run_dir=run_dir,
        final_dir=final_dir,
        best_dir=best_dir,
        root=root,
        hist_path=hist,
        t0_all=float(t0_all),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        total=int(total),
        done=int(progress["done"]),
        status_counts=dict(progress["status_counts"]),
        history_rows_written=int(progress["history_rows_written"]),
        audit_rows_written=int(progress["audit_rows_written"]),
        audit_prev_chain_hash=str(progress["audit_prev_chain_hash"]),
        tiers=state["TIERS"],
        instances=instances,
        stages=stages,
        run_manifest=run_manifest,
        run_manifest_path=run_manifest_path,
        write_json_fn=state["write_json"],
        write_pipeline_snapshot_files_fn=state["write_pipeline_snapshot_files"],
        build_summary_fn=state["_build_summary"],
        sha256_file_fn=state["_sha256_file"],
        format_seconds_fn=lambda seconds: state["base"]._format_seconds(float(seconds)),
        log_prefix="[pipeline_no_wli]",
    )
