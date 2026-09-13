# ============================================================
# rdp/core/config/run.py
# Unified dataclasses for cipher/scorer/solver/run configs.
# ============================================================

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

from rdp.core.config.logging_config import LoggingConfig
from rdp.core.config.scoring import ScoringConfig
from rdp.core.config.cipher import CipherConfig
from rdp.core.config.solver import SolverConfig
from rdp.core.types import (
    SolverName,
    ScorerName,
    ensure_solver_name,
    ensure_scorer_name,
)

_DEFAULT_RUN_SEED = 12345

@dataclass
class RunConfig:
    cipher: CipherConfig | Dict[str, Any]
    scorer_name: ScorerName | str
    scorer_params: Dict[str, Any] | ScoringConfig
    solver: SolverConfig | Dict[str, Any]
    enable_telemetry: bool = True
    optimizer_name: Optional[SolverName | str] = None
    optimizer_params: Optional[Dict[str, Any]] = None
    logging: LoggingConfig | None = None
    seed: Optional[int] = _DEFAULT_RUN_SEED

    def __post_init__(self) -> None:
        if isinstance(self.cipher, dict):
            self.cipher = CipherConfig(**self.cipher)
        if isinstance(self.scorer_params, dict):
            self.scorer_params = ScoringConfig(**self.scorer_params)
        if isinstance(self.solver, dict):
            self.solver = SolverConfig(**self.solver)

        if not isinstance(self.cipher, CipherConfig):
            raise TypeError(f"cipher must be CipherConfig, got {type(self.cipher)}")
        if not isinstance(self.scorer_params, ScoringConfig):
            raise TypeError(f"scorer_params must be ScoringConfig, got {type(self.scorer_params)}")
        if not isinstance(self.solver, SolverConfig):
            raise TypeError(f"solver must be SolverConfig, got {type(self.solver)}")

        self.scorer_name = ensure_scorer_name(self.scorer_name)

        if self.optimizer_name is not None:
            self.optimizer_name = ensure_solver_name(self.optimizer_name)

        if self.optimizer_params is not None and not isinstance(self.optimizer_params, dict):
            self.optimizer_params = dict(self.optimizer_params)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RunConfig":
        d = d.copy()
        cipher_cfg = d.get("cipher")
        if cipher_cfg is not None and not isinstance(cipher_cfg, CipherConfig):
            d["cipher"] = CipherConfig(**cipher_cfg)
        sp = d.get("scorer_params", {})
        if isinstance(sp, dict) and not isinstance(sp, ScoringConfig):
            d["scorer_params"] = ScoringConfig(**sp)
        if "solver" in d and d["solver"] is not None:
            opt_dict = d["solver"]
            if isinstance(opt_dict, dict):
                d["solver"] = SolverConfig(**opt_dict)
            elif not isinstance(opt_dict, SolverConfig):
                d["solver"] = SolverConfig(**dict(vars(opt_dict)))
        else:
            name = d.pop("optimizer_name", None)
            params = d.pop("optimizer_params", {}) or {}
            if not isinstance(params, dict):
                params = dict(vars(params))
            d["solver"] = SolverConfig(name=name or SolverName.BEAM, **params)
        if "enable_telemetry" not in d:
            d["enable_telemetry"] = True
        return cls(**d)

    def asdict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["cipher"] = self.cipher.asdict() if hasattr(self.cipher, "asdict") else asdict(self.cipher)
        out["scorer_params"] = (
            self.scorer_params.asdict() if isinstance(self.scorer_params, ScoringConfig) else self.scorer_params
        )
        out["solver"] = self.solver.asdict() if hasattr(self.solver, "asdict") else asdict(self.solver)
        if isinstance(out.get("scorer_name"), ScorerName):
            out["scorer_name"] = out["scorer_name"].value
        if isinstance(out.get("optimizer_name"), SolverName):
            out["optimizer_name"] = out["optimizer_name"].value
        out["optimizer_name"] = None
        out["optimizer_params"] = None
        return out


