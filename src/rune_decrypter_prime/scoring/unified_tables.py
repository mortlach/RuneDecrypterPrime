# ============================================================
# rune_decrypter_prime/scoring/unified_tables.py   (Model registry & table shapes)
# Shared lookup for model kinds, n-gram orders, and table shape contracts.
# ============================================================
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Literal, Dict, Any
import numpy as np

# Public kind tag used across scorers
Kind = Literal["wli", "char"]

@dataclass(frozen=True)
class JointNgramTable:
    """
    Hash table backing for joint n-gram lookups.

    keys: uint64 open-addressing keys (0 denotes empty)
    logp: float32 log-probabilities parallel to keys
    mask: 2^k - 1 mask for linear probing
    stats: robust stats used by downstream scorers
           {"mu","sigma","median","mad_sigma","fallback_logp"}
    """
    keys: np.ndarray        # dtype=uint64, C-contig
    logp: np.ndarray        # dtype=float32, C-contig
    mask: int               # 2^k - 1
    stats: Dict[str, float] # {"mu","sigma","median","mad_sigma","fallback_logp"}

class TablesProvider(Protocol):
    """Stable contract consumed by both NumPy and Torch scorers."""
    def get_joint_table(self, kind: Kind, n: int) -> JointNgramTable: ...

class RuntimeTablesProvider:
    """
    Bridge ScoringConfig/CipherConfig -> joint n-gram tables (keys/logp/mask/stats).

    Implementation details:
      • Uses LanguageModelPrime's index/patterns to resolve joint-bin paths
      • Loads C-contiguous NumPy arrays via _load_bin(...)
      • Computes robust stats needed by GPU scorer (z-norm + fallback)
      • Returns CPU NumPy arrays; Torch scorer moves them to device on load
    """

    def __init__(self, cfg_cipher, cfg_scorer_params):
        self.cfg_cipher = cfg_cipher
        self.cfg_scorer_params = cfg_scorer_params
        self._lm = None  # lazy LanguageModelPrime

    # ---------- internals ----------

    def _ensure_lm(self) -> None:
        if self._lm is not None:
            return
        # Late import to avoid cycles
        from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
        s = self.cfg_scorer_params
        self._lm = LanguageModelPrime(
            smoothing=getattr(s, "smoothing", "auto_gt"),
            alpha=float(getattr(s, "alpha", 0.5)),
            oov_policy=getattr(s, "oov_policy", "floor_min_seen"),
            include_char=bool(getattr(s, "include_char", True)),
        )

    @staticmethod
    def _stats_from_logp(logp: np.ndarray) -> Dict[str, float]:
        # Robust summary statistics used by Torch scorer
        # (MAD scaled to sigma; fallback is a conservative floor)
        mu = float(np.mean(logp, dtype=np.float64))
        sigma = float(np.std(logp.astype(np.float64), ddof=0))
        med = float(np.median(logp))
        mad = float(np.median(np.abs(logp - med))) * 1.4826  # MAD→sigma
        fallback = float(np.min(logp))
        return {
            "mu": mu,
            "sigma": sigma,
            "median": med,
            "mad_sigma": mad,
            "fallback_logp": fallback,
        }

    # ---------- public ----------

    def get_joint_table(self, kind: Kind, n: int) -> JointNgramTable:
        """
        kind: "wli" | "char"
        n:    1..4
        Returns:
            JointNgramTable(keys:uint64[N], logp:float32[N], mask:int, stats:dict)
        """
        self._ensure_lm()

        # Helpers for path normalisation + bin loading
        from rune_decrypter_prime.scoring.language_model.language_model_prime import (
            _load_bin,
            _norm_dir,
            _norm_se,
            _norm_model,
        )
        # Pull canonical fields and convert Enums to their .value strings
        dir_raw = (
                getattr(self.cfg_cipher, "encoding_dir", None)
                or getattr(self.cfg_cipher, "text_encoding_direction", None)
                or getattr(self.cfg_cipher, "text_transposition", None)
                or "ltr"
        )
        if hasattr(dir_raw, "value"):  # Direction Enum -> "ltr"/"rtl"
            dir_raw = dir_raw.value

        se_raw = getattr(self.cfg_scorer_params, "se_mode", "nose")
        if hasattr(se_raw, "value"):  # SeMode Enum -> "nose"/"wise"
            se_raw = se_raw.value

        d = _norm_dir(dir_raw)
        se = _norm_se(se_raw)
        model = _norm_model(kind)

        model = _norm_model(kind)

        # Resolve file and load raw arrays
        path = self._lm._joint_path(d, se, model, int(n))
        keys, logp, _cnts, mask = _load_bin(path)

        # Normalise dtype/layout and compute stats
        keys = np.asarray(keys, dtype=np.uint64, order="C")
        logp = np.asarray(logp, dtype=np.float32, order="C")
        stats = self._stats_from_logp(logp)

        return JointNgramTable(keys=keys, logp=logp, mask=int(mask), stats=stats)
