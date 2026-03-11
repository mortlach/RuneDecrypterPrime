from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.api import KeySpec, SolverSpec, by_name, run

from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    score_plaintexts_chunked,
)


def run_stage3_two_phase_followup(
    *,
    tier_name: str,
    tier_period: int,
    tier_columns: int,
    text_id: int,
    key_seed: int,
    key_len: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    order: str,
    alphabet_size: int,
    direction: Any,
    solve_match_threshold: float,
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
    stage3_span_basin_judge_require_span_active: bool,
    stage3_span_basin_judge_dedupe_by_end_hash: bool,
    stage3_span_basin_judge_tie_eps: float,
    stage3_span_basin_judge_tie_max_seeds: int,
    stage3_word_ngram_decision_influence: bool,
    batch_eval_chunk_size: int,
    require_batch_scoring: bool,
    base_seed: int,
    ev3_base: int,
    stage3_heartbeat_seconds: float,
    stage3_heartbeat_min_step: int,
    stage3_heartbeat_min_elapsed_seconds: float,
    stage3_hb_state: Dict[str, Any],
    stage3_topk_payload: List[Dict[str, Any]],
    full_cipher: Any,
    append_stage3_topk_from_phasea_fn: Callable[..., None],
    append_stage3_topk_from_kaeding_fn: Callable[..., None],
    is_better_stage3_candidate_preserving_solve_fn: Callable[..., bool],
    match_ratio_fn: Callable[[Sequence[int], Sequence[int]], float],
    extract_kaeding_metrics_fn: Callable[[Any], Dict[str, float]],
    solution_span_counter_summary_fn: Callable[[Any], Dict[str, float]],
    scorer_span_counter_summary_fn: Callable[[Any], Dict[str, float]],
    span_counter_delta_fn: Callable[..., Dict[str, float]],
    stage3_progress_logging_fn: Callable[..., Dict[str, Any]],
    fmt_finite_float_fn: Callable[..., str],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    best3_match = float("nan")
    best3_score = float("nan")
    pt3 = np.asarray([], dtype=np.uint8)
    best3_key: List[int] | None = None
    stop_reason_update = ""

    dt3_delta = 0.0
    ev3_delta = 0
    stage3_solve_hits_delta = 0

    slip_count = 0
    slip_accept_count = 0
    slip_accept_rate = float("nan")
    accept_rate = float("nan")
    phase_attempts_total = 0
    phase_improves_total = 0
    phase_best_delta_max = float("nan")

    phaseA_best_delta = float("nan")
    phaseA_best_start_score = float("nan")
    phaseA_best_end_score = float("nan")
    phaseA_solved = False
    phaseB_top_n_used = 0
    phaseB_skipped = 0
    phaseB_ran = 0
    phaseB_skip_reason = ""

    stage3_span_full_eval_total = 0.0
    stage3_span_full_eval_active = 0.0
    stage3_span_full_eval_skipped = 0.0
    stage3_span_full_seconds_total = 0.0
    stage3_span_full_seconds_active = 0.0
    stage3_span_basin_judge_k_used = 0
    stage3_span_basin_judge_seconds = 0.0
    stage3_basin_judge_span_calls_total = 0
    stage3_basin_judge_span_calls_active = 0
    stage3_basin_judge_span_calls_rejected_or_gated = 0
    stage3_basin_judge_span_seconds_total = 0.0
    stage3_basin_judge_unique_end_hash = 0
    stage3_word_ngram_rows_scored = 0
    stage3_word_ngram_rows_active = 0

    if phaseA_rows:
        phaseA_end_plaintexts = [
            np.asarray(r.get("end_plaintext", []), dtype=np.uint8).reshape(-1)
            for r in phaseA_rows
        ]
        phaseA_end_scores_search_arr, _phaseA_end_stats = score_plaintexts_chunked(
            scorer=scorer_stage3_search_runtime,
            plaintexts=phaseA_end_plaintexts,
            wli=None,
            chunk_size=int(batch_eval_chunk_size),
            require_batch=bool(require_batch_scoring),
        )
        for idx_r, row in enumerate(phaseA_rows):
            end_score_search = (
                float(phaseA_end_scores_search_arr[idx_r])
                if idx_r < int(phaseA_end_scores_search_arr.size)
                else float("nan")
            )
            row["end_score_search"] = float(end_score_search)

        judge_ranked = sorted(
            enumerate(phaseA_rows),
            key=lambda it: (
                float(it[1].get("end_score_search", float("-inf"))),
                float(it[1].get("end_match", float("-inf"))),
                float(it[1].get("end_score_raw", float("-inf"))),
                -int(it[1].get("restart_idx", 0)),
            ),
            reverse=True,
        )
        judge_pool = list(judge_ranked)
        if bool(stage3_span_basin_judge_dedupe_by_end_hash):
            judge_pool = []
            seen_end_hash: set[str] = set()
            for row_idx, row in judge_ranked:
                end_hash = str(row.get("end_hash", ""))
                if end_hash in seen_end_hash:
                    continue
                seen_end_hash.add(end_hash)
                judge_pool.append((row_idx, row))
        stage3_span_basin_judge_k_used = int(
            max(0, min(int(stage3_span_basin_judge_k_cfg), len(judge_pool)))
        )
        judge_idx = [
            int(idx) for idx, _row in judge_pool[: int(stage3_span_basin_judge_k_used)]
        ]
        stage3_basin_judge_unique_end_hash = int(
            len({str(phaseA_rows[idx].get("end_hash", "")) for idx in judge_idx})
        )
        if judge_idx:
            judge_end_plaintexts = [
                np.asarray(r.get("end_plaintext", []), dtype=np.uint8).reshape(-1)
                for r in (phaseA_rows[idx] for idx in judge_idx)
            ]
            judge_start_plaintexts = [
                np.asarray(r.get("start_plaintext", []), dtype=np.uint8).reshape(-1)
                for r in (phaseA_rows[idx] for idx in judge_idx)
            ]
            t_span_judge = float(time.time())
            for local_idx, row_idx in enumerate(judge_idx):
                span_before = scorer_span_counter_summary_fn(scorer_basin_judge_runtime)
                judge_end_scores_arr, _judge_end_stats = score_plaintexts_chunked(
                    scorer=scorer_basin_judge_runtime,
                    plaintexts=[judge_end_plaintexts[local_idx]],
                    wli=None,
                    chunk_size=1,
                    require_batch=bool(require_batch_scoring),
                )
                span_after = scorer_span_counter_summary_fn(scorer_basin_judge_runtime)
                span_delta = span_counter_delta_fn(before=span_before, after=span_after)
                call_total_i = int(round(float(span_delta.get("total", 0.0))))
                call_active_i = int(round(float(span_delta.get("active", 0.0))))
                call_rejected_i = int(max(0, call_total_i - call_active_i))
                stage3_basin_judge_span_calls_total += int(max(0, call_total_i))
                stage3_basin_judge_span_calls_active += int(max(0, call_active_i))
                stage3_basin_judge_span_calls_rejected_or_gated += int(
                    max(0, call_rejected_i)
                )
                stage3_basin_judge_span_seconds_total += float(
                    max(0.0, float(span_delta.get("seconds_total", 0.0)))
                )
                row = phaseA_rows[int(row_idx)]
                end_score_pct = (
                    float(judge_end_scores_arr[0])
                    if int(judge_end_scores_arr.size) > 0
                    else float("nan")
                )
                span_active_for_row = bool(
                    call_total_i > 0 and call_active_i > 0 and call_rejected_i <= 0
                )
                if bool(stage3_span_basin_judge_require_span_active) and (
                    not span_active_for_row
                ):
                    end_score_pct = float("-inf")
                    if int(call_total_i) <= 0:
                        stage3_basin_judge_span_calls_rejected_or_gated += 1
                judge_start_scores_arr, _judge_start_stats = score_plaintexts_chunked(
                    scorer=scorer_basin_judge_runtime,
                    plaintexts=[judge_start_plaintexts[local_idx]],
                    wli=None,
                    chunk_size=1,
                    require_batch=bool(require_batch_scoring),
                )
                start_score_pct = (
                    float(judge_start_scores_arr[0])
                    if int(judge_start_scores_arr.size) > 0
                    else float("nan")
                )
                best_delta_pct = (
                    float(end_score_pct - start_score_pct)
                    if np.isfinite(end_score_pct) and np.isfinite(start_score_pct)
                    else float("nan")
                )
                row["start_score_pct"] = float(start_score_pct)
                row["end_score_pct"] = float(end_score_pct)
                row["best_delta_pct"] = float(best_delta_pct)
                row["basin_judge_span_active"] = int(1 if span_active_for_row else 0)
                row["word_ngram_judge_active"] = int(0)
                row["word_ngram_report_xent"] = float("nan")
                row["word_ngram_trust_score"] = float("nan")
                if bool(stage3_word_ngram_decision_influence) and (
                    scorer_word_ngram_report_runtime is not None
                ):
                    _word_ngram_scores_arr, _word_ngram_stats = score_plaintexts_chunked(
                        scorer=scorer_word_ngram_report_runtime,
                        plaintexts=[judge_end_plaintexts[local_idx]],
                        wli=None,
                        chunk_size=1,
                        require_batch=bool(require_batch_scoring),
                    )
                    _ = _word_ngram_scores_arr, _word_ngram_stats
                    word_ngram_last_stats: dict[str, Any] = {}
                    try:
                        if hasattr(scorer_word_ngram_report_runtime, "last_stats") and callable(
                            scorer_word_ngram_report_runtime.last_stats
                        ):
                            maybe_stats = scorer_word_ngram_report_runtime.last_stats()
                            if isinstance(maybe_stats, dict):
                                word_ngram_last_stats = dict(maybe_stats)
                    except Exception:
                        word_ngram_last_stats = {}
                    word_ngram_active = bool(
                        word_ngram_last_stats.get("word_ngram_judge_active", False)
                    )
                    word_ngram_report_xent = word_ngram_last_stats.get(
                        "word_ngram_judge_report_xent", None
                    )
                    word_ngram_trust_score = word_ngram_last_stats.get(
                        "word_ngram_judge_trust_score", None
                    )
                    row["word_ngram_judge_active"] = int(1 if word_ngram_active else 0)
                    row["word_ngram_report_xent"] = (
                        float(word_ngram_report_xent)
                        if word_ngram_report_xent is not None
                        else float("nan")
                    )
                    row["word_ngram_trust_score"] = (
                        float(word_ngram_trust_score)
                        if word_ngram_trust_score is not None
                        else float("nan")
                    )
                    stage3_word_ngram_rows_scored += 1
                    stage3_word_ngram_rows_active += int(1 if word_ngram_active else 0)
                row_metrics = row.get("metrics", {})
                if isinstance(row_metrics, dict):
                    row_metrics["score_pct"] = float(end_score_pct)
                    row_metrics["score_search"] = float(
                        row.get("end_score_search", float("nan"))
                    )
                    row_metrics["score_raw"] = float(
                        row.get("end_score_raw", float("nan"))
                    )
                    row_metrics["basin_judge_span_active"] = int(
                        1 if span_active_for_row else 0
                    )
                    row_metrics["word_ngram_judge_active"] = int(
                        row.get("word_ngram_judge_active", 0)
                    )
                    row_metrics["word_ngram_report_xent"] = float(
                        row.get("word_ngram_report_xent", float("nan"))
                    )
                    row_metrics["word_ngram_trust_score"] = float(
                        row.get("word_ngram_trust_score", float("nan"))
                    )
                restart_stage_idx = int(row.get("restart_idx", -1))
                for stage_row in reversed(stage_rows):
                    if (
                        isinstance(stage_row, dict)
                        and str(stage_row.get("stage", "")) == "stage3_phaseA_restart"
                        and int(stage_row.get("restart_idx", -2)) == restart_stage_idx
                        and int(stage_row.get("text_id", -1)) == int(text_id)
                        and int(stage_row.get("key_seed", -1)) == int(key_seed)
                    ):
                        stage_row["start_score_pct"] = float(start_score_pct)
                        stage_row["end_score_pct"] = float(end_score_pct)
                        stage_row["score"] = float(end_score_pct)
                        stage_row["best_delta"] = float(best_delta_pct)
                        stage_row["end_score_search"] = float(
                            row.get("end_score_search", float("nan"))
                        )
                        stage_row["basin_judge_span_active"] = int(
                            1 if span_active_for_row else 0
                        )
                        stage_row["word_ngram_judge_active"] = int(
                            row.get("word_ngram_judge_active", 0)
                        )
                        stage_row["word_ngram_report_xent"] = float(
                            row.get("word_ngram_report_xent", float("nan"))
                        )
                        stage_row["word_ngram_trust_score"] = float(
                            row.get("word_ngram_trust_score", float("nan"))
                        )
                        break
            stage3_span_basin_judge_seconds += max(0.0, float(time.time() - t_span_judge))
        print(
            f"{log_prefix} stage3-basin-judge tier={tier_name} text={text_id} "
            f"key_seed={key_seed} k={int(stage3_span_basin_judge_k_used)}/"
            f"{int(stage3_span_basin_judge_k_cfg)} "
            f"basin_judge_unique_end_hash={int(stage3_basin_judge_unique_end_hash)} "
            f"basin_judge_span_calls_total={int(stage3_basin_judge_span_calls_total)} "
            f"basin_judge_span_calls_active={int(stage3_basin_judge_span_calls_active)} "
            f"basin_judge_span_calls_rejected_or_gated={int(stage3_basin_judge_span_calls_rejected_or_gated)} "
            f"basin_judge_span_seconds_total={float(stage3_basin_judge_span_seconds_total):.3f} "
            f"span_judge_wall_s={float(stage3_span_basin_judge_seconds):.3f}",
            flush=True,
        )

    phaseA_start_scores = [
        float(r["start_score_pct"])
        for r in phaseA_rows
        if np.isfinite(float(r.get("start_score_pct", float("nan"))))
    ]
    phaseA_end_scores = [
        float(r["end_score_pct"])
        for r in phaseA_rows
        if np.isfinite(float(r["end_score_pct"]))
    ]
    phaseA_deltas = [
        float(r["best_delta_pct"])
        for r in phaseA_rows
        if np.isfinite(float(r["best_delta_pct"]))
    ]
    phaseA_best_start_score = (
        float(max(phaseA_start_scores)) if phaseA_start_scores else float("nan")
    )
    phaseA_best_end_score = (
        float(max(phaseA_end_scores)) if phaseA_end_scores else float("nan")
    )
    phaseA_best_delta = float(max(phaseA_deltas)) if phaseA_deltas else float("nan")

    if phaseA_rows:
        phaseA_best = phaseA_rows[0]
        for row in phaseA_rows[1:]:
            better_phasea = is_better_stage3_candidate_preserving_solve_fn(
                float(row.get("end_score_pct", float("nan"))),
                float(row.get("end_match", float("nan"))),
                float(phaseA_best.get("end_score_pct", float("nan"))),
                float(phaseA_best.get("end_match", float("nan"))),
                score_first=(not bool(oracle_assist_selection_effective)),
            )
            if better_phasea:
                phaseA_best = row
        best3_score = float(phaseA_best["end_score_pct"])
        best3_match = (
            float(phaseA_best["end_match"])
            if np.isfinite(float(phaseA_best["end_match"]))
            else float("nan")
        )
        best3_key = list(map(int, phaseA_best["end_key"]))
        pt3 = np.asarray(phaseA_best["end_plaintext"], dtype=np.uint8).reshape(-1)
        mm_best = dict(phaseA_best["metrics"])
        slip_count = int(mm_best["slip_count"])
        slip_accept_count = int(mm_best["slip_accept_count"])
        slip_accept_rate = float(mm_best["slip_accept_rate"])
        accept_rate = float(mm_best["accept_rate"])
        phase_attempts_total = int(mm_best["phase_attempts_total"])
        phase_improves_total = int(mm_best["phase_improves_total"])
        phase_best_delta_max = float(mm_best["phase_best_delta_max"])
        phaseA_solved = bool(
            np.isfinite(best3_match)
            and float(best3_match) >= float(solve_match_threshold)
        )

    gate_delta = float(stage3_phaseB_gate_delta)
    gate_end_gain = float(stage3_phaseB_gate_end_gain)
    phaseB_forced_skip_reason = (
        "scan_phaseA_only" if bool(stage3_scan_phaseA_only) else ""
    )
    gate_skip = bool(stage3_scan_phaseA_only)
    if not gate_skip:
        gate_skip = bool(phaseA_solved)
    if not gate_skip:
        gate_skip = (
            np.isfinite(phaseA_best_delta)
            and np.isfinite(phaseA_best_start_score)
            and np.isfinite(phaseA_best_end_score)
            and (float(phaseA_best_delta) < gate_delta)
            and (
                float(phaseA_best_end_score)
                < float(phaseA_best_start_score) + gate_end_gain
            )
        )
    phaseA_best_end_score_raw = float("nan")
    if phaseA_rows:
        phaseA_end_raw_vals = [
            float(r.get("end_score_raw", float("nan")))
            for r in phaseA_rows
            if np.isfinite(float(r.get("end_score_raw", float("nan"))))
        ]
        if phaseA_end_raw_vals:
            phaseA_best_end_score_raw = float(max(phaseA_end_raw_vals))
    stage_rows.append(
        dict(
            tier=tier_name,
            text_id=int(text_id),
            key_seed=int(key_seed),
            stage="stage3_phaseB_gate",
            phaseA_experiment=str(stage3_phaseA_experiment),
            phaseB_experiment=str(stage3_phaseB_experiment),
            phaseA_best_delta=float(phaseA_best_delta),
            phaseA_best_start_score=float(phaseA_best_start_score),
            phaseA_best_end_score=float(phaseA_best_end_score),
            phaseA_best_end_score_raw=float(phaseA_best_end_score_raw),
            phaseA_solved=int(1 if phaseA_solved else 0),
            gate_delta_floor=float(gate_delta),
            gate_end_gain_floor=float(gate_end_gain),
            phaseB_skipped=int(1 if gate_skip else 0),
            phaseB_top_n=int(stage3_phaseB_top_n),
            span_basin_judge_k_cfg=int(stage3_span_basin_judge_k_cfg),
            span_basin_judge_k=int(stage3_span_basin_judge_k_used),
            span_basin_judge_seconds=float(stage3_span_basin_judge_seconds),
            basin_judge_span_calls_total=int(stage3_basin_judge_span_calls_total),
            basin_judge_span_calls_active=int(stage3_basin_judge_span_calls_active),
            basin_judge_span_calls_rejected_or_gated=int(
                stage3_basin_judge_span_calls_rejected_or_gated
            ),
            basin_judge_span_seconds_total=float(stage3_basin_judge_span_seconds_total),
            basin_judge_unique_end_hash=int(stage3_basin_judge_unique_end_hash),
            word_ngram_decision_influence=int(
                1 if bool(stage3_word_ngram_decision_influence) else 0
            ),
            word_ngram_rows_scored=int(stage3_word_ngram_rows_scored),
            word_ngram_rows_active=int(stage3_word_ngram_rows_active),
            phaseB_char_pct_min_dynamic=float(stage3_phaseB_char_pct_min_dynamic),
            phaseB_char_pct_min_source=str(stage3_phaseB_char_pct_min_source),
            scan_phaseA_only=int(1 if bool(stage3_scan_phaseA_only) else 0),
        )
    )

    if gate_skip:
        phaseB_skipped = 1
        if bool(phaseB_forced_skip_reason):
            phaseB_skip_reason = str(phaseB_forced_skip_reason)
            stop_reason_update = "stage3_phaseb_skipped_scan_phaseA_only"
        else:
            phaseB_skip_reason = "phaseA_solved" if phaseA_solved else "phaseA_low_progress"
            stop_reason_update = "solved_stage3" if phaseA_solved else "stage3_phaseb_skipped"
        print(
            f"{log_prefix} stage3-phaseB-gate tier={tier_name} text={text_id} "
            f"key_seed={key_seed} start_pct={fmt_finite_float_fn(phaseA_best_start_score)} "
            f"end_pct={fmt_finite_float_fn(phaseA_best_end_score)} "
            f"delta_pct={fmt_finite_float_fn(phaseA_best_delta)} "
            f"gate=(delta>={float(gate_delta):.4f},end_gain>={float(gate_end_gain):.4f}) "
            f"phaseB_skipped=1 reason={phaseB_skip_reason} top_n={int(stage3_phaseB_top_n)}",
            flush=True,
        )
        append_stage3_topk_from_phasea_fn(
            payload=stage3_topk_payload,
            rows=phaseA_rows,
            key_len=int(key_len),
        )
        return dict(
            stage_rows=stage_rows,
            best3_score=float(best3_score),
            best3_match=float(best3_match),
            best3_key=(list(map(int, best3_key)) if best3_key is not None else None),
            pt3=np.asarray(pt3, dtype=np.uint8),
            stop_reason_update=str(stop_reason_update),
            dt3_delta=float(dt3_delta),
            ev3_delta=int(ev3_delta),
            stage3_solve_hits_delta=int(stage3_solve_hits_delta),
            slip_count=int(slip_count),
            slip_accept_count=int(slip_accept_count),
            slip_accept_rate=float(slip_accept_rate),
            accept_rate=float(accept_rate),
            phase_attempts_total=int(phase_attempts_total),
            phase_improves_total=int(phase_improves_total),
            phase_best_delta_max=float(phase_best_delta_max),
            phaseA_best_delta=float(phaseA_best_delta),
            phaseA_best_start_score=float(phaseA_best_start_score),
            phaseA_best_end_score=float(phaseA_best_end_score),
            phaseA_solved=bool(phaseA_solved),
            phaseB_ran=int(phaseB_ran),
            phaseB_skipped=int(phaseB_skipped),
            phaseB_skip_reason=str(phaseB_skip_reason),
            phaseB_top_n_used=int(phaseB_top_n_used),
            stage3_span_basin_judge_k_used=int(stage3_span_basin_judge_k_used),
            stage3_span_basin_judge_seconds=float(stage3_span_basin_judge_seconds),
            stage3_basin_judge_span_calls_total=int(stage3_basin_judge_span_calls_total),
            stage3_basin_judge_span_calls_active=int(
                stage3_basin_judge_span_calls_active
            ),
            stage3_basin_judge_span_calls_rejected_or_gated=int(
                stage3_basin_judge_span_calls_rejected_or_gated
            ),
            stage3_basin_judge_span_seconds_total=float(
                stage3_basin_judge_span_seconds_total
            ),
            stage3_basin_judge_unique_end_hash=int(stage3_basin_judge_unique_end_hash),
            stage3_word_ngram_rows_scored=int(stage3_word_ngram_rows_scored),
            stage3_word_ngram_rows_active=int(stage3_word_ngram_rows_active),
            stage3_span_full_eval_total=float(stage3_span_full_eval_total),
            stage3_span_full_eval_active=float(stage3_span_full_eval_active),
            stage3_span_full_eval_skipped=float(stage3_span_full_eval_skipped),
            stage3_span_full_seconds_total=float(stage3_span_full_seconds_total),
            stage3_span_full_seconds_active=float(stage3_span_full_seconds_active),
        )

    top_n = max(1, int(stage3_phaseB_top_n))

    def _phaseb_rank_key(row: Dict[str, Any]) -> tuple[float, ...]:
        end_score_pct = float(row.get("end_score_pct", float("-inf")))
        best_delta_pct = float(row.get("best_delta_pct", float("-inf")))
        end_score_raw = float(row.get("end_score_raw", float("-inf")))
        restart_key = float(-int(row.get("restart_idx", 0)))
        if not bool(stage3_word_ngram_decision_influence):
            return (end_score_pct, best_delta_pct, end_score_raw, restart_key)
        word_ngram_active = float(1 if bool(row.get("word_ngram_judge_active", 0)) else 0)
        word_ngram_trust = float(row.get("word_ngram_trust_score", float("-inf")))
        if not np.isfinite(word_ngram_trust):
            word_ngram_trust = float("-inf")
        word_ngram_report_xent = float(row.get("word_ngram_report_xent", float("nan")))
        word_ngram_report_xent_sort = (
            float(-word_ngram_report_xent)
            if np.isfinite(word_ngram_report_xent)
            else float("-inf")
        )
        return (
            end_score_pct,
            word_ngram_active,
            word_ngram_trust,
            word_ngram_report_xent_sort,
            best_delta_pct,
            end_score_raw,
            restart_key,
        )

    ranked = sorted(phaseA_rows, key=_phaseb_rank_key, reverse=True)
    selected: List[Dict[str, Any]] = []
    seen_basin: set[Tuple[str, str]] = set()
    for row in ranked:
        basin_id = (str(row["start_hash"]), str(row["end_hash"]))
        if basin_id in seen_basin:
            continue
        seen_basin.add(basin_id)
        selected.append(row)
    if not selected and ranked:
        selected = [ranked[0]]
    judge_top1 = float("nan")
    judge_top2 = float("nan")
    judge_margin = float("nan")
    if selected:
        judge_top1 = float(selected[0].get("end_score_pct", float("nan")))
        if len(selected) > 1:
            judge_top2 = float(selected[1].get("end_score_pct", float("nan")))
            if np.isfinite(judge_top1) and np.isfinite(judge_top2):
                judge_margin = float(judge_top1 - judge_top2)
    selected_top_n = list(selected[:top_n])
    tie_eps = float(max(0.0, float(stage3_span_basin_judge_tie_eps)))
    tie_cap = int(max(int(top_n), int(stage3_span_basin_judge_tie_max_seeds)))
    tie_band: List[Dict[str, Any]] = []
    if selected and np.isfinite(float(selected[0].get("end_score_pct", float("nan")))):
        top_score = float(selected[0].get("end_score_pct", float("nan")))
        for row in selected:
            row_score = float(row.get("end_score_pct", float("nan")))
            if not np.isfinite(row_score):
                continue
            if float(top_score - row_score) <= float(tie_eps):
                tie_band.append(row)
    selected = list(selected_top_n)
    phaseB_ready_reason = "passed"
    if len(tie_band) > len(selected_top_n):
        selected = list(tie_band[:tie_cap])
        phaseB_ready_reason = (
            f"tie_band_eps={float(tie_eps):.4f}_"
            f"n={int(len(tie_band))}_cap={int(tie_cap)}"
        )
    phaseB_top_n_used = int(len(selected))
    phaseB_ran = int(1 if selected else 0)
    if (not selected) and bool(selected_top_n):
        selected = [selected_top_n[0]]
        phaseB_top_n_used = int(len(selected))
        phaseB_ran = 1
        phaseB_ready_reason = "fallback_top1"
    elif not selected:
        phaseB_ready_reason = "selected_empty"
    tie_band_n = int(len(tie_band))
    selected_top_n_n = int(len(selected_top_n))
    selected_final_n = int(len(selected))
    tie_clipped = int(max(0, tie_band_n - int(tie_cap)))

    print(
        f"{log_prefix} stage3-phaseB-gate tier={tier_name} text={text_id} key_seed={key_seed} "
        f"start_pct={fmt_finite_float_fn(phaseA_best_start_score)} "
        f"end_pct={fmt_finite_float_fn(phaseA_best_end_score)} "
        f"delta_pct={fmt_finite_float_fn(phaseA_best_delta)} "
        f"gate=(delta>={float(gate_delta):.4f},end_gain>={float(gate_end_gain):.4f}) "
        f"phaseB_ran={int(phaseB_ran)} reason={phaseB_ready_reason} "
        f"top_n={int(phaseB_top_n_used)} "
        f"judge_top1={fmt_finite_float_fn(judge_top1)} "
        f"judge_top2={fmt_finite_float_fn(judge_top2)} "
        f"judge_margin={fmt_finite_float_fn(judge_margin)} "
        f"word_ngram_influence={1 if bool(stage3_word_ngram_decision_influence) else 0} "
        f"word_ngram_active_rows={int(stage3_word_ngram_rows_active)}/{int(stage3_word_ngram_rows_scored)} "
        f"tie_eps={float(tie_eps):.6f} tie_band={tie_band_n} tie_cap={int(tie_cap)} "
        f"tie_clipped={tie_clipped} selected_top_n={selected_top_n_n} "
        f"selected_final={selected_final_n}",
        flush=True,
    )

    if selected:
        phaseB_init = [list(map(int, row["end_key"])) for row in selected]
        phaseB_cfg = dict(solver_stage3_cfg)
        phaseB_cfg.update(dict(stage3_phaseB_cfg))
        phaseB_cfg["restarts"] = int(max(1, len(phaseB_init)))
        phaseB_cfg["seed_restarts"] = 0
        phaseB_cfg["seed"] = int(base_seed + 900001)
        t_run = time.time()
        stage3_phaseb_logging_cfg = stage3_progress_logging_fn(
            tier_name=str(tier_name),
            text_id=int(text_id),
            key_seed=int(key_seed),
            phase="phaseB",
            phase_steps=int(phaseB_cfg.get("steps", 0) or 0),
            phase_start_ts=float(t_run),
            heartbeat_seconds=float(stage3_heartbeat_seconds),
            heartbeat_state=stage3_hb_state,
            min_step=int(stage3_heartbeat_min_step),
            min_elapsed_seconds=float(stage3_heartbeat_min_elapsed_seconds),
            evals_base=int(ev3_base),
        )
        sol_b = run(
            text=ct_idx.tolist(),
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
            solver=SolverSpec.kaeding(**phaseB_cfg),
            scorer_params=scorer_stage3_phaseB,
            logging=stage3_phaseb_logging_cfg,
            wli_data=[],
            encoding_dir=direction,
            telemetry_on=True,
            force_no_wli=True,
            initial_keys=phaseB_init,
        )
        dt_run = float(time.time() - t_run)
        dt3_delta += float(dt_run)
        ev_b = int((getattr(sol_b, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
        ev3_delta += int(ev_b)

        pt_b = np.asarray(getattr(sol_b, "plaintext_idx", []) or [], dtype=np.uint8).reshape(
            -1
        )
        k_b_arr = np.asarray(getattr(sol_b, "key", []) or [], dtype=np.int16).reshape(-1)
        best_b_key = best3_key if best3_key is not None else list(map(int, phaseB_init[0]))
        if k_b_arr.size == int(key_len):
            best_b_key = k_b_arr.astype(int).tolist()
        best_b_score = float(getattr(sol_b, "score", float("nan")))
        if pt_b.size > 0:
            judge_b_arr, _judge_b_stats = score_plaintexts_chunked(
                scorer=scorer_full_runtime,
                plaintexts=[pt_b],
                wli=None,
                chunk_size=int(batch_eval_chunk_size),
                require_batch=bool(require_batch_scoring),
            )
            if judge_b_arr.size > 0:
                best_b_score = float(judge_b_arr[0])
        best_b_match = (
            float(match_ratio_fn(pt_b.tolist(), pt_idx.tolist()))
            if pt_b.size > 0
            else float("nan")
        )
        if np.isfinite(best_b_match) and float(best_b_match) >= float(solve_match_threshold):
            stage3_solve_hits_delta = int(stage3_solve_hits_delta) + 1
            print(
                f"{log_prefix} stage3-solve-hit tier={tier_name} text={text_id} key_seed={key_seed} "
                f"phase=phaseB match={float(best_b_match):.3f} score={float(best_b_score):.6f}",
                flush=True,
            )
        tele_b = (getattr(sol_b, "meta", {}) or {}).get("telemetry", {})
        kaeding_b = tele_b.get("kaeding", {}) if isinstance(tele_b, dict) else {}
        mm_b = extract_kaeding_metrics_fn(kaeding_b)
        span_b = solution_span_counter_summary_fn(sol_b)
        stage3_span_full_eval_total += float(span_b["total"])
        stage3_span_full_eval_active += float(span_b["active"])
        stage3_span_full_eval_skipped += float(span_b["skipped"])
        stage3_span_full_seconds_total += float(span_b["seconds_total"])
        stage3_span_full_seconds_active += float(span_b["seconds_active"])

        stage_rows.append(
            dict(
                tier=tier_name,
                text_id=int(text_id),
                key_seed=int(key_seed),
                stage="stage3_phaseB",
                phaseB_top_n_used=int(phaseB_top_n_used),
                score=float(best_b_score),
                match_ratio=float(best_b_match),
                seconds=round(dt_run, 3),
                evals=int(ev_b),
                slip_count=int(mm_b["slip_count"]),
                slip_accept_count=int(mm_b["slip_accept_count"]),
                slip_accept_rate=float(mm_b["slip_accept_rate"]),
                accept_rate=float(mm_b["accept_rate"]),
                phase_attempts_total=int(mm_b["phase_attempts_total"]),
                phase_improves_total=int(mm_b["phase_improves_total"]),
                phase_best_delta_max=float(mm_b["phase_best_delta_max"]),
            )
        )

        better_phaseb = is_better_stage3_candidate_preserving_solve_fn(
            float(best_b_score),
            float(best_b_match),
            float(best3_score),
            float(best3_match),
            score_first=(not bool(oracle_assist_selection_effective)),
        )
        if better_phaseb:
            best3_score = float(best_b_score)
            best3_match = float(best_b_match)
            best3_key = list(map(int, best_b_key))
            pt3 = pt_b.copy()
            slip_count = int(mm_b["slip_count"])
            slip_accept_count = int(mm_b["slip_accept_count"])
            slip_accept_rate = float(mm_b["slip_accept_rate"])
            accept_rate = float(mm_b["accept_rate"])
            phase_attempts_total = int(mm_b["phase_attempts_total"])
            phase_improves_total = int(mm_b["phase_improves_total"])
            phase_best_delta_max = float(mm_b["phase_best_delta_max"])
        append_stage3_topk_from_kaeding_fn(
            payload=stage3_topk_payload,
            kaeding_obj=kaeding_b,
            key_len=int(key_len),
            full_cipher=full_cipher,
            ciphertext=np.asarray(ct_idx, dtype=np.uint8),
            scorer_full_runtime=scorer_full_runtime,
            target_plaintext=np.asarray(pt_idx, dtype=np.uint8),
        )

    return dict(
        stage_rows=stage_rows,
        best3_score=float(best3_score),
        best3_match=float(best3_match),
        best3_key=(list(map(int, best3_key)) if best3_key is not None else None),
        pt3=np.asarray(pt3, dtype=np.uint8),
        stop_reason_update=str(stop_reason_update),
        dt3_delta=float(dt3_delta),
        ev3_delta=int(ev3_delta),
        stage3_solve_hits_delta=int(stage3_solve_hits_delta),
        slip_count=int(slip_count),
        slip_accept_count=int(slip_accept_count),
        slip_accept_rate=float(slip_accept_rate),
        accept_rate=float(accept_rate),
        phase_attempts_total=int(phase_attempts_total),
        phase_improves_total=int(phase_improves_total),
        phase_best_delta_max=float(phase_best_delta_max),
        phaseA_best_delta=float(phaseA_best_delta),
        phaseA_best_start_score=float(phaseA_best_start_score),
        phaseA_best_end_score=float(phaseA_best_end_score),
        phaseA_solved=bool(phaseA_solved),
        phaseB_ran=int(phaseB_ran),
        phaseB_skipped=int(phaseB_skipped),
        phaseB_skip_reason=str(phaseB_skip_reason),
        phaseB_top_n_used=int(phaseB_top_n_used),
        stage3_span_basin_judge_k_used=int(stage3_span_basin_judge_k_used),
        stage3_span_basin_judge_seconds=float(stage3_span_basin_judge_seconds),
        stage3_basin_judge_span_calls_total=int(stage3_basin_judge_span_calls_total),
        stage3_basin_judge_span_calls_active=int(stage3_basin_judge_span_calls_active),
        stage3_basin_judge_span_calls_rejected_or_gated=int(
            stage3_basin_judge_span_calls_rejected_or_gated
        ),
        stage3_basin_judge_span_seconds_total=float(
            stage3_basin_judge_span_seconds_total
        ),
        stage3_basin_judge_unique_end_hash=int(stage3_basin_judge_unique_end_hash),
        stage3_word_ngram_rows_scored=int(stage3_word_ngram_rows_scored),
        stage3_word_ngram_rows_active=int(stage3_word_ngram_rows_active),
        stage3_span_full_eval_total=float(stage3_span_full_eval_total),
        stage3_span_full_eval_active=float(stage3_span_full_eval_active),
        stage3_span_full_eval_skipped=float(stage3_span_full_eval_skipped),
        stage3_span_full_seconds_total=float(stage3_span_full_seconds_total),
        stage3_span_full_seconds_active=float(stage3_span_full_seconds_active),
    )
