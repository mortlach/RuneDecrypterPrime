from __future__ import annotations

from typing import Any, Callable, Dict, Mapping

import numpy as np


def run_iteration_pre_stage3(
    *,
    state: Mapping[str, Any],
    stage1_label: str,
    stage2_label: str,
    stage3_label: str,
    stage3_continue_after_solve: bool,
    stage3_phaseb_top_n: int,
    stage3_phaseb_gate_delta_floor: float,
    stage3_phaseb_gate_end_gain_floor: float,
    stage3_c1_focus_enabled: bool,
    stage3_span_char_pct_min_override: float | None,
    scoring_experiment_c_char_pct_min: float,
    oracle_stage3_floor_guard_eps: float,
    build_iteration_runtime_fn: Callable[..., Dict[str, Any]],
    evaluate_oracle_precheck_fn: Callable[..., Dict[str, Any]],
    handle_oracle_floor_guard_if_triggered_fn: Callable[..., bool],
    run_stage12_pipeline_fn: Callable[..., Dict[str, Any]],
    scorer_objective_summary_fn: Callable[[Dict[str, Any]], str],
    oracle_score_for_stage_fn: Callable[..., float],
    weights_text_fn: Callable[[Mapping[int, float]], str],
    mark_oracle_decision_use_fn: Callable[[], None],
    print_stage_preview_fn: Callable[..., None],
    build_oracle_floor_guard_result_fn: Callable[..., Dict[str, Any]],
    build_iteration_payloads_fn: Callable[..., Any],
    derive_outcome_code_fn: Callable[..., str],
    commit_iteration_with_checkpoint_fn: Callable[..., None],
    run_stage1_substitution_fn: Callable[..., Dict[str, Any]],
    run_stage2_search_fn: Callable[..., Dict[str, Any]],
    finalize_stage2_archive_fn: Callable[..., Dict[str, Any]],
) -> Dict[str, Any]:
    tier = state["tier"]
    text_id = int(state["text_id"])
    key_seed = int(state["key_seed"])
    off = int(state["off"])
    offset_used = int(state["offset_used"])
    pt_idx = np.asarray(state["pt_idx"], dtype=np.uint8)
    wli = state["wli"]
    direction = state["direction"]
    span_assets_dir = state["span_assets_dir"]
    scoring_experiment_meta = dict(state["scoring_experiment_meta"])
    oracle_mode = str(state["oracle_mode"])
    oracle_consulted_in_decisions = bool(state["oracle_consulted_in_decisions"])
    oracle_decision_paths_enabled = bool(state["oracle_decision_paths_enabled"])
    oracle_assist_selection_effective = bool(state["oracle_assist_selection_effective"])
    stages = state["stages"]
    instances = state["instances"]

    iteration_runtime = build_iteration_runtime_fn(
        tier=tier,
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        key_seed=int(key_seed),
        direction=direction,
        span_assets_dir=span_assets_dir,
        scoring_experiment_meta=scoring_experiment_meta,
    )
    key_len = int(iteration_runtime["key_len"])
    key_true = np.asarray(iteration_runtime["key_true"], dtype=np.int16)
    cfg_full = iteration_runtime["cfg_full"]
    cfg_sub = iteration_runtime["cfg_sub"]
    full_cipher = iteration_runtime["full_cipher"]
    sub_cipher = iteration_runtime["sub_cipher"]
    ct_idx = np.asarray(iteration_runtime["ct_idx"], dtype=np.uint8)
    sub_len = int(iteration_runtime["sub_len"])
    true_sub = np.asarray(iteration_runtime["true_sub"], dtype=np.int16)
    pt_stage1_oracle = np.asarray(iteration_runtime["pt_stage1_oracle"], dtype=np.uint8)
    stage3_phase_switch_enabled = bool(iteration_runtime["stage3_phase_switch_enabled"])
    stage3_phaseA_experiment = str(iteration_runtime["stage3_phaseA_experiment"])
    stage3_phaseB_experiment = str(iteration_runtime["stage3_phaseB_experiment"])
    scorer_stage1 = dict(iteration_runtime["scorer_stage1"])
    scorer_stage2 = dict(iteration_runtime["scorer_stage2"])
    scorer_full = dict(iteration_runtime["scorer_full"])
    scorer_stage3_phaseA = dict(iteration_runtime["scorer_stage3_phaseA"])
    scorer_stage3_phaseB = dict(iteration_runtime["scorer_stage3_phaseB"])
    scorer_stage1_runtime = iteration_runtime["scorer_stage1_runtime"]
    scorer_stage2_runtime = iteration_runtime["scorer_stage2_runtime"]
    scorer_stage3_search_runtime = iteration_runtime["scorer_stage3_search_runtime"]
    scorer_full_runtime = iteration_runtime["scorer_full_runtime"]
    scorer_basin_judge_runtime = iteration_runtime["scorer_basin_judge_runtime"]
    scorer_word_ngram_report_runtime = iteration_runtime.get(
        "scorer_word_ngram_report_runtime",
        None,
    )
    scorer_stage3_phaseA_runtime = iteration_runtime["scorer_stage3_phaseA_runtime"]
    stage2_judge_policy = str(iteration_runtime["stage2_judge_policy"])
    scorer_stage2_judge_runtime = iteration_runtime["scorer_stage2_judge_runtime"]
    scorer_stage2_judge_cfg = dict(iteration_runtime["scorer_stage2_judge_cfg"])
    scorer_stage2_pass1_primary_runtime = iteration_runtime[
        "scorer_stage2_pass1_primary_runtime"
    ]
    scorer_stage2_pass1_fallback_runtime = iteration_runtime[
        "scorer_stage2_pass1_fallback_runtime"
    ]

    oracle_pre = evaluate_oracle_precheck_fn(
        tier_name=str(tier.name),
        text_id=int(text_id),
        key_seed=int(key_seed),
        pt_stage1_oracle=np.asarray(pt_stage1_oracle, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        cfg_sub=cfg_sub,
        cfg_full=cfg_full,
        scorer_stage1=dict(scorer_stage1),
        scorer_stage2=dict(scorer_stage2),
        scorer_full=dict(scorer_full),
        stage1_label=str(stage1_label),
        stage2_label=str(stage2_label),
        stage3_label=str(stage3_label),
        stage2_judge_policy=str(stage2_judge_policy),
        stage2_judge_objective_summary=str(
            scorer_objective_summary_fn(scorer_stage2_judge_cfg)
        ),
        stage3_phase_switch_enabled=bool(stage3_phase_switch_enabled),
        stage3_phaseA_experiment=str(stage3_phaseA_experiment),
        stage3_phaseB_experiment=str(stage3_phaseB_experiment),
        scoring_experiment_c_char_pct_min=float(scoring_experiment_c_char_pct_min),
        stage3_span_char_pct_min_override=stage3_span_char_pct_min_override,
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        oracle_stage3_floor_guard_eps=float(oracle_stage3_floor_guard_eps),
        oracle_score_for_stage_fn=oracle_score_for_stage_fn,
        weights_text_fn=weights_text_fn,
        log_prefix="[pipeline_no_wli]",
    )
    oracle_s1 = float(oracle_pre["oracle_s1"])
    oracle_s2 = float(oracle_pre["oracle_s2"])
    oracle_s3 = float(oracle_pre["oracle_s3"])
    stage3_phaseB_char_pct_min_dynamic = float(
        oracle_pre["stage3_phaseB_char_pct_min_dynamic"]
    )
    stage3_phaseB_char_pct_min_source = str(
        oracle_pre["stage3_phaseB_char_pct_min_source"]
    )
    if handle_oracle_floor_guard_if_triggered_fn(
        oracle_pre=dict(oracle_pre),
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        off=int(off),
        offset_used=int(offset_used),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        oracle_mode=str(oracle_mode),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        stage3_continue_after_solve=bool(stage3_continue_after_solve),
        stage3_phaseb_top_n=int(stage3_phaseb_top_n),
        stage3_phaseb_gate_delta_floor=float(stage3_phaseb_gate_delta_floor),
        stage3_phaseb_gate_end_gain_floor=float(stage3_phaseb_gate_end_gain_floor),
        stage3_c1_focus_enabled=bool(stage3_c1_focus_enabled),
        build_oracle_floor_guard_result_fn=build_oracle_floor_guard_result_fn,
        build_iteration_payloads_fn=build_iteration_payloads_fn,
        derive_outcome_code_fn=derive_outcome_code_fn,
        commit_iteration_with_checkpoint_fn=commit_iteration_with_checkpoint_fn,
        mark_oracle_decision_use_fn=mark_oracle_decision_use_fn,
        stages=stages,
        instances=instances,
    ):
        return dict(continue_iteration=True)

    if not np.array_equal(
        np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=key_true), dtype=np.uint8),
        np.asarray(pt_idx, dtype=np.uint8),
    ):
        raise RuntimeError(
            f"[pipeline_no_wli] gate0 roundtrip failed tier={tier.name} text={text_id} key_seed={key_seed}"
        )
    print_stage_preview_fn(label="oracle", pt=pt_idx.tolist(), wli=wli, match_ratio=1.0)

    stage12 = run_stage12_pipeline_fn(
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        true_sub=np.asarray(true_sub, dtype=np.int16),
        sub_len=int(sub_len),
        wli=wli,
        direction=direction,
        scorer_stage1=dict(scorer_stage1),
        scorer_stage1_runtime=scorer_stage1_runtime,
        sub_cipher=sub_cipher,
        scorer_stage2=dict(scorer_stage2),
        scorer_stage2_runtime=scorer_stage2_runtime,
        scorer_stage2_pass1_primary_runtime=scorer_stage2_pass1_primary_runtime,
        scorer_stage2_pass1_fallback_runtime=scorer_stage2_pass1_fallback_runtime,
        full_cipher=full_cipher,
        scorer_stage2_judge_cfg=dict(scorer_stage2_judge_cfg),
        scorer_stage2_judge_runtime=scorer_stage2_judge_runtime,
        scorer_full_runtime=scorer_full_runtime,
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        run_stage1_substitution_fn=run_stage1_substitution_fn,
        run_stage2_search_fn=run_stage2_search_fn,
        finalize_stage2_archive_fn=finalize_stage2_archive_fn,
        mark_oracle_decision_use_fn=mark_oracle_decision_use_fn,
        stages=stages,
    )

    return dict(
        continue_iteration=False,
        key_len=int(key_len),
        full_cipher=full_cipher,
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        scorer_stage2=dict(scorer_stage2),
        scorer_full=dict(scorer_full),
        scorer_stage3_phaseA=dict(scorer_stage3_phaseA),
        scorer_stage3_phaseB=dict(scorer_stage3_phaseB),
        scorer_stage3_search_runtime=scorer_stage3_search_runtime,
        scorer_basin_judge_runtime=scorer_basin_judge_runtime,
        scorer_word_ngram_report_runtime=scorer_word_ngram_report_runtime,
        scorer_full_runtime=scorer_full_runtime,
        scorer_stage3_phaseA_runtime=scorer_stage3_phaseA_runtime,
        oracle_s1=float(oracle_s1),
        oracle_s2=float(oracle_s2),
        oracle_s3=float(oracle_s3),
        stage3_phaseA_experiment=str(stage3_phaseA_experiment),
        stage3_phaseB_experiment=str(stage3_phaseB_experiment),
        stage3_phaseB_char_pct_min_dynamic=float(stage3_phaseB_char_pct_min_dynamic),
        stage3_phaseB_char_pct_min_source=str(stage3_phaseB_char_pct_min_source),
        sub_key_match=float(stage12.get("sub_key_match", 0.0)),
        stage1_best_score=float(stage12.get("stage1_best_score", float("nan"))),
        ev1=int(stage12.get("ev1", 0)),
        best2_match=float(stage12.get("best2_match", float("-inf"))),
        best2_score=float(stage12.get("best2_score", float("-inf"))),
        best2_key=stage12.get("best2_key", None),
        best2_pt=stage12.get("best2_pt", None),
        best2_preview=str(stage12.get("best2_preview", "")),
        stage2_evals_total=int(stage12.get("stage2_evals_total", 0)),
        stage2_archive=dict(stage12.get("stage2_archive", {})),
        stage2_continue_to_gate=bool(stage12.get("stage2_continue_to_gate", False)),
        stage2_continue_stop_reason=str(stage12.get("stage2_continue_stop_reason", "")),
        stage2_ranked=list(stage12.get("stage2_ranked", [])),
        stage2_promoted=list(stage12.get("stage2_promoted", [])),
        stage2_entry_score=float(stage12.get("stage2_entry_score", float("-inf"))),
        stage2_entry_score_judge=float(
            stage12.get("stage2_entry_score_judge", float("-inf"))
        ),
        stage2_score_match_spearman=float(
            stage12.get("stage2_score_match_spearman", float("nan"))
        ),
        stage2_topk_payload=list(stage12.get("stage2_topk_payload", [])),
        stage2_topk_has_best_match=bool(stage12.get("stage2_topk_has_best_match", False)),
    )
