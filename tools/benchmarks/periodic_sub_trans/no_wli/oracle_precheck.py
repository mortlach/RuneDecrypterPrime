from __future__ import annotations

from typing import Any, Callable, Dict, Mapping

import numpy as np


def evaluate_oracle_precheck(
    *,
    tier_name: str,
    text_id: int,
    key_seed: int,
    pt_stage1_oracle: np.ndarray,
    pt_idx: np.ndarray,
    cfg_sub: Any,
    cfg_full: Any,
    scorer_stage1: Mapping[str, Any],
    scorer_stage2: Mapping[str, Any],
    scorer_full: Mapping[str, Any],
    stage1_label: str,
    stage2_label: str,
    stage3_label: str,
    stage2_judge_policy: str,
    stage2_judge_objective_summary: str,
    stage3_phase_switch_enabled: bool,
    stage3_phaseA_experiment: str,
    stage3_phaseB_experiment: str,
    scoring_experiment_c_char_pct_min: float,
    stage3_span_char_pct_min_override: float | None,
    oracle_decision_paths_enabled: bool,
    oracle_stage3_floor_guard_eps: float,
    oracle_score_for_stage_fn: Callable[..., tuple[float, float, str]],
    weights_text_fn: Callable[[dict[int, float]], str],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    oracle_s1, oracle_s1_raw, s1_obj = oracle_score_for_stage_fn(
        pt_idx=np.asarray(pt_stage1_oracle, dtype=np.uint8),
        cipher_cfg=cfg_sub,
        scorer_params=dict(scorer_stage1),
    )
    oracle_s2, oracle_s2_raw, s2_obj = oracle_score_for_stage_fn(
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        cipher_cfg=cfg_full,
        scorer_params=dict(scorer_stage2),
    )
    oracle_s3, oracle_s3_raw, s3_obj = oracle_score_for_stage_fn(
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        cipher_cfg=cfg_full,
        scorer_params=dict(scorer_full),
    )

    print(
        f"{log_prefix} objective tier={tier_name} text={int(text_id)} key_seed={int(key_seed)} "
        f"stage1={str(stage1_label)} stage2={str(stage2_label)} stage3={str(stage3_label)}",
        flush=True,
    )
    print(
        f"{log_prefix} oracle-score "
        f"stage=stage1_sub model={s1_obj} "
        f"(char={weights_text_fn(dict(scorer_stage1.get('char_weights', {})))},wli={{}},wb=0) "
        f"score={float(oracle_s1):.6f} raw={float(oracle_s1_raw):.6f}",
        flush=True,
    )
    print(
        f"{log_prefix} oracle-score "
        f"stage=stage2_search model={s2_obj} "
        f"(char={weights_text_fn(dict(scorer_stage2.get('char_weights', {})))},wli={{}},wb=0) "
        f"score={float(oracle_s2):.6f} raw={float(oracle_s2_raw):.6f}",
        flush=True,
    )
    print(
        f"{log_prefix} oracle-score "
        f"stage=stage3_refine model={s3_obj} "
        f"(char={weights_text_fn(dict(scorer_full.get('char_weights', {})))},wli={{}},wb=0) "
        f"score={float(oracle_s3):.6f} raw={float(oracle_s3_raw):.6f}",
        flush=True,
    )
    print(
        f"{log_prefix} stage2-judge-policy tier={tier_name} text={int(text_id)} key_seed={int(key_seed)} "
        f"policy={str(stage2_judge_policy)} objective={str(stage2_judge_objective_summary)}",
        flush=True,
    )

    stage3_phaseB_char_pct_min_dynamic = float("nan")
    stage3_phaseB_char_pct_min_source = "not_used_explicit_basin_judge"
    if bool(stage3_phase_switch_enabled) and str(stage3_phaseB_experiment) == "c_min_late":
        if np.isfinite(float(oracle_s3)):
            stage3_phaseB_char_pct_min_dynamic = float(
                np.clip(float(oracle_s3) - 0.10, 0.30, 0.45)
            )
            stage3_phaseB_char_pct_min_source = "oracle_minus_0.10_clamp_0.30_0.45_not_applied"
        else:
            stage3_phaseB_char_pct_min_dynamic = float(scoring_experiment_c_char_pct_min)
            stage3_phaseB_char_pct_min_source = "profile_default_not_applied"
        if stage3_span_char_pct_min_override is not None:
            stage3_phaseB_char_pct_min_dynamic = float(stage3_span_char_pct_min_override)
            stage3_phaseB_char_pct_min_source = "diagnostic_override_not_applied"
        print(
            f"{log_prefix} stage3-phase-switch tier={tier_name} text={int(text_id)} key_seed={int(key_seed)} "
            f"phaseA_experiment={str(stage3_phaseA_experiment)} "
            f"phaseB_experiment={str(stage3_phaseB_experiment)} "
            f"phaseB_char_pct_min={float(stage3_phaseB_char_pct_min_dynamic):.6f} "
            f"source={stage3_phaseB_char_pct_min_source} "
            "applied_to_basin_judge=0",
            flush=True,
        )

    stage3_objective_txt = str(scorer_full.get("objective", "") or "").strip().lower()
    stage3_floor_guard_enabled = stage3_objective_txt.startswith("pct.") or stage3_objective_txt.startswith("energy.")
    stage3_floor_threshold = float(
        scorer_full.get(
            "span_hamming_ecdf_clamp_min",
            scorer_full.get("ecdf_clamp_min", 1e-6),
        )
    )
    floor_guard_triggered = bool(
        bool(oracle_decision_paths_enabled)
        and bool(stage3_floor_guard_enabled)
        and np.isfinite(float(stage3_floor_threshold))
        and np.isfinite(float(oracle_s3))
        and (float(oracle_s3) <= float(stage3_floor_threshold) + float(oracle_stage3_floor_guard_eps))
    )
    floor_guard_stop_reason = ""
    if floor_guard_triggered:
        floor_guard_stop_reason = (
            "oracle_floor_guard:"
            f"stage3_score={float(oracle_s3):.6f}:floor={float(stage3_floor_threshold):.6f}"
        )
        print(
            f"{log_prefix} oracle-floor-guard tier={tier_name} text={int(text_id)} key_seed={int(key_seed)} "
            f"stage3_oracle={float(oracle_s3):.6f} floor={float(stage3_floor_threshold):.6f} "
            "action=abort_tier",
            flush=True,
        )

    return dict(
        oracle_s1=float(oracle_s1),
        oracle_s2=float(oracle_s2),
        oracle_s3=float(oracle_s3),
        oracle_s1_raw=float(oracle_s1_raw),
        oracle_s2_raw=float(oracle_s2_raw),
        oracle_s3_raw=float(oracle_s3_raw),
        s1_obj=str(s1_obj),
        s2_obj=str(s2_obj),
        s3_obj=str(s3_obj),
        stage3_phaseB_char_pct_min_dynamic=float(stage3_phaseB_char_pct_min_dynamic),
        stage3_phaseB_char_pct_min_source=str(stage3_phaseB_char_pct_min_source),
        stage3_floor_guard_enabled=bool(stage3_floor_guard_enabled),
        stage3_floor_threshold=float(stage3_floor_threshold),
        floor_guard_triggered=bool(floor_guard_triggered),
        floor_guard_stop_reason=str(floor_guard_stop_reason),
    )
