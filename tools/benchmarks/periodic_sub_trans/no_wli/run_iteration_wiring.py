from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Mapping


def build_iteration_wiring(
    *,
    state: Mapping[str, Any],
    run_dir: Path,
    oracle_mode: str,
    oracle_decision_paths_enabled: bool,
    oracle_assist_selection_effective: bool,
    get_oracle_consulted_in_decisions_fn: Callable[[], bool],
    build_iteration_payloads_bridge_fn: Callable[..., Any],
    derive_outcome_code_fn: Callable[..., Any],
    commit_iteration_with_checkpoint_fn: Callable[..., Any],
    build_iteration_runtime_bridge_fn: Callable[..., Any],
    scorer_objective_summary_fn: Callable[..., Any],
    oracle_score_for_stage_fn: Callable[..., Any],
    weights_text_fn: Callable[..., Any],
    mark_oracle_decision_use_fn: Callable[..., Any],
    print_stage_preview_fn: Callable[..., Any],
    run_stage1_substitution_bridge_fn: Callable[..., Any],
    run_stage2_search_bridge_fn: Callable[..., Any],
    finalize_stage2_archive_bridge_fn: Callable[..., Any],
    evaluate_stage3_entry_policy_bridge_fn: Callable[..., Any],
    prepare_stage3_refine_inputs_bridge_fn: Callable[..., Any],
    fmt_finite_float_fn: Callable[..., Any],
    build_stage3_runtime_call_context_bridge_fn: Callable[..., Any],
    build_iteration_matrix_config_fn: Callable[..., Any],
    build_iteration_matrix_fns_fn: Callable[..., Any],
    handlers: Dict[str, Any],
) -> Dict[str, Any]:
    runner_state = state
    build_iteration_runtime_fn = lambda **kwargs: build_iteration_runtime_bridge_fn(
        state=runner_state, **kwargs
    )
    run_stage1_substitution_fn = lambda **kwargs: run_stage1_substitution_bridge_fn(
        state=runner_state, **kwargs
    )
    run_stage2_search_fn = lambda **kwargs: run_stage2_search_bridge_fn(
        state=runner_state, **kwargs
    )
    finalize_stage2_archive_fn = lambda **kwargs: finalize_stage2_archive_bridge_fn(
        state=runner_state, **kwargs
    )
    evaluate_stage3_entry_policy_fn = (
        lambda **kwargs: evaluate_stage3_entry_policy_bridge_fn(
            state=runner_state, **kwargs
        )
    )
    prepare_stage3_refine_inputs_fn = (
        lambda **kwargs: prepare_stage3_refine_inputs_bridge_fn(
            state=runner_state, **kwargs
        )
    )
    build_iteration_payloads_fn = lambda **kwargs: build_iteration_payloads_bridge_fn(
        state=runner_state, **kwargs
    )
    stage3_runtime_call_ctx = build_stage3_runtime_call_context_bridge_fn(
        state=runner_state,
        run_dir=run_dir,
    )
    iteration_config = build_iteration_matrix_config_fn(
        state=runner_state,
        oracle_mode=str(oracle_mode),
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
    )
    iteration_fns = build_iteration_matrix_fns_fn(
        get_oracle_consulted_in_decisions_fn=get_oracle_consulted_in_decisions_fn,
        build_iteration_payloads_fn=build_iteration_payloads_fn,
        derive_outcome_code_fn=derive_outcome_code_fn,
        commit_iteration_with_checkpoint_fn=commit_iteration_with_checkpoint_fn,
        build_iteration_runtime_fn=build_iteration_runtime_fn,
        scorer_objective_summary_fn=scorer_objective_summary_fn,
        oracle_score_for_stage_fn=oracle_score_for_stage_fn,
        weights_text_fn=weights_text_fn,
        mark_oracle_decision_use_fn=mark_oracle_decision_use_fn,
        print_stage_preview_fn=print_stage_preview_fn,
        run_stage1_substitution_fn=run_stage1_substitution_fn,
        run_stage2_search_fn=run_stage2_search_fn,
        finalize_stage2_archive_fn=finalize_stage2_archive_fn,
        evaluate_stage3_entry_policy_fn=evaluate_stage3_entry_policy_fn,
        prepare_stage3_refine_inputs_fn=prepare_stage3_refine_inputs_fn,
        fmt_finite_float_fn=fmt_finite_float_fn,
        handlers=dict(handlers),
    )
    return dict(
        stage3_runtime_call_ctx=stage3_runtime_call_ctx,
        iteration_config=iteration_config,
        iteration_fns=iteration_fns,
    )
