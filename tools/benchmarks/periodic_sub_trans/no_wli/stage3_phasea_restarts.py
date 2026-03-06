from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Sequence

import numpy as np

from rune_decrypter_prime.api import KeySpec, SolverSpec, by_name, run

from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    decrypt_and_score_keys_chunked,
)


def run_stage3_phasea_restarts(
    *,
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
    order: str,
    alphabet_size: int,
    phaseA_cfg: Dict[str, Any],
    scorer_stage3_phaseA: Dict[str, Any],
    scorer_stage3_phaseA_runtime: Any,
    stage3_heartbeat_seconds: float,
    stage3_heartbeat_min_step: int,
    stage3_heartbeat_min_elapsed_seconds: float,
    stage3_phaseA_hb_state: Dict[str, Any],
    solve_match_threshold: float,
    stage3_continue_after_solve: bool,
    batch_eval_chunk_size: int,
    require_batch_scoring: bool,
    extract_kaeding_metrics_fn: Callable[[Any], Dict[str, float]],
    solution_span_counter_summary_fn: Callable[[Any], Dict[str, float]],
    stage3_progress_logging_fn: Callable[..., Dict[str, Any]],
    match_ratio_fn: Callable[[Sequence[int], Sequence[int]], float],
    key_hash_fn: Callable[[Sequence[int]], str],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    phaseA_rows: List[Dict[str, Any]] = []
    stage_rows: List[Dict[str, Any]] = []
    phaseA_stop_on_solve = False
    phaseA_total_runs = int(len(init3))
    stage3_solve_hits_delta = 0
    dt3_delta = 0.0
    ev3_delta = 0
    span_phaseA_eval_total = 0.0
    span_phaseA_eval_active = 0.0
    span_phaseA_eval_skipped = 0.0
    span_phaseA_seconds_total = 0.0
    span_phaseA_seconds_active = 0.0

    phaseA_seed_keys = [list(map(int, seed_key)) for seed_key in init3]
    phaseA_start_pts, phaseA_start_scores, _phaseA_batch_stats = decrypt_and_score_keys_chunked(
        cipher=full_cipher,
        ciphertext=np.asarray(ct_idx, dtype=np.uint8),
        keys=phaseA_seed_keys,
        scorer=scorer_stage3_phaseA_runtime,
        wli=None,
        chunk_size=int(batch_eval_chunk_size),
        require_batch=bool(require_batch_scoring),
    )
    for restart_idx, seed_key in enumerate(init3):
        seed_key_arr = np.asarray(seed_key, dtype=np.int16).reshape(-1)
        start_pt = (
            np.asarray(phaseA_start_pts[restart_idx], dtype=np.uint8).reshape(-1)
            if restart_idx < len(phaseA_start_pts)
            else np.asarray(
                full_cipher.decrypt_single(
                    ciphertext=np.asarray(ct_idx, dtype=np.uint8),
                    key=seed_key_arr,
                ),
                dtype=np.uint8,
            ).reshape(-1)
        )
        start_score = (
            float(phaseA_start_scores[restart_idx])
            if restart_idx < int(phaseA_start_scores.size)
            else float("nan")
        )
        start_hash = key_hash_fn(seed_key_arr.astype(int).tolist())
        seed_offset = int((restart_idx + 1) * 10007)

        cfg_i = dict(phaseA_cfg)
        cfg_i["seed"] = int(base_seed + seed_offset)

        phaseA_evals_base = int(ev3_delta)
        t_run = time.time()
        stage3_phasea_logging_cfg = stage3_progress_logging_fn(
            tier_name=str(tier_name),
            text_id=int(text_id),
            key_seed=int(key_seed),
            phase="phaseA",
            phase_steps=int(cfg_i.get("steps", 0) or 0),
            phase_start_ts=float(t_run),
            heartbeat_seconds=float(stage3_heartbeat_seconds),
            heartbeat_state=stage3_phaseA_hb_state,
            min_step=int(stage3_heartbeat_min_step),
            min_elapsed_seconds=float(stage3_heartbeat_min_elapsed_seconds),
            evals_base=int(phaseA_evals_base),
            phaseA_done=int(restart_idx),
            phaseA_total=int(phaseA_total_runs),
        )
        sol_i = run(
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
            solver=SolverSpec.kaeding(**cfg_i),
            scorer_params=dict(scorer_stage3_phaseA),
            logging=stage3_phasea_logging_cfg,
            wli_data=[],
            encoding_dir=direction,
            telemetry_on=True,
            force_no_wli=True,
            initial_keys=[seed_key_arr.astype(int).tolist()],
        )
        dt_run = float(time.time() - t_run)
        dt3_delta += float(dt_run)
        ev_i = int((getattr(sol_i, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
        ev3_delta += int(ev_i)

        pt_i = np.asarray(getattr(sol_i, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
        k_i_arr = np.asarray(getattr(sol_i, "key", []) or [], dtype=np.int16).reshape(-1)
        end_key_list = seed_key_arr.astype(int).tolist()
        if k_i_arr.size == int(key_len):
            end_key_list = k_i_arr.astype(int).tolist()
        end_hash = key_hash_fn(end_key_list)
        end_score_raw = float(getattr(sol_i, "score", float("nan")))
        end_match = (
            float(
                match_ratio_fn(
                    np.asarray(pt_i, dtype=np.uint8).astype(int).tolist(),
                    np.asarray(pt_idx, dtype=np.uint8).astype(int).tolist(),
                )
            )
            if pt_i.size > 0
            else float("nan")
        )

        tele_i = (getattr(sol_i, "meta", {}) or {}).get("telemetry", {})
        kaeding_i = tele_i.get("kaeding", {}) if isinstance(tele_i, dict) else {}
        mm_i = extract_kaeding_metrics_fn(kaeding_i)
        span_i = solution_span_counter_summary_fn(sol_i)
        span_phaseA_eval_total += float(span_i["total"])
        span_phaseA_eval_active += float(span_i["active"])
        span_phaseA_eval_skipped += float(span_i["skipped"])
        span_phaseA_seconds_total += float(span_i["seconds_total"])
        span_phaseA_seconds_active += float(span_i["seconds_active"])

        phaseA_rows.append(
            dict(
                restart_idx=int(restart_idx),
                seed_offset=int(seed_offset),
                start_hash=str(start_hash),
                end_hash=str(end_hash),
                start_score_search=float(start_score),
                start_score_pct=float("nan"),
                end_score_raw=float(end_score_raw),
                end_score_search=float(end_score_raw),
                end_score_pct=float("nan"),
                best_delta_pct=float("nan"),
                end_match=float(end_match),
                end_key=list(map(int, end_key_list)),
                start_plaintext=start_pt.astype(int).tolist(),
                end_plaintext=pt_i.astype(int).tolist(),
                metrics=mm_i,
            )
        )
        if np.isfinite(end_match) and float(end_match) >= float(solve_match_threshold):
            stage3_solve_hits_delta = int(stage3_solve_hits_delta) + 1
            print(
                f"{log_prefix} stage3-solve-hit tier={tier_name} text={int(text_id)} "
                f"key_seed={int(key_seed)} phase=phaseA restart={int(restart_idx)} "
                f"match={float(end_match):.3f} score_raw={float(end_score_raw):.6f}",
                flush=True,
            )
            if not bool(stage3_continue_after_solve):
                phaseA_stop_on_solve = True
        stage_rows.append(
            dict(
                tier=str(tier_name),
                text_id=int(text_id),
                key_seed=int(key_seed),
                stage="stage3_phaseA_restart",
                restart_idx=int(restart_idx),
                seed_offset=int(seed_offset),
                start_hash=str(start_hash),
                end_hash=str(end_hash),
                start_score=float(start_score),
                end_score_raw=float(end_score_raw),
                end_score_pct=float("nan"),
                score=float("nan"),
                best_delta=float("nan"),
                match_ratio=float(end_match),
                seconds=round(dt_run, 3),
                evals=int(ev_i),
                slip_count=int(mm_i["slip_count"]),
                slip_accept_count=int(mm_i["slip_accept_count"]),
                slip_accept_rate=float(mm_i["slip_accept_rate"]),
                accept_rate=float(mm_i["accept_rate"]),
            )
        )
        if phaseA_stop_on_solve:
            break

    return dict(
        phaseA_rows=phaseA_rows,
        stage_rows=stage_rows,
        stage3_solve_hits_delta=int(stage3_solve_hits_delta),
        dt3_delta=float(dt3_delta),
        ev3_delta=int(ev3_delta),
        span_phaseA_eval_total=float(span_phaseA_eval_total),
        span_phaseA_eval_active=float(span_phaseA_eval_active),
        span_phaseA_eval_skipped=float(span_phaseA_eval_skipped),
        span_phaseA_seconds_total=float(span_phaseA_seconds_total),
        span_phaseA_seconds_active=float(span_phaseA_seconds_active),
    )
