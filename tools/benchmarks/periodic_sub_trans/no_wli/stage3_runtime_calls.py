from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.stage3_phasea_restarts import (
    run_stage3_phasea_restarts as run_stage3_phasea_restarts_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_single_phase import (
    run_stage3_single_phase as run_stage3_single_phase_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_two_phase import (
    run_stage3_two_phase_followup as run_stage3_two_phase_followup_external,
)


@dataclass(frozen=True)
class Stage3RuntimeCallContext:
    order: str
    alphabet_size: int
    batch_eval_chunk_size: int
    require_batch_scoring: bool
    solve_match_threshold: float
    stage3_continue_after_solve: bool
    stage3_heartbeat_seconds: float
    stage3_heartbeat_min_step: int
    stage3_heartbeat_min_elapsed_seconds: float
    stage3_span_basin_judge_require_span_active: bool
    stage3_span_basin_judge_dedupe_by_end_hash: bool
    stage3_span_basin_judge_tie_eps: float
    stage3_span_basin_judge_tie_max_seeds: int
    stage3_word_ngram_decision_influence: bool
    stage3_phasec_enabled: bool
    stage3_phasec_cfg: Dict[str, Any]
    stage3_phasec_start_keys: int
    stage3_phasec_seed_offset: int
    stage3_phasec_word_ngram_tiebreak: bool
    extract_kaeding_metrics_fn: Callable[[Any], Dict[str, float]]
    solution_span_counter_summary_fn: Callable[[Any], Dict[str, float]]
    stage3_progress_logging_fn: Callable[..., Dict[str, Any]]
    match_ratio_fn: Callable[[Sequence[int], Sequence[int]], float]
    key_hash_fn: Callable[..., str]
    append_stage3_topk_from_phasea_fn: Callable[..., None]
    append_stage3_topk_from_kaeding_fn: Callable[..., None]
    is_better_stage3_candidate_preserving_solve_fn: Callable[..., bool]
    scorer_span_counter_summary_fn: Callable[[Any], Dict[str, float]]
    span_counter_delta_fn: Callable[..., Dict[str, float]]
    fmt_finite_float_fn: Callable[..., str]
    phasec_start_checkpoint_path: Path | None = None
    append_jsonl_row_fn: Callable[[Path, Dict[str, Any]], None] | None = None
    log_prefix: str = "[pipeline_no_wli]"


def run_stage3_single_phase_call(
    *,
    ctx: Stage3RuntimeCallContext,
    tier_name: str,
    tier_period: int,
    tier_columns: int,
    text_id: int,
    key_seed: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    key_len: int,
    init3: Sequence[Sequence[int]],
    solver_stage3_cfg: Dict[str, Any],
    scorer_stage3_phaseB: Dict[str, Any],
    scorer_full_runtime: Any,
    direction: Any,
    ev3_base: int,
    stage3_hb_state: Dict[str, Any],
) -> Dict[str, Any]:
    return run_stage3_single_phase_external(
        tier_name=str(tier_name),
        tier_period=int(tier_period),
        tier_columns=int(tier_columns),
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
        order=str(ctx.order),
        alphabet_size=int(ctx.alphabet_size),
        batch_eval_chunk_size=int(ctx.batch_eval_chunk_size),
        require_batch_scoring=bool(ctx.require_batch_scoring),
        solve_match_threshold=float(ctx.solve_match_threshold),
        stage3_heartbeat_seconds=float(ctx.stage3_heartbeat_seconds),
        stage3_heartbeat_min_step=int(ctx.stage3_heartbeat_min_step),
        stage3_heartbeat_min_elapsed_seconds=float(ctx.stage3_heartbeat_min_elapsed_seconds),
        ev3_base=int(ev3_base),
        stage3_hb_state=stage3_hb_state,
        extract_kaeding_metrics_fn=ctx.extract_kaeding_metrics_fn,
        solution_span_counter_summary_fn=ctx.solution_span_counter_summary_fn,
        stage3_progress_logging_fn=ctx.stage3_progress_logging_fn,
        match_ratio_fn=ctx.match_ratio_fn,
    )


def run_stage3_phasea_restarts_call(
    *,
    ctx: Stage3RuntimeCallContext,
    tier_name: str,
    tier_period: int,
    tier_columns: int,
    text_id: int,
    key_seed: int,
    key_len: int,
    init3: Sequence[Sequence[int]],
    base_seed: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    full_cipher: Any,
    direction: Any,
    phaseA_cfg: Dict[str, Any],
    scorer_stage3_phaseA: Dict[str, Any],
    scorer_stage3_phaseA_runtime: Any,
    stage3_phaseA_hb_state: Dict[str, Any],
) -> Dict[str, Any]:
    return run_stage3_phasea_restarts_external(
        tier_name=str(tier_name),
        tier_period=int(tier_period),
        tier_columns=int(tier_columns),
        text_id=int(text_id),
        key_seed=int(key_seed),
        key_len=int(key_len),
        init3=init3,
        base_seed=int(base_seed),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        full_cipher=full_cipher,
        direction=direction,
        order=str(ctx.order),
        alphabet_size=int(ctx.alphabet_size),
        phaseA_cfg=dict(phaseA_cfg),
        scorer_stage3_phaseA=dict(scorer_stage3_phaseA),
        scorer_stage3_phaseA_runtime=scorer_stage3_phaseA_runtime,
        stage3_heartbeat_seconds=float(ctx.stage3_heartbeat_seconds),
        stage3_heartbeat_min_step=int(ctx.stage3_heartbeat_min_step),
        stage3_heartbeat_min_elapsed_seconds=float(ctx.stage3_heartbeat_min_elapsed_seconds),
        stage3_phaseA_hb_state=stage3_phaseA_hb_state,
        solve_match_threshold=float(ctx.solve_match_threshold),
        stage3_continue_after_solve=bool(ctx.stage3_continue_after_solve),
        batch_eval_chunk_size=int(ctx.batch_eval_chunk_size),
        require_batch_scoring=bool(ctx.require_batch_scoring),
        extract_kaeding_metrics_fn=ctx.extract_kaeding_metrics_fn,
        solution_span_counter_summary_fn=ctx.solution_span_counter_summary_fn,
        stage3_progress_logging_fn=ctx.stage3_progress_logging_fn,
        match_ratio_fn=ctx.match_ratio_fn,
        key_hash_fn=ctx.key_hash_fn,
        log_prefix=str(ctx.log_prefix),
    )


def run_stage3_two_phase_followup_call(
    *,
    ctx: Stage3RuntimeCallContext,
    tier_name: str,
    tier_period: int,
    tier_columns: int,
    text_id: int,
    key_seed: int,
    key_len: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    direction: Any,
    oracle_assist_selection_effective: bool,
    stage3_phaseA_experiment: str,
    stage3_phaseB_experiment: str,
    stage3_phaseB_char_pct_min_dynamic: float,
    stage3_phaseB_char_pct_min_source: str,
    phaseA_rows: List[Dict[str, Any]],
    stage_rows: List[Dict[str, Any]],
    scorer_stage3_search_runtime: Any,
    scorer_basin_judge_runtime: Any,
    scorer_word_ngram_report_runtime: Any | None,
    scorer_full_runtime: Any,
    scorer_stage3_phaseB: Dict[str, Any],
    solver_stage3_cfg: Dict[str, Any],
    stage3_phaseB_cfg: Dict[str, Any],
    stage3_phaseB_top_n: int,
    stage3_phaseB_gate_delta: float,
    stage3_phaseB_gate_end_gain: float,
    stage3_scan_phaseA_only: bool,
    stage3_span_basin_judge_k_cfg: int,
    base_seed: int,
    ev3_base: int,
    stage3_hb_state: Dict[str, Any],
    stage3_topk_payload: List[Dict[str, Any]],
    full_cipher: Any,
) -> Dict[str, Any]:
    return run_stage3_two_phase_followup_external(
        tier_name=str(tier_name),
        tier_period=int(tier_period),
        tier_columns=int(tier_columns),
        text_id=int(text_id),
        key_seed=int(key_seed),
        key_len=int(key_len),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        order=str(ctx.order),
        alphabet_size=int(ctx.alphabet_size),
        direction=direction,
        solve_match_threshold=float(ctx.solve_match_threshold),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        stage3_phaseA_experiment=str(stage3_phaseA_experiment),
        stage3_phaseB_experiment=str(stage3_phaseB_experiment),
        stage3_phaseB_char_pct_min_dynamic=float(stage3_phaseB_char_pct_min_dynamic),
        stage3_phaseB_char_pct_min_source=str(stage3_phaseB_char_pct_min_source),
        phaseA_rows=phaseA_rows,
        stage_rows=stage_rows,
        scorer_stage3_search_runtime=scorer_stage3_search_runtime,
        scorer_basin_judge_runtime=scorer_basin_judge_runtime,
        scorer_word_ngram_report_runtime=scorer_word_ngram_report_runtime,
        scorer_full_runtime=scorer_full_runtime,
        scorer_stage3_phaseB=dict(scorer_stage3_phaseB),
        solver_stage3_cfg=dict(solver_stage3_cfg),
        stage3_phaseB_cfg=dict(stage3_phaseB_cfg),
        stage3_phaseB_top_n=int(stage3_phaseB_top_n),
        stage3_phaseB_gate_delta=float(stage3_phaseB_gate_delta),
        stage3_phaseB_gate_end_gain=float(stage3_phaseB_gate_end_gain),
        stage3_scan_phaseA_only=bool(stage3_scan_phaseA_only),
        stage3_span_basin_judge_k_cfg=int(stage3_span_basin_judge_k_cfg),
        stage3_span_basin_judge_require_span_active=bool(
            ctx.stage3_span_basin_judge_require_span_active
        ),
        stage3_span_basin_judge_dedupe_by_end_hash=bool(
            ctx.stage3_span_basin_judge_dedupe_by_end_hash
        ),
        stage3_span_basin_judge_tie_eps=float(ctx.stage3_span_basin_judge_tie_eps),
        stage3_span_basin_judge_tie_max_seeds=int(ctx.stage3_span_basin_judge_tie_max_seeds),
        stage3_word_ngram_decision_influence=bool(
            ctx.stage3_word_ngram_decision_influence
        ),
        stage3_phasec_enabled=bool(ctx.stage3_phasec_enabled),
        stage3_phasec_cfg=dict(ctx.stage3_phasec_cfg),
        stage3_phasec_start_keys=int(ctx.stage3_phasec_start_keys),
        stage3_phasec_seed_offset=int(ctx.stage3_phasec_seed_offset),
        stage3_phasec_word_ngram_tiebreak=bool(ctx.stage3_phasec_word_ngram_tiebreak),
        batch_eval_chunk_size=int(ctx.batch_eval_chunk_size),
        require_batch_scoring=bool(ctx.require_batch_scoring),
        base_seed=int(base_seed),
        ev3_base=int(ev3_base),
        stage3_heartbeat_seconds=float(ctx.stage3_heartbeat_seconds),
        stage3_heartbeat_min_step=int(ctx.stage3_heartbeat_min_step),
        stage3_heartbeat_min_elapsed_seconds=float(ctx.stage3_heartbeat_min_elapsed_seconds),
        stage3_hb_state=stage3_hb_state,
        stage3_topk_payload=stage3_topk_payload,
        full_cipher=full_cipher,
        append_stage3_topk_from_phasea_fn=ctx.append_stage3_topk_from_phasea_fn,
        append_stage3_topk_from_kaeding_fn=ctx.append_stage3_topk_from_kaeding_fn,
        is_better_stage3_candidate_preserving_solve_fn=ctx.is_better_stage3_candidate_preserving_solve_fn,
        match_ratio_fn=ctx.match_ratio_fn,
        extract_kaeding_metrics_fn=ctx.extract_kaeding_metrics_fn,
        solution_span_counter_summary_fn=ctx.solution_span_counter_summary_fn,
        scorer_span_counter_summary_fn=ctx.scorer_span_counter_summary_fn,
        span_counter_delta_fn=ctx.span_counter_delta_fn,
        stage3_progress_logging_fn=ctx.stage3_progress_logging_fn,
        fmt_finite_float_fn=ctx.fmt_finite_float_fn,
        phasec_start_checkpoint_path=ctx.phasec_start_checkpoint_path,
        append_jsonl_row_fn=ctx.append_jsonl_row_fn,
        key_hash_fn=ctx.key_hash_fn,
        log_prefix=str(ctx.log_prefix),
    )
