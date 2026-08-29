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
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np

from rune_decrypter_prime.core.types import Stat
from rune_decrypter_prime.scoring.stat_transform import apply_stat_transform
from .language_model_prime import LanguageModelPrime
from .load_status import LmLoadReporter, LmLoadStatus
from .paths import load_index, expand_pattern, default_lm_root  # (used by ECDFCache)

_LM_RUNTIME_CACHE: dict[tuple, "LmPrimeRuntime"] = {}
# Global disk-cache for ECDF assets. Key MUST include the resolved LM root;
# tests frequently use tmp_path roots with different contents but identical
# (mode,pos,model,n,stat,win) selectors.
_ECDF_GLOBAL_CACHE: dict[
    tuple, tuple[np.ndarray, np.ndarray, dict, str, tuple[float, float]]
] = {}

# ──────────────────────────────────────────────────────────────────────────────
# ECDF loader/cache
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Bucket:
    """Selector for a specific ECDF bucket (mode/pos/model/n/win)."""

    d: str  # "ltr" | "rtl"
    se: str  # "wise" | "nose"
    model: str  # "wli" | "char"
    n: int  # 1..4
    win: int  # window length (e.g., 10)


class ECDFCache:
    """
    Caches ECDF lookup arrays per (mode,pos,model,n,stat,win).
    Enforces ABI: grid/q are float64 on disk, strictly increasing, meta_json required.
    Allows explicit float32 working buffers if they remain strictly increasing.
    """

    def __init__(
        self,
        root: Optional[Path] = None,
        *,
        prefer_float32: bool = True,
        load_reporter: LmLoadReporter | None = None,
    ):
        self.root: Path = (root or default_lm_root()).resolve()
        self.idx = load_index(self.root)
        self._cache: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
        self._meta_cache: dict[tuple, dict] = {}
        self._hash_cache: dict[tuple, str] = {}
        self._interp_dtype_cache: dict[tuple, str] = {}
        self._q_range_cache: dict[tuple, tuple[float, float]] = {}
        self._load_reporter = load_reporter
        self._prefer_float32 = bool(prefer_float32)

    def _ecdf_path(
        self, *, model: str, mode: str, pos: str, n: int, stat: str, win: int
    ) -> Path:
        model_cfg = self.idx.models[model]
        pattern: str = model_cfg["ecdf_pattern"]
        return expand_pattern(
            self.root, pattern, mode=mode, pos=pos, n=n, stat=stat, win=int(win)
        )

    @staticmethod
    def _key(*, model: str, mode: str, pos: str, n: int, stat: str, win: int) -> tuple:
        return (mode, pos, model, int(n), stat, int(win))

    def asset_id(
        self, *, model: str, mode: str, pos: str, n: int, stat: str, win: int
    ) -> str:
        """Stable asset id for telemetry (relative path when possible)."""
        fp = self._ecdf_path(model=model, mode=mode, pos=pos, n=n, stat=stat, win=win)
        try:
            return str(fp.relative_to(self.root)).replace("\\", "/")
        except Exception:
            return str(fp)

    def load(
        self, *, model: str, mode: str, pos: str, n: int, stat: str, win: int
    ) -> tuple[np.ndarray, np.ndarray]:
        key = self._key(model=model, mode=mode, pos=pos, n=n, stat=stat, win=win)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        global_key = (str(self.root),) + key
        global_hit = _ECDF_GLOBAL_CACHE.get(global_key)
        if global_hit is not None:
            grid64, q64, meta, meta_hash, q_range = global_hit
            q0, q1 = q_range
            fp = self._ecdf_path(
                model=model, mode=mode, pos=pos, n=n, stat=stat, win=win
            )
            self._emit_load_status(
                kind="cache_hit",
                asset_id=self.asset_id(
                    model=model, mode=mode, pos=pos, n=n, stat=stat, win=win
                ),
                path=fp,
                status="cached",
                cached=True,
            )
        else:
            fp = self._ecdf_path(
                model=model, mode=mode, pos=pos, n=n, stat=stat, win=win
            )
            if not fp.exists():
                self._emit_load_status(
                    kind="missing_asset",
                    asset_id=self.asset_id(
                        model=model, mode=mode, pos=pos, n=n, stat=stat, win=win
                    ),
                    path=fp,
                    status="missing",
                    cached=False,
                )
                raise FileNotFoundError(f"ECDF file not found: {fp}")

            arr = np.load(fp, allow_pickle=True)
            if "grid" not in arr or "q" not in arr:
                missing = [k for k in ("grid", "q") if k not in arr]
                raise ValueError(f"ECDF missing arrays: {', '.join(missing)} in {fp}")

            grid64 = np.asarray(arr["grid"])
            q64 = np.asarray(arr["q"])
            if grid64.dtype != np.float64:
                raise ValueError(
                    f"ECDF grid dtype must be float64; got {grid64.dtype} in {fp}"
                )
            if q64.dtype != np.float64:
                raise ValueError(
                    f"ECDF q dtype must be float64; got {q64.dtype} in {fp}"
                )
            if grid64.ndim != 1 or q64.ndim != 1 or grid64.size != q64.size:
                raise ValueError(f"ECDF grid/q must be 1D and same length in {fp}")
            if grid64.size > 1 and not bool(np.all(np.diff(grid64) > 0.0)):
                raise ValueError(f"ECDF grid must be strictly increasing in {fp}")
            if q64.size > 1 and not bool(np.all(np.diff(q64) > 0.0)):
                raise ValueError(f"ECDF q must be strictly increasing in {fp}")
            q0 = float(q64[0]) if q64.size else 0.0
            q1 = float(q64[-1]) if q64.size else 0.0
            if not (0.0 <= q0 < q1 <= 1.0):
                raise ValueError(f"ECDF q range invalid in {fp}: q0={q0}, q1={q1}")

            if "meta_json" not in arr:
                raise ValueError(f"ECDF meta_json missing in {fp}")
            raw_meta = arr["meta_json"]
            meta_json = None
            try:
                if isinstance(raw_meta, np.ndarray):
                    if raw_meta.shape == ():
                        raw_meta = raw_meta.item()
                    elif raw_meta.size == 1:
                        raw_meta = raw_meta.reshape(()).item()
                if isinstance(raw_meta, bytes):
                    meta_json = raw_meta.decode("utf-8")
                elif isinstance(raw_meta, str):
                    meta_json = raw_meta
            except Exception:
                meta_json = None
            if not meta_json:
                raise ValueError(f"ECDF meta_json could not be decoded in {fp}")
            try:
                meta = json.loads(meta_json)
            except Exception as exc:
                raise ValueError(f"ECDF meta_json invalid JSON in {fp}: {exc}") from exc

            # Minimal required meta validation
            for k in ("model", "direction", "se_mode", "n", "stat", "win_ngrams"):
                if k not in meta:
                    raise ValueError(f"ECDF meta_json missing '{k}' in {fp}")
            if str(meta.get("model")) != str(model):
                raise ValueError(f"ECDF meta_json model mismatch in {fp}")
            if str(meta.get("direction")) != str(mode):
                raise ValueError(f"ECDF meta_json direction mismatch in {fp}")
            if str(meta.get("se_mode")) != str(pos):
                raise ValueError(f"ECDF meta_json se_mode mismatch in {fp}")
            if int(meta.get("n")) != int(n):
                raise ValueError(f"ECDF meta_json n mismatch in {fp}")
            if str(meta.get("stat")) != str(stat):
                raise ValueError(f"ECDF meta_json stat mismatch in {fp}")
            if int(meta.get("win_ngrams")) != int(win):
                raise ValueError(f"ECDF meta_json win_ngrams mismatch in {fp}")

            # Compute meta hash (meta_json + grid + q)
            try:
                import hashlib

                h = hashlib.sha256()
                h.update(meta_json.encode("utf-8"))
                h.update(np.ascontiguousarray(grid64, dtype=np.float64).tobytes())
                h.update(np.ascontiguousarray(q64, dtype=np.float64).tobytes())
                meta_hash = h.hexdigest()
            except Exception as exc:
                raise ValueError(
                    f"ECDF meta_hash computation failed in {fp}: {exc}"
                ) from exc
            _ECDF_GLOBAL_CACHE[global_key] = (
                grid64,
                q64,
                dict(meta),
                meta_hash,
                (q0, q1),
            )
            self._emit_load_status(
                kind="ecdf_load",
                asset_id=self.asset_id(
                    model=model, mode=mode, pos=pos, n=n, stat=stat, win=win
                ),
                path=fp,
                status="loaded",
                cached=False,
            )

        # Working buffers for interpolation
        interp_dtype = "float64"
        if self._prefer_float32:
            grid32 = grid64.astype(np.float32)
            q32 = q64.astype(np.float32)
            grid_ok = (grid32.size <= 1) or bool(np.all(np.diff(grid32) > 0.0))
            q_ok = (q32.size <= 1) or bool(np.all(np.diff(q32) > 0.0))
            if grid_ok and q_ok:
                grid = grid32
                q = q32
                interp_dtype = "float32"
            else:
                grid = grid64
                q = q64
                interp_dtype = "float64"
        else:
            grid = grid64
            q = q64
            interp_dtype = "float64"

        self._cache[key] = (grid, q)
        self._meta_cache[key] = dict(meta)
        self._hash_cache[key] = meta_hash
        self._interp_dtype_cache[key] = interp_dtype
        self._q_range_cache[key] = (q0, q1)
        return (grid, q)

    def _emit_load_status(
        self,
        *,
        kind: str,
        asset_id: str,
        path: Path,
        status: str,
        cached: bool,
    ) -> None:
        if self._load_reporter is None:
            return
        self._load_reporter(
            LmLoadStatus(
                kind=kind,  # type: ignore[arg-type]
                asset_type="ecdf",
                asset_id=asset_id,
                path=str(path),
                status=status,
                cached=bool(cached),
            )
        )

    def meta(
        self, *, model: str, mode: str, pos: str, n: int, stat: str, win: int
    ) -> dict:
        key = self._key(model=model, mode=mode, pos=pos, n=n, stat=stat, win=win)
        if key not in self._meta_cache:
            _ = self.load(model=model, mode=mode, pos=pos, n=n, stat=stat, win=win)
        return dict(self._meta_cache[key])

    def meta_hash(
        self, *, model: str, mode: str, pos: str, n: int, stat: str, win: int
    ) -> str:
        key = self._key(model=model, mode=mode, pos=pos, n=n, stat=stat, win=win)
        if key not in self._hash_cache:
            _ = self.load(model=model, mode=mode, pos=pos, n=n, stat=stat, win=win)
        return str(self._hash_cache[key])

    def interp_dtype(
        self, *, model: str, mode: str, pos: str, n: int, stat: str, win: int
    ) -> str:
        key = self._key(model=model, mode=mode, pos=pos, n=n, stat=stat, win=win)
        if key not in self._interp_dtype_cache:
            _ = self.load(model=model, mode=mode, pos=pos, n=n, stat=stat, win=win)
        return str(self._interp_dtype_cache[key])

    def validate_clamp_range(
        self,
        *,
        model: str,
        mode: str,
        pos: str,
        n: int,
        stat: str,
        win: int,
        clamp_min: float,
        clamp_max: float,
    ) -> None:
        key = self._key(model=model, mode=mode, pos=pos, n=n, stat=stat, win=win)
        if key not in self._q_range_cache:
            _ = self.load(model=model, mode=mode, pos=pos, n=n, stat=stat, win=win)
        q0, q1 = self._q_range_cache[key]
        if not (q0 <= float(clamp_min) and float(clamp_max) <= q1):
            raise ValueError(
                f"ECDF clamp range outside q range: clamp_min={clamp_min}, "
                f"clamp_max={clamp_max}, q0={q0}, q1={q1}"
            )

    @staticmethod
    def interp_percentile(grid: np.ndarray, q: np.ndarray, x: np.ndarray) -> np.ndarray:
        """Piecewise-linear ECDF mapping; clamped to [0, 1] with tiny endpoint tolerance."""
        dtype = (
            np.float64
            if (grid.dtype == np.float64 or q.dtype == np.float64)
            else np.float32
        )
        # Allow a tiny epsilon near endpoints to avoid CPU/GPU drift from float jitter.
        x_arr = np.asarray(x, dtype=dtype)
        g0 = dtype(grid[0])
        g1 = dtype(grid[-1])
        eps = dtype(1.0e-5)
        # Nudge tiny-below-min values just inside the grid to avoid falling off to 0.0.
        low_nudge = np.minimum(g0 + eps, g1)
        high_nudge = np.maximum(g1 - eps, g0)
        x_adj = np.where((x_arr < g0) & (x_arr >= g0 - eps), low_nudge, x_arr)
        x_adj = np.where((x_adj > g1) & (x_adj <= g1 + eps), high_nudge, x_adj)
        grid_cast = grid.astype(dtype, copy=False)
        q_cast = q.astype(dtype, copy=False)
        out = np.interp(x_adj, grid_cast, q_cast, left=dtype(0.0), right=dtype(1.0))
        return out.astype(dtype, copy=False)

    def percentiles(self, b: Bucket, x: np.ndarray) -> Dict[str, np.ndarray]:
        """Compute percentiles for all three stats using the same bucket selector."""
        out: Dict[str, np.ndarray] = {}
        for stat in ("zsum", "madsum", "logp"):
            grid, qq = self.load(
                model=b.model, mode=b.d, pos=b.se, n=b.n, stat=stat, win=b.win
            )
            out[stat] = self.interp_percentile(grid, qq, x)
        return out

    def percentiles_multi(
        self, b: Bucket, arrays: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """Compute percentiles for specific stats provided in arrays.

        Example: arrays={"zsum": zsum_a, "madsum": madsum_a, "logp": logp_a}
        Only those stats are computed; each uses one cached grid/q and a single interp.
        """
        out: Dict[str, np.ndarray] = {}
        for stat, x in arrays.items():
            grid, qq = self.load(
                model=b.model, mode=b.d, pos=b.se, n=b.n, stat=stat, win=b.win
            )
            out[stat] = self.interp_percentile(grid, qq, x)
        return out

    @staticmethod
    def energy(p: np.ndarray, eps: float = 1e-9) -> np.ndarray:
        """Convert percentile (likelihood) to a positive surprisal-like score."""
        dtype = np.float64 if np.asarray(p).dtype == np.float64 else np.float32
        p = np.asarray(p, dtype=dtype)
        lo = np.nextafter(dtype(0.0), dtype(1.0))
        hi = np.nextafter(dtype(1.0), dtype(0.0))
        if eps is not None:
            lo = np.maximum(lo, dtype(eps))
            hi = np.minimum(hi, dtype(1.0 - float(eps)))
        p = np.clip(p, lo, hi).astype(dtype, copy=False)
        return (-np.log1p(-p)).astype(dtype, copy=False)


# ──────────────────────────────────────────────────────────────────────────────
# Runtime scorer
# ──────────────────────────────────────────────────────────────────────────────


def _norm_dir(d: str) -> str:
    d = str(d).lower()
    if d == "ltr":
        return "ltr"
    if d == "rtl":
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
        prefer_float32: bool = True,
        load_reporter: LmLoadReporter | None = None,
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
        self._prefer_float32 = bool(prefer_float32)
        self._compute_dtype = np.float32 if self._prefer_float32 else np.float64
        self.ecdf = ECDFCache(
            self.root, prefer_float32=self._prefer_float32, load_reporter=load_reporter
        )
        # Coverage cache: key = (L, n, wise:bool, N)
        self._coverage_cache: Dict[
            Tuple[int, int, bool, int], Tuple[np.ndarray, np.ndarray]
        ] = {}

    @classmethod
    def get_cached(
        cls,
        root: Optional[Path] = None,
        *,
        smoothing: str = "auto_gt",
        alpha: float = 0.5,
        oov_policy: str = "floor_min_seen",
        include_char: bool = True,
        prefer_float32: bool = True,
    ) -> "LmPrimeRuntime":
        """
        Return a shared LmPrimeRuntime instance for the given configuration.

        This avoids reloading LM tables/ECDF files across repeated runs within
        the same process (e.g., window scans).
        """
        root_path = (root or default_lm_root()).resolve()
        smoothing = "auto_gt" if smoothing is None else smoothing
        oov_policy = "floor_min_seen" if oov_policy is None else oov_policy
        key = (
            str(root_path),
            str(smoothing),
            float(alpha),
            str(oov_policy),
            bool(include_char),
            bool(prefer_float32),
        )
        cached = _LM_RUNTIME_CACHE.get(key)
        if cached is None:
            cached = cls(
                root=root_path,
                smoothing=smoothing,
                alpha=float(alpha),
                oov_policy=oov_policy,
                include_char=include_char,
                prefer_float32=bool(prefer_float32),
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
                if (
                    pt_windows.ndim != 2
                    or pt_windows.shape[0] <= 0
                    or pt_windows.shape[1] <= 0
                ):
                    raise ValueError(
                        f"{name}: ndarray must be 2D (N,L) with N>0, L>0; got {pt_windows.shape}"
                    )
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

    def _coverage_arrays_cached(
        self, L: int, n: int, wise: bool, N: int
    ) -> Tuple[np.ndarray, np.ndarray]:
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
            pt = pt_windows.astype(np.uint8, copy=False, order="C")
        else:
            pt_rows = [np.asarray(w, dtype=np.uint8) for w in pt_windows]
            try:
                L = int(pt_rows[0].shape[0])
            except Exception:
                raise ValueError("pt_windows must be sequences of equal length")
            pt = np.ascontiguousarray(np.vstack(pt_rows))  # (N, L)

        # L from pt shape
        L = int(pt.shape[1])

        if isinstance(wli_windows, np.ndarray):
            # Accept either (N,L,2) or a single (L,2) window source and derive sliding windows
            if wli_windows.ndim >= 3 and wli_windows.shape[-1] == 2:
                if int(wli_windows.shape[-2]) != L:
                    raise ValueError(
                        f"wli_windows length {wli_windows.shape[-2]} != pt length {L}"
                    )
                # Flatten any leading dims into N
                N = int(pt.shape[0])
                wli_flat = wli_windows.reshape(-1, L, 2)
                if int(wli_flat.shape[0]) != N:
                    # If mismatch, prefer a clear error rather than silent broadcast
                    raise ValueError(
                        f"wli_windows N {wli_flat.shape[0]} != pt windows N {N}"
                    )
                wli = wli_flat.astype(np.uint8, copy=False, order="C")
            elif wli_windows.ndim == 2 and wli_windows.shape[1] == 2:
                # Build (N,L,2) by sliding a single (full) WLI over axis 0
                N = int(pt.shape[0])
                try:
                    from numpy.lib.stride_tricks import sliding_window_view as _swv  # type: ignore

                    wli_sw = _swv(
                        wli_windows.astype(np.uint8, copy=False), window_shape=L, axis=0
                    )
                    # wli_sw shape: (L-L+1, L, 2) == (1, L, 2) if N==1, else (N,L,2)
                    if int(wli_sw.shape[0]) != N:
                        raise ValueError(
                            f"derived wli_windows N {wli_sw.shape[0]} != pt windows N {N}"
                        )
                    wli = wli_sw.astype(np.uint8, copy=False, order="C")
                except Exception:
                    # Fallback: explicit build
                    starts = range(0, 1 + (L - L)) if L > 0 else range(0)
                    wli_list = [
                        wli_windows[s : s + L, :].astype(np.uint8, copy=False)
                        for s in starts
                    ]
                    if len(wli_list) != N:
                        raise ValueError(
                            "wli_windows could not be derived to match pt windows"
                        )
                    wli = np.ascontiguousarray(np.stack(wli_list, 0), dtype=np.uint8)
            else:
                # As a last resort, if sizes match exactly, reshape to (N,L,2)
                N = int(pt.shape[0])
                expected = N * L * 2
                if int(wli_windows.size) == expected:
                    wli = wli_windows.astype(np.uint8, copy=False).reshape(N, L, 2)
                else:
                    raise ValueError(
                        "wli_windows ndarray must have last dim=2 (…, L, 2)"
                    )
        else:
            # Validate and stack WLI pairs: each sentence must be (L, 2)
            wli_rows = []
            for i, pairs in enumerate(wli_windows):
                a = np.asarray(pairs, dtype=np.uint8)
                if a.ndim != 2 or a.shape[1] != 2:
                    raise ValueError(
                        f"wli_windows[{i}] must have shape (L,2); got {a.shape}"
                    )
                if a.shape[0] != L:
                    raise ValueError(
                        f"wli_windows[{i}] length {a.shape[0]} != pt length {L}"
                    )
                wli_rows.append(a)
            wli = np.ascontiguousarray(np.stack(wli_rows, 0))  # (N, L, 2)

        mdl = self.lm._ensure(d, se, "wli", int(n))

        # Raw sums from the native scorer
        logp_sum = np.asarray(mdl.batch_logp(pt, wli, int(n), 0), dtype=np.float32)
        zsum_sum = np.asarray(mdl.batch_zsum(pt, wli, int(n), 0), dtype=np.float32)
        madsum_sum = np.asarray(mdl.batch_madsum(pt, wli, int(n), 0), dtype=np.float32)

        # Normalise by total evals per sentence: (L - n + 1)
        total = float(self._total_eval_from_L(L, n))
        if total <= 0:
            raise ValueError("window too short for given n")
        compute_dtype = getattr(self, "_compute_dtype", np.float32)
        if isinstance(compute_dtype, str):
            compute_dtype = np.float64 if compute_dtype == "float64" else np.float32
        inv = compute_dtype(1.0 / total)

        logp_avg = np.asarray(logp_sum, dtype=compute_dtype) * inv
        zsum_avg = np.asarray(zsum_sum, dtype=compute_dtype) * inv
        madsum_avg = np.asarray(madsum_sum, dtype=compute_dtype) * inv
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

        logp_sum = np.asarray(mdl.batch_logp_char(pt, int(n)), dtype=np.float32)
        zsum_sum = np.asarray(mdl.batch_zsum_char(pt, int(n)), dtype=np.float32)
        madsum_sum = np.asarray(mdl.batch_madsum_char(pt, int(n)), dtype=np.float32)

        L = pt.shape[1]
        total = float(self._total_eval_from_L(L, n))
        if total <= 0:
            raise ValueError("window too short for given n")
        compute_dtype = getattr(self, "_compute_dtype", np.float32)
        if isinstance(compute_dtype, str):
            compute_dtype = np.float64 if compute_dtype == "float64" else np.float32
        inv = compute_dtype(1.0 / total)

        logp_avg = np.asarray(logp_sum, dtype=compute_dtype) * inv
        zsum_avg = np.asarray(zsum_sum, dtype=compute_dtype) * inv
        madsum_avg = np.asarray(madsum_sum, dtype=compute_dtype) * inv
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
        logp_a, zsum_a, madsum_a = self._score_batch_wli(
            dir_, "wise", n, pt_windows, wli_windows
        )
        b = Bucket(_norm_dir(dir_), "wise", "wli", int(n), int(win))
        pct = self.ecdf.percentiles_multi(
            b, {"zsum": zsum_a, "madsum": madsum_a, "logp": logp_a}
        )
        if include_energy:
            energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        else:
            energy = {k: np.zeros_like(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays_cached(
            len(pt_windows[0]), n, True, len(pt_windows)
        )
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
        logp_a, zsum_a, madsum_a = self._score_batch_wli(
            dir_, "nose", n, pt_windows, wli_windows
        )
        b = Bucket(_norm_dir(dir_), "nose", "wli", int(n), int(win))
        pct = self.ecdf.percentiles_multi(
            b, {"zsum": zsum_a, "madsum": madsum_a, "logp": logp_a}
        )
        if include_energy:
            energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        else:
            energy = {k: np.zeros_like(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays_cached(
            len(pt_windows[0]), n, False, len(pt_windows)
        )
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
        pct = self.ecdf.percentiles_multi(
            b, {"zsum": zsum_a, "madsum": madsum_a, "logp": logp_a}
        )
        if include_energy:
            energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        else:
            energy = {k: np.zeros_like(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays_cached(
            len(pt_windows[0]), n, True, len(pt_windows)
        )
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
        pct = self.ecdf.percentiles_multi(
            b, {"zsum": zsum_a, "madsum": madsum_a, "logp": logp_a}
        )
        if include_energy:
            energy = {k: self.ecdf.energy(v) for k, v in pct.items()}
        else:
            energy = {k: np.zeros_like(v) for k, v in pct.items()}
        interior, total = self._coverage_arrays_cached(
            len(pt_windows[0]), n, False, len(pt_windows)
        )
        return {
            "avg": {"logp": logp_a, "zsum": zsum_a, "madsum": madsum_a},
            "pct": pct,
            "energy": energy,
            "coverage": {"interior": interior, "total_eval": total},
        }


# TODO(test): Add a small regression test that ECDF percentiles clamp strictly to [0,1].
