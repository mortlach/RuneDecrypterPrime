from __future__ import annotations

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
}


def _int_cfg(cfg: Mapping[str, Any] | None) -> dict[str, Any]:
    merged = dict(DEFAULT_STAGE35_SOLVER_CFG)
    if cfg is not None:
        merged.update({str(k): v for k, v in dict(cfg).items()})
    out: dict[str, Any] = {}
    for key, value in merged.items():
        if str(key) in {"accept_score_min_gain", "accept_search_score_max_drop"}:
            out[str(key)] = float(value)
        else:
            out[str(key)] = int(value)
    return out


def _finite_gte_with_margin(*, lhs: float, rhs: float, margin: float) -> bool:
    if np.isfinite(float(lhs)) and np.isfinite(float(rhs)):
        return bool(float(lhs) >= float(rhs) - float(margin))
    return bool(np.isfinite(float(lhs)) and not np.isfinite(float(rhs)))


def _finite_gt_with_margin(*, lhs: float, rhs: float, margin: float) -> bool:
    if np.isfinite(float(lhs)) and np.isfinite(float(rhs)):
        return bool(float(lhs) > float(rhs) + float(margin))
    return bool(np.isfinite(float(lhs)) and not np.isfinite(float(rhs)))


def _score_rows_for_keys(
    *,
    keys: Sequence[Sequence[int]],
    ciphertext_idx: np.ndarray,
    cipher: Any,
    scorer_full: Any,
    scorer_search: Any,
    chunk_size: int,
    require_batch: bool,
) -> list[dict[str, Any]]:
    if not keys:
        return []
    pts, full_scores, _stats = decrypt_and_score_keys_chunked(
        cipher=cipher,
        ciphertext=ciphertext_idx,
        keys=keys,
        scorer=scorer_full,
        wli=None,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
    )
    _ = _stats
    search_scores, _search_stats = score_plaintexts_chunked(
        scorer=scorer_search,
        plaintexts=pts,
        wli=None,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
    )
    _ = _search_stats
    out: list[dict[str, Any]] = []
    for idx, key_vals in enumerate(keys):
        pt = np.asarray(pts[idx], dtype=np.uint8).reshape(-1)
        out.append(
            dict(
                key=list(map(int, key_vals)),
                key_idx=list(map(int, key_vals)),
                pt=pt.astype(int).tolist(),
                plaintext_idx=pt.astype(int).tolist(),
                score=float(full_scores[idx]),
                search_score=float(search_scores[idx]),
                candidate_hash=stable_key_hash(key_vals),
            )
        )
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
        return _score_rows_for_keys(
            keys=normalized_keys,
            ciphertext_idx=ciphertext_idx,
            cipher=cipher,
            scorer_full=scorer_full,
            scorer_search=scorer_search,
            chunk_size=int(chunk_size),
            require_batch=bool(require_batch),
        )

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
) -> dict[str, Any]:
    solver_cfg = _int_cfg(cfg)
    prefix_len = int(
        substitution_prefix_len(period=int(period), alphabet_size=int(alphabet_size))
    )
    if not seed_rows:
        return dict(
            archive_rows=[],
            seed_rows_scored=[],
            evals=0,
            rounds_completed=0,
            runtime_seconds=0.0,
            prefix_len=int(prefix_len),
            fixed_tail=list(map(int, fixed_tail)),
            diversity=stage35_archive_diversity([], prefix_len=int(prefix_len)),
        )

    t0 = float(time.perf_counter())
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
    )
    score_key_rows_fn = _scoring_callback(
        ciphertext_idx=np.asarray(ciphertext_idx, dtype=np.uint8).reshape(-1),
        cipher=cipher,
        scorer_full=scorer_full,
        scorer_search=scorer_search,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
        fixed_tail=fixed_tail,
        prefix_len=int(prefix_len),
    )

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
    initial_seed_keep = int(max(1, int(solver_cfg.get("seed_keep", 6))))
    beam_width = int(max(1, int(solver_cfg.get("beam_width", 6))))
    archive_keep = int(max(1, int(solver_cfg.get("archive_keep", 24))))
    rounds = int(max(0, int(solver_cfg.get("rounds", 4))))
    mini_steps = int(max(1, int(solver_cfg.get("mini_search_steps", 2))))
    mini_beam_width = int(max(1, int(solver_cfg.get("mini_search_beam_width", 4))))
    mini_top_symbols = int(max(2, int(solver_cfg.get("mini_search_top_symbols", 10))))
    mini_final_keep = int(max(1, int(solver_cfg.get("mini_search_final_keep", 2))))
    mini_keep_all_rows = int(max(0, int(solver_cfg.get("mini_search_keep_all_rows", 0))))

    beam_rows = rank_stage35_rows(ranked_seed_rows[:initial_seed_keep], limit=beam_width)
    archive_map: dict[tuple[int, ...], dict[str, Any]] = {
        tuple(map(int, row.get("key_idx", []) or [])): dict(row) for row in beam_rows
    }
    total_evals = 0
    mini_search_collected_rows_total = 0
    mini_search_rows_kept_total = 0
    rounds_completed = 0
    for round_idx in range(1, int(rounds) + 1):
        proposal_rows: list[dict[str, Any]] = []
        for parent_row in beam_rows:
            current_key = list(map(int, parent_row.get("key_idx", []) or []))
            current_pt = np.asarray(
                parent_row.get("plaintext_idx", []) or [],
                dtype=np.uint8,
            ).reshape(-1)
            current_score = float(parent_row.get("score", float("nan")))
            current_search_score = float(parent_row.get("search_score", float("nan")))
            for slice_idx in range(int(max(1, int(period)))):
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
                total_evals += int(mini.get("evals", 0) or 0)
                mini_search_collected_rows_total += int(
                    mini.get("collected_row_count", 0) or 0
                )
                mini_search_rows_kept_total += int(len(list(mini.get("rows", []) or [])))
                for row in list(mini.get("rows", []) or []):
                    key_vals = apply_frozen_columns_tail(
                        key_vals=row.get("key", []) or row.get("key_idx", []) or [],
                        prefix_len=int(prefix_len),
                        frozen_tail=fixed_tail,
                    )
                    proposal_rows.append(
                        dict(
                            key_idx=list(map(int, key_vals)),
                            plaintext_idx=list(map(int, row.get("pt", row.get("plaintext_idx", [])) or [])),
                            score=float(row.get("score", float("nan"))),
                            search_score=float(row.get("search_score", float("nan"))),
                            candidate_hash=stable_key_hash(key_vals),
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
        if not proposal_rows:
            break
        rounds_completed = int(round_idx)
        for row in proposal_rows:
            key_t = tuple(map(int, row.get("key_idx", []) or []))
            prev = archive_map.get(key_t, None)
            row_d = dict(row)
            if prev is None:
                archive_map[key_t] = row_d
            else:
                merged = dedupe_stage35_rows([prev, row_d])
                archive_map[key_t] = dict(merged[0])
        ranked_archive = rank_stage35_rows(list(archive_map.values()), limit=archive_keep)
        archive_map = {
            tuple(map(int, row.get("key_idx", []) or [])): dict(row)
            for row in ranked_archive
        }
        beam_rows = rank_stage35_rows(list(archive_map.values()), limit=beam_width)

    archive_rows = rank_stage35_rows(list(archive_map.values()), limit=archive_keep)
    runtime_seconds = float(time.perf_counter() - t0)
    return dict(
        archive_rows=archive_rows,
        seed_rows_scored=ranked_seed_rows,
        evals=int(total_evals),
        rounds_completed=int(rounds_completed),
        runtime_seconds=float(runtime_seconds),
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
) -> dict[str, Any]:
    solver_cfg = _int_cfg(cfg)
    raw_cfg = dict(cfg or {})
    accept_score_min_gain = float(raw_cfg.get("accept_score_min_gain", 0.0) or 0.0)
    accept_search_score_max_drop = float(
        raw_cfg.get("accept_search_score_max_drop", 0.0) or 0.0
    )

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

    artifact_like = dict(
        period=int(period),
        columns=int(columns),
        alphabet_size=int(alphabet_size),
        final_best_key_idx=list(map(int, baseline_key)),
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
    baseline_key_list = list(map(int, baseline_key))
    baseline_pt_list = list(map(int, baseline_plaintext_idx))
    baseline_hash = stable_key_hash(baseline_key_list)
    baseline_search_score = float("nan")
    try:
        baseline_search_scores, _baseline_search_stats = score_plaintexts_chunked(
            scorer=scorer_search,
            plaintexts=[np.asarray(baseline_pt_list, dtype=np.uint8).reshape(-1)],
            wli=None,
            chunk_size=int(chunk_size),
            require_batch=bool(require_batch),
        )
        _ = _baseline_search_stats
        if int(baseline_search_scores.size) > 0:
            baseline_search_score = float(baseline_search_scores[0])
    except Exception:
        baseline_search_score = float("nan")
    if not seed_rows:
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
            archive_unique_keys=0,
            archive_unique_seed_sources=0,
            archive_unique_target_slices=0,
            archive_mean_substitution_hamming=0.0,
            archive_max_substitution_hamming=0,
            baseline_candidate_hash=str(baseline_hash),
            baseline_score=float(baseline_score),
            baseline_search_score=float(baseline_search_score),
            accept_score_min_gain_cfg=float(accept_score_min_gain),
            accept_search_score_max_drop_cfg=float(accept_search_score_max_drop),
            accept_passed=0,
            accept_reason="no_seed_rows",
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
    selected = int(int(accept_passed) == 1)
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
        baseline_candidate_hash=str(baseline_hash),
        baseline_score=float(baseline_score),
        baseline_search_score=float(baseline_search_score),
        accept_score_min_gain_cfg=float(accept_score_min_gain),
        accept_search_score_max_drop_cfg=float(accept_search_score_max_drop),
        accept_passed=int(accept_passed),
        accept_reason=str(accept_reason),
        best_key=list(top_key),
        best_plaintext_idx=list(top_pt),
        best_score=float(top_score),
        best_search_score=float(top_search_score),
        best_candidate_hash=str(top_hash),
        best_seed_source=str(top_row.get("seed_source", "") or ""),
        best_stage3_source=str(top_row.get("stage3_source", "") or ""),
        best_lane=str(top_row.get("lane", "") or ""),
        best_source_rank=int(top_row.get("source_rank", 0) or 0),
        best_target_slice=top_row.get("target_slice", None),
        best_depth=int(top_row.get("depth", 0) or 0),
        best_move_type=str(top_row.get("move_type", "") or ""),
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
    )
