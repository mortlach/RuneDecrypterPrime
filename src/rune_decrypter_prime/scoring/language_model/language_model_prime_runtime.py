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
  - dir: "ltr" or "rtl"
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

from rune_decrypter_prime.core.types import Stat
from rune_decrypter_prime.scoring.stat_transform import apply_stat_transform
from .language_model_prime import LanguageModelPrime
from .paths import load_index, expand_pattern, default_lm_root  # (used by ECDFCache)

_LM_RUNTIME_CACHE: dict[tuple, "LmPrimeRuntime"] = {}

# ──────────────────────────────────────────────────────────────────────────────
# ECDF loader/cache
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Bucket:
    """Selector for a specific ECDF bucket (mode/pos/model/n/win)."""
    d: str          # "ltr" | "rtl"
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
        self._printed_files: set[Path] = set()

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
        if fp not in self._printed_files:
            try:
                rel = fp.relative_to(self.root)
            except Exception:
                rel = fp
            print(f"[LM ECDF] Loading {rel}")
            self._printed_files.add(fp)
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

    def percentiles_multi(self, b: Bucket, arrays: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Compute percentiles for specific stats provided in arrays.

        Example: arrays={"zsum": zsum_a, "madsum": madsum_a, "logp": logp_a}
        Only those stats are computed; each uses one cached grid/q and a single interp.
        """
        out: Dict[str, np.ndarray] = {}
        for stat, x in arrays.items():
            grid, qq = self.load(model=b.model, mode=b.d, pos=b.se, n=b.n, stat=stat)
            out[stat] = self.interp_percentile(grid, qq, x)
        return out

    @staticmethod
    def energy(p: np.ndarray, eps: float = 1e-9) -> np.ndarray:
        """Convert percentile (likelihood) to a positive surprisal-like score."""
        p = np.asarray(p, dtype=np.float32)
        lo = np.nextafter(np.float32(0.0), np.float32(1.0))
        hi = np.nextafter(np.float32(1.0), np.float32(0.0))
        if eps is not None:
            lo = np.maximum(lo, np.float32(eps))
            hi = np.minimum(hi, np.float32(1.0 - float(eps)))
        p = np.clip(p, lo, hi).astype(np.float32, copy=False)
        return (-np.log1p(-p)).astype(np.float32, copy=False)


# ──────────────────────────────────────────────────────────────────────────────
# Runtime scorer
# ──────────────────────────────────────────────────────────────────────────────

def _norm_dir(d: str) -> str:
    d = str(d).lower()
    if d in ("ltr", "forward"):
        return "ltr"
    if d in ("rtl", "reverse"):
        return "rtl"
    raise ValueError("dir must be 'ltr' or 'rtl'")


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
        # Coverage cache: key = (L, n, wise:bool, N)
        self._coverage_cache: Dict[Tuple[int, int, bool, int], Tuple[np.ndarray, np.ndarray]] = {}

    @classmethod
    def get_cached(
        cls,
        root: Optional[Path] = None,
        *,
        smoothing: str = "auto_gt",
        alpha: float = 0.5,
        oov_policy: str = "floor_min_seen",
        include_char: bool = True,
    ) -> "LmPrimeRuntime":
        """
        Return a shared LmPrimeRuntime instance for the given configuration.

        This avoids reloading LM tables/ECDF files across repeated runs within
        the same process (e.g., window scans).
        """
        root_path = (root or default_lm_root()).resolve()
        smoothing = "auto_gt" if smoothing is None else smoothing
        oov_policy = "floor_min_seen" if oov_policy is None else oov_policy
        key = (str(root_path), str(smoothing), float(alpha), str(oov_policy), bool(include_char))
        cached = _LM_RUNTIME_CACHE.get(key)
        if cached is None:
            cached = cls(
                root=root_path,
                smoothing=smoothing,
                alpha=float(alpha),
                oov_policy=oov_policy,
                include_char=include_char,
            )
            _LM_RUNTIME_CACHE[key] = cached
        return cached

    # ─── internals ───

    @staticmethod
    def _check_fixed_length(pt_windows, name: str):
        """Accepts list-of-lists or a 2D ndarray; validates equal window length.

        For ndarray inputs, simply checks shape is (N, L) with N>0 and L>0.
        For sequences, verifies each row has the same length as the first.
        """
        try:
            import numpy as _np  # local import to avoid circulars during type checking
            if isinstance(pt_windows, _np.ndarray):
                if pt_windows.ndim != 2 or pt_windows.shape[0] <= 0 or pt_windows.shape[1] <= 0:
                    raise ValueError(f"{name}: ndarray must be 2D (N,L) with N>0, L>0; got {pt_windows.shape}")
                return
        except Exception:
            pass

        if not pt_windows:
            raise ValueError(f"{name}: empty windows")
        L0 = len(pt_windows[0])
        for i, w in enumerate(pt_windows):
            if len(w) != L0:
                raise ValueError(
                    f"{name}: windows must be equal length; window 0 has {L0}, window {i} has {len(w)}"
                )

    @staticmethod
    def _total_eval_from_L(L: int, n: int) -> int:
        # number of n-grams in a length-L sentence
        return max(0, L - int(n) + 1)

    def _coverage_arrays_cached(self, L: int, n: int, wise: bool, N: int) -> Tuple[np.ndarray, np.ndarray]:
        key = (int(L), int(n), bool(wise), int(N))
        hit = self._coverage_cache.get(key)
        if hit is not None:
            return hit
        total = L - int(n) + 1
        if total <= 0:
            raise ValueError("window too short for given n")
        total_arr = np.full((N,), total, dtype=np.int32)
        interior = total - 2 if wise else total
        interior_arr = np.full((N,), interior, dtype=np.int32)
        self._coverage_cache[key] = (interior_arr, total_arr)
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

        # Normalise to contiguous arrays with fast paths for ndarray inputs
        if isinstance(pt_windows, np.ndarray):
            if pt_windows.ndim != 2:
                raise ValueError("pt_windows ndarray must be 2D (N,L)")
            pt = pt_windows.astype(np.uint8, copy=False, order='C')
        else:
            pt_rows = [np.asarray(w, dtype=np.uint8) for w in pt_windows]
            try:
                L = int(pt_rows[0].shape[0])
            except Exception:
                raise ValueError("pt_windows must be sequences of equal length")
            pt = np.ascontiguousarray(np.vstack(pt_rows))       # (N, L)

        # L from pt shape
        L = int(pt.shape[1])

        if isinstance(wli_windows, np.ndarray):
            # Accept either (N,L,2) or a single (L,2) window source and derive sliding windows
            if wli_windows.ndim >= 3 and wli_windows.shape[-1] == 2:
                if int(wli_windows.shape[-2]) != L:
                    raise ValueError(f"wli_windows length {wli_windows.shape[-2]} != pt length {L}")
                # Flatten any leading dims into N
                N = int(pt.shape[0])
                wli_flat = wli_windows.reshape(-1, L, 2)
                if int(wli_flat.shape[0]) != N:
                    # If mismatch, prefer a clear error rather than silent broadcast
                    raise ValueError(f"wli_windows N {wli_flat.shape[0]} != pt windows N {N}")
                wli = wli_flat.astype(np.uint8, copy=False, order='C')
            elif wli_windows.ndim == 2 and wli_windows.shape[1] == 2:
                # Build (N,L,2) by sliding a single (full) WLI over axis 0
                N = int(pt.shape[0])
                try:
                    from numpy.lib.stride_tricks import sliding_window_view as _swv  # type: ignore
                    wli_sw = _swv(wli_windows.astype(np.uint8, copy=False), window_shape=L, axis=0)
                    # wli_sw shape: (L-L+1, L, 2) == (1, L, 2) if N==1, else (N,L,2)
                    if int(wli_sw.shape[0]) != N:
                        raise ValueError(f"derived wli_windows N {wli_sw.shape[0]} != pt windows N {N}")
                    wli = wli_sw.astype(np.uint8, copy=False, order='C')
                except Exception:
                    # Fallback: explicit build
                    starts = range(0, 1 + (L - L)) if L > 0 else range(0)
                    wli_list = [wli_windows[s:s+L, :].astype(np.uint8, copy=False) for s in starts]
                    if len(wli_list) != N:
                        raise ValueError("wli_windows could not be derived to match pt windows")
                    wli = np.ascontiguousarray(np.stack(wli_list, 0), dtype=np.uint8)
            else:
                # As a last resort, if sizes match exactly, reshape to (N,L,2)
                N = int(pt.shape[0])
                expected = N * L * 2
                if int(wli_windows.size) == expected:
                    wli = wli_windows.astype(np.uint8, copy=False).reshape(N, L, 2)
                else:
                    raise ValueError("wli_windows ndarray must have last dim=2 (…, L, 2)")
        else:
            # Validate and stack WLI pairs: each sentence must be (L, 2)
            wli_rows = []
            for i, pairs in enumerate(wli_windows):
                a = np.asarray(pairs, dtype=np.uint8)
                if a.ndim != 2 or a.shape[1] != 2:
                    raise ValueError(f"wli_windows[{i}] must have shape (L,2); got {a.shape}")
                if a.shape[0] != L:
                    raise ValueError(f"wli_windows[{i}] length {a.shape[0]} != pt length {L}")
                wli_rows.append(a)
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

        logp_avg = logp_sum * inv
        zsum_avg = zsum_sum * inv
        madsum_avg = madsum_sum * inv
        logp_avg = apply_stat_transform(Stat.LOGP, logp_avg)
        zsum_avg = apply_stat_transform(Stat.ZSUM, zsum_avg)
        madsum_avg = apply_stat_transform(Stat.MADSUM, madsum_avg)
        return logp_avg, zsum_avg, madsum_avg

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
        if isinstance(pt_windows, np.ndarray):
            pt = pt_windows.astype(np.uint8, copy=False, order="C")
        else:
            pt = np.asarray(pt_windows, dtype=np.uint8, order="C")  # (N, L)

        logp_sum   = np.asarray(mdl.batch_logp_char(  pt, int(n)), dtype=np.float32)
        zsum_sum   = np.asarray(mdl.batch_zsum_char(  pt, int(n)), dtype=np.float32)
        madsum_sum = np.asarray(mdl.batch_madsum_char(pt, int(n)), dtype=np.float32)

        L = pt.shape[1]
        total = float(self._total_eval_from_L(L, n))
        if total <= 0:
            raise ValueError("window too short for given n")
        inv = np.float32(1.0 / total)

        logp_avg = logp_sum * inv
        zsum_avg = zsum_sum * inv
        madsum_avg = madsum_sum * inv
        logp_avg = apply_stat_transform(Stat.LOGP, logp_avg)
        zsum_avg = apply_stat_transform(Stat.ZSUM, zsum_avg)
        madsum_avg = apply_stat_transform(Stat.MADSUM, madsum_avg)
        return logp_avg, zsum_avg, madsum_avg

    # ─── public API (4 calls) ───

    def score_wli_wise(
        self,
        dir_: str,
        n: int,
        win: int,
        pt_windows: List[List[int]],
        wli_windows: List[List[List[int]]],
        *,
        include_energy: bool = True,
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """WLI × WISE. Windows must include [29] ... [30]."""
        logp_a, zsum_a, madsum_a = self._score_batch_wli(dir_, "wise", n, pt_windows, wli_windows)
        b = Bucket(_norm_dir(dir_), "wise", "wli", int(n), int(win))
        pct = self.ecdf.percentiles_multi(b, {"zsum": zsum_a, "madsum": madsum_a, "logp": logp_a})
        if include_energy:
            energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        else:
            energy = {k: np.zeros_like(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays_cached(len(pt_windows[0]), n, True, len(pt_windows))
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
        *,
        include_energy: bool = True,
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """WLI × NOSE. No 29/30 in the windows."""
        logp_a, zsum_a, madsum_a = self._score_batch_wli(dir_, "nose", n, pt_windows, wli_windows)
        b = Bucket(_norm_dir(dir_), "nose", "wli", int(n), int(win))
        pct = self.ecdf.percentiles_multi(b, {"zsum": zsum_a, "madsum": madsum_a, "logp": logp_a})
        if include_energy:
            energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        else:
            energy = {k: np.zeros_like(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays_cached(len(pt_windows[0]), n, False, len(pt_windows))
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
        *,
        include_energy: bool = True,
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """CHAR × WISE. Windows must include [29] ... [30]."""
        logp_a, zsum_a, madsum_a = self._score_batch_char(dir_, "wise", n, pt_windows)
        b = Bucket(_norm_dir(dir_), "wise", "char", int(n), int(win))
        pct = self.ecdf.percentiles_multi(b, {"zsum": zsum_a, "madsum": madsum_a, "logp": logp_a})
        if include_energy:
            energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        else:
            energy = {k: np.zeros_like(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays_cached(len(pt_windows[0]), n, True, len(pt_windows))
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
        *,
        include_energy: bool = True,
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """CHAR × NOSE. No 29/30 in the windows."""
        logp_a, zsum_a, madsum_a = self._score_batch_char(dir_, "nose", n, pt_windows)
        b = Bucket(_norm_dir(dir_), "nose", "char", int(n), int(win))
        pct = self.ecdf.percentiles_multi(b, {"zsum": zsum_a, "madsum": madsum_a, "logp": logp_a})
        if include_energy:
            energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        else:
            energy = {k: np.zeros_like(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays_cached(len(pt_windows[0]), n, False, len(pt_windows))
        return {
            "avg": {"logp": logp_a, "zsum": zsum_a, "madsum": madsum_a},
            "pct": pct,
            "energy": energy,
            "coverage": {"interior": interior, "total_eval": total},
        }

# TODO(test): Add a small regression test that ECDF percentiles clamp strictly to [0,1].
