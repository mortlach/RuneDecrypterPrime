# ============================================================
# rune_decrypter_prime/core/config.py
# Unified dataclasses for cipher/scorer/solver/run configs.
# ============================================================

from __future__ import annotations

# rune_decrypter_prime/core/config.py
"""
Temporary shim for v1: config split into core/config/*.py.
This file re-exports public names for backward compatibility.
"""
from warnings import warn as _warn
from .config import (
    CipherConfig,
    ScoringConfig,
    SolverConfig,
    RunConfig,
    Solution,
)

__all__ = [
    "CipherConfig",
    "ScoringConfig",
    "SolverConfig",
    "RunConfig",
    "Solution",
]

_warn(
    "rune_decrypter_prime.core.config is split into submodules under core/config/. "
    "Importing from core.config remains supported for v1 but will be deprecated.",
    DeprecationWarning,
    stacklevel=2,
)
#
#     def __post_init__(self) -> None:
#         if self.encoding_dir is not None:
#             self.encoding_dir = ensure_direction(self.encoding_dir)
#         if self.impl is not None:
#             self.impl = ensure_scorer_impl(self.impl)
#         if self.se_mode is not None:
#             self.se_mode = ensure_se_mode(self.se_mode)
#
#         obj = getattr(self, "objective", None)
#         if isinstance(obj, dict):
#             fam = ensure_objective_family(obj.get("family", ObjectiveFamily.PCT))
#             stat_val = obj.get("stat")
#             stat = ensure_stat(stat_val) if stat_val is not None else None
#             win = obj.get("win")
#             self.objective = ObjectiveSpec(family=fam, stat=stat, win=win)
#         elif isinstance(obj, ObjectiveSpec):
#             fam = ensure_objective_family(obj.family)
#             stat = ensure_stat(obj.stat) if obj.stat is not None else None
#             self.objective = ObjectiveSpec(family=fam, stat=stat, win=obj.win)
#
#         self.char_weights = self._normalise_channel_weights(self.char_weights, 'char_weights')
#         self.wli_weights = self._normalise_channel_weights(self.wli_weights, 'wli_weights')
#
#     def asdict(self) -> Dict[str, Any]:
#         out = asdict(self)
#         out["model_root"] = self.model_root
#         out["smoothing"] = self.smoothing
#         out["alpha"] = self.alpha
#         out["oov_policy"] = self.oov_policy
#         out["include_char"] = self.include_char
#         out["use_word_breaks"] = self.use_word_breaks
#         out["n_char"] = self.n_char
#         out["n_wli"] = self.n_wli
#         out["win"] = self.win
#         out["se_mode"] = self.se_mode
#         out["objective"] = self.objective
#         #     {
#         #     "family": self.objective.family.value if isinstance(self.objective.family, ObjectiveFamily) else self.objective.family,
#         #     "stat": (self.objective.stat.value if isinstance(self.objective.stat, Stat) else self.objective.stat),
#         #     "win": self.objective.win,
#         # }
#         # out["weights"] = self.weights
#         out["maximize"] = self.maximize
#         out["encoding_dir"] = self.encoding_dir
#         out["char_weights"] = self.char_weights
#         out["wli_weights"] = self.wli_weights
#         out["impl"] = self.impl.value if isinstance(self.impl, ScorerImpl) else self.impl
#         out["dtype"] = self.dtype
#         return out
#
#
#
#     @staticmethod
#     def _normalise_channel_weights(weights: Any, field_name: str) -> Dict[int, float]:
#         if weights in (None, {}):
#             return {}
#         if isinstance(weights, dict):
#             iterable = weights.items()
#         elif isinstance(weights, (list, tuple)):
#             iterable = weights
#         else:
#             raise TypeError(f"{field_name} must be a dict or list of (n, weight) pairs as documented")
#
#         normalised: Dict[int, float] = {}
#         for item in iterable:
#             if isinstance(item, dict):
#                 if len(item) != 1:
#                     raise ValueError(f"{field_name} dict entries must contain a single (n, weight) mapping")
#                 ((key, value),) = item.items()
#             elif isinstance(item, (list, tuple)) and len(item) == 2:
#                 key, value = item
#             else:
#                 raise TypeError(f"{field_name} entries must be (n, weight) pairs")
#
#             try:
#                 n_val = int(key)
#             except Exception as exc:
#                 raise TypeError(f"{field_name} keys must be integers (n-gram length)") from exc
#             if n_val <= 0:
#                 raise ValueError(f"{field_name} keys must be positive integers per scoring docs")
#
#             try:
#                 weight_val = float(value)
#             except Exception as exc:
#                 raise TypeError(f"{field_name} values must be numeric weights") from exc
#             if not math.isfinite(weight_val):
#                 raise ValueError(f"{field_name} weights must be finite numbers")
#
#             normalised[n_val] = weight_val
#
#         return normalised
#
# class SolverConfig:
#     """
#     Backward/forward compatible solver config.
#     Canonical: SolverConfig(name=OptimizerKind.BEAM, params={...})
#     Legacy:    SolverConfig(name="beam", params={...})
#     """
#     def __init__(self, name: SolverName | str = SolverName.BEAM, params: dict | None = None, **legacy_kwargs):
#         self.kind: SolverName = parse_optimizer_kind(name)
#         self.params = dict(params) if params is not None else {}
#         for k, v in legacy_kwargs.items():
#             self.params[k] = v
#
#     # preserve old .name for callers; returns canonical string
#     @property
#     def name(self) -> str:
#         return self.kind.value
#
#     def __repr__(self) -> str:
#         return f"SolverConfig(name={self.kind!s}, params={self.params!r})"
#
#     def asdict(self) -> Dict[str, Any]:
#         return {
#             "name": self.kind.value,
#             "params": dict(self.params),
#         }
#
#     @classmethod
#     def from_dict(cls, d: dict | None):
#         if d is None:
#             return cls()
#         d = dict(d)
#         name = d.pop("name", SolverName.BEAM)
#         p = d.pop("params", None)
#         if p is None:
#             return cls(name=name, **d)
#         params = dict(p); params.update(d)
#         return cls(name=name, params=params)
#
# # class SolverConfig:
# #     """
# #     Backward/forward compatible solver config.
# #     Canonical: SolverConfig(name="beam", params={...})
# #     Legacy:    SolverConfig(name="beam", beam_width=1, ...)
# #     """
# #     def __init__(self, name: str = "beam", params: dict | None = None, **legacy_kwargs):
# #         self.name = str(name)
# #         self.params = dict(params) if params is not None else {}
# #         for k, v in legacy_kwargs.items():
# #             self.params[k] = v
# #
# #     def __repr__(self) -> str:
# #         return f"SolverConfig(name={self.name!r}, params={self.params!r})"
# #
# #     @classmethod
# #     def from_dict(cls, d: dict | None):
# #         if d is None:
# #             return cls()
# #         d = dict(d)
# #         name = d.pop("name", "beam")
# #         p = d.pop("params", None)
# #         if p is None:
# #             return cls(name=name, **d)
# #         params = dict(p); params.update(d)
# #         return cls(name=name, params=params)
#
# # ---------------- SolverConfig ------------------------------------------------
# @dataclass
# class RunConfig:
#     cipher: CipherConfig | Dict[str, Any]
#     scorer_name: ScorerName | str
#     scorer_params: Dict[str, Any] | ScoringConfig
#     solver: SolverConfig | Dict[str, Any]
#     enable_telemetry: bool = True
#     optimizer_name: Optional[SolverName | str] = None
#     optimizer_params: Optional[Dict[str, Any]] = None
#     logging: LoggingConfig | None = None
#     seed: Optional[int] = BASELINE["seed"]
#
#     def __post_init__(self) -> None:
#         if isinstance(self.cipher, dict):
#             self.cipher = CipherConfig(**self.cipher)
#         if isinstance(self.scorer_params, dict):
#             self.scorer_params = ScoringConfig(**self.scorer_params)
#         if isinstance(self.solver, dict):
#             self.solver = SolverConfig(**self.solver)
#
#         if not isinstance(self.cipher, CipherConfig):
#             raise TypeError(f"cipher must be CipherConfig, got {type(self.cipher)}")
#         if not isinstance(self.scorer_params, ScoringConfig):
#             raise TypeError(f"scorer_params must be ScoringConfig, got {type(self.scorer_params)}")
#         if not isinstance(self.solver, SolverConfig):
#             raise TypeError(f"solver must be SolverConfig, got {type(self.solver)}")
#
#         self.scorer_name = ensure_scorer_name(self.scorer_name)
#
#         if self.optimizer_name is not None:
#             self.optimizer_name = ensure_solver_name(self.optimizer_name)
#
#         if self.optimizer_params is not None and not isinstance(self.optimizer_params, dict):
#             self.optimizer_params = dict(self.optimizer_params)
#
#     @classmethod
#     def from_dict(cls, d: Dict[str, Any]) -> "RunConfig":
#         d = d.copy()
#         cipher_cfg = d.get("cipher")
#         if cipher_cfg is not None and not isinstance(cipher_cfg, CipherConfig):
#             d["cipher"] = CipherConfig(**cipher_cfg)
#         sp = d.get("scorer_params", {})
#         if isinstance(sp, dict) and not isinstance(sp, ScoringConfig):
#             d["scorer_params"] = ScoringConfig(**sp)
#         if "solver" in d and d["solver"] is not None:
#             opt_dict = d["solver"]
#             if isinstance(opt_dict, dict):
#                 d["solver"] = SolverConfig(**opt_dict)
#             elif not isinstance(opt_dict, SolverConfig):
#                 d["solver"] = SolverConfig(**dict(vars(opt_dict)))
#         else:
#             name = d.pop("optimizer_name", None)
#             params = d.pop("optimizer_params", {}) or {}
#             if not isinstance(params, dict):
#                 params = dict(vars(params))
#             d["solver"] = SolverConfig(name=name or SolverName.BEAM, **params)
#         if "enable_telemetry" not in d:
#             d["enable_telemetry"] = True
#         return cls(**d)
#
#     def asdict(self) -> Dict[str, Any]:
#         out = asdict(self)
#         out["cipher"] = self.cipher.asdict() if hasattr(self.cipher, "asdict") else asdict(self.cipher)
#         out["scorer_params"] = (
#             asdict(self.scorer_params) if isinstance(self.scorer_params, ScoringConfig) else self.scorer_params
#         )
#         out["solver"] = self.solver.asdict() if hasattr(self.solver, "asdict") else asdict(self.solver)
#         if isinstance(out.get("scorer_name"), ScorerName):
#             out["scorer_name"] = out["scorer_name"].value
#         if isinstance(out.get("optimizer_name"), SolverName):
#             out["optimizer_name"] = out["optimizer_name"].value
#         out["optimizer_name"] = None
#         out["optimizer_params"] = None
#         return out
#
#
# # ---------------- Solution  ----------------------
# from dataclasses import dataclass, field
# from typing import Any, Dict, Optional, Sequence
#
#
# @dataclass(slots=True)
# class Solution:
#     """Container for a solver’s best output.
#     Required on construct: (key, plaintext, score).
#     Engine populates the convenience + context fields before returning to API.
#     """
#     # Required
#     key: Any
#     plaintext: Any
#     score: float
#
#     # Optional context / flags
#     has_wli: Optional[bool] = None
#     meta: Dict[str, Any] = field(default_factory=dict)
#
#     # Convenience (safe views for tutorials/UIs)
#     plaintext_str: str = ""                 # always a real str by the time API returns
#     plaintext_idx: List[int] = field(default_factory=list)
#     plaintext_rune: str = ""
#     plaintext_rune_nospace: str = ""
#     plaintext_latin: str = ""
#     plaintext_latin_nospace: str = ""
#     wli: Optional[Sequence[Sequence[int]]] = None
#     ciphertext_idx: List[int] = field(default_factory=list)
#     ciphertext_rune: str = ""
#     ciphertext_rune_nospace: str = ""
#     ciphertext_latin: str = ""
#     ciphertext_latin_nospace: str = ""
#     alphabet: str = "runic-29"
#     alphabet_size: int = 29
#
#     # -------- v1 standardised context (add-only, optional) --------
#     device: Device = Device.CPU             # v1 surface
#     cipher_name: str = ""
#     solver_name: Optional[SolverName] = None
#     scorer_impl: Optional[ScorerImpl] = None
#     scorer_n_char: int = 0
#     scorer_n_wli: int = 0
#     direction: Direction = Direction.LTR
#     pipeline: Dict[str, Any] = field(default_factory=lambda: {
#         "text_encoding_direction": Direction.LTR,
#         "input_permutation": {"kind": "none", "length": 0, "hash": ""},
#     })
#
#     # Optimisation sense
#     maximize: bool = True
#
#     # Progress summary
#     step: int = 0
#     evals: int = 0
#     since_improve: int = 0
#     tokens_processed: int = 0
#
#     # Timings
#     wall_time_s: float = 0.0
#     decrypt_time_s: float = 0.0
#     score_time_s: float = 0.0
#
#     # Termination & extras
#     stop_reason: Optional[str] = None       # "patience"|"time_budget"|"eval_budget"|"target"|"error"
#     extras: Dict[str, Any] = field(default_factory=dict)
#
#     def __post_init__(self) -> None:
#         # Trigger enum normalisation for constructor arguments.
#         self.device = self.device
#         self.direction = self.direction
#         if self.solver_name:
#             self.solver_name = self.solver_name
#         if self.scorer_impl:
#             self.scorer_impl = self.scorer_impl
#
#     def __setattr__(self, name: str, value: Any) -> None:
#         if name == "device" and value is not None:
#             value = ensure_device(value)
#         elif name == "direction" and value is not None:
#             value = ensure_direction(value)
#         elif name == "solver_name":
#             if not value:
#                 value = None
#             else:
#                 value = ensure_solver_name(value)
#         elif name == "scorer_impl":
#             if not value:
#                 value = None
#             else:
#                 value = ensure_scorer_impl(value)
#         object.__setattr__(self, name, value)
#
# # TODO: prune unused GAParams/SAParams scaffolds if not required by tests.
