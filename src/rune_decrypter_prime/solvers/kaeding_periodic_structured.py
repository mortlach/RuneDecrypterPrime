# -*- coding: utf-8 -*-
"""
Kaeding-style solver for periodic structured keys.
Block-focused swaps with occasional column moves and slips.
"""
from __future__ import annotations
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

    def solve(self):
        traits = self._structure_traits()
        self.A = int(traits.get("alphabet_size"))
        self.period = int(traits.get("period"))
        self.columns = int(traits.get("columns", 0) or 0)
        self.sub_len = int(self.period * self.A)
        has_columnar = bool(traits.get("has_columnar", False) and self.columns > 0)

        steps = max(1, int(self.get_param("steps", 2000)))
        restarts = max(1, int(self.get_param("restarts", 8)))
        inner_batch = max(1, int(self.get_param("inner_batch", 128)))
        block_schedule = str(self.get_param("block_schedule", "round_robin") or "round_robin")
        slip_every = max(0, int(self.get_param("slip_every", 50)))
        slip_blocks = max(1, int(self.get_param("slip_blocks", 1)))
        col_every = max(0, int(self.get_param("col_every", 10)))
        col_batch = max(1, int(self.get_param("col_batch", 64)))

        if block_schedule not in {"round_robin", "random"}:
            raise ValueError("block_schedule must be 'round_robin' or 'random'")

        fast = self._maybe_return_test_key_fastpath(SolverName.KAEDING)
        if fast is not None:
            return fast

        span = self._start_span()
        total_evals = 0
        total_steps = steps * restarts
        global_step = 0

        try:
            best_key = None
            best_score = float("-inf")

            self._early_stop_reset(initial_best=best_score,
                                   plateau_override=int(self.get_param("plateau_rounds", 0)))

            self._maybe_update_hamming_progress(0.0)

            for restart in range(restarts):
                if restart == 0:
                    k = self._maybe_best_of_seeds(self.rng)
                else:
                    k = self.keyops.random(self.rng).astype(KEY_DTYPE, copy=False)
                k = np.ascontiguousarray(self.keyops.normalize(k), dtype=self.key_dtype)
                s = float(self._score_batch(k[None, :])[0])
                total_evals += 1

                if s > best_score:
                    best_score = float(s)
                    best_key = k.copy()

                for step in range(1, steps + 1):
                    global_step += 1
                    self._maybe_update_hamming_progress(global_step / float(total_steps))

                    if block_schedule == "round_robin":
                        block = (step - 1) % self.period
                    else:
                        block = int(self.rng.integers(0, self.period))

                    slip = False
                    col_moves = 0
                    improved = False

                    candidates = self._block_swap_batch(k, block, inner_batch)
                    scores = self._score_batch(candidates)
                    total_evals += int(candidates.shape[0])
                    idx = int(np.argmax(scores))
                    if scores[idx] > s:
                        k = candidates[idx].copy()
                        s = float(scores[idx])
                        improved = True

                    if has_columnar and col_every > 0 and (step % col_every == 0):
                        col_candidates = self._col_swap_batch(k, col_batch)
                        col_scores = self._score_batch(col_candidates)
                        total_evals += int(col_candidates.shape[0])
                        col_moves = int(col_candidates.shape[0])
                        idx = int(np.argmax(col_scores))
                        if col_scores[idx] > s:
                            k = col_candidates[idx].copy()
                            s = float(col_scores[idx])
                            improved = True

                    if slip_every > 0 and (step % slip_every == 0):
                        picks = self.rng.choice(self.period, size=min(self.period, slip_blocks), replace=False)
                        k = self._slip_blocks(k, picks.tolist())
                        s = float(self._score_batch(k[None, :])[0])
                        total_evals += 1
                        slip = True

                    if s > best_score:
                        best_score = float(s)
                        best_key = k.copy()

                    plateau_stop = self._early_stop_update(float(best_score), int(global_step))
                    since_improve = int(self._since_improve(int(global_step)))

                    self._progress_pct(
                        global_step,
                        total_steps,
                        step=int(global_step),
                        restart=int(restart),
                        block=int(block),
                        slip=int(slip),
                        col_moves=int(col_moves),
                        improved=int(improved),
                        best_score=float(best_score),
                        evals=int(total_evals),
                        since_improve=int(since_improve),
                        preview_key=best_key,
                    )

                    if self._early_stop_stop_score(float(best_score)) or plateau_stop:
                        break

                if self._early_stop_stop_score(float(best_score)) or plateau_stop:
                    break

            if best_key is None:
                best_key = self.keyops.random(self.rng).astype(self.key_dtype, copy=False)
                best_score = float(self._score_batch(best_key[None, :])[0])
                total_evals += 1

            self._end_span(getattr(self, "_span", None),
                           steps=int(global_step),
                           candidates=int(total_evals),
                           best_score=float(best_score),
                           reason=(getattr(self, "_stop_reason", None) or "done"))
            return self._finalize_solution(best_key, float(best_score))

        except Exception as e:
            self._end_span(getattr(self, "_span", None), error=str(e))
            raise
