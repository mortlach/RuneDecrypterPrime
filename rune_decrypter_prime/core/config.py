# ============================================================
# rune_decrypter_prime/core/config.py
# Unified dataclasses for cipher/scorer/optimizer/run configs.
# ============================================================

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Literal

from rune_decrypter_prime.core.logging_config import LoggingConfig
from rune_decrypter_prime.data.cipher_tests.baseline_registry import BASELINE

__all__ = [
    "LoggingConfig",
    "CipherConfig",
    "ScoringConfig",
    "OptimizerConfig",
    "RunConfig",
    "Solution",
]

# ---------------- CipherConfig ------------------------------------------------
@dataclass
class CipherConfig:
    """Cipher-specific configuration (ciphertext, WLI, keys, device, etc.)."""
    ciphertext: Sequence[int]
    wli_data: Sequence[Sequence[int]]
    key_length: Optional[int]
    plaintext_english26: Optional[str] = None
    plaintext: Optional[Sequence[int]] = None
    text_transposition: str = "fwd"
    key_transposition: str = "fwd"
    device: Optional[str] = "cpu"  # TODO: rename to compute_device
    interruptors: Optional[List[int]] = None
    initial_keys: Optional[List[Sequence[int]]] = None
    test_key: Optional[Sequence[int]] = None
    interruptors_exact: Optional[List[int]] = None
    interruptors_pool: Optional[List[int]] = None
    interruptors_max: Optional[int] = None
    transposition_search_modes: Optional[List[str]] = None
    name: str = "vigenere"

# ---------------- ScoringConfig ----------------------------------------------
@dataclass
class ScoringConfig:
    """Configuration for the Language Model scorer (LMPrime)."""
    model_root: Path = None
    smoothing: str = "auto_gt"
    alpha: float = 0.5
    oov_policy: str = "floor_min_seen"
    include_char: bool = True
    use_word_breaks: bool = True
    n_char: int = 3
    n_wli: int  = 3
    win: int = 10
    se_mode: Literal["nose", "wise"] = "nose"
    objective: str = "pct.logp.win10"
    weights: Tuple[float, float] = (0.25, 0.75)   # (w_char, w_wli)
    maximize: bool = True
    encoding_dir: Literal["fwd", "rev", "auto"] = "fwd"
    char_weights: Dict[int, float] = field(default_factory=lambda: {2: 0.5})
    wli_weights: Dict[int, float] = field(default_factory=lambda: {2: 0.5})
    impl: Literal["auto", "numpy", "torch"] = "auto"  # TODO: rename to scorer_backend
    dtype: Literal["float32", "float64"] = "float32"

class OptimizerConfig:
    """
    Backward/forward compatible optimizer config.
    Canonical: OptimizerConfig(name="beam", params={...})
    Legacy:    OptimizerConfig(name="beam", beam_width=1, ...)
    """
    def __init__(self, name: str = "beam", params: dict | None = None, **legacy_kwargs):
        self.name = str(name)
        self.params = dict(params) if params is not None else {}
        for k, v in legacy_kwargs.items():
            self.params[k] = v

    def __repr__(self) -> str:
        return f"OptimizerConfig(name={self.name!r}, params={self.params!r})"

    @classmethod
    def from_dict(cls, d: dict | None):
        if d is None:
            return cls()
        d = dict(d)
        name = d.pop("name", "beam")
        p = d.pop("params", None)
        if p is None:
            return cls(name=name, **d)
        params = dict(p); params.update(d)
        return cls(name=name, params=params)

# ---------------- SolverConfig ------------------------------------------------
@dataclass
class RunConfig:
    cipher: CipherConfig
    scorer_name: str
    scorer_params: Dict[str, Any] | ScoringConfig
    optimizer: OptimizerConfig
    enable_telemetry: bool = True
    optimizer_name: Optional[str] = None
    optimizer_params: Optional[Dict[str, Any]] = None
    logging: LoggingConfig | None = None
    seed: Optional[int] = BASELINE["seed"]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RunConfig":
        d = d.copy()
        d["cipher"] = CipherConfig(**d["cipher"])
        sp = d.get("scorer_params", {})
        if isinstance(sp, dict) and not isinstance(sp, ScoringConfig):
            d["scorer_params"] = ScoringConfig(**sp)
        if "optimizer" in d and d["optimizer"] is not None:
            opt_dict = d["optimizer"]
            if isinstance(opt_dict, dict):
                d["optimizer"] = OptimizerConfig(**opt_dict)
            elif not isinstance(opt_dict, OptimizerConfig):
                d["optimizer"] = OptimizerConfig(**dict(vars(opt_dict)))
        else:
            name = d.pop("optimizer_name", None)
            params = d.pop("optimizer_params", {}) or {}
            if not isinstance(params, dict):
                params = dict(vars(params))
            d["optimizer"] = OptimizerConfig(name=name or "beam", **params)
        if "enable_telemetry" not in d:
            d["enable_telemetry"] = True
        return cls(**d)

    def asdict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["cipher"] = asdict(self.cipher)
        out["scorer_params"] = (
            asdict(self.scorer_params) if isinstance(self.scorer_params, ScoringConfig) else self.scorer_params
        )
        out["optimizer"] = asdict(self.optimizer)
        out["optimizer_name"] = None
        out["optimizer_params"] = None
        return out

# ---------------- Solution  ----------------------
@dataclass(slots=True)
class Solution:
    """Container for a solver’s best output."""
    key: Any
    plaintext: Any
    score: float
    meta: Dict[str, Any] = field(default_factory=dict)
    plaintext_str: str = ""
    plaintext_idx: Any = field(default_factory=list)

# TODO: prune unused GAParams/SAParams scaffolds if not required by tests.
