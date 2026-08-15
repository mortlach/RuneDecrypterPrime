# -*- coding: utf-8 -*-
"""
solver/sa.py — Simulated Annealing using KeyOps neighbour + decrypt/score

Parity goals:
  - Classic acceptance with temperature schedule.
  - Deterministic rng; honours plateau/stop_score.
  - Emits canonical progress: iter, temp, evals, since_improve, best_score.
"""

from __future__ import annotations
import math
import numpy as np

from ..core.config.validation import strict_positive_int
from ..core.types import SolverName, KEY_DTYPE
from .solver_base import SolverBase


class SASolver(SolverBase):
    name = "sa"

    def __init__(self, problem, opt_cfg=None, **kwargs):
        params = {}
        if opt_cfg is not None:
            if isinstance(opt_cfg, dict):
                params = dict(opt_cfg)
            elif hasattr(opt_cfg, "as_dict"):
                params = dict(opt_cfg.as_dict())
            else:
                params = dict(getattr(opt_cfg, "__dict__", {}))

        auto_cooling = params.pop("auto_cooling", False)

        # Defaults (kept close to common SA setups; we’ll match legacy constants if provided)
        params.setdefault("iters", 2000)
        params["iters"] = strict_positive_int(params["iters"], "iters")
        params.setdefault("T0", 1.0)
        params.setdefault("Tmin", 1e-3)
        params.setdefault("cool", 0.995)           # geometric cooling
        params.setdefault("local_improve_on_accept", False)

        if auto_cooling:
            I = max(1, int(params["iters"]))
            T0 = max(1e-12, float(params["T0"]))
            Tmin = max(1e-12, float(params["Tmin"]))
            params["cool"] = 1.0 if Tmin >= T0 else float((Tmin / T0) ** (1.0 / I))

        if bool(params.get("sa_elitism", False)):
            raise ValueError("sa_elitism is not supported (remove or set to False)")

        rng = kwargs.get("rng")
        if rng is None:
            raise TypeError("SASolver requires rng=np.random.Generator from the engine")

        super().__init__(
            problem,
            optimizer_name=SolverName.SA,
            params=params,
            rng=rng,
            seed_keys=kwargs.get("seed_keys"),
            stop_score=kwargs.get("stop_score"),
            verbose=bool(kwargs.get("verbose", True)),
            log_interval=int(kwargs.get("log_interval", 50)),
        )

    # ---------- helpers ----------

    def _initial_key_and_score(self):
        # Best of seeds (if any) else random
        k0 = self._maybe_best_of_seeds(self.rng)
        if k0 is None:
            k0 = self.keyops.random(self.rng).astype(KEY_DTYPE, copy=False)
        s0 = float(self._score_batch(k0[None, :])[0])
        return k0, s0

    def _neighbor(self, k: np.ndarray) -> np.ndarray:
        if "neighbour" in self.keyops.caps.ops:
            return np.ascontiguousarray(self.keyops.neighbour(k, self.rng), dtype=KEY_DTYPE)
        if "neighbor" in self.keyops.caps.ops:
            return np.ascontiguousarray(self.keyops.neighbor(k, self.rng), dtype=KEY_DTYPE)
        # Fallback: mutate a single copy
        return np.ascontiguousarray(self.keyops.mutate(k[None, :], self.rng)[0], dtype=KEY_DTYPE)

    # ---------- main solve ----------

    def solve(self):
        I: int = int(self.get_param("iters", 2000))
        T0: float = float(self.get_param("T0", 1.0))
        Tmin: float = float(self.get_param("Tmin", 1e-3))
        cool: float = float(self.get_param("cool", 0.995))
        local_improve: bool = bool(self.get_param("local_improve_on_accept", False))
        rescue_abs: float = float(self.get_param("sa_rescue_drop_abs", 0.0) or 0.0)
        rescue_ratio: float = float(self.get_param("sa_rescue_drop_ratio", 0.0) or 0.0)
        reseed_interval: int = int(self.get_param("sa_reseed_interval", 0) or 0)
        fast = self._maybe_return_test_key_fastpath(SolverName.SA)
        if fast is not None:
            return fast

        span = self._start_span()
        total_evals = 0

        try:
            k_cur, s_cur = self._initial_key_and_score()
            k_best, s_best = k_cur.copy(), float(s_cur)
            total_evals += 1

            self._early_stop_reset(initial_best=s_best,
                                   plateau_override=int(self.get_param("plateau_rounds", 0)))

            T = float(T0)
            self._maybe_update_hamming_progress(0.0)
            for it in range(1, I + 1):
                # Temperature schedule (geometric)
                if it > 1:
                    T = max(Tmin, T * cool)
                # Update Hamming weight based on progress through SA
                self._maybe_update_hamming_progress(it / float(I))

                # Neighbour + evaluate
                k2 = self._neighbor(k_cur)
                s2 = float(self._score_batch(k2[None, :])[0]); total_evals += 1

                d = s2 - s_cur
                accept = False
                if d >= 0:
                    accept = True
                else:
                    # classic Metropolis
                    p = math.exp(d / max(1e-12, T))
                    accept = (self.rng.random() < p)

                if accept:
                    k_cur, s_cur = k2, s2
                    if local_improve:
                        k_cur, s_cur = self._local_improve(k_cur, s_cur, self.rng)

                # Track best & plateau
                if s_cur > s_best:
                    k_best, s_best = k_cur.copy(), float(s_cur)
                plateau_stop = self._early_stop_update(float(s_best), int(it))
                since_improve = int(self._since_improve(int(it)))

                # Optional rescue/reset if we drift too far from the best solution seen.
                if rescue_abs > 0 and (s_best - s_cur) >= rescue_abs:
                    k_cur, s_cur = k_best.copy(), float(s_best)
                elif rescue_ratio > 0 and s_best > 0 and s_cur <= s_best * (1.0 - rescue_ratio):
                    k_cur, s_cur = k_best.copy(), float(s_best)

                if reseed_interval > 0 and (it % reseed_interval == 0):
                    reseed = self._maybe_best_of_seeds(self.rng)
                    if reseed is not None:
                        k_cur = reseed.copy()
                        s_cur = float(self._score_batch(k_cur[None, :])[0])
                        total_evals += 1
                        if s_cur > s_best:
                            k_best, s_best = k_cur.copy(), float(s_cur)
                            plateau_stop = self._early_stop_update(float(s_best), int(it))
                            since_improve = int(self._since_improve(int(it)))

                # Percent-bucket progress
                self._progress_pct(
                    it,
                    I,
                    iter=int(it),
                    temp=float(T),
                    best_score=float(s_best),
                    evals=int(total_evals),
                    since_improve=int(since_improve),
                    preview_key=k_best,
                )

                # Early-stop checks
                if self._early_stop_stop_score(float(s_best)) or plateau_stop:
                    break

            if self._stop_reason is None:
                self._stop_reason = "max_iterations_reached"
            self._end_span(getattr(self, "_span", None),
                           iters=int(it),
                           candidates=int(total_evals),
                           best_score=float(s_best),
                           reason=self._stop_reason)
            return self._finalize_solution(k_best, float(s_best))

        except Exception as e:
            self._end_span(getattr(self, "_span", None), error=str(e))
            raise
