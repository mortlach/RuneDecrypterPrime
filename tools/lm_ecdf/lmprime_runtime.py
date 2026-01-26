# lmprime_runtime.py
"""
High-level runtime wrapper for LanguageModelPrime + ECDF normalization.

You get four calls:
    - score_wli_wise(dir, n, win, pt_windows, wli_windows)
    - score_wli_nose(dir, n, win, pt_windows, wli_windows)
    - score_char_wise(dir, n, win, pt_windows)
    - score_char_nose(dir, n, win, pt_windows)

Inputs (per call):
    dir         : "fwd" or "rev"
    n           : 1..4 (ngram order)
    win         : W in "WINDOW_NGRAMS=W" used to build the windows
    pt_windows  : List[List[int]]  (each window is a sentence for _fastlm)
    wli_windows : List[List[List[int]]] ((L,2) pairs) -- required for WLI calls

Expect windows to be built like the ECDF builder:
    - WISE windows include [29] ... [30], so total_eval = (L - n + 1) = W + 2
    - NOSE windows have no tags,          total_eval = (L - n + 1) = W

Returns a dict:
{
  'avg': { 'logp': np.float32[N], 'zsum': np.float32[N], 'madsum': np.float32[N] },
  'pct': { 'logp': np.float32[N], 'zsum': np.float32[N], 'madsum': np.float32[N] },
  'energy': { 'logp': np.float32[N], 'zsum': np.float32[N], 'madsum': np.float32[N] },
  'coverage': { 'total_eval': np.int32[N], 'interior': np.int32[N] }
}

The returned 'avg' matches the ECDF canonical normalization ("divide by total_eval").
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np

from language_model_prime import LanguageModelPrime  # your wrapper on _fastlm


# ──────────────────────────────────────────────────────────────────────────────
# ECDF loader/cache
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Bucket:
    d: str
    se: str
    model: str
    n: int
    win: int

class ECDFCache:
    """
    Loads ECDF tables (grid, q) saved by your ECDF builder.
    Caches by (d,se,model,n,win,stat) and returns percentiles for vectors.
    """
    def __init__(self, ecdf_root: str | Path):
        self.root = Path(ecdf_root)
        if not self.root.exists():
            raise FileNotFoundError(f"ECDF root not found: {self.root}")
        self._cache: Dict[Tuple[str,str,str,int,int,str], Tuple[np.ndarray,np.ndarray]] = {}

    def _path(self, b: Bucket, stat: str) -> Path:
        return self.root / f"{b.d}_{b.se}_{b.model}_n{b.n}_win{b.win}_{stat}.npz"

    def load(self, b: Bucket, stat: str) -> Tuple[np.ndarray, np.ndarray]:
        key = (b.d, b.se, b.model, b.n, b.win, stat)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        fp = self._path(b, stat)
        arr = np.load(fp, allow_pickle=True)
        grid = arr["grid"].astype(np.float32, copy=False)
        q    = arr["q"].astype(np.float32, copy=False)
        self._cache[key] = (grid, q)
        return grid, q

    @staticmethod
    def interp_percentile(grid: np.ndarray, q: np.ndarray, x: np.ndarray) -> np.ndarray:
        # piecewise linear ECDF mapping
        return np.interp(x, grid, q, left=0.0, right=1.0).astype(np.float32)

    def percentiles(self, b: Bucket, x: np.ndarray) -> Dict[str,np.ndarray]:
        out = {}
        for stat in ("zsum","madsum","logp"):
            g, qq = self.load(b, stat)
            out[stat] = self.interp_percentile(g, qq, x)
        return out

    @staticmethod
    def energy(p: np.ndarray, eps: float = 1e-9) -> np.ndarray:
        p = np.clip(p, 0.0, 1.0, dtype=np.float32)
        return -np.log1p(-p + eps).astype(np.float32)


# ──────────────────────────────────────────────────────────────────────────────
# Runtime scorer
# ──────────────────────────────────────────────────────────────────────────────

def _norm_dir(d: str) -> str:
    d = str(d).lower()
    if d in ("fwd","forward"): return "fwd"
    if d in ("rev","reverse"): return "rev"
    raise ValueError("dir must be 'fwd'/'rev'")

class LmPrimeRuntime:
    """
    Thin orchestrator around LanguageModelPrime + ECDFCache.
    You typically create ONE instance and reuse it.
    """
    def __init__(self,
                 bins_dir: str | Path,
                 ecdf_dir: str | Path,
                 smoothing: str = "auto_gt",
                 alpha: float = 0.5,
                 oov_policy: str = "floor_min_seen",
                 include_char: bool = True):
        self.lm = LanguageModelPrime(
            bins_dir=bins_dir,
            smoothing=smoothing,
            alpha=float(alpha),
            oov_policy=oov_policy,
            include_char=include_char
        )
        self.ecdf = ECDFCache(ecdf_dir)

    # ─── internals ───

    @staticmethod
    def _check_fixed_length(pt_windows: List[List[int]], name: str):
        if not pt_windows:
            raise ValueError(f"{name}: empty windows")
        L = len(pt_windows[0])
        for i, w in enumerate(pt_windows):
            if len(w) != L:
                raise ValueError(f"{name}: windows must be equal length; window {i} has {len(w)} vs {L}")

    @staticmethod
    def _total_eval_from_L(L: int, n: int) -> int:
        # generic: number of n-grams in a length-L sentence is (L - n + 1)
        return max(0, L - n + 1)

    @staticmethod
    def _coverage_arrays(pt_windows: List[List[int]], n: int, wise: bool) -> Tuple[np.ndarray, np.ndarray]:
        L = len(pt_windows[0])
        total = L - n + 1
        if total <= 0:
            raise ValueError("window too short for given n")
        total_arr = np.full((len(pt_windows),), total, dtype=np.int32)
        if wise:
            interior = total - 2
        else:
            interior = total
        interior_arr = np.full((len(pt_windows),), interior, dtype=np.int32)
        return interior_arr, total_arr

    # ─── core batch scorers that return averages (/total_eval) ───

    def _score_batch_wli(self, dir_: str, se: str, n: int,
                         pt_windows: List[List[int]],
                         wli_windows: List[List[List[int]]]) -> Tuple[np.ndarray,np.ndarray,np.ndarray]:
        d = _norm_dir(dir_)
        self._check_fixed_length(pt_windows, "pt_windows")
        if len(pt_windows) != len(wli_windows):
            raise ValueError("pt_windows and wli_windows must have same length")

        # Grab the underlying fast model once
        mdl = self.lm._ensure(d, se, "wli", int(n))  # uses your cache

        # Form contiguous arrays
        N = len(pt_windows)
        L = len(pt_windows[0])
        pt = np.asarray(pt_windows, dtype=np.uint8, order="C")
        wli = np.asarray(wli_windows, dtype=np.uint8, order="C")  # (N,L,2)

        # sums
        logp_sum  = np.asarray(mdl.batch_logp(pt, wli, int(n), 0),   dtype=np.float32)
        zsum_sum  = np.asarray(mdl.batch_zsum(pt, wli, int(n), 0),   dtype=np.float32)
        madsum_sum= np.asarray(mdl.batch_madsum(pt, wli, int(n), 0), dtype=np.float32)

        total = float(self._total_eval_from_L(L, n))
        if total <= 0:
            raise ValueError("window too short for given n")
        inv = np.float32(1.0 / total)

        return logp_sum * inv, zsum_sum * inv, madsum_sum * inv

    def _score_batch_char(self, dir_: str, se: str, n: int,
                          pt_windows: List[List[int]]) -> Tuple[np.ndarray,np.ndarray,np.ndarray]:
        d = _norm_dir(dir_)
        self._check_fixed_length(pt_windows, "pt_windows")

        mdl = self.lm._ensure(d, se, "char", int(n))

        N = len(pt_windows)
        L = len(pt_windows[0])
        pt = np.asarray(pt_windows, dtype=np.uint8, order="C")

        logp_sum   = np.asarray(mdl.batch_logp_char(pt, int(n)),   dtype=np.float32)
        zsum_sum   = np.asarray(mdl.batch_zsum_char(pt, int(n)),   dtype=np.float32)
        madsum_sum = np.asarray(mdl.batch_madsum_char(pt, int(n)), dtype=np.float32)

        total = float(self._total_eval_from_L(L, n))
        if total <= 0:
            raise ValueError("window too short for given n")
        inv = np.float32(1.0 / total)

        return logp_sum * inv, zsum_sum * inv, madsum_sum * inv

    # ─── public API (4 calls) ───

    def score_wli_wise(self, dir_: str, n: int, win: int,
                       pt_windows: List[List[int]],
                       wli_windows: List[List[List[int]]]) -> Dict[str,Dict[str,np.ndarray]]:
        """WLI × WISE. Windows must include [29] ... [30]."""
        logp_a, zsum_a, madsum_a = self._score_batch_wli(dir_, "wise", n, pt_windows, wli_windows)
        b = Bucket(_norm_dir(dir_), "wise", "wli", int(n), int(win))
        pct = {
            "zsum": self.ecdf.percentiles(b, zsum_a)["zsum"],
            "madsum": self.ecdf.percentiles(b, madsum_a)["madsum"],
            "logp": self.ecdf.percentiles(b, logp_a)["logp"],
        }
        energy = { k: self.ecdf.energy(v) for k,v in pct.items() }
        interior, total = self._coverage_arrays(pt_windows, n, wise=True)
        return {
            "avg":    {"logp": logp_a, "zsum": zsum_a, "madsum": madsum_a},
            "pct":    pct,
            "energy": energy,
            "coverage": {"interior": interior, "total_eval": total}
        }

    def score_wli_nose(self, dir_: str, n: int, win: int,
                       pt_windows: List[List[int]],
                       wli_windows: List[List[List[int]]]) -> Dict[str,Dict[str,np.ndarray]]:
        """WLI × NOSE. No 29/30 in the windows."""
        logp_a, zsum_a, madsum_a = self._score_batch_wli(dir_, "nose", n, pt_windows, wli_windows)
        b = Bucket(_norm_dir(dir_), "nose", "wli", int(n), int(win))
        pct = {
            "zsum": self.ecdf.percentiles(b, zsum_a)["zsum"],
            "madsum": self.ecdf.percentiles(b, madsum_a)["madsum"],
            "logp": self.ecdf.percentiles(b, logp_a)["logp"],
        }
        energy = { k: self.ecdf.energy(v) for k,v in pct.items() }
        interior, total = self._coverage_arrays(pt_windows, n, wise=False)
        return {
            "avg":    {"logp": logp_a, "zsum": zsum_a, "madsum": madsum_a},
            "pct":    pct,
            "energy": energy,
            "coverage": {"interior": interior, "total_eval": total}
        }

    def score_char_wise(self, dir_: str, n: int, win: int,
                        pt_windows: List[List[int]]) -> Dict[str,Dict[str,np.ndarray]]:
        """CHAR × WISE. Windows must include [29] ... [30]."""
        logp_a, zsum_a, madsum_a = self._score_batch_char(dir_, "wise", n, pt_windows)
        b = Bucket(_norm_dir(dir_), "wise", "char", int(n), int(win))
        pct = {
            "zsum": self.ecdf.percentiles(b, zsum_a)["zsum"],
            "madsum": self.ecdf.percentiles(b, madsum_a)["madsum"],
            "logp": self.ecdf.percentiles(b, logp_a)["logp"],
        }
        energy = { k: self.ecdf.energy(v) for k,v in pct.items() }
        interior, total = self._coverage_arrays(pt_windows, n, wise=True)
        return {
            "avg":    {"logp": logp_a, "zsum": zsum_a, "madsum": madsum_a},
            "pct":    pct,
            "energy": energy,
            "coverage": {"interior": interior, "total_eval": total}
        }

    def score_char_nose(self, dir_: str, n: int, win: int,
                        pt_windows: List[List[int]]) -> Dict[str,Dict[str,np.ndarray]]:
        """CHAR × NOSE. No 29/30 in the windows."""
        logp_a, zsum_a, madsum_a = self._score_batch_char(dir_, "nose", n, pt_windows)
        b = Bucket(_norm_dir(dir_), "nose", "char", int(n), int(win))
        pct = {
            "zsum": self.ecdf.percentiles(b, zsum_a)["zsum"],
            "madsum": self.ecdf.percentiles(b, madsum_a)["madsum"],
            "logp": self.ecdf.percentiles(b, logp_a)["logp"],
        }
        energy = { k: self.ecdf.energy(v) for k,v in pct.items() }
        interior, total = self._coverage_arrays(pt_windows, n, wise=False)
        return {
            "avg":    {"logp": logp_a, "zsum": zsum_a, "madsum": madsum_a},
            "pct":    pct,
            "energy": energy,
            "coverage": {"interior": interior, "total_eval": total}
        }
