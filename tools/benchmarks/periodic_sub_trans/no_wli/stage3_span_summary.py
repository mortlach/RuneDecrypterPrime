from __future__ import annotations

from typing import Any, Dict


def summarize_stage3_span(
    *,
    tier_name: str,
    text_id: int,
    key_seed: int,
    span_phaseA_eval_total: float,
    span_phaseA_eval_active: float,
    span_phaseA_eval_skipped: float,
    span_phaseA_seconds_total: float,
    span_phaseA_seconds_active: float,
    span_full_eval_total: float,
    span_full_eval_active: float,
    span_full_eval_skipped: float,
    span_full_seconds_total: float,
    span_full_seconds_active: float,
    span_basin_judge_k_used: int,
    span_basin_judge_seconds: float,
    basin_judge_span_calls_total: int,
    basin_judge_span_calls_active: int,
    basin_judge_span_calls_rejected_or_gated: int,
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    span_eval_total = float(span_phaseA_eval_total + span_full_eval_total)
    span_eval_active = float(span_phaseA_eval_active + span_full_eval_active)
    span_eval_skipped = float(span_phaseA_eval_skipped + span_full_eval_skipped)
    span_seconds_total = float(span_phaseA_seconds_total + span_full_seconds_total)
    span_seconds_active = float(span_phaseA_seconds_active + span_full_seconds_active)
    if span_eval_total > 0.0:
        span_active_rate = float(span_eval_active / span_eval_total)
        span_active_rate_source = "solver_run_telemetry"
    else:
        span_active_rate = 0.0
        span_active_rate_source = "solver_run_telemetry_zero_total"
    print(
        f"{log_prefix} stage3-span tier={tier_name} text={text_id} key_seed={key_seed} "
        f"active={int(round(span_eval_active))}/{int(round(span_eval_total))} "
        f"skipped={int(round(span_eval_skipped))} "
        f"active_rate={float(span_active_rate):.3f} "
        f"span_seconds={float(span_seconds_total):.3f} "
        f"phaseA_calls={int(round(span_phaseA_eval_total))} "
        f"full_calls={int(round(span_full_eval_total))} "
        f"phaseA_basins_judged_by_span={int(span_basin_judge_k_used)} "
        f"span_judge_time_s={float(span_basin_judge_seconds):.3f} "
        f"basin_judge_span_calls_total={int(basin_judge_span_calls_total)} "
        f"basin_judge_span_calls_active={int(basin_judge_span_calls_active)} "
        f"basin_judge_span_calls_rejected_or_gated={int(basin_judge_span_calls_rejected_or_gated)}",
        flush=True,
    )
    return dict(
        span_eval_total=float(span_eval_total),
        span_eval_active=float(span_eval_active),
        span_eval_skipped=float(span_eval_skipped),
        span_seconds_total=float(span_seconds_total),
        span_seconds_active=float(span_seconds_active),
        span_active_rate=float(span_active_rate),
        span_active_rate_source=str(span_active_rate_source),
    )
