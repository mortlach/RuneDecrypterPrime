from __future__ import annotations

import time
from typing import Any, Callable, Dict, Sequence

import numpy as np

from rune_decrypter_prime.api import KeySpec, SolverSpec, by_name, run

from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    score_plaintexts_chunked,
)


def run_stage3_single_phase(
    *,
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
    order: str,
    alphabet_size: int,
    batch_eval_chunk_size: int,
    require_batch_scoring: bool,
    solve_match_threshold: float,
    stage3_heartbeat_seconds: float,
    stage3_heartbeat_min_step: int,
    stage3_heartbeat_min_elapsed_seconds: float,
    ev3_base: int,
    stage3_hb_state: Dict[str, Any],
    extract_kaeding_metrics_fn: Callable[[Any], Dict[str, float]],
    solution_span_counter_summary_fn: Callable[[Any], Dict[str, float]],
    stage3_progress_logging_fn: Callable[..., Dict[str, Any]],
    match_ratio_fn: Callable[[Sequence[int], Sequence[int]], float],
) -> Dict[str, Any]:
    t_run = time.time()
    stage3_logging_cfg = stage3_progress_logging_fn(
        tier_name=str(tier_name),
        text_id=int(text_id),
        key_seed=int(key_seed),
        phase="full",
        phase_steps=int(solver_stage3_cfg.get("steps", 0) or 0),
        phase_start_ts=float(t_run),
        heartbeat_seconds=float(stage3_heartbeat_seconds),
        heartbeat_state=stage3_hb_state,
        min_step=int(stage3_heartbeat_min_step),
        min_elapsed_seconds=float(stage3_heartbeat_min_elapsed_seconds),
        evals_base=int(ev3_base),
    )
    sol3 = run(
        text=np.asarray(ct_idx, dtype=np.uint8).tolist(),
        cipher=by_name.cipher(
            "periodic_columnar",
            period=int(tier_period),
            columns=int(tier_columns),
            order=str(order),
            alphabet_size=int(alphabet_size),
        ),
        key=KeySpec.periodic_columnar(
            period=int(tier_period),
            columns=int(tier_columns),
            alphabet_size=int(alphabet_size),
        ),
        solver=SolverSpec.kaeding(**dict(solver_stage3_cfg)),
        scorer_params=dict(scorer_stage3_phaseB),
        logging=stage3_logging_cfg,
        wli_data=[],
        encoding_dir=direction,
        telemetry_on=True,
        force_no_wli=True,
        initial_keys=[list(map(int, k)) for k in init3],
    )
    dt3 = float(time.time() - t_run)
    ev3 = int((getattr(sol3, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)

    pt3 = np.asarray(getattr(sol3, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
    k3_arr = np.asarray(getattr(sol3, "key", []) or [], dtype=np.int16).reshape(-1)
    best3_key: list[int] | None = None
    if int(k3_arr.size) == int(key_len):
        best3_key = k3_arr.astype(int).tolist()

    best3_match = float(
        match_ratio_fn(
            np.asarray(pt3, dtype=np.uint8).astype(int).tolist(),
            np.asarray(pt_idx, dtype=np.uint8).astype(int).tolist(),
        )
    )
    best3_score = float(getattr(sol3, "score", float("nan")))
    if int(pt3.size) > 0:
        judge_arr, _judge_stats = score_plaintexts_chunked(
            scorer=scorer_full_runtime,
            plaintexts=[np.asarray(pt3, dtype=np.uint8)],
            wli=None,
            chunk_size=int(batch_eval_chunk_size),
            require_batch=bool(require_batch_scoring),
        )
        if int(judge_arr.size) > 0:
            best3_score = float(judge_arr[0])

    stage3_solve_hit = bool(
        np.isfinite(float(best3_match))
        and float(best3_match) >= float(solve_match_threshold)
    )
    tele3 = (getattr(sol3, "meta", {}) or {}).get("telemetry", {})
    kaeding3 = tele3.get("kaeding", {}) if isinstance(tele3, dict) else {}
    mm = extract_kaeding_metrics_fn(kaeding3)
    span3 = solution_span_counter_summary_fn(sol3)

    return dict(
        dt3=float(dt3),
        ev3=int(ev3),
        pt3=np.asarray(pt3, dtype=np.uint8),
        best3_key=best3_key,
        best3_match=float(best3_match),
        best3_score=float(best3_score),
        stage3_solve_hit=bool(stage3_solve_hit),
        kaeding3=kaeding3,
        slip_count=int(mm["slip_count"]),
        slip_accept_count=int(mm["slip_accept_count"]),
        slip_accept_rate=float(mm["slip_accept_rate"]),
        accept_rate=float(mm["accept_rate"]),
        phase_attempts_total=int(mm["phase_attempts_total"]),
        phase_improves_total=int(mm["phase_improves_total"]),
        phase_best_delta_max=float(mm["phase_best_delta_max"]),
        span_total=float(span3["total"]),
        span_active=float(span3["active"]),
        span_skipped=float(span3["skipped"]),
        span_seconds_total=float(span3["seconds_total"]),
        span_seconds_active=float(span3["seconds_active"]),
    )
