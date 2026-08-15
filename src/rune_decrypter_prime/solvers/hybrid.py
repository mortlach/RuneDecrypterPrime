# -*- coding: utf-8 -*-
"""
solver/hybrid.py — Phase-chained Hybrid: Beam → GA → SA

Goals:
  - Deterministic: one main rng; child rngs spawned per phase.
  - Phase tags in progress: {"phase": "beam"|"ga"|"sa"}.
  - True handover: Beam seeds → GA start; GA best → SA start.
  - Best-of selection at the end, with meta["from_phase"] recorded.
  - Canonical stop/telemetry fields preserved.

Params (all optional; defaults chosen to match common recipes):
  use_beam: bool (default True if beam_width > 0)
  beam.* : forwarded to BeamSolver
  ga.*   : forwarded to GASolver
  sa.*   : forwarded to SASolver

Stop behaviour:
  - Global stop_score honoured across phases (early termination if reached).
  - Per-phase plateaus are handled by the sub-solvers themselves.
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
import numpy as np

from ..core.types import SolverName, KEY_DTYPE
from .solver_base import SolverBase
from .beam import BeamSolver
from .ga import GASolver
from .sa import SASolver


def _child_rng(parent: np.random.Generator, tag: int) -> np.random.Generator:
    # Create a deterministic child stream without relying on global state
    try:
        # NumPy >=1.20 style: advance a derived stream by mixing in a tag
        s = np.random.SeedSequence(parent.bit_generator.state["state"]["state"] ^ (0x9E3779B97F4A7C15 * (1 + tag)))
        return np.random.Generator(np.random.PCG64(s))
    except Exception:
        # Conservative fallback: sample a u64 from parent as a seed
        seed = int(parent.integers(0, 2**63 - 1, dtype=np.int64))
        return np.random.Generator(np.random.PCG64(seed ^ (0xD1B54A32D192ED03 * (1 + tag))))


class HybridSolver(SolverBase):
    name = "hybrid"

    def __init__(self, problem, opt_cfg=None, **kwargs):
        # Flatten/normalise params
        params: Dict[str, Any] = {}
        if opt_cfg is not None:
            if isinstance(opt_cfg, dict):
                params = dict(opt_cfg)
            elif hasattr(opt_cfg, "as_dict"):
                params = dict(opt_cfg.as_dict())
            else:
                params = dict(getattr(opt_cfg, "__dict__", {}))

        # Top-level toggles / defaults
        bw = int(params.get("beam_width", params.get("beam.width", 0)) or 0)
        params.setdefault("use_beam", (bw > 0))
        params.setdefault("beam_width", bw if bw > 0 else 16)  # if enabled but unspecified, use 16
        params.setdefault("ga.pop_size", params.get("pop_size", 64))
        params.setdefault("ga.generations", params.get("generations", 150))
        params.setdefault("sa.iters", params.get("iters", 1500))
        if kwargs.get("stop_score") is not None:
            params.setdefault("stop_score", kwargs["stop_score"])

        rng = kwargs.get("rng")
        if rng is None:
            raise TypeError("HybridSolver requires rng=np.random.Generator from the engine")

        super().__init__(
            problem,
            optimizer_name=SolverName.HYBRID,
            params=params,
            rng=rng,
            seed_keys=kwargs.get("seed_keys"),
            stop_score=kwargs.get("stop_score"),
            verbose=bool(kwargs.get("verbose", True)),
            log_interval=int(kwargs.get("log_interval", 50)),
        )
        self._phase: str = "beam" if bool(self.get_param("use_beam", True)) else "ga"

    # Provide phase tag in progress
    def extra_progress_fields(self) -> Dict[str, Any]:
        return {"phase": self._phase}

    # --------- phase helpers ---------

    def _run_beam(self) -> Optional[Tuple[np.ndarray, float, np.ndarray]]:
        """Return (best_key, best_score, beam_matrix[W,K]) or None if skipped."""
        if not bool(self.get_param("use_beam", True)):
            return None
        self._phase = "beam"

        # Build child params for Beam (prefixed or flat keys)
        b_params = {}
        for k, v in (self.params or {}).items():
            if k.startswith("beam.") or k.startswith("expand.") or k in {
                "beam_width", "rounds",
            }:
                b_params[k] = v
        for key in ("plateau_rounds", "plateau_min_delta"):
            if key in self.params and key not in b_params:
                b_params[key] = self.params[key]

        self._inherit_progress_knobs(b_params)

        beam_rng = _child_rng(self.rng, tag=1)
        beam = BeamSolver(
            self.problem,
            opt_cfg=b_params,
            rng=beam_rng,
            seed_keys=self.seed_keys,
            stop_score=self.get_param("stop_score", None),
            verbose=self.verbose,
            log_interval=self.log_interval,
        )
        sol = beam.solve()

        best_key = np.asarray(sol.key, dtype=KEY_DTYPE).reshape(-1)
        best_score = float(sol.score)

        # Try to pull final beam keys for GA seeding (if provided by BeamSolver meta)
        beam_mat = None
        try:
            meta = getattr(sol, "meta", {}) or {}
            beam_meta = meta.get("beam", {})
            fbk = beam_meta.get("final_keys", None)
            if fbk is not None:
                arr = np.asarray(fbk, dtype=KEY_DTYPE, copy=False)
                if arr.ndim == 2 and arr.shape[1] == self.K:
                    beam_mat = arr
        except Exception:
            beam_mat = None

        return best_key, best_score, beam_mat

    def _run_ga(self, seed_keys: Optional[np.ndarray]) -> Tuple[np.ndarray, float]:
        """Run GA; return (best_key, best_score)."""
        self._phase = "ga"
        g_params = {}
        for k, v in (self.params or {}).items():
            if k.startswith("ga."):
                g_params[k[3:]] = v
        ga_block = self.params.get("ga")
        if isinstance(ga_block, dict):
            g_params.update(ga_block)
        for alias in ("pop_size", "generations", "tournament_k", "elite_frac", "cx_frac", "mut_prob"):
            if alias in self.params and alias not in g_params:
                g_params[alias] = self.params[alias]
        for key in ("plateau_rounds", "plateau_min_delta"):
            if key in self.params and key not in g_params:
                g_params[key] = self.params[key]
        self._inherit_progress_knobs(g_params)

        ga_rng = _child_rng(self.rng, tag=2)
        ga = GASolver(
            self.problem,
            opt_cfg=g_params,
            rng=ga_rng,
            seed_keys=seed_keys if seed_keys is not None and len(seed_keys) > 0 else self.seed_keys,
            stop_score=self.get_param("stop_score", None),
            verbose=self.verbose,
            log_interval=self.log_interval,
        )
        sol = ga.solve()
        return np.asarray(sol.key, dtype=KEY_DTYPE).reshape(-1), float(sol.score)

    def _run_sa(self, start_key: np.ndarray) -> Tuple[np.ndarray, float]:
        """Run SA from a given starting key; return (best_key, best_score)."""
        self._phase = "sa"
        s_params = {}
        for k, v in (self.params or {}).items():
            if k.startswith("sa."):
                s_params[k[3:]] = v
        sa_block = self.params.get("sa")
        if isinstance(sa_block, dict):
            s_params.update(sa_block)
        for alias in ("iters", "T0", "Tmin", "cool", "local_improve_on_accept"):
            if alias in self.params and alias not in s_params:
                s_params[alias] = self.params[alias]
        for key in ("plateau_rounds", "plateau_min_delta"):
            if key in self.params and key not in s_params:
                s_params[key] = self.params[key]
        self._inherit_progress_knobs(s_params)

        sa_rng = _child_rng(self.rng, tag=3)
        sa = SASolver(
            self.problem,
            opt_cfg=s_params,
            rng=sa_rng,
            seed_keys=start_key.reshape(1, -1),  # deterministic start
            stop_score=self.get_param("stop_score", None),
            verbose=self.verbose,
            log_interval=self.log_interval,
        )
        sol = sa.solve()
        return np.asarray(sol.key, dtype=KEY_DTYPE).reshape(-1), float(sol.score)

    # --------- main solve ---------

    def solve(self):
        self._capture_seed_quality()
        fast = self._maybe_return_test_key_fastpath(SolverName.HYBRID)
        if fast is not None:
            return fast

        span = self._start_span()
        try:
            best_key = None
            best_score = float("-inf")
            from_phase = None

            beam_result = self._run_beam()
            seed_for_ga: Optional[np.ndarray] = None

            if beam_result is not None:
                b_key, b_score, beam_mat = beam_result
                best_key, best_score, from_phase = b_key.copy(), float(b_score), "beam"

                # Seed GA with beam keys (if available)
                if beam_mat is not None and beam_mat.ndim == 2 and beam_mat.shape[1] == self.K:
                    seed_for_ga = beam_mat.copy()
                else:
                    seed_for_ga = b_key.reshape(1, -1)

                # Early terminate if we’ve hit stop_score
                if self._early_stop_stop_score(best_score):
                    self._end_span(span, best_score=float(best_score), reason=self._stop_reason)
                    return self._finalize_solution(best_key, float(best_score))

            # GA phase
            g_key, g_score = self._run_ga(seed_for_ga)
            if g_score > best_score:
                best_key, best_score, from_phase = g_key.copy(), float(g_score), "ga"

            if self._early_stop_stop_score(best_score):
                self._end_span(span, best_score=float(best_score), reason=self._stop_reason)
                return self._finalize_solution(best_key, float(best_score))

            # SA phase (refine)
            s_key, s_score = self._run_sa(best_key)
            if s_score > best_score:
                best_key, best_score, from_phase = s_key.copy(), float(s_score), "sa"

            # End of hybrid: all configured phases completed without an earlier stop.
            self._stop_reason = "configured_work_limit_reached"
            self._end_span(span, best_score=float(best_score), reason=self._stop_reason)
            sol = self._finalize_solution(best_key, float(best_score))
            try:
                if not hasattr(sol, "meta") or sol.meta is None:
                    sol.meta = {}
                sol.meta["from_phase"] = from_phase or ("ga" if not bool(self.get_param("use_beam", True)) else "beam")
            except Exception:
                pass
            return sol

        except Exception as e:
            self._end_span(span, error=str(e))
            raise

    def _inherit_progress_knobs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Propagate console/preview knobs into sub-solvers."""
        if not isinstance(payload, dict):
            return payload
        for key in ("progress_pct", "print_progress", "progress_preview_chars", "verbose_console"):
            if key in self.params and key not in payload:
                payload[key] = self.params[key]
        return payload
