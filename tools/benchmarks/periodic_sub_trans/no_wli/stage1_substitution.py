from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.api import KeySpec, SolverSpec, by_name, run
from rune_decrypter_prime.utils.seed_utils import make_periodic_seed_pool

from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    decrypt_and_score_keys_chunked,
)


def run_stage1_substitution(
    *,
    tier_name: str,
    tier_period: int,
    tier_columns: int,
    text_id: int,
    key_seed: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    true_sub: np.ndarray,
    sub_len: int,
    wli: Sequence[Sequence[int]],
    direction_value: str,
    alphabet_size: int,
    scorer_stage1: Dict[str, Any],
    scorer_stage1_runtime: Any,
    sub_cipher: Any,
    stages: List[Dict[str, Any]],
    solver_stage1: Dict[str, Any],
    stage1_seed_restarts: int,
    stage1_sub_candidates: int,
    stage1_sub_candidates_by_columns: Mapping[int, int],
    stage12_archive_keep: int,
    stage12_scout_runs: int,
    stage1_scout_min_steps: int,
    stage1_scout_step_scale: float,
    stage1_scout_min_restarts: int,
    stage1_scout_restart_scale: float,
    stage1_seed_n_blocks: int,
    stage1_seed_total: int,
    stage1_seed_swaps: int,
    batch_eval_chunk_size: int,
    require_batch_scoring: bool,
    stage1_scout_no_improve_delta: float,
    stage1_scout_min_new_archive: int,
    stage1_scout_early_stop_min_scouts: int,
    stage1_scout_no_improve_patience: int,
    extract_top_keys_fn: Callable[[Any, int], List[List[int]]],
    key_hash_fn: Callable[[Sequence[int]], str],
    match_ratio_fn: Callable[[Sequence[int], Sequence[int]], float],
    print_stage_preview_fn: Callable[..., None],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    t_s1 = time.time()
    solver_stage1_base_cfg = dict(solver_stage1)
    solver_stage1_base_cfg["seed_restarts"] = int(stage1_seed_restarts)
    stage1_sub_limit = int(stage1_sub_candidates_by_columns.get(int(tier_columns), stage1_sub_candidates))
    stage1_archive_keep = max(int(stage1_sub_limit), int(stage12_archive_keep), 1)
    stage1_scout_runs = max(1, int(stage12_scout_runs))
    print(
        f"{log_prefix} stage1-stop tier={tier_name} text={text_id} key_seed={key_seed} "
        f"stop_score={solver_stage1_base_cfg.get('stop_score', 'none')} "
        f"plateau_rounds={solver_stage1_base_cfg.get('plateau_rounds')} "
        f"plateau_min_delta={solver_stage1_base_cfg.get('plateau_min_delta')} "
        f"scouts={stage1_scout_runs} archive_keep={stage1_archive_keep} "
        f"scout_plateau=(delta={float(stage1_scout_no_improve_delta):.1e},"
        f"patience={int(stage1_scout_no_improve_patience)},"
        f"min_new_archive={int(stage1_scout_min_new_archive)},"
        f"early_stop_min_scouts={int(stage1_scout_early_stop_min_scouts)}) "
        f"oracle_guard=off",
        flush=True,
    )
    stage1_archive: Dict[Tuple[int, ...], Dict[str, Any]] = {}
    stage1_unique_start_hashes: set[str] = set()
    stage1_unique_end_hashes: set[str] = set()
    stage1_best_score = float("-inf")
    stage1_best_sub: List[int] = []
    stage1_best_pt: List[int] = []
    stage1_best_match = float("-inf")
    ev1 = 0
    base_steps = int(solver_stage1_base_cfg.get("steps", 0))
    base_restarts = int(solver_stage1_base_cfg.get("restarts", 0))
    base_seed_restarts = int(solver_stage1_base_cfg.get("seed_restarts", stage1_seed_restarts))
    stage1_scouts_done = 0
    stage1_no_improve_scouts = 0
    stage1_seed_probe_added_total = 0
    stage1_seed_probe_scouts = 0

    for scout_idx in range(stage1_scout_runs):
        stage1_scouts_done += 1
        pre_scout_best_score = float(stage1_best_score)
        pre_scout_archive_n = int(len(stage1_archive))
        pre_scout_unique_end_n = int(len(stage1_unique_end_hashes))
        solver_stage1_cfg = dict(solver_stage1_base_cfg)
        solver_stage1_cfg["seed"] = int(solver_stage1_base_cfg.get("seed", 2026)) + 7919 * int(scout_idx)
        if scout_idx > 0:
            solver_stage1_cfg["steps"] = max(
                int(stage1_scout_min_steps),
                int(round(float(base_steps) * float(stage1_scout_step_scale))),
            )
            solver_stage1_cfg["restarts"] = max(
                int(stage1_scout_min_restarts),
                int(round(float(base_restarts) * float(stage1_scout_restart_scale))),
            )
            solver_stage1_cfg["seed_restarts"] = max(
                1,
                int(round(float(base_seed_restarts) * float(stage1_scout_restart_scale))),
            )

        scout_seed = 2026 + int(key_seed) + 1009 * int(scout_idx)
        s1_seeds = make_periodic_seed_pool(
            ct_idx,
            period=int(tier_period),
            direction=str(direction_value),
            seed=int(scout_seed),
            n_block_seeds=int(stage1_seed_n_blocks),
            total_seeds=int(stage1_seed_total),
            swaps_per_block=int(stage1_seed_swaps),
            alphabet_size=int(alphabet_size),
        )
        for seed_key in s1_seeds:
            stage1_unique_start_hashes.add(key_hash_fn(seed_key))
        sol1 = run(
            text=ct_idx.tolist(),
            cipher=by_name.cipher("periodic_substitution", period=int(tier_period), alphabet_size=int(alphabet_size)),
            key=KeySpec.periodic_substitution(period=int(tier_period), alphabet_size=int(alphabet_size)),
            solver=SolverSpec.kaeding(**solver_stage1_cfg),
            scorer_params=scorer_stage1,
            wli_data=[],
            encoding_dir=str(direction_value),
            telemetry_on=True,
            initial_keys=s1_seeds,
            force_no_wli=True,
        )
        scout_evals = int((getattr(sol1, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
        ev1 += scout_evals
        sub_best = np.asarray(getattr(sol1, "key", []) or [], dtype=np.int16).reshape(-1)
        sub_key_match_this = match_ratio_fn(sub_best.tolist(), true_sub.tolist())
        sub_candidates_this = extract_top_keys_fn(sol1, int(stage1_sub_limit)) or [sub_best.astype(int).tolist()]
        sub_candidates_source = "telemetry_topk"
        seed_probe_added = 0
        if len(sub_candidates_this) < int(stage1_sub_limit):
            seen_keys: set[Tuple[int, ...]] = set(
                tuple(int(x) for x in row) for row in sub_candidates_this if row
            )
            seed_probe_keys: List[np.ndarray] = []
            for seed_key in s1_seeds:
                seed_arr = np.asarray(seed_key, dtype=np.int16).reshape(-1)
                if seed_arr.size != int(sub_len):
                    continue
                seed_t = tuple(int(x) for x in seed_arr.tolist())
                if seed_t in seen_keys:
                    continue
                seen_keys.add(seed_t)
                seed_probe_keys.append(seed_arr)
            if seed_probe_keys:
                _pt_seed, sc_seed, _seed_stats = decrypt_and_score_keys_chunked(
                    cipher=sub_cipher,
                    ciphertext=ct_idx,
                    keys=seed_probe_keys,
                    scorer=scorer_stage1_runtime,
                    wli=None,
                    key_dtype=np.int16,
                    chunk_size=int(batch_eval_chunk_size),
                    require_batch=bool(require_batch_scoring),
                )
                if int(sc_seed.size) > 0:
                    seed_ranked = np.argsort(sc_seed)[::-1]
                    for seed_idx in seed_ranked.tolist():
                        if len(sub_candidates_this) >= int(stage1_sub_limit):
                            break
                        key_list = seed_probe_keys[int(seed_idx)].astype(int).tolist()
                        sub_candidates_this.append(key_list)
                        seed_probe_added += 1
            if seed_probe_added > 0:
                sub_candidates_source = "telemetry_plus_seed_probe"
                stage1_seed_probe_scouts += 1
                stage1_seed_probe_added_total += int(seed_probe_added)
            elif sub_candidates_this:
                sub_candidates_source = "telemetry_only"
            else:
                sub_candidates_source = "seed_probe_empty"

        sub_keys_stage1: List[np.ndarray] = []
        for sub_key in sub_candidates_this:
            sub_arr = np.asarray(sub_key, dtype=np.int16).reshape(-1)
            if sub_arr.size == int(sub_len):
                sub_keys_stage1.append(sub_arr)
        if sub_keys_stage1:
            pt_batch, sc_batch, _batch_stats = decrypt_and_score_keys_chunked(
                cipher=sub_cipher,
                ciphertext=ct_idx,
                keys=sub_keys_stage1,
                scorer=scorer_stage1_runtime,
                wli=None,
                key_dtype=np.int16,
                chunk_size=int(batch_eval_chunk_size),
                require_batch=bool(require_batch_scoring),
            )
            scout_unique_end_hashes: set[str] = set()
            for i_row, sub_arr in enumerate(sub_keys_stage1):
                pt1 = np.asarray(pt_batch[i_row], dtype=np.uint8).reshape(-1)
                sc1 = float(sc_batch[i_row])
                key_t = tuple(int(x) for x in sub_arr.tolist())
                scout_unique_end_hashes.add(key_hash_fn(key_t))
                sub_m = float(match_ratio_fn(sub_arr.tolist(), true_sub.tolist()))
                prev = stage1_archive.get(key_t)
                if (prev is None) or (sc1 > float(prev.get("score", float("-inf")))):
                    stage1_archive[key_t] = dict(
                        sub_key=sub_arr.astype(int).tolist(),
                        score=float(sc1),
                        sub_key_match=float(sub_m),
                        plaintext=pt1.astype(int).tolist(),
                    )
                if sc1 > stage1_best_score:
                    stage1_best_score = float(sc1)
                    stage1_best_sub = sub_arr.astype(int).tolist()
                    stage1_best_pt = pt1.astype(int).tolist()
                    stage1_best_match = float(sub_m)
            stage1_unique_end_hashes.update(scout_unique_end_hashes)

        stage1_score_gain = (
            float(stage1_best_score - pre_scout_best_score)
            if np.isfinite(stage1_best_score) and np.isfinite(pre_scout_best_score)
            else float("inf")
        )
        stage1_new_archive = int(len(stage1_archive) - pre_scout_archive_n)
        stage1_new_unique_hashes = int(len(stage1_unique_end_hashes) - pre_scout_unique_end_n)
        stages.append(
            dict(
                tier=str(tier_name),
                text_id=int(text_id),
                key_seed=int(key_seed),
                stage=f"stage1_sub_scout_{int(scout_idx) + 1}",
                score=float(getattr(sol1, "score", float("nan"))),
                sub_key_match=float(sub_key_match_this),
                seconds=0.0,
                evals=int(scout_evals),
                candidates=len(sub_candidates_this),
                candidate_source=str(sub_candidates_source),
                seed_probe_added=int(seed_probe_added),
                scout_seed=int(scout_seed),
                archive_size=int(len(stage1_archive)),
                new_archive_keys=int(stage1_new_archive),
                new_archive_hashes=int(stage1_new_unique_hashes),
                score_gain=(float(stage1_score_gain) if np.isfinite(stage1_score_gain) else np.nan),
            )
        )
        if (
            scout_idx > 0
            and stage1_score_gain <= float(stage1_scout_no_improve_delta)
            and stage1_new_unique_hashes <= int(stage1_scout_min_new_archive)
        ):
            stage1_no_improve_scouts += 1
        else:
            stage1_no_improve_scouts = 0
        min_scouts_before_early_stop = int(
            max(1, min(int(stage1_scout_runs), int(stage1_scout_early_stop_min_scouts)))
        )
        if (
            scout_idx + 1 < int(stage1_scout_runs)
            and int(stage1_scouts_done) >= int(min_scouts_before_early_stop)
            and stage1_no_improve_scouts >= int(stage1_scout_no_improve_patience)
        ):
            print(
                f"{log_prefix} stage1-early-stop tier={tier_name} text={text_id} key_seed={key_seed} "
                f"reason=scout_plateau scouts_done={stage1_scouts_done}/{stage1_scout_runs} "
                f"score_gain={stage1_score_gain:.6g} new_archive={stage1_new_archive} "
                f"new_archive_hashes={int(stage1_new_unique_hashes)}",
                flush=True,
            )
            break

    dt1 = float(time.time() - t_s1)
    stage1_ranked = sorted(
        stage1_archive.values(),
        key=lambda e: (float(e.get("score", float("-inf"))), float(e.get("sub_key_match", float("-inf")))),
        reverse=True,
    )
    if len(stage1_ranked) > int(stage1_archive_keep):
        stage1_ranked = stage1_ranked[: int(stage1_archive_keep)]
    sub_candidates = [list(map(int, e.get("sub_key", []))) for e in stage1_ranked if e.get("sub_key")]
    if not sub_candidates and stage1_best_sub:
        sub_candidates = [list(stage1_best_sub)]
    sub_key_match = float(stage1_best_match if np.isfinite(stage1_best_match) else 0.0)
    if stage1_best_pt:
        m1 = match_ratio_fn(stage1_best_pt, pt_idx.tolist())
        print_stage_preview_fn(label="stage1_sub", pt=stage1_best_pt, wli=wli, match_ratio=float(m1))
    stages.append(
        dict(
            tier=str(tier_name),
            text_id=int(text_id),
            key_seed=int(key_seed),
            stage="stage1_sub",
            score=float(stage1_best_score if np.isfinite(stage1_best_score) else np.nan),
            sub_key_match=float(sub_key_match),
            seconds=round(dt1, 3),
            evals=int(ev1),
            candidates=len(sub_candidates),
            scouts=int(stage1_scouts_done),
            archive_keep=int(stage1_archive_keep),
            archive_size=int(len(stage1_archive)),
        )
    )
    print(
        f"{log_prefix} stage1-summary tier={tier_name} text={text_id} key_seed={key_seed} "
        f"score={float(stage1_best_score if np.isfinite(stage1_best_score) else np.nan):.6f} "
        f"sub_key_match={float(sub_key_match):.3f} evals={int(ev1)} seconds={dt1:.1f} "
        f"candidates={len(sub_candidates)} scouts={int(stage1_scouts_done)} "
        f"archive_size={int(len(stage1_archive))} "
        f"seed_probe_scouts={int(stage1_seed_probe_scouts)} "
        f"seed_probe_added_total={int(stage1_seed_probe_added_total)}",
        flush=True,
    )
    print(
        f"{log_prefix} stage1-diversity tier={tier_name} text={text_id} key_seed={key_seed} "
        f"unique_start_hash={int(len(stage1_unique_start_hashes))} "
        f"unique_end_hash={int(len(stage1_unique_end_hashes))} "
        f"archive_size={int(len(stage1_archive))}",
        flush=True,
    )
    return dict(
        sub_candidates=[list(map(int, key)) for key in sub_candidates],
        sub_key_match=float(sub_key_match),
        stage1_best_score=float(stage1_best_score),
        evals=int(ev1),
    )
