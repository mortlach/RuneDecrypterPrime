# ============================================================
# rune_decrypter_prime/core/rune_solver.py   (Config-first wrapper)
# A thin, friendly façade around the engine: normalises configs,
# builds cipher/scorer/optimizer, and returns a Solution.
# ============================================================
from __future__ import annotations
from typing import Any, Dict, Optional, Union

import numpy as np

from rune_decrypter_prime.core.config import Solution
from rune_decrypter_prime.io.run_logger import RunLogger
from rune_decrypter_prime.core.problem import DecryptionProblem
from rune_decrypter_prime.core.logging_config import LoggingConfig
from rune_decrypter_prime.core.config import (
    CipherConfig,
    ScoringConfig,
    OptimizerConfig,
    RunConfig,
)
from rune_decrypter_prime.core.solver_engine import (
    CIPHERS,
    SCORERS,
    OPTIMIZERS,           # registries (kept for parity with engine)
    build_cipher,
    build_scorer,
    build_optimizer,
)


class RuneSolver:
    """
    Config-first convenience wrapper.

    • Accepts a full RunConfig (preferred) or individual parts.
    • Builds cipher → scorer → problem → optimizer using the same builders as the engine.
    • Returns a `Solution` from optimizer.search().

    Notes
    -----
    - Cipher pipeline enforces interrupters/transpositions from cfg.cipher.
    - Optimizers are cipher-agnostic and interact via `DecryptionProblem`.
    - KeyOps are provided by the cipher (for GA/SA/etc).
    """

    def __init__(
        self,
        solver_cfg: Optional[RunConfig] = None,
        *,
        cipher: Optional[CipherConfig] = None,
        scorer_name: str = "rune",
        scorer_params: Optional[Union[ScoringConfig, Dict[str, Any]]] = None,
        optimizer: Optional[Union[OptimizerConfig, Dict[str, Any]]] = None,
        verbose: bool = False,
    ) -> None:
        # ---------- Normalise to a RunConfig ----------
        if solver_cfg is None:
            if cipher is None:
                raise ValueError("Either `solver_cfg` or `cipher` must be provided.")

            # scorer_params can be a ScoringConfig or a dict
            if isinstance(scorer_params, ScoringConfig):
                s_cfg = scorer_params
            else:
                s_cfg = ScoringConfig(**(scorer_params or {}))

            # optimizer can be an OptimizerConfig or a dict
            if isinstance(optimizer, OptimizerConfig):
                o_cfg = optimizer
            else:
                # allow dicts like {"name": "beam", ...}
                o_cfg = OptimizerConfig.from_dict(optimizer or {"name": "beam"})

            solver_cfg = RunConfig(
                cipher=cipher,
                scorer_name=scorer_name,
                scorer_params=s_cfg,
                optimizer=o_cfg,
            )

        self.cfg = solver_cfg
        self.verbose = verbose

        # ---------- Build components (same path as engine) ----------
        self.cipher = build_cipher(self.cfg.cipher)
        self.scorer = build_scorer(self.cfg.cipher, self.cfg.scorer_params)
        self.problem = DecryptionProblem(cipher=self.cipher, scorer=self.scorer, c_cfg=self.cfg)

        # Optional logger (quiet by default under pytest)
        log_cfg = getattr(self.cfg, "logging", None)
        if not isinstance(log_cfg, LoggingConfig):
            # Verbose logging, but avoid stdout spam unless explicitly requested
            log_cfg = LoggingConfig(verbose=True, print_progress=False, write_jsonl=True)

        echo = bool(getattr(log_cfg, "print_progress", False)) and not bool(
            __import__("os").getenv("PYTEST_CURRENT_TEST")
        )

        self._logger = RunLogger(
            out_dir=getattr(log_cfg, "out_dir", None),
            echo=echo,
        ) if bool(getattr(log_cfg, "verbose", True)) else None

        if self._logger:
            dev_str = getattr(self.cfg.cipher, "device", None) or "numpy"
            self._logger.log({
                "type": "run_start",
                "cipher": getattr(self.cfg.cipher, "name", "unknown"),
                "optimizer": getattr(getattr(self.cfg, "optimizer", None), "name", None),
                "device": dev_str,
            })

        # Optimizer (accept OptimizerConfig or dict)
        self.optimizer = build_optimizer(self.problem, self.cfg.optimizer)

        # Optional hooks for structure search (future-ready)
        intr_exact = getattr(self.cfg.cipher, "interruptors_exact", None)
        intr_legacy = getattr(self.cfg.cipher, "interruptors", None)
        fixed_interrupt_idx = intr_exact if intr_exact is not None else intr_legacy

        if hasattr(self.optimizer, "set_interrupt_idx"):
            self.optimizer.set_interrupt_idx(
                np.asarray(fixed_interrupt_idx, dtype=np.intp) if fixed_interrupt_idx is not None else None
            )

        pool = getattr(self.cfg.cipher, "interruptors_pool", None)
        imax = getattr(self.cfg.cipher, "interruptors_max", None)
        if hasattr(self.optimizer, "set_interrupt_search_space"):
            self.optimizer.set_interrupt_search_space(
                pool=np.asarray(pool, dtype=np.intp) if pool is not None else None,
                max_count=int(imax) if imax is not None else None,
            )

        t_modes = getattr(self.cfg.cipher, "transposition_search_modes", None)
        if hasattr(self.optimizer, "set_transposition_modes"):
            self.optimizer.set_transposition_modes(t_modes)

    # ---------- Convenience constructors ----------
    @classmethod
    def from_parts(
        cls,
        *,
        cipher: CipherConfig,
        scorer_name: str = "rune",
        scorer_params: Optional[Union[ScoringConfig, Dict[str, Any]]] = None,
        optimizer: Optional[Union[OptimizerConfig, Dict[str, Any]]] = None,
        verbose: bool = False,
    ) -> "RuneSolver":
        return cls(
            solver_cfg=None,
            cipher=cipher,
            scorer_name=scorer_name,
            scorer_params=scorer_params,
            optimizer=optimizer,
            verbose=verbose,
        )

    # ---------- Solve ----------
    def solve(self) -> Solution:
        """
        Run the optimizer and return a `Solution`.

        Returns
        -------
        Solution
            Solution(key: list[int] | nested, plaintext: str, score: float, meta: dict)
        """
        return self.optimizer.search()


# ------------------------------------------------------------
# TODO (non-blocking, follow-up PRs):
# - Consider harmonising logger defaults with solver_engine (progress printing).
# - Interruptor/transposition hand-offs are duplicated with engine; unify later.
# ------------------------------------------------------------
