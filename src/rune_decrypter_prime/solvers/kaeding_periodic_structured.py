# -*- coding: utf-8 -*-
"""
Kaeding-style solver for periodic structured keys.
Block-focused swaps with occasional column moves and slips.
"""
from __future__ import annotations
from collections import deque
import hashlib
import numpy as np

from ..core.types import SolverName, KEY_DTYPE
from .solver_base import SolverBase


class KaedingPeriodicStructuredSolver(SolverBase):
    name = "kaeding"

    def __init__(self, problem, opt_cfg=None, **kwargs):
        params = {}
        if opt_cfg is not None:
            if isinstance(opt_cfg, dict):
                params = dict(opt_cfg)
            elif hasattr(opt_cfg, "as_dict"):
                params = dict(opt_cfg.as_dict())
            else:
                params = dict(getattr(opt_cfg, "__dict__", {}))

        params.setdefault("steps", 2000)
        params.setdefault("restarts", 8)
        params.setdefault("inner_batch", 128)
        params.setdefault("block_schedule", "round_robin")
        params.setdefault("slip_every", 50)
        params.setdefault("slip_blocks", 1)
        params.setdefault("col_every", 10)
        params.setdefault("col_batch", 64)
        params.setdefault("seed_selection_metric", "auto")
        params.setdefault("seed_restarts", 0)

        rng = kwargs.get("rng")
        if rng is None:
            raise TypeError("KaedingPeriodicStructuredSolver requires rng=np.random.Generator from the engine")

        super().__init__(
            problem,
            optimizer_name=SolverName.KAEDING,
            params=params,
            rng=rng,
            seed_keys=kwargs.get("seed_keys"),
            stop_score=kwargs.get("stop_score"),
            verbose=bool(kwargs.get("verbose", True)),
            log_interval=int(kwargs.get("log_interval", 50)),
        )

    def _structure_traits(self) -> dict:
        traits = getattr(getattr(self.keyops, "caps", None), "traits", {}) or {}
        if traits.get("structure") != "periodic_structured":
            raise ValueError("Kaeding solver requires periodic_structured keyops (use SA/GA/Hybrid otherwise).")
        return traits

    def _block_swap_batch(self, key: np.ndarray, block: int, batch_size: int) -> np.ndarray:
        out = np.empty((batch_size, self.K), dtype=self.key_dtype)
        start = block * self.A
        for i in range(batch_size):
            cand = key.copy()
            a = int(self.rng.integers(0, self.A))
            b = int(self.rng.integers(0, self.A - 1))
            if b >= a:
                b += 1
            i1 = start + a
            i2 = start + b
            cand[i1], cand[i2] = cand[i2], cand[i1]
            out[i] = cand
        return out

    def _col_swap_batch(self, key: np.ndarray, batch_size: int) -> np.ndarray:
        out = np.empty((batch_size, self.K), dtype=self.key_dtype)
        start = self.sub_len
        for i in range(batch_size):
            cand = key.copy()
            a = int(self.rng.integers(0, self.columns))
            b = int(self.rng.integers(0, self.columns - 1))
            if b >= a:
                b += 1
            i1 = start + a
            i2 = start + b
            cand[i1], cand[i2] = cand[i2], cand[i1]
            out[i] = cand
        return out

    def _slip_blocks(self, key: np.ndarray, blocks: list[int]) -> np.ndarray:
        out = key.copy()
        for r in blocks:
            base = np.arange(self.A, dtype=self.key_dtype)
            self.rng.shuffle(base)
            start = int(r) * self.A
            out[start : start + self.A] = base
        return out

    def _partial_slip_block(self, key: np.ndarray, block: int, swaps: int) -> np.ndarray:
        out = key.copy()
        start = int(block) * self.A
        swaps = max(1, int(swaps))
        for _ in range(swaps):
            a = int(self.rng.integers(0, self.A))
            b = int(self.rng.integers(0, self.A - 1))
            if b >= a:
                b += 1
            i1 = start + a
            i2 = start + b
            out[i1], out[i2] = out[i2], out[i1]
        return out

    def _score_batch_dual(self, keys: np.ndarray, *, use_raw: bool) -> tuple[np.ndarray, np.ndarray]:
        if use_raw:
            eval_raw = getattr(self.problem, "evaluate_keys_with_raw", None)
            if callable(eval_raw):
                pct, raw = eval_raw(keys)
                return np.asarray(pct, dtype=np.float64), np.asarray(raw, dtype=np.float64)
        pct = self._score_batch(keys)
        return np.asarray(pct, dtype=np.float64), np.asarray(pct, dtype=np.float64)

    @staticmethod
    def _key_hash16(key_vec: np.ndarray) -> str:
        arr = np.asarray(key_vec, dtype=np.int16).reshape(-1)
        return hashlib.sha1(arr.tobytes()).hexdigest()[:16]

    def _resolve_seed_selection_metric(self, *, use_raw_score: bool) -> str:
        raw = str(self.get_param("seed_selection_metric", "auto") or "auto").strip().lower()
        if raw == "auto":
            return "raw" if use_raw_score else "pct"
        if raw in {"raw", "pct"}:
            return raw
        raise ValueError("seed_selection_metric must be one of {'auto','raw','pct'}")

    def _prepare_seed_schedule(self, rng, *, use_raw_score: bool) -> list[np.ndarray]:
        """
        Build restart seed schedule.

        - If seed_keys are provided: rank them once and consume in order for early restarts.
        - Otherwise: keep old behaviour (initial_key if present, else random for restart 0).
        """
        seed_keys = getattr(self, "seed_keys", None)
        initial_key = getattr(self, "initial_key", None)

        no_seeds = False
        if seed_keys is None:
            no_seeds = True
        elif isinstance(seed_keys, np.ndarray):
            no_seeds = (seed_keys.size == 0)
        elif isinstance(seed_keys, (list, tuple)):
            no_seeds = (len(seed_keys) == 0)

        if no_seeds:
            if initial_key is not None:
                key = np.ascontiguousarray(np.array(initial_key, dtype=self.key_dtype))
                if key.ndim == 2:
                    key = key[0]
                elif key.ndim != 1:
                    key = self.keyops.normalize(key)
                    if key.ndim == 2:
                        key = key[0]
                key = key.astype(self.key_dtype, copy=False)
                self._seed_selection_meta = {
                    "seed_selected_source": "initial_key",
                    "seed_selection_metric": "n/a",
                    "seed_selected_index": -1,
                    "seed_selected_hash": self._key_hash16(key),
                    "seed_selected_raw": None,
                    "seed_selected_pct": None,
                    "seed_pool_size": 0,
                    "seed_restarts_used": 1,
                }
                return [key]

            k = self.keyops.random(rng).astype(self.key_dtype, copy=False)
            self._seed_selection_meta = {
                "seed_selected_source": "random",
                "seed_selection_metric": "n/a",
                "seed_selected_index": -1,
                "seed_selected_hash": self._key_hash16(k),
                "seed_selected_raw": None,
                "seed_selected_pct": None,
                "seed_pool_size": 0,
                "seed_restarts_used": 1,
            }
            return [k]

        seeds = np.array(seed_keys, dtype=self.key_dtype, copy=False)
        if seeds.ndim == 1:
            seeds = seeds[None, :]
        seeds = np.ascontiguousarray(seeds, dtype=self.key_dtype)

        if seeds.shape[1] != self.K:
            rows = []
            for row in seeds:
                fixed = self.keyops.normalize(row)
                if fixed.ndim == 2:
                    fixed = fixed[0]
                rows.append(np.ascontiguousarray(fixed, dtype=self.key_dtype))
            seeds = np.ascontiguousarray(np.stack(rows, axis=0), dtype=self.key_dtype)

        # Always request dual scores so we can rank by either raw or pct.
        pct_scores, raw_scores = self._score_batch_dual(seeds, use_raw=True)
        pct_scores = np.asarray(pct_scores, dtype=np.float64)
        raw_scores = np.asarray(raw_scores, dtype=np.float64)

        metric = self._resolve_seed_selection_metric(use_raw_score=use_raw_score)
        rank_scores = raw_scores if metric == "raw" else pct_scores
        order = np.argsort(rank_scores, kind="mergesort")[::-1]
        ordered = np.ascontiguousarray(seeds[order], dtype=self.key_dtype)
        ordered_raw = raw_scores[order]
        ordered_pct = pct_scores[order]

        seed_restarts = max(0, int(self.get_param("seed_restarts", 0)))
        n_use = int(ordered.shape[0]) if seed_restarts <= 0 else min(seed_restarts, int(ordered.shape[0]))
        schedule = [ordered[i].copy() for i in range(n_use)]

        first_raw = (
            float(ordered_raw[0])
            if ordered_raw.size and np.isfinite(ordered_raw[0])
            else None
        )
        first_pct = (
            float(ordered_pct[0])
            if ordered_pct.size and np.isfinite(ordered_pct[0])
            else None
        )
        first_idx = int(order[0]) if order.size else -1
        first_hash = self._key_hash16(schedule[0]) if schedule else ""
        self._seed_selection_meta = {
            "seed_selected_source": "seed_pool",
            "seed_selection_metric": metric,
            "seed_selected_index": first_idx,
            "seed_selected_hash": first_hash,
            "seed_selected_raw": first_raw,
            "seed_selected_pct": first_pct,
            "seed_pool_size": int(seeds.shape[0]),
            "seed_restarts_used": int(len(schedule)),
        }
        return schedule

    @staticmethod
    def _pick_stall_phase(attempts: np.ndarray, improves: np.ndarray) -> int:
        if attempts.size == 0:
            return 0
        # Prefer the least-improving phase (tie-breaker: fewer attempts).
        scores = improves.astype(np.int64)
        min_imp = int(scores.min())
        candidates = np.where(scores == min_imp)[0]
        if candidates.size == 1:
            return int(candidates[0])
        cand_attempts = attempts[candidates]
        return int(candidates[int(np.argmin(cand_attempts))])

    def solve(self):
        traits = self._structure_traits()
        self.A = int(traits.get("alphabet_size"))
        self.period = int(traits.get("period"))
        self.columns = int(traits.get("columns", 0) or 0)
        self.sub_len = int(self.period * self.A)
        # Column swap requires at least two columns; columns==1 is a valid degenerate case.
        has_columnar = bool(traits.get("has_columnar", False) and self.columns > 1)

        steps = max(1, int(self.get_param("steps", 2000)))
        restarts = max(1, int(self.get_param("restarts", 8)))
        inner_batch = max(1, int(self.get_param("inner_batch", 128)))
        block_schedule = str(self.get_param("block_schedule", "round_robin") or "round_robin")
        slip_every = max(0, int(self.get_param("slip_every", 50)))
        slip_blocks = max(1, int(self.get_param("slip_blocks", 1)))
        col_every = max(0, int(self.get_param("col_every", 10)))
        col_batch = max(1, int(self.get_param("col_batch", 64)))
        slip_policy = str(self.get_param("slip_policy", "fixed") or "fixed").lower()
        stall_rounds = max(0, int(self.get_param("stall_rounds", slip_every)))
        stall_slip_limit = max(0, int(self.get_param("stall_slip_limit", 2)))
        slip_swaps = max(1, int(self.get_param("slip_swaps", 20)))
        stall_stop_on_limit = bool(self.get_param("stall_stop_on_limit", False))
        slip_follow_steps = max(1, int(self.get_param("slip_follow_steps", 200)))
        use_raw_score = bool(self.get_param("use_raw_score", True))
        raw_accept_min_delta = float(self.get_param("raw_accept_min_delta", 1e-6) or 0.0)
        pct_plateau_min_delta = float(self.get_param("pct_plateau_min_delta", 0.0) or 0.0)
        delta_window = max(1, int(self.get_param("delta_window", 200)))
        top_k = max(0, int(self.get_param("top_k", 0)))

        if block_schedule not in {"round_robin", "random"}:
            raise ValueError("block_schedule must be 'round_robin' or 'random'")
        if slip_policy not in {"fixed", "stall"}:
            raise ValueError("slip_policy must be 'fixed' or 'stall'")

        fast = self._maybe_return_test_key_fastpath(SolverName.KAEDING)
        if fast is not None:
            return fast

        self._seed_selection_meta = {}
        self._start_span()
        total_evals = 0
        total_steps = steps * restarts
        global_step = 0

        try:
            best_key = None
            best_raw = float("-inf")
            best_pct = float("-inf")
            best_pct_seen = float("-inf")
            last_pct_improve_at = 0
            accept_count = 0
            attempt_count = 0
            block_accept_count = 0
            col_accept_count = 0
            slip_count = 0
            delta_history = deque(maxlen=delta_window)
            phase_attempts = np.zeros((self.period,), dtype=np.int64)
            phase_improves = np.zeros((self.period,), dtype=np.int64)
            phase_best_delta = np.full((self.period,), float("-inf"), dtype=np.float64)
            slip_history: list[dict] = []
            active_slips: list[dict] = []
            top_candidates: list[tuple[float, float, tuple[int, ...]]] = []
            top_seen: set[tuple[int, ...]] = set()
            restart_start_hashes: list[str] = []

            self._early_stop_reset(initial_best=best_raw,
                                   plateau_override=int(self.get_param("plateau_rounds", 0)))

            self._maybe_update_hamming_progress(0.0)

            def _record_top(raw_score: float, pct_score: float, key_vec: np.ndarray) -> None:
                if top_k <= 0:
                    return
                t = tuple(int(x) for x in key_vec.tolist())
                if t in top_seen:
                    return
                top_candidates.append((float(raw_score), float(pct_score), t))
                top_seen.add(t)
                if len(top_candidates) > top_k:
                    top_candidates.sort(key=lambda x: x[0], reverse=True)
                    drop = top_candidates[top_k:]
                    top_candidates[:] = top_candidates[:top_k]
                    for _, _, k in drop:
                        top_seen.discard(k)

            def _update_best(raw_score: float, pct_score: float, key_vec: np.ndarray, step_idx: int) -> None:
                nonlocal best_raw, best_pct, best_key, best_pct_seen, last_pct_improve_at
                if raw_score > (best_raw + raw_accept_min_delta):
                    best_raw = float(raw_score)
                    best_pct = float(pct_score)
                    best_key = key_vec.copy()
                    _record_top(best_raw, best_pct, best_key)
                if pct_score > (best_pct_seen + pct_plateau_min_delta):
                    best_pct_seen = float(pct_score)
                    last_pct_improve_at = int(step_idx)
                    self._best_at_step = int(step_idx)

            seed_schedule = self._prepare_seed_schedule(self.rng, use_raw_score=use_raw_score)
            if isinstance(self._seed_selection_meta, dict):
                self._seed_selection_meta.setdefault("seed_restarts_used", int(len(seed_schedule)))
                self._seed_selection_meta.setdefault("seed_restarts_config", int(self.get_param("seed_restarts", 0)))

            for restart in range(restarts):
                stall_slips_used = 0
                if restart < len(seed_schedule):
                    k = seed_schedule[restart].copy()
                else:
                    k = self.keyops.random(self.rng).astype(KEY_DTYPE, copy=False)
                k = np.ascontiguousarray(self.keyops.normalize(k), dtype=self.key_dtype)
                restart_start_hashes.append(self._key_hash16(k))
                s_pct_arr, s_raw_arr = self._score_batch_dual(k[None, :], use_raw=use_raw_score)
                s_pct = float(s_pct_arr[0])
                s_raw = float(s_raw_arr[0])
                total_evals += 1

                _update_best(s_raw, s_pct, k, global_step)

                for step in range(1, steps + 1):
                    global_step += 1
                    self._maybe_update_hamming_progress(global_step / float(total_steps))

                    if block_schedule == "round_robin":
                        block = (step - 1) % self.period
                    else:
                        block = int(self.rng.integers(0, self.period))

                    slip = False
                    col_moves = 0
                    block_improved = False
                    col_improved = False
                    best_delta_raw = 0.0
                    median_delta_raw = 0.0

                    candidates = self._block_swap_batch(k, block, inner_batch)
                    scores_pct, scores_raw = self._score_batch_dual(candidates, use_raw=use_raw_score)
                    total_evals += int(candidates.shape[0])
                    attempt_count += 1
                    phase_attempts[block] += 1
                    if np.isneginf(s_raw):
                        raw_deltas = np.where(np.isfinite(scores_raw), np.inf, -np.inf)
                    elif np.isfinite(s_raw):
                        raw_deltas = scores_raw - s_raw
                    else:
                        raw_deltas = np.full_like(scores_raw, -np.inf)
                    idx = int(np.argmax(scores_raw))
                    if raw_deltas.size:
                        best_delta_raw = float(raw_deltas[idx])
                        median_delta_raw = float(np.median(raw_deltas))
                        delta_history.append(best_delta_raw)
                        if scores_raw[idx] > (s_raw + raw_accept_min_delta):
                            k = candidates[idx].copy()
                            s_raw = float(scores_raw[idx])
                            s_pct = float(scores_pct[idx])
                            block_improved = True
                            accept_count += 1
                            block_accept_count += 1
                            phase_improves[block] += 1
                            if best_delta_raw > phase_best_delta[block]:
                                phase_best_delta[block] = best_delta_raw

                    if has_columnar and col_every > 0 and (step % col_every == 0):
                        col_candidates = self._col_swap_batch(k, col_batch)
                        col_pct, col_raw = self._score_batch_dual(col_candidates, use_raw=use_raw_score)
                        total_evals += int(col_candidates.shape[0])
                        col_moves = int(col_candidates.shape[0])
                        attempt_count += 1
                        if np.isneginf(s_raw):
                            col_deltas = np.where(np.isfinite(col_raw), np.inf, -np.inf)
                        elif np.isfinite(s_raw):
                            col_deltas = col_raw - s_raw
                        else:
                            col_deltas = np.full_like(col_raw, -np.inf)
                        col_idx = int(np.argmax(col_raw))
                        if col_deltas.size:
                            col_best_delta = float(col_deltas[col_idx])
                            delta_history.append(col_best_delta)
                            best_delta_raw = max(best_delta_raw, col_best_delta)
                            median_delta_raw = float(np.median(col_deltas))  # noqa: F841 -- retained for loop diagnostics
                        if col_raw[col_idx] > (s_raw + raw_accept_min_delta):
                            k = col_candidates[col_idx].copy()
                            s_raw = float(col_raw[col_idx])
                            s_pct = float(col_pct[col_idx])
                            col_improved = True
                            accept_count += 1
                            col_accept_count += 1

                    if slip_policy == "fixed" and slip_every > 0 and (step % slip_every == 0):
                        raw_before = float(s_raw)
                        picks = self.rng.choice(self.period, size=min(self.period, slip_blocks), replace=False)
                        k = self._slip_blocks(k, picks.tolist())
                        s_pct_arr, s_raw_arr = self._score_batch_dual(k[None, :], use_raw=use_raw_score)
                        s_pct = float(s_pct_arr[0])
                        s_raw = float(s_raw_arr[0])
                        total_evals += 1
                        slip = True
                        slip_count += 1
                        active_slips.append({
                            "step": int(global_step),
                            "raw_before": raw_before,
                            "raw_after": float(s_raw),
                            "raw_best_after": float(s_raw),
                        })

                    _update_best(s_raw, s_pct, k, global_step)

                    plateau_stop = self._early_stop_update(float(best_raw), int(global_step))
                    since_improve = int(self._since_improve(int(global_step)))

                    if slip_policy == "stall" and stall_rounds > 0 and since_improve >= stall_rounds:
                        if stall_slips_used < stall_slip_limit:
                            raw_before = float(s_raw)
                            stall_phase = self._pick_stall_phase(phase_attempts, phase_improves)
                            k = self._partial_slip_block(k, stall_phase, slip_swaps)
                            s_pct_arr, s_raw_arr = self._score_batch_dual(k[None, :], use_raw=use_raw_score)
                            s_pct = float(s_pct_arr[0])
                            s_raw = float(s_raw_arr[0])
                            total_evals += 1
                            slip = True
                            slip_count += 1
                            stall_slips_used += 1
                            active_slips.append({
                                "step": int(global_step),
                                "raw_before": raw_before,
                                "raw_after": float(s_raw),
                                "raw_best_after": float(s_raw),
                            })
                            _update_best(s_raw, s_pct, k, global_step)
                            self._last_improve_at = int(global_step)
                            self._best_at_step = int(global_step)
                            plateau_stop = False
                            since_improve = 0
                        elif stall_stop_on_limit:
                            self._stop_reason = f"stall_slip_limit_{int(stall_slip_limit)}"
                            plateau_stop = True

                    if plateau_stop and pct_plateau_min_delta > 0.0:
                        if (int(global_step) - int(last_pct_improve_at)) < int(self.plateau_rounds):
                            self._last_improve_at = int(last_pct_improve_at)
                            plateau_stop = False

                    for rec in list(active_slips):
                        rec["raw_best_after"] = max(float(rec.get("raw_best_after", s_raw)), float(s_raw))
                        if int(global_step) - int(rec["step"]) >= slip_follow_steps:
                            rec["raw_best_after_200"] = float(rec.pop("raw_best_after"))
                            slip_history.append(rec)
                            active_slips.remove(rec)

                    accept_rate = float(accept_count) / float(max(1, attempt_count))
                    hist_median = float(np.median(delta_history)) if len(delta_history) > 0 else 0.0

                    self._progress_pct(
                        global_step,
                        total_steps,
                        step=int(global_step),
                        restart=int(restart),
                        block=int(block),
                        slip=int(slip),
                        col_moves=int(col_moves),
                        improved=int(block_improved or col_improved),
                        best_score=float(best_pct),
                        best_raw=float(best_raw),
                        delta_raw_best=float(best_delta_raw),
                        delta_raw_median=float(hist_median),
                        accept_rate=accept_rate,
                        evals=int(total_evals),
                        since_improve=int(since_improve),
                        preview_key=best_key,
                    )

                    if self._early_stop_stop_score(float(best_pct)) or plateau_stop:
                        break

                if self._early_stop_stop_score(float(best_pct)) or plateau_stop:
                    break

            if best_key is None:
                best_key = self.keyops.random(self.rng).astype(self.key_dtype, copy=False)
                best_pct_arr, best_raw_arr = self._score_batch_dual(best_key[None, :], use_raw=use_raw_score)
                best_pct = float(best_pct_arr[0])
                best_raw = float(best_raw_arr[0])
                total_evals += 1

            # Finalize slip history and attach telemetry summaries.
            try:
                for rec in list(active_slips):
                    rec["raw_best_after_200"] = float(rec.pop("raw_best_after", best_raw))
                    slip_history.append(rec)
                    active_slips.remove(rec)
            except Exception:
                pass

            tele = getattr(self.problem, "telemetry", None)
            if isinstance(tele, dict):
                try:
                    sc = getattr(self.problem, "scorer", None)
                    wli = getattr(self.problem, "wli_data", None)
                    pt_idx = None
                    resolver = getattr(self.problem, "resolve_plaintext", None)
                    if callable(resolver):
                        pt_idx = resolver(best_key)
                    if pt_idx is None:
                        pt_idx = self.problem.cipher.decrypt(ciphertext=self.problem.ciphertext, key=best_key)
                    if isinstance(pt_idx, tuple):
                        pt_idx = pt_idx[0]
                    pt_idx = np.asarray(pt_idx, dtype=np.int64).reshape(-1).tolist()
                    if sc is not None:
                        if hasattr(sc, "score_with_raw") and callable(sc.score_with_raw):
                            sc.score_with_raw(pt_idx, wli)
                        else:
                            sc.score(pt_idx, wli)
                        stats = sc.last_stats() if hasattr(sc, "last_stats") else {}
                        obj = None
                        if isinstance(stats, dict):
                            obj = stats.get("objective_stats") or stats.get("objective")
                        if isinstance(obj, dict):
                            tele["objective"] = obj
                        else:
                            tele["objective"] = {
                                "pct_lm": float(best_pct),
                                "raw_total": float(best_raw),
                            }
                except Exception:
                    tele["objective"] = {
                        "pct_lm": float(best_pct),
                        "raw_total": float(best_raw),
                    }

                try:
                    per_phase = {}
                    for i in range(int(self.period)):
                        per_phase[str(i)] = {
                            "attempts": int(phase_attempts[i]),
                            "improves": int(phase_improves[i]),
                            "best_delta_raw": (
                                None if not np.isfinite(phase_best_delta[i]) else float(phase_best_delta[i])
                            ),
                        }
                    kaeding_meta = {
                        "accept_rate": float(accept_count) / float(max(1, attempt_count)),
                        "block_accept_count": int(block_accept_count),
                        "col_accept_count": int(col_accept_count),
                        "slip_count": int(slip_count),
                        "best_delta_raw": (float(max(delta_history)) if len(delta_history) > 0 else 0.0),
                        "median_delta_raw": (float(np.median(delta_history)) if len(delta_history) > 0 else 0.0),
                        "since_improve": int(self._since_improve(int(global_step))),
                        "slips": slip_history,
                        "per_phase": per_phase,
                        "best_pct": float(best_pct),
                        "best_raw": float(best_raw),
                        "restart_start_hashes": list(restart_start_hashes),
                    }
                    seed_meta = getattr(self, "_seed_selection_meta", None)
                    if isinstance(seed_meta, dict) and seed_meta:
                        kaeding_meta.update(seed_meta)
                    if top_candidates:
                        top_candidates.sort(key=lambda x: x[0], reverse=True)
                        kaeding_meta["top_keys"] = [list(k) for _, _, k in top_candidates]
                        kaeding_meta["top_raw"] = [float(r) for r, _, _ in top_candidates]
                        kaeding_meta["top_pct"] = [float(p) for _, p, _ in top_candidates]
                    tele["kaeding"] = kaeding_meta
                except Exception:
                    pass

            final_score = float(best_raw) if use_raw_score else float(best_pct)
            if self._stop_reason is None:
                self._stop_reason = "max_steps_reached"
            self._end_span(getattr(self, "_span", None),
                           steps=int(global_step),
                           candidates=int(total_evals),
                           best_score=float(final_score),
                           best_raw=float(best_raw),
                           reason=self._stop_reason)
            return self._finalize_solution(best_key, float(final_score))

        except Exception as e:
            self._end_span(getattr(self, "_span", None), error=str(e))
            raise
