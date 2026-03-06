from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, Mapping

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.stage3_runtime_calls import (
    Stage3RuntimeCallContext,
    run_stage3_phasea_restarts_call,
    run_stage3_single_phase_call,
    run_stage3_two_phase_followup_call,
)


def run_stage3_iteration_flow(
    *,
    state: Mapping[str, Any],
    stage3_runtime_call_ctx: Stage3RuntimeCallContext,
    stage3_two_phase_enabled: bool,
    stage3_continue_after_solve: bool,
    stage3_phasea_cfg_default: Dict[str, Any],
    stage3_phaseb_cfg_default: Dict[str, Any],
    stage3_phaseb_top_n_default: int,
    stage3_phaseb_gate_delta_floor_default: float,
    stage3_phaseb_gate_end_gain_floor_default: float,
    solver_stage3_default_cfg: Dict[str, Any],
    stage3_span_basin_judge_k: int,
    tier_heartbeat_seconds: float,
    solve_match_threshold: float,
    stall_delta: float,
    stall_stage_limit: int,
    evaluate_stage3_entry_policy_fn: Callable[..., Dict[str, Any]],
    prepare_stage3_refine_inputs_fn: Callable[..., Dict[str, Any]],
    summarize_stage3_span_fn: Callable[..., Dict[str, Any]],
    mark_oracle_decision_use_fn: Callable[[], None],
    print_stage_preview_fn: Callable[..., None],
    fmt_finite_float_fn: Callable[..., str],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    tier = state["tier"]
    text_id = int(state["text_id"])
    key_seed = int(state["key_seed"])
    t0_i = float(state["t0_i"])
    key_len = int(state["key_len"])
    best2_match = float(state["best2_match"])
    best2_key = state["best2_key"]
    stage2_promoted = list(state["stage2_promoted"])
    stage2_entry_score = float(state["stage2_entry_score"])
    stage2_entry_score_judge = float(state["stage2_entry_score_judge"])
    scorer_stage2 = dict(state["scorer_stage2"])
    scorer_full = dict(state["scorer_full"])
    oracle_s3 = float(state["oracle_s3"])
    oracle_decision_paths_enabled = bool(state["oracle_decision_paths_enabled"])
    ct_idx = np.asarray(state["ct_idx"], dtype=np.uint8)
    pt_idx = np.asarray(state["pt_idx"], dtype=np.uint8)
    wli = state["wli"]
    direction = state["direction"]
    scorer_stage3_phaseA = dict(state["scorer_stage3_phaseA"])
    scorer_stage3_phaseB = dict(state["scorer_stage3_phaseB"])
    scorer_stage3_phaseA_runtime = state["scorer_stage3_phaseA_runtime"]
    scorer_stage3_search_runtime = state["scorer_stage3_search_runtime"]
    scorer_basin_judge_runtime = state["scorer_basin_judge_runtime"]
    scorer_full_runtime = state["scorer_full_runtime"]
    full_cipher = state["full_cipher"]
    stage2_evals_total = int(state["stage2_evals_total"])
    stage2_continue_to_gate = bool(state["stage2_continue_to_gate"])
    stage2_continue_stop_reason = str(state["stage2_continue_stop_reason"])
    stage3_phaseA_experiment = str(state["stage3_phaseA_experiment"])
    stage3_phaseB_experiment = str(state["stage3_phaseB_experiment"])
    stage3_phaseB_char_pct_min_dynamic = float(state["stage3_phaseB_char_pct_min_dynamic"])
    stage3_phaseB_char_pct_min_source = str(state["stage3_phaseB_char_pct_min_source"])
    oracle_assist_selection_effective = bool(state["oracle_assist_selection_effective"])
    stages = state["stages"]

    best3_match, best3_score, stop_reason = float("nan"), float("nan"), "completed_pipeline"
    ev3 = 0
    stage2_gap_to_oracle = float("nan")
    stage3_band_name = ""
    pt3 = np.asarray([], dtype=np.uint8)
    best3_key: list[int] | None = None
    stage3_topk_payload: list[Dict[str, Any]] = []
    stage3_init_target = 0
    stage3_init_actual = 0
    stage3_promoted_keys_count = 0
    stage3_gate_source = ""
    stage3_phaseB_top_n_cfg = 0
    stage3_phaseB_gate_delta_cfg = float("nan")
    stage3_phaseB_gate_end_gain_cfg = float("nan")
    stage3_solve_hits = 0
    stage3_period_init_mult = 1.0
    stage3_period_step_mult = 1.0
    stage3_period_restart_bonus = 0
    stage3_span_active_rate = 0.0
    stage3_span_active_rate_source = "solver_run_telemetry_zero_total"
    stage3_span_eval_total = 0.0
    stage3_span_eval_active = 0.0
    stage3_span_eval_skipped = 0.0
    stage3_span_seconds_total = 0.0
    stage3_span_seconds_active = 0.0
    stage3_span_phaseA_eval_total = 0.0
    stage3_span_phaseA_eval_active = 0.0
    stage3_span_phaseA_eval_skipped = 0.0
    stage3_span_phaseA_seconds_total = 0.0
    stage3_span_phaseA_seconds_active = 0.0
    stage3_span_full_eval_total = 0.0
    stage3_span_full_eval_active = 0.0
    stage3_span_full_eval_skipped = 0.0
    stage3_span_full_seconds_total = 0.0
    stage3_span_full_seconds_active = 0.0
    stage3_span_basin_judge_k_cfg = int(max(1, int(stage3_span_basin_judge_k)))
    stage3_span_basin_judge_k_used = 0
    stage3_span_basin_judge_seconds = 0.0
    stage3_basin_judge_span_calls_total = 0
    stage3_basin_judge_span_calls_active = 0
    stage3_basin_judge_span_calls_rejected_or_gated = 0
    stage3_basin_judge_span_seconds_total = 0.0
    stage3_basin_judge_unique_end_hash = 0
    stage3_scan_phaseA_only = False

    tier_elapsed_before_stage3 = float(time.time() - t0_i)
    stage3_policy = evaluate_stage3_entry_policy_fn(
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        best2_match=float(best2_match),
        stage2_continue_to_gate=bool(stage2_continue_to_gate),
        stage2_continue_stop_reason=str(stage2_continue_stop_reason),
        tier_elapsed_before_stage3=float(tier_elapsed_before_stage3),
        stages=stages,
    )
    stop_reason = str(stage3_policy.get("stop_reason", stop_reason))
    stage3_band_name = str(stage3_policy.get("stage3_band_name", stage3_band_name))
    stage3_scan_phaseA_only = bool(stage3_policy.get("stage3_scan_phaseA_only", False))
    stage3_policy_branch = str(stage3_policy.get("policy_branch", "continue"))
    if stage3_policy_branch == "continue" and best2_key is not None:
        stage3_prep = prepare_stage3_refine_inputs_fn(
            tier=tier,
            key_len=int(key_len),
            key_seed=int(key_seed),
            best2_key=best2_key,
            best2_match=float(best2_match),
            stage2_promoted=stage2_promoted,
            stage2_entry_score=float(stage2_entry_score),
            stage2_entry_score_judge=float(stage2_entry_score_judge),
            scorer_stage2=dict(scorer_stage2),
            scorer_full=dict(scorer_full),
            oracle_s3=float(oracle_s3),
            oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        )
        c1_focus_enabled = bool(stage3_prep.get("c1_focus_enabled", False))
        init3_n = int(stage3_prep.get("init3_n", 1))
        init3 = list(stage3_prep.get("init3", []))
        promoted_keys = list(stage3_prep.get("promoted_keys", []))
        stage3_promoted_keys_count = int(stage3_prep.get("stage3_promoted_keys_count", len(promoted_keys)))
        stage3_init_target = int(init3_n)
        stage3_init_actual = int(len(init3))
        stage3_period_init_mult = float(stage3_prep.get("stage3_period_init_mult", 1.0))
        stage3_period_step_mult = float(stage3_prep.get("stage3_period_step_mult", 1.0))
        stage3_period_restart_bonus = int(stage3_prep.get("stage3_period_restart_bonus", 0))
        stage2_gap_to_oracle = float(stage3_prep.get("stage2_gap_to_oracle", float("nan")))
        stage2_gate_score = float(stage3_prep.get("stage2_gate_score", stage2_entry_score))
        stage2_gate_source = str(stage3_prep.get("stage2_gate_source", "mid"))
        stage3_gate_source = str(stage2_gate_source)
        promoted_best_match = float(stage3_prep.get("promoted_best_match", float("nan")))
        if bool(stage3_prep.get("oracle_used_for_stage3_band", False)):
            mark_oracle_decision_use_fn()
        stage3_band_name = str(stage3_prep.get("stage3_band_name", stage3_band_name))
        stage3_phaseA_cfg = dict(stage3_prep.get("stage3_phaseA_cfg", dict(stage3_phasea_cfg_default)))
        stage3_phaseB_cfg = dict(stage3_prep.get("stage3_phaseB_cfg", dict(stage3_phaseb_cfg_default)))
        stage3_phaseB_top_n = int(stage3_prep.get("stage3_phaseB_top_n", int(stage3_phaseb_top_n_default)))
        stage3_phaseB_gate_delta = float(
            stage3_prep.get("stage3_phaseB_gate_delta", float(stage3_phaseb_gate_delta_floor_default))
        )
        stage3_phaseB_gate_end_gain = float(
            stage3_prep.get(
                "stage3_phaseB_gate_end_gain",
                float(stage3_phaseb_gate_end_gain_floor_default),
            )
        )
        stage3_phaseB_top_n_cfg = int(stage3_phaseB_top_n)
        stage3_phaseB_gate_delta_cfg = float(stage3_phaseB_gate_delta)
        stage3_phaseB_gate_end_gain_cfg = float(stage3_phaseB_gate_end_gain)
        solver_stage3_cfg = dict(stage3_prep.get("solver_stage3_cfg", dict(solver_stage3_default_cfg)))
        print(
            f"{log_prefix} stage3-stop tier={tier.name} text={text_id} key_seed={key_seed} "
            f"band={stage3_band_name} entry_mode=full entry_score={stage2_gate_score:.6f} "
            f"entry_score_source={stage2_gate_source} "
            f"init_keys={len(init3)} promoted_keys={len(promoted_keys)} "
            f"init_target={int(init3_n)} c1_focus={1 if c1_focus_enabled else 0} "
            f"period_scale=(init={float(stage3_period_init_mult):.2f},"
            f"steps={float(stage3_period_step_mult):.2f},"
            f"restart_bonus={int(stage3_period_restart_bonus)}) "
            f"stage2_best_match={float(best2_match):.3f} promoted_best_match={float(promoted_best_match):.3f} "
            f"steps={solver_stage3_cfg.get('steps')} restarts={solver_stage3_cfg.get('restarts')} "
            f"col_batch={solver_stage3_cfg.get('col_batch')} inner_batch={solver_stage3_cfg.get('inner_batch')} "
            f"gap_to_oracle={stage2_gap_to_oracle:.6f}",
            flush=True,
        )
        if bool(stage3_two_phase_enabled):
            print(
                f"{log_prefix} stage3-two-phase "
                f"phaseA={json.dumps(dict(stage3_phaseA_cfg), separators=(',', ':'))} "
                f"phaseB={json.dumps(dict(stage3_phaseB_cfg), separators=(',', ':'))} "
                f"phaseB_top_n={int(stage3_phaseB_top_n)} "
                f"scan_phaseA_only={1 if bool(stage3_scan_phaseA_only) else 0} "
                f"continue_after_solve={1 if bool(stage3_continue_after_solve) else 0} "
                f"gate=(delta={float(stage3_phaseB_gate_delta):.4f},"
                f"end_gain={float(stage3_phaseB_gate_end_gain):.4f})",
                flush=True,
            )
        print(
            f"{log_prefix} tier-heartbeat tier={tier.name} stage=stage3_start "
            f"text={text_id} key_seed={key_seed} elapsed={float(time.time() - t0_i):.1f}s "
            f"stage2_match={fmt_finite_float_fn(best2_match, digits=3)} "
            f"stage2_evals={int(stage2_evals_total)} "
            f"interval={float(tier_heartbeat_seconds):.0f}s",
            flush=True,
        )
        dt3 = 0.0
        ev3 = 0
        phaseB_ran = 0
        phaseB_skipped = 0
        phaseB_top_n_used = 0
        phaseB_skip_reason = ""
        stage3_hb_state: Dict[str, Any] = dict(last_emit_ts=float("-inf"))
        stage3_phaseA_hb_state: Dict[str, Any] = dict(last_emit_ts=float("-inf"))

        if not bool(stage3_two_phase_enabled):
            single_phase = run_stage3_single_phase_call(
                ctx=stage3_runtime_call_ctx,
                tier_name=str(tier.name),
                tier_period=int(tier.period),
                tier_columns=int(tier.columns),
                text_id=int(text_id),
                key_seed=int(key_seed),
                ct_idx=np.asarray(ct_idx, dtype=np.uint8),
                pt_idx=np.asarray(pt_idx, dtype=np.uint8),
                key_len=int(key_len),
                init3=init3,
                solver_stage3_cfg=dict(solver_stage3_cfg),
                scorer_stage3_phaseB=dict(scorer_stage3_phaseB),
                scorer_full_runtime=scorer_full_runtime,
                direction=direction,
                ev3_base=int(ev3),
                stage3_hb_state=stage3_hb_state,
            )
            dt3 += float(single_phase["dt3"])
            ev3 += int(single_phase["ev3"])
            pt3 = np.asarray(single_phase["pt3"], dtype=np.uint8).reshape(-1)
            best3_key = single_phase.get("best3_key", best3_key)
            best3_match = float(single_phase["best3_match"])
            best3_score = float(single_phase["best3_score"])
            stage3_solve_hits += int(1 if bool(single_phase.get("stage3_solve_hit", False)) else 0)
            stage3_span_full_eval_total += float(single_phase["span_total"])
            stage3_span_full_eval_active += float(single_phase["span_active"])
            stage3_span_full_eval_skipped += float(single_phase["span_skipped"])
            stage3_span_full_seconds_total += float(single_phase["span_seconds_total"])
            stage3_span_full_seconds_active += float(single_phase["span_seconds_active"])
            stage3_runtime_call_ctx.append_stage3_topk_from_kaeding_fn(
                payload=stage3_topk_payload,
                kaeding_obj=single_phase.get("kaeding3", {}),
                key_len=int(key_len),
                full_cipher=full_cipher,
                ciphertext=np.asarray(ct_idx, dtype=np.uint8),
                scorer_full_runtime=scorer_full_runtime,
                target_plaintext=np.asarray(pt_idx, dtype=np.uint8),
            )
        else:
            base_seed = int(solver_stage3_cfg.get("seed", solver_stage3_default_cfg.get("seed", 2026)))
            phaseA_cfg = dict(solver_stage3_cfg)
            phaseA_cfg.update(dict(stage3_phaseA_cfg))
            phaseA_cfg["restarts"] = 1
            phaseA_cfg["seed_restarts"] = 0
            phasea_restarts = run_stage3_phasea_restarts_call(
                ctx=stage3_runtime_call_ctx,
                tier_name=str(tier.name),
                tier_period=int(tier.period),
                tier_columns=int(tier.columns),
                text_id=int(text_id),
                key_seed=int(key_seed),
                key_len=int(key_len),
                init3=init3,
                base_seed=int(base_seed),
                ct_idx=np.asarray(ct_idx, dtype=np.uint8),
                pt_idx=np.asarray(pt_idx, dtype=np.uint8),
                full_cipher=full_cipher,
                direction=direction,
                phaseA_cfg=dict(phaseA_cfg),
                scorer_stage3_phaseA=dict(scorer_stage3_phaseA),
                scorer_stage3_phaseA_runtime=scorer_stage3_phaseA_runtime,
                stage3_phaseA_hb_state=stage3_phaseA_hb_state,
            )
            phaseA_rows = list(phasea_restarts.get("phaseA_rows", []))
            phase_stage_rows = [dict(stage_row) for stage_row in phasea_restarts.get("stage_rows", [])]
            stage3_solve_hits += int(phasea_restarts.get("stage3_solve_hits_delta", 0))
            dt3 += float(phasea_restarts.get("dt3_delta", 0.0))
            ev3 += int(phasea_restarts.get("ev3_delta", 0))
            stage3_span_phaseA_eval_total += float(phasea_restarts.get("span_phaseA_eval_total", 0.0))
            stage3_span_phaseA_eval_active += float(phasea_restarts.get("span_phaseA_eval_active", 0.0))
            stage3_span_phaseA_eval_skipped += float(phasea_restarts.get("span_phaseA_eval_skipped", 0.0))
            stage3_span_phaseA_seconds_total += float(phasea_restarts.get("span_phaseA_seconds_total", 0.0))
            stage3_span_phaseA_seconds_active += float(phasea_restarts.get("span_phaseA_seconds_active", 0.0))
            two_phase_followup = run_stage3_two_phase_followup_call(
                ctx=stage3_runtime_call_ctx,
                tier_name=str(tier.name),
                tier_period=int(tier.period),
                tier_columns=int(tier.columns),
                text_id=int(text_id),
                key_seed=int(key_seed),
                key_len=int(key_len),
                ct_idx=np.asarray(ct_idx, dtype=np.uint8),
                pt_idx=np.asarray(pt_idx, dtype=np.uint8),
                direction=direction,
                oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
                stage3_phaseA_experiment=str(stage3_phaseA_experiment),
                stage3_phaseB_experiment=str(stage3_phaseB_experiment),
                stage3_phaseB_char_pct_min_dynamic=float(stage3_phaseB_char_pct_min_dynamic),
                stage3_phaseB_char_pct_min_source=str(stage3_phaseB_char_pct_min_source),
                phaseA_rows=phaseA_rows,
                stage_rows=phase_stage_rows,
                scorer_stage3_search_runtime=scorer_stage3_search_runtime,
                scorer_basin_judge_runtime=scorer_basin_judge_runtime,
                scorer_full_runtime=scorer_full_runtime,
                scorer_stage3_phaseB=dict(scorer_stage3_phaseB),
                solver_stage3_cfg=dict(solver_stage3_cfg),
                stage3_phaseB_cfg=dict(stage3_phaseB_cfg),
                stage3_phaseB_top_n=int(stage3_phaseB_top_n),
                stage3_phaseB_gate_delta=float(stage3_phaseB_gate_delta),
                stage3_phaseB_gate_end_gain=float(stage3_phaseB_gate_end_gain),
                stage3_scan_phaseA_only=bool(stage3_scan_phaseA_only),
                stage3_span_basin_judge_k_cfg=int(stage3_span_basin_judge_k_cfg),
                base_seed=int(base_seed),
                ev3_base=int(ev3),
                stage3_hb_state=stage3_hb_state,
                stage3_topk_payload=stage3_topk_payload,
                full_cipher=full_cipher,
            )
            for stage_row in two_phase_followup.get("stage_rows", []):
                stages.append(dict(stage_row))
            dt3 += float(two_phase_followup.get("dt3_delta", 0.0))
            ev3 += int(two_phase_followup.get("ev3_delta", 0))
            stage3_solve_hits += int(two_phase_followup.get("stage3_solve_hits_delta", 0))
            stage3_span_full_eval_total += float(two_phase_followup.get("stage3_span_full_eval_total", 0.0))
            stage3_span_full_eval_active += float(two_phase_followup.get("stage3_span_full_eval_active", 0.0))
            stage3_span_full_eval_skipped += float(two_phase_followup.get("stage3_span_full_eval_skipped", 0.0))
            stage3_span_full_seconds_total += float(two_phase_followup.get("stage3_span_full_seconds_total", 0.0))
            stage3_span_full_seconds_active += float(two_phase_followup.get("stage3_span_full_seconds_active", 0.0))
            phaseB_ran = int(two_phase_followup.get("phaseB_ran", phaseB_ran))
            phaseB_skipped = int(two_phase_followup.get("phaseB_skipped", phaseB_skipped))
            phaseB_skip_reason = str(two_phase_followup.get("phaseB_skip_reason", phaseB_skip_reason))
            phaseB_top_n_used = int(two_phase_followup.get("phaseB_top_n_used", phaseB_top_n_used))
            stage3_span_basin_judge_k_used = int(
                two_phase_followup.get("stage3_span_basin_judge_k_used", stage3_span_basin_judge_k_used)
            )
            stage3_span_basin_judge_seconds = float(
                two_phase_followup.get("stage3_span_basin_judge_seconds", stage3_span_basin_judge_seconds)
            )
            stage3_basin_judge_span_calls_total = int(
                two_phase_followup.get("stage3_basin_judge_span_calls_total", stage3_basin_judge_span_calls_total)
            )
            stage3_basin_judge_span_calls_active = int(
                two_phase_followup.get("stage3_basin_judge_span_calls_active", stage3_basin_judge_span_calls_active)
            )
            stage3_basin_judge_span_calls_rejected_or_gated = int(
                two_phase_followup.get(
                    "stage3_basin_judge_span_calls_rejected_or_gated",
                    stage3_basin_judge_span_calls_rejected_or_gated,
                )
            )
            stage3_basin_judge_span_seconds_total = float(
                two_phase_followup.get("stage3_basin_judge_span_seconds_total", stage3_basin_judge_span_seconds_total)
            )
            stage3_basin_judge_unique_end_hash = int(
                two_phase_followup.get("stage3_basin_judge_unique_end_hash", stage3_basin_judge_unique_end_hash)
            )
            best3_score = float(two_phase_followup.get("best3_score", best3_score))
            best3_match = float(two_phase_followup.get("best3_match", best3_match))
            best3_key = two_phase_followup.get("best3_key", best3_key)
            pt3 = np.asarray(two_phase_followup.get("pt3", pt3), dtype=np.uint8).reshape(-1)
            stop_reason_update = str(two_phase_followup.get("stop_reason_update", "")).strip()
            if stop_reason_update:
                stop_reason = str(stop_reason_update)

        if pt3.size > 0:
            print_stage_preview_fn(
                label="stage3_full_refine",
                pt=pt3.tolist(),
                wli=wli,
                match_ratio=float(best3_match),
            )
        if np.isfinite(best3_match) and best3_match >= solve_match_threshold:
            stop_reason = "solved_stage3"
        elif (best3_match - best2_match) <= stall_delta:
            stop_reason = "stalled_no_improve" if int(stall_stage_limit) <= 1 else "unsolved"
        else:
            stop_reason = "unsolved"
    elif stage3_policy_branch != "continue":
        pass
    else:
        stop_reason = "no_stage2_candidate"

    stage3_span_summary = summarize_stage3_span_fn(
        tier_name=str(tier.name),
        text_id=int(text_id),
        key_seed=int(key_seed),
        span_phaseA_eval_total=float(stage3_span_phaseA_eval_total),
        span_phaseA_eval_active=float(stage3_span_phaseA_eval_active),
        span_phaseA_eval_skipped=float(stage3_span_phaseA_eval_skipped),
        span_phaseA_seconds_total=float(stage3_span_phaseA_seconds_total),
        span_phaseA_seconds_active=float(stage3_span_phaseA_seconds_active),
        span_full_eval_total=float(stage3_span_full_eval_total),
        span_full_eval_active=float(stage3_span_full_eval_active),
        span_full_eval_skipped=float(stage3_span_full_eval_skipped),
        span_full_seconds_total=float(stage3_span_full_seconds_total),
        span_full_seconds_active=float(stage3_span_full_seconds_active),
        span_basin_judge_k_used=int(stage3_span_basin_judge_k_used),
        span_basin_judge_seconds=float(stage3_span_basin_judge_seconds),
        basin_judge_span_calls_total=int(stage3_basin_judge_span_calls_total),
        basin_judge_span_calls_active=int(stage3_basin_judge_span_calls_active),
        basin_judge_span_calls_rejected_or_gated=int(stage3_basin_judge_span_calls_rejected_or_gated),
        log_prefix=str(log_prefix),
    )
    stage3_span_eval_total = float(stage3_span_summary["span_eval_total"])
    stage3_span_eval_active = float(stage3_span_summary["span_eval_active"])
    stage3_span_eval_skipped = float(stage3_span_summary["span_eval_skipped"])
    stage3_span_seconds_total = float(stage3_span_summary["span_seconds_total"])
    stage3_span_seconds_active = float(stage3_span_summary["span_seconds_active"])
    stage3_span_active_rate = float(stage3_span_summary["span_active_rate"])
    stage3_span_active_rate_source = str(stage3_span_summary["span_active_rate_source"])

    return dict(
        stop_reason=str(stop_reason),
        ev3=int(ev3),
        best3_match=float(best3_match),
        best3_score=float(best3_score),
        best3_key=best3_key,
        pt3=np.asarray(pt3, dtype=np.uint8).reshape(-1),
        stage2_gap_to_oracle=float(stage2_gap_to_oracle),
        stage3_band_name=str(stage3_band_name),
        stage3_topk_payload=stage3_topk_payload,
        stage3_init_target=int(stage3_init_target),
        stage3_init_actual=int(stage3_init_actual),
        stage3_promoted_keys_count=int(stage3_promoted_keys_count),
        stage3_gate_source=str(stage3_gate_source),
        stage3_phaseB_top_n_cfg=int(stage3_phaseB_top_n_cfg),
        stage3_phaseB_gate_delta_cfg=float(stage3_phaseB_gate_delta_cfg),
        stage3_phaseB_gate_end_gain_cfg=float(stage3_phaseB_gate_end_gain_cfg),
        stage3_solve_hits=int(stage3_solve_hits),
        stage3_period_init_mult=float(stage3_period_init_mult),
        stage3_period_step_mult=float(stage3_period_step_mult),
        stage3_period_restart_bonus=int(stage3_period_restart_bonus),
        stage3_scan_phaseA_only=bool(stage3_scan_phaseA_only),
        stage3_span_active_rate=float(stage3_span_active_rate),
        stage3_span_active_rate_source=str(stage3_span_active_rate_source),
        stage3_span_eval_total=float(stage3_span_eval_total),
        stage3_span_eval_active=float(stage3_span_eval_active),
        stage3_span_eval_skipped=float(stage3_span_eval_skipped),
        stage3_span_seconds_total=float(stage3_span_seconds_total),
        stage3_span_seconds_active=float(stage3_span_seconds_active),
        stage3_span_phaseA_eval_total=float(stage3_span_phaseA_eval_total),
        stage3_span_phaseA_eval_active=float(stage3_span_phaseA_eval_active),
        stage3_span_phaseA_eval_skipped=float(stage3_span_phaseA_eval_skipped),
        stage3_span_phaseA_seconds_total=float(stage3_span_phaseA_seconds_total),
        stage3_span_phaseA_seconds_active=float(stage3_span_phaseA_seconds_active),
        stage3_span_full_eval_total=float(stage3_span_full_eval_total),
        stage3_span_full_eval_active=float(stage3_span_full_eval_active),
        stage3_span_full_eval_skipped=float(stage3_span_full_eval_skipped),
        stage3_span_full_seconds_total=float(stage3_span_full_seconds_total),
        stage3_span_full_seconds_active=float(stage3_span_full_seconds_active),
        stage3_span_basin_judge_k_cfg=int(stage3_span_basin_judge_k_cfg),
        stage3_span_basin_judge_k_used=int(stage3_span_basin_judge_k_used),
        stage3_span_basin_judge_seconds=float(stage3_span_basin_judge_seconds),
        stage3_basin_judge_span_calls_total=int(stage3_basin_judge_span_calls_total),
        stage3_basin_judge_span_calls_active=int(stage3_basin_judge_span_calls_active),
        stage3_basin_judge_span_calls_rejected_or_gated=int(stage3_basin_judge_span_calls_rejected_or_gated),
        stage3_basin_judge_span_seconds_total=float(stage3_basin_judge_span_seconds_total),
        stage3_basin_judge_unique_end_hash=int(stage3_basin_judge_unique_end_hash),
        phaseB_ran=int(phaseB_ran),
        phaseB_skipped=int(phaseB_skipped),
        phaseB_top_n_used=int(phaseB_top_n_used),
        phaseB_skip_reason=str(phaseB_skip_reason),
    )
