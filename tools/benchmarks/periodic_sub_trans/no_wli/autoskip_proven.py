from __future__ import annotations

from typing import Any, Callable, Dict, List

import numpy as np


def handle_autoskip_proven_iteration(
    *,
    tier: Any,
    text_id: int,
    key_seed: int,
    off: int,
    offset_used: int,
    source_row: Dict[str, Any],
    stage3_continue_after_solve: bool,
    stage3_phaseb_top_n: int,
    stage3_phaseb_gate_delta_floor: float,
    stage3_phaseb_gate_end_gain_floor: float,
    stage3_c1_focus_enabled: bool,
    oracle_mode: str,
    oracle_consulted_in_decisions: bool,
    build_iteration_payloads_fn: Callable[..., Any],
    derive_outcome_code_fn: Callable[..., str],
    commit_iteration_with_checkpoint_fn: Callable[..., None],
    instances: List[Dict[str, Any]],
    stages: List[Dict[str, Any]],
    log_prefix: str = "[pipeline_no_wli]",
) -> None:
    src = dict(source_row)
    src_run = str(src.get("run_id", "") or "")
    src_ts = str(src.get("timestamp_utc", "") or "")
    src_match = float(src.get("best_match_ratio", float("nan")))
    src_stage = str(src.get("best_stage", "") or "proven_history")
    stop_reason = (
        f"autoskip_proven:source_run={src_run}" if src_run else "autoskip_proven"
    )
    outcome_code = derive_outcome_code_fn(
        status="skipped_proven", stop_reason=stop_reason
    )
    preview_txt = (
        f"[autoskip] source_run={src_run}" if src_run else "[autoskip] proven history"
    )
    stages.append(
        dict(
            tier=tier.name,
            text_id=int(text_id),
            key_seed=int(key_seed),
            stage="skip_proven",
            score=np.nan,
            match_ratio=float(src_match if np.isfinite(src_match) else np.nan),
            seconds=0.0,
            evals=0,
            source_run_id=src_run,
            source_timestamp=src_ts,
        )
    )

    stage2_diagnostics = dict(
        archive_entries=0,
        kept_entries=0,
        promoted_entries=0,
        score_match_spearman=float("nan"),
    )
    stage3_diagnostics = dict(
        init_target=0,
        init_actual=0,
        promoted_keys=0,
        gate_source="autoskip",
        continue_after_solve=bool(stage3_continue_after_solve),
        solve_hits=0,
        period_init_mult=1.0,
        period_step_mult=1.0,
        period_restart_bonus=0,
        phaseB_top_n_cfg=int(stage3_phaseb_top_n),
        phaseB_gate_delta_cfg=float(stage3_phaseb_gate_delta_floor),
        phaseB_gate_end_gain_cfg=float(stage3_phaseb_gate_end_gain_floor),
        phaseB_ran=0,
        phaseB_skipped=1,
        phaseB_top_n_used=0,
        phaseB_skip_reason="autoskip_proven",
        stage3_eval_count=0,
        c1_focus=int(
            1 if (int(tier.columns) <= 1 and bool(stage3_c1_focus_enabled)) else 0
        ),
    )
    inst_row, artifact_payload = build_iteration_payloads_fn(
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        off=int(off),
        offset_used=int(offset_used),
        status="skipped_proven",
        stop_reason=str(stop_reason),
        best_stage=str(src_stage),
        best_match=float(src_match if np.isfinite(src_match) else np.nan),
        sub_key_match=float("nan"),
        best2_match=float("nan"),
        best3_match=float("nan"),
        stage2_gap_to_oracle=float("nan"),
        stage3_band_name="autoskip",
        stage3_basin_judge_span_calls_total=0,
        stage3_basin_judge_span_calls_active=0,
        stage3_basin_judge_span_calls_rejected_or_gated=0,
        stage3_basin_judge_span_seconds_total=0.0,
        stage3_basin_judge_unique_end_hash=0,
        oracle_mode=str(oracle_mode),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        dt_i=0.0,
        total_evals=0,
        preview_best=str(preview_txt),
        outcome_code=str(outcome_code),
        final_best_score=float("nan"),
        oracle_scores=dict(
            stage1=float("nan"), stage2=float("nan"), stage3=float("nan")
        ),
        score_minus_oracle=dict(
            stage1=float("nan"), stage2=float("nan"), stage3=float("nan")
        ),
        ct_idx=np.asarray([], dtype=np.uint8),
        pt_idx=np.asarray([], dtype=np.uint8),
        final_best_key_idx=[],
        final_best_plaintext_idx=[],
        stage2_topk_payload=[],
        stage2_topk_has_best_match=False,
        stage2_diagnostics=stage2_diagnostics,
        stage3_topk_payload=[],
        stage3_diagnostics=stage3_diagnostics,
    )
    instances.append(dict(inst_row))
    print(
        f"{log_prefix} skip-proven tier={tier.name} text={text_id} key_seed={key_seed} "
        f"source_run={src_run if src_run else 'unknown'} best_match={float(src_match):.3f}",
        flush=True,
    )
    commit_iteration_with_checkpoint_fn(
        inst_row=inst_row,
        artifact_payload=artifact_payload,
        status_key="skipped_proven",
    )
