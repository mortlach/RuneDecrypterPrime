# ============================================================
# rune_decrypter_prime/scoring/rune_scorer.py   (NumPy scorer)
# CPU implementation of the normalised objective using Enums at the API.
# Public name/signature preserved: class RuneScorer(BaseScorer)
# ============================================================
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Dict, Any, Optional, Tuple
import numpy as np
import warnings

from rune_decrypter_prime.scoring.base_scorer import BaseScorer, WIN_FIXED
from rune_decrypter_prime.scoring.language_model.language_model_prime_runtime import LmPrimeRuntime
from rune_decrypter_prime.core.types import (
    Direction, SeMode, Channel, ObjectiveFamily, Stat, ObjectiveSpec,
)


def _cfg_get(cfg: Any, key: str, default: Any = None) -> Any:
    if hasattr(cfg, key):
        return getattr(cfg, key)
    if isinstance(cfg, dict):
        return cfg.get(key, default)
    return default

# --------------------------- dtype helpers ---------------------------
_DEF_FLOOR = 1e-6
_DEF_CEIL = 1.0


def _to_u8_1d(a: Iterable[int]) -> np.ndarray:
    x = np.asarray(list(a), dtype=np.uint8)
    return np.ascontiguousarray(x, dtype=np.uint8)


def _to_u8_L2(wli_like: Iterable[Tuple[int, int]]) -> np.ndarray:
    arr = np.asarray(list(wli_like), dtype=np.uint8)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError(f"WLI must be shape (L,2); got {tuple(arr.shape)}")
    return np.ascontiguousarray(arr, dtype=np.uint8)


# =============================== Scorer ===============================
@dataclass
class _WliSourceCacheEntry:
    source_obj: Any
    array: np.ndarray


@dataclass
class _WliWindowCacheEntry:
    source_array: np.ndarray
    windows: np.ndarray


class RuneScorer(BaseScorer):
    """
    NumPy scorer using LanguageModelPrime runtime.

    Input contracts:
      - direction: Direction Enum
      - objective: ObjectiveSpec (ObjectiveFamily.PCT/ENERGY/AVG/NEGLOGP)
      - se_mode: SeMode Enum
      - WLI: iterable of (int,int) pairs with shape (L,2) when provided

    Windows: fixed WIN=10, stride=1.
    """

    def __init__(self, cfg_cipher, scorer_cfg) -> None:
        # Required enums
        self.direction: Direction = _cfg_get(scorer_cfg, "encoding_dir")
        self.se_mode: SeMode = _cfg_get(scorer_cfg, "se_mode")
        self.objective: ObjectiveSpec = _cfg_get(scorer_cfg, "objective")
        if not isinstance(self.direction, Direction):
            raise TypeError("direction must be Direction Enum")
        if not isinstance(self.se_mode, SeMode):
            raise TypeError("se_mode must be SeMode Enum")
        if not isinstance(self.objective, ObjectiveSpec):
            raise TypeError("objective must be ObjectiveSpec")
        if self.objective.family is ObjectiveFamily.ENERGY:
            self.objective = ObjectiveSpec(
                family=ObjectiveFamily.PCT,
                stat=self.objective.stat,
                win=self.objective.win,
            )
        if self.objective.family in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
            if self.objective.win is None:
                legacy_win = _cfg_get(scorer_cfg, "win", WIN_FIXED)
                self.objective = ObjectiveSpec(
                    family=ObjectiveFamily.PCT,
                    stat=self.objective.stat,
                    win=int(legacy_win),
                )
            if int(self.objective.win) != int(WIN_FIXED):
                raise ValueError("pct/energy objectives only support win=10 in the current LM tables.")

        # Channels
        self.include_char: bool = bool(_cfg_get(scorer_cfg, "include_char", True))
        self.use_word_breaks: bool = bool(_cfg_get(scorer_cfg, "use_word_breaks", True))

        # ECDF clamps / dtype
        self._ecdf_floor: float = float(_cfg_get(scorer_cfg, "ecdf_floor", _DEF_FLOOR))
        self._ecdf_ceiling: float = float(_cfg_get(scorer_cfg, "ecdf_ceiling", _DEF_CEIL))
        self._dtype: str = str(_cfg_get(scorer_cfg, "dtype", "float32"))
        if not (0.0 <= self._ecdf_floor <= 1.0 and 0.0 <= self._ecdf_ceiling <= 1.0):
            raise ValueError("ecdf_floor/ceiling must be in [0,1]")
        if self._ecdf_floor > self._ecdf_ceiling:
            raise ValueError("ecdf_floor cannot exceed ecdf_ceiling")
        self._stride: int = int(_cfg_get(scorer_cfg, "stride", 1) or 1)
        if self._stride <= 0:
            raise ValueError("stride must be >= 1")

        # Model selection — either per-order maps or legacy single-order + pair weights
        self._char_weights: Dict[int, float] | None = _cfg_get(scorer_cfg, "char_weights")
        self._wli_weights: Dict[int, float] | None = _cfg_get(scorer_cfg, "wli_weights")
        self._n_char: Optional[int] = _cfg_get(scorer_cfg, "n_char")
        self._n_wli: Optional[int] = _cfg_get(scorer_cfg, "n_wli")
        self._weights_pair: Optional[Tuple[float, float]] = _cfg_get(scorer_cfg, "weights")

        # Language-model runtime (LM tables + ECDF cache)
        rt_kwargs = dict(
            root=getattr(scorer_cfg, "model_root", None),
            smoothing=getattr(scorer_cfg, "smoothing", None),
            alpha=float(getattr(scorer_cfg, "alpha", 0.0) or 0.0),
            oov_policy=getattr(scorer_cfg, "oov_policy", None),
            include_char=self.include_char,
        )
        get_cached = getattr(LmPrimeRuntime, "get_cached", None)
        if callable(get_cached):
            self._rt = get_cached(**rt_kwargs)
        else:
            self._rt = LmPrimeRuntime(**rt_kwargs)
        self._ecdf = self._rt.ecdf

        # Optional Hamming backend (lazy import; skip if unavailable or disabled)
        self._hamming_backend = None
        raw_hw = _cfg_get(scorer_cfg, "hamming_weight", None)
        hw_max_default = float(_cfg_get(scorer_cfg, "hamming_weight_max", 0.01) or 0.0)
        if raw_hw is None:
            if bool(_cfg_get(scorer_cfg, "hamming_enabled", False)):
                self._hamming_weight = hw_max_default
            else:
                self._hamming_weight = 0.0
        else:
            self._hamming_weight = float(raw_hw)
        self._hamming_weight_max: float = float(_cfg_get(scorer_cfg, "hamming_weight_max", hw_max_default))
        self._hamming_ramp_start: float = float(_cfg_get(scorer_cfg, "hamming_ramp_start_frac", 0.2) or 0.0)
        self._hamming_ramp_end: float = float(_cfg_get(scorer_cfg, "hamming_ramp_end_frac", 0.7) or 1.0)
        self._hamming_max_hd: int = int(_cfg_get(scorer_cfg, "hamming_max_hd", 2 ** 31 - 1))
        self._hamming_direction_mode: str = str(_cfg_get(scorer_cfg, "hamming_direction_mode", "match") or "match").lower()
        self._hamming_enabled: bool = bool(_cfg_get(scorer_cfg, "hamming_enabled", False) or self._hamming_weight != 0.0)
        self._hamming_length_weights = None
        try:
            lw = _cfg_get(scorer_cfg, "hamming_length_weights")
            if lw:
                self._hamming_length_weights = {int(k): float(v) for k, v in dict(lw).items()}
        except Exception:
            self._hamming_length_weights = None

        if self._hamming_enabled:
            try:
                from rune_decrypter_prime.scoring.hamming.loader import load_raw1grams_wordlists
                from rune_decrypter_prime.scoring.hamming.backend import HammingBackend

                wl_dir = _cfg_get(scorer_cfg, "hamming_wordlist_dir")
                build_rtl = bool(_cfg_get(scorer_cfg, "hamming_build_rtl", False))
                wl_ltr, wl_rtl = load_raw1grams_wordlists(wl_dir, build_rtl=build_rtl)
                self._hamming_backend = HammingBackend(
                    wl_ltr,
                    wl_rtl if build_rtl else None,
                    max_hd=self._hamming_max_hd,
                    length_weights=self._hamming_length_weights,
                )
            except Exception:
                warnings.warn("Hamming backend unavailable; skipping Hamming scoring component", RuntimeWarning, stacklevel=2)
                self._hamming_backend = None

        # Telemetry invariants
        self._device_str = "cpu"
        # Caches for WLI conversions/windows (bounded LRU)
        self._wli_cache_limit = 8
        self._wli_source_cache: "OrderedDict[int, _WliSourceCacheEntry]" = OrderedDict()
        self._wli_window_cache: "OrderedDict[Tuple[int, int], _WliWindowCacheEntry]" = OrderedDict()

    # ---------------------------- public API ----------------------------
    def score(self, plaintext: Iterable[int], wli_windows: Iterable[Tuple[int, int]] | None = None) -> float:
        fam = self.objective.family
        stat = self.objective.stat
        want_energy = fam is ObjectiveFamily.ENERGY

        if fam is ObjectiveFamily.NEGLOGP:
            warnings.warn("Using legacy objective; consider migrating to PCT.*", DeprecationWarning, stacklevel=2)
            out = float(self._score_legacy_scalar(plaintext, wli_windows))
            self._stash_stats(
                dtype=self._dtype,
                impl="numpy", device=self._device_str,
                legacy_objective=True, score_mean=out, score_std=0.0, n_windows=1,
            )
            return out
        if fam is ObjectiveFamily.AVG:
            out = float(self._score_raw_avg(plaintext, wli_windows))
            return out

        # ENERGY alias → PCT
        if fam not in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
            raise ValueError(f"Unsupported objective family: {fam}")
        if stat is None:
            raise ValueError("ObjectiveSpec.stat is required for PCT/ENERGY")

        pt = _to_u8_1d(plaintext)
        L = int(pt.shape[0])
        win = int(WIN_FIXED)
        nwin = max(0, L - win + 1)
        if nwin == 0:
            self._stash_stats(dtype=self._dtype, impl="numpy", device=self._device_str,
                              score_mean=float(self._ecdf_floor), score_std=0.0, n_windows=0)
            return float(self._ecdf_floor)

        # Prepare windows (vectorised where possible for speed).
        try:
            from numpy.lib.stride_tricks import sliding_window_view as _swv  # type: ignore
            pt_w = _swv(pt, win)
            if not pt_w.flags["C_CONTIGUOUS"]:
                pt_w = np.ascontiguousarray(pt_w, dtype=np.uint8)
            else:
                pt_w = pt_w.astype(np.uint8, copy=False)
        except Exception:
            starts = range(0, L - win + 1)
            pt_w = np.ascontiguousarray([pt[s:s + win] for s in starts], dtype=np.uint8)

        # Optional WLI (shared per window)
        wli = None
        if wli_windows is not None:
            wli = self._get_wli_array(wli_windows)
        if wli is not None and self.use_word_breaks:
            wli_w = self._get_wli_windows(wli, win, nwin)
        else:
            wli_w = None

        # Active models (sorted, L1-normalised)
        models = self._active_models()

        perwin = np.zeros((nwin,), dtype=np.float32)
        raw_perwin = np.zeros((nwin,), dtype=np.float32)
        components: Dict[str, Dict[str, float]] = {}
        dir_name = BaseScorer._dir_name(self.direction)
        se_name = BaseScorer._se_name(self.se_mode)

        # Compute percentiles for each component and mix
        for ch, n, w in models:
            if ch is Channel.CHAR:
                call = self._rt.score_char_nose if se_name == "nose" else self._rt.score_char_wise
                bucket = call(dir_name, int(n), win, pt_w, include_energy=want_energy)
                label = f"char_n{int(n)}"
            else:
                if wli_w is None:
                    # No WLI data: component contributes zeros
                    continue
                call = self._rt.score_wli_nose if se_name == "nose" else self._rt.score_wli_wise
                bucket = call(dir_name, int(n), win, pt_w, wli_w, include_energy=want_energy)
                label = f"wli_n{int(n)}"

            try:
                u = np.asarray(bucket["pct"][stat.value], dtype=np.float32)
            except Exception:
                # Very old table shapes: fall back to pct.logp
                u = np.asarray(bucket.get("pct", {}).get("logp", [0.0] * nwin), dtype=np.float32)
            try:
                raw = np.asarray(bucket["avg"][stat.value], dtype=np.float32)
            except Exception:
                raw = np.asarray(bucket.get("avg", {}).get("logp", [0.0] * nwin), dtype=np.float32)

            # Clamp then mix
            if self._ecdf_floor > 0.0:
                u = np.maximum(u, np.float32(self._ecdf_floor))
            if self._ecdf_ceiling < 1.0:
                u = np.minimum(u, np.float32(self._ecdf_ceiling))
            perwin += np.float32(w) * u
            raw_perwin += np.float32(w) * raw
            components[label] = {
                "pct_lm": float(np.mean(u, dtype=np.float64)),
                "raw_lm": float(np.mean(raw, dtype=np.float64)),
            }

        mean = float(np.mean(perwin, dtype=np.float64))
        std = float(np.std(perwin, dtype=np.float64))  # population/std across windows
        raw_lm = float(np.mean(raw_perwin, dtype=np.float64))
        raw_std = float(np.std(raw_perwin, dtype=np.float64))

        p10 = float(np.percentile(perwin, 10.0))
        p50 = float(np.percentile(perwin, 50.0))
        p90 = float(np.percentile(perwin, 90.0))

        hamming_total = None
        hamming_avg = None
        penalty_raw = 0.0
        if self._hamming_backend is not None and wli is not None:
            try:
                stats = self._hamming_backend.total_min_hd_stats(
                    pt.tolist(),
                    wli.tolist(),
                    direction=self.direction,
                    mode=self._hamming_direction_mode,
                )
                hamming_total = float(stats.get("total_hd", 0.0))
                hamming_avg = float(stats.get("avg_hd_word", hamming_total))
                penalty_raw = float(-self._hamming_weight * hamming_avg)
            except Exception:
                hamming_total = None
                hamming_avg = None

        raw_total = float(raw_lm + penalty_raw)

        energy_lm = None
        try:
            energy_lm = float(self._ecdf.energy(np.asarray([mean], dtype=np.float32))[0])
        except Exception:
            energy_lm = None
        objective = {
            "pct_lm": mean,
            "energy_lm": energy_lm,
            "raw_lm": raw_lm,
            "raw_total": raw_total,
            "penalty_raw": penalty_raw,
            "components": components,
            "windows": {"p10": p10, "p50": p50, "p90": p90},
        }

        self._stash_stats(
            dtype=self._dtype,
            impl="numpy", device=self._device_str,
            score_mean=mean, score_std=std, n_windows=int(nwin),
            raw_score_mean=raw_total, raw_score_std=raw_std,
            raw_score_mean_lm=raw_lm,
            penalty_raw=penalty_raw,
            hamming_total_hd=(hamming_total if hamming_total is not None else None),
            hamming_avg_hd=(hamming_avg if hamming_avg is not None else None),
            hamming_weight=self._hamming_weight,
            objective_stats=objective,
        )
        return mean

    def supports_raw(self) -> bool:
        return True

    def score_with_raw(
        self,
        plaintext: Iterable[int],
        wli_windows: Iterable[Tuple[int, int]] | None = None,
    ) -> Tuple[float, float]:
        pct = float(self.score(plaintext, wli_windows))
        stats = self.last_stats() if hasattr(self, "last_stats") else {}
        raw = stats.get("raw_score_mean", pct) if isinstance(stats, dict) else pct
        return pct, float(raw)

    def _score_raw_avg(
        self,
        plaintext: Iterable[int],
        wli_windows: Iterable[Tuple[int, int]] | None = None,
    ) -> float:
        stat = self.objective.stat
        if stat is None:
            raise ValueError("ObjectiveSpec.stat is required for avg objectives.")
        if self.objective.win is None:
            raise ValueError("ObjectiveSpec.win is required for avg objectives.")

        pt = _to_u8_1d(plaintext)
        L = int(pt.shape[0])
        win = int(self.objective.win)
        stride = int(self._stride)
        nwin = max(0, (L - win) // stride + 1)
        if nwin == 0:
            self._stash_stats(
                dtype=self._dtype,
                impl="numpy", device=self._device_str,
                score_mean=0.0, score_std=0.0, n_windows=0,
                raw_score_mean=0.0, raw_score_std=0.0,
                raw_score_mean_lm=0.0,
                penalty_raw=0.0,
            )
            return 0.0

        try:
            from numpy.lib.stride_tricks import sliding_window_view as _swv  # type: ignore
            pt_w = _swv(pt, win)
            if stride != 1:
                pt_w = pt_w[::stride]
            if not pt_w.flags["C_CONTIGUOUS"]:
                pt_w = np.ascontiguousarray(pt_w, dtype=np.uint8)
            else:
                pt_w = pt_w.astype(np.uint8, copy=False)
        except Exception:
            starts = range(0, L - win + 1, stride)
            pt_w = np.ascontiguousarray([pt[s:s + win] for s in starts], dtype=np.uint8)

        wli = None
        if wli_windows is not None:
            wli = self._get_wli_array(wli_windows)
        if wli is not None and self.use_word_breaks:
            wli_w = self._get_wli_windows(wli, win, nwin, stride=stride)
        else:
            wli_w = None

        models = self._active_models()
        raw_perwin = np.zeros((nwin,), dtype=np.float32)
        components: Dict[str, Dict[str, float]] = {}
        dir_name = BaseScorer._dir_name(self.direction)
        se_name = BaseScorer._se_name(self.se_mode)

        for ch, n, w in models:
            if ch is Channel.CHAR:
                logp_a, zsum_a, madsum_a = self._rt._score_batch_char(dir_name, se_name, int(n), pt_w)
                label = f"char_n{int(n)}"
            else:
                if wli_w is None:
                    continue
                logp_a, zsum_a, madsum_a = self._rt._score_batch_wli(dir_name, se_name, int(n), pt_w, wli_w)
                label = f"wli_n{int(n)}"

            if stat is Stat.ZSUM:
                raw = zsum_a
            elif stat is Stat.MADSUM:
                raw = madsum_a
            else:
                raw = logp_a

            raw_perwin += np.float32(w) * np.asarray(raw, dtype=np.float32)
            components[label] = {
                "raw_lm": float(np.mean(raw, dtype=np.float64)),
            }

        raw_lm = float(np.mean(raw_perwin, dtype=np.float64))
        raw_std = float(np.std(raw_perwin, dtype=np.float64))

        hamming_total = None
        hamming_avg = None
        penalty_raw = 0.0
        if self._hamming_backend is not None and wli is not None:
            try:
                stats = self._hamming_backend.total_min_hd_stats(
                    pt.tolist(),
                    wli.tolist(),
                    direction=self.direction,
                    mode=self._hamming_direction_mode,
                )
                hamming_total = float(stats.get("total_hd", 0.0))
                hamming_avg = float(stats.get("avg_hd_word", hamming_total))
                penalty_raw = float(-self._hamming_weight * hamming_avg)
            except Exception:
                hamming_total = None
                hamming_avg = None

        raw_total = float(raw_lm + penalty_raw)

        p10 = float(np.percentile(raw_perwin, 10.0))
        p50 = float(np.percentile(raw_perwin, 50.0))
        p90 = float(np.percentile(raw_perwin, 90.0))
        objective = {
            "pct_lm": None,
            "energy_lm": None,
            "raw_lm": raw_lm,
            "raw_total": raw_total,
            "penalty_raw": penalty_raw,
            "components": components,
            "windows": {"p10": p10, "p50": p50, "p90": p90},
        }

        self._stash_stats(
            dtype=self._dtype,
            impl="numpy", device=self._device_str,
            score_mean=raw_total, score_std=raw_std, n_windows=int(nwin),
            raw_score_mean=raw_total, raw_score_std=raw_std,
            raw_score_mean_lm=raw_lm,
            penalty_raw=penalty_raw,
            hamming_total_hd=(hamming_total if hamming_total is not None else None),
            hamming_avg_hd=(hamming_avg if hamming_avg is not None else None),
            hamming_weight=self._hamming_weight,
            objective_stats=objective,
        )
        return raw_total

    def set_hamming_progress(self, progress: float) -> None:
        """
        Optional hook for solvers: update the effective Hamming weight using a
        piecewise-linear ramp based on progress in [0,1].
        """
        if not self._hamming_enabled:
            return
        try:
            from rune_decrypter_prime.scoring.hamming.anneal import compute_hamming_weight
            self._hamming_weight = float(compute_hamming_weight(progress, self._hamming_weight_max, self._hamming_ramp_start, self._hamming_ramp_end))
        except Exception:
            pass

    def batch_score(self, pts: Sequence[Iterable[int]], wlis: Sequence[Iterable[Tuple[int, int]]] | Iterable[Tuple[int, int]] | None = None) -> np.ndarray:
        pts_seq = list(pts)
        if not pts_seq:
            return np.asarray([], dtype=np.float32)

        materialised_pts: List[Iterable[int]] = []
        lengths = set()
        for p in pts_seq:
            if isinstance(p, np.ndarray):
                materialised_pts.append(p)
                lengths.add(int(p.shape[0]))
            elif isinstance(p, (list, tuple)):
                materialised_pts.append(p)
                lengths.add(len(p))
            else:
                seq = tuple(p)
                materialised_pts.append(seq)
                lengths.add(len(seq))
        if len(lengths) != 1:
            raise ValueError("all plaintexts must have the same length in batch_score()")
        L0 = lengths.pop()

        # Interpret WLI as shared (L,2) or per-item list[(L,2)]
        wli_single = None
        wli_list = None
        if wlis is not None:
            if hasattr(wlis, "__len__"):
                size = len(wlis)  # type: ignore[arg-type]
                if size == L0:
                    wli_single = wlis  # type: ignore[assignment]
                elif size == len(materialised_pts):
                    wli_list = list(wlis)  # type: ignore[arg-type]
                else:
                    raise ValueError("wlis length must equal plaintext length or batch size.")
            else:
                try:
                    candidate = list(wlis)  # type: ignore[arg-type]
                except TypeError:
                    wli_single = wlis  # type: ignore[assignment]
                else:
                    if len(candidate) == len(materialised_pts):
                        wli_list = candidate  # type: ignore[assignment]
                    elif len(candidate) == L0:
                        wli_single = candidate  # type: ignore[assignment]
                    else:
                        raise ValueError("wlis iterable must expand to plaintext length or batch size.")

        out = np.zeros((len(pts),), dtype=np.float32)
        stds = np.zeros_like(out)
        raws = np.zeros_like(out)
        for i, pt in enumerate(materialised_pts):
            wli_i = wli_single if wli_single is not None else (wli_list[i] if wli_list is not None else None)
            out[i] = self.score(pt, wli_i)
            stats = self.last_stats()
            raws[i] = np.float32(float(stats.get("raw_score_mean", out[i])) if isinstance(stats, dict) else float(out[i]))
            stds[i] = np.float32(float(self.telemetry().get("score_std", 0.0)))

        self._stash_stats(
            dtype=self._dtype,
            impl="numpy", device=self._device_str,
            score_mean_batch=out.astype(np.float32).tolist(),
            score_std_batch=stds.astype(np.float32).tolist(),
            raw_score_mean_batch=raws.astype(np.float32).tolist(),
            n_windows=max(0, L0 - int(WIN_FIXED) + 1),
        )
        return out.astype(np.float32, copy=False)

    def batch_score_with_raw(
        self,
        pts: Sequence[Iterable[int]],
        wlis: Sequence[Iterable[Tuple[int, int]]] | Iterable[Tuple[int, int]] | None = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        pts_seq = list(pts)
        if not pts_seq:
            return np.asarray([], dtype=np.float32), np.asarray([], dtype=np.float32)
        out = np.zeros((len(pts_seq),), dtype=np.float32)
        raw = np.zeros_like(out)
        stds = np.zeros_like(out)
        n_windows = None
        for i, pt in enumerate(pts_seq):
            wli_i = None
            if wlis is not None:
                if isinstance(wlis, (list, tuple)) and len(wlis) == len(pts_seq):
                    wli_i = wlis[i]
                else:
                    wli_i = wlis
            pct_i = float(self.score(pt, wli_i))
            stats = self.last_stats()
            raw_i = stats.get("raw_score_mean", pct_i) if isinstance(stats, dict) else pct_i
            out[i] = np.float32(pct_i)
            raw[i] = np.float32(raw_i)
            stds[i] = np.float32(float(self.telemetry().get("score_std", 0.0)))
            if n_windows is None and isinstance(stats, dict):
                n_windows = stats.get("n_windows")
        if n_windows is None:
            try:
                L0 = len(pts_seq[0])
            except Exception:
                n_windows = 0
            else:
                n_windows = max(0, int(L0) - int(WIN_FIXED) + 1)
        self._stash_stats(
            dtype=self._dtype,
            impl="numpy",
            device=self._device_str,
            score_mean_batch=out.astype(np.float32).tolist(),
            score_std_batch=stds.astype(np.float32).tolist(),
            raw_score_mean_batch=raw.astype(np.float32).tolist(),
            n_windows=int(n_windows),
        )
        return out.astype(np.float32, copy=False), raw.astype(np.float32, copy=False)

    def clear_wli_cache(self) -> None:
        """Manual hook to drop cached WLI conversions/windows between solver runs."""
        self._wli_source_cache.clear()
        self._wli_window_cache.clear()

    # ---------------------------- cache helpers ----------------------------
    def _get_wli_array(self, wli_windows: Iterable[Tuple[int, int]]) -> np.ndarray:
        src_id = id(wli_windows)
        entry = self._wli_source_cache.get(src_id)
        if entry is not None and entry.source_obj is wli_windows:
            self._wli_source_cache.move_to_end(src_id)
            return entry.array
        wli = _to_u8_L2(wli_windows)
        self._remember_wli_source(src_id, wli_windows, wli)
        return wli

    def _remember_wli_source(self, key: int, src_obj: Any, array: np.ndarray) -> None:
        if len(self._wli_source_cache) >= self._wli_cache_limit:
            _, evicted = self._wli_source_cache.popitem(last=False)
            self._purge_windows_for_array(evicted.array)
        self._wli_source_cache[key] = _WliSourceCacheEntry(source_obj=src_obj, array=array)

    def _purge_windows_for_array(self, source_array: np.ndarray) -> None:
        drop_keys = [key for key, entry in self._wli_window_cache.items() if entry.source_array is source_array]
        for key in drop_keys:
            del self._wli_window_cache[key]

    def _get_wli_windows(self, wli: np.ndarray, win: int, nwin: int, *, stride: int = 1) -> np.ndarray:
        cache_key = (id(wli), int(win), int(stride))
        entry = self._wli_window_cache.get(cache_key)
        if entry is not None and entry.source_array is wli:
            self._wli_window_cache.move_to_end(cache_key)
            return entry.windows
        try:
            from numpy.lib.stride_tricks import sliding_window_view as _swv  # type: ignore
            wli_w = _swv(wli, window_shape=win, axis=0)
            wli_w = np.swapaxes(wli_w, 1, 2)
            if int(stride) != 1:
                wli_w = wli_w[:: int(stride)]
            if not wli_w.flags["C_CONTIGUOUS"]:
                wli_w = np.ascontiguousarray(wli_w, dtype=np.uint8)
            else:
                wli_w = wli_w.astype(np.uint8, copy=False)
        except Exception:
            starts = range(0, nwin * int(stride), int(stride))
            wli_w = np.ascontiguousarray([wli[s:s + win, :] for s in starts], dtype=np.uint8)
        self._remember_wli_windows(cache_key, wli, wli_w)
        return wli_w

    def _remember_wli_windows(self, key: Tuple[int, int, int], source_array: np.ndarray, windows: np.ndarray) -> None:
        if len(self._wli_window_cache) >= self._wli_cache_limit:
            self._wli_window_cache.popitem(last=False)
        self._wli_window_cache[key] = _WliWindowCacheEntry(source_array=source_array, windows=windows)

    # ---------------------------- legacy path ----------------------------
    def _score_legacy_scalar(self, plaintext: Iterable[int], wli_windows: Iterable[Tuple[int, int]] | None) -> float:
        pt = _to_u8_1d(plaintext)
        L = int(pt.shape[0])
        if L == 0:
            return float(self._ecdf_floor)

        dir_name = BaseScorer._dir_name(self.direction)
        se_name = BaseScorer._se_name(self.se_mode)

        # CHAR
        char_val = 0.0
        for ch, n, w in self._active_models():
            if ch is Channel.CHAR:
                call = self._rt.score_char_nose if se_name == "nose" else self._rt.score_char_wise
                bucket = call(dir_name, int(n), int(WIN_FIXED), [pt], include_energy=False)
                char_val = _extract_legacy(bucket, self.objective)
                break

        # WLI
        wli_val = 0.0
        if wli_windows is not None and self.use_word_breaks:
            for ch, n, w in self._active_models():
                if ch is Channel.WLI:
                    wli = _to_u8_L2(wli_windows)
                    call = self._rt.score_wli_nose if se_name == "nose" else self._rt.score_wli_wise
                    bucket = call(dir_name, int(n), int(WIN_FIXED), [pt], [wli], include_energy=False)
                    wli_val = _extract_legacy(bucket, self.objective)
                    break

        # Mix (renormalise if one side absent)
        w_char = sum(w for ch, n, w in self._active_models() if ch is Channel.CHAR)
        w_wli = sum(w for ch, n, w in self._active_models() if ch is Channel.WLI)
        s = (w_char + w_wli) or 1.0
        w_char /= s
        w_wli /= s
        return float(w_char * char_val + w_wli * wli_val)

    # ---------------------------- model selection ----------------------------
    def _active_models(self) -> List[Tuple[Channel, int, float]]:
        # Prefer per-order maps if any provided
        have_maps = (self._char_weights is not None and len(self._char_weights) > 0) or (
            self._wli_weights is not None and len(self._wli_weights) > 0
        )
        models: List[Tuple[Channel, int, float]] = []
        if have_maps:
            if self.include_char and self._char_weights:
                for n, w in sorted({int(k): float(v) for k, v in self._char_weights.items() if float(v) > 0.0}.items()):
                    models.append((Channel.CHAR, int(n), float(w)))
            if self.use_word_breaks and self._wli_weights:
                for n, w in sorted({int(k): float(v) for k, v in self._wli_weights.items() if float(v) > 0.0}.items()):
                    models.append((Channel.WLI, int(n), float(w)))
        else:
            # Legacy single-order + pair weights
            w_char, w_wli = self._weights_pair or (0.5, 0.5)
            if self.include_char:
                if self._n_char is None:
                    raise ValueError("n_char must be set when include_char=True and using legacy weights")
                models.append((Channel.CHAR, int(self._n_char), float(w_char)))
            if self.use_word_breaks:
                if self._n_wli is None:
                    raise ValueError("n_wli must be set when use_word_breaks=True and using legacy weights")
                models.append((Channel.WLI, int(self._n_wli), float(w_wli)))

        # L1-normalise weights
        s = sum(max(0.0, w) for _, _, w in models)
        if s <= 0.0:
            raise ValueError("No active models; check weights and include/use flags")
        return [(ch, n, (w / s)) for ch, n, w in models]


# ---------------------------- legacy extraction ----------------------------
def _extract_legacy(bucket_out: Dict[str, Any], objective: ObjectiveSpec) -> float:
    fam = objective.family
    stat = objective.stat or Stat.LOGP
    if fam is ObjectiveFamily.NEGLOGP:
        return float(-np.asarray(bucket_out["avg"]["logp"], dtype=np.float32)[0])
    if fam is ObjectiveFamily.AVG:
        if stat not in (Stat.LOGP, Stat.ZSUM, Stat.MADSUM):
            raise ValueError(f"unknown avg stat: {stat}")
        return float(np.asarray(bucket_out["avg"][stat.value], dtype=np.float32)[0])
    # Fallback: try pct.logp scalar if present
    try:
        return float(np.asarray(bucket_out["pct"]["logp"], dtype=np.float32)[0])
    except Exception as e:
        raise ValueError(f"unsupported legacy objective: {fam}.{stat}") from e

