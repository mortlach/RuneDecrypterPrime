from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    decrypt_and_score_keys_chunked,
    score_plaintexts_chunked,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_search import (
    run_slice_local_mini_search,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_selector import (
    select_guard_passing_row,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage35_candidate_archive import (
    apply_frozen_columns_tail,
    build_stage35_seed_archive,
    stable_key_hash,
    substitution_prefix_len,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage35_ranking import (
    dedupe_stage35_rows,
    rank_stage35_rows,
    stage35_archive_diversity,
)
from tools.benchmarks.periodic_sub_trans.no_wli.shadow_stop_v1 import (
    build_shadow_stop_v1_state,
    update_shadow_stop_v1_state,
)


STAGE35_SHADOW_STOP_V1_PLATEAU_MINI_SEARCHES = 6
STAGE35_SHADOW_STOP_V1_HIGH_SCORE_FLOOR = 0.25
STAGE35_SHADOW_STOP_V1_HIGH_SCORE_STABLE_MINI_SEARCHES = 2
STAGE35_SHADOW_STOP_V1_SCORE_IMPROVE_EPS = 1.0e-6


DEFAULT_STAGE35_SOLVER_CFG: dict[str, Any] = {
    "seed_keep": 6,
    "beam_width": 6,
    "archive_keep": 24,
    "rounds": 4,
    "mini_search_steps": 2,
    "mini_search_beam_width": 4,
    "mini_search_top_symbols": 10,
    "mini_search_final_keep": 2,
    "mini_search_keep_all_rows": 0,
    "accept_score_min_gain": 0,
    "accept_search_score_max_drop": 0,
    "accept_guard_passing_selector_mode": "off",
    "accept_guard_passing_score_band_eps": 0.001,
}


def _empty_solver_telemetry() -> dict[str, Any]:
    return dict(
        row_scoring_input_keys_total=0,
        row_scoring_normalized_unique_keys_total=0,
        row_scoring_normalized_duplicate_keys_total=0,
        row_scoring_calls=0,
        row_scoring_keys_total=0,
        row_scoring_seconds=0.0,
        decrypt_seconds=0.0,
        batch_score_seconds=0.0,
        scorer_batch_calls=0,
        scorer_scalar_fallback_calls=0,
        scorer_candidates=0,
        row_scoring_candidate_hash_calls=0,
        row_scoring_candidate_hash_seconds=0.0,
        seed_scoring_seconds=0.0,
        seed_rank_seconds=0.0,
        beam_init_seconds=0.0,
        mini_search_count=0,
        mini_search_generation_seconds=0.0,
        mini_search_scoring_seconds=0.0,
        mini_search_ranking_seconds=0.0,
        mini_search_total_seconds=0.0,
        mini_search_proposals_generated=0,
        mini_search_duplicate_proposals_skipped=0,
        mini_search_rows_scored=0,
        mini_search_rows_kept=0,
        proposal_materialization_seconds=0.0,
        proposal_rows_materialized=0,
        proposal_candidate_hash_calls=0,
        proposal_candidate_hash_seconds=0.0,
        archive_update_seconds=0.0,
        archive_update_rows=0,
        archive_rank_seconds=0.0,
        beam_rank_seconds=0.0,
        max_archive_candidate_pool_size=0,
        shadow_stop_v1={},
        mini_search_summaries=[],
    )


def _int_cfg(cfg: Mapping[str, Any] | None) -> dict[str, Any]:
    merged = dict(DEFAULT_STAGE35_SOLVER_CFG)
    if cfg is not None:
        merged.update({str(k): v for k, v in dict(cfg).items()})
    out: dict[str, Any] = {}
    for key, value in merged.items():
        if str(key) in {
            "accept_score_min_gain",
            "accept_search_score_max_drop",
            "accept_guard_passing_score_band_eps",
            "max_runtime_seconds",
        }:
            out[str(key)] = float(value)
        elif str(key) in {"accept_guard_passing_selector_mode"}:
            out[str(key)] = str(value)
        else:
            out[str(key)] = int(value)
    return out


def _progress_ts() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _jsonify_progress_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonify_progress_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify_progress_value(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value).replace("\\", "/")
    return value


def _preview_stage35_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for row in list(rows or [])[: int(max(0, int(limit)))]:
        row_d = dict(row)
        preview.append(
            dict(
                candidate_hash=str(row_d.get("candidate_hash", "") or ""),
                seed_source=str(row_d.get("seed_source", "") or ""),
                stage3_source=str(row_d.get("stage3_source", "") or ""),
                lane=str(row_d.get("lane", "") or ""),
                source_rank=int(row_d.get("source_rank", 0) or 0),
                depth=int(row_d.get("depth", 0) or 0),
                target_slice=row_d.get("target_slice", None),
                move_type=str(row_d.get("move_type", "") or ""),
                score=float(row_d.get("score", float("nan"))),
                search_score=float(row_d.get("search_score", float("nan"))),
            )
        )
    return preview


def _finite_gte_with_margin(*, lhs: float, rhs: float, margin: float) -> bool:
    if np.isfinite(float(lhs)) and np.isfinite(float(rhs)):
        return bool(float(lhs) >= float(rhs) - float(margin))
    return bool(np.isfinite(float(lhs)) and not np.isfinite(float(rhs)))


def _finite_gt_with_margin(*, lhs: float, rhs: float, margin: float) -> bool:
    if np.isfinite(float(lhs)) and np.isfinite(float(rhs)):
        return bool(float(lhs) > float(rhs) + float(margin))
    return bool(np.isfinite(float(lhs)) and not np.isfinite(float(rhs)))


def _safe_float_or_nan(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return float(out)


def _truth_match_ratio(
    *,
    plaintext_idx: Sequence[int] | None,
    target_plaintext_idx: Sequence[int] | None,
) -> float:
    lhs = np.asarray(plaintext_idx if plaintext_idx is not None else [], dtype=np.uint8).reshape(
        -1
    )
    rhs = np.asarray(
        target_plaintext_idx if target_plaintext_idx is not None else [],
        dtype=np.uint8,
    ).reshape(-1)
    if int(lhs.size) <= 0 or int(lhs.size) != int(rhs.size):
        return float("nan")
    return float(np.mean(lhs == rhs))


def _score_rows_for_keys(
    *,
    keys: Sequence[Sequence[int]],
    ciphertext_idx: np.ndarray,
    cipher: Any,
    scorer_full: Any,
    scorer_search: Any,
    chunk_size: int,
    require_batch: bool,
    telemetry: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not keys:
        return []
    t0 = time.perf_counter()
    pts, full_scores, stats_obj = decrypt_and_score_keys_chunked(
        cipher=cipher,
        ciphertext=ciphertext_idx,
        keys=keys,
        scorer=scorer_full,
        wli=None,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
    )
    search_scores, stats_obj = score_plaintexts_chunked(
        scorer=scorer_search,
        plaintexts=pts,
        wli=None,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
        stats=stats_obj,
    )
    out: list[dict[str, Any]] = []
    hash_seconds = 0.0
    for idx, key_vals in enumerate(keys):
        pt = np.asarray(pts[idx], dtype=np.uint8).reshape(-1)
        t_hash = time.perf_counter()
        candidate_hash = stable_key_hash(key_vals)
        hash_seconds += float(time.perf_counter() - t_hash)
        out.append(
            dict(
                key=list(map(int, key_vals)),
                key_idx=list(map(int, key_vals)),
                pt=pt.astype(int).tolist(),
                plaintext_idx=pt.astype(int).tolist(),
                score=float(full_scores[idx]),
                search_score=float(search_scores[idx]),
                candidate_hash=str(candidate_hash),
            )
        )
    if telemetry is not None:
        telemetry["row_scoring_calls"] = int(telemetry.get("row_scoring_calls", 0) or 0) + 1
        telemetry["row_scoring_keys_total"] = int(
            telemetry.get("row_scoring_keys_total", 0) or 0
        ) + int(len(keys))
        telemetry["row_scoring_seconds"] = float(
            telemetry.get("row_scoring_seconds", 0.0) or 0.0
        ) + float(time.perf_counter() - t0)
        telemetry["decrypt_seconds"] = float(
            telemetry.get("decrypt_seconds", 0.0) or 0.0
        ) + float(stats_obj.decrypt_seconds)
        telemetry["batch_score_seconds"] = float(
            telemetry.get("batch_score_seconds", 0.0) or 0.0
        ) + float(stats_obj.score_seconds)
        telemetry["scorer_batch_calls"] = int(
            telemetry.get("scorer_batch_calls", 0) or 0
        ) + int(stats_obj.batch_calls)
        telemetry["scorer_scalar_fallback_calls"] = int(
            telemetry.get("scorer_scalar_fallback_calls", 0) or 0
        ) + int(stats_obj.scalar_fallback_calls)
        telemetry["scorer_candidates"] = int(
            telemetry.get("scorer_candidates", 0) or 0
        ) + int(stats_obj.candidates)
        telemetry["row_scoring_candidate_hash_calls"] = int(
            telemetry.get("row_scoring_candidate_hash_calls", 0) or 0
        ) + int(len(keys))
        telemetry["row_scoring_candidate_hash_seconds"] = float(
            telemetry.get("row_scoring_candidate_hash_seconds", 0.0) or 0.0
        ) + float(hash_seconds)
    return out


def _scoring_callback(
    *,
    ciphertext_idx: np.ndarray,
    cipher: Any,
    scorer_full: Any,
    scorer_search: Any,
    chunk_size: int,
    require_batch: bool,
    fixed_tail: Sequence[int],
    prefix_len: int,
    telemetry: dict[str, Any] | None = None,
) -> Callable[[Sequence[Sequence[int]]], Sequence[Mapping[str, Any]]]:
    def _score_key_rows(keys: Sequence[Sequence[int]]) -> Sequence[Mapping[str, Any]]:
        normalized_keys = [
            apply_frozen_columns_tail(
                key_vals=key_vals,
                prefix_len=int(prefix_len),
                frozen_tail=fixed_tail,
            )
            for key_vals in keys
        ]
        unique_keys: list[list[int]] = []
        unique_index_by_key: dict[tuple[int, ...], int] = {}
        row_unique_indices: list[int] = []
        for key_vals in normalized_keys:
            key_t = tuple(map(int, key_vals))
            unique_idx = unique_index_by_key.get(key_t, None)
            if unique_idx is None:
                unique_idx = int(len(unique_keys))
                unique_index_by_key[key_t] = int(unique_idx)
                unique_keys.append(list(map(int, key_vals)))
            row_unique_indices.append(int(unique_idx))
        if telemetry is not None:
            telemetry["row_scoring_input_keys_total"] = int(
                telemetry.get("row_scoring_input_keys_total", 0) or 0
            ) + int(len(normalized_keys))
            telemetry["row_scoring_normalized_unique_keys_total"] = int(
                telemetry.get("row_scoring_normalized_unique_keys_total", 0) or 0
            ) + int(len(unique_keys))
            telemetry["row_scoring_normalized_duplicate_keys_total"] = int(
                telemetry.get("row_scoring_normalized_duplicate_keys_total", 0) or 0
            ) + int(len(normalized_keys) - len(unique_keys))
        scored_unique_rows = _score_rows_for_keys(
            keys=unique_keys,
            ciphertext_idx=ciphertext_idx,
            cipher=cipher,
            scorer_full=scorer_full,
            scorer_search=scorer_search,
            chunk_size=int(chunk_size),
            require_batch=bool(require_batch),
            telemetry=telemetry,
        )
        return [
            dict(scored_unique_rows[int(unique_idx)])
            for unique_idx in row_unique_indices
        ]

    return _score_key_rows


def _slice_hamming(
    *,
    key_a: Sequence[int],
    key_b: Sequence[int],
    slice_idx: int,
    alphabet_size: int,
) -> int:
    lo = int(slice_idx) * int(alphabet_size)
    hi = int(lo + int(alphabet_size))
    lhs = list(map(int, key_a[lo:hi]))
    rhs = list(map(int, key_b[lo:hi]))
    return int(sum(1 for av, bv in zip(lhs, rhs) if int(av) != int(bv)))


def _choose_probe_seed(
    *,
    current_key: Sequence[int],
    seed_rows: Sequence[Mapping[str, Any]],
    slice_idx: int,
    alphabet_size: int,
) -> dict[str, Any]:
    differing: list[dict[str, Any]] = []
    for row in seed_rows:
        key_vals = list(map(int, row.get("key_idx", []) or []))
        if not key_vals:
            continue
        slice_hamming = _slice_hamming(
            key_a=current_key,
            key_b=key_vals,
            slice_idx=int(slice_idx),
            alphabet_size=int(alphabet_size),
        )
        if int(slice_hamming) <= 0:
            continue
        differing.append(
            dict(
                row,
                probe_slice_hamming=int(slice_hamming),
            )
        )
    if differing:
        differing = sorted(
            differing,
            key=lambda row: (
                -int(row.get("probe_slice_hamming", 0) or 0),
                int(
                    99
                    if row.get("seed_priority_group", 99) is None
                    else row.get("seed_priority_group", 99)
                ),
                int(
                    99
                    if row.get("seed_priority_rank", 99) is None
                    else row.get("seed_priority_rank", 99)
                ),
                str(row.get("seed_source", "") or ""),
                tuple(map(int, row.get("key_idx", []) or [])),
            ),
        )
        return dict(differing[0])
    return dict(seed_rows[0]) if seed_rows else {}


def _score_seed_rows(
    *,
    seed_rows: Sequence[Mapping[str, Any]],
    ciphertext_idx: np.ndarray,
    cipher: Any,
    scorer_full: Any,
    scorer_search: Any,
    chunk_size: int,
    require_batch: bool,
    prefix_len: int,
    fixed_tail: Sequence[int],
    telemetry: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    seed_keys = [
        apply_frozen_columns_tail(
            key_vals=row.get("key_idx", []) or [],
            prefix_len=int(prefix_len),
            frozen_tail=fixed_tail,
        )
        for row in seed_rows
    ]
    scored = _score_rows_for_keys(
        keys=seed_keys,
        ciphertext_idx=ciphertext_idx,
        cipher=cipher,
        scorer_full=scorer_full,
        scorer_search=scorer_search,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
        telemetry=telemetry,
    )
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(seed_rows):
        scored_row = dict(scored[idx])
        seed_row = dict(row)
        out.append(
            dict(
                scored_row,
                seed_source=str(seed_row.get("seed_source", "") or ""),
                stage3_source=str(seed_row.get("stage3_source", "") or ""),
                lane=str(seed_row.get("lane", "") or ""),
                source_rank=int(seed_row.get("source_rank", 0) or 0),
                stage3_rank=int(seed_row.get("stage3_rank", 0) or 0),
                seed_priority_group=int(
                    99
                    if seed_row.get("seed_priority_group", 99) is None
                    else seed_row.get("seed_priority_group", 99)
                ),
                seed_priority_rank=int(
                    99
                    if seed_row.get("seed_priority_rank", 99) is None
                    else seed_row.get("seed_priority_rank", 99)
                ),
                checkpoint_final_match=float(
                    seed_row.get("checkpoint_final_match", float("nan"))
                ),
                checkpoint_final_score=float(
                    seed_row.get("checkpoint_final_score", float("nan"))
                ),
                checkpoint_rescue_applied=int(
                    seed_row.get("checkpoint_rescue_applied", 0) or 0
                ),
                tail_was_normalized=int(seed_row.get("tail_was_normalized", 0) or 0),
                depth=0,
                target_slice=None,
                move_type="seed",
                parent_hash="",
                probe_seed_source="",
                probe_seed_rank=0,
                mini_search_step=0,
                mini_search_parent_type="seed",
                mini_search_swap_a=None,
                mini_search_swap_b=None,
            )
        )
    return out


def solve_stage35_substitution_only(
    *,
    ciphertext_idx: np.ndarray,
    seed_rows: Sequence[Mapping[str, Any]],
    period: int,
    alphabet_size: int,
    cipher: Any,
    scorer_full: Any,
    scorer_search: Any,
    cfg: Mapping[str, Any] | None = None,
    chunk_size: int,
    require_batch: bool,
    fixed_tail: Sequence[int],
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    raw_cfg = dict(cfg or {})
    solver_cfg = _int_cfg(cfg)
    prefix_len = int(
        substitution_prefix_len(period=int(period), alphabet_size=int(alphabet_size))
    )
    telemetry = _empty_solver_telemetry()
    max_runtime_seconds = float(raw_cfg.get("max_runtime_seconds", 0.0) or 0.0)
    max_evals = int(max(0, int(raw_cfg.get("max_evals", 0) or 0)))
    partial_dump_preview_rows = int(
        max(1, int(raw_cfg.get("partial_dump_preview_rows", 3) or 3))
    )
    if not seed_rows:
        return dict(
            archive_rows=[],
            seed_rows_scored=[],
            evals=0,
            rounds_completed=0,
            runtime_seconds=0.0,
            outcome_status="not_run_no_seed_rows",
            outcome_reason="no_seed_rows",
            completed=0,
            capped=0,
            prefix_len=int(prefix_len),
            fixed_tail=list(map(int, fixed_tail)),
            diversity=stage35_archive_diversity([], prefix_len=int(prefix_len)),
            telemetry=dict(
                telemetry,
                average_batch_size=0.0,
                average_proposals_generated_per_mini=0.0,
                average_rows_scored_per_mini=0.0,
                average_rows_kept_per_mini=0.0,
            ),
        )

    t0 = float(time.perf_counter())
    t_seed = time.perf_counter()
    seed_rows_scored = _score_seed_rows(
        seed_rows=seed_rows,
        ciphertext_idx=np.asarray(ciphertext_idx, dtype=np.uint8).reshape(-1),
        cipher=cipher,
        scorer_full=scorer_full,
        scorer_search=scorer_search,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
        prefix_len=int(prefix_len),
        fixed_tail=fixed_tail,
        telemetry=telemetry,
    )
    telemetry["seed_scoring_seconds"] = float(time.perf_counter() - t_seed)
    score_key_rows_fn = _scoring_callback(
        ciphertext_idx=np.asarray(ciphertext_idx, dtype=np.uint8).reshape(-1),
        cipher=cipher,
        scorer_full=scorer_full,
        scorer_search=scorer_search,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
        fixed_tail=fixed_tail,
        prefix_len=int(prefix_len),
        telemetry=telemetry,
    )

    t_seed_rank = time.perf_counter()
    ranked_seed_rows = sorted(
        (dict(row) for row in seed_rows_scored),
        key=lambda row: (
            int(
                99
                if row.get("seed_priority_group", 99) is None
                else row.get("seed_priority_group", 99)
            ),
            int(
                99
                if row.get("seed_priority_rank", 99) is None
                else row.get("seed_priority_rank", 99)
            ),
            -float(row.get("score", float("-inf"))),
            -float(row.get("search_score", float("-inf"))),
            tuple(map(int, row.get("key_idx", []) or [])),
        ),
    )
    ranked_seed_rows = dedupe_stage35_rows(ranked_seed_rows)
    telemetry["seed_rank_seconds"] = float(time.perf_counter() - t_seed_rank)
    if progress_callback is not None:
        progress_callback(
            dict(
                event="seed_rows_scored",
                seed_rows_scored_count=int(len(ranked_seed_rows)),
                elapsed_seconds=float(time.perf_counter() - t0),
            )
        )
    initial_seed_keep = int(max(1, int(solver_cfg.get("seed_keep", 6))))
    beam_width = int(max(1, int(solver_cfg.get("beam_width", 6))))
    archive_keep = int(max(1, int(solver_cfg.get("archive_keep", 24))))
    rounds = int(max(0, int(solver_cfg.get("rounds", 4))))
    mini_steps = int(max(1, int(solver_cfg.get("mini_search_steps", 2))))
    mini_beam_width = int(max(1, int(solver_cfg.get("mini_search_beam_width", 4))))
    mini_top_symbols = int(max(2, int(solver_cfg.get("mini_search_top_symbols", 10))))
    mini_final_keep = int(max(1, int(solver_cfg.get("mini_search_final_keep", 2))))
    mini_keep_all_rows = int(max(0, int(solver_cfg.get("mini_search_keep_all_rows", 0))))

    t_beam_init = time.perf_counter()
    beam_rows = rank_stage35_rows(ranked_seed_rows[:initial_seed_keep], limit=beam_width)
    archive_map: dict[tuple[int, ...], dict[str, Any]] = {
        tuple(map(int, row.get("key_idx", []) or [])): dict(row) for row in beam_rows
    }
    telemetry["beam_init_seconds"] = float(time.perf_counter() - t_beam_init)
    telemetry["max_archive_candidate_pool_size"] = int(len(archive_map))
    stage35_shadow_stop_v1_state = build_shadow_stop_v1_state(
        phase_name="stage35",
        plateau_work_units=int(STAGE35_SHADOW_STOP_V1_PLATEAU_MINI_SEARCHES),
        high_score_floor=float(STAGE35_SHADOW_STOP_V1_HIGH_SCORE_FLOOR),
        high_score_stable_work_units=int(
            STAGE35_SHADOW_STOP_V1_HIGH_SCORE_STABLE_MINI_SEARCHES
        ),
        score_improve_eps=float(STAGE35_SHADOW_STOP_V1_SCORE_IMPROVE_EPS),
        initial_score=(
            float(beam_rows[0].get("score", float("nan")))
            if beam_rows
            else float("nan")
        ),
        initial_match=float("nan"),
    )
    telemetry["shadow_stop_v1"] = dict(stage35_shadow_stop_v1_state)
    total_evals = 0
    mini_search_collected_rows_total = 0
    mini_search_rows_kept_total = 0
    rounds_completed = 0
    outcome_status = "completed"
    outcome_reason = ""

    def _cap_hit() -> tuple[bool, str, str]:
        elapsed = float(time.perf_counter() - t0)
        if float(max_runtime_seconds) > 0.0 and float(elapsed) >= float(
            max_runtime_seconds
        ):
            return True, "capped_runtime", "max_runtime_seconds"
        if int(max_evals) > 0 and int(total_evals) >= int(max_evals):
            return True, "capped_evals", "max_evals"
        return False, "", ""

    for round_idx in range(1, int(rounds) + 1):
        proposal_rows: list[dict[str, Any]] = []
        proposal_key_pool: set[tuple[int, ...]] = set()
        mini_searches_planned_round = int(len(beam_rows) * int(max(1, int(period))))
        mini_searches_done_round = 0
        round_capped = False
        for parent_row in beam_rows:
            current_key = list(map(int, parent_row.get("key_idx", []) or []))
            current_pt = np.asarray(
                parent_row.get("plaintext_idx", []) or [],
                dtype=np.uint8,
            ).reshape(-1)
            current_score = float(parent_row.get("score", float("nan")))
            current_search_score = float(parent_row.get("search_score", float("nan")))
            for slice_idx in range(int(max(1, int(period)))):
                cap_hit, cap_status, cap_reason = _cap_hit()
                if bool(cap_hit):
                    outcome_status = str(cap_status)
                    outcome_reason = str(cap_reason)
                    round_capped = True
                    break
                if progress_callback is not None:
                    progress_callback(
                        dict(
                            event="mini_search_start",
                            round_idx=int(round_idx),
                            rounds_total=int(rounds),
                            mini_search_index_round=int(mini_searches_done_round) + 1,
                            mini_searches_planned_round=int(
                                mini_searches_planned_round
                            ),
                            beam_rows_count=int(len(beam_rows)),
                            archive_rows_count=int(len(archive_map)),
                            total_evals=int(total_evals),
                            slice_idx=int(slice_idx),
                            parent_candidate_hash=str(
                                parent_row.get("candidate_hash", "") or "none"
                            ),
                            elapsed_seconds=float(time.perf_counter() - t0),
                        )
                    )
                probe_row = _choose_probe_seed(
                    current_key=current_key,
                    seed_rows=ranked_seed_rows,
                    slice_idx=int(slice_idx),
                    alphabet_size=int(alphabet_size),
                )
                probe_key = list(map(int, probe_row.get("key_idx", current_key) or current_key))
                probe_pt = np.asarray(
                    probe_row.get("plaintext_idx", current_pt.astype(int).tolist()) or current_pt.astype(int).tolist(),
                    dtype=np.uint8,
                ).reshape(-1)
                probe_score = float(probe_row.get("score", current_score))
                probe_search_score = float(probe_row.get("search_score", current_search_score))
                mini = run_slice_local_mini_search(
                    current_key=current_key,
                    current_pt=current_pt,
                    current_score=float(current_score),
                    current_search_score=float(current_search_score),
                    current_match=float("nan"),
                    probe_key=probe_key,
                    probe_pt=probe_pt,
                    probe_score=float(probe_score),
                    probe_search_score=float(probe_search_score),
                    probe_match=float("nan"),
                    target_slice=int(slice_idx),
                    ciphertext_idx=np.asarray(ciphertext_idx, dtype=np.uint8).reshape(-1),
                    period=int(period),
                    alphabet_size=int(alphabet_size),
                    top_symbols=int(mini_top_symbols),
                    beam_width=int(mini_beam_width),
                    steps=int(mini_steps),
                    final_keep=int(mini_final_keep),
                    keep_all_rows=bool(int(mini_keep_all_rows) == 1),
                    score_key_rows_fn=score_key_rows_fn,
                )
                mini_telemetry = dict(mini.get("telemetry", {}) or {})
                telemetry["mini_search_count"] = int(
                    telemetry.get("mini_search_count", 0) or 0
                ) + 1
                telemetry["mini_search_generation_seconds"] = float(
                    telemetry.get("mini_search_generation_seconds", 0.0) or 0.0
                ) + float(mini_telemetry.get("generation_seconds", 0.0) or 0.0)
                telemetry["mini_search_scoring_seconds"] = float(
                    telemetry.get("mini_search_scoring_seconds", 0.0) or 0.0
                ) + float(mini_telemetry.get("scoring_seconds", 0.0) or 0.0)
                telemetry["mini_search_ranking_seconds"] = float(
                    telemetry.get("mini_search_ranking_seconds", 0.0) or 0.0
                ) + float(mini_telemetry.get("ranking_seconds", 0.0) or 0.0)
                telemetry["mini_search_total_seconds"] = float(
                    telemetry.get("mini_search_total_seconds", 0.0) or 0.0
                ) + float(mini_telemetry.get("total_seconds", 0.0) or 0.0)
                telemetry["mini_search_proposals_generated"] = int(
                    telemetry.get("mini_search_proposals_generated", 0) or 0
                ) + int(mini_telemetry.get("proposals_generated", 0) or 0)
                telemetry["mini_search_duplicate_proposals_skipped"] = int(
                    telemetry.get("mini_search_duplicate_proposals_skipped", 0) or 0
                ) + int(
                    mini_telemetry.get("duplicate_proposals_skipped", 0) or 0
                )
                telemetry["mini_search_rows_scored"] = int(
                    telemetry.get("mini_search_rows_scored", 0) or 0
                ) + int(mini_telemetry.get("rows_scored", 0) or 0)
                telemetry["mini_search_rows_kept"] = int(
                    telemetry.get("mini_search_rows_kept", 0) or 0
                ) + int(mini_telemetry.get("rows_kept", 0) or 0)
                total_evals += int(mini.get("evals", 0) or 0)
                mini_search_collected_rows_total += int(
                    mini.get("collected_row_count", 0) or 0
                )
                mini_search_rows_kept_total += int(len(list(mini.get("rows", []) or [])))
                mini_searches_done_round += 1
                if progress_callback is not None and (
                    int(mini_searches_done_round) == 1
                    or int(mini_searches_done_round) == int(mini_searches_planned_round)
                    or int(mini_searches_done_round) % 8 == 0
                ):
                    progress_callback(
                        dict(
                            event="round_progress",
                            round_idx=int(round_idx),
                            rounds_total=int(rounds),
                            mini_searches_done_round=int(mini_searches_done_round),
                            mini_searches_planned_round=int(
                                mini_searches_planned_round
                            ),
                            beam_rows_count=int(len(beam_rows)),
                            archive_rows_count=int(len(archive_map)),
                            total_evals=int(total_evals),
                            elapsed_seconds=float(time.perf_counter() - t0),
                        )
                    )
                t_material = time.perf_counter()
                material_hash_seconds = 0.0
                for row in list(mini.get("rows", []) or []):
                    key_vals = apply_frozen_columns_tail(
                        key_vals=row.get("key", []) or row.get("key_idx", []) or [],
                        prefix_len=int(prefix_len),
                        frozen_tail=fixed_tail,
                    )
                    key_tuple = tuple(map(int, key_vals))
                    proposal_key_pool.add(key_tuple)
                    t_hash = time.perf_counter()
                    candidate_hash = stable_key_hash(key_vals)
                    material_hash_seconds += float(time.perf_counter() - t_hash)
                    proposal_rows.append(
                        dict(
                            key_idx=list(map(int, key_vals)),
                            plaintext_idx=list(map(int, row.get("pt", row.get("plaintext_idx", [])) or [])),
                            score=float(row.get("score", float("nan"))),
                            search_score=float(row.get("search_score", float("nan"))),
                            candidate_hash=str(candidate_hash),
                            seed_source=str(parent_row.get("seed_source", "") or ""),
                            stage3_source=str(parent_row.get("stage3_source", "") or ""),
                            lane=str(parent_row.get("lane", "") or ""),
                            source_rank=int(parent_row.get("source_rank", 0) or 0),
                            stage3_rank=int(parent_row.get("stage3_rank", 0) or 0),
                            seed_priority_group=int(
                                99
                                if parent_row.get("seed_priority_group", 99) is None
                                else parent_row.get("seed_priority_group", 99)
                            ),
                            seed_priority_rank=int(
                                99
                                if parent_row.get("seed_priority_rank", 99) is None
                                else parent_row.get("seed_priority_rank", 99)
                            ),
                            checkpoint_final_match=float(
                                parent_row.get("checkpoint_final_match", float("nan"))
                            ),
                            checkpoint_final_score=float(
                                parent_row.get("checkpoint_final_score", float("nan"))
                            ),
                            checkpoint_rescue_applied=int(
                                parent_row.get("checkpoint_rescue_applied", 0) or 0
                            ),
                            tail_was_normalized=int(
                                parent_row.get("tail_was_normalized", 0) or 0
                            ),
                            depth=int(round_idx),
                            target_slice=int(slice_idx),
                            move_type="slice_local_mini_search",
                            parent_hash=str(parent_row.get("candidate_hash", "") or ""),
                            probe_seed_source=str(
                                probe_row.get("seed_source", "") or ""
                            ),
                            probe_seed_rank=int(
                                0
                                if probe_row.get("seed_priority_rank", 0) is None
                                else probe_row.get("seed_priority_rank", 0)
                            ),
                            probe_slice_hamming=int(
                                probe_row.get("probe_slice_hamming", 0) or 0
                            ),
                            mini_search_step=int(
                                row.get("mini_search_step", 0) or 0
                            ),
                            mini_search_parent_type=str(
                                row.get("mini_search_parent_type", "") or ""
                            ),
                            mini_search_swap_a=row.get("mini_search_swap_a", None),
                            mini_search_swap_b=row.get("mini_search_swap_b", None),
                            mini_search_pool_rows=int(
                                mini.get("collected_row_count", 0) or 0
                            ),
                            mini_search_evals=int(mini.get("evals", 0) or 0),
                        )
                    )
                telemetry["proposal_materialization_seconds"] = float(
                    telemetry.get("proposal_materialization_seconds", 0.0) or 0.0
                ) + float(time.perf_counter() - t_material)
                telemetry["proposal_rows_materialized"] = int(
                    telemetry.get("proposal_rows_materialized", 0) or 0
                ) + int(len(list(mini.get("rows", []) or [])))
                telemetry["proposal_candidate_hash_calls"] = int(
                    telemetry.get("proposal_candidate_hash_calls", 0) or 0
                ) + int(len(list(mini.get("rows", []) or [])))
                telemetry["proposal_candidate_hash_seconds"] = float(
                    telemetry.get("proposal_candidate_hash_seconds", 0.0) or 0.0
                ) + float(material_hash_seconds)
                archive_candidate_pool_size_after_mini = int(
                    len(set(archive_map.keys()).union(proposal_key_pool))
                )
                mini_best_score = float(current_score)
                for row in list(mini.get("rows", []) or []):
                    row_score = _safe_float_or_nan(row.get("score", float("nan")))
                    if _finite_gt_with_margin(
                        lhs=float(row_score),
                        rhs=float(mini_best_score),
                        margin=0.0,
                    ):
                        mini_best_score = float(row_score)
                stage35_shadow_stop_v1_state = update_shadow_stop_v1_state(
                    stage35_shadow_stop_v1_state,
                    work_unit=int(telemetry.get("mini_search_count", 0) or 0),
                    evals_done=int(total_evals),
                    best_score=float(mini_best_score),
                    best_match=float("nan"),
                    progress_counter=int(
                        telemetry.get("mini_search_rows_kept", 0) or 0
                    ),
                    novelty_counter=int(archive_candidate_pool_size_after_mini),
                )
                telemetry["shadow_stop_v1"] = dict(stage35_shadow_stop_v1_state)
                telemetry["mini_search_summaries"].append(
                    dict(
                        round_idx=int(round_idx),
                        mini_search_index_round=int(mini_searches_done_round),
                        mini_searches_planned_round=int(mini_searches_planned_round),
                        slice_idx=int(slice_idx),
                        parent_candidate_hash=str(
                            parent_row.get("candidate_hash", "") or ""
                        ),
                        beam_rows_count_before_mini=int(len(beam_rows)),
                        archive_size_before_round=int(len(archive_map)),
                        archive_candidate_pool_size_after_mini=int(
                            archive_candidate_pool_size_after_mini
                        ),
                        proposals_generated=int(
                            mini_telemetry.get("proposals_generated", 0) or 0
                        ),
                        duplicate_proposals_skipped=int(
                            mini_telemetry.get("duplicate_proposals_skipped", 0) or 0
                        ),
                        rows_scored=int(mini_telemetry.get("rows_scored", 0) or 0),
                        rows_kept=int(mini_telemetry.get("rows_kept", 0) or 0),
                        collected_rows=int(mini.get("collected_row_count", 0) or 0),
                        active_position_count=int(
                            mini_telemetry.get("active_position_count", 0) or 0
                        ),
                        generation_seconds=float(
                            mini_telemetry.get("generation_seconds", 0.0) or 0.0
                        ),
                        scoring_seconds=float(
                            mini_telemetry.get("scoring_seconds", 0.0) or 0.0
                        ),
                        ranking_seconds=float(
                            mini_telemetry.get("ranking_seconds", 0.0) or 0.0
                        ),
                        total_seconds=float(
                            mini_telemetry.get("total_seconds", 0.0) or 0.0
                        ),
                        shadow_stop_v1=dict(stage35_shadow_stop_v1_state),
                    )
                )
                cap_hit, cap_status, cap_reason = _cap_hit()
                if bool(cap_hit):
                    outcome_status = str(cap_status)
                    outcome_reason = str(cap_reason)
                    round_capped = True
                    break
            if bool(round_capped):
                break
        if not proposal_rows:
            break
        rounds_completed = int(round_idx)
        t_archive_update = time.perf_counter()
        for row in proposal_rows:
            key_t = tuple(map(int, row.get("key_idx", []) or []))
            prev = archive_map.get(key_t, None)
            row_d = dict(row)
            if prev is None:
                archive_map[key_t] = row_d
            else:
                merged = dedupe_stage35_rows([prev, row_d])
                archive_map[key_t] = dict(merged[0])
        telemetry["archive_update_seconds"] = float(
            telemetry.get("archive_update_seconds", 0.0) or 0.0
        ) + float(time.perf_counter() - t_archive_update)
        telemetry["archive_update_rows"] = int(
            telemetry.get("archive_update_rows", 0) or 0
        ) + int(len(proposal_rows))
        telemetry["max_archive_candidate_pool_size"] = int(
            max(
                int(telemetry.get("max_archive_candidate_pool_size", 0) or 0),
                int(len(archive_map)),
            )
        )
        t_archive_rank = time.perf_counter()
        ranked_archive = rank_stage35_rows(list(archive_map.values()), limit=archive_keep)
        telemetry["archive_rank_seconds"] = float(
            telemetry.get("archive_rank_seconds", 0.0) or 0.0
        ) + float(time.perf_counter() - t_archive_rank)
        archive_map = {
            tuple(map(int, row.get("key_idx", []) or [])): dict(row)
            for row in ranked_archive
        }
        t_beam_rank = time.perf_counter()
        beam_rows = rank_stage35_rows(list(archive_map.values()), limit=beam_width)
        telemetry["beam_rank_seconds"] = float(
            telemetry.get("beam_rank_seconds", 0.0) or 0.0
        ) + float(time.perf_counter() - t_beam_rank)
        if progress_callback is not None:
            progress_callback(
                dict(
                    event="round_archive_snapshot",
                    round_idx=int(round_idx),
                    rounds_total=int(rounds),
                    beam_rows_count=int(len(beam_rows)),
                    archive_rows_count=int(len(archive_map)),
                    total_evals=int(total_evals),
                    elapsed_seconds=float(time.perf_counter() - t0),
                    outcome_status=str(outcome_status),
                    outcome_reason=str(outcome_reason),
                    archive_preview_rows=_preview_stage35_rows(
                        beam_rows,
                        limit=int(partial_dump_preview_rows),
                    ),
                )
            )
        if bool(round_capped):
            break

    t_final_archive_rank = time.perf_counter()
    archive_rows = rank_stage35_rows(list(archive_map.values()), limit=archive_keep)
    telemetry["archive_rank_seconds"] = float(
        telemetry.get("archive_rank_seconds", 0.0) or 0.0
    ) + float(time.perf_counter() - t_final_archive_rank)
    runtime_seconds = float(time.perf_counter() - t0)
    scorer_batch_calls = int(telemetry.get("scorer_batch_calls", 0) or 0)
    mini_search_count = int(telemetry.get("mini_search_count", 0) or 0)
    telemetry.update(
        average_batch_size=(
            float(telemetry.get("scorer_candidates", 0) or 0) / float(scorer_batch_calls)
            if scorer_batch_calls > 0
            else 0.0
        ),
        average_proposals_generated_per_mini=(
            float(telemetry.get("mini_search_proposals_generated", 0) or 0)
            / float(mini_search_count)
            if mini_search_count > 0
            else 0.0
        ),
        average_rows_scored_per_mini=(
            float(telemetry.get("mini_search_rows_scored", 0) or 0)
            / float(mini_search_count)
            if mini_search_count > 0
            else 0.0
        ),
        average_rows_kept_per_mini=(
            float(telemetry.get("mini_search_rows_kept", 0) or 0)
            / float(mini_search_count)
            if mini_search_count > 0
            else 0.0
        ),
    )
    if progress_callback is not None:
        progress_callback(
            dict(
                event="finish",
                rounds_completed=int(rounds_completed),
                archive_rows_count=int(len(archive_rows)),
                total_evals=int(total_evals),
                elapsed_seconds=float(runtime_seconds),
                outcome_status=str(outcome_status),
                outcome_reason=str(outcome_reason),
                completed=int(1 if str(outcome_status) == "completed" else 0),
                capped=int(1 if str(outcome_status).startswith("capped_") else 0),
                telemetry_summary=dict(
                    mini_search_count=int(telemetry.get("mini_search_count", 0) or 0),
                    row_scoring_seconds=float(
                        telemetry.get("row_scoring_seconds", 0.0) or 0.0
                    ),
                    archive_update_seconds=float(
                        telemetry.get("archive_update_seconds", 0.0) or 0.0
                    ),
                ),
            )
        )
    return dict(
        archive_rows=archive_rows,
        seed_rows_scored=ranked_seed_rows,
        evals=int(total_evals),
        rounds_completed=int(rounds_completed),
        runtime_seconds=float(runtime_seconds),
        outcome_status=str(outcome_status),
        outcome_reason=str(outcome_reason),
        completed=int(1 if str(outcome_status) == "completed" else 0),
        capped=int(1 if str(outcome_status).startswith("capped_") else 0),
        prefix_len=int(prefix_len),
        fixed_tail=list(map(int, fixed_tail)),
        diversity=stage35_archive_diversity(
            archive_rows,
            prefix_len=int(prefix_len),
        ),
        cfg=dict(solver_cfg),
        mini_search_keep_all_rows_cfg=int(mini_keep_all_rows),
        mini_search_collected_rows=int(mini_search_collected_rows_total),
        mini_search_rows_kept=int(mini_search_rows_kept_total),
        telemetry=dict(telemetry),
    )


def run_stage35_live_followup(
    *,
    period: int,
    columns: int,
    alphabet_size: int,
    ciphertext_idx: np.ndarray,
    baseline_key: Sequence[int],
    baseline_plaintext_idx: Sequence[int],
    baseline_score: float,
    baseline_selector: str = "legacy",
    baseline_summary_row: Mapping[str, Any] | None = None,
    phasec_score_winner_summary_row: Mapping[str, Any] | None = None,
    stage3_topk_rows: Sequence[Mapping[str, Any]],
    phasec_start_summaries: Sequence[Mapping[str, Any]],
    phasec_final_winner_lane: str,
    phasec_final_winner_source: str,
    cipher: Any,
    scorer_full: Any,
    scorer_search: Any,
    cfg: Mapping[str, Any] | None,
    chunk_size: int,
    require_batch: bool,
    target_plaintext_idx: Sequence[int] | None = None,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
    partial_state_path: Path | None = None,
    progress_jsonl_path: Path | None = None,
    append_jsonl_row_fn: Callable[[Path, Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    solver_cfg = _int_cfg(cfg)
    raw_cfg = dict(cfg or {})
    accept_score_min_gain = float(raw_cfg.get("accept_score_min_gain", 0.0) or 0.0)
    accept_search_score_max_drop = float(
        raw_cfg.get("accept_search_score_max_drop", 0.0) or 0.0
    )
    accept_guard_passing_selector_mode = str(
        raw_cfg.get("accept_guard_passing_selector_mode", "off") or "off"
    ).strip().lower()
    accept_guard_passing_score_band_eps = float(
        raw_cfg.get("accept_guard_passing_score_band_eps", 0.001) or 0.001
    )
    partial_dump_preview_rows = int(
        max(1, int(raw_cfg.get("partial_dump_preview_rows", 3) or 3))
    )
    progress_events_written = 0
    partial_dump_write_count = 0

    def _append_progress_row(payload: Mapping[str, Any]) -> None:
        nonlocal progress_events_written
        if progress_jsonl_path is None or append_jsonl_row_fn is None:
            return
        row_out = dict(payload)
        row_out.setdefault("ts", _progress_ts())
        append_jsonl_row_fn(Path(progress_jsonl_path), _jsonify_progress_value(row_out))
        progress_events_written += 1

    def _write_partial_state(payload: Mapping[str, Any]) -> None:
        nonlocal partial_dump_write_count
        if partial_state_path is None:
            return
        path = Path(partial_state_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_jsonify_progress_value(dict(payload)), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        partial_dump_write_count += 1

    def _emit_progress(payload: Mapping[str, Any]) -> None:
        event_payload = dict(payload)
        if progress_callback is not None:
            progress_callback(event_payload)
        _append_progress_row(event_payload)
        if str(event_payload.get("event", "") or "") in {
            "seed_rows_scored",
            "round_archive_snapshot",
            "finish",
        }:
            _write_partial_state(event_payload)

    live_phasec_start_summaries: list[dict[str, Any]] = []
    for row in list(phasec_start_summaries or []):
        row_d = dict(row)
        live_phasec_start_summaries.append(
            dict(
                start_idx=int(row_d.get("start_idx", 0) or 0),
                lane=str(row_d.get("lane", "") or ""),
                source=str(row_d.get("source", "") or ""),
                source_rank=int(row_d.get("source_rank", 0) or 0),
                candidate_hash=str(row_d.get("candidate_hash", "") or ""),
                final_score=float(row_d.get("final_score", float("nan"))),
                rescue_applied=int(row_d.get("rescue_applied", 0) or 0),
            )
        )

    baseline_summary = dict(baseline_summary_row or {})
    phasec_score_winner_summary = dict(phasec_score_winner_summary_row or {})
    baseline_key_list = list(map(int, baseline_key))
    baseline_pt_list = list(map(int, baseline_plaintext_idx))
    baseline_hash = str(
        baseline_summary.get("candidate_hash", "") or stable_key_hash(baseline_key_list)
    )
    baseline_source = str(baseline_summary.get("source", "") or "")
    baseline_lane = str(baseline_summary.get("lane", "") or "")
    baseline_source_rank = int(baseline_summary.get("source_rank", 0) or 0)
    baseline_final_score = _safe_float_or_nan(
        baseline_summary.get("final_score", baseline_score)
    )
    if not np.isfinite(baseline_final_score):
        baseline_final_score = float(baseline_score)
    baseline_final_match = _safe_float_or_nan(
        baseline_summary.get("final_match", float("nan"))
    )

    phasec_score_winner_key = list(
        map(
            int,
            phasec_score_winner_summary.get("final_key_idx", []) or baseline_key_list,
        )
    )
    phasec_score_winner_hash = str(
        phasec_score_winner_summary.get("candidate_hash", "")
        or stable_key_hash(phasec_score_winner_key)
    )
    phasec_score_winner_source = str(
        phasec_score_winner_summary.get("source", "") or ""
    )
    phasec_score_winner_lane = str(
        phasec_score_winner_summary.get("lane", "") or ""
    )
    phasec_score_winner_final_score = _safe_float_or_nan(
        phasec_score_winner_summary.get("final_score", baseline_score)
    )
    if not np.isfinite(phasec_score_winner_final_score):
        phasec_score_winner_final_score = float(baseline_score)
    phasec_score_winner_final_match = _safe_float_or_nan(
        phasec_score_winner_summary.get("final_match", float("nan"))
    )

    baseline_differs_from_phasec_score_winner = int(
        1
        if (
            baseline_hash
            and phasec_score_winner_hash
            and str(baseline_hash) != str(phasec_score_winner_hash)
        )
        else 0
    )

    artifact_like = dict(
        period=int(period),
        columns=int(columns),
        alphabet_size=int(alphabet_size),
        final_best_key_idx=list(baseline_key_list),
        stage3_topk=[dict(row) for row in list(stage3_topk_rows or [])],
        stage3_diagnostics=dict(
            phaseC_final_winner_lane=str(phasec_final_winner_lane),
            phaseC_final_winner_source=str(phasec_final_winner_source),
            phaseC_start_summaries=live_phasec_start_summaries,
        ),
    )
    seed_archive = build_stage35_seed_archive(
        artifact_like,
        checkpoint_order_mode="live_safe",
    )
    seed_rows = [dict(row) for row in list(seed_archive.get("seed_rows", []) or [])]
    baseline_search_score = float("nan")
    baseline_search_score_seconds = 0.0
    try:
        t_baseline_search = time.perf_counter()
        baseline_search_scores, _baseline_search_stats = score_plaintexts_chunked(
            scorer=scorer_search,
            plaintexts=[np.asarray(baseline_pt_list, dtype=np.uint8).reshape(-1)],
            wli=None,
            chunk_size=int(chunk_size),
            require_batch=bool(require_batch),
        )
        _ = _baseline_search_stats
        baseline_search_score_seconds = float(time.perf_counter() - t_baseline_search)
        if int(baseline_search_scores.size) > 0:
            baseline_search_score = float(baseline_search_scores[0])
    except Exception:
        baseline_search_score = float("nan")
        baseline_search_score_seconds = 0.0
    if not seed_rows:
        final_payload = dict(
            event="followup_finish",
            ts=_progress_ts(),
            baseline_selector=str(baseline_selector),
            baseline_candidate_hash=str(baseline_hash),
            baseline_candidate_source=str(baseline_source),
            baseline_candidate_lane=str(baseline_lane),
            accept_passed=0,
            accept_reason="no_seed_rows",
            outcome_status="not_run_no_seed_rows",
            outcome_reason="no_seed_rows",
            completed=0,
            capped=0,
            archive_count=0,
            rounds_completed=0,
            evals=0,
            runtime_seconds=0.0,
            archive_preview_rows=[],
        )
        _append_progress_row(final_payload)
        _write_partial_state(final_payload)
        return dict(
            enabled_cfg=1,
            ran=0,
            selected=0,
            cfg=dict(solver_cfg),
            seed_count=0,
            tail_mismatch_count=0,
            seed_source_counts={},
            archive_count=0,
            rounds_completed=0,
            evals=0,
            runtime_seconds=0.0,
            outcome_status="not_run_no_seed_rows",
            outcome_reason="no_seed_rows",
            completed=0,
            capped=0,
            archive_unique_keys=0,
            archive_unique_seed_sources=0,
            archive_unique_target_slices=0,
            archive_mean_substitution_hamming=0.0,
            archive_max_substitution_hamming=0,
            baseline_selector=str(baseline_selector),
            baseline_candidate_hash=str(baseline_hash),
            baseline_candidate_source=str(baseline_source),
            baseline_candidate_lane=str(baseline_lane),
            baseline_candidate_source_rank=int(baseline_source_rank),
            baseline_candidate_final_score=float(baseline_final_score),
            baseline_candidate_final_match=float(baseline_final_match),
            phasec_score_winner_candidate_hash=str(phasec_score_winner_hash),
            phasec_score_winner_candidate_source=str(phasec_score_winner_source),
            phasec_score_winner_candidate_lane=str(phasec_score_winner_lane),
            phasec_score_winner_candidate_final_score=float(
                phasec_score_winner_final_score
            ),
            phasec_score_winner_candidate_final_match=float(
                phasec_score_winner_final_match
            ),
            baseline_differs_from_phasec_score_winner=int(
                baseline_differs_from_phasec_score_winner
            ),
            baseline_score=float(baseline_score),
            baseline_search_score=float(baseline_search_score),
            accept_score_min_gain_cfg=float(accept_score_min_gain),
            accept_search_score_max_drop_cfg=float(accept_search_score_max_drop),
            accept_passed=0,
            accept_reason="no_seed_rows",
            best_match=float("nan"),
            truth_gain_vs_selected_row=float("nan"),
            truth_gain_vs_phasec_score_winner=float("nan"),
            best_key=list(baseline_key_list),
            best_plaintext_idx=list(baseline_pt_list),
            best_score=float(baseline_score),
            best_search_score=float("nan"),
            best_candidate_hash=str(baseline_hash),
            best_seed_source="",
            best_stage3_source="",
            best_lane="",
            best_source_rank=0,
            best_target_slice=None,
            best_depth=0,
            best_move_type="baseline",
            archive_rows=[],
            seed_rows_scored=[],
            mini_search_keep_all_rows_cfg=int(
                solver_cfg.get("mini_search_keep_all_rows", 0)
            ),
            mini_search_collected_rows=0,
            mini_search_rows_kept=0,
            partial_state_path_name=(
                str(Path(partial_state_path).name) if partial_state_path is not None else ""
            ),
            progress_jsonl_path_name=(
                str(Path(progress_jsonl_path).name)
                if progress_jsonl_path is not None
                else ""
            ),
            progress_events_written=int(progress_events_written),
            partial_dump_write_count=int(partial_dump_write_count),
            telemetry=dict(
                _empty_solver_telemetry(),
                baseline_search_score_seconds=float(baseline_search_score_seconds),
                accept_check_seconds=0.0,
                average_batch_size=0.0,
                average_proposals_generated_per_mini=0.0,
                average_rows_scored_per_mini=0.0,
                average_rows_kept_per_mini=0.0,
            ),
        )

    solver_out = solve_stage35_substitution_only(
        ciphertext_idx=np.asarray(ciphertext_idx, dtype=np.uint8).reshape(-1),
        seed_rows=seed_rows,
        period=int(period),
        alphabet_size=int(alphabet_size),
        cipher=cipher,
        scorer_full=scorer_full,
        scorer_search=scorer_search,
        cfg=dict(solver_cfg),
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
        fixed_tail=list(seed_archive.get("frozen_tail", [])),
        progress_callback=_emit_progress,
    )
    archive_rows_raw = [
        dict(row) for row in list(solver_out.get("archive_rows", []) or [])
    ]
    seed_rows_scored_raw = [
        dict(row) for row in list(solver_out.get("seed_rows_scored", []) or [])
    ]
    archive_rows = [
        dict(
            row,
            archive_rank=int(rank_idx),
            live_visible_only=1,
        )
        for rank_idx, row in enumerate(archive_rows_raw, start=1)
    ]
    seed_rows_scored = [
        dict(row, seed_rank=int(rank_idx))
        for rank_idx, row in enumerate(seed_rows_scored_raw, start=1)
    ]
    diversity = dict(solver_out.get("diversity", {}) or {})
    top_row = dict(archive_rows[0]) if archive_rows else {}
    top_key = list(map(int, top_row.get("key_idx", baseline_key_list) or baseline_key_list))
    top_pt = list(
        map(
            int,
            top_row.get("plaintext_idx", baseline_pt_list) or baseline_pt_list,
        )
    )
    top_hash = str(top_row.get("candidate_hash", "") or stable_key_hash(top_key))
    top_score = float(top_row.get("score", baseline_score))
    top_search_score = float(top_row.get("search_score", float("nan")))
    top_match = _truth_match_ratio(
        plaintext_idx=top_pt,
        target_plaintext_idx=target_plaintext_idx,
    )
    selected_row = dict(top_row)
    selected_archive_rank = int(top_row.get("archive_rank", 0) or 0)
    selected_via_guard_passing_selector = 0

    def _row_passes_acceptance_guards(row_obj: Mapping[str, Any]) -> bool:
        row_key = list(
            map(int, row_obj.get("key_idx", baseline_key_list) or baseline_key_list)
        )
        row_hash = str(
            row_obj.get("candidate_hash", "") or stable_key_hash(row_key)
        )
        row_score = float(row_obj.get("score", float("nan")))
        row_search_score = float(row_obj.get("search_score", float("nan")))
        if str(row_hash) == str(baseline_hash):
            return False
        if not _finite_gt_with_margin(
            lhs=float(row_score),
            rhs=float(baseline_score),
            margin=float(accept_score_min_gain),
        ):
            return False
        if not _finite_gte_with_margin(
            lhs=float(row_search_score),
            rhs=float(baseline_search_score),
            margin=float(accept_search_score_max_drop),
        ):
            return False
        return True

    t_accept = time.perf_counter()
    accept_passed = 0
    accept_reason = "no_archive_rows"
    if not archive_rows:
        accept_reason = "no_archive_rows"
    elif str(top_hash) == str(baseline_hash):
        accept_reason = "top_candidate_matches_baseline"
    elif not _finite_gt_with_margin(
        lhs=float(top_score),
        rhs=float(baseline_score),
        margin=float(accept_score_min_gain),
    ):
        accept_reason = "score_gain_guard_failed"
    elif not _finite_gte_with_margin(
        lhs=float(top_search_score),
        rhs=float(baseline_search_score),
        margin=float(accept_search_score_max_drop),
    ):
        accept_reason = "search_score_drop_guard_failed"
    else:
        accept_passed = 1
        accept_reason = "accepted"
    if (
        int(accept_passed) == 0
        and str(accept_guard_passing_selector_mode) != "off"
        and archive_rows
    ):
        passing_rows = [
            dict(row)
            for row in archive_rows
            if _row_passes_acceptance_guards(row)
        ]
        chosen_row = select_guard_passing_row(
            passing_rows=passing_rows,
            selector_mode=str(accept_guard_passing_selector_mode),
            current_score=float(baseline_score),
            current_search_score=float(baseline_search_score),
            score_band_eps=float(accept_guard_passing_score_band_eps),
        )
        if chosen_row is not None:
            selected_row = dict(chosen_row)
            selected_archive_rank = int(selected_row.get("archive_rank", 0) or 0)
            selected_via_guard_passing_selector = int(
                1 if int(selected_archive_rank) != int(top_row.get("archive_rank", 0) or 0) else 0
            )
            accept_passed = 1
            accept_reason = (
                "accepted_via_guard_passing_selector"
                if int(selected_via_guard_passing_selector) == 1
                else "accepted"
            )
    accept_check_seconds = float(time.perf_counter() - t_accept)
    selected = int(int(accept_passed) == 1)
    accepted_row = dict(selected_row) if int(accept_passed) == 1 else dict(top_row)
    accepted_key = list(
        map(int, accepted_row.get("key_idx", baseline_key_list) or baseline_key_list)
    )
    accepted_pt = list(
        map(
            int,
            accepted_row.get("plaintext_idx", baseline_pt_list) or baseline_pt_list,
        )
    )
    accepted_hash = str(
        accepted_row.get("candidate_hash", "") or stable_key_hash(accepted_key)
    )
    accepted_score = float(accepted_row.get("score", baseline_score))
    accepted_search_score = float(accepted_row.get("search_score", float("nan")))
    accepted_match = _truth_match_ratio(
        plaintext_idx=accepted_pt,
        target_plaintext_idx=target_plaintext_idx,
    )
    final_payload = dict(
        event="followup_finish",
        ts=_progress_ts(),
        baseline_selector=str(baseline_selector),
        baseline_candidate_hash=str(baseline_hash),
        baseline_candidate_source=str(baseline_source),
        baseline_candidate_lane=str(baseline_lane),
        accept_guard_passing_selector_mode=str(accept_guard_passing_selector_mode),
        accept_guard_passing_score_band_eps=float(accept_guard_passing_score_band_eps),
        accept_passed=int(accept_passed),
        accept_reason=str(accept_reason),
        selected_archive_rank=int(selected_archive_rank),
        selected_via_guard_passing_selector=int(selected_via_guard_passing_selector),
        selected_candidate_hash=str(accepted_hash),
        outcome_status=str(solver_out.get("outcome_status", "completed") or "completed"),
        outcome_reason=str(solver_out.get("outcome_reason", "") or ""),
        completed=int(solver_out.get("completed", 0) or 0),
        capped=int(solver_out.get("capped", 0) or 0),
        archive_count=int(len(archive_rows)),
        rounds_completed=int(solver_out.get("rounds_completed", 0) or 0),
        evals=int(solver_out.get("evals", 0) or 0),
        runtime_seconds=float(solver_out.get("runtime_seconds", 0.0) or 0.0),
        archive_preview_rows=_preview_stage35_rows(
            archive_rows,
            limit=int(partial_dump_preview_rows),
        ),
    )
    _append_progress_row(final_payload)
    _write_partial_state(final_payload)
    return dict(
        enabled_cfg=1,
        ran=int(1 if archive_rows else 0),
        selected=int(selected),
        cfg=dict(solver_cfg),
        seed_count=int(len(seed_rows)),
        tail_mismatch_count=int(seed_archive.get("tail_mismatch_count", 0) or 0),
        seed_source_counts=dict(seed_archive.get("seed_source_counts", {}) or {}),
        archive_count=int(len(archive_rows)),
        rounds_completed=int(solver_out.get("rounds_completed", 0) or 0),
        evals=int(solver_out.get("evals", 0) or 0),
        runtime_seconds=float(solver_out.get("runtime_seconds", 0.0) or 0.0),
        outcome_status=str(solver_out.get("outcome_status", "completed") or "completed"),
        outcome_reason=str(solver_out.get("outcome_reason", "") or ""),
        completed=int(solver_out.get("completed", 0) or 0),
        capped=int(solver_out.get("capped", 0) or 0),
        archive_unique_keys=int(diversity.get("unique_keys", 0) or 0),
        archive_unique_seed_sources=int(
            diversity.get("unique_seed_sources", 0) or 0
        ),
        archive_unique_target_slices=int(
            diversity.get("unique_target_slices", 0) or 0
        ),
        archive_mean_substitution_hamming=float(
            diversity.get("mean_substitution_hamming", 0.0) or 0.0
        ),
        archive_max_substitution_hamming=int(
            diversity.get("max_substitution_hamming", 0) or 0
        ),
        baseline_selector=str(baseline_selector),
        baseline_candidate_hash=str(baseline_hash),
        baseline_candidate_source=str(baseline_source),
        baseline_candidate_lane=str(baseline_lane),
        baseline_candidate_source_rank=int(baseline_source_rank),
        baseline_candidate_final_score=float(baseline_final_score),
        baseline_candidate_final_match=float(baseline_final_match),
        phasec_score_winner_candidate_hash=str(phasec_score_winner_hash),
        phasec_score_winner_candidate_source=str(phasec_score_winner_source),
        phasec_score_winner_candidate_lane=str(phasec_score_winner_lane),
        phasec_score_winner_candidate_final_score=float(
            phasec_score_winner_final_score
        ),
        phasec_score_winner_candidate_final_match=float(
            phasec_score_winner_final_match
        ),
        baseline_differs_from_phasec_score_winner=int(
            baseline_differs_from_phasec_score_winner
        ),
        baseline_score=float(baseline_score),
        baseline_search_score=float(baseline_search_score),
        accept_score_min_gain_cfg=float(accept_score_min_gain),
        accept_search_score_max_drop_cfg=float(accept_search_score_max_drop),
        accept_guard_passing_selector_mode_cfg=str(accept_guard_passing_selector_mode),
        accept_guard_passing_score_band_eps_cfg=float(
            accept_guard_passing_score_band_eps
        ),
        accept_passed=int(accept_passed),
        accept_reason=str(accept_reason),
        selected_archive_rank=int(selected_archive_rank),
        selected_via_guard_passing_selector=int(selected_via_guard_passing_selector),
        best_match=float(accepted_match),
        truth_gain_vs_selected_row=(
            float(accepted_match - baseline_final_match)
            if np.isfinite(accepted_match) and np.isfinite(baseline_final_match)
            else float("nan")
        ),
        truth_gain_vs_phasec_score_winner=(
            float(accepted_match - phasec_score_winner_final_match)
            if np.isfinite(accepted_match) and np.isfinite(phasec_score_winner_final_match)
            else float("nan")
        ),
        best_key=list(accepted_key),
        best_plaintext_idx=list(accepted_pt),
        best_score=float(accepted_score),
        best_search_score=float(accepted_search_score),
        best_candidate_hash=str(accepted_hash),
        best_seed_source=str(accepted_row.get("seed_source", "") or ""),
        best_stage3_source=str(accepted_row.get("stage3_source", "") or ""),
        best_lane=str(accepted_row.get("lane", "") or ""),
        best_source_rank=int(accepted_row.get("source_rank", 0) or 0),
        best_target_slice=accepted_row.get("target_slice", None),
        best_depth=int(accepted_row.get("depth", 0) or 0),
        best_move_type=str(accepted_row.get("move_type", "") or ""),
        archive_rows=archive_rows,
        seed_rows_scored=seed_rows_scored,
        mini_search_keep_all_rows_cfg=int(
            solver_out.get("mini_search_keep_all_rows_cfg", 0) or 0
        ),
        mini_search_collected_rows=int(
            solver_out.get("mini_search_collected_rows", 0) or 0
        ),
        mini_search_rows_kept=int(
            solver_out.get("mini_search_rows_kept", 0) or 0
        ),
        partial_state_path_name=(
            str(Path(partial_state_path).name) if partial_state_path is not None else ""
        ),
        progress_jsonl_path_name=(
            str(Path(progress_jsonl_path).name)
            if progress_jsonl_path is not None
            else ""
        ),
        progress_events_written=int(progress_events_written),
        partial_dump_write_count=int(partial_dump_write_count),
        telemetry=dict(
            dict(solver_out.get("telemetry", {}) or {}),
            baseline_search_score_seconds=float(baseline_search_score_seconds),
            accept_check_seconds=float(accept_check_seconds),
        ),
    )
