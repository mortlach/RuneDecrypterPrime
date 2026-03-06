from __future__ import annotations

import time
from itertools import permutations
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.api import KeySpec, SolverSpec, by_name, run

from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    decrypt_and_score_keys_chunked,
    score_plaintexts_chunked,
)


def spearman_corr_safe(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Spearman rank correlation with average-tie ranks; returns NaN when undefined."""
    if len(xs) != len(ys):
        return float("nan")
    n = int(len(xs))
    if n < 2:
        return float("nan")
    x = np.asarray(xs, dtype=np.float64).reshape(-1)
    y = np.asarray(ys, dtype=np.float64).reshape(-1)
    mask = np.isfinite(x) & np.isfinite(y)
    if int(np.sum(mask)) < 2:
        return float("nan")
    x = x[mask]
    y = y[mask]

    def _avg_tie_ranks(v: np.ndarray) -> np.ndarray:
        order = np.argsort(v, kind="mergesort")
        ranks = np.empty_like(order, dtype=np.float64)
        i = 0
        m = int(v.size)
        while i < m:
            j = i
            while (j + 1) < m and v[order[j + 1]] == v[order[i]]:
                j += 1
            r = (float(i + j) / 2.0) + 1.0
            ranks[order[i : j + 1]] = r
            i = j + 1
        return ranks

    rx = _avg_tie_ranks(x)
    ry = _avg_tie_ranks(y)
    rx -= float(np.mean(rx))
    ry -= float(np.mean(ry))
    den = float(np.sqrt(np.sum(rx * rx)) * np.sqrt(np.sum(ry * ry)))
    if den <= 0.0:
        return float("nan")
    return float(np.sum(rx * ry) / den)


def tail_hamming(a: Sequence[int], b: Sequence[int]) -> int:
    return int(sum(1 for x, y in zip(a, b) if int(x) != int(y)))


def tail_diversity_metrics(tails: List[Tuple[int, ...]], *, columns: int) -> Dict[str, float]:
    if not tails:
        return dict(unique_first=0.0, mean_hamming=0.0)
    uniq_first = float(len({int(t[0]) for t in tails if len(t) > 0}))
    if len(tails) < 2:
        return dict(unique_first=uniq_first, mean_hamming=0.0)
    total = 0
    count = 0
    for i in range(len(tails)):
        ti = tails[i]
        for j in range(i + 1, len(tails)):
            total += tail_hamming(ti, tails[j])
            count += 1
    mean_h = float(total / max(1, count))
    return dict(unique_first=uniq_first, mean_hamming=mean_h)


def tail_diversity_collapsed(
    tails: List[Tuple[int, ...]],
    *,
    columns: int,
    min_first_symbols: int,
    min_hamming_factor: float,
) -> Tuple[bool, Dict[str, float]]:
    metrics = tail_diversity_metrics(tails, columns=columns)
    min_first = float(min(max(1, int(min_first_symbols)), int(columns)))
    min_hamming = float(max(1.0, float(min_hamming_factor) * float(columns)))
    collapsed = bool(metrics["unique_first"] < min_first or metrics["mean_hamming"] < min_hamming)
    metrics["min_first_required"] = float(min_first)
    metrics["min_hamming_required"] = float(min_hamming)
    return collapsed, metrics


def run_stage2_search(
    *,
    tier_name: str,
    tier_columns: int,
    text_id: int,
    key_seed: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    wli: Sequence[Sequence[int]],
    sub_candidates: Sequence[Sequence[int]],
    direction_value: str,
    full_cipher: Any,
    sub_cipher: Any,
    scorer_stage2: Dict[str, Any],
    scorer_stage2_runtime: Any,
    scorer_stage2_pass1_primary_runtime: Any | None,
    scorer_stage2_pass1_fallback_runtime: Any | None,
    stages: List[Dict[str, Any]],
    oracle_assist_selection_effective: bool,
    mark_oracle_decision_use: Callable[[], None],
    preview_latin_fn: Callable[[Sequence[int], Sequence[Sequence[int]]], str],
    print_stage_preview_fn: Callable[..., None],
    match_ratio_fn: Callable[[Sequence[int], Sequence[int]], float],
    is_better_score_first_fn: Callable[..., bool],
    scan_mode_active_stage2: bool,
    cfg: Mapping[str, Any],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    best2_match, best2_score, best2_key, best2_preview = float("-inf"), float("-inf"), None, ""
    best2_pt: List[int] | None = None
    stage2_evals_total = 0
    stage2_archive_keep = max(1, int(cfg.get("stage12_archive_keep", 1)))
    stage2_promote_top = max(1, int(cfg.get("stage12_promote_top", 1)))
    stage2_archive: Dict[Tuple[int, ...], Dict[str, Any]] = {}
    stage2_entry_score = float("-inf")
    stage2_started_t = float(time.time())
    stage2_continue_to_gate = bool(scan_mode_active_stage2 and bool(cfg.get("scan_stage2_continue_to_gate", False)))
    stage2_continue_gate_match = float(cfg.get("scan_stage3_gate_low_match", 0.0))
    stage2_continue_cap_seconds = float(cfg.get("scan_stage2_continue_cap_seconds", 0.0))
    stage2_continue_stop_reason = ""
    exact_sub_limit = int(
        dict(cfg.get("stage2_exact_sub_candidates_by_columns", {})).get(
            int(tier_columns),
            int(cfg.get("stage2_exact_sub_candidates", 1)),
        )
    )
    pass1_top_tails = int(
        dict(cfg.get("stage2_exact_pass1_top_tails_by_columns", {})).get(
            int(tier_columns),
            int(cfg.get("stage2_exact_pass1_top_tails", 1)),
        )
    )
    hybrid_sub_limit = int(
        dict(cfg.get("stage2_hybrid_sub_candidates_by_columns", {})).get(
            int(tier_columns),
            int(cfg.get("stage2_hybrid_sub_candidates", 1)),
        )
    )
    tail_chunk = int(cfg.get("batch_eval_chunk_size", 1))
    require_batch_scoring = bool(cfg.get("require_batch_scoring", True))
    solve_match_threshold = float(cfg.get("solve_match_threshold", 0.9))

    def _stage2_continuation_should_stop() -> Tuple[bool, str]:
        if not bool(stage2_continue_to_gate):
            return False, ""
        if np.isfinite(float(best2_match)) and float(best2_match) >= float(stage2_continue_gate_match):
            return True, "gate"
        if float(stage2_continue_cap_seconds) > 0.0:
            elapsed = float(time.time() - stage2_started_t)
            if elapsed >= float(stage2_continue_cap_seconds):
                return True, "cap"
        return False, ""

    def _iter_tail_chunks(columns: int, chunk_size: int):
        block: List[Tuple[int, ...]] = []
        for tail in permutations(range(int(columns))):
            block.append(tuple(int(x) for x in tail))
            if len(block) >= int(chunk_size):
                yield block
                block = []
        if block:
            yield block

    def _consider_stage2_candidate(
        *,
        full_key_arr: np.ndarray,
        pt2_arr: np.ndarray,
        match_val: float,
        score_val: float,
        preview_label: str,
    ) -> None:
        nonlocal best2_match, best2_score, best2_key, best2_pt, best2_preview
        key_list = full_key_arr.astype(int).tolist()
        key_t = tuple(int(x) for x in key_list)
        prev = stage2_archive.get(key_t)
        if (prev is None) or (float(score_val) > float(prev.get("score", float("-inf")))):
            stage2_archive[key_t] = dict(
                key=key_list,
                score=float(score_val),
                match=float(match_val),
                plaintext=pt2_arr.astype(int).tolist(),
                preview=preview_latin_fn(pt2_arr.tolist(), wli),
            )
        if bool(oracle_assist_selection_effective):
            mark_oracle_decision_use()
            better = (match_val > best2_match) or (
                abs(match_val - best2_match) <= 1e-12 and score_val > best2_score
            )
        else:
            better = bool(
                is_better_score_first_fn(
                    cand_score=float(score_val),
                    cand_match=float(match_val),
                    best_score=float(best2_score),
                    best_match=float(best2_match),
                )
            )
        if better:
            best2_match, best2_score = float(match_val), float(score_val)
            best2_key = key_list
            best2_pt = pt2_arr.astype(int).tolist()
            best2_preview = preview_latin_fn(pt2_arr.tolist(), wli)
            print_stage_preview_fn(
                label=preview_label,
                pt=pt2_arr.tolist(),
                wli=wli,
                match_ratio=float(match_val),
            )

    if int(tier_columns) <= 1:
        full_keys_identity: List[np.ndarray] = []
        for sub_key in sub_candidates:
            sub_arr = np.asarray(sub_key, dtype=np.int16).reshape(-1)
            full_key = np.concatenate([sub_arr, np.asarray([0], dtype=np.int16)], axis=0)
            full_keys_identity.append(full_key)
        if full_keys_identity:
            pt_batch, sc_batch, _batch_stats = decrypt_and_score_keys_chunked(
                cipher=full_cipher,
                ciphertext=ct_idx,
                keys=full_keys_identity,
                scorer=scorer_stage2_runtime,
                wli=None,
                key_dtype=np.int16,
                chunk_size=int(tail_chunk),
                require_batch=bool(require_batch_scoring),
            )
            for i, full_key in enumerate(full_keys_identity):
                pt2 = np.asarray(pt_batch[i], dtype=np.uint8).reshape(-1)
                m2 = float(match_ratio_fn(pt2.tolist(), pt_idx.tolist()))
                sc2 = float(sc_batch[i])
                stage2_evals_total += 1
                _consider_stage2_candidate(
                    full_key_arr=full_key,
                    pt2_arr=pt2,
                    match_val=float(m2),
                    score_val=float(sc2),
                    preview_label=f"stage2_identity_best_{i + 1}",
                )
        print(
            f"{log_prefix} stage2-summary tier={tier_name} text={text_id} key_seed={key_seed} "
            f"mode=identity best_match_ratio={float(best2_match):.3f} "
            f"best_score_at_best_match={float(best2_score):.6f} evals={int(stage2_evals_total)}",
            flush=True,
        )
    elif int(tier_columns) <= int(cfg.get("stage2_exact_max_columns", 0)):
        exact_sub_cap = int(len(sub_candidates)) if bool(stage2_continue_to_gate) else int(exact_sub_limit)
        exact_subs = list(sub_candidates[: max(1, int(exact_sub_cap))])
        exact_early_stop = False
        for i, sub_key in enumerate(exact_subs):
            sub_arr = np.asarray(sub_key, dtype=np.int16)
            pass1_evals = 0
            pass2_evals = 0
            shortlist_tails: List[Tuple[int, ...]] = []
            pass1_scorer_used = "none"
            pass1_fallback_used = False
            pass1_primary_metrics: Dict[str, float] = {}
            pass1_used_metrics: Dict[str, float] = {}

            if bool(cfg.get("stage2_exact_two_pass", False)) and scorer_stage2_pass1_primary_runtime is not None:
                pass1_ranked: List[Tuple[float, Tuple[int, ...]]] = []
                for tail_block in _iter_tail_chunks(int(tier_columns), tail_chunk):
                    full_keys_block: List[np.ndarray] = []
                    for tail in tail_block:
                        col_key = np.asarray(tail, dtype=np.int16)
                        full_keys_block.append(np.concatenate([sub_arr, col_key], axis=0))
                    pt_block, fast_block, _batch_stats = decrypt_and_score_keys_chunked(
                        cipher=full_cipher,
                        ciphertext=ct_idx,
                        keys=full_keys_block,
                        scorer=scorer_stage2_pass1_primary_runtime,
                        wli=None,
                        key_dtype=np.int16,
                        chunk_size=int(tail_chunk),
                        require_batch=bool(require_batch_scoring),
                    )
                    pass1_evals += int(len(tail_block))
                    stage2_evals_total += int(len(tail_block))
                    for j, tail in enumerate(tail_block):
                        pt2 = np.asarray(pt_block[j], dtype=np.uint8).reshape(-1)
                        full_key = full_keys_block[j]
                        fast_sc = float(fast_block[j])
                        pass1_ranked.append((fast_sc, tail))
                        if bool(cfg.get("stage2_exact_early_solve_break", False)):
                            m2 = float(match_ratio_fn(pt2.tolist(), pt_idx.tolist()))
                            if float(m2) >= float(solve_match_threshold):
                                sc2 = float(
                                    score_plaintexts_chunked(
                                        scorer=scorer_stage2_runtime,
                                        plaintexts=np.asarray([pt2], dtype=np.uint8),
                                        wli=None,
                                        chunk_size=1,
                                        require_batch=bool(require_batch_scoring),
                                    )[0][0]
                                )
                                pass2_evals += 1
                                stage2_evals_total += 1
                                _consider_stage2_candidate(
                                    full_key_arr=full_key,
                                    pt2_arr=pt2,
                                    match_val=float(m2),
                                    score_val=float(sc2),
                                    preview_label=f"stage2_exact_best_sub{i + 1}",
                                )
                                exact_early_stop = True
                                break
                    if exact_early_stop:
                        break
                if not exact_early_stop:
                    pass1_ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
                    k_short = min(int(pass1_top_tails), len(pass1_ranked))
                    shortlist_primary = [tail for _s, tail in pass1_ranked[:k_short]]
                    pass1_scorer_used = "primary_char34"
                    collapsed, pass1_primary_metrics = tail_diversity_collapsed(
                        shortlist_primary,
                        columns=int(tier_columns),
                        min_first_symbols=int(cfg.get("stage2_pass1_diversity_min_first_symbols", 1)),
                        min_hamming_factor=float(cfg.get("stage2_pass1_diversity_min_hamming_factor", 1.0)),
                    )
                    shortlist_tails = list(shortlist_primary)
                    pass1_used_metrics = dict(pass1_primary_metrics)
                    if collapsed and scorer_stage2_pass1_fallback_runtime is not None:
                        pass1_fallback_used = True
                        pass1_ranked_fb: List[Tuple[float, Tuple[int, ...]]] = []
                        for tail_block in _iter_tail_chunks(int(tier_columns), tail_chunk):
                            full_keys_block = []
                            for tail in tail_block:
                                col_key = np.asarray(tail, dtype=np.int16)
                                full_keys_block.append(np.concatenate([sub_arr, col_key], axis=0))
                            _pt_block, fast_fb_block, _batch_stats = decrypt_and_score_keys_chunked(
                                cipher=full_cipher,
                                ciphertext=ct_idx,
                                keys=full_keys_block,
                                scorer=scorer_stage2_pass1_fallback_runtime,
                                wli=None,
                                key_dtype=np.int16,
                                chunk_size=int(tail_chunk),
                                require_batch=bool(require_batch_scoring),
                            )
                            pass1_evals += int(len(tail_block))
                            stage2_evals_total += int(len(tail_block))
                            for j, tail in enumerate(tail_block):
                                fast_sc_fb = float(fast_fb_block[j])
                                pass1_ranked_fb.append((fast_sc_fb, tail))
                        pass1_ranked_fb.sort(key=lambda x: (x[0], x[1]), reverse=True)
                        shortlist_tails = [tail for _s, tail in pass1_ranked_fb[:k_short]]
                        pass1_scorer_used = "fallback_char2"
                        _collapsed_fb, pass1_used_metrics = tail_diversity_collapsed(
                            shortlist_tails,
                            columns=int(tier_columns),
                            min_first_symbols=int(cfg.get("stage2_pass1_diversity_min_first_symbols", 1)),
                            min_hamming_factor=float(cfg.get("stage2_pass1_diversity_min_hamming_factor", 1.0)),
                        )
            else:
                shortlist_tails = [tuple(int(x) for x in tail) for tail in permutations(range(int(tier_columns)))]
                pass1_scorer_used = "full_enum"
                _collapsed_enum, pass1_used_metrics = tail_diversity_collapsed(
                    shortlist_tails,
                    columns=int(tier_columns),
                    min_first_symbols=int(cfg.get("stage2_pass1_diversity_min_first_symbols", 1)),
                    min_hamming_factor=float(cfg.get("stage2_pass1_diversity_min_hamming_factor", 1.0)),
                )

            if not exact_early_stop:
                for lo in range(0, len(shortlist_tails), int(tail_chunk)):
                    tail_block = shortlist_tails[lo : lo + int(tail_chunk)]
                    full_keys_block = []
                    for tail in tail_block:
                        col_key = np.asarray(tail, dtype=np.int16)
                        full_keys_block.append(np.concatenate([sub_arr, col_key], axis=0))
                    pt_block, sc_block, _batch_stats = decrypt_and_score_keys_chunked(
                        cipher=full_cipher,
                        ciphertext=ct_idx,
                        keys=full_keys_block,
                        scorer=scorer_stage2_runtime,
                        wli=None,
                        key_dtype=np.int16,
                        chunk_size=int(tail_chunk),
                        require_batch=bool(require_batch_scoring),
                    )
                    pass2_evals += int(len(tail_block))
                    stage2_evals_total += int(len(tail_block))
                    for j, _tail in enumerate(tail_block):
                        pt2 = np.asarray(pt_block[j], dtype=np.uint8).reshape(-1)
                        full_key = full_keys_block[j]
                        m2 = float(match_ratio_fn(pt2.tolist(), pt_idx.tolist()))
                        sc2 = float(sc_block[j])
                        _consider_stage2_candidate(
                            full_key_arr=full_key,
                            pt2_arr=pt2,
                            match_val=float(m2),
                            score_val=float(sc2),
                            preview_label=f"stage2_exact_best_sub{i + 1}",
                        )
                        if bool(cfg.get("stage2_exact_early_solve_break", False)) and float(m2) >= float(
                            solve_match_threshold
                        ):
                            exact_early_stop = True
                            break
                    if exact_early_stop:
                        break

            stages.append(
                dict(
                    tier=str(tier_name),
                    text_id=int(text_id),
                    key_seed=int(key_seed),
                    stage=f"stage2_exact_attempt_{i + 1}",
                    score=float(best2_score),
                    match_ratio=float(best2_match),
                    seconds=0.0,
                    evals=int(stage2_evals_total),
                    pass1_evals=int(pass1_evals),
                    pass2_evals=int(pass2_evals),
                    pass2_shortlist=int(len(shortlist_tails)),
                    pass1_top_cap=int(pass1_top_tails),
                    exact_sub_limit=int(exact_sub_limit),
                    early_stop=int(bool(exact_early_stop)),
                    pass1_scorer_used=str(pass1_scorer_used),
                    pass1_fallback_used=int(bool(pass1_fallback_used)),
                    pass1_primary_unique_first=float(pass1_primary_metrics.get("unique_first", np.nan)),
                    pass1_primary_mean_hamming=float(pass1_primary_metrics.get("mean_hamming", np.nan)),
                    pass1_used_unique_first=float(pass1_used_metrics.get("unique_first", np.nan)),
                    pass1_used_mean_hamming=float(pass1_used_metrics.get("mean_hamming", np.nan)),
                )
            )
            if exact_early_stop:
                stage2_continue_stop_reason = "solve_threshold"
                break
            stop_now, stop_kind = _stage2_continuation_should_stop()
            if bool(stop_now):
                elapsed_now = float(time.time() - stage2_started_t)
                stage2_continue_stop_reason = str(stop_kind)
                print(
                    f"{log_prefix} stage2-continue-stop tier={tier_name} text={text_id} key_seed={key_seed} "
                    f"reason={str(stop_kind)} best_match={float(best2_match):.3f} "
                    f"elapsed={float(elapsed_now):.1f}s gate={float(stage2_continue_gate_match):.3f} "
                    f"cap={float(stage2_continue_cap_seconds):.1f}s",
                    flush=True,
                )
                break
        print(
            f"{log_prefix} stage2-summary tier={tier_name} text={text_id} key_seed={key_seed} "
            f"mode=exact best_match_ratio={float(best2_match):.3f} "
            f"best_score_at_best_match={float(best2_score):.6f} evals={int(stage2_evals_total)}",
            flush=True,
        )
    else:
        hybrid_sub_cap = int(len(sub_candidates)) if bool(stage2_continue_to_gate) else int(hybrid_sub_limit)
        hybrid_subs = list(sub_candidates[: max(1, int(hybrid_sub_cap))])
        solver_stage2_template = dict(cfg.get("solver_stage2", {}))
        for i, sub_key in enumerate(hybrid_subs):
            t_s2 = time.time()
            inter = sub_cipher.decrypt_single(ciphertext=ct_idx, key=np.asarray(sub_key, dtype=np.int16))
            solver_stage2_cfg = dict(solver_stage2_template)
            solver_stage2_cfg["seed"] = int(solver_stage2_cfg.get("seed", 2026)) + 131 * int(i) + int(key_seed)
            sol2 = run(
                text=np.asarray(inter, dtype=np.uint8).tolist(),
                cipher=by_name.cipher("columnar", key_length=int(tier_columns)),
                key=KeySpec.permutation(len=int(tier_columns)),
                solver=SolverSpec.hybrid(**solver_stage2_cfg),
                scorer_params=scorer_stage2,
                wli_data=[],
                encoding_dir=str(direction_value),
                telemetry_on=True,
                force_no_wli=True,
            )
            dt2 = float(time.time() - t_s2)
            ev2 = int((getattr(sol2, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
            stage2_evals_total += int(ev2)
            col_key = np.asarray(getattr(sol2, "key", []) or [], dtype=np.int16).reshape(-1)
            if col_key.size != int(tier_columns):
                continue
            full_key = np.concatenate([np.asarray(sub_key, dtype=np.int16), col_key], axis=0)
            pt2 = np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=full_key), dtype=np.uint8).reshape(-1)
            m2 = float(match_ratio_fn(pt2.tolist(), pt_idx.tolist()))
            _judge_scores, _judge_stats = score_plaintexts_chunked(
                scorer=scorer_stage2_runtime,
                plaintexts=[pt2],
                wli=None,
                chunk_size=int(tail_chunk),
                require_batch=bool(require_batch_scoring),
            )
            sc2 = float(_judge_scores[0]) if _judge_scores.size > 0 else float("nan")
            stages.append(
                dict(
                    tier=str(tier_name),
                    text_id=int(text_id),
                    key_seed=int(key_seed),
                    stage=f"stage2_col_attempt_{i + 1}",
                    score=float(sc2),
                    match_ratio=float(m2),
                    seconds=round(dt2, 3),
                    evals=int(ev2),
                )
            )
            _consider_stage2_candidate(
                full_key_arr=full_key,
                pt2_arr=pt2,
                match_val=float(m2),
                score_val=float(sc2),
                preview_label=f"stage2_best_attempt_{i + 1}",
            )
            stop_now, stop_kind = _stage2_continuation_should_stop()
            if bool(stop_now):
                elapsed_now = float(time.time() - stage2_started_t)
                stage2_continue_stop_reason = str(stop_kind)
                print(
                    f"{log_prefix} stage2-continue-stop tier={tier_name} text={text_id} key_seed={key_seed} "
                    f"reason={str(stop_kind)} best_match={float(best2_match):.3f} "
                    f"elapsed={float(elapsed_now):.1f}s gate={float(stage2_continue_gate_match):.3f} "
                    f"cap={float(stage2_continue_cap_seconds):.1f}s",
                    flush=True,
                )
                break
        print(
            f"{log_prefix} stage2-summary tier={tier_name} text={text_id} key_seed={key_seed} "
            f"mode=hybrid best_match_ratio={float(best2_match):.3f} "
            f"best_score_at_best_match={float(best2_score):.6f} "
            f"evals={int(stage2_evals_total)} sub_limit={int(hybrid_sub_limit)}",
            flush=True,
        )

    if bool(stage2_continue_to_gate):
        stage2_elapsed = float(time.time() - stage2_started_t)
        if not stage2_continue_stop_reason:
            if np.isfinite(float(best2_match)) and float(best2_match) >= float(stage2_continue_gate_match):
                stage2_continue_stop_reason = "gate"
            elif float(stage2_continue_cap_seconds) > 0.0 and stage2_elapsed >= float(stage2_continue_cap_seconds):
                stage2_continue_stop_reason = "cap"
            else:
                stage2_continue_stop_reason = "sub_candidates_exhausted"
        print(
            f"{log_prefix} stage2-continue-summary tier={tier_name} text={text_id} key_seed={key_seed} "
            f"reason={str(stage2_continue_stop_reason)} elapsed={float(stage2_elapsed):.1f}s "
            f"best_match={float(best2_match):.3f} gate={float(stage2_continue_gate_match):.3f} "
            f"cap={float(stage2_continue_cap_seconds):.1f}s",
            flush=True,
        )
        stages.append(
            dict(
                tier=str(tier_name),
                text_id=int(text_id),
                key_seed=int(key_seed),
                stage="stage2_continuation",
                score=float(best2_score if np.isfinite(best2_score) else np.nan),
                match_ratio=float(best2_match if np.isfinite(best2_match) else np.nan),
                seconds=round(float(stage2_elapsed), 3),
                evals=int(stage2_evals_total),
                reason=str(stage2_continue_stop_reason),
                gate=float(stage2_continue_gate_match),
                cap_seconds=float(stage2_continue_cap_seconds),
            )
        )

    return dict(
        best2_match=float(best2_match),
        best2_score=float(best2_score),
        best2_key=(list(map(int, best2_key)) if best2_key is not None else None),
        best2_pt=(list(map(int, best2_pt)) if best2_pt is not None else None),
        best2_preview=str(best2_preview),
        stage2_evals_total=int(stage2_evals_total),
        stage2_archive=stage2_archive,
        stage2_archive_keep=int(stage2_archive_keep),
        stage2_promote_top=int(stage2_promote_top),
        stage2_entry_score=float(stage2_entry_score),
        stage2_continue_to_gate=bool(stage2_continue_to_gate),
        stage2_continue_stop_reason=str(stage2_continue_stop_reason),
    )


def finalize_stage2_archive(
    *,
    tier_name: str,
    text_id: int,
    key_seed: int,
    stage2_archive: Dict[Tuple[int, ...], Dict[str, Any]],
    stage2_archive_keep: int,
    stage2_promote_top: int,
    best2_key: List[int] | None,
    best2_pt: List[int] | None,
    best2_preview: str,
    best2_score: float,
    best2_match: float,
    scorer_stage2: Dict[str, Any],
    scorer_stage2_judge_cfg: Dict[str, Any],
    scorer_stage2_judge_runtime: Any,
    scorer_full_runtime: Any,
    oracle_assist_selection_effective: bool,
    mark_oracle_decision_use: Callable[[], None],
    stage2_promote_by_stage3_judge: bool,
    save_stage2_topk: int,
    batch_eval_chunk_size: int,
    require_batch_scoring: bool,
    objective_space_key_fn: Callable[[Dict[str, Any]], str],
    stage2_judge_pool_limit_fn: Callable[..., int],
    ensure_best_entry_in_ranked_fn: Callable[..., List[Dict[str, Any]]],
    ensure_best_entry_in_promoted_fn: Callable[..., Tuple[List[Dict[str, Any]], bool]],
    entry_key_tuple_fn: Callable[[Dict[str, Any]], Tuple[int, ...]],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    stage2_all = list(stage2_archive.values())
    stage2_score_match_spearman = spearman_corr_safe(
        [float(e.get("score", float("nan"))) for e in stage2_all],
        [float(e.get("match", float("nan"))) for e in stage2_all],
    )
    stage2_ranked_by_score = sorted(
        stage2_all,
        key=lambda e: (float(e.get("score", float("-inf"))), float(e.get("match", float("-inf")))),
        reverse=True,
    )
    stage2_ranked_by_match = sorted(
        stage2_all,
        key=lambda e: (float(e.get("match", float("-inf"))), float(e.get("score", float("-inf")))),
        reverse=True,
    )
    stage2_ranked = stage2_ranked_by_score[: int(stage2_archive_keep)]
    stage2_best_entry: Dict[str, Any] | None = None
    stage2_best_key_t: Tuple[int, ...] = tuple()
    if best2_key is not None:
        stage2_best_key_t = tuple(int(x) for x in best2_key)
        if stage2_best_key_t and stage2_best_key_t in stage2_archive:
            stage2_best_entry = dict(stage2_archive[stage2_best_key_t])
        elif stage2_best_key_t and best2_pt is not None:
            stage2_best_entry = dict(
                key=list(map(int, best2_key)),
                score=float(best2_score),
                match=float(best2_match),
                plaintext=list(map(int, best2_pt)),
                preview=str(best2_preview),
            )
    stage2_ranked = ensure_best_entry_in_ranked_fn(
        ranked_entries=stage2_ranked,
        best_entry=stage2_best_entry,
    )
    stage2_kept_by_score = list(stage2_ranked)
    stage2_kept_by_match = sorted(
        stage2_ranked,
        key=lambda e: (
            float(e.get("match", float("-inf"))),
            float(e.get("score", float("-inf"))),
        ),
        reverse=True,
    )

    stage2_promoted: List[Dict[str, Any]] = []
    stage2_promoted_seen: set[Tuple[int, ...]] = set()
    stage2_promote_mode = "score_only"

    def _push_promoted(entry: Dict[str, Any]) -> None:
        key_vals = tuple(int(x) for x in entry.get("key", []))
        if (not key_vals) or (key_vals in stage2_promoted_seen):
            return
        stage2_promoted_seen.add(key_vals)
        stage2_promoted.append(entry)

    if bool(oracle_assist_selection_effective):
        mark_oracle_decision_use()
        stage2_promote_mode = "score_match_interleave"
        max_rank = max(len(stage2_kept_by_score), len(stage2_kept_by_match))
        for r in range(max_rank):
            if len(stage2_promoted) >= int(stage2_promote_top):
                break
            if r < len(stage2_kept_by_score):
                _push_promoted(stage2_kept_by_score[r])
            if len(stage2_promoted) >= int(stage2_promote_top):
                break
            if r < len(stage2_kept_by_match):
                _push_promoted(stage2_kept_by_match[r])
    else:
        for r in range(min(len(stage2_kept_by_score), int(stage2_promote_top))):
            _push_promoted(stage2_kept_by_score[r])

    if (best2_key is None) and stage2_kept_by_score:
        top = stage2_kept_by_score[0]
        best2_key = list(map(int, top.get("key", [])))
        best2_pt = list(map(int, top.get("plaintext", [])))
        best2_preview = str(top.get("preview", best2_preview))
        best2_score = float(top.get("score", best2_score))
        best2_match = float(top.get("match", best2_match))

    stage2_entry_score = float("-inf")
    if stage2_kept_by_score:
        stage2_entry_score = float(stage2_kept_by_score[0].get("score", float("-inf")))
    elif np.isfinite(best2_score):
        stage2_entry_score = float(best2_score)
    stage2_entry_score_judge = float("-inf")
    stage2_judge_pool_size = stage2_judge_pool_limit_fn(
        ranked_count=len(stage2_ranked),
        archive_keep=int(stage2_archive_keep),
        stage2_scorer_cfg=dict(scorer_stage2),
        stage3_scorer_cfg=dict(scorer_stage2_judge_cfg),
    )
    stage2_judge_entries = stage2_ranked[: int(stage2_judge_pool_size)]
    stage2_judge_plaintexts: List[np.ndarray] = []
    stage2_judge_map: List[int] = []
    for rank_idx, ent in enumerate(stage2_judge_entries, start=1):
        pt_list = ent.get("plaintext", [])
        if isinstance(pt_list, list) and pt_list:
            stage2_judge_plaintexts.append(np.asarray(pt_list, dtype=np.uint8).reshape(-1))
            stage2_judge_map.append(int(rank_idx))
    stage2_judge_scores: Dict[int, float] = {}
    if stage2_judge_plaintexts:
        _judge_scores, _judge_stats = score_plaintexts_chunked(
            scorer=scorer_stage2_judge_runtime,
            plaintexts=stage2_judge_plaintexts,
            wli=None,
            chunk_size=int(batch_eval_chunk_size),
            require_batch=bool(require_batch_scoring),
        )
        for idx, rank_idx in enumerate(stage2_judge_map):
            if idx < int(_judge_scores.size):
                stage2_judge_scores[int(rank_idx)] = float(_judge_scores[idx])
    if 1 in stage2_judge_scores:
        stage2_entry_score_judge = float(stage2_judge_scores[1])
    if (not np.isfinite(stage2_entry_score_judge)) and np.isfinite(stage2_entry_score):
        stage2_entry_score_judge = float(stage2_entry_score)

    stage2_stage3_space_match = (
        objective_space_key_fn(dict(scorer_stage2))
        == objective_space_key_fn(dict(scorer_stage2_judge_cfg))
    )
    if bool(stage2_promote_by_stage3_judge) and stage2_judge_scores:
        judged_entries: List[Dict[str, Any]] = []
        for rank_idx, ent in enumerate(stage2_judge_entries, start=1):
            judge_sc = float(stage2_judge_scores.get(int(rank_idx), float("nan")))
            if not np.isfinite(judge_sc):
                continue
            enriched = dict(ent)
            enriched["judge_score"] = float(judge_sc)
            judged_entries.append(enriched)
        if judged_entries:
            by_judge = sorted(
                judged_entries,
                key=lambda e: (
                    float(e.get("judge_score", float("-inf"))),
                    float(e.get("match", float("-inf"))),
                ),
                reverse=True,
            )
            by_match = sorted(
                judged_entries,
                key=lambda e: (
                    float(e.get("match", float("-inf"))),
                    float(e.get("judge_score", float("-inf"))),
                ),
                reverse=True,
            )
            stage2_promoted = []
            stage2_promoted_seen = set()
            max_jrank = max(len(by_judge), len(by_match))
            for r in range(max_jrank):
                if len(stage2_promoted) >= int(stage2_promote_top):
                    break
                if r < len(by_judge):
                    _push_promoted(by_judge[r])
                if len(stage2_promoted) >= int(stage2_promote_top):
                    break
                if r < len(by_match):
                    _push_promoted(by_match[r])
            stage2_promote_mode = "judge_match_interleave"
    elif (not bool(stage2_promote_by_stage3_judge)) and (not stage2_stage3_space_match) and stage2_judge_scores:
        judged_entries: List[Dict[str, Any]] = []
        for rank_idx, ent in enumerate(stage2_judge_entries, start=1):
            judge_sc = float(stage2_judge_scores.get(int(rank_idx), float("nan")))
            if not np.isfinite(judge_sc):
                continue
            enriched = dict(ent)
            enriched["judge_score"] = float(judge_sc)
            judged_entries.append(enriched)
        if judged_entries:
            by_judge = sorted(
                judged_entries,
                key=lambda e: (
                    float(e.get("judge_score", float("-inf"))),
                    float(e.get("score", float("-inf"))),
                ),
                reverse=True,
            )
            stage2_promoted = []
            stage2_promoted_seen = set()
            for r in range(min(len(by_judge), int(stage2_promote_top))):
                _push_promoted(by_judge[r])
            stage2_promote_mode = "judge_auto_bridge"

    stage2_promoted, stage2_best_in_promoted = ensure_best_entry_in_promoted_fn(
        promoted_entries=stage2_promoted,
        best_entry=stage2_best_entry,
        promote_top=int(stage2_promote_top),
    )
    stage2_promoted_seen = {
        entry_key_tuple_fn(ent)
        for ent in stage2_promoted
        if entry_key_tuple_fn(ent)
    }
    _ = stage2_promoted_seen

    stage2_topk_payload: List[Dict[str, Any]] = []
    for rank_idx, ent in enumerate(stage2_kept_by_score[: int(save_stage2_topk)], start=1):
        key_list = list(map(int, ent.get("key", [])))
        pt_list = list(map(int, ent.get("plaintext", [])))
        judge_sc = float(stage2_judge_scores.get(int(rank_idx), float("nan")))
        stage2_topk_payload.append(
            dict(
                rank=int(rank_idx),
                score_stage2=float(ent.get("score", float("nan"))),
                score_judge=float(judge_sc),
                match_ratio=float(ent.get("match", float("nan"))),
                key_idx=key_list,
                plaintext_idx=pt_list,
            )
        )
    stage2_topk_has_best_match = False
    if stage2_best_entry is not None:
        best2_t = entry_key_tuple_fn(stage2_best_entry)
        payload_key_set = {
            tuple(int(x) for x in row.get("key_idx", []))
            for row in stage2_topk_payload
            if isinstance(row.get("key_idx"), list) and row.get("key_idx")
        }
        stage2_topk_has_best_match = bool(best2_t in payload_key_set)
        if (not stage2_topk_has_best_match) and best2_t:
            best2_pt_arr = np.asarray(stage2_best_entry.get("plaintext", []), dtype=np.uint8).reshape(-1)
            best2_judge = float("nan")
            if best2_pt_arr.size > 0:
                _judge_arr, _judge_stats = score_plaintexts_chunked(
                    scorer=scorer_full_runtime,
                    plaintexts=[best2_pt_arr],
                    wli=None,
                    chunk_size=1,
                    require_batch=bool(require_batch_scoring),
                )
                if _judge_arr.size > 0:
                    best2_judge = float(_judge_arr[0])
            stage2_topk_payload.append(
                dict(
                    rank=int(len(stage2_topk_payload) + 1),
                    score_stage2=float(stage2_best_entry.get("score", float("nan"))),
                    score_judge=float(best2_judge),
                    match_ratio=float(stage2_best_entry.get("match", float("nan"))),
                    key_idx=list(map(int, stage2_best_entry.get("key", []))),
                    plaintext_idx=list(map(int, stage2_best_entry.get("plaintext", []))),
                    tag="best_match_injected",
                )
            )
            stage2_topk_has_best_match = True
    print(
        f"{log_prefix} stage2-archive tier={tier_name} text={text_id} key_seed={key_seed} "
        f"entries={len(stage2_archive)} kept={len(stage2_ranked)} promoted={len(stage2_promoted)} "
        f"judge_pool={int(stage2_judge_pool_size)} promoted_by={stage2_promote_mode} "
        f"best2_in_promoted={1 if stage2_best_in_promoted else 0} "
        f"best2_in_stage2_topk={1 if stage2_topk_has_best_match else 0} "
        f"spearman_score_match={float(stage2_score_match_spearman) if np.isfinite(stage2_score_match_spearman) else float('nan'):.3f} "
        f"top_score_mid_rank1={float(stage2_entry_score) if np.isfinite(stage2_entry_score) else float('nan'):.6f} "
        f"top_score_judge_rank1={float(stage2_entry_score_judge) if np.isfinite(stage2_entry_score_judge) else float('nan'):.6f} "
        f"top_match_ratio={float(best2_match) if np.isfinite(best2_match) else float('nan'):.3f}",
        flush=True,
    )
    return dict(
        best2_match=float(best2_match),
        best2_score=float(best2_score),
        best2_key=(list(map(int, best2_key)) if best2_key is not None else None),
        best2_pt=(list(map(int, best2_pt)) if best2_pt is not None else None),
        best2_preview=str(best2_preview),
        stage2_ranked=stage2_ranked,
        stage2_promoted=stage2_promoted,
        stage2_entry_score=float(stage2_entry_score),
        stage2_entry_score_judge=float(stage2_entry_score_judge),
        stage2_score_match_spearman=float(stage2_score_match_spearman),
        stage2_stage3_space_match=bool(stage2_stage3_space_match),
        stage2_topk_payload=stage2_topk_payload,
        stage2_topk_has_best_match=bool(stage2_topk_has_best_match),
    )
