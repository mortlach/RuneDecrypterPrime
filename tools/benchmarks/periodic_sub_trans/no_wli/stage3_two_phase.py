from __future__ import annotations

from pathlib import Path
import threading
import time
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.api import KeySpec, SolverSpec, by_name, run

from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    decrypt_and_score_keys_chunked,
    score_plaintexts_chunked,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_candidates import (
    apply_slice_pair_swap,
    apply_slice_slip,
    target_slice_active_positions,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_checkpoint import (
    append_phasec_start_checkpoint,
    build_phasec_start_checkpoint_row,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_search import (
    run_slice_local_mini_search,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_selector import (
    landing_sort_key,
    rank_rows,
    row_score_gain,
    row_search_gain,
    score_sort_key,
    select_guard_passing_row,
)
from tools.benchmarks.periodic_sub_trans.no_wli.family_views import (
    cluster_family_ids,
    family_view_distance,
    find_family_view,
    rows_share_family,
)
from tools.benchmarks.periodic_sub_trans.no_wli.shadow_stop_v1 import (
    build_shadow_stop_v1_state,
    update_shadow_stop_v1_state,
)


PHASEC_SHADOW_STOP_V1_PLATEAU_STEPS = 16
PHASEC_SHADOW_STOP_V1_HIGH_SCORE_FLOOR = 0.45
PHASEC_SHADOW_STOP_V1_HIGH_SCORE_STABLE_STEPS = 4
PHASEC_SHADOW_STOP_V1_SCORE_IMPROVE_EPS = 1.0e-6


def build_phasea_gate_snapshot(
    *,
    tier_name: str,
    text_id: int,
    key_seed: int,
    phaseA_rows: Sequence[Dict[str, Any]],
    phaseA_selected_rows: Sequence[Dict[str, Any]],
    gate_delta: float,
    gate_end_gain: float,
    phaseB_ran: int,
    phaseB_ready_reason: str,
    phaseB_top_n_used: int,
    phaseB_selected_unique_end_hash: int,
    phaseB_family_preservation_policy: str,
    phaseB_family_view_id: str,
    phaseB_family_reserved_slots: int,
    phaseB_family_count_in_top_band: int,
    phaseB_family_preserved_count: int,
    phaseB_family_reservation_applied: int,
    phaseB_downstream_selected_count: int,
    phaseB_downstream_selected_unique_end_hash: int,
) -> Dict[str, Any]:
    selected_rows = [dict(row) for row in list(phaseA_selected_rows or [])]
    rank1_row = dict(selected_rows[0]) if selected_rows else {}

    def _finite_metric(row: Mapping[str, Any], key: str) -> float:
        try:
            value = float(row.get(key, float("nan")))
        except (TypeError, ValueError):
            return float("nan")
        return value if np.isfinite(value) else float("-inf")

    def _metric_with_fallback(row: Mapping[str, Any], *keys: str) -> float:
        for key in keys:
            value = _finite_metric(row, key)
            if np.isfinite(value):
                return value
        return float("-inf")

    best_phasea_init = (
        dict(
            max(
                selected_rows,
                key=lambda row: _metric_with_fallback(row, "init_match", "end_match", "match"),
            )
        )
        if selected_rows
        else {}
    )
    best_phasea_final = (
        dict(
            max(
                selected_rows,
                key=lambda row: _metric_with_fallback(
                    row,
                    "final_match",
                    "end_match",
                    "match",
                ),
            )
        )
        if selected_rows
        else {}
    )

    def _row_match(row: Mapping[str, Any], *keys: str) -> float:
        for key in keys:
            try:
                value = float(row.get(key, float("nan")))
            except (TypeError, ValueError):
                continue
            if np.isfinite(value):
                return value
        return float("nan")

    def _row_int(row: Mapping[str, Any], *keys: str, default: int = 0) -> int:
        for key in keys:
            if key not in row:
                continue
            raw_value = row.get(key)
            if raw_value in (None, ""):
                continue
            try:
                value = int(raw_value)
            except (TypeError, ValueError):
                continue
            return value
        return int(default)

    def _row_str(row: Mapping[str, Any], *keys: str) -> str:
        for key in keys:
            value = str(row.get(key, "") or "")
            if value:
                return value
        return ""

    def _row_hash(row: Mapping[str, Any]) -> str:
        return str(
            row.get(
                "end_hash",
                row.get(
                    "candidate_hash",
                    row.get("start_hash", ""),
                ),
            )
            or ""
        )

    def _plateau_flag(row: Mapping[str, Any]) -> int:
        shadow_stop = dict(row.get("shadow_stop_v1", {}) or {})
        try:
            return int(shadow_stop.get("plateau_would_stop", 0) or 0)
        except (TypeError, ValueError):
            return 0

    return dict(
        tier_name=str(tier_name),
        text_id=int(text_id),
        key_seed=int(key_seed),
        phaseA_rows_scored=int(len(list(phaseA_rows or []))),
        phaseA_selected_count=int(len(selected_rows)),
        phaseA_rank1_source=_row_str(rank1_row, "source", "selection_bucket"),
        phaseA_rank1_source_rank=_row_int(
            rank1_row,
            "source_rank",
            "phaseb_rank",
            default=1,
        ),
        phaseA_rank1_candidate_hash=_row_hash(rank1_row),
        phaseA_rank1_init_match=_row_match(rank1_row, "init_match", "end_match", "match"),
        phaseA_rank1_final_match=_row_match(rank1_row, "final_match", "end_match", "match"),
        phaseA_rank1_score_gain=_row_match(rank1_row, "score_gain", "best_delta_pct"),
        phaseA_rank1_plateau_would_stop=_plateau_flag(rank1_row),
        phaseA_best_init_match=_row_match(
            best_phasea_init,
            "init_match",
            "end_match",
            "match",
        ),
        phaseA_best_init_source_rank=_row_int(
            best_phasea_init,
            "source_rank",
            "phaseb_rank",
            default=0,
        ),
        phaseA_best_init_candidate_hash=_row_hash(best_phasea_init),
        phaseA_best_final_match=_row_match(
            best_phasea_final,
            "final_match",
            "end_match",
            "match",
        ),
        phaseA_best_final_source_rank=_row_int(
            best_phasea_final,
            "source_rank",
            "phaseb_rank",
            default=0,
        ),
        phaseA_best_final_candidate_hash=_row_hash(best_phasea_final),
        phaseB_ran=int(phaseB_ran),
        phaseB_ready_reason=str(phaseB_ready_reason),
        phaseB_top_n_used=int(phaseB_top_n_used),
        phaseB_selected_unique_end_hash=int(phaseB_selected_unique_end_hash),
        phaseB_gate_delta_cfg=float(gate_delta),
        phaseB_gate_end_gain_cfg=float(gate_end_gain),
        phaseB_family_preservation_policy=str(phaseB_family_preservation_policy),
        phaseB_family_view_id=str(phaseB_family_view_id),
        phaseB_family_reserved_slots=int(phaseB_family_reserved_slots),
        phaseB_family_count_in_top_band=int(phaseB_family_count_in_top_band),
        phaseB_family_preserved_count=int(phaseB_family_preserved_count),
        phaseB_family_reservation_applied=int(phaseB_family_reservation_applied),
        phaseB_downstream_selected_count=int(phaseB_downstream_selected_count),
        phaseB_downstream_selected_unique_end_hash=int(
            phaseB_downstream_selected_unique_end_hash
        ),
    )


def _phaseb_rank_key_for_gate_snapshot(
    row: Mapping[str, Any],
    *,
    stage3_word_ngram_decision_influence: bool,
) -> tuple[float, ...]:
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


def build_phasea_provisional_gate_snapshot(
    *,
    tier_name: str,
    text_id: int,
    key_seed: int,
    key_len: int,
    phaseA_rows: Sequence[Dict[str, Any]],
    phaseA_checkpoint_restart_count: int,
    phaseA_checkpoint_restart_total: int,
    phaseA_checkpoint_elapsed_seconds: float,
    stage3_phaseB_top_n: int,
    stage3_span_basin_judge_tie_eps: float,
    stage3_span_basin_judge_tie_max_seeds: int,
    stage3_word_ngram_decision_influence: bool,
    phaseB_family_preservation_policy: str,
    phaseB_family_view_id: str,
    phaseB_family_reserved_slots: int,
    gate_delta: float,
    gate_end_gain: float,
) -> Dict[str, Any]:
    rows = [dict(row) for row in list(phaseA_rows or [])]
    if not rows:
        return {}

    def _snapshot_candidate_hash(row: Mapping[str, Any]) -> str:
        existing_hash = str(row.get("end_hash", "") or "")
        if existing_hash:
            return existing_hash
        end_key = list(map(int, row.get("end_key", [])))
        return ",".join(str(value) for value in end_key)

    def _fallback_phaseb_family_preservation(
        ranked_rows: Sequence[Dict[str, Any]],
        selected_rows: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        selected_out = [dict(row) for row in list(selected_rows or [])]
        unique_end_hash = int(
            len(
                {
                    _snapshot_candidate_hash(row)
                    for row in selected_out
                    if len(list(map(int, row.get("end_key", [])))) == int(key_len)
                }
            )
        )
        return dict(
            rows=selected_out,
            family_count_in_top_band=int(len(list(ranked_rows or []))),
            family_preserved_count=int(len(selected_out)),
            reservation_applied=0,
            downstream_selected_unique_end_hash=int(unique_end_hash),
        )

    top_n = max(1, int(stage3_phaseB_top_n))
    tie_eps = float(max(0.0, float(stage3_span_basin_judge_tie_eps)))
    tie_cap = int(max(int(top_n), int(stage3_span_basin_judge_tie_max_seeds)))
    ranked = sorted(
        rows,
        key=lambda row: _phaseb_rank_key_for_gate_snapshot(
            row,
            stage3_word_ngram_decision_influence=bool(
                stage3_word_ngram_decision_influence
            ),
        ),
        reverse=True,
    )
    ranked_unique_rows: List[Dict[str, Any]] = []
    seen_basin: set[Tuple[str, str]] = set()
    for row in ranked:
        basin_id = (str(row.get("start_hash", "")), str(row.get("end_hash", "")))
        if basin_id in seen_basin:
            continue
        seen_basin.add(basin_id)
        ranked_unique_rows.append(dict(row))
    selected_top_n = list(ranked_unique_rows[:top_n])
    tie_band: List[Dict[str, Any]] = []
    if ranked_unique_rows and np.isfinite(
        float(ranked_unique_rows[0].get("end_score_pct", float("nan")))
    ):
        top_score = float(ranked_unique_rows[0].get("end_score_pct", float("nan")))
        for row in ranked_unique_rows:
            row_score = float(row.get("end_score_pct", float("nan")))
            if not np.isfinite(row_score):
                continue
            if float(top_score - row_score) <= float(tie_eps):
                tie_band.append(dict(row))
    selected_rows = list(selected_top_n)
    phaseB_ready_reason = "passed"
    if len(tie_band) > len(selected_top_n):
        selected_rows = list(tie_band[:tie_cap])
        phaseB_ready_reason = (
            f"tie_band_eps={float(tie_eps):.4f}_"
            f"n={int(len(tie_band))}_cap={int(tie_cap)}"
        )
    phaseB_top_n_used = int(len(selected_rows))
    phaseB_ran = int(1 if selected_rows else 0)
    if (not selected_rows) and bool(selected_top_n):
        selected_rows = [dict(selected_top_n[0])]
        phaseB_top_n_used = int(len(selected_rows))
        phaseB_ran = 1
        phaseB_ready_reason = "fallback_top1"
    elif not selected_rows:
        phaseB_ready_reason = "selected_empty"
    phaseB_selected_unique_end_hash = int(
        len(
            {
                _snapshot_candidate_hash(row)
                for row in selected_rows
                if len(list(map(int, row.get("end_key", [])))) == int(key_len)
            }
        )
    )
    phaseB_family_preservation = _fallback_phaseb_family_preservation(
        ranked_rows=ranked_unique_rows,
        selected_rows=selected_rows,
    )
    downstream_rows = [dict(row) for row in list(phaseB_family_preservation["rows"])]
    snapshot = build_phasea_gate_snapshot(
        tier_name=str(tier_name),
        text_id=int(text_id),
        key_seed=int(key_seed),
        phaseA_rows=rows,
        phaseA_selected_rows=downstream_rows,
        gate_delta=float(gate_delta),
        gate_end_gain=float(gate_end_gain),
        phaseB_ran=int(phaseB_ran),
        phaseB_ready_reason=str(phaseB_ready_reason),
        phaseB_top_n_used=int(phaseB_top_n_used),
        phaseB_selected_unique_end_hash=int(phaseB_selected_unique_end_hash),
        phaseB_family_preservation_policy=str(phaseB_family_preservation_policy),
        phaseB_family_view_id=str(phaseB_family_view_id),
        phaseB_family_reserved_slots=int(phaseB_family_reserved_slots),
        phaseB_family_count_in_top_band=int(
            phaseB_family_preservation["family_count_in_top_band"]
        ),
        phaseB_family_preserved_count=int(
            phaseB_family_preservation["family_preserved_count"]
        ),
        phaseB_family_reservation_applied=int(
            phaseB_family_preservation["reservation_applied"]
        ),
        phaseB_downstream_selected_count=int(len(downstream_rows)),
        phaseB_downstream_selected_unique_end_hash=int(
            phaseB_family_preservation["downstream_selected_unique_end_hash"]
        ),
    )
    checkpoint_fraction = (
        float(phaseA_checkpoint_restart_count) / float(max(1, phaseA_checkpoint_restart_total))
    )
    snapshot.update(
        event="stage3_phasea_provisional_gate_snapshot",
        phaseA_checkpoint_restart_count=int(phaseA_checkpoint_restart_count),
        phaseA_checkpoint_restart_total=int(phaseA_checkpoint_restart_total),
        phaseA_checkpoint_fraction=float(checkpoint_fraction),
        phaseA_checkpoint_elapsed_seconds=float(phaseA_checkpoint_elapsed_seconds),
    )
    return snapshot


def _approx_phase_eval_budget(
    *,
    restarts: int,
    steps: int,
    inner_batch: int,
    col_every: int,
    col_batch: int,
) -> Dict[str, float]:
    restarts_i = int(max(1, int(restarts)))
    steps_i = int(max(0, int(steps)))
    inner_batch_i = int(max(0, int(inner_batch)))
    col_every_i = int(max(0, int(col_every)))
    col_batch_i = int(max(0, int(col_batch)))
    col_evals_per_step = (
        float(col_batch_i) / float(max(1, col_every_i)) if col_every_i > 0 else 0.0
    )
    evals_per_step = float(inner_batch_i) + float(col_evals_per_step)
    total_steps = int(restarts_i * steps_i)
    approx_eval_budget = float(total_steps) * float(evals_per_step)
    return dict(
        restarts=float(restarts_i),
        steps=float(steps_i),
        total_steps=float(total_steps),
        evals_per_step=float(evals_per_step),
        approx_eval_budget=float(approx_eval_budget),
    )


def _start_phase_watchdog(
    *,
    interval_seconds: float,
    phase_name: str,
    tier_name: str,
    text_id: int,
    key_seed: int,
    restarts: int,
    steps: int,
    total_steps: int,
    approx_eval_budget: float,
    start_ts: float,
    log_prefix: str,
) -> tuple[threading.Event, threading.Thread]:
    stop_event = threading.Event()
    interval = float(max(60.0, interval_seconds))

    def _worker() -> None:
        while not stop_event.wait(interval):
            elapsed_s = float(max(0.0, time.time() - start_ts))
            print(
                f"{log_prefix} {phase_name}-watchdog tier={tier_name} text={int(text_id)} "
                f"key_seed={int(key_seed)} elapsed={elapsed_s / 60.0:.1f}m "
                f"restarts={int(restarts)} steps={int(steps)} total_steps={int(total_steps)} "
                f"approx_eval_budget={int(round(float(approx_eval_budget)))}",
                flush=True,
            )

    thread = threading.Thread(
        target=_worker,
        name=f"{phase_name}-watchdog",
        daemon=True,
    )
    thread.start()
    return stop_event, thread


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
    stage3_phasec_enabled: bool,
    stage3_phasec_cfg: Dict[str, Any],
    stage3_phasec_start_keys: int,
    stage3_phasec_seed_offset: int,
    stage3_phasec_word_ngram_tiebreak: bool,
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
    phasec_start_checkpoint_path: Path | None = None,
    append_jsonl_row_fn: Callable[[Path, Dict[str, Any]], None] | None = None,
    persist_phasea_gate_snapshot_fn: Callable[[Dict[str, Any]], None] | None = None,
    key_hash_fn: Callable[[Sequence[int]], str] | None = None,
    stage3_phasec_start_policy: str = "source_order",
    stage3_phaseb_family_preservation_policy: str = "off",
    stage3_phaseb_family_view_id: str = "prefix_hamming_le_24",
    stage3_phaseb_family_reserved_slots: int = 0,
    stage3_continue_after_solve: bool = True,
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
    phaseA_best_key_vals: List[int] | None = None
    phaseB_top_n_used = 0
    phaseB_skipped = 0
    phaseB_ran = 0
    phaseB_skip_reason = ""
    phaseB_best_key_vals: List[int] | None = None
    phaseB_selected_unique_end_hash = 0
    phaseB_topk_saved_count = 0
    phaseB_topk_saved_unique_end_hash = 0
    phaseB_topk_rows: List[Dict[str, Any]] = []
    phaseB_topk_saved_summaries: List[Dict[str, Any]] = []

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
    phaseC_enabled_cfg = bool(stage3_phasec_enabled)
    phaseC_enabled_effective = 0
    phaseC_ran = 0
    phaseC_start_keys_used = 0
    phaseB_family_preservation_policy_cfg = str(
        stage3_phaseb_family_preservation_policy
    ).strip().lower()
    if not phaseB_family_preservation_policy_cfg:
        phaseB_family_preservation_policy_cfg = "off"
    phaseB_family_view_id_cfg = str(stage3_phaseb_family_view_id).strip().lower()
    if not phaseB_family_view_id_cfg:
        phaseB_family_view_id_cfg = "prefix_hamming_le_24"
    phaseB_family_reserved_slots_cfg = int(max(0, int(stage3_phaseb_family_reserved_slots)))
    phaseB_family_count_in_top_band = 0
    phaseB_family_preserved_count = 0
    phaseB_family_reservation_applied = 0
    phaseB_downstream_selected_count = 0
    phaseB_downstream_selected_unique_end_hash = 0
    phaseB_downstream_selected_summaries: List[Dict[str, Any]] = []
    phaseC_start_policy_cfg = str(stage3_phasec_start_policy).strip().lower()
    if not phaseC_start_policy_cfg:
        phaseC_start_policy_cfg = "source_order"
    phaseC_steps_cfg = 0
    phaseC_proposals_per_step_cfg = 0
    phaseC_evals = 0
    phaseC_accepts = 0
    phaseC_improves = 0
    phaseC_lexical_requests = 0
    phaseC_lexical_cache_hits = 0
    phaseC_lexical_cache_misses = 0
    phaseC_lexical_tiebreak_decisions = 0
    phaseC_lexical_budget_skips = 0
    phaseC_lexical_threshold_skips = 0
    phaseC_lexical_min_match_cfg = float("nan")
    phaseC_start_summaries: List[Dict[str, Any]] = []
    phaseC_candidate_pool_count = 0
    phaseC_candidate_pool_unique_keys = 0
    phaseC_candidate_pool_unique_end_hash = 0
    phaseC_candidate_pool_rows: List[Dict[str, Any]] = []
    phaseC_candidate_pool_source_counts: Dict[str, int] = {}
    phaseC_start_source_counts: Dict[str, int] = {}
    phaseC_start_unique_end_hash = 0
    phaseC_novel_view_id = ""
    phaseC_anchor_candidate_hash = ""
    phaseC_candidate_pool_eligible_novel_count = 0
    phaseC_candidate_pool_eligible_novel_row_count = 0
    phaseC_candidate_pool_eligible_novel_source_counts: Dict[str, int] = {}
    phaseC_start_eligible_novel_count = 0
    phaseC_selected_novel_challenger_count = 0
    phaseC_eligible_novel_not_selected_count = 0
    phaseC_selected_novel_challenger_hashes: List[str] = []
    phaseC_improved_best = 0
    phaseC_rescue_enabled_cfg = 0
    phaseC_rescue_ran = 0
    phaseC_rescue_starts_attempted = 0
    phaseC_rescue_applied_starts = 0
    phaseC_rescue_target_mode_cfg = "slice_probe"
    phaseC_rescue_selector_mode_cfg = "rescue_shallow_then_search"
    phaseC_rescue_candidates_cfg = 0
    phaseC_rescue_slip_swaps_cfg = 0
    phaseC_rescue_mini_search_steps_cfg = 0
    phaseC_rescue_mini_search_beam_width_cfg = 0
    phaseC_rescue_mini_search_top_symbols_cfg = 0
    phaseC_rescue_mini_search_keep_all_rows_cfg = 0
    phaseC_rescue_polish_steps_cfg = 0
    phaseC_rescue_probe_evals = 0
    phaseC_rescue_evals = 0
    phaseC_rescue_mini_search_evals = 0
    phaseC_rescue_lexical_requests = 0
    phaseC_rescue_lexical_cache_hits = 0
    phaseC_rescue_lexical_cache_misses = 0
    phaseC_rescue_lexical_tiebreak_decisions = 0
    phaseC_rescue_lexical_budget_skips = 0
    phaseC_rescue_lexical_threshold_skips = 0
    phaseC_rescue_anchor_enabled_cfg = 0
    phaseC_rescue_phaseb_topk_min_rank_cfg = 2
    phaseC_rescue_max_starts_cfg = 0
    phaseC_rescue_search_score_max_drop_cfg = 0.0
    phaseC_rescue_eligible_starts = 0
    phaseC_rescue_guard_search_evals = 0
    phaseC_rescue_guard_search_passes = 0
    phaseC_rescue_guard_search_rejects = 0
    phaseC_anchor_lane_starts = 0
    phaseC_challenger_lane_starts = 0
    phaseC_challenger_overtook_anchor_count = 0
    phaseC_final_winner_lane = ""
    phaseC_final_winner_source = ""
    phaseC_checkpoint_rows_written = 0
    phaseC_checkpoint_jsonl_name = (
        Path(phasec_start_checkpoint_path).name
        if phasec_start_checkpoint_path is not None
        else ""
    )

    def _candidate_hash(
        *,
        key_vals: Sequence[int],
        existing_hash: str = "",
    ) -> str:
        existing_hash_s = str(existing_hash or "").strip()
        if existing_hash_s:
            return existing_hash_s
        if callable(key_hash_fn):
            try:
                hashed = str(key_hash_fn(key_vals)).strip()
            except Exception:
                hashed = ""
            if hashed:
                return hashed
        return ",".join(str(int(v)) for v in key_vals)

    def _count_source_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for row in rows:
            source = str(row.get("source", "")).strip()
            if not source:
                continue
            counts[source] = int(counts.get(source, 0)) + 1
        return counts

    def _append_unique_start_row(
        *,
        out_rows: List[Dict[str, Any]],
        seen_starts: set[tuple[int, ...]],
        candidate_row: Mapping[str, Any],
        selection_bucket: str = "legacy_fill",
        selected_by_novel_policy: bool = False,
        selected_by_anchor_family_policy: bool = False,
        selected_by_phaseb_topk_anchor_policy: bool = False,
        eligible_novel_challenger: bool = False,
        novelty_distance_to_anchor: int | None = None,
        novelty_min_distance_to_selected_challenger: int | None = None,
    ) -> bool:
        candidate_key_t = tuple(map(int, candidate_row.get("key", [])))
        if candidate_key_t in seen_starts:
            return False
        seen_starts.add(candidate_key_t)
        row = dict(candidate_row)
        row["selection_bucket"] = str(selection_bucket)
        row["selected_by_novel_policy"] = int(1 if bool(selected_by_novel_policy) else 0)
        row["selected_by_anchor_family_policy"] = int(
            1 if bool(selected_by_anchor_family_policy) else 0
        )
        row["selected_by_phaseb_topk_anchor_policy"] = int(
            1 if bool(selected_by_phaseb_topk_anchor_policy) else 0
        )
        row["eligible_novel_challenger"] = int(
            1 if bool(eligible_novel_challenger) else 0
        )
        row["novelty_distance_to_anchor"] = (
            int(novelty_distance_to_anchor)
            if novelty_distance_to_anchor is not None
            else None
        )
        row["novelty_min_distance_to_selected_challenger"] = (
            int(novelty_min_distance_to_selected_challenger)
            if novelty_min_distance_to_selected_challenger is not None
            else None
        )
        out_rows.append(row)
        return True

    def _build_phasec_start_records(
        *,
        candidate_pool_records: Sequence[Dict[str, Any]],
        candidate_buckets: Mapping[str, List[Dict[str, Any]]],
        phasec_best_source: str,
        phasec_start_policy: str,
        stage3_phasec_start_keys: int,
    ) -> Dict[str, Any]:
        start_limit = int(max(0, int(stage3_phasec_start_keys)))
        novelty_view_id = "prefix_hamming_le_24"
        novelty_view = find_family_view(novelty_view_id)
        anchor_candidate_hash = ""
        candidate_pool_rows = [
            dict(
                dict(row),
                eligible_novel_challenger=int(
                    row.get("eligible_novel_challenger", 0) or 0
                ),
                novelty_distance_to_anchor=row.get(
                    "novelty_distance_to_anchor",
                    None,
                ),
                selected_by_anchor_family_policy=int(
                    row.get("selected_by_anchor_family_policy", 0) or 0
                ),
                selected_by_phaseb_topk_anchor_policy=int(
                    row.get("selected_by_phaseb_topk_anchor_policy", 0) or 0
                ),
                selected_by_phasec_start=int(
                    row.get("selected_by_phasec_start", 0) or 0
                ),
            )
            for row in list(candidate_pool_records or [])
        ]
        eligible_novel_rows: List[Dict[str, Any]] = []
        eligible_novel_hashes: set[str] = set()
        eligible_novel_source_counts: Dict[str, int] = {}
        selected_novel_hashes: List[str] = []
        selected_start_novel_hashes: set[str] = set()

        def _row_is_anchor(
            row: Mapping[str, Any],
            *,
            anchor_row: Mapping[str, Any],
        ) -> bool:
            row_hash = str(row.get("candidate_hash", ""))
            anchor_hash = str(anchor_row.get("candidate_hash", ""))
            if row_hash and anchor_hash and row_hash == anchor_hash:
                return True
            row_key = tuple(map(int, row.get("key", [])))
            anchor_key = tuple(map(int, anchor_row.get("key", [])))
            return bool(row_key and anchor_key and row_key == anchor_key)

        def _novelty_distance(
            lhs: Mapping[str, Any],
            rhs: Mapping[str, Any],
        ) -> int | None:
            if novelty_view is None:
                return None
            return family_view_distance(
                lhs,
                rhs,
                family_view=novelty_view,
                columns=int(max(1, int(tier_columns))),
            )

        def _is_eligible_novel(
            row: Mapping[str, Any],
            *,
            anchor_row: Mapping[str, Any],
            selected_novel_rows: Sequence[Mapping[str, Any]] | None = None,
        ) -> tuple[bool, int | None, int | None]:
            if novelty_view is None:
                return False, None, None
            if _row_is_anchor(row, anchor_row=anchor_row):
                return False, None, None
            row_hash = str(row.get("candidate_hash", ""))
            anchor_hash = str(anchor_row.get("candidate_hash", ""))
            if row_hash and anchor_hash and row_hash == anchor_hash:
                return False, None, None
            same_family_vs_anchor = rows_share_family(
                row,
                anchor_row,
                family_view=novelty_view,
                columns=int(max(1, int(tier_columns))),
            )
            distance_to_anchor = _novelty_distance(row, anchor_row)
            if same_family_vs_anchor is not False:
                return False, distance_to_anchor, None
            min_distance_to_selected: int | None = None
            for selected_row in list(selected_novel_rows or []):
                row_same_hash = str(row.get("candidate_hash", ""))
                selected_hash = str(selected_row.get("candidate_hash", ""))
                if row_same_hash and selected_hash and row_same_hash == selected_hash:
                    return False, distance_to_anchor, min_distance_to_selected
                same_family_vs_selected = rows_share_family(
                    row,
                    selected_row,
                    family_view=novelty_view,
                    columns=int(max(1, int(tier_columns))),
                )
                distance_vs_selected = _novelty_distance(row, selected_row)
                if distance_vs_selected is not None:
                    if min_distance_to_selected is None:
                        min_distance_to_selected = int(distance_vs_selected)
                    else:
                        min_distance_to_selected = int(
                            min(int(min_distance_to_selected), int(distance_vs_selected))
                        )
                if same_family_vs_selected is not False:
                    return False, distance_to_anchor, min_distance_to_selected
            return True, distance_to_anchor, min_distance_to_selected

        def _is_anchor_family_match(
            row: Mapping[str, Any],
            *,
            anchor_row: Mapping[str, Any],
        ) -> tuple[bool, int | None]:
            if novelty_view is None:
                return False, None
            if _row_is_anchor(row, anchor_row=anchor_row):
                return False, None
            distance_to_anchor = _novelty_distance(row, anchor_row)
            same_family_vs_anchor = rows_share_family(
                row,
                anchor_row,
                family_view=novelty_view,
                columns=int(max(1, int(tier_columns))),
            )
            return bool(same_family_vs_anchor is True), distance_to_anchor

        def _legacy_fill(
            *,
            out_rows: List[Dict[str, Any]],
            seen_starts: set[tuple[int, ...]],
            source_names: Sequence[str],
            anchor_row: Mapping[str, Any] | None,
        ) -> None:
            for source_name in source_names:
                for bucket_row in candidate_buckets.get(str(source_name), []):
                    eligible_novel = False
                    distance_to_anchor: int | None = None
                    if anchor_row is not None:
                        eligible_novel, distance_to_anchor, _ = _is_eligible_novel(
                            bucket_row,
                            anchor_row=anchor_row,
                        )
                    _append_unique_start_row(
                        out_rows=out_rows,
                        seen_starts=seen_starts,
                        candidate_row=bucket_row,
                        selection_bucket="legacy_fill",
                        selected_by_novel_policy=False,
                        eligible_novel_challenger=bool(eligible_novel),
                        novelty_distance_to_anchor=distance_to_anchor,
                        novelty_min_distance_to_selected_challenger=None,
                    )
                    if len(out_rows) >= start_limit:
                        break
                if len(out_rows) >= start_limit:
                    break

        if start_limit <= 0:
            return dict(
                rows=[],
                candidate_pool_rows=[dict(row) for row in candidate_pool_rows],
                novelty_view_id=novelty_view_id,
                anchor_candidate_hash="",
                candidate_pool_eligible_novel_count=0,
                candidate_pool_eligible_novel_row_count=0,
                candidate_pool_eligible_novel_source_counts={},
                start_eligible_novel_count=0,
                selected_novel_challenger_count=0,
                eligible_novel_not_selected_count=0,
                selected_novel_challenger_hashes=[],
            )
        policy = str(phasec_start_policy).strip().lower()
        start_records: List[Dict[str, Any]] = []
        seen_starts: set[tuple[int, ...]] = set()
        anchor_row: Dict[str, Any] | None = None
        for anchor_row in candidate_buckets.get(str(phasec_best_source), []):
            if _append_unique_start_row(
                out_rows=start_records,
                seen_starts=seen_starts,
                candidate_row=anchor_row,
                selection_bucket="anchor",
            ):
                anchor_row = dict(start_records[-1])
                anchor_candidate_hash = str(anchor_row.get("candidate_hash", ""))
                break
        if anchor_row is not None:
            candidate_pool_rows = []
            for pool_row in candidate_pool_records:
                eligible_novel, distance_to_anchor, _ = _is_eligible_novel(
                    pool_row,
                    anchor_row=anchor_row,
                )
                candidate_pool_rows.append(
                    dict(
                        dict(pool_row),
                        eligible_novel_challenger=int(
                            1 if bool(eligible_novel) else 0
                        ),
                        novelty_distance_to_anchor=(
                            int(distance_to_anchor)
                            if distance_to_anchor is not None
                            else None
                        ),
                    )
                )
                if not eligible_novel:
                    continue
                eligible_novel_rows.append(
                    dict(
                        dict(pool_row),
                        novelty_distance_to_anchor=(
                            int(distance_to_anchor)
                            if distance_to_anchor is not None
                            else None
                        ),
                    )
                )
                row_hash = str(pool_row.get("candidate_hash", ""))
                if row_hash:
                    eligible_novel_hashes.add(row_hash)
                source_name = str(pool_row.get("source", "")).strip()
                if source_name:
                    eligible_novel_source_counts[source_name] = int(
                        eligible_novel_source_counts.get(source_name, 0)
                    ) + 1
        if len(start_records) >= start_limit:
            selected_start_hashes = {
                str(row.get("candidate_hash", ""))
                for row in start_records
                if str(row.get("candidate_hash", ""))
            }
            return dict(
                rows=start_records,
                candidate_pool_rows=[
                    dict(
                        row,
                        selected_by_phasec_start=int(
                            1
                            if str(row.get("candidate_hash", "")) in selected_start_hashes
                            else 0
                        ),
                    )
                    for row in candidate_pool_rows
                ],
                novelty_view_id=novelty_view_id,
                anchor_candidate_hash=str(anchor_candidate_hash),
                candidate_pool_eligible_novel_count=int(len(eligible_novel_hashes)),
                candidate_pool_eligible_novel_row_count=int(len(eligible_novel_rows)),
                candidate_pool_eligible_novel_source_counts=dict(
                    eligible_novel_source_counts
                ),
                start_eligible_novel_count=0,
                selected_novel_challenger_count=0,
                eligible_novel_not_selected_count=int(len(eligible_novel_hashes)),
                selected_novel_challenger_hashes=[],
            )
        if policy == "source_order":
            _legacy_fill(
                out_rows=start_records,
                seen_starts=seen_starts,
                source_names=("phaseB_topk", "phaseA_selected"),
                anchor_row=anchor_row,
            )
        elif policy == "balanced_sources_v1":
            source_order = ("phaseB_topk", "phaseA_selected")
            source_offsets = {str(source_name): 0 for source_name in source_order}
            while len(start_records) < start_limit:
                progressed = False
                for source_name in source_order:
                    bucket = candidate_buckets.get(str(source_name), [])
                    offset = int(source_offsets[str(source_name)])
                    while offset < len(bucket):
                        bucket_row = bucket[offset]
                        offset += 1
                        eligible_novel = False
                        distance_to_anchor: int | None = None
                        if anchor_row is not None:
                            eligible_novel, distance_to_anchor, _ = _is_eligible_novel(
                                bucket_row,
                                anchor_row=anchor_row,
                            )
                        if _append_unique_start_row(
                            out_rows=start_records,
                            seen_starts=seen_starts,
                            candidate_row=bucket_row,
                            selection_bucket="balanced_fill",
                            selected_by_novel_policy=False,
                            eligible_novel_challenger=bool(eligible_novel),
                            novelty_distance_to_anchor=distance_to_anchor,
                            novelty_min_distance_to_selected_challenger=None,
                        ):
                            progressed = True
                            break
                    source_offsets[str(source_name)] = int(offset)
                    if len(start_records) >= start_limit:
                        break
                if not progressed:
                    break
        elif policy == "novel_challenger_v1":
            reserved_limit = int(max(0, min(int(start_limit - len(start_records)), 2)))
            selected_novel_rows: List[Dict[str, Any]] = []
            if anchor_row is not None and reserved_limit > 0:
                for pool_row in candidate_pool_records:
                    eligible_novel, distance_to_anchor, min_distance_to_selected = _is_eligible_novel(
                        pool_row,
                        anchor_row=anchor_row,
                        selected_novel_rows=selected_novel_rows,
                    )
                    if not eligible_novel:
                        continue
                    if _append_unique_start_row(
                        out_rows=start_records,
                        seen_starts=seen_starts,
                        candidate_row=pool_row,
                        selection_bucket="novel_reserved",
                        selected_by_novel_policy=True,
                        eligible_novel_challenger=True,
                        novelty_distance_to_anchor=distance_to_anchor,
                        novelty_min_distance_to_selected_challenger=min_distance_to_selected,
                    ):
                        selected_row = dict(start_records[-1])
                        selected_novel_rows.append(selected_row)
                        selected_hash = str(selected_row.get("candidate_hash", ""))
                        if selected_hash:
                            selected_novel_hashes.append(selected_hash)
                        if len(selected_novel_rows) >= reserved_limit:
                            break
            _legacy_fill(
                out_rows=start_records,
                seen_starts=seen_starts,
                source_names=("phaseB_topk", "phaseA_selected"),
                anchor_row=anchor_row,
            )
        elif policy == "anchor_family_reserved_v1":
            reserved_limit = int(max(0, min(int(start_limit - len(start_records)), 2)))
            reserved_count = 0
            if anchor_row is not None and reserved_limit > 0:
                for pool_row in candidate_pool_records:
                    same_family, distance_to_anchor = _is_anchor_family_match(
                        pool_row,
                        anchor_row=anchor_row,
                    )
                    if not same_family:
                        continue
                    if _append_unique_start_row(
                        out_rows=start_records,
                        seen_starts=seen_starts,
                        candidate_row=pool_row,
                        selection_bucket="anchor_family_reserved",
                        selected_by_novel_policy=False,
                        selected_by_anchor_family_policy=True,
                        eligible_novel_challenger=False,
                        novelty_distance_to_anchor=distance_to_anchor,
                        novelty_min_distance_to_selected_challenger=None,
                    ):
                        reserved_count += 1
                        if reserved_count >= reserved_limit:
                            break
            _legacy_fill(
                out_rows=start_records,
                seen_starts=seen_starts,
                source_names=("phaseB_topk", "phaseA_selected"),
                anchor_row=anchor_row,
            )
        elif policy == "phaseb_topk_anchor_swap_v1":
            topk_anchor_row: Dict[str, Any] | None = None
            for pool_row in candidate_buckets.get("phaseB_topk", []):
                pool_hash = str(pool_row.get("candidate_hash", "") or "")
                anchor_hash = str(anchor_row.get("candidate_hash", "") or "")
                if pool_hash and anchor_hash and pool_hash == anchor_hash:
                    continue
                topk_anchor_row = dict(pool_row)
                break
            if anchor_row is not None and topk_anchor_row is not None:
                start_records = []
                seen_starts = set()
                _append_unique_start_row(
                    out_rows=start_records,
                    seen_starts=seen_starts,
                    candidate_row=topk_anchor_row,
                    selection_bucket="phaseb_topk_anchor",
                    selected_by_novel_policy=False,
                    selected_by_anchor_family_policy=False,
                    selected_by_phaseb_topk_anchor_policy=True,
                )
                _append_unique_start_row(
                    out_rows=start_records,
                    seen_starts=seen_starts,
                    candidate_row=anchor_row,
                    selection_bucket="anchor_demoted",
                    selected_by_novel_policy=False,
                    selected_by_anchor_family_policy=False,
                    selected_by_phaseb_topk_anchor_policy=False,
                )
            _legacy_fill(
                out_rows=start_records,
                seen_starts=seen_starts,
                source_names=("phaseB_topk", "phaseA_selected"),
                anchor_row=anchor_row,
            )
        else:
            raise ValueError(f"Unknown Phase-C start policy: {phasec_start_policy}")
        start_eligible_novel_hashes = {
            str(row.get("candidate_hash", ""))
            for row in start_records
            if int(row.get("eligible_novel_challenger", 0)) == 1
            and str(row.get("candidate_hash", ""))
        }
        selected_start_hashes = {
            str(row.get("candidate_hash", ""))
            for row in start_records
            if str(row.get("candidate_hash", ""))
        }
        return dict(
            rows=start_records,
            candidate_pool_rows=[
                dict(
                    row,
                    selected_by_phasec_start=int(
                        1
                        if str(row.get("candidate_hash", "")) in selected_start_hashes
                        else 0
                    ),
                )
                for row in candidate_pool_rows
            ],
            novelty_view_id=novelty_view_id,
            anchor_candidate_hash=str(anchor_candidate_hash),
            candidate_pool_eligible_novel_count=int(len(eligible_novel_hashes)),
            candidate_pool_eligible_novel_row_count=int(len(eligible_novel_rows)),
            candidate_pool_eligible_novel_source_counts=dict(
                eligible_novel_source_counts
            ),
            start_eligible_novel_count=int(len(start_eligible_novel_hashes)),
            selected_novel_challenger_count=int(len(set(selected_novel_hashes))),
            eligible_novel_not_selected_count=int(
                max(0, len(eligible_novel_hashes) - len(start_eligible_novel_hashes))
            ),
            selected_novel_challenger_hashes=list(dict.fromkeys(selected_novel_hashes)),
        )

    def _preserve_phaseb_rows_for_downstream(
        *,
        ranked_rows: Sequence[Mapping[str, Any]],
        selected_rows: Sequence[Mapping[str, Any]],
        family_preservation_policy: str,
        family_view_id: str,
        family_reserved_slots: int,
    ) -> Dict[str, Any]:
        target_count = int(len(selected_rows))
        if target_count <= 0:
            return dict(
                rows=[],
                family_count_in_top_band=0,
                family_preserved_count=0,
                reservation_applied=0,
                downstream_selected_unique_end_hash=0,
                summaries=[],
            )

        view = find_family_view(str(family_view_id))
        annotated_rows: List[Dict[str, Any]] = []
        for rank, row in enumerate(ranked_rows, start=1):
            end_key = list(map(int, row.get("end_key", [])))
            annotated_rows.append(
                dict(
                    row_id=f"phaseb_ranked:{int(rank)}",
                    phaseb_rank=int(rank),
                    key_idx=end_key,
                    candidate_hash=_candidate_hash(
                        key_vals=end_key,
                        existing_hash=str(row.get("end_hash", "")),
                    ),
                    original_row=dict(row),
                )
            )

        if not annotated_rows:
            return dict(
                rows=[dict(row) for row in selected_rows],
                family_count_in_top_band=0,
                family_preserved_count=0,
                reservation_applied=0,
                downstream_selected_unique_end_hash=int(
                    len({str(row.get("end_hash", "")) for row in selected_rows})
                ),
                summaries=[],
            )

        family_assignments: Dict[str, str] = {}
        if view is not None:
            family_assignments, _ = cluster_family_ids(
                annotated_rows,
                family_view=view,
                columns=int(tier_columns),
            )
        top_band_rows = list(annotated_rows[:target_count])
        family_count_in_top_band = int(
            len(
                {
                    str(family_assignments[str(row["row_id"])])
                    for row in top_band_rows
                    if str(row["row_id"]) in family_assignments
                }
            )
        )

        policy = str(family_preservation_policy).strip().lower()
        if policy == "off":
            preserved_rows = list(top_band_rows)
            reservation_applied = 0
        elif policy not in {"reserve_by_family_v1", "reinforce_top_family_v1"}:
            raise ValueError(
                f"Unknown Phase-B family preservation policy: {family_preservation_policy}"
            )
        else:
            if view is None:
                raise ValueError(
                    f"Unknown Phase-B family view id: {family_view_id}"
                )
            reserved_slots = int(max(0, int(family_reserved_slots)))
            preserved_rows = []
            preserved_row_ids: set[str] = set()
            preserved_family_ids: set[str] = set()
            reservation_applied = 0

            top_row = annotated_rows[0]
            preserved_rows.append(top_row)
            preserved_row_ids.add(str(top_row["row_id"]))
            top_family_id = family_assignments.get(str(top_row["row_id"]))
            if top_family_id is not None:
                preserved_family_ids.add(str(top_family_id))

            if reserved_slots > 0:
                if policy == "reserve_by_family_v1":
                    for row in annotated_rows[1:]:
                        if int(len(preserved_rows)) >= int(1 + reserved_slots):
                            break
                        family_id = family_assignments.get(str(row["row_id"]))
                        if family_id is None:
                            continue
                        family_id_s = str(family_id)
                        if family_id_s in preserved_family_ids:
                            continue
                        preserved_rows.append(row)
                        preserved_row_ids.add(str(row["row_id"]))
                        preserved_family_ids.add(family_id_s)
                        reservation_applied = 1
                else:
                    top_family_id_s = str(top_family_id) if top_family_id is not None else ""
                    for row in annotated_rows[1:]:
                        if int(len(preserved_rows)) >= int(1 + reserved_slots):
                            break
                        family_id = family_assignments.get(str(row["row_id"]))
                        if family_id is None:
                            continue
                        family_id_s = str(family_id)
                        if not top_family_id_s or family_id_s != top_family_id_s:
                            continue
                        row_id = str(row["row_id"])
                        if row_id in preserved_row_ids:
                            continue
                        preserved_rows.append(row)
                        preserved_row_ids.add(row_id)
                        preserved_family_ids.add(family_id_s)
                        reservation_applied = 1

            for row in annotated_rows:
                if int(len(preserved_rows)) >= int(target_count):
                    break
                row_id = str(row["row_id"])
                if row_id in preserved_row_ids:
                    continue
                preserved_rows.append(row)
                preserved_row_ids.add(row_id)

        preserved_rows = list(preserved_rows[:target_count])
        preserved_families = {
            str(family_assignments[str(row["row_id"])])
            for row in preserved_rows
            if str(row["row_id"]) in family_assignments
        }
        summaries: List[Dict[str, Any]] = []
        for downstream_rank, row in enumerate(preserved_rows, start=1):
            row_id = str(row["row_id"])
            summaries.append(
                dict(
                    downstream_rank=int(downstream_rank),
                    phaseb_rank=int(row["phaseb_rank"]),
                    end_hash=str(row["candidate_hash"]),
                    family_id=str(family_assignments.get(row_id, "")),
                )
            )
        return dict(
            rows=[dict(row["original_row"]) for row in preserved_rows],
            family_count_in_top_band=int(family_count_in_top_band),
            family_preserved_count=int(len(preserved_families)),
            reservation_applied=int(reservation_applied),
            downstream_selected_unique_end_hash=int(
                len({str(row["candidate_hash"]) for row in preserved_rows})
            ),
            summaries=summaries,
        )

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
        phaseA_best_key_vals = list(map(int, best3_key))
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
        gate_skip = bool(phaseA_solved) and not bool(stage3_continue_after_solve)
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
            phaseB_family_preservation_policy=str(
                phaseB_family_preservation_policy_cfg
            ),
            phaseB_family_view_id=str(phaseB_family_view_id_cfg),
            phaseB_family_reserved_slots=int(phaseB_family_reserved_slots_cfg),
            phaseB_family_count_in_top_band=int(phaseB_family_count_in_top_band),
            phaseB_family_preserved_count=int(phaseB_family_preserved_count),
            phaseB_family_reservation_applied=int(phaseB_family_reservation_applied),
            phaseB_selected_unique_end_hash=int(phaseB_selected_unique_end_hash),
            phaseB_downstream_selected_count=int(phaseB_downstream_selected_count),
            phaseB_downstream_selected_unique_end_hash=int(
                phaseB_downstream_selected_unique_end_hash
            ),
            phaseB_downstream_selected_summaries=[
                dict(row) for row in phaseB_downstream_selected_summaries
            ],
            phaseB_topk_saved_count=int(phaseB_topk_saved_count),
            phaseB_topk_saved_unique_end_hash=int(phaseB_topk_saved_unique_end_hash),
            phaseC_enabled_cfg=int(1 if bool(phaseC_enabled_cfg) else 0),
            phaseC_enabled_effective=int(phaseC_enabled_effective),
            phaseC_ran=int(phaseC_ran),
            phaseC_start_keys_used=int(phaseC_start_keys_used),
            phaseC_steps_cfg=int(phaseC_steps_cfg),
            phaseC_proposals_per_step_cfg=int(phaseC_proposals_per_step_cfg),
            phaseC_evals=int(phaseC_evals),
            phaseC_accepts=int(phaseC_accepts),
            phaseC_improves=int(phaseC_improves),
            phaseC_candidate_pool_count=int(phaseC_candidate_pool_count),
            phaseC_candidate_pool_unique_keys=int(phaseC_candidate_pool_unique_keys),
            phaseC_candidate_pool_unique_end_hash=int(
                phaseC_candidate_pool_unique_end_hash
            ),
            phaseC_candidate_pool_source_counts=dict(phaseC_candidate_pool_source_counts),
            phaseC_start_source_counts=dict(phaseC_start_source_counts),
            phaseC_start_unique_end_hash=int(phaseC_start_unique_end_hash),
            phaseC_improved_best=int(phaseC_improved_best),
            phaseC_checkpoint_jsonl_name=str(phaseC_checkpoint_jsonl_name),
            phaseC_checkpoint_rows_written=int(phaseC_checkpoint_rows_written),
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
    phaseB_ranked_unique_rows = list(selected)
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
    phaseB_selected_unique_end_hash = int(
        len(
            {
                _candidate_hash(
                    key_vals=list(map(int, row.get("end_key", []))),
                    existing_hash=str(row.get("end_hash", "")),
                )
                for row in selected
                if len(list(map(int, row.get("end_key", [])))) == int(key_len)
            }
        )
    )
    phaseA_selected_rows = list(selected)
    phaseB_family_preservation = _preserve_phaseb_rows_for_downstream(
        ranked_rows=phaseB_ranked_unique_rows,
        selected_rows=phaseA_selected_rows,
        family_preservation_policy=str(phaseB_family_preservation_policy_cfg),
        family_view_id=str(phaseB_family_view_id_cfg),
        family_reserved_slots=int(phaseB_family_reserved_slots_cfg),
    )
    phaseA_selected_rows = list(phaseB_family_preservation["rows"])
    phaseB_family_count_in_top_band = int(
        phaseB_family_preservation["family_count_in_top_band"]
    )
    phaseB_family_preserved_count = int(
        phaseB_family_preservation["family_preserved_count"]
    )
    phaseB_family_reservation_applied = int(
        phaseB_family_preservation["reservation_applied"]
    )
    phaseB_downstream_selected_count = int(len(phaseA_selected_rows))
    phaseB_downstream_selected_unique_end_hash = int(
        phaseB_family_preservation["downstream_selected_unique_end_hash"]
    )
    phaseB_downstream_selected_summaries = list(
        phaseB_family_preservation["summaries"]
    )

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
        f"selected_final={selected_final_n} "
        f"selected_unique_end_hash={int(phaseB_selected_unique_end_hash)}",
        flush=True,
    )
    print(
        f"{log_prefix} stage3-phaseB-family tier={tier_name} text={text_id} key_seed={key_seed} "
        f"policy={phaseB_family_preservation_policy_cfg} "
        f"view={phaseB_family_view_id_cfg} "
        f"reserved_slots={int(phaseB_family_reserved_slots_cfg)} "
        f"top_band_families={int(phaseB_family_count_in_top_band)} "
        f"preserved_families={int(phaseB_family_preserved_count)} "
        f"applied={int(phaseB_family_reservation_applied)} "
        f"downstream_selected={int(phaseB_downstream_selected_count)} "
        f"downstream_unique_end_hash={int(phaseB_downstream_selected_unique_end_hash)}",
        flush=True,
    )
    if callable(persist_phasea_gate_snapshot_fn):
        persist_phasea_gate_snapshot_fn(
            build_phasea_gate_snapshot(
                tier_name=str(tier_name),
                text_id=int(text_id),
                key_seed=int(key_seed),
                phaseA_rows=phaseA_rows,
                phaseA_selected_rows=phaseA_selected_rows,
                gate_delta=float(gate_delta),
                gate_end_gain=float(gate_end_gain),
                phaseB_ran=int(phaseB_ran),
                phaseB_ready_reason=str(phaseB_ready_reason),
                phaseB_top_n_used=int(phaseB_top_n_used),
                phaseB_selected_unique_end_hash=int(phaseB_selected_unique_end_hash),
                phaseB_family_preservation_policy=str(
                    phaseB_family_preservation_policy_cfg
                ),
                phaseB_family_view_id=str(phaseB_family_view_id_cfg),
                phaseB_family_reserved_slots=int(phaseB_family_reserved_slots_cfg),
                phaseB_family_count_in_top_band=int(phaseB_family_count_in_top_band),
                phaseB_family_preserved_count=int(phaseB_family_preserved_count),
                phaseB_family_reservation_applied=int(
                    phaseB_family_reservation_applied
                ),
                phaseB_downstream_selected_count=int(
                    phaseB_downstream_selected_count
                ),
                phaseB_downstream_selected_unique_end_hash=int(
                    phaseB_downstream_selected_unique_end_hash
                ),
            )
        )

    if selected:
        phaseB_init = [list(map(int, row["end_key"])) for row in selected]
        phaseB_cfg = dict(solver_stage3_cfg)
        phaseB_cfg.update(dict(stage3_phaseB_cfg))
        phaseB_cfg["restarts"] = int(max(1, len(phaseB_init)))
        phaseB_cfg["seed_restarts"] = 0
        phaseB_cfg["seed"] = int(base_seed + 900001)
        phaseB_plan = _approx_phase_eval_budget(
            restarts=int(phaseB_cfg.get("restarts", 1) or 1),
            steps=int(phaseB_cfg.get("steps", 0) or 0),
            inner_batch=int(phaseB_cfg.get("inner_batch", 0) or 0),
            col_every=int(phaseB_cfg.get("col_every", 0) or 0),
            col_batch=int(phaseB_cfg.get("col_batch", 0) or 0),
        )
        print(
            f"{log_prefix} stage3-phaseB-plan tier={tier_name} text={text_id} key_seed={key_seed} "
            f"restarts={int(phaseB_plan['restarts'])} steps={int(phaseB_plan['steps'])} "
            f"total_steps={int(phaseB_plan['total_steps'])} "
            f"inner_batch={int(phaseB_cfg.get('inner_batch', 0) or 0)} "
            f"col_every={int(phaseB_cfg.get('col_every', 0) or 0)} "
            f"col_batch={int(phaseB_cfg.get('col_batch', 0) or 0)} "
            f"approx_evals_per_step={float(phaseB_plan['evals_per_step']):.1f} "
            f"approx_eval_budget={int(round(float(phaseB_plan['approx_eval_budget'])))}",
            flush=True,
        )
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
        watchdog_stop, watchdog_thread = _start_phase_watchdog(
            interval_seconds=float(stage3_heartbeat_seconds),
            phase_name="stage3-phaseB",
            tier_name=str(tier_name),
            text_id=int(text_id),
            key_seed=int(key_seed),
            restarts=int(phaseB_plan["restarts"]),
            steps=int(phaseB_plan["steps"]),
            total_steps=int(phaseB_plan["total_steps"]),
            approx_eval_budget=float(phaseB_plan["approx_eval_budget"]),
            start_ts=float(t_run),
            log_prefix=str(log_prefix),
        )
        try:
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
        finally:
            watchdog_stop.set()
            watchdog_thread.join(timeout=0.1)
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
        print(
            f"{log_prefix} stage3-phaseB-finish tier={tier_name} text={text_id} key_seed={key_seed} "
            f"seconds={dt_run:.1f} evals={int(ev_b)} "
            f"best_match={fmt_finite_float_fn(best_b_match)} "
            f"best_score={fmt_finite_float_fn(best_b_score)}",
            flush=True,
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
        phaseB_best_key_vals = list(map(int, best_b_key))
        stage3_span_full_eval_total += float(span_b["total"])
        stage3_span_full_eval_active += float(span_b["active"])
        stage3_span_full_eval_skipped += float(span_b["skipped"])
        stage3_span_full_seconds_total += float(span_b["seconds_total"])
        stage3_span_full_seconds_active += float(span_b["seconds_active"])
        topk_before = int(len(stage3_topk_payload))
        append_stage3_topk_from_kaeding_fn(
            payload=stage3_topk_payload,
            kaeding_obj=kaeding_b,
            key_len=int(key_len),
            full_cipher=full_cipher,
            ciphertext=np.asarray(ct_idx, dtype=np.uint8),
            scorer_full_runtime=scorer_full_runtime,
            target_plaintext=np.asarray(pt_idx, dtype=np.uint8),
        )
        phaseB_topk_rows = [dict(row) for row in stage3_topk_payload[topk_before:]]
        phaseB_topk_saved_count = int(len(phaseB_topk_rows))
        phaseB_topk_saved_unique_end_hash = int(
            len(
                {
                    _candidate_hash(
                        key_vals=list(map(int, row.get("key_idx", []))),
                        existing_hash=str(row.get("end_hash", "")),
                    )
                    for row in phaseB_topk_rows
                    if len(list(map(int, row.get("key_idx", [])))) == int(key_len)
                }
            )
        )
        phaseB_topk_saved_summaries = []
        for saved_rank, row in enumerate(phaseB_topk_rows, start=1):
            end_key = list(map(int, row.get("key_idx", [])))
            candidate_hash = _candidate_hash(
                key_vals=end_key,
                existing_hash=str(row.get("end_hash", "")),
            )
            phaseB_topk_saved_summaries.append(
                dict(
                    saved_rank=int(saved_rank),
                    stage3_topk_rank=int(row.get("rank", saved_rank) or saved_rank),
                    candidate_hash=str(candidate_hash),
                    end_hash=str(candidate_hash),
                    source=str(row.get("source", "") or ""),
                    match_ratio=float(row.get("match_ratio", float("nan"))),
                )
            )

        stage_rows.append(
            dict(
                tier=tier_name,
                text_id=int(text_id),
                key_seed=int(key_seed),
                stage="stage3_phaseB",
                phaseB_top_n_used=int(phaseB_top_n_used),
                phaseB_selected_unique_end_hash=int(phaseB_selected_unique_end_hash),
                phaseB_topk_saved_count=int(phaseB_topk_saved_count),
                phaseB_topk_saved_unique_end_hash=int(
                    phaseB_topk_saved_unique_end_hash
                ),
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

    phaseC_cfg = dict(stage3_phasec_cfg or {})
    phaseC_steps_cfg = int(max(0, int(phaseC_cfg.get("steps", 0) or 0)))
    phaseC_proposals_per_step_cfg = int(
        max(1, int(phaseC_cfg.get("proposals_per_step", 1) or 1))
    )
    phaseC_three_cycle_prob = float(
        max(0.0, min(1.0, float(phaseC_cfg.get("three_cycle_prob", 0.0) or 0.0)))
    )
    phaseC_lexical_min_match = float(
        max(0.0, min(1.0, float(phaseC_cfg.get("lexical_min_match", 0.72) or 0.0)))
    )
    phaseC_lexical_min_match_cfg = float(phaseC_lexical_min_match)
    phaseC_lexical_match_tie_eps = float(
        max(0.0, float(phaseC_cfg.get("lexical_match_tie_eps", 0.01) or 0.0))
    )
    phaseC_lexical_score_tie_eps = float(
        max(0.0, float(phaseC_cfg.get("lexical_score_tie_eps", 0.002) or 0.0))
    )
    raw_phaseC_lexical_max_calls = phaseC_cfg.get("lexical_max_calls", 256)
    phaseC_lexical_max_calls = int(max(0, int(raw_phaseC_lexical_max_calls or 0)))
    phaseC_rescue_enabled_cfg = int(1 if bool(phaseC_cfg.get("rescue_enabled", False)) else 0)
    phaseC_rescue_target_mode_cfg = str(
        phaseC_cfg.get("rescue_target_mode", "slice_probe") or "slice_probe"
    ).strip().lower()
    phaseC_rescue_selector_mode_cfg = str(
        phaseC_cfg.get(
            "rescue_selector_mode",
            "rescue_shallow_then_search",
        )
        or "rescue_shallow_then_search"
    ).strip().lower()
    phaseC_rescue_anchor_enabled_cfg = int(
        1 if bool(phaseC_cfg.get("rescue_anchor_enabled", False)) else 0
    )
    phaseC_rescue_phaseb_topk_min_rank_cfg = int(
        max(1, int(phaseC_cfg.get("rescue_phaseb_topk_min_rank", 2) or 0))
    )
    phaseC_rescue_max_starts_cfg = int(
        max(
            0,
            int(
                phaseC_cfg.get(
                    "rescue_max_starts",
                    int(max(0, int(stage3_phasec_start_keys))),
                )
                or 0
            ),
        )
    )
    phaseC_rescue_search_score_max_drop_cfg = float(
        max(0.0, float(phaseC_cfg.get("rescue_search_score_max_drop", 0.0) or 0.0))
    )
    phaseC_rescue_candidates_cfg = int(
        max(0, int(phaseC_cfg.get("rescue_candidates", 0) or 0))
    )
    phaseC_rescue_slip_swaps_cfg = int(
        max(0, int(phaseC_cfg.get("rescue_slip_swaps", 0) or 0))
    )
    phaseC_rescue_mini_search_steps_cfg = int(
        max(0, int(phaseC_cfg.get("rescue_mini_search_steps", 2) or 0))
    )
    phaseC_rescue_mini_search_beam_width_cfg = int(
        max(1, int(phaseC_cfg.get("rescue_mini_search_beam_width", 4) or 1))
    )
    phaseC_rescue_mini_search_top_symbols_cfg = int(
        max(2, int(phaseC_cfg.get("rescue_mini_search_top_symbols", 10) or 2))
    )
    phaseC_rescue_mini_search_keep_all_rows_cfg = int(
        1
        if bool(phaseC_cfg.get("rescue_mini_search_keep_all_rows", True))
        else 0
    )
    phaseC_rescue_polish_steps_cfg = int(
        max(
            0,
            int(phaseC_cfg.get("rescue_polish_steps", phaseC_steps_cfg) or 0),
        )
    )
    sub_len = int(tier_period) * int(alphabet_size)
    phaseC_enabled_effective = int(
        bool(phaseC_enabled_cfg)
        and int(phaseC_steps_cfg) > 0
        and int(stage3_phasec_start_keys) > 0
        and int(sub_len) > 1
    )
    phasec_skip_solved_before_start = bool(
        int(phaseC_enabled_effective) == 1
        and not bool(stage3_continue_after_solve)
        and np.isfinite(best3_match)
        and float(best3_match) >= float(solve_match_threshold)
    )
    if phasec_skip_solved_before_start:
        phaseC_enabled_effective = 0
        if not str(stop_reason_update).strip():
            stop_reason_update = "solved_stage3"
        print(
            f"{log_prefix} stage3-phaseC-skip tier={tier_name} text={text_id} key_seed={key_seed} "
            f"reason=solved_before_phaseC best_match={fmt_finite_float_fn(best3_match, digits=3)} "
            f"threshold={float(solve_match_threshold):.3f} continue_after_solve=0",
            flush=True,
        )
    phaseC_rescue_effective = int(
        bool(phaseC_rescue_enabled_cfg)
        and int(phaseC_rescue_candidates_cfg) > 0
        and int(phaseC_rescue_slip_swaps_cfg) > 0
        and int(phaseC_rescue_mini_search_steps_cfg) > 0
        and int(phaseC_rescue_mini_search_beam_width_cfg) > 0
        and int(tier_period) > 0
        and int(alphabet_size) > 1
    )

    phasec_lexical_cache: dict[tuple[int, ...], tuple[float, float, float]] = {}
    phasec_default_lex = (-1.0, float("-inf"), float("-inf"))

    def _phasec_lexical_rank(
        *,
        key_vals: Sequence[int],
        plaintext_idx: np.ndarray,
    ) -> tuple[float, float, float]:
        nonlocal phaseC_lexical_requests
        nonlocal phaseC_lexical_cache_hits
        nonlocal phaseC_lexical_cache_misses
        nonlocal phaseC_lexical_budget_skips
        phaseC_lexical_requests += 1
        if (not bool(stage3_phasec_word_ngram_tiebreak)) or (
            scorer_word_ngram_report_runtime is None
        ):
            return phasec_default_lex
        key_t = tuple(int(x) for x in key_vals)
        cached = phasec_lexical_cache.get(key_t, None)
        if cached is not None:
            phaseC_lexical_cache_hits += 1
            return cached
        if int(phaseC_lexical_max_calls) > 0 and int(phaseC_lexical_cache_misses) >= int(
            phaseC_lexical_max_calls
        ):
            phaseC_lexical_budget_skips += 1
            return phasec_default_lex
        phaseC_lexical_cache_misses += 1
        _scores, _stats = score_plaintexts_chunked(
            scorer=scorer_word_ngram_report_runtime,
            plaintexts=[np.asarray(plaintext_idx, dtype=np.uint8).reshape(-1)],
            wli=None,
            chunk_size=1,
            require_batch=bool(require_batch_scoring),
        )
        _ = _scores, _stats
        lex_rank = phasec_default_lex
        try:
            if hasattr(scorer_word_ngram_report_runtime, "last_stats") and callable(
                scorer_word_ngram_report_runtime.last_stats
            ):
                stats_obj = scorer_word_ngram_report_runtime.last_stats()
                if isinstance(stats_obj, dict):
                    active = 1.0 if bool(stats_obj.get("word_ngram_judge_active", False)) else 0.0
                    trust = float(stats_obj.get("word_ngram_judge_trust_score", float("-inf")))
                    if not np.isfinite(trust):
                        trust = float("-inf")
                    report_xent = float(
                        stats_obj.get("word_ngram_judge_report_xent", float("nan"))
                    )
                    report_xent_sort = (
                        float(-report_xent) if np.isfinite(report_xent) else float("-inf")
                    )
                    lex_rank = (active, trust, report_xent_sort)
        except Exception:
            lex_rank = phasec_default_lex
        phasec_lexical_cache[key_t] = tuple(lex_rank)
        return tuple(lex_rank)

    def _phasec_search_scores(
        *,
        plaintext_rows: Sequence[np.ndarray] | np.ndarray,
        count_guard_evals: bool = False,
    ) -> np.ndarray:
        nonlocal phaseC_rescue_guard_search_evals
        scores, _stats = score_plaintexts_chunked(
            scorer=scorer_stage3_search_runtime,
            plaintexts=plaintext_rows,
            wli=None,
            chunk_size=int(max(1, int(batch_eval_chunk_size))),
            require_batch=bool(require_batch_scoring),
        )
        _ = _stats
        if bool(count_guard_evals):
            phaseC_rescue_guard_search_evals += int(scores.size)
        return np.asarray(scores, dtype=np.float64).reshape(-1)

    def _phasec_is_better(
        *,
        cand_score: float,
        cand_match: float,
        cand_key: Sequence[int],
        cand_pt: np.ndarray,
        best_score_v: float,
        best_match_v: float,
        best_key_v: Sequence[int],
        best_pt_v: np.ndarray,
    ) -> bool:
        nonlocal phaseC_lexical_tiebreak_decisions
        nonlocal phaseC_lexical_threshold_skips
        cand_primary = bool(
            is_better_stage3_candidate_preserving_solve_fn(
                float(cand_score),
                float(cand_match),
                float(best_score_v),
                float(best_match_v),
                score_first=(not bool(oracle_assist_selection_effective)),
            )
        )
        best_primary = bool(
            is_better_stage3_candidate_preserving_solve_fn(
                float(best_score_v),
                float(best_match_v),
                float(cand_score),
                float(cand_match),
                score_first=(not bool(oracle_assist_selection_effective)),
            )
        )
        if cand_primary and (not best_primary):
            return True
        if best_primary and (not cand_primary):
            return False
        cand_match_f = float(cand_match)
        best_match_f = float(best_match_v)
        cand_score_f = float(cand_score)
        best_score_f = float(best_score_v)
        match_gap = (
            float(cand_match_f - best_match_f)
            if np.isfinite(cand_match_f) and np.isfinite(best_match_f)
            else float("nan")
        )
        score_gap = (
            float(cand_score_f - best_score_f)
            if np.isfinite(cand_score_f) and np.isfinite(best_score_f)
            else float("nan")
        )
        if np.isfinite(match_gap) and abs(match_gap) > float(phaseC_lexical_match_tie_eps):
            return bool(match_gap > 0.0)
        if np.isfinite(score_gap) and abs(score_gap) > float(phaseC_lexical_score_tie_eps):
            return bool(score_gap > 0.0)
        gate_match = max(
            cand_match_f if np.isfinite(cand_match_f) else float("-inf"),
            best_match_f if np.isfinite(best_match_f) else float("-inf"),
        )
        if gate_match < float(phaseC_lexical_min_match):
            phaseC_lexical_threshold_skips += 1
            if np.isfinite(match_gap) and match_gap != 0.0:
                return bool(match_gap > 0.0)
            if np.isfinite(score_gap) and score_gap != 0.0:
                return bool(score_gap > 0.0)
            return False
        phaseC_lexical_tiebreak_decisions += 1
        cand_lex = _phasec_lexical_rank(
            key_vals=cand_key,
            plaintext_idx=np.asarray(cand_pt, dtype=np.uint8).reshape(-1),
        )
        best_lex = _phasec_lexical_rank(
            key_vals=best_key_v,
            plaintext_idx=np.asarray(best_pt_v, dtype=np.uint8).reshape(-1),
        )
        return bool(cand_lex > best_lex)

    def _phasec_pick_rescue_slice(
        *,
        current_key: Sequence[int],
        current_score: float,
        fallback_slice: int,
        start_idx: int,
        phase_seed: int,
    ) -> Dict[str, Any]:
        period_i = int(max(1, int(tier_period)))
        if str(phaseC_rescue_target_mode_cfg) != "slice_probe":
            fallback_i = int(fallback_slice % max(1, period_i))
            return dict(
                target_slice=int(fallback_i),
                reason="fallback_cycle_unknown_target_mode",
                target_score=float("nan"),
                target_score_per_char=float("nan"),
                target_score_gain=float("nan"),
                probe_evals=0,
                probe_key=list(map(int, current_key)),
                probe_pt=np.asarray([], dtype=np.uint8),
                probe_match=float("nan"),
                probe_rows=[],
            )

        probe_keys: List[List[int]] = []
        probe_meta: List[Dict[str, Any]] = []
        current_key_t = tuple(map(int, current_key))
        for slice_idx in range(period_i):
            probe_seed = (
                int(phase_seed)
                + int(start_idx) * 10007
                + int(slice_idx) * 313
            )
            probe_rng = np.random.default_rng(int(probe_seed))
            cand = _phasec_apply_slice_slip(
                key_vals=current_key,
                target_slice=int(slice_idx),
                swaps=int(phaseC_rescue_slip_swaps_cfg),
                rng_obj=probe_rng,
            )
            cand_t = tuple(map(int, cand))
            if cand_t == current_key_t:
                continue
            probe_keys.append(list(cand))
            probe_meta.append(dict(slice_idx=int(slice_idx)))

        if not probe_keys:
            fallback_i = int(fallback_slice % max(1, period_i))
            return dict(
                target_slice=int(fallback_i),
                reason="fallback_cycle_no_probe_candidates",
                target_score=float("nan"),
                target_score_per_char=float("nan"),
                target_score_gain=float("nan"),
                probe_evals=0,
                probe_key=list(map(int, current_key)),
                probe_pt=np.asarray([], dtype=np.uint8),
                probe_match=float("nan"),
                probe_rows=[],
            )

        probe_pts, probe_scores, _probe_stats = decrypt_and_score_keys_chunked(
            cipher=full_cipher,
            ciphertext=np.asarray(ct_idx, dtype=np.uint8),
            keys=probe_keys,
            scorer=scorer_full_runtime,
            wli=None,
            chunk_size=int(min(int(batch_eval_chunk_size), len(probe_keys))),
            require_batch=bool(require_batch_scoring),
        )
        _ = _probe_stats
        best_idx = 0
        best_score = float("nan")
        best_gain = float("nan")
        probe_rows: List[Dict[str, Any]] = []
        for probe_idx, cand_key in enumerate(probe_keys):
            cand_score = (
                float(probe_scores[probe_idx])
                if probe_idx < int(probe_scores.size)
                else float("nan")
            )
            score_gain = (
                float(cand_score - current_score)
                if np.isfinite(cand_score) and np.isfinite(current_score)
                else float("nan")
            )
            slice_idx = int(probe_meta[probe_idx].get("slice_idx", 0))
            probe_rows.append(
                dict(
                    slice_idx=int(slice_idx),
                    score=float(cand_score),
                    score_gain=float(score_gain),
                )
            )
            better = False
            if probe_idx == 0:
                better = True
            elif np.isfinite(score_gain) and np.isfinite(best_gain):
                if float(score_gain) > float(best_gain):
                    better = True
                elif float(score_gain) == float(best_gain):
                    if np.isfinite(cand_score) and np.isfinite(best_score):
                        if float(cand_score) > float(best_score):
                            better = True
                        elif float(cand_score) == float(best_score):
                            better = bool(slice_idx < int(probe_meta[best_idx]["slice_idx"]))
                    else:
                        better = bool(slice_idx < int(probe_meta[best_idx]["slice_idx"]))
            elif np.isfinite(score_gain) and (not np.isfinite(best_gain)):
                better = True
            elif (not np.isfinite(score_gain)) and (not np.isfinite(best_gain)):
                better = bool(slice_idx < int(probe_meta[best_idx]["slice_idx"]))
            if better:
                best_idx = int(probe_idx)
                best_score = float(cand_score)
                best_gain = float(score_gain)

        best_pt = (
            np.asarray(probe_pts[best_idx], dtype=np.uint8).reshape(-1)
            if best_idx < int(probe_pts.shape[0])
            else np.asarray([], dtype=np.uint8)
        )
        best_match = (
            float(match_ratio_fn(best_pt.tolist(), pt_idx.tolist()))
            if int(best_pt.size) > 0
            else float("nan")
        )
        return dict(
            target_slice=int(probe_meta[best_idx]["slice_idx"]),
            reason="slice_probe_best_score_gain",
            target_score=float(best_score),
            target_score_per_char=float("nan"),
            target_score_gain=float(best_gain),
            probe_evals=int(len(probe_keys)),
            probe_key=list(map(int, probe_keys[best_idx])),
            probe_pt=best_pt,
            probe_match=float(best_match),
            probe_rows=[dict(row) for row in probe_rows],
        )

    def _phasec_apply_slice_slip(
        *,
        key_vals: Sequence[int],
        target_slice: int,
        swaps: int,
        rng_obj: np.random.Generator,
    ) -> List[int]:
        return apply_slice_slip(
            key_vals=key_vals,
            target_slice=int(target_slice),
            swaps=int(swaps),
            rng_obj=rng_obj,
            alphabet_size=int(alphabet_size),
        )

    def _phasec_apply_slice_pair_swap(
        *,
        key_vals: Sequence[int],
        target_slice: int,
        pos_a: int,
        pos_b: int,
    ) -> List[int]:
        return apply_slice_pair_swap(
            key_vals=key_vals,
            target_slice=int(target_slice),
            pos_a=int(pos_a),
            pos_b=int(pos_b),
            alphabet_size=int(alphabet_size),
        )

    def _phasec_score_sort_key(value: float) -> tuple[int, float]:
        return score_sort_key(float(value))

    def _phasec_landing_sort_key(row: Dict[str, Any]) -> tuple[Any, ...]:
        return landing_sort_key(row)

    def _phasec_rank_rows(
        *,
        rows: Sequence[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        return rank_rows(rows, limit=int(limit))

    def _phasec_score_key_rows(
        *,
        keys: Sequence[Sequence[int]],
        count_guard_search_evals: bool = False,
    ) -> List[Dict[str, Any]]:
        if not keys:
            return []
        pts, scores, _stats = decrypt_and_score_keys_chunked(
            cipher=full_cipher,
            ciphertext=np.asarray(ct_idx, dtype=np.uint8),
            keys=[list(map(int, key_vals)) for key_vals in keys],
            scorer=scorer_full_runtime,
            wli=None,
            chunk_size=int(max(1, min(int(batch_eval_chunk_size), len(keys)))),
            require_batch=bool(require_batch_scoring),
        )
        _ = _stats
        search_scores = _phasec_search_scores(
            plaintext_rows=[
                np.asarray(pts[row_idx], dtype=np.uint8).reshape(-1)
                for row_idx in range(int(pts.shape[0]))
            ],
            count_guard_evals=bool(count_guard_search_evals),
        )
        rows: List[Dict[str, Any]] = []
        for row_idx, key_vals in enumerate(keys):
            if row_idx >= int(pts.shape[0]):
                continue
            pt = np.asarray(pts[row_idx], dtype=np.uint8).reshape(-1)
            rows.append(
                dict(
                    key=list(map(int, key_vals)),
                    pt=pt.copy(),
                    score=(
                        float(scores[row_idx])
                        if row_idx < int(scores.size)
                        else float("nan")
                    ),
                    search_score=(
                        float(search_scores[row_idx])
                        if row_idx < int(search_scores.size)
                        else float("nan")
                    ),
                    match=float(match_ratio_fn(pt.tolist(), pt_idx.tolist())),
                )
            )
        return rows

    def _phasec_target_slice_active_positions(
        *,
        target_slice: int,
        current_key: Sequence[int],
        probe_key: Sequence[int],
    ) -> List[int]:
        return target_slice_active_positions(
            ciphertext_idx=np.asarray(ct_idx, dtype=np.uint8),
            period=int(max(1, int(tier_period))),
            target_slice=int(target_slice),
            alphabet_size=int(alphabet_size),
            current_key=current_key,
            probe_key=probe_key,
            top_symbols=int(phaseC_rescue_mini_search_top_symbols_cfg),
        )

    def _phasec_run_slice_local_mini_search(
        *,
        current_key: Sequence[int],
        current_pt: np.ndarray,
        current_score: float,
        current_search_score: float,
        current_match: float,
        probe_key: Sequence[int],
        probe_pt: np.ndarray,
        probe_score: float,
        probe_match: float,
        target_slice: int,
    ) -> Dict[str, Any]:
        probe_pt_arr = np.asarray(probe_pt, dtype=np.uint8).reshape(-1)
        probe_search_score = np.asarray([], dtype=np.float64)
        if int(probe_pt_arr.size) > 0:
            probe_search_score = _phasec_search_scores(
                plaintext_rows=[probe_pt_arr],
                count_guard_evals=True,
            )
        return run_slice_local_mini_search(
            current_key=current_key,
            current_pt=np.asarray(current_pt, dtype=np.uint8).reshape(-1),
            current_score=float(current_score),
            current_search_score=float(current_search_score),
            current_match=float(current_match),
            probe_key=probe_key,
            probe_pt=probe_pt_arr,
            probe_score=float(probe_score),
            probe_search_score=(
                float(probe_search_score[0])
                if int(probe_search_score.size) > 0
                else float("nan")
            ),
            probe_match=float(probe_match),
            target_slice=int(target_slice),
            ciphertext_idx=np.asarray(ct_idx, dtype=np.uint8),
            period=int(max(1, int(tier_period))),
            alphabet_size=int(alphabet_size),
            top_symbols=int(phaseC_rescue_mini_search_top_symbols_cfg),
            beam_width=int(phaseC_rescue_mini_search_beam_width_cfg),
            steps=int(phaseC_rescue_mini_search_steps_cfg),
            final_keep=int(max(1, int(phaseC_rescue_candidates_cfg))),
            keep_all_rows=bool(int(phaseC_rescue_mini_search_keep_all_rows_cfg) == 1),
            score_key_rows_fn=lambda keys: _phasec_score_key_rows(
                keys=keys,
                count_guard_search_evals=True,
            ),
        )

    def _phasec_row_score_gain(
        row: Dict[str, Any],
        *,
        current_score: float,
    ) -> float:
        return row_score_gain(row, current_score=float(current_score))

    def _phasec_row_search_gain(
        row: Dict[str, Any],
        *,
        current_search_score: float,
    ) -> float:
        return row_search_gain(
            row,
            current_search_score=float(current_search_score),
        )

    def _phasec_select_guarded_rescue_row(
        *,
        passing_rows: Sequence[Dict[str, Any]],
        current_score: float,
        current_search_score: float,
    ) -> Dict[str, Any] | None:
        return select_guard_passing_row(
            passing_rows=passing_rows,
            selector_mode=str(phaseC_rescue_selector_mode_cfg),
            current_score=float(current_score),
            current_search_score=float(current_search_score),
            score_band_eps=0.0,
        )

    if int(phaseC_enabled_effective) == 1 and selected:
        phasec_seed = int(base_seed + int(stage3_phasec_seed_offset))
        rng = np.random.default_rng(int(phasec_seed))
        candidate_buckets: Dict[str, List[Dict[str, Any]]] = {}

        def _append_phasec_candidate(
            *,
            source: str,
            source_rank: int,
            key_vals: Sequence[int],
            existing_hash: str = "",
        ) -> None:
            key_list = list(map(int, key_vals))
            if len(key_list) != int(key_len):
                return
            candidate_buckets.setdefault(str(source), []).append(
                dict(
                    source=str(source),
                    source_rank=int(source_rank),
                    key=list(key_list),
                    candidate_hash=_candidate_hash(
                        key_vals=key_list,
                        existing_hash=str(existing_hash),
                    ),
                )
            )

        phasec_best_source = "stage3_best"
        if (
            best3_key is not None
            and phaseB_best_key_vals is not None
            and tuple(map(int, best3_key)) == tuple(map(int, phaseB_best_key_vals))
        ):
            phasec_best_source = "stage3_best_phaseB"
        elif (
            best3_key is not None
            and phaseA_best_key_vals is not None
            and tuple(map(int, best3_key)) == tuple(map(int, phaseA_best_key_vals))
        ):
            phasec_best_source = "stage3_best_phaseA"

        if best3_key is not None and len(best3_key) == int(key_len):
            _append_phasec_candidate(
                source=str(phasec_best_source),
                source_rank=1,
                key_vals=best3_key,
            )
        for topk_row in phaseB_topk_rows:
            _append_phasec_candidate(
                source="phaseB_topk",
                source_rank=int(topk_row.get("rank", 0) or 0),
                key_vals=topk_row.get("key_idx", []),
                existing_hash=str(topk_row.get("end_hash", "")),
            )
        for selected_rank, row in enumerate(phaseA_selected_rows, start=1):
            _append_phasec_candidate(
                source="phaseA_selected",
                source_rank=int(selected_rank),
                key_vals=row.get("end_key", []),
                existing_hash=str(row.get("end_hash", "")),
            )

        candidate_pool_records = [
            dict(row)
            for source_name in (
                str(phasec_best_source),
                "phaseB_topk",
                "phaseA_selected",
            )
            for row in candidate_buckets.get(source_name, [])
        ]
        phaseC_candidate_pool_count = int(len(candidate_pool_records))
        phaseC_candidate_pool_unique_keys = int(
            len({tuple(map(int, row.get("key", []))) for row in candidate_pool_records})
        )
        phaseC_candidate_pool_unique_end_hash = int(
            len({str(row.get("candidate_hash", "")) for row in candidate_pool_records})
        )
        phaseC_candidate_pool_source_counts = _count_source_rows(candidate_pool_records)

        start_selection = _build_phasec_start_records(
            candidate_pool_records=candidate_pool_records,
            candidate_buckets=candidate_buckets,
            phasec_best_source=str(phasec_best_source),
            phasec_start_policy=str(phaseC_start_policy_cfg),
            stage3_phasec_start_keys=int(stage3_phasec_start_keys),
        )
        start_records = list(start_selection.get("rows", []))
        phaseC_candidate_pool_rows = [
            dict(row)
            for row in list(start_selection.get("candidate_pool_rows", []) or [])
        ]
        phaseC_novel_view_id = str(
            start_selection.get("novelty_view_id", phaseC_novel_view_id)
        )
        phaseC_anchor_candidate_hash = str(
            start_selection.get(
                "anchor_candidate_hash",
                phaseC_anchor_candidate_hash,
            )
        )
        phaseC_candidate_pool_eligible_novel_count = int(
            start_selection.get(
                "candidate_pool_eligible_novel_count",
                phaseC_candidate_pool_eligible_novel_count,
            )
        )
        phaseC_candidate_pool_eligible_novel_row_count = int(
            start_selection.get(
                "candidate_pool_eligible_novel_row_count",
                phaseC_candidate_pool_eligible_novel_row_count,
            )
        )
        phaseC_candidate_pool_eligible_novel_source_counts = dict(
            start_selection.get(
                "candidate_pool_eligible_novel_source_counts",
                phaseC_candidate_pool_eligible_novel_source_counts,
            )
        )
        phaseC_start_eligible_novel_count = int(
            start_selection.get(
                "start_eligible_novel_count",
                phaseC_start_eligible_novel_count,
            )
        )
        phaseC_selected_novel_challenger_count = int(
            start_selection.get(
                "selected_novel_challenger_count",
                phaseC_selected_novel_challenger_count,
            )
        )
        phaseC_eligible_novel_not_selected_count = int(
            start_selection.get(
                "eligible_novel_not_selected_count",
                phaseC_eligible_novel_not_selected_count,
            )
        )
        phaseC_selected_novel_challenger_hashes = list(
            start_selection.get(
                "selected_novel_challenger_hashes",
                phaseC_selected_novel_challenger_hashes,
            )
        )

        if start_records:
            phaseC_ran = 1
            phaseC_start_keys_used = int(len(start_records))
            phaseC_start_source_counts = _count_source_rows(start_records)
            phaseC_start_unique_end_hash = int(
                len({str(row.get("candidate_hash", "")) for row in start_records})
            )
            phaseC_anchor_lane_starts = int(1 if int(phaseC_start_keys_used) > 0 else 0)
            phaseC_challenger_lane_starts = int(
                max(0, int(phaseC_start_keys_used) - int(phaseC_anchor_lane_starts))
            )
            rescue_anchor_candidates: List[Dict[str, int]] = []
            rescue_challenger_candidates: List[Dict[str, int]] = []
            for start_idx, start_row in enumerate(start_records, start=1):
                start_source = str(start_row.get("source", ""))
                start_source_rank = int(start_row.get("source_rank", 0) or 0)
                is_anchor_lane = bool(int(start_idx) == 1)
                if is_anchor_lane and int(phaseC_rescue_anchor_enabled_cfg) == 1:
                    rescue_anchor_candidates.append(
                        dict(start_idx=int(start_idx), source_rank=int(start_source_rank))
                    )
                    continue
                if (
                    (not is_anchor_lane)
                    and str(start_source) == "phaseB_topk"
                    and int(start_source_rank) >= int(phaseC_rescue_phaseb_topk_min_rank_cfg)
                ):
                    rescue_challenger_candidates.append(
                        dict(start_idx=int(start_idx), source_rank=int(start_source_rank))
                    )
            rescue_challenger_candidates = sorted(
                rescue_challenger_candidates,
                key=lambda row: (
                    int(row.get("source_rank", 0)),
                    int(row.get("start_idx", 0)),
                ),
            )
            rescue_budget_rows = list(rescue_anchor_candidates) + list(
                rescue_challenger_candidates
            )
            if int(phaseC_rescue_max_starts_cfg) > 0:
                rescue_budget_rows = rescue_budget_rows[
                    : int(phaseC_rescue_max_starts_cfg)
                ]
            rescue_eligible_start_indices: set[int] = {
                int(row.get("start_idx", 0)) for row in rescue_budget_rows
            }
            phaseC_rescue_eligible_starts = int(len(rescue_eligible_start_indices))
            phaseC_total_steps = (
                int(phaseC_start_keys_used) * int(phaseC_steps_cfg)
                + int(phaseC_rescue_eligible_starts)
                * int(max(0, int(phaseC_rescue_polish_steps_cfg) - int(phaseC_steps_cfg)))
            )
            phaseC_rescue_probe_eval_budget = (
                int(phaseC_rescue_eligible_starts) * int(max(1, int(tier_period)))
                if (
                    int(phaseC_rescue_effective) == 1
                    and str(phaseC_rescue_target_mode_cfg) == "slice_probe"
                )
                else 0
            )
            phaseC_rescue_active_positions_cap = int(
                max(
                    2,
                    min(
                        int(phaseC_rescue_mini_search_top_symbols_cfg),
                        int(max(2, int(alphabet_size))),
                    ),
                )
            )
            phaseC_rescue_pair_moves_cap = int(
                max(
                    0,
                    (
                        int(phaseC_rescue_active_positions_cap)
                        * int(max(0, int(phaseC_rescue_active_positions_cap) - 1))
                    )
                    // 2,
                )
            )
            phaseC_rescue_eval_budget = (
                int(phaseC_rescue_eligible_starts)
                * int(phaseC_rescue_mini_search_steps_cfg)
                * int(phaseC_rescue_mini_search_beam_width_cfg)
                * int(phaseC_rescue_pair_moves_cap)
                if int(phaseC_rescue_effective) == 1
                else 0
            )
            phaseC_rescue_polish_eval_budget = (
                int(phaseC_rescue_eligible_starts)
                * int(max(0, int(phaseC_rescue_polish_steps_cfg) - int(phaseC_steps_cfg)))
                * int(phaseC_proposals_per_step_cfg)
                if (
                    int(phaseC_rescue_effective) == 1
                    and int(phaseC_rescue_polish_steps_cfg) > int(phaseC_steps_cfg)
                )
                else 0
            )
            phaseC_eval_budget = (
                int(phaseC_start_keys_used)
                * int(phaseC_steps_cfg)
                * int(phaseC_proposals_per_step_cfg)
                + int(phaseC_rescue_probe_eval_budget)
                + int(phaseC_rescue_eval_budget)
                + int(phaseC_rescue_polish_eval_budget)
            )
            phaseC_progress_interval_s = float(
                max(5.0, min(30.0, float(stage3_heartbeat_seconds)))
            )
            phaseC_t0 = float(time.time())
            phaseC_last_hb = float(phaseC_t0)
            phaseC_completed_steps = 0
            print(
                f"{log_prefix} stage3-phaseC-plan tier={tier_name} text={text_id} key_seed={key_seed} "
                f"candidate_pool={int(phaseC_candidate_pool_count)} "
                f"candidate_pool_unique_keys={int(phaseC_candidate_pool_unique_keys)} "
                f"candidate_pool_unique_end_hash={int(phaseC_candidate_pool_unique_end_hash)} "
                f"candidate_pool_sources={phaseC_candidate_pool_source_counts} "
                f"eligible_novel_pool={int(phaseC_candidate_pool_eligible_novel_count)} "
                f"eligible_novel_rows={int(phaseC_candidate_pool_eligible_novel_row_count)} "
                f"eligible_novel_sources={phaseC_candidate_pool_eligible_novel_source_counts} "
                f"start_keys={int(phaseC_start_keys_used)} "
                f"start_unique_end_hash={int(phaseC_start_unique_end_hash)} "
                f"start_policy={phaseC_start_policy_cfg} "
                f"novel_view={phaseC_novel_view_id or 'off'} "
                f"anchor_candidate_hash={phaseC_anchor_candidate_hash or 'off'} "
                f"start_sources={phaseC_start_source_counts} "
                f"start_eligible_novel={int(phaseC_start_eligible_novel_count)} "
                f"selected_novel={int(phaseC_selected_novel_challenger_count)} "
                f"eligible_novel_not_selected={int(phaseC_eligible_novel_not_selected_count)} "
                f"steps={int(phaseC_steps_cfg)} total_steps={int(phaseC_total_steps)} "
                f"proposals_per_step={int(phaseC_proposals_per_step_cfg)} "
                f"rescue_enabled={int(phaseC_rescue_effective)} "
                f"rescue_target_mode={phaseC_rescue_target_mode_cfg} "
                f"rescue_selector_mode={phaseC_rescue_selector_mode_cfg} "
                f"rescue_anchor_enabled={int(phaseC_rescue_anchor_enabled_cfg)} "
                f"rescue_phaseb_topk_min_rank={int(phaseC_rescue_phaseb_topk_min_rank_cfg)} "
                f"rescue_max_starts={int(phaseC_rescue_max_starts_cfg)} "
                f"rescue_eligible_starts={int(phaseC_rescue_eligible_starts)} "
                f"rescue_search_score_max_drop={float(phaseC_rescue_search_score_max_drop_cfg):.6f} "
                f"rescue_probe_budget={int(phaseC_rescue_probe_eval_budget)} "
                f"rescue_candidates={int(phaseC_rescue_candidates_cfg)} "
                f"rescue_slip_swaps={int(phaseC_rescue_slip_swaps_cfg)} "
                f"rescue_mini_search_steps={int(phaseC_rescue_mini_search_steps_cfg)} "
                f"rescue_mini_search_beam={int(phaseC_rescue_mini_search_beam_width_cfg)} "
                f"rescue_mini_search_top_symbols={int(phaseC_rescue_mini_search_top_symbols_cfg)} "
                f"rescue_mini_search_keep_all_rows={int(phaseC_rescue_mini_search_keep_all_rows_cfg)} "
                f"rescue_polish_steps={int(phaseC_rescue_polish_steps_cfg)} "
                f"approx_eval_budget={int(phaseC_eval_budget)} "
                f"word_ngram_tiebreak={1 if bool(stage3_phasec_word_ngram_tiebreak) else 0} "
                f"lexical_min_match={float(phaseC_lexical_min_match):.3f} "
                f"lexical_match_tie_eps={float(phaseC_lexical_match_tie_eps):.4f} "
                f"lexical_score_tie_eps={float(phaseC_lexical_score_tie_eps):.4f} "
                f"lexical_max_calls={int(phaseC_lexical_max_calls)} "
                f"checkpoint_jsonl={phaseC_checkpoint_jsonl_name or 'off'}",
                flush=True,
            )
            global_best_key = (
                list(map(int, best3_key))
                if (best3_key is not None and len(best3_key) == int(key_len))
                else list(map(int, start_records[0]["key"]))
            )
            global_best_pt = np.asarray(pt3, dtype=np.uint8).reshape(-1)
            global_best_score = float(best3_score)
            global_best_match = float(best3_match)
            if (
                global_best_pt.size <= 0
                or (not np.isfinite(global_best_score))
                or (not np.isfinite(global_best_match))
            ):
                init_pts, init_scores, _init_stats = decrypt_and_score_keys_chunked(
                    cipher=full_cipher,
                    ciphertext=np.asarray(ct_idx, dtype=np.uint8),
                    keys=[global_best_key],
                    scorer=scorer_full_runtime,
                    wli=None,
                    chunk_size=1,
                    require_batch=bool(require_batch_scoring),
                )
                _ = _init_stats
                if int(init_pts.shape[0]) > 0:
                    global_best_pt = np.asarray(init_pts[0], dtype=np.uint8).reshape(-1)
                    global_best_score = (
                        float(init_scores[0]) if int(init_scores.size) > 0 else float("nan")
                    )
                    global_best_match = float(
                        match_ratio_fn(global_best_pt.tolist(), pt_idx.tolist())
                    )
            phaseC_final_winner_lane = "anchor"
            phaseC_final_winner_source = str(phasec_best_source)
            anchor_best_key = list(map(int, global_best_key))
            anchor_best_pt = np.asarray(global_best_pt, dtype=np.uint8).copy()
            anchor_best_score = float(global_best_score)
            anchor_best_match = float(global_best_match)
            anchor_best_established = False

            for start_idx, start_row in enumerate(start_records, start=1):
                start_key = list(map(int, start_row.get("key", [])))
                start_source = str(start_row.get("source", ""))
                start_source_rank = int(start_row.get("source_rank", 0) or 0)
                start_candidate_hash = str(start_row.get("candidate_hash", ""))
                start_lane = "anchor" if int(start_idx) == 1 else "challenger"
                init_pts, init_scores, _init_stats = decrypt_and_score_keys_chunked(
                    cipher=full_cipher,
                    ciphertext=np.asarray(ct_idx, dtype=np.uint8),
                    keys=[start_key],
                    scorer=scorer_full_runtime,
                    wli=None,
                    chunk_size=1,
                    require_batch=bool(require_batch_scoring),
                )
                _ = _init_stats
                if int(init_pts.shape[0]) <= 0:
                    continue
                cur_key = list(map(int, start_key))
                cur_pt = np.asarray(init_pts[0], dtype=np.uint8).reshape(-1)
                cur_score = (
                    float(init_scores[0]) if int(init_scores.size) > 0 else float("nan")
                )
                cur_match = float(match_ratio_fn(cur_pt.tolist(), pt_idx.tolist()))
                local_best_key = list(map(int, cur_key))
                local_best_pt = np.asarray(cur_pt, dtype=np.uint8).copy()
                local_best_score = float(cur_score)
                local_best_match = float(cur_match)
                init_search_scores = _phasec_search_scores(plaintext_rows=[cur_pt])
                init_search_score_start = (
                    float(init_search_scores[0])
                    if int(init_search_scores.size) > 0
                    else float("nan")
                )
                cur_search_score = float(init_search_score_start)
                rescue_eligible = int(
                    1 if int(start_idx) in rescue_eligible_start_indices else 0
                )
                if int(phaseC_rescue_effective) != 1:
                    rescue_skip_reason = "rescue_disabled"
                elif int(rescue_eligible) == 1:
                    rescue_skip_reason = ""
                elif str(start_lane) == "anchor":
                    rescue_skip_reason = "anchor_polish_only"
                elif str(start_source) != "phaseB_topk":
                    rescue_skip_reason = "challenger_not_phaseB_topk"
                elif int(start_source_rank) < int(phaseC_rescue_phaseb_topk_min_rank_cfg):
                    rescue_skip_reason = "phaseB_topk_rank_below_min"
                else:
                    rescue_skip_reason = "rescue_max_starts_exhausted"
                print(
                    f"{log_prefix} stage3-phaseC-start tier={tier_name} text={text_id} key_seed={key_seed} "
                    f"start={int(start_idx)}/{int(phaseC_start_keys_used)} "
                    f"lane={start_lane} rescue_eligible={int(rescue_eligible)} "
                    f"source={start_source} source_rank={int(start_source_rank)} "
                    f"candidate_hash={start_candidate_hash} "
                    f"init_match={fmt_finite_float_fn(local_best_match, digits=3)} "
                    f"init_score={fmt_finite_float_fn(local_best_score, digits=6)} "
                    f"init_search_score={fmt_finite_float_fn(init_search_score_start, digits=6)} "
                    f"rescue_skip_reason={rescue_skip_reason or 'eligible'}",
                    flush=True,
                )
                start_accepts_before = int(phaseC_accepts)
                start_improves_before = int(phaseC_improves)
                start_lexical_requests_before = int(phaseC_lexical_requests)
                start_lexical_cache_hits_before = int(phaseC_lexical_cache_hits)
                start_lexical_cache_misses_before = int(phaseC_lexical_cache_misses)
                start_lexical_tie_before = int(phaseC_lexical_tiebreak_decisions)
                start_lexical_budget_skip_before = int(phaseC_lexical_budget_skips)
                start_lexical_threshold_skip_before = int(
                    phaseC_lexical_threshold_skips
                )
                start_evals_before = int(phaseC_evals)
                init_match_start = float(local_best_match)
                init_score_start = float(local_best_score)
                phasec_shadow_stop_v1_state = build_shadow_stop_v1_state(
                    phase_name="phaseC",
                    plateau_work_units=int(PHASEC_SHADOW_STOP_V1_PLATEAU_STEPS),
                    high_score_floor=float(PHASEC_SHADOW_STOP_V1_HIGH_SCORE_FLOOR),
                    high_score_stable_work_units=int(
                        PHASEC_SHADOW_STOP_V1_HIGH_SCORE_STABLE_STEPS
                    ),
                    score_improve_eps=float(
                        PHASEC_SHADOW_STOP_V1_SCORE_IMPROVE_EPS
                    ),
                    initial_score=float(local_best_score),
                    initial_match=float(local_best_match),
                )
                rescue_attempted = 0
                rescue_target_slice: int | None = None
                rescue_slice_reason = ""
                rescue_slice_score = float("nan")
                rescue_slice_score_per_char = float("nan")
                rescue_probe_score_gain = float("nan")
                rescue_applied = 0
                rescue_landing_type = "current_seed"
                rescue_landing_step = 0
                rescue_landing_parent_type = ""
                rescue_landing_swap_a: int | None = None
                rescue_landing_swap_b: int | None = None
                rescue_mini_search_pool_rows = 0
                rescue_polish_steps_used = int(phaseC_steps_cfg)
                rescue_post_match: float | None = None
                rescue_post_score: float | None = None
                rescue_match_gain = float("nan")
                rescue_score_gain = float("nan")
                rescue_became_global_best = 0
                rescue_lexical_requests_delta = 0
                rescue_lexical_cache_hits_delta = 0
                rescue_lexical_cache_misses_delta = 0
                rescue_lexical_tiebreak_decisions_delta = 0
                rescue_lexical_budget_skips_delta = 0
                rescue_lexical_threshold_skips_delta = 0
                rescue_guard_search_base_score = float(init_search_score_start)
                rescue_guard_search_best_score = float("nan")
                rescue_guard_search_passed = 0
                overtook_anchor = 0

                if int(phaseC_rescue_effective) == 1 and int(rescue_eligible) == 1:
                    rescue_attempted = 1
                    phaseC_rescue_ran = 1
                    phaseC_rescue_starts_attempted += 1
                    rescue_lexical_requests_before = int(phaseC_lexical_requests)
                    rescue_lexical_cache_hits_before = int(phaseC_lexical_cache_hits)
                    rescue_lexical_cache_misses_before = int(phaseC_lexical_cache_misses)
                    rescue_lexical_tie_before = int(phaseC_lexical_tiebreak_decisions)
                    rescue_lexical_budget_skip_before = int(phaseC_lexical_budget_skips)
                    rescue_lexical_threshold_skip_before = int(
                        phaseC_lexical_threshold_skips
                    )
                    rescue_pick = _phasec_pick_rescue_slice(
                        current_key=cur_key,
                        current_score=float(cur_score),
                        fallback_slice=int(start_idx - 1),
                        start_idx=int(start_idx),
                        phase_seed=int(phasec_seed),
                    )
                    rescue_target_slice = int(rescue_pick.get("target_slice", 0))
                    rescue_slice_reason = str(rescue_pick.get("reason", ""))
                    rescue_slice_score = float(
                        rescue_pick.get("target_score", float("nan"))
                    )
                    rescue_slice_score_per_char = float("nan")
                    rescue_probe_score_gain = float(
                        rescue_pick.get("target_score_gain", float("nan"))
                    )
                    probe_key = list(
                        map(int, rescue_pick.get("probe_key", list(cur_key)))
                    )
                    probe_pt = np.asarray(
                        rescue_pick.get("probe_pt", []),
                        dtype=np.uint8,
                    ).reshape(-1)
                    probe_match = float(
                        rescue_pick.get("probe_match", float("nan"))
                    )
                    probe_evals = int(rescue_pick.get("probe_evals", 0) or 0)
                    phaseC_evals += int(probe_evals)
                    phaseC_rescue_probe_evals += int(probe_evals)
                    rescue_mini_search = _phasec_run_slice_local_mini_search(
                        current_key=cur_key,
                        current_pt=cur_pt,
                        current_score=float(cur_score),
                        current_search_score=float(cur_search_score),
                        current_match=float(cur_match),
                        probe_key=probe_key,
                        probe_pt=probe_pt,
                        probe_score=float(rescue_slice_score),
                        probe_match=float(probe_match),
                        target_slice=int(rescue_target_slice),
                    )
                    phaseC_evals += int(rescue_mini_search.get("evals", 0) or 0)
                    phaseC_rescue_evals += int(
                        rescue_mini_search.get("evals", 0) or 0
                    )
                    phaseC_rescue_mini_search_evals += int(
                        rescue_mini_search.get("evals", 0) or 0
                    )
                    rescue_mini_search_pool_rows = int(
                        rescue_mini_search.get("collected_row_count", 0) or 0
                    )
                    print(
                        f"{log_prefix} stage3-phaseC-rescue-start tier={tier_name} text={text_id} key_seed={key_seed} "
                        f"start={int(start_idx)}/{int(phaseC_start_keys_used)} "
                        f"lane={start_lane} "
                        f"source={start_source} source_rank={int(start_source_rank)} "
                        f"candidate_hash={start_candidate_hash} "
                        f"target_slice={int(rescue_target_slice)} "
                        f"slice_reason={rescue_slice_reason} "
                        f"target_mode={phaseC_rescue_target_mode_cfg} "
                        f"selector_mode={phaseC_rescue_selector_mode_cfg} "
                        f"slice_score={fmt_finite_float_fn(rescue_slice_score, digits=6)} "
                        f"probe_score_gain={fmt_finite_float_fn(rescue_probe_score_gain, digits=6)} "
                        f"probe_evals={int(probe_evals)} "
                        f"mini_search_pool_rows={int(rescue_mini_search_pool_rows)} "
                        f"mini_search_evals={int(rescue_mini_search.get('evals', 0) or 0)} "
                        f"mini_search_steps={int(rescue_mini_search.get('expanded_steps', 0) or 0)} "
                        f"rescue_slip_swaps={int(phaseC_rescue_slip_swaps_cfg)} "
                        f"init_match={fmt_finite_float_fn(init_match_start, digits=3)} "
                        f"init_score={fmt_finite_float_fn(init_score_start, digits=6)} "
                        f"guard_search_base={fmt_finite_float_fn(rescue_guard_search_base_score, digits=6)}",
                        flush=True,
                    )
                    landing_candidates: List[Dict[str, Any]] = []
                    if int(np.asarray(probe_pt, dtype=np.uint8).size) > 0:
                        probe_search_score = _phasec_search_scores(
                            plaintext_rows=[np.asarray(probe_pt, dtype=np.uint8).reshape(-1)],
                            count_guard_evals=True,
                        )
                        landing_candidates.append(
                            dict(
                                key=list(map(int, probe_key)),
                                pt=np.asarray(probe_pt, dtype=np.uint8).copy(),
                                score=float(rescue_slice_score),
                                match=float(probe_match),
                                search_score=(
                                    float(probe_search_score[0])
                                    if int(probe_search_score.size) > 0
                                    else float("nan")
                                ),
                                landing_type="probe_seed",
                                mini_search_step=0,
                                mini_search_parent_type="probe_seed",
                                mini_search_swap_a=None,
                                mini_search_swap_b=None,
                            )
                        )
                    for cand_row in list(rescue_mini_search.get("rows", []) or []):
                        landing_candidates.append(dict(cand_row))
                    landing_key = list(map(int, cur_key))
                    landing_pt = np.asarray(cur_pt, dtype=np.uint8).copy()
                    landing_score = float(cur_score)
                    landing_match = float(cur_match)
                    landing_search_score = float(cur_search_score)
                    if landing_candidates:
                        passing_rows: List[Dict[str, Any]] = []
                        for cand_row in landing_candidates:
                            cand_search_score = float(
                                cand_row.get("search_score", float("nan"))
                            )
                            guard_pass = True
                            if (
                                np.isfinite(float(cur_search_score))
                                and np.isfinite(float(cand_search_score))
                                and float(cand_search_score)
                                < float(cur_search_score)
                                - float(phaseC_rescue_search_score_max_drop_cfg)
                            ):
                                guard_pass = False
                            cand_row["guard_pass"] = int(1 if guard_pass else 0)
                            if not guard_pass:
                                phaseC_rescue_guard_search_rejects += 1
                                continue
                            passing_rows.append(dict(cand_row))
                        best_guarded = _phasec_select_guarded_rescue_row(
                            passing_rows=passing_rows,
                            current_score=float(cur_score),
                            current_search_score=float(cur_search_score),
                        )
                        if best_guarded is not None:
                            rescue_guard_search_passed = int(
                                best_guarded.get("guard_pass", 0) or 0
                            )
                            if int(rescue_guard_search_passed) == 1:
                                phaseC_rescue_guard_search_passes += 1
                            rescue_guard_search_best_score = float(
                                best_guarded.get("search_score", float("nan"))
                            )
                            landing_key = list(map(int, best_guarded.get("key", cur_key)))
                            landing_pt = np.asarray(
                                best_guarded.get("pt", cur_pt),
                                dtype=np.uint8,
                            ).copy()
                            landing_score = float(best_guarded.get("score", cur_score))
                            landing_match = float(best_guarded.get("match", cur_match))
                            landing_search_score = float(
                                best_guarded.get("search_score", cur_search_score)
                            )
                            rescue_landing_type = str(
                                best_guarded.get("landing_type", "probe_seed") or "probe_seed"
                            )
                            rescue_landing_step = int(
                                best_guarded.get("mini_search_step", 0) or 0
                            )
                            rescue_landing_parent_type = str(
                                best_guarded.get("mini_search_parent_type", "") or ""
                            )
                            rescue_landing_swap_a = (
                                int(best_guarded.get("mini_search_swap_a"))
                                if best_guarded.get("mini_search_swap_a", None) is not None
                                else None
                            )
                            rescue_landing_swap_b = (
                                int(best_guarded.get("mini_search_swap_b"))
                                if best_guarded.get("mini_search_swap_b", None) is not None
                                else None
                            )
                    if (
                        tuple(map(int, landing_key)) != tuple(map(int, cur_key))
                        and int(np.asarray(landing_pt, dtype=np.uint8).size) > 0
                    ):
                        rescue_applied = 1
                        phaseC_rescue_applied_starts += 1
                        cur_key = list(map(int, landing_key))
                        cur_pt = np.asarray(landing_pt, dtype=np.uint8).copy()
                        cur_score = float(landing_score)
                        cur_match = float(landing_match)
                        cur_search_score = float(landing_search_score)
                        local_best_key = list(map(int, cur_key))
                        local_best_pt = np.asarray(cur_pt, dtype=np.uint8).copy()
                        local_best_score = float(cur_score)
                        local_best_match = float(cur_match)
                        rescue_became_global_best = int(
                            1
                            if _phasec_is_better(
                                cand_score=float(cur_score),
                                cand_match=float(cur_match),
                                cand_key=cur_key,
                                cand_pt=cur_pt,
                                best_score_v=float(global_best_score),
                                best_match_v=float(global_best_match),
                                best_key_v=global_best_key,
                                best_pt_v=global_best_pt,
                            )
                            else 0
                        )
                        if str(start_lane) == "challenger" and int(
                            phaseC_rescue_polish_steps_cfg
                        ) > 0:
                            rescue_polish_steps_used = int(phaseC_rescue_polish_steps_cfg)
                    rescue_post_match = (
                        float(cur_match) if np.isfinite(cur_match) else None
                    )
                    rescue_post_score = (
                        float(cur_score) if np.isfinite(cur_score) else None
                    )
                    rescue_match_gain = (
                        float(cur_match - init_match_start)
                        if np.isfinite(cur_match) and np.isfinite(init_match_start)
                        else float("nan")
                    )
                    rescue_score_gain = (
                        float(cur_score - init_score_start)
                        if np.isfinite(cur_score) and np.isfinite(init_score_start)
                        else float("nan")
                    )
                    rescue_lexical_requests_delta = int(
                        int(phaseC_lexical_requests) - int(rescue_lexical_requests_before)
                    )
                    rescue_lexical_cache_hits_delta = int(
                        int(phaseC_lexical_cache_hits)
                        - int(rescue_lexical_cache_hits_before)
                    )
                    rescue_lexical_cache_misses_delta = int(
                        int(phaseC_lexical_cache_misses)
                        - int(rescue_lexical_cache_misses_before)
                    )
                    rescue_lexical_tiebreak_decisions_delta = int(
                        int(phaseC_lexical_tiebreak_decisions)
                        - int(rescue_lexical_tie_before)
                    )
                    rescue_lexical_budget_skips_delta = int(
                        int(phaseC_lexical_budget_skips)
                        - int(rescue_lexical_budget_skip_before)
                    )
                    rescue_lexical_threshold_skips_delta = int(
                        int(phaseC_lexical_threshold_skips)
                        - int(rescue_lexical_threshold_skip_before)
                    )
                    phaseC_rescue_lexical_requests += int(rescue_lexical_requests_delta)
                    phaseC_rescue_lexical_cache_hits += int(
                        rescue_lexical_cache_hits_delta
                    )
                    phaseC_rescue_lexical_cache_misses += int(
                        rescue_lexical_cache_misses_delta
                    )
                    phaseC_rescue_lexical_tiebreak_decisions += int(
                        rescue_lexical_tiebreak_decisions_delta
                    )
                    phaseC_rescue_lexical_budget_skips += int(
                        rescue_lexical_budget_skips_delta
                    )
                    phaseC_rescue_lexical_threshold_skips += int(
                        rescue_lexical_threshold_skips_delta
                    )
                    print(
                        f"{log_prefix} stage3-phaseC-rescue-finish-start tier={tier_name} text={text_id} key_seed={key_seed} "
                        f"start={int(start_idx)}/{int(phaseC_start_keys_used)} "
                        f"lane={start_lane} "
                        f"source={start_source} source_rank={int(start_source_rank)} "
                        f"candidate_hash={start_candidate_hash} "
                        f"target_slice={int(rescue_target_slice)} "
                        f"slice_reason={rescue_slice_reason} "
                        f"target_mode={phaseC_rescue_target_mode_cfg} "
                        f"selector_mode={phaseC_rescue_selector_mode_cfg} "
                        f"landing_type={rescue_landing_type} "
                        f"landing_step={int(rescue_landing_step)} "
                        f"landing_parent={rescue_landing_parent_type or 'none'} "
                        f"rescue_match={fmt_finite_float_fn(cur_match, digits=3)} "
                        f"rescue_score={fmt_finite_float_fn(cur_score, digits=6)} "
                        f"rescue_match_gain={fmt_finite_float_fn(rescue_match_gain, digits=3)} "
                        f"rescue_score_gain={fmt_finite_float_fn(rescue_score_gain, digits=6)} "
                        f"rescue_applied={int(rescue_applied)} "
                        f"guard_search_best={fmt_finite_float_fn(rescue_guard_search_best_score, digits=6)} "
                        f"guard_search_passed={int(rescue_guard_search_passed)} "
                        f"rescue_lex_req_delta={int(rescue_lexical_requests_delta)} "
                        f"rescue_lex_budget_skip_delta={int(rescue_lexical_budget_skips_delta)} "
                        f"rescue_lex_threshold_skip_delta={int(rescue_lexical_threshold_skips_delta)} "
                        f"rescue_became_global_best={int(rescue_became_global_best)}",
                        flush=True,
                    )

                phaseC_steps_this_start = int(
                    rescue_polish_steps_used
                    if (
                        int(rescue_applied) == 1
                        and str(start_lane) == "challenger"
                        and int(rescue_polish_steps_used) > 0
                    )
                    else phaseC_steps_cfg
                )
                for _step in range(int(phaseC_steps_this_start)):
                    phaseC_completed_steps += 1
                    proposal_keys: list[list[int]] = []
                    for _ in range(int(phaseC_proposals_per_step_cfg)):
                        cand = list(map(int, cur_key))
                        phase_i = int(rng.integers(0, max(1, int(tier_period))))
                        phase_base = int(phase_i * int(alphabet_size))
                        if (int(alphabet_size) >= 3) and (
                            float(rng.random()) < float(phaseC_three_cycle_prob)
                        ):
                            picks = np.asarray(
                                rng.choice(int(alphabet_size), size=3, replace=False),
                                dtype=np.int64,
                            )
                            i0 = int(phase_base + int(picks[0]))
                            i1 = int(phase_base + int(picks[1]))
                            i2 = int(phase_base + int(picks[2]))
                            v0, v1, v2 = cand[i0], cand[i1], cand[i2]
                            cand[i0], cand[i1], cand[i2] = int(v2), int(v0), int(v1)
                        else:
                            a = int(rng.integers(0, int(alphabet_size)))
                            b = int(rng.integers(0, int(alphabet_size - 1)))
                            if b >= a:
                                b += 1
                            i1 = int(phase_base + int(a))
                            i2 = int(phase_base + int(b))
                            cand[i1], cand[i2] = int(cand[i2]), int(cand[i1])
                        proposal_keys.append(cand)
                    if not proposal_keys:
                        continue
                    prop_pts, prop_scores, _prop_stats = decrypt_and_score_keys_chunked(
                        cipher=full_cipher,
                        ciphertext=np.asarray(ct_idx, dtype=np.uint8),
                        keys=proposal_keys,
                        scorer=scorer_full_runtime,
                        wli=None,
                        chunk_size=int(min(int(batch_eval_chunk_size), len(proposal_keys))),
                        require_batch=bool(require_batch_scoring),
                    )
                    _ = _prop_stats
                    phaseC_evals += int(len(proposal_keys))
                    best_prop_idx: int | None = None
                    best_prop_key: list[int] | None = None
                    best_prop_pt = np.asarray([], dtype=np.uint8)
                    best_prop_score = float("nan")
                    best_prop_match = float("nan")
                    for cand_idx, cand_key in enumerate(proposal_keys):
                        if cand_idx >= int(prop_pts.shape[0]):
                            continue
                        cand_pt = np.asarray(prop_pts[cand_idx], dtype=np.uint8).reshape(-1)
                        cand_score = (
                            float(prop_scores[cand_idx])
                            if cand_idx < int(prop_scores.size)
                            else float("nan")
                        )
                        cand_match = float(match_ratio_fn(cand_pt.tolist(), pt_idx.tolist()))
                        better_than_current = _phasec_is_better(
                            cand_score=float(cand_score),
                            cand_match=float(cand_match),
                            cand_key=cand_key,
                            cand_pt=cand_pt,
                            best_score_v=float(cur_score),
                            best_match_v=float(cur_match),
                            best_key_v=cur_key,
                            best_pt_v=cur_pt,
                        )
                        if not better_than_current:
                            continue
                        if best_prop_idx is None:
                            best_prop_idx = int(cand_idx)
                            best_prop_key = list(map(int, cand_key))
                            best_prop_pt = cand_pt.copy()
                            best_prop_score = float(cand_score)
                            best_prop_match = float(cand_match)
                            continue
                        better_than_proposal = _phasec_is_better(
                            cand_score=float(cand_score),
                            cand_match=float(cand_match),
                            cand_key=cand_key,
                            cand_pt=cand_pt,
                            best_score_v=float(best_prop_score),
                            best_match_v=float(best_prop_match),
                            best_key_v=list(map(int, best_prop_key)),
                            best_pt_v=best_prop_pt,
                        )
                        if better_than_proposal:
                            best_prop_idx = int(cand_idx)
                            best_prop_key = list(map(int, cand_key))
                            best_prop_pt = cand_pt.copy()
                            best_prop_score = float(cand_score)
                            best_prop_match = float(cand_match)
                    if best_prop_idx is not None and best_prop_key is not None:
                        cur_key = list(map(int, best_prop_key))
                        cur_pt = np.asarray(best_prop_pt, dtype=np.uint8).copy()
                        cur_score = float(best_prop_score)
                        cur_match = float(best_prop_match)
                        phaseC_accepts += 1
                        local_improved = _phasec_is_better(
                            cand_score=float(cur_score),
                            cand_match=float(cur_match),
                            cand_key=cur_key,
                            cand_pt=cur_pt,
                            best_score_v=float(local_best_score),
                            best_match_v=float(local_best_match),
                            best_key_v=local_best_key,
                            best_pt_v=local_best_pt,
                        )
                        if local_improved:
                            local_best_key = list(map(int, cur_key))
                            local_best_pt = np.asarray(cur_pt, dtype=np.uint8).copy()
                            local_best_score = float(cur_score)
                            local_best_match = float(cur_match)
                            phaseC_improves += 1
                    phasec_shadow_stop_v1_state = update_shadow_stop_v1_state(
                        phasec_shadow_stop_v1_state,
                        work_unit=int(_step + 1),
                        evals_done=int(int(phaseC_evals) - int(start_evals_before)),
                        best_score=float(local_best_score),
                        best_match=float(local_best_match),
                        progress_counter=int(
                            int(phaseC_improves) - int(start_improves_before)
                        ),
                        novelty_counter=int(
                            int(phaseC_accepts) - int(start_accepts_before)
                        ),
                    )
                    now_phasec = float(time.time())
                    if (
                        (now_phasec - float(phaseC_last_hb)) >= float(phaseC_progress_interval_s)
                        or int(_step + 1) == int(phaseC_steps_this_start)
                    ):
                        phaseC_last_hb = float(now_phasec)
                        phaseC_pct = (
                            int((100 * int(phaseC_completed_steps)) // max(1, int(phaseC_total_steps)))
                            if int(phaseC_total_steps) > 0
                            else 0
                        )
                        print(
                            f"{log_prefix} stage3-phaseC-heartbeat tier={tier_name} text={text_id} key_seed={key_seed} "
                            f"start={int(start_idx)}/{int(phaseC_start_keys_used)} "
                            f"source={start_source} "
                            f"step={int(_step + 1)}/{int(phaseC_steps_this_start)} pct={int(phaseC_pct)} "
                            f"evals={int(phaseC_evals)} accepts={int(phaseC_accepts)} improves={int(phaseC_improves)} "
                            f"lex_req={int(phaseC_lexical_requests)} "
                            f"lex_hit={int(phaseC_lexical_cache_hits)} "
                            f"lex_miss={int(phaseC_lexical_cache_misses)} "
                            f"lex_tie={int(phaseC_lexical_tiebreak_decisions)} "
                            f"best_match={fmt_finite_float_fn(local_best_match, digits=3)} "
                            f"best_score={fmt_finite_float_fn(local_best_score, digits=6)} "
                            f"shadow_plateau={int(phasec_shadow_stop_v1_state.get('plateau_would_stop', 0) or 0)} "
                            f"shadow_high_score={int(phasec_shadow_stop_v1_state.get('high_score_would_stop', 0) or 0)}",
                            flush=True,
                        )

                if str(start_lane) == "anchor":
                    anchor_best_key = list(map(int, local_best_key))
                    anchor_best_pt = np.asarray(local_best_pt, dtype=np.uint8).copy()
                    anchor_best_score = float(local_best_score)
                    anchor_best_match = float(local_best_match)
                    anchor_best_established = True
                elif bool(anchor_best_established):
                    overtook_anchor = int(
                        1
                        if _phasec_is_better(
                            cand_score=float(local_best_score),
                            cand_match=float(local_best_match),
                            cand_key=local_best_key,
                            cand_pt=local_best_pt,
                            best_score_v=float(anchor_best_score),
                            best_match_v=float(anchor_best_match),
                            best_key_v=anchor_best_key,
                            best_pt_v=anchor_best_pt,
                        )
                        else 0
                    )
                    if int(overtook_anchor) == 1:
                        phaseC_challenger_overtook_anchor_count += 1

                better_than_global = _phasec_is_better(
                    cand_score=float(local_best_score),
                    cand_match=float(local_best_match),
                    cand_key=local_best_key,
                    cand_pt=local_best_pt,
                    best_score_v=float(global_best_score),
                    best_match_v=float(global_best_match),
                    best_key_v=global_best_key,
                    best_pt_v=global_best_pt,
                )
                if better_than_global:
                    solved_before = bool(
                        np.isfinite(global_best_match)
                        and float(global_best_match) >= float(solve_match_threshold)
                    )
                    solved_after = bool(
                        np.isfinite(local_best_match)
                        and float(local_best_match) >= float(solve_match_threshold)
                    )
                    global_best_key = list(map(int, local_best_key))
                    global_best_pt = np.asarray(local_best_pt, dtype=np.uint8).copy()
                    global_best_score = float(local_best_score)
                    global_best_match = float(local_best_match)
                    phaseC_final_winner_lane = str(start_lane)
                    phaseC_final_winner_source = str(start_source)
                    if solved_after and (not solved_before):
                        stage3_solve_hits_delta = int(stage3_solve_hits_delta) + 1
                        print(
                            f"{log_prefix} stage3-solve-hit tier={tier_name} text={text_id} key_seed={key_seed} "
                            f"phase=phaseC match={float(global_best_match):.3f} score={float(global_best_score):.6f}",
                            flush=True,
                        )
                match_gain = (
                    float(local_best_match - init_match_start)
                    if np.isfinite(local_best_match) and np.isfinite(init_match_start)
                    else float("nan")
                )
                score_gain = (
                    float(local_best_score - init_score_start)
                    if np.isfinite(local_best_score) and np.isfinite(init_score_start)
                    else float("nan")
                )
                start_summary_row = dict(
                    start_idx=int(start_idx),
                    lane=str(start_lane),
                    source=str(start_source),
                    source_rank=int(start_source_rank),
                    candidate_hash=str(start_candidate_hash),
                    init_key_idx=list(map(int, start_key)),
                    init_plaintext_idx=list(
                        map(
                            int,
                            np.asarray(cur_pt, dtype=np.uint8).reshape(-1).tolist(),
                        )
                    ),
                    final_key_idx=list(map(int, local_best_key)),
                    final_plaintext_idx=list(
                        map(
                            int,
                            np.asarray(local_best_pt, dtype=np.uint8).reshape(-1).tolist(),
                        )
                    ),
                    selection_bucket=str(
                        start_row.get("selection_bucket", "legacy_fill")
                    ),
                    selected_by_novel_policy=int(
                        start_row.get("selected_by_novel_policy", 0) or 0
                    ),
                    selected_by_anchor_family_policy=int(
                        start_row.get("selected_by_anchor_family_policy", 0) or 0
                    ),
                    selected_by_phaseb_topk_anchor_policy=int(
                        start_row.get(
                            "selected_by_phaseb_topk_anchor_policy", 0
                        )
                        or 0
                    ),
                    eligible_novel_challenger=int(
                        start_row.get("eligible_novel_challenger", 0) or 0
                    ),
                    novelty_distance_to_anchor=(
                        int(start_row["novelty_distance_to_anchor"])
                        if start_row.get("novelty_distance_to_anchor") is not None
                        else None
                    ),
                    novelty_min_distance_to_selected_challenger=(
                        int(start_row["novelty_min_distance_to_selected_challenger"])
                        if start_row.get(
                            "novelty_min_distance_to_selected_challenger"
                        )
                        is not None
                        else None
                    ),
                    init_match=float(init_match_start),
                    init_score=float(init_score_start),
                    init_search_score=(
                        float(init_search_score_start)
                        if np.isfinite(init_search_score_start)
                        else None
                    ),
                    rescue_eligible=int(rescue_eligible),
                    rescue_skip_reason=str(rescue_skip_reason),
                    rescue_attempted=int(rescue_attempted),
                    rescue_applied=int(rescue_applied),
                    rescue_target_mode=str(phaseC_rescue_target_mode_cfg),
                    rescue_selector_mode=str(phaseC_rescue_selector_mode_cfg),
                    rescue_target_slice=(
                        int(rescue_target_slice)
                        if rescue_target_slice is not None
                        else None
                    ),
                    rescue_slice_reason=str(rescue_slice_reason),
                    rescue_slice_score=(
                        float(rescue_slice_score)
                        if np.isfinite(rescue_slice_score)
                        else None
                    ),
                    rescue_slice_score_per_char=(
                        float(rescue_slice_score_per_char)
                        if np.isfinite(rescue_slice_score_per_char)
                        else None
                    ),
                    rescue_probe_score_gain=(
                        float(rescue_probe_score_gain)
                        if np.isfinite(rescue_probe_score_gain)
                        else None
                    ),
                    rescue_guard_search_base_score=(
                        float(rescue_guard_search_base_score)
                        if np.isfinite(rescue_guard_search_base_score)
                        else None
                    ),
                    rescue_guard_search_best_score=(
                        float(rescue_guard_search_best_score)
                        if np.isfinite(rescue_guard_search_best_score)
                        else None
                    ),
                    rescue_guard_search_passed=int(rescue_guard_search_passed),
                    rescue_landing_type=str(rescue_landing_type),
                    rescue_landing_step=int(rescue_landing_step),
                    rescue_landing_parent_type=str(rescue_landing_parent_type),
                    rescue_landing_swap_a=(
                        int(rescue_landing_swap_a)
                        if rescue_landing_swap_a is not None
                        else None
                    ),
                    rescue_landing_swap_b=(
                        int(rescue_landing_swap_b)
                        if rescue_landing_swap_b is not None
                        else None
                    ),
                    rescue_mini_search_pool_rows=int(rescue_mini_search_pool_rows),
                    rescue_polish_steps_used=int(rescue_polish_steps_used),
                    rescue_post_match=(
                        float(rescue_post_match)
                        if rescue_post_match is not None
                        else None
                    ),
                    rescue_post_score=(
                        float(rescue_post_score)
                        if rescue_post_score is not None
                        else None
                    ),
                    rescue_match_gain=(
                        float(rescue_match_gain)
                        if np.isfinite(rescue_match_gain)
                        else None
                    ),
                    rescue_score_gain=(
                        float(rescue_score_gain)
                        if np.isfinite(rescue_score_gain)
                        else None
                    ),
                    rescue_lexical_requests_delta=int(rescue_lexical_requests_delta),
                    rescue_lexical_cache_hits_delta=int(
                        rescue_lexical_cache_hits_delta
                    ),
                    rescue_lexical_cache_misses_delta=int(
                        rescue_lexical_cache_misses_delta
                    ),
                    rescue_lexical_tiebreak_decisions_delta=int(
                        rescue_lexical_tiebreak_decisions_delta
                    ),
                    rescue_lexical_budget_skips_delta=int(
                        rescue_lexical_budget_skips_delta
                    ),
                    rescue_lexical_threshold_skips_delta=int(
                        rescue_lexical_threshold_skips_delta
                    ),
                    rescue_became_global_best=int(rescue_became_global_best),
                    final_match=float(local_best_match),
                    final_score=float(local_best_score),
                    match_gain=float(match_gain),
                    score_gain=float(score_gain),
                    accepts_delta=int(int(phaseC_accepts) - int(start_accepts_before)),
                    improves_delta=int(
                        int(phaseC_improves) - int(start_improves_before)
                    ),
                    lexical_requests_delta=int(
                        int(phaseC_lexical_requests)
                        - int(start_lexical_requests_before)
                    ),
                    lexical_cache_hits_delta=int(
                        int(phaseC_lexical_cache_hits)
                        - int(start_lexical_cache_hits_before)
                    ),
                    lexical_cache_misses_delta=int(
                        int(phaseC_lexical_cache_misses)
                        - int(start_lexical_cache_misses_before)
                    ),
                    lexical_tiebreak_decisions_delta=int(
                        int(phaseC_lexical_tiebreak_decisions)
                        - int(start_lexical_tie_before)
                    ),
                    lexical_budget_skips_delta=int(
                        int(phaseC_lexical_budget_skips)
                        - int(start_lexical_budget_skip_before)
                    ),
                    lexical_threshold_skips_delta=int(
                        int(phaseC_lexical_threshold_skips)
                        - int(start_lexical_threshold_skip_before)
                    ),
                    improved_vs_init=int(
                        1
                        if (
                            np.isfinite(float(local_best_match))
                            and np.isfinite(float(init_match_start))
                            and float(local_best_match) > float(init_match_start)
                        )
                        else 0
                    ),
                    overtook_anchor=int(overtook_anchor),
                    became_global_best=int(1 if bool(better_than_global) else 0),
                    shadow_stop_v1=dict(phasec_shadow_stop_v1_state),
                )
                phaseC_start_summaries.append(dict(start_summary_row))
                phaseC_checkpoint_rows_written += int(
                    append_phasec_start_checkpoint(
                        path=phasec_start_checkpoint_path,
                        row=build_phasec_start_checkpoint_row(
                            run_id=(
                                Path(phasec_start_checkpoint_path).parent.name
                                if phasec_start_checkpoint_path is not None
                                else ""
                            ),
                            tier_name=str(tier_name),
                            text_id=int(text_id),
                            key_seed=int(key_seed),
                            summary_row=start_summary_row,
                        ),
                        append_jsonl_row_fn=append_jsonl_row_fn,
                    )
                )
                print(
                    f"{log_prefix} stage3-phaseC-finish-start tier={tier_name} text={text_id} key_seed={key_seed} "
                    f"start={int(start_idx)}/{int(phaseC_start_keys_used)} "
                    f"lane={start_lane} "
                    f"source={start_source} source_rank={int(start_source_rank)} "
                    f"candidate_hash={start_candidate_hash} "
                    f"init_match={fmt_finite_float_fn(init_match_start, digits=3)} "
                    f"final_match={fmt_finite_float_fn(local_best_match, digits=3)} "
                    f"match_gain={fmt_finite_float_fn(match_gain, digits=3)} "
                    f"init_score={fmt_finite_float_fn(init_score_start, digits=6)} "
                    f"final_score={fmt_finite_float_fn(local_best_score, digits=6)} "
                    f"score_gain={fmt_finite_float_fn(score_gain, digits=6)} "
                    f"accepts_delta={int(int(phaseC_accepts) - int(start_accepts_before))} "
                    f"improves_delta={int(int(phaseC_improves) - int(start_improves_before))} "
                    f"lex_req_delta={int(int(phaseC_lexical_requests) - int(start_lexical_requests_before))} "
                    f"lex_budget_skip_delta={int(int(phaseC_lexical_budget_skips) - int(start_lexical_budget_skip_before))} "
                    f"lex_threshold_skip_delta={int(int(phaseC_lexical_threshold_skips) - int(start_lexical_threshold_skip_before))} "
                    f"rescue_polish_steps={int(rescue_polish_steps_used)} "
                    f"overtook_anchor={int(overtook_anchor)} "
                    f"became_global_best={int(1 if bool(better_than_global) else 0)} "
                    f"shadow_plateau={int(phasec_shadow_stop_v1_state.get('plateau_would_stop', 0) or 0)} "
                    f"shadow_high_score={int(phasec_shadow_stop_v1_state.get('high_score_would_stop', 0) or 0)}",
                    flush=True,
                )

            improved_vs_best3 = _phasec_is_better(
                cand_score=float(global_best_score),
                cand_match=float(global_best_match),
                cand_key=global_best_key,
                cand_pt=global_best_pt,
                best_score_v=float(best3_score),
                best_match_v=float(best3_match),
                best_key_v=(list(map(int, best3_key)) if best3_key is not None else global_best_key),
                best_pt_v=(np.asarray(pt3, dtype=np.uint8) if int(pt3.size) > 0 else global_best_pt),
            )
            phaseC_improved_best = int(1 if bool(improved_vs_best3) else 0)
            if improved_vs_best3:
                best3_score = float(global_best_score)
                best3_match = float(global_best_match)
                best3_key = list(map(int, global_best_key))
                pt3 = np.asarray(global_best_pt, dtype=np.uint8).copy()

            stage_rows.append(
                dict(
                    tier=tier_name,
                    text_id=int(text_id),
                    key_seed=int(key_seed),
                    stage="stage3_phaseC",
                    phaseC_enabled=int(1 if bool(phaseC_enabled_cfg) else 0),
                    phaseC_start_keys_used=int(phaseC_start_keys_used),
                    phaseC_start_policy=str(phaseC_start_policy_cfg),
                    phaseC_candidate_pool_count=int(phaseC_candidate_pool_count),
                    phaseC_candidate_pool_unique_keys=int(phaseC_candidate_pool_unique_keys),
                    phaseC_candidate_pool_unique_end_hash=int(
                        phaseC_candidate_pool_unique_end_hash
                    ),
                    phaseC_start_unique_end_hash=int(phaseC_start_unique_end_hash),
                    phaseC_candidate_pool_source_counts=dict(
                        phaseC_candidate_pool_source_counts
                    ),
                    phaseC_novel_view_id=str(phaseC_novel_view_id),
                    phaseC_anchor_candidate_hash=str(phaseC_anchor_candidate_hash),
                    phaseC_candidate_pool_eligible_novel_count=int(
                        phaseC_candidate_pool_eligible_novel_count
                    ),
                    phaseC_candidate_pool_eligible_novel_row_count=int(
                        phaseC_candidate_pool_eligible_novel_row_count
                    ),
                    phaseC_candidate_pool_eligible_novel_source_counts=dict(
                        phaseC_candidate_pool_eligible_novel_source_counts
                    ),
                    phaseC_start_source_counts=dict(phaseC_start_source_counts),
                    phaseC_start_eligible_novel_count=int(
                        phaseC_start_eligible_novel_count
                    ),
                    phaseC_selected_novel_challenger_count=int(
                        phaseC_selected_novel_challenger_count
                    ),
                    phaseC_eligible_novel_not_selected_count=int(
                        phaseC_eligible_novel_not_selected_count
                    ),
                    phaseC_selected_novel_challenger_hashes=list(
                        phaseC_selected_novel_challenger_hashes
                    ),
                    phaseC_steps=int(phaseC_steps_cfg),
                    phaseC_proposals_per_step=int(phaseC_proposals_per_step_cfg),
                    phaseC_lexical_min_match=float(phaseC_lexical_min_match_cfg),
                    phaseC_evals=int(phaseC_evals),
                    phaseC_accepts=int(phaseC_accepts),
                    phaseC_improves=int(phaseC_improves),
                    phaseC_improved_best=int(phaseC_improved_best),
                    phaseC_checkpoint_jsonl_name=str(phaseC_checkpoint_jsonl_name),
                    phaseC_checkpoint_rows_written=int(
                        phaseC_checkpoint_rows_written
                    ),
                    phaseC_rescue_enabled=int(phaseC_rescue_enabled_cfg),
                    phaseC_rescue_ran=int(phaseC_rescue_ran),
                    phaseC_rescue_starts_attempted=int(
                        phaseC_rescue_starts_attempted
                    ),
                    phaseC_rescue_applied_starts=int(
                        phaseC_rescue_applied_starts
                    ),
                    phaseC_rescue_target_mode=str(phaseC_rescue_target_mode_cfg),
                    phaseC_rescue_selector_mode=str(
                        phaseC_rescue_selector_mode_cfg
                    ),
                    phaseC_rescue_candidates=int(phaseC_rescue_candidates_cfg),
                    phaseC_rescue_slip_swaps=int(phaseC_rescue_slip_swaps_cfg),
                    phaseC_rescue_mini_search_steps=int(
                        phaseC_rescue_mini_search_steps_cfg
                    ),
                    phaseC_rescue_mini_search_beam_width=int(
                        phaseC_rescue_mini_search_beam_width_cfg
                    ),
                    phaseC_rescue_mini_search_top_symbols=int(
                        phaseC_rescue_mini_search_top_symbols_cfg
                    ),
                    phaseC_rescue_mini_search_keep_all_rows=int(
                        phaseC_rescue_mini_search_keep_all_rows_cfg
                    ),
                    phaseC_rescue_polish_steps=int(phaseC_rescue_polish_steps_cfg),
                    phaseC_rescue_probe_evals=int(phaseC_rescue_probe_evals),
                    phaseC_rescue_evals=int(phaseC_rescue_evals),
                    phaseC_rescue_mini_search_evals=int(
                        phaseC_rescue_mini_search_evals
                    ),
                    phaseC_rescue_lexical_requests=int(
                        phaseC_rescue_lexical_requests
                    ),
                    phaseC_rescue_lexical_cache_hits=int(
                        phaseC_rescue_lexical_cache_hits
                    ),
                    phaseC_rescue_lexical_cache_misses=int(
                        phaseC_rescue_lexical_cache_misses
                    ),
                    phaseC_rescue_lexical_tiebreak_decisions=int(
                        phaseC_rescue_lexical_tiebreak_decisions
                    ),
                    phaseC_rescue_lexical_budget_skips=int(
                        phaseC_rescue_lexical_budget_skips
                    ),
                    phaseC_rescue_lexical_threshold_skips=int(
                        phaseC_rescue_lexical_threshold_skips
                    ),
                    phaseC_rescue_anchor_enabled=int(
                        phaseC_rescue_anchor_enabled_cfg
                    ),
                    phaseC_rescue_phaseb_topk_min_rank=int(
                        phaseC_rescue_phaseb_topk_min_rank_cfg
                    ),
                    phaseC_rescue_max_starts=int(phaseC_rescue_max_starts_cfg),
                    phaseC_rescue_eligible_starts=int(
                        phaseC_rescue_eligible_starts
                    ),
                    phaseC_rescue_search_score_max_drop=float(
                        phaseC_rescue_search_score_max_drop_cfg
                    ),
                    phaseC_rescue_guard_search_evals=int(
                        phaseC_rescue_guard_search_evals
                    ),
                    phaseC_rescue_guard_search_passes=int(
                        phaseC_rescue_guard_search_passes
                    ),
                    phaseC_rescue_guard_search_rejects=int(
                        phaseC_rescue_guard_search_rejects
                    ),
                    phaseC_anchor_lane_starts=int(phaseC_anchor_lane_starts),
                    phaseC_challenger_lane_starts=int(
                        phaseC_challenger_lane_starts
                    ),
                    phaseC_challenger_overtook_anchor_count=int(
                        phaseC_challenger_overtook_anchor_count
                    ),
                    phaseC_final_winner_lane=str(phaseC_final_winner_lane),
                    phaseC_final_winner_source=str(phaseC_final_winner_source),
                    phaseC_lexical_requests=int(phaseC_lexical_requests),
                    phaseC_lexical_cache_hits=int(phaseC_lexical_cache_hits),
                    phaseC_lexical_cache_misses=int(phaseC_lexical_cache_misses),
                    phaseC_lexical_tiebreak_decisions=int(phaseC_lexical_tiebreak_decisions),
                    phaseC_lexical_budget_skips=int(phaseC_lexical_budget_skips),
                    phaseC_lexical_threshold_skips=int(phaseC_lexical_threshold_skips),
                    score=float(best3_score),
                    match_ratio=float(best3_match),
                )
            )
            print(
                f"{log_prefix} stage3-phaseC tier={tier_name} text={text_id} key_seed={key_seed} "
                f"enabled={int(phaseC_enabled_effective)} start_keys={int(phaseC_start_keys_used)} "
                f"candidate_pool={int(phaseC_candidate_pool_count)} "
                f"candidate_pool_unique_end_hash={int(phaseC_candidate_pool_unique_end_hash)} "
                f"start_policy={phaseC_start_policy_cfg} "
                f"novel_view={phaseC_novel_view_id or 'off'} "
                f"eligible_novel_pool={int(phaseC_candidate_pool_eligible_novel_count)} "
                f"selected_novel={int(phaseC_selected_novel_challenger_count)} "
                f"eligible_novel_not_selected={int(phaseC_eligible_novel_not_selected_count)} "
                f"start_sources={phaseC_start_source_counts} "
                f"improved_best={int(phaseC_improved_best)} "
                f"steps={int(phaseC_steps_cfg)} proposals_per_step={int(phaseC_proposals_per_step_cfg)} "
                f"rescue_enabled={int(phaseC_rescue_enabled_cfg)} "
                f"rescue_anchor_enabled={int(phaseC_rescue_anchor_enabled_cfg)} "
                f"rescue_eligible_starts={int(phaseC_rescue_eligible_starts)} "
                f"rescue_starts={int(phaseC_rescue_starts_attempted)} "
                f"rescue_applied_starts={int(phaseC_rescue_applied_starts)} "
                f"rescue_target_mode={phaseC_rescue_target_mode_cfg} "
                f"rescue_selector_mode={phaseC_rescue_selector_mode_cfg} "
                f"rescue_probe_evals={int(phaseC_rescue_probe_evals)} "
                f"rescue_evals={int(phaseC_rescue_evals)} "
                f"rescue_mini_search_evals={int(phaseC_rescue_mini_search_evals)} "
                f"rescue_guard_search_evals={int(phaseC_rescue_guard_search_evals)} "
                f"rescue_guard_search_passes={int(phaseC_rescue_guard_search_passes)} "
                f"rescue_guard_search_rejects={int(phaseC_rescue_guard_search_rejects)} "
                f"challenger_overtook_anchor={int(phaseC_challenger_overtook_anchor_count)} "
                f"final_winner_lane={phaseC_final_winner_lane} "
                f"final_winner_source={phaseC_final_winner_source} "
                f"evals={int(phaseC_evals)} accepts={int(phaseC_accepts)} improves={int(phaseC_improves)} "
                f"lex_req={int(phaseC_lexical_requests)} "
                f"lex_hit={int(phaseC_lexical_cache_hits)} "
                f"lex_miss={int(phaseC_lexical_cache_misses)} "
                f"lex_tie={int(phaseC_lexical_tiebreak_decisions)} "
                f"lex_budget_skip={int(phaseC_lexical_budget_skips)} "
                f"lex_threshold_skip={int(phaseC_lexical_threshold_skips)} "
                f"checkpoint_rows={int(phaseC_checkpoint_rows_written)} "
                f"checkpoint_jsonl={phaseC_checkpoint_jsonl_name or 'off'} "
                f"best_match={fmt_finite_float_fn(best3_match, digits=3)} "
                f"best_score={fmt_finite_float_fn(best3_score, digits=6)}",
                flush=True,
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
        phaseB_family_preservation_policy=str(phaseB_family_preservation_policy_cfg),
        phaseB_family_view_id=str(phaseB_family_view_id_cfg),
        phaseB_family_reserved_slots=int(phaseB_family_reserved_slots_cfg),
        phaseB_family_count_in_top_band=int(phaseB_family_count_in_top_band),
        phaseB_family_preserved_count=int(phaseB_family_preserved_count),
        phaseB_family_reservation_applied=int(phaseB_family_reservation_applied),
        phaseB_selected_unique_end_hash=int(phaseB_selected_unique_end_hash),
        phaseB_downstream_selected_count=int(phaseB_downstream_selected_count),
        phaseB_downstream_selected_unique_end_hash=int(
            phaseB_downstream_selected_unique_end_hash
        ),
        phaseB_downstream_selected_summaries=[
            dict(row) for row in phaseB_downstream_selected_summaries
        ],
        phaseB_topk_saved_count=int(phaseB_topk_saved_count),
        phaseB_topk_saved_unique_end_hash=int(phaseB_topk_saved_unique_end_hash),
        phaseB_topk_saved_summaries=[
            dict(row) for row in phaseB_topk_saved_summaries
        ],
        phaseC_enabled_cfg=int(1 if bool(phaseC_enabled_cfg) else 0),
        phaseC_enabled_effective=int(phaseC_enabled_effective),
        phaseC_ran=int(phaseC_ran),
        phaseC_start_keys_used=int(phaseC_start_keys_used),
        phaseC_start_policy=str(phaseC_start_policy_cfg),
        phaseC_steps_cfg=int(phaseC_steps_cfg),
        phaseC_proposals_per_step_cfg=int(phaseC_proposals_per_step_cfg),
        phaseC_lexical_min_match_cfg=float(phaseC_lexical_min_match_cfg),
        phaseC_evals=int(phaseC_evals),
        phaseC_accepts=int(phaseC_accepts),
        phaseC_improves=int(phaseC_improves),
        phaseC_rescue_enabled_cfg=int(phaseC_rescue_enabled_cfg),
        phaseC_rescue_ran=int(phaseC_rescue_ran),
        phaseC_rescue_starts_attempted=int(phaseC_rescue_starts_attempted),
        phaseC_rescue_applied_starts=int(phaseC_rescue_applied_starts),
        phaseC_rescue_target_mode_cfg=str(phaseC_rescue_target_mode_cfg),
        phaseC_rescue_selector_mode_cfg=str(phaseC_rescue_selector_mode_cfg),
        phaseC_rescue_candidates_cfg=int(phaseC_rescue_candidates_cfg),
        phaseC_rescue_slip_swaps_cfg=int(phaseC_rescue_slip_swaps_cfg),
        phaseC_rescue_mini_search_steps_cfg=int(phaseC_rescue_mini_search_steps_cfg),
        phaseC_rescue_mini_search_beam_width_cfg=int(
            phaseC_rescue_mini_search_beam_width_cfg
        ),
        phaseC_rescue_mini_search_top_symbols_cfg=int(
            phaseC_rescue_mini_search_top_symbols_cfg
        ),
        phaseC_rescue_mini_search_keep_all_rows_cfg=int(
            phaseC_rescue_mini_search_keep_all_rows_cfg
        ),
        phaseC_rescue_polish_steps_cfg=int(phaseC_rescue_polish_steps_cfg),
        phaseC_rescue_probe_evals=int(phaseC_rescue_probe_evals),
        phaseC_rescue_evals=int(phaseC_rescue_evals),
        phaseC_rescue_mini_search_evals=int(phaseC_rescue_mini_search_evals),
        phaseC_rescue_anchor_enabled_cfg=int(phaseC_rescue_anchor_enabled_cfg),
        phaseC_rescue_phaseb_topk_min_rank_cfg=int(
            phaseC_rescue_phaseb_topk_min_rank_cfg
        ),
        phaseC_rescue_max_starts_cfg=int(phaseC_rescue_max_starts_cfg),
        phaseC_rescue_eligible_starts=int(phaseC_rescue_eligible_starts),
        phaseC_rescue_search_score_max_drop_cfg=float(
            phaseC_rescue_search_score_max_drop_cfg
        ),
        phaseC_rescue_guard_search_evals=int(phaseC_rescue_guard_search_evals),
        phaseC_rescue_guard_search_passes=int(phaseC_rescue_guard_search_passes),
        phaseC_rescue_guard_search_rejects=int(phaseC_rescue_guard_search_rejects),
        phaseC_rescue_lexical_requests=int(phaseC_rescue_lexical_requests),
        phaseC_rescue_lexical_cache_hits=int(phaseC_rescue_lexical_cache_hits),
        phaseC_rescue_lexical_cache_misses=int(
            phaseC_rescue_lexical_cache_misses
        ),
        phaseC_rescue_lexical_tiebreak_decisions=int(
            phaseC_rescue_lexical_tiebreak_decisions
        ),
        phaseC_rescue_lexical_budget_skips=int(phaseC_rescue_lexical_budget_skips),
        phaseC_rescue_lexical_threshold_skips=int(
            phaseC_rescue_lexical_threshold_skips
        ),
        phaseC_lexical_requests=int(phaseC_lexical_requests),
        phaseC_lexical_cache_hits=int(phaseC_lexical_cache_hits),
        phaseC_lexical_cache_misses=int(phaseC_lexical_cache_misses),
        phaseC_lexical_tiebreak_decisions=int(phaseC_lexical_tiebreak_decisions),
        phaseC_lexical_budget_skips=int(phaseC_lexical_budget_skips),
        phaseC_lexical_threshold_skips=int(phaseC_lexical_threshold_skips),
        phaseC_candidate_pool_count=int(phaseC_candidate_pool_count),
        phaseC_candidate_pool_unique_keys=int(phaseC_candidate_pool_unique_keys),
        phaseC_candidate_pool_unique_end_hash=int(
            phaseC_candidate_pool_unique_end_hash
        ),
        phaseC_candidate_pool_source_counts=dict(phaseC_candidate_pool_source_counts),
        phaseC_candidate_pool_rows=[
            dict(row) for row in list(phaseC_candidate_pool_rows or [])
        ],
        phaseC_novel_view_id=str(phaseC_novel_view_id),
        phaseC_anchor_candidate_hash=str(phaseC_anchor_candidate_hash),
        phaseC_candidate_pool_eligible_novel_count=int(
            phaseC_candidate_pool_eligible_novel_count
        ),
        phaseC_candidate_pool_eligible_novel_row_count=int(
            phaseC_candidate_pool_eligible_novel_row_count
        ),
        phaseC_candidate_pool_eligible_novel_source_counts=dict(
            phaseC_candidate_pool_eligible_novel_source_counts
        ),
        phaseC_start_source_counts=dict(phaseC_start_source_counts),
        phaseC_start_unique_end_hash=int(phaseC_start_unique_end_hash),
        phaseC_start_eligible_novel_count=int(phaseC_start_eligible_novel_count),
        phaseC_selected_novel_challenger_count=int(
            phaseC_selected_novel_challenger_count
        ),
        phaseC_eligible_novel_not_selected_count=int(
            phaseC_eligible_novel_not_selected_count
        ),
        phaseC_selected_novel_challenger_hashes=list(
            phaseC_selected_novel_challenger_hashes
        ),
        phaseC_improved_best=int(phaseC_improved_best),
        phaseC_checkpoint_jsonl_name=str(phaseC_checkpoint_jsonl_name),
        phaseC_checkpoint_rows_written=int(phaseC_checkpoint_rows_written),
        phaseC_anchor_lane_starts=int(phaseC_anchor_lane_starts),
        phaseC_challenger_lane_starts=int(phaseC_challenger_lane_starts),
        phaseC_challenger_overtook_anchor_count=int(
            phaseC_challenger_overtook_anchor_count
        ),
        phaseC_final_winner_lane=str(phaseC_final_winner_lane),
        phaseC_final_winner_source=str(phaseC_final_winner_source),
        phaseC_start_summaries=[dict(row) for row in phaseC_start_summaries],
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
