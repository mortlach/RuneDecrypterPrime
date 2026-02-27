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
from rune_decrypter_prime.scoring.language_model.language_model_prime_runtime import LmPrimeRuntime, ECDFCache
from rune_decrypter_prime.utils.telemetry import stash as _tstash
from rune_decrypter_prime.scoring.windowing import (
    START_TAG,
    END_TAG,
    span_core_tokens,
    aligned_window_count,
    span_map,
    span_max,
)
from rune_decrypter_prime.core.types import (
    Direction,
    SeMode,
    Channel,
    ObjectiveFamily,
    Stat,
    ObjectiveSpec,
    AvgWindowPolicy,
    ensure_avg_window_policy,
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
    if (arr_i64 < 0).any() or (arr_i64 > 63).any():
        raise ValueError("WLI entries must be <= 63 to match LMPrime WLI encoding")
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
        self._avg_window_policy: AvgWindowPolicy = ensure_avg_window_policy(
            _cfg_get(scorer_cfg, "avg_window_policy", AvgWindowPolicy.FIXED_WIN)
        )

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
        def _dtype_str(value: Any, default: str) -> str:
            if value is None:
                return default
            if hasattr(value, "value"):
                return str(getattr(value, "value")).lower()
            return str(value).lower()
        compute_dt = _dtype_str(_cfg_get(scorer_cfg, "compute_dtype", None), "float32")
        acc_dt = _dtype_str(_cfg_get(scorer_cfg, "acc_dtype", None), "float64")
        out_dt = _dtype_str(_cfg_get(scorer_cfg, "dtype", None), acc_dt)
        if compute_dt not in {"float32", "float64"}:
            compute_dt = "float32"
        if acc_dt not in {"float32", "float64"}:
            acc_dt = "float64"
        if out_dt not in {"float32", "float64"}:
            out_dt = acc_dt
        self._compute_dtype = compute_dt
        self._acc_dtype = np.float64 if acc_dt == "float64" else np.float32
        self._dtype = out_dt
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
            prefer_float32=(self._compute_dtype != "float64"),
        )
        get_cached = getattr(LmPrimeRuntime, "get_cached", None)
        if callable(get_cached):
            self._rt = get_cached(**rt_kwargs)
        else:
            self._rt = LmPrimeRuntime(**rt_kwargs)
        self._ecdf_root = _cfg_get(scorer_cfg, "model_root", None)
        self._ecdf_prefer_float32 = (acc_dt != "float64")
        self._ecdf: ECDFCache | None = None

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

        # Optional span-hamming backend (pure Python dictionary span matcher)
        self._span_hamming_backend = None
        self._span_hamming_assets = None
        self._span_hamming_weight = float(_cfg_get(scorer_cfg, "span_hamming_weight", 0.0) or 0.0)
        self._span_hamming_mode = str(_cfg_get(scorer_cfg, "span_hamming_mode", "off") or "off").strip().lower()
        if self._span_hamming_mode not in {"off", "raw_bonus", "calibrated"}:
            raise ValueError("span_hamming_mode must be one of: off, raw_bonus, calibrated")
        legacy_enabled = bool(_cfg_get(scorer_cfg, "span_hamming_enabled", False) or self._span_hamming_weight != 0.0)
        if self._span_hamming_mode == "off" and legacy_enabled:
            self._span_hamming_mode = "raw_bonus"
        self._span_hamming_enabled = (self._span_hamming_mode != "off")
        self._span_hamming_assets_dir = _cfg_get(scorer_cfg, "span_hamming_assets_dir", None)
        self._span_hamming_bucket_policy = str(
            _cfg_get(scorer_cfg, "span_hamming_bucket_policy", "nearest_smaller_tie") or "nearest_smaller_tie"
        ).strip().lower()
        self._span_hamming_ecdf_clamp_min = _cfg_get(scorer_cfg, "span_hamming_ecdf_clamp_min", None)
        self._span_hamming_ecdf_clamp_max = _cfg_get(scorer_cfg, "span_hamming_ecdf_clamp_max", None)
        if self._span_hamming_ecdf_clamp_min is None:
            self._span_hamming_ecdf_clamp_min = float(self._ecdf_clamp_min)
        else:
            self._span_hamming_ecdf_clamp_min = float(self._span_hamming_ecdf_clamp_min)
        if self._span_hamming_ecdf_clamp_max is None:
            self._span_hamming_ecdf_clamp_max = float(self._ecdf_clamp_max)
        else:
            self._span_hamming_ecdf_clamp_max = float(self._span_hamming_ecdf_clamp_max)
        self._span_hamming_coverage_min = float(_cfg_get(scorer_cfg, "span_hamming_coverage_min", 0.0) or 0.0)
        self._span_hamming_quality_min = float(_cfg_get(scorer_cfg, "span_hamming_quality_min", 0.0) or 0.0)
        self._span_hamming_span_pct_min = _cfg_get(scorer_cfg, "span_hamming_span_pct_min", None)
        if self._span_hamming_span_pct_min is not None:
            self._span_hamming_span_pct_min = float(self._span_hamming_span_pct_min)
        self._span_hamming_char_pct_min = _cfg_get(scorer_cfg, "span_hamming_char_pct_min", None)
        if self._span_hamming_char_pct_min is not None:
            self._span_hamming_char_pct_min = float(self._span_hamming_char_pct_min)
        self._span_hamming_combine_mode = str(
            _cfg_get(scorer_cfg, "span_hamming_combine_mode", "min") or "min"
        ).strip().lower()
        if self._span_hamming_combine_mode not in {"min", "weighted_sum"}:
            raise ValueError("span_hamming_combine_mode must be one of: min, weighted_sum")
        self._span_hamming_weight_span = float(_cfg_get(scorer_cfg, "span_hamming_weight_span", 1.0) or 0.0)
        self._span_hamming_weight_char = float(_cfg_get(scorer_cfg, "span_hamming_weight_char", 0.0) or 0.0)
        self._span_hamming_use_char_channel = False
        self._span_hamming_gate_fail_policy = str(
            _cfg_get(scorer_cfg, "span_hamming_gate_fail_policy", "score_floor") or "score_floor"
        ).strip().lower()
        self._span_hamming_gate_score_floor = _cfg_get(scorer_cfg, "span_hamming_gate_score_floor", None)
        if self._span_hamming_gate_score_floor is not None:
            self._span_hamming_gate_score_floor = float(self._span_hamming_gate_score_floor)
        if not (0.0 < self._span_hamming_ecdf_clamp_min < self._span_hamming_ecdf_clamp_max < 1.0):
            raise ValueError("span_hamming_ecdf_clamp_min/max must satisfy 0 < min < max < 1")
        if self._span_hamming_bucket_policy != "nearest_smaller_tie":
            raise ValueError("span_hamming_bucket_policy currently only supports 'nearest_smaller_tie'")
        if self._span_hamming_gate_fail_policy != "score_floor":
            raise ValueError("span_hamming_gate_fail_policy currently only supports 'score_floor'")
        if self._span_hamming_enabled:
            try:
                from rune_decrypter_prime.scoring.span_hamming import (
                    SpanCalibratedAssets,
                    SpanHammingBackend,
                    SpanHammingConfig,
                )

                span_cfg = SpanHammingConfig(
                    len_min=int(_cfg_get(scorer_cfg, "span_hamming_len_min", 3)),
                    len_max=int(_cfg_get(scorer_cfg, "span_hamming_len_max", 14)),
                    max_hd=int(_cfg_get(scorer_cfg, "span_hamming_max_hd", 2)),
                    max_candidates_per_window=int(
                        _cfg_get(scorer_cfg, "span_hamming_max_candidates_per_window", 256)
                    ),
                    max_intervals_considered_per_start=int(
                        _cfg_get(scorer_cfg, "span_hamming_max_intervals_considered_per_start", 4)
                    ),
                    min_quality_threshold=float(
                        _cfg_get(scorer_cfg, "span_hamming_min_quality_threshold", 1e-9)
                    ),
                    debug_return_intervals=bool(
                        _cfg_get(scorer_cfg, "span_hamming_debug_return_intervals", False)
                    ),
                )
                wl_dir = _cfg_get(scorer_cfg, "span_hamming_wordlist_dir", None)
                require_selected = bool(_cfg_get(scorer_cfg, "span_hamming_require_selected", True))
                self._span_hamming_backend = SpanHammingBackend(
                    config=span_cfg,
                    wordlist_dir=wl_dir,
                    require_selected=require_selected,
                )
                if self._span_hamming_mode == "calibrated":
                    fam = self.objective.family
                    if fam not in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
                        raise ValueError(
                            "span_hamming_mode='calibrated' only supports ObjectiveFamily.PCT or ENERGY"
                        )
                    if self._span_hamming_assets_dir is None:
                        raise ValueError(
                            "span_hamming_assets_dir is required when span_hamming_mode='calibrated'"
                        )
                    self._span_hamming_assets = SpanCalibratedAssets.load(self._span_hamming_assets_dir)
                    self._span_hamming_use_char_channel = bool(
                        self._span_hamming_weight_char > 0.0
                        or self._span_hamming_char_pct_min is not None
                    )
                    if self._span_hamming_use_char_channel and not self._calibrated_char_pct_available():
                        raise ValueError(
                            "calibrated span char channel requires char4-only base scorer "
                            "(include_char=True, use_word_breaks=False, char_weights={4:1.0})"
                        )
                    if self._span_hamming_weight_span < 0.0 or self._span_hamming_weight_char < 0.0:
                        raise ValueError("span_hamming_weight_span/char must be >= 0")
                    if self._span_hamming_combine_mode == "weighted_sum":
                        w_span = float(self._span_hamming_weight_span)
                        w_char = float(self._span_hamming_weight_char if self._span_hamming_use_char_channel else 0.0)
                        if (w_span + w_char) <= 0.0:
                            raise ValueError(
                                "weighted_sum combine requires positive total weight "
                                "(span_hamming_weight_span + span_hamming_weight_char)"
                            )
                    if self._span_hamming_gate_score_floor is None:
                        if fam is ObjectiveFamily.ENERGY:
                            self._span_hamming_gate_score_floor = float(
                                -np.log1p(-self._span_hamming_ecdf_clamp_min)
                            )
                        else:
                            self._span_hamming_gate_score_floor = float(self._span_hamming_ecdf_clamp_min)
            except Exception:
                if self._span_hamming_mode == "calibrated":
                    raise
                warnings.warn(
                    "Span-hamming backend unavailable; skipping span-hamming scoring component",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self._span_hamming_backend = None

        # Telemetry invariants
        self._device_str = "cpu"
        win_cfg = int(self.objective.win) if self.objective.win is not None else None
        win_effective: Any = (
            "full_text"
            if (self.objective.family is ObjectiveFamily.AVG and self._avg_window_policy is AvgWindowPolicy.FULL_TEXT)
            else win_cfg
        )
        self._telemetry: Dict[str, Any] = {
            "impl": "numpy",
            "device": self._device_str,
            "compute_dtype": self._compute_dtype,
            "acc_dtype": acc_dt,
            "dtype": self._dtype,
            "encoding_dir": self.direction,
            "avg_window_policy": self._avg_window_policy.value,
            "win_configured": win_cfg,
            "win_effective": win_effective,
            "span_hamming_enabled": bool(
                self._span_hamming_backend is not None
                and (
                    (self._span_hamming_mode == "raw_bonus" and self._span_hamming_weight != 0.0)
                    or self._span_hamming_mode == "calibrated"
                )
            ),
            "span_hamming_mode": self._span_hamming_mode,
            "span_hamming_weight": float(self._span_hamming_weight),
            "span_hamming_combine_mode": self._span_hamming_combine_mode,
            "span_hamming_weight_span": float(self._span_hamming_weight_span),
            "span_hamming_weight_char": float(self._span_hamming_weight_char),
            "span_hamming_use_char_channel": bool(self._span_hamming_use_char_channel),
            "span_hamming_ecdf_clamp_min": float(self._span_hamming_ecdf_clamp_min),
            "span_hamming_ecdf_clamp_max": float(self._span_hamming_ecdf_clamp_max),
            "span_hamming_bucket_policy": self._span_hamming_bucket_policy,
        }
        # Caches for WLI conversions/windows (bounded LRU)
        self._wli_cache_limit = 8
        self._wli_source_cache: "OrderedDict[int, _WliSourceCacheEntry]" = OrderedDict()
        self._wli_window_cache: "OrderedDict[Tuple[int, int], _WliWindowCacheEntry]" = OrderedDict()
        self._diagnostics_enabled: bool = bool(_cfg_get(scorer_cfg, "diagnostics_enabled", False))

    def _ensure_ecdf(self) -> ECDFCache:
        if self._ecdf is None:
            self._ecdf = ECDFCache(self._ecdf_root, prefer_float32=self._ecdf_prefer_float32)
        return self._ecdf

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

    def _calibrated_char_pct_available(self) -> bool:
        try:
            models = self._active_models()
        except Exception:
            return False
        if len(models) != 1:
            return False
        ch, n, w = models[0]
        return (ch is Channel.CHAR) and (int(n) == 4) and (abs(float(w) - 1.0) <= 1e-9)

    def _score_base_channel_pct(self, pt: np.ndarray, wli_windows: Iterable[Tuple[int, int]] | None) -> tuple[float, float]:
        prev_mode = self._span_hamming_mode
        prev_enabled = self._span_hamming_enabled
        self._span_hamming_mode = "off"
        self._span_hamming_enabled = False
        try:
            base_score = float(self.score(pt, wli_windows))
        finally:
            self._span_hamming_mode = prev_mode
            self._span_hamming_enabled = prev_enabled
        fam = self.objective.family
        if fam is ObjectiveFamily.ENERGY:
            base_pct = float(-np.expm1(-base_score))
        else:
            base_pct = float(base_score)
        base_pct = float(np.clip(base_pct, self._ecdf_clamp_min, self._ecdf_clamp_max))
        return base_pct, base_score

    def _score_span_hamming_calibrated(
        self,
        pt: np.ndarray,
        wli_windows: Iterable[Tuple[int, int]] | None,
    ) -> float:
        backend = self._span_hamming_backend
        assets = self._span_hamming_assets
        if backend is None or assets is None:
            raise ValueError("Calibrated span mode requires loaded span backend and assets")
        try:
            span_stats = backend.score(pt.tolist())
            span_raw = float(span_stats.span_raw)
            span_cov = float(span_stats.coverage)
            span_q = float(span_stats.quality)
            span_bins = tuple(int(v) for v in getattr(span_stats, "length_bins", ()))
            span_raw_by_len = tuple(float(v) for v in getattr(span_stats, "span_raw_by_len", ()))
            span_cov_by_len = tuple(float(v) for v in getattr(span_stats, "coverage_by_len", ()))
            span_q_by_len = tuple(float(v) for v in getattr(span_stats, "quality_by_len", ()))
        except Exception as exc:
            raise ValueError(f"Span backend failed in calibrated mode: {exc}") from exc

        bucket = assets.score_span_raw(
            direction=BaseScorer._dir_name(self.direction),
            text_length=int(pt.shape[0]),
            span_raw=span_raw,
            clamp_min=float(self._span_hamming_ecdf_clamp_min),
            clamp_max=float(self._span_hamming_ecdf_clamp_max),
        )

        gate_reasons: list[str] = []
        if span_cov < float(self._span_hamming_coverage_min):
            gate_reasons.append("coverage_below_min")
        if span_q < float(self._span_hamming_quality_min):
            gate_reasons.append("quality_below_min")
        if self._span_hamming_span_pct_min is not None and bucket.span_pct < float(self._span_hamming_span_pct_min):
            gate_reasons.append("span_pct_below_min")
        char_pct: float | None = None
        char_score: float | None = None
        if self._span_hamming_use_char_channel:
            char_pct, char_score = self._score_base_channel_pct(pt=pt, wli_windows=wli_windows)
            if self._span_hamming_char_pct_min is not None and char_pct < float(self._span_hamming_char_pct_min):
                gate_reasons.append("char_pct_below_min")
        gate_failed = bool(gate_reasons)

        span_pct = float(bucket.span_pct)
        combine_mode = str(self._span_hamming_combine_mode)
        if char_pct is None:
            combined_pct = span_pct
        elif combine_mode == "min":
            combined_pct = min(span_pct, char_pct)
        else:
            w_span = float(self._span_hamming_weight_span)
            w_char = float(self._span_hamming_weight_char)
            w_total = w_span + w_char
            if w_total <= 0.0:
                raise ValueError(
                    "weighted_sum combine requires positive total weight "
                    "(span_hamming_weight_span + span_hamming_weight_char)"
                )
            combined_pct = ((w_span * span_pct) + (w_char * char_pct)) / w_total
        combined_pct = float(
            np.clip(
                combined_pct,
                float(self._span_hamming_ecdf_clamp_min),
                float(self._span_hamming_ecdf_clamp_max),
            )
        )
        combined_energy = float(-np.log1p(-combined_pct))

        fam = self.objective.family
        if gate_failed:
            score = float(self._span_hamming_gate_score_floor)
        else:
            score = float(combined_energy if fam is ObjectiveFamily.ENERGY else combined_pct)

        objective_stats = {
            "score_mean": float(score),
            "score_std": 0.0,
            "n_windows": 1,
            "span_raw": float(span_raw),
            "span_coverage": float(span_cov),
            "span_quality": float(span_q),
            "span_x": float(bucket.x_span),
            "span_pct": float(bucket.span_pct),
            "span_energy": float(bucket.span_energy),
            "char_pct": (None if char_pct is None else float(char_pct)),
            "char_score": (None if char_score is None else float(char_score)),
            "combine_mode": combine_mode,
            "combined_pct": float(combined_pct),
            "combined_energy": float(combined_energy),
            "span_bucket_length": int(bucket.length_bucket),
            "span_bucket_direction": str(bucket.direction),
            "gate_failed": bool(gate_failed),
            "gate_reasons": list(gate_reasons),
        }
        self._stash_stats(
            dtype=self._dtype,
            impl="numpy",
            device=self._device_str,
            score_mean=float(score),
            score_std=0.0,
            n_windows=1,
            objective_stats=objective_stats,
            **{
                "stat.name": "x_span",
                "stat.variant": "span_full_text",
                "stat.mean_per_ngram_penalized": float(span_raw),
            },
            span_hamming_mode="calibrated",
            span_hamming_combine_mode=combine_mode,
            span_hamming_weight_span=float(self._span_hamming_weight_span),
            span_hamming_weight_char=float(self._span_hamming_weight_char),
            span_hamming_use_char_channel=bool(self._span_hamming_use_char_channel),
            span_hamming_raw=float(span_raw),
            span_hamming_coverage=float(span_cov),
            span_hamming_quality=float(span_q),
            span_hamming_length_bins=span_bins,
            span_hamming_raw_by_len=span_raw_by_len,
            span_hamming_coverage_by_len=span_cov_by_len,
            span_hamming_quality_by_len=span_q_by_len,
            span_hamming_x=float(bucket.x_span),
            span_hamming_pct=float(bucket.span_pct),
            span_hamming_energy=float(bucket.span_energy),
            span_hamming_char_pct=(None if char_pct is None else float(char_pct)),
            span_hamming_char_score=(None if char_score is None else float(char_score)),
            span_hamming_combined_pct=float(combined_pct),
            span_hamming_combined_energy=float(combined_energy),
            span_hamming_bucket_length=int(bucket.length_bucket),
            span_hamming_gate_failed=bool(gate_failed),
            span_hamming_gate_reasons=list(gate_reasons),
            span_hamming_gate_score_floor=float(self._span_hamming_gate_score_floor),
        )
        return float(score)

    def _apply_span_hamming_bonus(self, base_score: float, pt: np.ndarray) -> float:
        """
        Optionally augment final score with weighted span-hamming signal.
        """
        if self._span_hamming_mode != "raw_bonus":
            return float(base_score)
        backend = self._span_hamming_backend
        weight = float(self._span_hamming_weight)
        if backend is None or weight == 0.0:
            return float(base_score)
        try:
            span_stats = backend.score(pt.tolist())
            span_raw = float(span_stats.span_raw)
            span_cov = float(span_stats.coverage)
            span_q = float(span_stats.quality)
            span_bins = tuple(int(v) for v in getattr(span_stats, "length_bins", ()))
            span_raw_by_len = tuple(float(v) for v in getattr(span_stats, "span_raw_by_len", ()))
            span_cov_by_len = tuple(float(v) for v in getattr(span_stats, "coverage_by_len", ()))
            span_q_by_len = tuple(float(v) for v in getattr(span_stats, "quality_by_len", ()))
        except Exception:
            return float(base_score)

        bonus = float(weight * span_raw)
        out = float(base_score + bonus)
        stats = self.__dict__.setdefault("_last_stats", {})
        if isinstance(stats, dict):
            stats["span_hamming_raw"] = span_raw
            stats["span_hamming_coverage"] = span_cov
            stats["span_hamming_quality"] = span_q
            stats["span_hamming_length_bins"] = span_bins
            stats["span_hamming_raw_by_len"] = span_raw_by_len
            stats["span_hamming_coverage_by_len"] = span_cov_by_len
            stats["span_hamming_quality_by_len"] = span_q_by_len
            stats["span_hamming_bonus"] = bonus
            stats["span_hamming_weight"] = weight
            stats["score_mean_base"] = float(base_score)
            stats["score_mean"] = out
            if "stat.mean_per_ngram_penalized" in stats:
                stats["stat.mean_per_ngram_penalized"] = float(stats["stat.mean_per_ngram_penalized"]) + bonus
            obj = stats.get("objective_stats")
            if isinstance(obj, dict):
                obj["span_hamming_raw"] = span_raw
                obj["span_hamming_coverage"] = span_cov
                obj["span_hamming_quality"] = span_q
                obj["span_hamming_length_bins"] = span_bins
                obj["span_hamming_raw_by_len"] = span_raw_by_len
                obj["span_hamming_coverage_by_len"] = span_cov_by_len
                obj["span_hamming_quality_by_len"] = span_q_by_len
                obj["span_hamming_bonus"] = bonus
                obj["span_hamming_weight"] = weight
                if "score_mean" in obj:
                    obj["score_mean"] = float(obj["score_mean"]) + bonus
                if "logp_mean_per_ngram_penalized" in obj:
                    obj["logp_mean_per_ngram_penalized"] = float(obj["logp_mean_per_ngram_penalized"]) + bonus
                stat_name = stats.get("stat.name")
                if isinstance(stat_name, str):
                    key = f"{stat_name}_mean_per_ngram_penalized"
                    if key in obj:
                        obj[key] = float(obj[key]) + bonus
        _tstash(
            self._telemetry,
            span_hamming_raw=span_raw,
            span_hamming_coverage=span_cov,
            span_hamming_quality=span_q,
            span_hamming_length_bins=span_bins,
            span_hamming_raw_by_len=span_raw_by_len,
            span_hamming_coverage_by_len=span_cov_by_len,
            span_hamming_quality_by_len=span_q_by_len,
            span_hamming_bonus=bonus,
            span_hamming_weight=weight,
            score_mean=out,
            score_mean_base=float(base_score),
        )
        return out

    # ---------------------------- public API ----------------------------
    def score(self, plaintext: Iterable[int], wli_windows: Iterable[Tuple[int, int]] | None = None) -> float:
        fam = self.objective.family
        stat = self.objective.stat
        pt_single = _to_u8_1d(plaintext)

        if self._span_hamming_mode == "calibrated":
            if fam not in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
                raise ValueError(
                    "span_hamming_mode='calibrated' only supports ObjectiveFamily.PCT or ENERGY"
                )
            return self._score_span_hamming_calibrated(pt_single, wli_windows)

        want_energy = fam is ObjectiveFamily.ENERGY

        if self._requires_wli() and wli_windows is None:
            raise ValueError("WLI is required when use_word_breaks=True and WLI models are active")

        if fam is ObjectiveFamily.NEGLOGP:
            warnings.warn("Using legacy objective; consider migrating to PCT.*", DeprecationWarning, stacklevel=2)
            out = float(self._score_legacy_scalar(pt_single, wli_windows))
            self._stash_stats(
                dtype=self._dtype,
                impl="numpy", device=self._device_str,
                legacy_objective=True, score_mean=out, score_std=0.0, n_windows=1,
            )
            return self._apply_span_hamming_bonus(out, pt_single)
        if fam is ObjectiveFamily.AVG:
            out = float(self._score_raw_avg(pt_single, wli_windows))
            return self._apply_span_hamming_bonus(out, pt_single)

        if fam not in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
            raise ValueError(f"Unsupported objective family: {fam}")
        if stat is None:
            raise ValueError("ObjectiveSpec.stat is required for PCT/ENERGY")
        ecdf = self._ensure_ecdf()

        pt = _to_u8_1d(plaintext)
        W = int(self.objective.win or WIN_FIXED)
        stride = int(self._stride)
        acc_dtype = self._acc_dtype

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
            energy_floor = float(ecdf.energy(np.asarray([pct_floor], dtype=acc_dtype))[0])
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
                    "window.win_configured": int(W),
                    "window.win_effective": int(W),
                    "window.win_ignored": False,
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
                    "avg_window_policy": self._avg_window_policy.value,
                    "objective.id": self._objective_id(stat_name, variant, W, n_set, dir_name, se_name),
                    "objective.label": self._objective_label(stat_name, variant, W, n_set, dir_name, se_name),
                },
                hamming_total_hd=(hamming_total if hamming_total is not None else None),
                hamming_avg_hd=(hamming_avg if hamming_avg is not None else None),
                hamming_weight=self._hamming_weight,
                objective_stats=objective,
            )
            return self._apply_span_hamming_bonus(float(score_mean), pt)

        pct_perwin = np.zeros((nwin,), dtype=acc_dtype)
        stat_total_perwin = np.zeros((nwin,), dtype=acc_dtype)
        stat_interior_perwin = np.zeros((nwin,), dtype=acc_dtype)
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

            avg_total = np.asarray(avg_total, dtype=acc_dtype)
            avg_interior = avg_total * acc_dtype(scale_interior)
            stat_total_perwin += acc_dtype(w) * avg_total
            stat_interior_perwin += acc_dtype(w) * avg_interior

            stat_variant = avg_interior if wise else avg_total

            # ECDF lookup for chosen variant
            ecdf.validate_clamp_range(
                model=model_name,
                mode=dir_name,
                pos=se_name,
                n=int(n),
                stat=stat_name,
                win=int(W),
                clamp_min=self._ecdf_clamp_min,
                clamp_max=self._ecdf_clamp_max,
            )
            grid, q = ecdf.load(model=model_name, mode=dir_name, pos=se_name, n=int(n), stat=stat_name, win=int(W))
            u = ecdf.interp_percentile(grid, q, np.asarray(stat_variant, dtype=acc_dtype))
            u = np.clip(u, acc_dtype(self._ecdf_clamp_min), acc_dtype(self._ecdf_clamp_max))
            pct_perwin += acc_dtype(w) * u

            components[label] = {
                f"{stat_name}_mean_per_ngram_total": float(np.mean(avg_total, dtype=np.float64)),
                f"{stat_name}_mean_per_ngram_interior": float(np.mean(avg_interior, dtype=np.float64)),
                f"pct_{stat_name}_{variant}": float(np.mean(u, dtype=np.float64)),
            }

            asset_ids.append(ecdf.asset_id(model=model_name, mode=dir_name, pos=se_name, n=int(n), stat=stat_name, win=int(W)))
            asset_fps.append(ecdf.meta_hash(model=model_name, mode=dir_name, pos=se_name, n=int(n), stat=stat_name, win=int(W)))
            interp_dtypes.append(ecdf.interp_dtype(model=model_name, mode=dir_name, pos=se_name, n=int(n), stat=stat_name, win=int(W)))
            if self._diagnostics_enabled:
                try:
                    import json as _json
                    meta = ecdf.meta(model=model_name, mode=dir_name, pos=se_name, n=int(n), stat=stat_name, win=int(W))
                    meta_json_list.append(_json.dumps(meta, sort_keys=True))
                except Exception:
                    pass

        pct_mean = float(np.mean(pct_perwin, dtype=np.float64))
        pct_std = float(np.std(pct_perwin, dtype=np.float64))
        energy_perwin = ecdf.energy(pct_perwin)
        energy_mean = float(np.mean(energy_perwin, dtype=np.float64))
        energy_std = float(np.std(energy_perwin, dtype=np.float64))

        score_mean = energy_mean if want_energy else pct_mean
        if not want_energy:
            score_mean = float(np.clip(score_mean, self._ecdf_clamp_min, self._ecdf_clamp_max))
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
                "window.win_configured": int(W),
                "window.win_effective": int(W),
                "window.win_ignored": False,
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

        return self._apply_span_hamming_bonus(float(score_mean), pt)

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
        if self._avg_window_policy is AvgWindowPolicy.FULL_TEXT:
            return self._score_raw_avg_full_text(plaintext, wli_windows)

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

        acc_dtype = self._acc_dtype
        stat_total_perwin = np.zeros((nwin,), dtype=acc_dtype)
        stat_interior_perwin = np.zeros((nwin,), dtype=acc_dtype)
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

            avg_total = np.asarray(avg_total, dtype=acc_dtype)
            avg_interior = avg_total * acc_dtype(scale_interior)
            stat_total_perwin += acc_dtype(w) * avg_total
            stat_interior_perwin += acc_dtype(w) * avg_interior
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
                "avg_window_policy": self._avg_window_policy.value,
                "objective.id": self._objective_id(stat_name, variant, W, n_set, dir_name, se_name),
                "objective.label": self._objective_label(stat_name, variant, W, n_set, dir_name, se_name),
            },
            hamming_total_hd=(hamming_total if hamming_total is not None else None),
            hamming_avg_hd=(hamming_avg if hamming_avg is not None else None),
            hamming_weight=self._hamming_weight,
            objective_stats=objective,
        )
        return stat_penalized_mean

    def _score_raw_avg_full_text(
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

        wli = None
        if wli_windows is not None and self.use_word_breaks:
            wli = self._get_wli_array(wli_windows)

        models = self._active_models()
        dir_name = BaseScorer._dir_name(self.direction)
        se_name = BaseScorer._se_name(self.se_mode)
        wise = (se_name == "wise")
        stat_name = stat.value
        variant = "mean_per_ngram_interior" if wise else "mean_per_ngram_total"

        if wise:
            pt_full = np.empty((1, pt.shape[0] + 2), dtype=np.uint8)
            pt_full[:, 0] = START_TAG
            pt_full[:, -1] = END_TAG
            pt_full[:, 1:-1] = pt
            if wli is not None:
                wli_full = np.zeros((1, wli.shape[0] + 2, 2), dtype=np.uint8)
                wli_full[:, 1:-1, :] = wli
            else:
                wli_full = None
            tags_injected = True
        else:
            pt_full = np.ascontiguousarray(pt.reshape(1, -1), dtype=np.uint8)
            wli_full = (
                np.ascontiguousarray(wli.reshape(1, wli.shape[0], 2), dtype=np.uint8)
                if wli is not None
                else None
            )
            tags_injected = False

        valid: List[Tuple[Channel, int, float, int]] = []
        skipped_short: Dict[str, int] = {}
        L_full = int(pt_full.shape[1])
        for ch, n, w in models:
            ngrams = int(L_full - int(n) + 1)
            if ngrams <= 0:
                key = f"{ch.value}_n{int(n)}"
                skipped_short[key] = int(ngrams)
                continue
            valid.append((ch, int(n), float(w), int(ngrams)))

        if not valid:
            n_set = sorted({int(n) for _, n, _, _ in valid})
            self._stash_stats(
                dtype=self._dtype,
                impl="numpy",
                device=self._device_str,
                score_mean=0.0,
                score_std=0.0,
                n_windows=0,
                **{
                    "window.win_ngrams": int(W),
                    "window.win_configured": int(W),
                    "window.win_effective": "full_text",
                    "window.win_ignored": True,
                    "window.se_mode": se_name,
                    "window.n_set": list(n_set),
                    "window.stride_runes": int(self._stride),
                    "window.L_n": {},
                    "window.L_max": int(L_full),
                    "window.n_windows": 0,
                    "window.tags_injected": bool(tags_injected),
                    "stat.name": stat_name,
                    "stat.variant": variant,
                    "stat.ngrams_total": 0,
                    "stat.ngrams_total_by_model": {},
                    "direction": dir_name,
                    "avg_window_policy": self._avg_window_policy.value,
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
                    "skipped_short_models": skipped_short,
                },
            )
            return 0.0

        total_w = float(sum(w for _, _, w, _ in valid))
        valid = [(ch, n, (w / total_w), ngrams) for ch, n, w, ngrams in valid]
        n_set = sorted({int(n) for _, n, _, _ in valid})

        acc_dtype = self._acc_dtype
        stat_total_mean = acc_dtype(0.0)
        stat_interior_mean = acc_dtype(0.0)
        components: Dict[str, Dict[str, float]] = {}
        ngrams_by_model: Dict[str, int] = {}

        for ch, n, w_norm, ngrams in valid:
            if ch is Channel.CHAR:
                logp_a, zsum_a, madsum_a = self._rt._score_batch_char(dir_name, se_name, int(n), pt_full)
                label = f"char_n{int(n)}"
            else:
                if wli_full is None:
                    continue
                logp_a, zsum_a, madsum_a = self._rt._score_batch_wli(dir_name, se_name, int(n), pt_full, wli_full)
                label = f"wli_n{int(n)}"

            if stat is Stat.ZSUM:
                avg_total_arr = zsum_a
            elif stat is Stat.MADSUM:
                avg_total_arr = madsum_a
            else:
                avg_total_arr = logp_a

            avg_total = float(np.asarray(avg_total_arr, dtype=np.float64).reshape(-1)[0])
            avg_interior = avg_total
            stat_total_mean += acc_dtype(w_norm * avg_total)
            stat_interior_mean += acc_dtype(w_norm * avg_interior)
            ngrams_by_model[label] = int(ngrams)
            components[label] = {
                f"{stat_name}_mean_per_ngram_total": float(avg_total),
                f"{stat_name}_mean_per_ngram_interior": float(avg_interior),
                "ngram_count": int(ngrams),
                "weight": float(w_norm),
            }

        stat_total_mean_f = float(stat_total_mean)
        stat_interior_mean_f = float(stat_interior_mean)
        stat_variant_mean = stat_interior_mean_f if wise else stat_total_mean_f
        stat_variant_std = 0.0

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
        ngrams_ref = int(max(ngrams_by_model.values()) if ngrams_by_model else 0)

        objective = {
            f"{stat_name}_mean_per_ngram_total": float(stat_total_mean_f),
            f"{stat_name}_mean_per_ngram_interior": float(stat_interior_mean_f),
            f"{stat_name}_mean_per_ngram_penalized": float(stat_penalized_mean),
            "penalty_hamming": float(penalty_hamming),
            "components": components,
            "windows": {"p10": float(stat_variant_mean), "p50": float(stat_variant_mean), "p90": float(stat_variant_mean)},
            "n_windows": 1,
            "score_mean": float(stat_penalized_mean),
            "skipped_short_models": skipped_short,
        }

        self._stash_stats(
            dtype=self._dtype,
            impl="numpy",
            device=self._device_str,
            score_mean=float(stat_penalized_mean),
            score_std=float(stat_variant_std),
            n_windows=1,
            **{
                "window.win_ngrams": int(W),
                "window.win_configured": int(W),
                "window.win_effective": "full_text",
                "window.win_ignored": True,
                "window.se_mode": se_name,
                "window.n_set": list(n_set),
                "window.stride_runes": int(self._stride),
                "window.L_n": {int(n): int(L_full) for _, n, _, _ in valid},
                "window.L_max": int(L_full),
                "window.n_windows": 1,
                "window.tags_injected": bool(tags_injected),
                "stat.name": stat_name,
                "stat.variant": variant,
                "stat.ngrams_total": int(ngrams_ref),
                "stat.ngrams_total_by_model": {k: int(v) for k, v in ngrams_by_model.items()},
                "stat.mean_per_ngram_total.mean": float(stat_total_mean_f),
                "stat.mean_per_ngram_total.std": 0.0,
                "stat.mean_per_ngram_interior.mean": float(stat_interior_mean_f),
                "stat.mean_per_ngram_interior.std": 0.0,
                "stat.mean_per_ngram_penalized": float(stat_penalized_mean),
                "direction": dir_name,
                "avg_window_policy": self._avg_window_policy.value,
                "objective.id": self._objective_id(stat_name, variant, W, n_set, dir_name, se_name),
                "objective.label": self._objective_label(stat_name, variant, W, n_set, dir_name, se_name),
            },
            hamming_total_hd=(hamming_total if hamming_total is not None else None),
            hamming_avg_hd=(hamming_avg if hamming_avg is not None else None),
            hamming_weight=self._hamming_weight,
            objective_stats=objective,
        )
        return float(stat_penalized_mean)

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

        out = np.zeros((len(pts),), dtype=np.float64)
        stds = np.zeros_like(out)
        raws = np.zeros_like(out)
        for i, pt in enumerate(materialised_pts):
            wli_i = wli_single if wli_single is not None else (wli_list[i] if wli_list is not None else None)
            out[i] = float(self.score(pt, wli_i))
            stats = self.last_stats()
            raws[i] = float(stats.get("stat.mean_per_ngram_penalized", out[i])) if isinstance(stats, dict) else float(out[i])
            stds[i] = float(self.telemetry().get("score_std", 0.0))

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
            score_mean_batch=out.tolist(),
            score_std_batch=stds.tolist(),
            **{"stat.mean_per_ngram_penalized_batch": raws.tolist()},
            n_windows=int(nwin),
        )
        return out

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
        out = np.zeros((len(pts_seq),), dtype=np.float64)
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
            out[i] = float(pct_i)
            raw[i] = float(raw_i)
            stds[i] = float(self.telemetry().get("score_std", 0.0))
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
            score_mean_batch=out.tolist(),
            score_std_batch=stds.tolist(),
            **{"stat.mean_per_ngram_penalized_batch": raw.tolist()},
            n_windows=int(n_windows),
        )
        return out, raw

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
        return float(-np.asarray(bucket_out["avg"]["logp"], dtype=np.float64)[0])
    if fam is ObjectiveFamily.AVG:
        if stat not in (Stat.LOGP, Stat.ZSUM, Stat.MADSUM):
            raise ValueError(f"unknown avg stat: {stat}")
        return float(np.asarray(bucket_out["avg"][stat.value], dtype=np.float64)[0])
    # Fallback: try pct.logp scalar if present
    try:
        return float(np.asarray(bucket_out["pct"]["logp"], dtype=np.float64)[0])
    except Exception as e:
        raise ValueError(f"unsupported legacy objective: {fam}.{stat}") from e

