# ============================================================
# rune_decrypter_prime/core/solver_engine.py
# Compatibility shim that forwards callers to the Stage-2 engine.
# ============================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

from rune_decrypter_prime.core.config.run import RunConfig
from rune_decrypter_prime.core.config.solution import Solution
from rune_decrypter_prime.core.config.solver import SolverConfig
from rune_decrypter_prime.core.engine import EngineConfig, solve as engine_solve
from rune_decrypter_prime.core.problem import ProblemInstance, ProblemSpec
from rune_decrypter_prime.core.types import (
    Direction,
    SolverName,
    ensure_direction,
    KEY_DTYPE,
)
from rdp.api.pipeline_helpers import finalize_solution

from rune_decrypter_prime.solvers.beam import BeamSolver
from rune_decrypter_prime.solvers.ga import GASolver
from rune_decrypter_prime.solvers.sa import SASolver
from rune_decrypter_prime.solvers.hybrid import HybridSolver
from rune_decrypter_prime.solvers.kaeding_periodic_structured import (
    KaedingPeriodicStructuredSolver,
)


_SOLVER_TABLE: Dict[SolverName, Any] = {
    SolverName.BEAM: BeamSolver,
    SolverName.GA: GASolver,
    SolverName.SA: SASolver,
    SolverName.HYBRID: HybridSolver,
    SolverName.KAEDING: KaedingPeriodicStructuredSolver,
}


class _LegacyOptimizerAdapter:
    """Adapter that preserves the old .search() API surface."""

    def __init__(self, solver: Any):
        self._solver = solver

    def search(self) -> Solution:
        return self._solver.solve()

    def solve(self) -> Solution:
        return self._solver.solve()


def _solver_kind_from_cfg(cfg: SolverConfig) -> SolverName:
    if not isinstance(cfg, SolverConfig):
        raise TypeError(f"optimizer_cfg must be SolverConfig, got {type(cfg).__name__}")
    return cfg.kind


def build_optimizer(problem, optimizer_cfg: SolverConfig, *, rng=None):
    """
    Legacy helper used by tests and tutorials. Returns an object that exposes
    .search() but internally delegates to the new solver classes.

    Core callers must pass a canonical SolverConfig. User-facing dicts are
    normalised before this boundary.
    """
    kind = _solver_kind_from_cfg(optimizer_cfg)
    params = dict(optimizer_cfg.params)

    verbose = bool(params.pop("verbose", True))
    log_interval = int(params.pop("log_interval", 50))
    seed_keys = params.get("seed_keys") or params.get("initial_keys")
    stop_score = params.get("stop_score")

    if rng is None:
        raise TypeError(
            "build_optimizer requires rng (np.random.Generator) for determinism"
        )

    solver_cls = _SOLVER_TABLE[kind]
    solver = solver_cls(
        problem,
        opt_cfg=params,
        rng=rng,
        seed_keys=seed_keys,
        stop_score=stop_score,
        verbose=verbose,
        log_interval=log_interval,
    )
    return _LegacyOptimizerAdapter(solver)


@dataclass
class _Materialised:
    instance: ProblemInstance
    direction: Direction


class RuneSolverEngine:
    """
    Minimal compatibility wrapper around the Stage-2 engine.
    Accepts a RunConfig and exposes solve() like the legacy engine.
    """

    def __init__(self, cfg: RunConfig):
        self.cfg = cfg
        self._telemetry_on = bool(cfg.enable_telemetry)
        materialised = self._materialise_problem(cfg)
        self.instance = materialised.instance
        self.direction = materialised.direction
        self.problem = self.instance.problem
        self.cipher = self.problem.cipher
        self.scorer = self.problem.scorer

    def _materialise_problem(self, cfg: RunConfig) -> _Materialised:
        direction = ensure_direction(cfg.cipher.encoding_dir)
        spec = ProblemSpec(
            text="",
            text_encoding_direction=direction,
            cipher_cfg=cfg.cipher,
            scorer_params=cfg.scorer_params,
            input_permutation=cfg.cipher.initial_text_permutation_indices,
        )
        instance = ProblemInstance.materialise(spec)
        return _Materialised(instance=instance, direction=direction)

    def _seed_keys(self) -> Optional[np.ndarray]:
        keys = self.cfg.cipher.initial_keys
        if keys is None:
            return None
        arr = np.asarray(keys, dtype=KEY_DTYPE)
        if arr.size == 0:
            return None
        return arr

    def solve(self) -> Solution:
        solver_cfg = self.cfg.solver
        params = dict(solver_cfg.params)
        verbose = bool(params.get("verbose", True))
        log_interval = int(params.get("log_interval", 50))
        stop_score = params.get("stop_score")

        eng_cfg = EngineConfig(
            solver=solver_cfg.kind,
            params=params,
            seed=self.cfg.seed,
            stop_score=stop_score,
            verbose=verbose,
            log_interval=log_interval,
            seed_keys=self._seed_keys(),
        )

        solution = engine_solve(self.instance, eng_cfg)
        finalize_solution(
            self.problem,
            solution,
            ciphertext=np.asarray(self.cfg.cipher.ciphertext),
            wli=self.cfg.cipher.wli_data,
            cipher=self.cfg.cipher,
            encoding_dir=self.direction,
            cfg=self.cfg,
            telemetry_on=self._telemetry_on,
            pipeline_block=self.instance.pipeline_block,
        )
        return solution
