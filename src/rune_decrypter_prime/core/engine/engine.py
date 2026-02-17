# ============================================================
# rune_decrypter_prime/core/engine/engine.py
# Minimal, typed orchestrator for Stage-2
#  - Accepts a ProblemInstance (already materialised)
#  - Instantiates the chosen Solver (Beam/GA/SA/Hybrid)
#  - Emits canonical run_start / run_end telemetry
#  - Returns a fully-populated Solution (solvers attach telemetry)
# ============================================================

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

# Core
from rune_decrypter_prime.core.problem.instance import ProblemInstance
from rune_decrypter_prime.core.types import SolverName, ensure_solver_name
from rune_decrypter_prime.core.types import ensure_device, Device

# Solvers (Stage-2 paths)
from rune_decrypter_prime.solvers.beam import BeamSolver
from rune_decrypter_prime.solvers.ga import GASolver
from rune_decrypter_prime.solvers.sa import SASolver
from rune_decrypter_prime.solvers.hybrid import HybridSolver
from rune_decrypter_prime.solvers.kaeding_periodic_structured import KaedingPeriodicStructuredSolver

# Telemetry (keep canonical helpers)
from rune_decrypter_prime.telemetry.events import (
    run_start as tel_run_start,
    run_end   as tel_run_end,
)
from rune_decrypter_prime.telemetry.schema import to_canonical_device_str


_SOLVER_TABLE: Dict[SolverName, Any] = {
    SolverName.BEAM:   BeamSolver,
    SolverName.GA:     GASolver,
    SolverName.SA:     SASolver,
    SolverName.HYBRID: HybridSolver,
    SolverName.KAEDING: KaedingPeriodicStructuredSolver,
}


_GLOBAL_EARLY_STOP_DEFAULTS: Dict[SolverName, Dict[str, Any]] = {
    SolverName.BEAM: {"plateau_rounds": 16, "plateau_min_delta": 1e-6},
    SolverName.GA: {"plateau_rounds": 24, "plateau_min_delta": 1e-6},
    SolverName.SA: {"plateau_rounds": 300, "plateau_min_delta": 1e-6},
    SolverName.HYBRID: {"plateau_rounds": 24, "plateau_min_delta": 1e-6},
    SolverName.KAEDING: {"plateau_rounds": 360, "plateau_min_delta": 1e-6},
}


def _with_early_stop_defaults(kind: SolverName, params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Apply conservative plateau defaults when callers omit them."""
    out: Dict[str, Any] = dict(params or {})
    defaults = _GLOBAL_EARLY_STOP_DEFAULTS.get(kind, {})
    for key, value in defaults.items():
        out.setdefault(key, value)
    return out


@dataclass(slots=True)
class EngineConfig:
    """Thin, typed bag for engine-level knobs (avoid dicts here)."""
    solver: SolverName
    params: Dict[str, Any] | None = None
    seed: Optional[int] = None
    stop_score: Optional[float] = None
    verbose: bool = True
    log_interval: int = 50
    # Optional seeding of the solver with candidate keys (shape [N,K], uint8)
    seed_keys: Any | None = None


def _child_rng(seed: Optional[int]) -> np.random.Generator:
    # Deterministic, NumPy-native RNG for solvers.
    # Default to seed=0 when unspecified to avoid entropy-based drift.
    s = 0 if seed is None else int(seed)
    return np.random.default_rng(s)

def _scorer_meta(problem: Any, spec: ProblemInstance) -> Dict[str, str]:
    impl = None
    dtype = None
    device = None

    scorer = getattr(problem, "scorer", None)
    if scorer is not None:
        try:
            tele = scorer.telemetry() if callable(getattr(scorer, "telemetry", None)) else getattr(scorer, "telemetry", None)
        except Exception:
            tele = None
        if isinstance(tele, dict):
            impl = tele.get("impl", impl)
            dtype = tele.get("dtype", dtype)
            device = tele.get("device", device)

        if impl in (None, "unknown") and hasattr(scorer, "impl_name"):
            try:
                impl = scorer.impl_name()
            except Exception:
                pass
        if dtype in (None, "unknown") and hasattr(scorer, "dtype_name"):
            try:
                dtype = scorer.dtype_name()
            except Exception:
                pass
        if device in (None, "unknown") and hasattr(scorer, "device_name"):
            try:
                device = scorer.device_name()
            except Exception:
                pass

        if impl is None:
            impl = getattr(scorer, "impl", None)
        if dtype is None:
            dtype = getattr(scorer, "dtype", None) or getattr(scorer, "_dtype", None)

    scorer_params = getattr(spec, "spec", None)
    scorer_params = getattr(scorer_params, "scorer_params", None)
    if (impl in (None, "unknown")) and scorer_params is not None:
        impl = scorer_params.get("impl") if isinstance(scorer_params, dict) else getattr(scorer_params, "impl", None)
    if (dtype in (None, "unknown")) and scorer_params is not None:
        dtype = scorer_params.get("dtype") if isinstance(scorer_params, dict) else getattr(scorer_params, "dtype", None)

    impl = getattr(impl, "value", impl) if impl is not None else None
    device = getattr(device, "value", device) if device is not None else None

    out = {
        "impl": str(impl or "unknown"),
        "dtype": str(dtype or "float32"),
    }
    if device not in (None, "n/a"):
        out["device"] = str(device)
    return out


def _solver_from_cfg(kind: SolverName, problem: Any, params: Dict[str, Any] | None,
                     rng: np.random.Generator, cfg: EngineConfig):
    SolverCls = _SOLVER_TABLE[kind]
    return SolverCls(
        problem,
        opt_cfg=(params or {}),
        rng=rng,
        seed_keys=cfg.seed_keys,
        stop_score=cfg.stop_score,
        verbose=cfg.verbose,
        log_interval=int(cfg.log_interval),
    )


def solve(instance: ProblemInstance, engine_cfg: EngineConfig):
    """
    Single entrypoint for Stage-2 engine.
      - instance: ProblemInstance (cipher/scorer/problem/pipeline already materialised)
      - engine_cfg: which solver + params + seed + small knobs
    """
    if not isinstance(instance, ProblemInstance):
        raise TypeError("solve() expects a ProblemInstance (use ProblemInstance.materialise(spec)).")

    kind = ensure_solver_name(engine_cfg.solver)

    effective_params = _with_early_stop_defaults(kind, engine_cfg.params)

    # --- run_start telemetry (top-level wrapper around per-solver events) ---
    # Solvers already emit their own solver_start/progress/solver_end spans.
    # The run_start/run_end here are just a light envelope for the *whole* run.
    try:
        dev_raw = getattr(getattr(instance.problem, "c_cfg", None), "device", Device.CPU)
        dev = to_canonical_device_str(ensure_device(dev_raw))
    except Exception:
        dev = "cpu"

    scorer_meta = _scorer_meta(instance.problem, instance)

    tel_run_start(
        problem=instance.problem,
        seed=engine_cfg.seed,
        solver=kind.value,
        device=dev,
        scorer=scorer_meta,
        pipeline=instance.pipeline_block,
        params=effective_params,
    )

    # --- build solver and run ---
    rng = _child_rng(engine_cfg.seed)
    solver = _solver_from_cfg(kind, instance.problem, effective_params, rng, engine_cfg)

    scorer_obj = getattr(instance.problem, "scorer", None)
    clear_cache = getattr(scorer_obj, "clear_wli_cache", None)

    try:
        solution = solver.solve()

        stop_reason = getattr(solver, "_stop_reason", None)
        result_payload = {"score": float(getattr(solution, "score", 0.0))}
        if stop_reason:
            result_payload["reason"] = stop_reason

        # --- run_end telemetry envelope ---
        tel_run_end(
            problem=instance.problem,
            seed=engine_cfg.seed,
            solver=kind.value,
            device=dev,
            scorer=scorer_meta,
            pipeline=instance.pipeline_block,
            result=result_payload,
        )
        return solution

    except Exception as e:
        # Emit a failed run_end and re-raise
        tel_run_end(
            problem=instance.problem,
            seed=engine_cfg.seed,
            solver=kind.value,
            device=dev,
            scorer=scorer_meta,
            pipeline=instance.pipeline_block,
            result={"error": str(e)},
        )
        raise
    finally:
        if callable(clear_cache):
            try:
                clear_cache()
            except Exception:
                pass
