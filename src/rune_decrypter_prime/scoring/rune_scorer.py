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
from rune_decrypter_prime.scoring.windowing import (
    START_TAG,
    END_TAG,
    span_core_tokens,
    aligned_window_count,
    span_map,
    span_max,
)
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
_DEF_CLAMP_MIN = 1e-6
# Use the largest float32 below 1.0 to avoid ENERGY singularities.
_DEF_CLAMP_MAX = float(np.nextafter(np.float32(1.0), np.float32(0.0)))


def _to_u8_1d(a: Iterable[int]) -> np.ndarray:
    x = np.asarray(list(a), dtype=np.uint8)
    return np.ascontiguousarray(x, dtype=np.uint8)


def _to_u8_L2(wli_like: Iterable[Tuple[int, int]]) -> np.ndarray:
    arr_i64 = np.asarray(list(wli_like), dtype=np.int64)
    if arr_i64.ndim != 2 or arr_i64.shape[1] != 2:
        raise ValueError(f"WLI must be shape (L,2); got {tuple(arr_i64.shape)}")
    if arr_i64.size == 0:
        raise ValueError("WLI must be non-empty when use_word_breaks is enabled")
    if (arr_i64 < 0).any() or (arr_i64 > 255).any():
        raise ValueError("WLI entries must fit in uint8 (0..255)")
    return np.ascontiguousarray(arr_i64.astype(np.uint8, copy=False), dtype=np.uint8)


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

    Windows: W = n-grams per window (W=10 typical), stride in runes.
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
        if self.se_mode is SeMode.WISE:
            raise ValueError("WISE mode is not supported yet; use NOSE.")
        if not isinstance(self.objective, ObjectiveSpec):
            raise TypeError("objective must be ObjectiveSpec")
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
        self._ecdf_clamp_min: float = float(_cfg_get(
            scorer_cfg,
            "ecdf_clamp_min",
            _cfg_get(scorer_cfg, "ecdf_floor", _DEF_CLAMP_MIN),
        ))
        self._ecdf_clamp_max: float = float(_cfg_get(
            scorer_cfg,
            "ecdf_clamp_max",
            _cfg_get(scorer_cfg, "ecdf_ceiling", _DEF_CLAMP_MAX),
        ))
        self._dtype: str = str(_cfg_get(scorer_cfg, "dtype", "float32"))
        if not (0.0 < self._ecdf_clamp_min < 1.0 and 0.0 < self._ecdf_clamp_max < 1.0):
            raise ValueError("ecdf_clamp_min/max must be in (0,1) for ENERGY-safe scoring")
        if self._ecdf_clamp_min >= self._ecdf_clamp_max:
            raise ValueError("ecdf_clamp_min must be < ecdf_clamp_max")
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
        self._diagnostics_enabled: bool = bool(_cfg_get(scorer_cfg, "diagnostics_enabled", False))

    def _build_aligned_windows(
        self,
        pt: np.ndarray,
        wli: np.ndarray | None,
        *,
        n_set: List[int],
        W: int,
        stride: int,
    ) -> tuple[Dict[int, np.ndarray], Dict[int, np.ndarray] | None, Dict[int, int], int, bool]:
        """Build aligned windows per n using L_max start-index alignment.

        Returns:
          pt_windows_by_n: dict[n] -> np.ndarray [nwin, L_n]
          wli_windows_by_n: dict[n] -> np.ndarray [nwin, L_n, 2] (or None if no WLI)
          L_n_full: dict[n] -> L_n (full span including tags if WISE)
          nwin: int number of aligned windows
          tags_injected: bool (True if WISE tags were injected at sentence level)
        """
        if pt.ndim != 1:
            raise ValueError("pt must be a 1D uint8 array")
        if wli is not None and (wli.ndim != 2 or wli.shape[1] != 2):
            raise ValueError("wli must be shape (L,2)")
        if wli is not None and wli.shape[0] != pt.shape[0]:
            raise ValueError("pt and wli length mismatch")

        se_name = BaseScorer._se_name(self.se_mode)
        wise = (se_name == "wise")
        tags_injected = False

        interior_pt = pt
        interior_wli = wli
        if wise:
            if pt.shape[0] >= 2 and int(pt[0]) == START_TAG and int(pt[-1]) == END_TAG:
                interior_pt = pt[1:-1]
                if wli is not None:
                    interior_wli = wli[1:-1]
            else:
                tags_injected = True
                interior_pt = pt
                interior_wli = wli
        else:
            if np.any((pt == START_TAG) | (pt == END_TAG)):
                raise ValueError("NOSE input must not include boundary tags")

        # Core spans (no tags) used for slicing
        core_spans: Dict[int, int] = {int(n): span_core_tokens(n=int(n), W=W) for n in n_set}
        if not core_spans:
            raise ValueError("n_set must not be empty")
        L_max_core = max(core_spans.values())

        Lint = int(interior_pt.shape[0])
        stride_i = int(stride)
        if stride_i <= 0:
            raise ValueError("stride must be >= 1")
        if Lint < L_max_core:
            return {}, None, span_map(n_set=n_set, W=W, se_mode=self.se_mode), 0, tags_injected

        starts = np.arange(0, Lint - L_max_core + 1, stride_i, dtype=np.int32)
        nwin = int(starts.size)

        pt_windows: Dict[int, np.ndarray] = {}
        wli_windows: Dict[int, np.ndarray] | None = {} if (wli is not None) else None

        try:
            from numpy.lib.stride_tricks import sliding_window_view as _swv  # type: ignore
            swv_pt = None
            for n, core_len in core_spans.items():
                if swv_pt is None or getattr(swv_pt, "shape", None) is None or swv_pt.shape[1] != core_len:
                    swv_pt = _swv(interior_pt, window_shape=core_len, axis=0)
                pt_core = swv_pt[starts]
                if wise:
                    pt_w = np.empty((nwin, core_len + 2), dtype=np.uint8)
                    pt_w[:, 0] = START_TAG
                    pt_w[:, -1] = END_TAG
                    pt_w[:, 1:-1] = pt_core
                else:
                    pt_w = np.ascontiguousarray(pt_core, dtype=np.uint8)
                pt_windows[int(n)] = pt_w

                if wli_windows is not None and interior_wli is not None:
                    w_core = _swv(interior_wli, window_shape=core_len, axis=0)[starts]
                    # sliding_window_view on (L,2) yields (nwin, 2, core_len); swap to (nwin, core_len, 2)
                    w_core = np.swapaxes(w_core, 1, 2)
                    if wise:
                        w_w = np.zeros((nwin, core_len + 2, 2), dtype=np.uint8)
                        w_w[:, 1:-1, :] = w_core
                    else:
                        w_w = np.ascontiguousarray(w_core, dtype=np.uint8)
                    wli_windows[int(n)] = w_w
        except Exception:
            for n, core_len in core_spans.items():
                rows = [interior_pt[i:i + core_len] for i in starts.tolist()]
                pt_core = np.ascontiguousarray(rows, dtype=np.uint8)
                if wise:
                    pt_w = np.empty((nwin, core_len + 2), dtype=np.uint8)
                    pt_w[:, 0] = START_TAG
                    pt_w[:, -1] = END_TAG
                    pt_w[:, 1:-1] = pt_core
                else:
                    pt_w = pt_core
                pt_windows[int(n)] = pt_w

                if wli_windows is not None and interior_wli is not None:
                    w_rows = [interior_wli[i:i + core_len] for i in starts.tolist()]
                    w_core = np.ascontiguousarray(w_rows, dtype=np.uint8)
                    if wise:
                        w_w = np.zeros((nwin, core_len + 2, 2), dtype=np.uint8)
                        w_w[:, 1:-1, :] = w_core
                    else:
                        w_w = w_core
                    wli_windows[int(n)] = w_w

        return pt_windows, wli_windows, span_map(n_set=n_set, W=W, se_mode=self.se_mode), nwin, tags_injected

    # ---------------------------- public API ----------------------------
    def score(self, plaintext: Iterable[int], wli_windows: Iterable[Tuple[int, int]] | None = None) -> float:
        fam = self.objective.family
        stat = self.objective.stat
        want_energy = fam is ObjectiveFamily.ENERGY

        if self._requires_wli() and wli_windows is None:
            raise ValueError("WLI is required when use_word_breaks=True and WLI models are active")

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

        if fam not in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
            raise ValueError(f"Unsupported objective family: {fam}")
        if stat is None:
            raise ValueError("ObjectiveSpec.stat is required for PCT/ENERGY")

        pt = _to_u8_1d(plaintext)
        W = int(self.objective.win or WIN_FIXED)
        stride = int(self._stride)

        # Optional WLI (shared per sentence)
        wli = None
        if wli_windows is not None and self.use_word_breaks:
            wli = self._get_wli_array(wli_windows)

        models = self._active_models()
        n_set = sorted({int(n) for _, n, _ in models})

        pt_w_map, wli_w_map, L_n_full, nwin, tags_injected = self._build_aligned_windows(
            pt, wli, n_set=n_set, W=W, stride=stride
        )
        L_max = max(L_n_full.values()) if L_n_full else 0

        dir_name = BaseScorer._dir_name(self.direction)
        se_name = BaseScorer._se_name(self.se_mode)
        wise = (se_name == "wise")
        stat_name = stat.value
        variant = "mean_per_ngram_interior" if wise else "mean_per_ngram_total"
        total_eval = (W + 2) if wise else W
        interior_eval = W if wise else W
        scale_interior = (float(total_eval) / float(interior_eval)) if wise else 1.0

        # Short text: no windows
        if nwin == 0:
            pct_floor = float(self._ecdf_clamp_min)
            energy_floor = float(self._ecdf.energy(np.asarray([pct_floor], dtype=np.float32))[0])
            score_mean = energy_floor if want_energy else pct_floor
            score_std = 0.0
            hamming_total = None
            hamming_avg = None
            penalty_hamming = 0.0
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
                    penalty_hamming = float(-self._hamming_weight * hamming_avg)
                except Exception:
                    hamming_total = None
                    hamming_avg = None
                    penalty_hamming = 0.0
            stat_penalized_mean = float(penalty_hamming)
            objective = {
                f"pct_{stat_name}_{variant}": pct_floor,
                f"energy_{stat_name}_{variant}": energy_floor,
                f"{stat_name}_mean_per_ngram_total": 0.0,
                f"{stat_name}_mean_per_ngram_interior": 0.0,
                f"{stat_name}_mean_per_ngram_penalized": stat_penalized_mean,
                "penalty_hamming": penalty_hamming,
                "components": {},
                "windows": {},
                "n_windows": 0,
                "score_mean": float(score_mean),
            }
            self._stash_stats(
                dtype=self._dtype,
                impl="numpy",
                device=self._device_str,
                score_mean=float(score_mean),
                score_std=float(score_std),
                n_windows=0,
                **{
                    "window.win_ngrams": int(W),
                    "window.se_mode": se_name,
                    "window.n_set": list(n_set),
                    "window.stride_runes": int(stride),
                    "window.L_n": L_n_full,
                    "window.L_max": int(L_max),
                    "window.n_windows": 0,
                    "window.tags_injected": bool(tags_injected),
                    "stat.name": stat_name,
                    "stat.variant": variant,
                    "stat.ngrams_total": int(total_eval),
                    **({"stat.ngrams_interior": int(interior_eval)} if wise else {}),
                    "stat.mean_per_ngram_penalized": float(stat_penalized_mean),
                    "direction": dir_name,
                    "objective.id": self._objective_id(stat_name, variant, W, n_set, dir_name, se_name),
                    "objective.label": self._objective_label(stat_name, variant, W, n_set, dir_name, se_name),
                },
                hamming_total_hd=(hamming_total if hamming_total is not None else None),
                hamming_avg_hd=(hamming_avg if hamming_avg is not None else None),
                hamming_weight=self._hamming_weight,
                objective_stats=objective,
            )
            return float(score_mean)

        pct_perwin = np.zeros((nwin,), dtype=np.float32)
        stat_total_perwin = np.zeros((nwin,), dtype=np.float32)
        stat_interior_perwin = np.zeros((nwin,), dtype=np.float32)
        components: Dict[str, Dict[str, float]] = {}

        asset_ids: List[str] = []
        asset_fps: List[str] = []
        interp_dtypes: List[str] = []
        meta_json_list: List[str] = []

        for ch, n, w in models:
            pt_w = pt_w_map.get(int(n))
            if pt_w is None or pt_w.shape[0] == 0:
                continue
            if ch is Channel.CHAR:
                logp_a, zsum_a, madsum_a = self._rt._score_batch_char(dir_name, se_name, int(n), pt_w)
                model_name = "char"
                label = f"char_n{int(n)}"
            else:
                if wli_w_map is None or wli_w_map.get(int(n)) is None:
                    continue
                wli_w = wli_w_map[int(n)]
                logp_a, zsum_a, madsum_a = self._rt._score_batch_wli(dir_name, se_name, int(n), pt_w, wli_w)
                model_name = "wli"
                label = f"wli_n{int(n)}"

            if stat is Stat.ZSUM:
                avg_total = zsum_a
            elif stat is Stat.MADSUM:
                avg_total = madsum_a
            else:
                avg_total = logp_a

            avg_interior = avg_total * np.float32(scale_interior)
            stat_total_perwin += np.float32(w) * np.asarray(avg_total, dtype=np.float32)
            stat_interior_perwin += np.float32(w) * np.asarray(avg_interior, dtype=np.float32)

            stat_variant = avg_interior if wise else avg_total

            # ECDF lookup for chosen variant
            self._ecdf.validate_clamp_range(
                model=model_name,
                mode=dir_name,
                pos=se_name,
                n=int(n),
                stat=stat_name,
                clamp_min=self._ecdf_clamp_min,
                clamp_max=self._ecdf_clamp_max,
            )
            grid, q = self._ecdf.load(model=model_name, mode=dir_name, pos=se_name, n=int(n), stat=stat_name)
            u = self._ecdf.interp_percentile(grid, q, np.asarray(stat_variant, dtype=np.float32))
            u = np.clip(u, np.float32(self._ecdf_clamp_min), np.float32(self._ecdf_clamp_max))
            pct_perwin += np.float32(w) * u

            components[label] = {
                f"{stat_name}_mean_per_ngram_total": float(np.mean(avg_total, dtype=np.float64)),
                f"{stat_name}_mean_per_ngram_interior": float(np.mean(avg_interior, dtype=np.float64)),
                f"pct_{stat_name}_{variant}": float(np.mean(u, dtype=np.float64)),
            }

            asset_ids.append(self._ecdf.asset_id(model=model_name, mode=dir_name, pos=se_name, n=int(n), stat=stat_name))
            asset_fps.append(self._ecdf.meta_hash(model=model_name, mode=dir_name, pos=se_name, n=int(n), stat=stat_name))
            interp_dtypes.append(self._ecdf.interp_dtype(model=model_name, mode=dir_name, pos=se_name, n=int(n), stat=stat_name))
            if self._diagnostics_enabled:
                try:
                    import json as _json
                    meta = self._ecdf.meta(model=model_name, mode=dir_name, pos=se_name, n=int(n), stat=stat_name)
                    meta_json_list.append(_json.dumps(meta, sort_keys=True))
                except Exception:
                    pass

        pct_mean = float(np.mean(pct_perwin, dtype=np.float64))
        pct_std = float(np.std(pct_perwin, dtype=np.float64))
        energy_perwin = self._ecdf.energy(pct_perwin)
        energy_mean = float(np.mean(energy_perwin, dtype=np.float64))
        energy_std = float(np.std(energy_perwin, dtype=np.float64))

        score_mean = energy_mean if want_energy else pct_mean
        score_std = energy_std if want_energy else pct_std

        stat_total_mean = float(np.mean(stat_total_perwin, dtype=np.float64))
        stat_total_std = float(np.std(stat_total_perwin, dtype=np.float64))
        stat_interior_mean = float(np.mean(stat_interior_perwin, dtype=np.float64))
        stat_interior_std = float(np.std(stat_interior_perwin, dtype=np.float64))
        stat_variant_mean = stat_interior_mean if wise else stat_total_mean
        stat_variant_std = stat_interior_std if wise else stat_total_std

        window_metric = energy_perwin if want_energy else pct_perwin
        p10 = float(np.percentile(window_metric, 10.0))
        p50 = float(np.percentile(window_metric, 50.0))
        p90 = float(np.percentile(window_metric, 90.0))

        hamming_total = None
        hamming_avg = None
        penalty_hamming = 0.0
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
                penalty_hamming = float(-self._hamming_weight * hamming_avg)
            except Exception:
                hamming_total = None
                hamming_avg = None

        stat_penalized_mean = float(stat_variant_mean + penalty_hamming)
        stat_penalized_std = float(stat_variant_std)

        objective = {
            f"pct_{stat_name}_{variant}": pct_mean,
            f"energy_{stat_name}_{variant}": energy_mean,
            f"{stat_name}_mean_per_ngram_total": stat_total_mean,
            f"{stat_name}_mean_per_ngram_interior": stat_interior_mean,
            f"{stat_name}_mean_per_ngram_penalized": stat_penalized_mean,
            "penalty_hamming": penalty_hamming,
            "components": components,
            "windows": {"p10": p10, "p50": p50, "p90": p90},
            "n_windows": int(nwin),
            "score_mean": float(score_mean),
        }

        ecdf_asset_id = asset_ids[0] if len(asset_ids) == 1 else asset_ids
        ecdf_fp = asset_fps[0] if len(asset_fps) == 1 else asset_fps
        ecdf_interp_dtype = interp_dtypes[0] if len(interp_dtypes) == 1 else interp_dtypes

        self._stash_stats(
            dtype=self._dtype,
            impl="numpy",
            device=self._device_str,
            score_mean=float(score_mean),
            score_std=float(score_std),
            n_windows=int(nwin),
            **{
                "window.win_ngrams": int(W),
                "window.se_mode": se_name,
                "window.n_set": list(n_set),
                "window.stride_runes": int(stride),
                "window.L_n": L_n_full,
                "window.L_max": int(L_max),
                "window.n_windows": int(nwin),
                "window.tags_injected": bool(tags_injected),
                "stat.name": stat_name,
                "stat.variant": variant,
                "stat.ngrams_total": int(total_eval),
                **({"stat.ngrams_interior": int(interior_eval)} if wise else {}),
                "stat.mean_per_ngram_total.mean": float(stat_total_mean),
                "stat.mean_per_ngram_total.std": float(stat_total_std),
                "stat.mean_per_ngram_interior.mean": float(stat_interior_mean),
                "stat.mean_per_ngram_interior.std": float(stat_interior_std),
                "stat.mean_per_ngram_penalized": float(stat_penalized_mean),
                "stat.std_per_ngram_penalized": float(stat_penalized_std),
                "direction": dir_name,
                "objective.id": self._objective_id(stat_name, variant, W, n_set, dir_name, se_name),
                "objective.label": self._objective_label(stat_name, variant, W, n_set, dir_name, se_name),
                "ecdf.asset_id": ecdf_asset_id,
                "ecdf.asset_fingerprint": ecdf_fp,
                "ecdf.disk_dtype": "float64",
                "ecdf.canonical_dtype": "float64",
                "ecdf.compute_dtype": ecdf_interp_dtype,
                "ecdf.meta_hash": ecdf_fp,
                "ecdf.interp": "linear",
                "ecdf.interp_dtype": ecdf_interp_dtype,
                "ecdf.clamp_min": float(self._ecdf_clamp_min),
                "ecdf.clamp_max": float(self._ecdf_clamp_max),
            },
            objective_stats=objective,
        )
        if self._diagnostics_enabled and meta_json_list:
            self._stash_stats(**{"ecdf.meta_json": meta_json_list})

        return float(score_mean)

    def supports_raw(self) -> bool:
        return True

    def score_with_raw(
        self,
        plaintext: Iterable[int],
        wli_windows: Iterable[Tuple[int, int]] | None = None,
    ) -> Tuple[float, float]:
        pct = float(self.score(plaintext, wli_windows))
        stats = self.last_stats() if hasattr(self, "last_stats") else {}
        raw = stats.get("stat.mean_per_ngram_penalized", pct) if isinstance(stats, dict) else pct
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
        W = int(self.objective.win)
        stride = int(self._stride)

        wli = None
        if wli_windows is not None and self.use_word_breaks:
            wli = self._get_wli_array(wli_windows)

        models = self._active_models()
        n_set = sorted({int(n) for _, n, _ in models})

        pt_w_map, wli_w_map, L_n_full, nwin, tags_injected = self._build_aligned_windows(
            pt, wli, n_set=n_set, W=W, stride=stride
        )
        L_max = max(L_n_full.values()) if L_n_full else 0

        dir_name = BaseScorer._dir_name(self.direction)
        se_name = BaseScorer._se_name(self.se_mode)
        wise = (se_name == "wise")
        stat_name = stat.value
        variant = "mean_per_ngram_interior" if wise else "mean_per_ngram_total"
        total_eval = (W + 2) if wise else W
        interior_eval = W if wise else W
        scale_interior = (float(total_eval) / float(interior_eval)) if wise else 1.0

        if nwin == 0:
            self._stash_stats(
                dtype=self._dtype,
                impl="numpy",
                device=self._device_str,
                score_mean=0.0,
                score_std=0.0,
                n_windows=0,
                **{
                    "window.win_ngrams": int(W),
                    "window.se_mode": se_name,
                    "window.n_set": list(n_set),
                    "window.stride_runes": int(stride),
                    "window.L_n": L_n_full,
                    "window.L_max": int(L_max),
                    "window.n_windows": 0,
                    "window.tags_injected": bool(tags_injected),
                    "stat.name": stat_name,
                    "stat.variant": variant,
                    "stat.ngrams_total": int(total_eval),
                    **({"stat.ngrams_interior": int(interior_eval)} if wise else {}),
                    "direction": dir_name,
                    "objective.id": self._objective_id(stat_name, variant, W, n_set, dir_name, se_name),
                    "objective.label": self._objective_label(stat_name, variant, W, n_set, dir_name, se_name),
                },
                objective_stats={
                    f"{stat_name}_mean_per_ngram_total": 0.0,
                    f"{stat_name}_mean_per_ngram_interior": 0.0,
                    f"{stat_name}_mean_per_ngram_penalized": 0.0,
                    "penalty_hamming": 0.0,
                    "components": {},
                    "windows": {},
                    "n_windows": 0,
                    "score_mean": 0.0,
                },
            )
            return 0.0

        stat_total_perwin = np.zeros((nwin,), dtype=np.float32)
        stat_interior_perwin = np.zeros((nwin,), dtype=np.float32)
        components: Dict[str, Dict[str, float]] = {}

        for ch, n, w in models:
            pt_w = pt_w_map.get(int(n))
            if pt_w is None or pt_w.shape[0] == 0:
                continue
            if ch is Channel.CHAR:
                logp_a, zsum_a, madsum_a = self._rt._score_batch_char(dir_name, se_name, int(n), pt_w)
                label = f"char_n{int(n)}"
            else:
                if wli_w_map is None or wli_w_map.get(int(n)) is None:
                    continue
                wli_w = wli_w_map[int(n)]
                logp_a, zsum_a, madsum_a = self._rt._score_batch_wli(dir_name, se_name, int(n), pt_w, wli_w)
                label = f"wli_n{int(n)}"

            if stat is Stat.ZSUM:
                avg_total = zsum_a
            elif stat is Stat.MADSUM:
                avg_total = madsum_a
            else:
                avg_total = logp_a

            avg_interior = avg_total * np.float32(scale_interior)
            stat_total_perwin += np.float32(w) * np.asarray(avg_total, dtype=np.float32)
            stat_interior_perwin += np.float32(w) * np.asarray(avg_interior, dtype=np.float32)
            components[label] = {
                f"{stat_name}_mean_per_ngram_total": float(np.mean(avg_total, dtype=np.float64)),
                f"{stat_name}_mean_per_ngram_interior": float(np.mean(avg_interior, dtype=np.float64)),
            }

        stat_total_mean = float(np.mean(stat_total_perwin, dtype=np.float64))
        stat_total_std = float(np.std(stat_total_perwin, dtype=np.float64))
        stat_interior_mean = float(np.mean(stat_interior_perwin, dtype=np.float64))
        stat_interior_std = float(np.std(stat_interior_perwin, dtype=np.float64))
        stat_variant_mean = stat_interior_mean if wise else stat_total_mean
        stat_variant_std = stat_interior_std if wise else stat_total_std

        hamming_total = None
        hamming_avg = None
        penalty_hamming = 0.0
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
                penalty_hamming = float(-self._hamming_weight * hamming_avg)
            except Exception:
                hamming_total = None
                hamming_avg = None

        stat_penalized_mean = float(stat_variant_mean + penalty_hamming)

        p10 = float(np.percentile(stat_interior_perwin if wise else stat_total_perwin, 10.0))
        p50 = float(np.percentile(stat_interior_perwin if wise else stat_total_perwin, 50.0))
        p90 = float(np.percentile(stat_interior_perwin if wise else stat_total_perwin, 90.0))

        objective = {
            f"{stat_name}_mean_per_ngram_total": stat_total_mean,
            f"{stat_name}_mean_per_ngram_interior": stat_interior_mean,
            f"{stat_name}_mean_per_ngram_penalized": stat_penalized_mean,
            "penalty_hamming": penalty_hamming,
            "components": components,
            "windows": {"p10": p10, "p50": p50, "p90": p90},
            "n_windows": int(nwin),
            "score_mean": stat_penalized_mean,
        }

        self._stash_stats(
            dtype=self._dtype,
            impl="numpy",
            device=self._device_str,
            score_mean=stat_penalized_mean,
            score_std=stat_variant_std,
            n_windows=int(nwin),
            **{
                "window.win_ngrams": int(W),
                "window.se_mode": se_name,
                "window.n_set": list(n_set),
                "window.stride_runes": int(stride),
                "window.L_n": L_n_full,
                "window.L_max": int(L_max),
                "window.n_windows": int(nwin),
                "window.tags_injected": bool(tags_injected),
                "stat.name": stat_name,
                "stat.variant": variant,
                "stat.ngrams_total": int(total_eval),
                **({"stat.ngrams_interior": int(interior_eval)} if wise else {}),
                "stat.mean_per_ngram_total.mean": float(stat_total_mean),
                "stat.mean_per_ngram_total.std": float(stat_total_std),
                "stat.mean_per_ngram_interior.mean": float(stat_interior_mean),
                "stat.mean_per_ngram_interior.std": float(stat_interior_std),
                "stat.mean_per_ngram_penalized": float(stat_penalized_mean),
                "direction": dir_name,
                "objective.id": self._objective_id(stat_name, variant, W, n_set, dir_name, se_name),
                "objective.label": self._objective_label(stat_name, variant, W, n_set, dir_name, se_name),
            },
            hamming_total_hd=(hamming_total if hamming_total is not None else None),
            hamming_avg_hd=(hamming_avg if hamming_avg is not None else None),
            hamming_weight=self._hamming_weight,
            objective_stats=objective,
        )
        return stat_penalized_mean

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
        if self._requires_wli() and wlis is None:
            raise ValueError("WLI is required when use_word_breaks=True and WLI models are active")
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
            raws[i] = np.float32(float(stats.get("stat.mean_per_ngram_penalized", out[i])) if isinstance(stats, dict) else float(out[i]))
            stds[i] = np.float32(float(self.telemetry().get("score_std", 0.0)))

        nwin = 0
        try:
            last = self.last_stats()
            if isinstance(last, dict):
                nwin = int(last.get("n_windows", 0))
        except Exception:
            nwin = 0
        self._stash_stats(
            dtype=self._dtype,
            impl="numpy", device=self._device_str,
            score_mean_batch=out.astype(np.float32).tolist(),
            score_std_batch=stds.astype(np.float32).tolist(),
            **{"stat.mean_per_ngram_penalized_batch": raws.astype(np.float32).tolist()},
            n_windows=int(nwin),
        )
        return out.astype(np.float32, copy=False)

    def batch_score_with_raw(
        self,
        pts: Sequence[Iterable[int]],
        wlis: Sequence[Iterable[Tuple[int, int]]] | Iterable[Tuple[int, int]] | None = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        if self._requires_wli() and wlis is None:
            raise ValueError("WLI is required when use_word_breaks=True and WLI models are active")
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
            raw_i = stats.get("stat.mean_per_ngram_penalized", pct_i) if isinstance(stats, dict) else pct_i
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
                try:
                    n_set = sorted({int(n) for _, n, _ in self._active_models()})
                    W = int(self.objective.win or WIN_FIXED)
                    n_windows = aligned_window_count(
                        length=int(L0),
                        n_set=n_set,
                        W=int(W),
                        se_mode=self.se_mode,
                        stride=int(self._stride),
                    )
                except Exception:
                    n_windows = max(0, int(L0) - int(WIN_FIXED) + 1)
        self._stash_stats(
            dtype=self._dtype,
            impl="numpy",
            device=self._device_str,
            score_mean_batch=out.astype(np.float32).tolist(),
            score_std_batch=stds.astype(np.float32).tolist(),
            **{"stat.mean_per_ngram_penalized_batch": raw.astype(np.float32).tolist()},
            n_windows=int(n_windows),
        )
        return out.astype(np.float32, copy=False), raw.astype(np.float32, copy=False)

    def clear_wli_cache(self) -> None:
        """Manual hook to drop cached WLI conversions/windows between solver runs."""
        self._wli_source_cache.clear()
        self._wli_window_cache.clear()

    def _objective_id(
        self,
        stat_name: str,
        variant: str,
        W: int,
        n_set: Sequence[int],
        direction: str,
        se_mode: str,
    ) -> str:
        fam = getattr(self.objective.family, "value", str(self.objective.family))
        channels = []
        if self.include_char:
            channels.append("char")
        if self.use_word_breaks:
            channels.append("wli")
        ch_part = "_".join(channels) if channels else "none"
        n_part = "n" + "_".join(str(int(n)) for n in n_set)
        return f"{fam}.{stat_name}.{variant}.W{int(W)}.{n_part}.{ch_part}.{direction}.{se_mode}"

    def _objective_label(
        self,
        stat_name: str,
        variant: str,
        W: int,
        n_set: Sequence[int],
        direction: str,
        se_mode: str,
    ) -> str:
        fam = getattr(self.objective.family, "value", str(self.objective.family))
        fam_label = {
            "pct": "Percentile of",
            "energy": "Energy of",
            "avg": "Average",
        }.get(fam, fam)
        variant_label = "interior" if "interior" in variant else "total"
        channels = []
        if self.include_char:
            channels.append("char")
        if self.use_word_breaks:
            channels.append("wli")
        ch_part = "+".join(channels) if channels else "none"
        n_part = ",".join(str(int(n)) for n in n_set)
        return f"{fam_label} {stat_name} per n-gram ({variant_label}), W={int(W)}, n={n_part}, {ch_part}, {direction}, {se_mode}"

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
            return float(self._ecdf_clamp_min)

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

    def _requires_wli(self) -> bool:
        if not self.use_word_breaks:
            return False
        try:
            models = self._active_models()
        except Exception:
            return False
        return any(ch is Channel.WLI for ch, _, _ in models)


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

