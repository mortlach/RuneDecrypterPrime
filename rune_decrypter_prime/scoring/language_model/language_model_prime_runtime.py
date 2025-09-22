# ============================================================
# rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py
# Thin orchestrator combining joint-table scoring (LanguageModelPrime)
# with ECDF normalisation to produce avg/percentile/energy metrics per window.
# ============================================================

"""
Public API (vectorised over fixed-length windows):
    - score_wli_wise(dir, n, win, pt_windows, wli_windows)
    - score_wli_nose(dir, n, win, pt_windows, wli_windows)
    - score_char_wise(dir, n, win, pt_windows)
    - score_char_nose(dir, n, win, pt_windows)

Conventions:
  - dir: "fwd" or "rev"
  - n:   1..4 (ngram order)
  - win: window length used in ECDF selection (matches files built with win=10)
  - pt_windows: List[List[int]]; fixed-length windows of rune IDs
  - wli_windows: List[List[List[int]]] shape (N, L, 2); only for WLI scoring
    * WISE windows include boundary tags [29] ... [30] → interior = total_eval - 2
    * NOSE windows include no tags                      → interior = total_eval

Return shape for each scorer:
{
  'avg':     { 'logp': float32[N], 'zsum': float32[N], 'madsum': float32[N] },
  'pct':     { 'logp': float32[N], 'zsum': float32[N], 'madsum': float32[N] },
  'energy':  { 'logp': float32[N], 'zsum': float32[N], 'madsum': float32[N] },
  'coverage': { 'total_eval': int32[N], 'interior': int32[N] }
}
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np

from .language_model_prime import LanguageModelPrime
from .paths import load_index, expand_pattern, default_lm_root  # (used by ECDFCache)


# ──────────────────────────────────────────────────────────────────────────────
# ECDF loader/cache
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Bucket:
    """Selector for a specific ECDF bucket (mode/pos/model/n/win)."""
    d: str          # "fwd" | "rev"
    se: str         # "wise" | "nose"
    model: str      # "wli" | "char"
    n: int          # 1..4
    win: int        # window length (e.g., 10)


class ECDFCache:
    """
    Caches ECDF lookup arrays per (mode,pos,model,n,stat).
    Expects each NPZ to provide arrays: 'grid' and 'q' (float32), monotone in grid.
    """
    def __init__(self, root: Optional[Path] = None):
        self.root: Path = (root or default_lm_root()).resolve()
        self.idx = load_index(self.root)
        self._cache: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}

    def _ecdf_path(self, *, model: str, mode: str, pos: str, n: int, stat: str) -> Path:
        model_cfg = self.idx.models[model]
        pattern: str = model_cfg["ecdf_pattern"]
        return expand_pattern(self.root, pattern, mode=mode, pos=pos, n=n, stat=stat)

    def load(self, *, model: str, mode: str, pos: str, n: int, stat: str) -> tuple[np.ndarray, np.ndarray]:
        key = (mode, pos, model, int(n), stat)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        fp = self._ecdf_path(model=model, mode=mode, pos=pos, n=n, stat=stat)
        if not fp.exists():
            raise FileNotFoundError(f"ECDF file not found: {fp}")
        arr = np.load(fp, allow_pickle=False)
        grid = np.asarray(arr["grid"], dtype=np.float32)
        q = np.asarray(arr["q"], dtype=np.float32)
        self._cache[key] = (grid, q)
        return (grid, q)

    @staticmethod
    def interp_percentile(grid: np.ndarray, q: np.ndarray, x: np.ndarray) -> np.ndarray:
        """Piecewise-linear ECDF mapping; clamped to [0, 1]."""
        out = np.interp(x, grid, q, left=0.0, right=1.0)
        return out.astype(np.float32, copy=False)

    def percentiles(self, b: Bucket, x: np.ndarray) -> Dict[str, np.ndarray]:
        """Compute percentiles for all three stats using the same bucket selector."""
        out: Dict[str, np.ndarray] = {}
        for stat in ("zsum", "madsum", "logp"):
            grid, qq = self.load(model=b.model, mode=b.d, pos=b.se, n=b.n, stat=stat)
            out[stat] = self.interp_percentile(grid, qq, x)
        return out

    @staticmethod
    def energy(p: np.ndarray, eps: float = 1e-9) -> np.ndarray:
        """Convert percentile (likelihood) to a positive surprisal-like score."""
        p = np.clip(p, 0.0, 1.0).astype(np.float32, copy=False)
        return (-np.log1p(-p + eps)).astype(np.float32, copy=False)


# ──────────────────────────────────────────────────────────────────────────────
# Runtime scorer
# ──────────────────────────────────────────────────────────────────────────────

def _norm_dir(d: str) -> str:
    d = str(d).lower()
    if d in ("fwd", "forward"):
        return "fwd"
    if d in ("rev", "reverse"):
        return "rev"
    raise ValueError("dir must be 'fwd' or 'rev'")


class LmPrimeRuntime:
    """
    Thin orchestrator around LanguageModelPrime + ECDFCache.

    Create ONE instance and reuse it across scorers/optimisers to leverage caching.
    """
    def __init__(
        self,
        root: Optional[Path] = None,
        *,
        smoothing: str = "auto_gt",
        alpha: float = 0.5,
        oov_policy: str = "floor_min_seen",
        include_char: bool = True,
    ):
        # Discover language model root and index once
        self.root: Path = (root or default_lm_root()).resolve()
        self.idx = load_index(self.root)

        # Language model backend (joint bin loader + fast scorer)
        self.lm = LanguageModelPrime(
            lm_root=root,
            smoothing=smoothing,
            alpha=float(alpha),
            oov_policy=oov_policy,
            include_char=include_char,
        )

        # ECDF normalisation cache (reads NPZ based on index.json patterns)
        self.ecdf = ECDFCache(self.root)

    # ─── internals ───

    @staticmethod
    def _check_fixed_length(pt_windows: List[List[int]], name: str):
        if not pt_windows:
            raise ValueError(f"{name}: empty windows")
        L0 = len(pt_windows[0])
        for i, w in enumerate(pt_windows):
            if len(w) != L0:
                raise ValueError(
                    f"{name}: windows must be equal length; "
                    f"window 0 has {L0}, window {i} has {len(w)}"
                )

    @staticmethod
    def _total_eval_from_L(L: int, n: int) -> int:
        # number of n-grams in a length-L sentence
        return max(0, L - int(n) + 1)

    @staticmethod
    def _coverage_arrays(pt_windows: List[List[int]], n: int, wise: bool) -> Tuple[np.ndarray, np.ndarray]:
        L = len(pt_windows[0])
        total = L - int(n) + 1
        if total <= 0:
            raise ValueError("window too short for given n")
        total_arr = np.full((len(pt_windows),), total, dtype=np.int32)
        interior = total - 2 if wise else total
        interior_arr = np.full((len(pt_windows),), interior, dtype=np.int32)
        return interior_arr, total_arr

    # ─── core batch scorers that return averages (/total_eval) ───

    def _score_batch_wli(
        self,
        dir_: str,
        se: str,
        n: int,
        pt_windows: List[List[int]],
        wli_windows: List[List[List[int]]],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        d = _norm_dir(dir_)
        self._check_fixed_length(pt_windows, "pt_windows")

        if len(pt_windows) != len(wli_windows):
            raise ValueError("pt_windows and wli_windows must have the same length")

        # Normalise to contiguous arrays
        pt_rows = [np.asarray(w, dtype=np.uint8) for w in pt_windows]
        try:
            L = int(pt_rows[0].shape[0])
        except Exception:
            raise ValueError("pt_windows must be sequences of equal length")

        # Validate and stack WLI pairs: each sentence must be (L, 2)
        wli_rows = []
        for i, pairs in enumerate(wli_windows):
            a = np.asarray(pairs, dtype=np.uint8)
            if a.ndim != 2 or a.shape[1] != 2:
                raise ValueError(f"wli_windows[{i}] must have shape (L,2); got {a.shape}")
            if a.shape[0] != L:
                raise ValueError(f"wli_windows[{i}] length {a.shape[0]} != pt length {L}")
            wli_rows.append(a)

        pt = np.ascontiguousarray(np.vstack(pt_rows))       # (N, L)
        wli = np.ascontiguousarray(np.stack(wli_rows, 0))   # (N, L, 2)

        mdl = self.lm._ensure(d, se, "wli", int(n))

        # Raw sums from the native scorer
        logp_sum  = np.asarray(mdl.batch_logp(   pt, wli, int(n), 0), dtype=np.float32)
        zsum_sum  = np.asarray(mdl.batch_zsum(   pt, wli, int(n), 0), dtype=np.float32)
        madsum_sum= np.asarray(mdl.batch_madsum( pt, wli, int(n), 0), dtype=np.float32)

        # Normalise by total evals per sentence: (L - n + 1)
        total = float(self._total_eval_from_L(L, n))
        if total <= 0:
            raise ValueError("window too short for given n")
        inv = np.float32(1.0 / total)

        return logp_sum * inv, zsum_sum * inv, madsum_sum * inv

    def _score_batch_char(
        self,
        dir_: str,
        se: str,
        n: int,
        pt_windows: List[List[int]],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        d = _norm_dir(dir_)
        self._check_fixed_length(pt_windows, "pt_windows")

        mdl = self.lm._ensure(d, se, "char", int(n))
        pt = np.asarray(pt_windows, dtype=np.uint8, order="C")  # (N, L)

        logp_sum   = np.asarray(mdl.batch_logp_char(  pt, int(n)), dtype=np.float32)
        zsum_sum   = np.asarray(mdl.batch_zsum_char(  pt, int(n)), dtype=np.float32)
        madsum_sum = np.asarray(mdl.batch_madsum_char(pt, int(n)), dtype=np.float32)

        L = pt.shape[1]
        total = float(self._total_eval_from_L(L, n))
        if total <= 0:
            raise ValueError("window too short for given n")
        inv = np.float32(1.0 / total)

        return logp_sum * inv, zsum_sum * inv, madsum_sum * inv

    # ─── public API (4 calls) ───

    def score_wli_wise(
        self,
        dir_: str,
        n: int,
        win: int,
        pt_windows: List[List[int]],
        wli_windows: List[List[List[int]]],
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """WLI × WISE. Windows must include [29] ... [30]."""
        logp_a, zsum_a, madsum_a = self._score_batch_wli(dir_, "wise", n, pt_windows, wli_windows)
        b = Bucket(_norm_dir(dir_), "wise", "wli", int(n), int(win))
        pct = self.ecdf.percentiles(b, zsum_a)
        pct = {
            "zsum":   pct["zsum"],
            "madsum": self.ecdf.percentiles(b, madsum_a)["madsum"],
            "logp":   self.ecdf.percentiles(b, logp_a)["logp"],
        }
        energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays(pt_windows, n, wise=True)
        return {
            "avg": {"logp": logp_a, "zsum": zsum_a, "madsum": madsum_a},
            "pct": pct,
            "energy": energy,
            "coverage": {"interior": interior, "total_eval": total},
        }

    def score_wli_nose(
        self,
        dir_: str,
        n: int,
        win: int,
        pt_windows: List[List[int]],
        wli_windows: List[List[List[int]]],
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """WLI × NOSE. No 29/30 in the windows."""
        logp_a, zsum_a, madsum_a = self._score_batch_wli(dir_, "nose", n, pt_windows, wli_windows)
        b = Bucket(_norm_dir(dir_), "nose", "wli", int(n), int(win))
        pct = self.ecdf.percentiles(b, zsum_a)
        pct = {
            "zsum":   pct["zsum"],
            "madsum": self.ecdf.percentiles(b, madsum_a)["madsum"],
            "logp":   self.ecdf.percentiles(b, logp_a)["logp"],
        }
        energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays(pt_windows, n, wise=False)
        return {
            "avg": {"logp": logp_a, "zsum": zsum_a, "madsum": madsum_a},
            "pct": pct,
            "energy": energy,
            "coverage": {"interior": interior, "total_eval": total},
        }

    def score_char_wise(
        self,
        dir_: str,
        n: int,
        win: int,
        pt_windows: List[List[int]],
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """CHAR × WISE. Windows must include [29] ... [30]."""
        logp_a, zsum_a, madsum_a = self._score_batch_char(dir_, "wise", n, pt_windows)
        b = Bucket(_norm_dir(dir_), "wise", "char", int(n), int(win))
        pct = self.ecdf.percentiles(b, zsum_a)
        pct = {
            "zsum":   pct["zsum"],
            "madsum": self.ecdf.percentiles(b, madsum_a)["madsum"],
            "logp":   self.ecdf.percentiles(b, logp_a)["logp"],
        }
        energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays(pt_windows, n, wise=True)
        return {
            "avg": {"logp": logp_a, "zsum": zsum_a, "madsum": madsum_a},
            "pct": pct,
            "energy": energy,
            "coverage": {"interior": interior, "total_eval": total},
        }

    def score_char_nose(
        self,
        dir_: str,
        n: int,
        win: int,
        pt_windows: List[List[int]],
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """CHAR × NOSE. No 29/30 in the windows."""
        logp_a, zsum_a, madsum_a = self._score_batch_char(dir_, "nose", n, pt_windows)
        b = Bucket(_norm_dir(dir_), "nose", "char", int(n), int(win))
        pct = self.ecdf.percentiles(b, zsum_a)
        pct = {
            "zsum":   pct["zsum"],
            "madsum": self.ecdf.percentiles(b, madsum_a)["madsum"],
            "logp":   self.ecdf.percentiles(b, logp_a)["logp"],
        }
        energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays(pt_windows, n, wise=False)
        return {
            "avg": {"logp": logp_a, "zsum": zsum_a, "madsum": madsum_a},
            "pct": pct,
            "energy": energy,
            "coverage": {"interior": interior, "total_eval": total},
        }

# TODO(test): Add a small regression test that ECDF percentiles clamp strictly to [0,1].
