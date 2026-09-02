# ============================================================
# rdp/scoring/rune_scorer.py   (NumPy scorer)
# CPU implementation of the normalised objective using Enums at the API.
# Public name/signature preserved: class RuneScorer(BaseScorer)
# ============================================================
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Dict, Any, Optional, Tuple
import numpy as np
import time
import warnings

from rdp.scoring.base_scorer import BaseScorer, WIN_FIXED
from rdp.scoring.objective_normalize import (
    normalize_objective_input as _normalize_objective,
)
from rdp.scoring.language_model.language_model_prime_runtime import LmPrimeRuntime, ECDFCache
from rdp.core.config.cipher import CipherConfig
from rdp.core.config.scoring import (
    HammingTextDirectionMode,
    ScoringConfig,
    SpanHammingBucketPolicy,
    SpanHammingCombineMode,
    SpanHammingGateFailurePolicy,
    SpanHammingLanguageModelProfileSource,
    SpanHammingMode,
    ensure_hamming_text_direction_mode,
    ensure_span_hamming_bucket_policy,
    ensure_span_hamming_combine_mode,
    ensure_span_hamming_gate_failure_policy,
    ensure_span_hamming_language_model_profile_source,
    ensure_span_hamming_mode,
)
from rdp.telemetry.scoring import stash as _tstash
from rdp.scoring.windowing import (
    START_TAG,
    END_TAG,
    span_core_tokens,
    aligned_window_count,
    span_map,
)
from rdp.core.types import (
    Direction,
    SeMode,
    Channel,
    ObjectiveFamily,
    Stat,
    ObjectiveSpec,
    AvgWindowPolicy,
    ensure_direction,
    ensure_avg_window_policy,
)


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

    def __init__(self, cfg_cipher: CipherConfig, scorer_cfg: ScoringConfig) -> None:
        if not isinstance(cfg_cipher, CipherConfig):
            raise TypeError(f"cfg_cipher must be CipherConfig, got {type(cfg_cipher).__name__}")
        if not isinstance(scorer_cfg, ScoringConfig):
            raise TypeError(f"scorer_cfg must be ScoringConfig, got {type(scorer_cfg).__name__}")

        # Required enums
        self.direction: Direction = ensure_direction(cfg_cipher.encoding_dir)
        self.se_mode: SeMode = SeMode.NOSE
        self.objective: ObjectiveSpec = _normalize_objective(
            scorer_cfg.objective,
            default_win=int(scorer_cfg.window_size or WIN_FIXED),
        )
        if self.se_mode is SeMode.WISE:
            raise ValueError("WISE mode is not supported yet; use NOSE.")
        if self.objective.family in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
            if self.objective.win is None:
                legacy_win = scorer_cfg.window_size
                self.objective = ObjectiveSpec(
                    family=ObjectiveFamily.PCT,
                    stat=self.objective.stat,
                    win=int(legacy_win),
                )
            if int(self.objective.win) != int(WIN_FIXED):
                raise ValueError("pct/energy objectives only support win=10 in the current LM tables.")
        self._avg_window_policy: AvgWindowPolicy = ensure_avg_window_policy(
            scorer_cfg.average_window_policy.value.replace("window", "win")
        )

        # Channels
        self.include_char: bool = bool(scorer_cfg.character_lane_enabled)
        self.use_word_breaks: bool = bool(scorer_cfg.word_length_lane_enabled)

        # ECDF clamps / dtype
        self._ecdf_clamp_min: float = float(scorer_cfg.ecdf_clamp_minimum)
        self._ecdf_clamp_max: float = float(scorer_cfg.ecdf_clamp_maximum)
        def _dtype_str(value: Any, default: str) -> str:
            if value is None:
                return default
            if hasattr(value, "value"):
                return str(getattr(value, "value")).lower()
            return str(value).lower()
        compute_dt = _dtype_str(scorer_cfg.compute_dtype, "float32")
        acc_dt = _dtype_str(scorer_cfg.accumulator_dtype, "float64")
        out_dt = acc_dt
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
        self._stride: int = int(scorer_cfg.stride or 1)
        if self._stride <= 0:
            raise ValueError("stride must be >= 1")

        # Model selection — either per-order maps or legacy single-order + pair weights
        self._char_weights: Dict[int, float] | None = scorer_cfg.character_order_weights  # type: ignore[assignment]
        self._wli_weights: Dict[int, float] | None = scorer_cfg.word_length_order_weights  # type: ignore[assignment]
        self._n_char: Optional[int] = scorer_cfg.character_ngram_order
        self._n_wli: Optional[int] = scorer_cfg.word_length_ngram_order
        self._weights_pair: Optional[Tuple[float, float]] = scorer_cfg.base_lane_weights
        self._effective_model_weights = scorer_cfg.effective_lm_model_weights

        # Language-model runtime (LM tables + ECDF cache)
        rt_kwargs = dict(
            root=scorer_cfg.language_model_root,
            smoothing=scorer_cfg.smoothing.value.replace("auto_good_turing", "auto_gt"),
            alpha=float(scorer_cfg.smoothing_alpha or 0.0),
            oov_policy=scorer_cfg.out_of_vocabulary_policy.value.replace("floor_minimum_seen", "floor_min_seen"),
            include_char=self.include_char,
            prefer_float32=(self._compute_dtype != "float64"),
        )
        self._lm_load_reporter = getattr(scorer_cfg, "_lm_load_reporter", None)
        get_cached = getattr(LmPrimeRuntime, "get_cached", None)
        if self._lm_load_reporter is None and callable(get_cached):
            self._rt = get_cached(**rt_kwargs)
        else:
            self._rt = LmPrimeRuntime(**rt_kwargs, load_reporter=self._lm_load_reporter)
        self._ecdf_root = scorer_cfg.language_model_root
        self._ecdf_prefer_float32 = (acc_dt != "float64")
        self._ecdf: ECDFCache | None = None

        # Optional Hamming backend (lazy import; skip if unavailable or disabled)
        self._hamming_backend = None
        raw_hw = scorer_cfg.hamming_weight
        hw_max_default = float(scorer_cfg.hamming_maximum_weight or 0.0)
        if raw_hw is None:
            if bool(scorer_cfg.hamming_enabled):
                self._hamming_weight = hw_max_default
            else:
                self._hamming_weight = 0.0
        else:
            self._hamming_weight = float(raw_hw)
        self._hamming_weight_max: float = float(scorer_cfg.hamming_maximum_weight)
        self._hamming_ramp_start: float = float(scorer_cfg.hamming_ramp_start_fraction or 0.0)
        self._hamming_ramp_end: float = float(scorer_cfg.hamming_ramp_end_fraction or 1.0)
        self._hamming_max_hd: int = int(scorer_cfg.hamming_maximum_distance)
        self._hamming_direction_mode: HammingTextDirectionMode = ensure_hamming_text_direction_mode(scorer_cfg.hamming_text_direction_mode)
        self._hamming_enabled: bool = bool(scorer_cfg.hamming_enabled or self._hamming_weight != 0.0)
        self._hamming_dictionary_policy = scorer_cfg.hamming_dictionary_policy
        self._hamming_dictionary_policy_root = scorer_cfg.hamming_dictionary_root
        self._hamming_wordlist_dir_resolved = None
        self._hamming_length_weights = None
        try:
            lw = scorer_cfg.hamming_length_weights
            if lw:
                self._hamming_length_weights = {int(k): float(v) for k, v in dict(lw).items()}
        except Exception:
            self._hamming_length_weights = None

        if self._hamming_enabled:
            try:
                from rdp.scoring.hamming.dictionary_assets import choose_hamming_dictionary_wordlist_dir
                from rdp.scoring.hamming.loader import load_raw1grams_wordlists
                from rdp.scoring.hamming.backend import HammingBackend

                wl_dir = choose_hamming_dictionary_wordlist_dir(
                    explicit_wordlist_dir=scorer_cfg.hamming_wordlist_directory,
                    policy=self._hamming_dictionary_policy,
                    policy_root=self._hamming_dictionary_policy_root,
                )
                self._hamming_wordlist_dir_resolved = wl_dir
                build_rtl = bool(scorer_cfg.hamming_build_right_to_left)
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
        self._span_hamming_weight = float(scorer_cfg.span_hamming_weight or 0.0)
        self._span_hamming_mode: SpanHammingMode = ensure_span_hamming_mode(scorer_cfg.span_hamming_mode)
        legacy_enabled = bool(scorer_cfg.span_hamming_enabled or self._span_hamming_weight != 0.0)
        if self._span_hamming_mode is SpanHammingMode.OFF and legacy_enabled:
            self._span_hamming_mode = SpanHammingMode.RAW_BONUS
        self._span_hamming_enabled = (self._span_hamming_mode is not SpanHammingMode.OFF)
        self._span_hamming_assets_dir = scorer_cfg.span_hamming_assets_directory
        self._span_hamming_assets_dictionary_policy = scorer_cfg.span_hamming_assets_dictionary_policy
        self._span_hamming_allow_dictionary_policy_mismatch = bool(
            scorer_cfg.span_hamming_allow_dictionary_mismatch
        )
        self._span_hamming_wordlist_dir_resolved = None
        self._span_hamming_dictionary_policy = None
        self._span_hamming_dictionary_policy_match = None
        self._span_hamming_dictionary_policy_note = None
        self._span_hamming_bucket_policy: SpanHammingBucketPolicy = ensure_span_hamming_bucket_policy(
            scorer_cfg.span_hamming_bucket_policy
        )
        self._span_hamming_ecdf_clamp_min = scorer_cfg.span_hamming_ecdf_clamp_minimum
        self._span_hamming_ecdf_clamp_max = scorer_cfg.span_hamming_ecdf_clamp_maximum
        if self._span_hamming_ecdf_clamp_min is None:
            self._span_hamming_ecdf_clamp_min = float(self._ecdf_clamp_min)
        else:
            self._span_hamming_ecdf_clamp_min = float(self._span_hamming_ecdf_clamp_min)
        if self._span_hamming_ecdf_clamp_max is None:
            self._span_hamming_ecdf_clamp_max = float(self._ecdf_clamp_max)
        else:
            self._span_hamming_ecdf_clamp_max = float(self._span_hamming_ecdf_clamp_max)
        self._span_hamming_coverage_min = float(scorer_cfg.span_hamming_minimum_coverage or 0.0)
        self._span_hamming_quality_min = float(scorer_cfg.span_hamming_minimum_gate_quality or 0.0)
        self._span_hamming_span_pct_min = scorer_cfg.span_hamming_minimum_span_percentile
        if self._span_hamming_span_pct_min is not None:
            self._span_hamming_span_pct_min = float(self._span_hamming_span_pct_min)
        self._span_hamming_char_pct_min = scorer_cfg.span_hamming_minimum_character_percentile
        if self._span_hamming_char_pct_min is not None:
            self._span_hamming_char_pct_min = float(self._span_hamming_char_pct_min)
        self._span_hamming_combine_mode: SpanHammingCombineMode = ensure_span_hamming_combine_mode(
            scorer_cfg.span_hamming_combine_mode
        )
        self._span_hamming_weight_span = float(scorer_cfg.span_hamming_span_weight or 0.0)
        self._span_hamming_weight_char = float(scorer_cfg.span_hamming_character_weight or 0.0)
        self._span_hamming_use_char_channel = False
        self._span_hamming_gate_fail_policy: SpanHammingGateFailurePolicy = ensure_span_hamming_gate_failure_policy(
            scorer_cfg.span_hamming_gate_failure_policy
        )
        self._span_hamming_gate_score_floor = scorer_cfg.span_hamming_gate_score_floor
        if self._span_hamming_gate_score_floor is not None:
            self._span_hamming_gate_score_floor = float(self._span_hamming_gate_score_floor)
        self._span_hamming_lm_assets = None
        self._span_hamming_lm_assets_json = scorer_cfg.span_hamming_language_model_assets
        self._span_hamming_lm_profile_source: SpanHammingLanguageModelProfileSource = ensure_span_hamming_language_model_profile_source(
            scorer_cfg.span_hamming_language_model_profile_source
        )
        self._span_hamming_lm_tail_start_index = int(
            scorer_cfg.span_hamming_language_model_tail_start or 0
        )
        self._span_hamming_lm_weight = float(scorer_cfg.span_hamming_language_model_weight or 0.0)
        self._word_ngram_judge_enabled = bool(scorer_cfg.word_ngram_judge_enabled)
        self._word_ngram_judge_sqlite_path = scorer_cfg.word_ngram_judge_database
        self._word_ngram_judge_alpha = float(scorer_cfg.word_ngram_judge_alpha or 0.4)
        self._word_ngram_judge_miss_logp = float(scorer_cfg.word_ngram_judge_missing_log_probability or -20.0)
        self._word_ngram_judge_min_positions = int(
            scorer_cfg.word_ngram_judge_minimum_positions or 0
        )
        self._word_ngram_judge_prefix_total_thresholds = tuple(
            int(v)
            for v in (scorer_cfg.word_ngram_judge_prefix_thresholds or (1, 10, 100))
        )
        self._word_ngram_judge = None
        self._word_ngram_judge_forced_debug_intervals = False
        if self._word_ngram_judge_enabled:
            try:
                from rdp.scoring.word_ngrams import RuneTokenWordNgramJudgeRuntime
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "word_ngram_judge_enabled=True, but the experimental word-ngram "
                    "judge module is not present in this V1 release build. "
                    "Disable word_ngram_judge_enabled or install the experimental "
                    "ngram tooling branch."
                ) from exc

            self._word_ngram_judge = RuneTokenWordNgramJudgeRuntime.open_sqlite(
                self._word_ngram_judge_sqlite_path,
                alpha=float(self._word_ngram_judge_alpha),
                miss_logp=float(self._word_ngram_judge_miss_logp),
                min_positions=int(self._word_ngram_judge_min_positions),
                prefix_total_thresholds=self._word_ngram_judge_prefix_total_thresholds,
            )
        if not (0.0 < self._span_hamming_ecdf_clamp_min < self._span_hamming_ecdf_clamp_max < 1.0):
            raise ValueError("span_hamming_ecdf_clamp_min/max must satisfy 0 < min < max < 1")
        if self._span_hamming_bucket_policy is not SpanHammingBucketPolicy.NEAREST_SMALLER_ON_TIE:
            raise ValueError("span_hamming_bucket_policy currently only supports 'nearest_smaller_on_tie'")
        if self._span_hamming_enabled:
            try:
                from rdp.core.hamming_dictionary_policy import ensure_hamming_dictionary_policy
                from rdp.scoring.hamming.dictionary_assets import choose_hamming_dictionary_wordlist_dir
                from rdp.scoring.span_hamming import (
                    SpanCalibratedAssets,
                    SpanHammingBackend,
                    SpanHammingConfig,
                    SpanHammingLmAssetsV2,
                )

                debug_return_intervals = bool(
                    scorer_cfg.span_hamming_return_debug_intervals
                )
                if self._word_ngram_judge is not None and not debug_return_intervals:
                    debug_return_intervals = True
                    self._word_ngram_judge_forced_debug_intervals = True

                span_cfg = SpanHammingConfig(
                    len_min=int(scorer_cfg.span_hamming_minimum_length),
                    len_max=int(scorer_cfg.span_hamming_maximum_length),
                    max_hd=int(scorer_cfg.span_hamming_maximum_distance),
                    start_stride=int(scorer_cfg.span_hamming_start_stride),
                    max_windows_total=int(scorer_cfg.span_hamming_maximum_windows),
                    max_candidates_per_window=int(
                        scorer_cfg.span_hamming_maximum_candidates_per_window
                    ),
                    max_intervals_considered_per_start=int(
                        scorer_cfg.span_hamming_maximum_intervals_per_start
                    ),
                    min_quality_threshold=float(
                        scorer_cfg.span_hamming_minimum_quality
                    ),
                    debug_return_intervals=debug_return_intervals,
                )
                explicit_span_wl_dir = scorer_cfg.span_hamming_wordlist_directory
                wl_dir = choose_hamming_dictionary_wordlist_dir(
                    explicit_wordlist_dir=explicit_span_wl_dir,
                    policy=self._hamming_dictionary_policy,
                    policy_root=self._hamming_dictionary_policy_root,
                )
                self._span_hamming_wordlist_dir_resolved = wl_dir
                if explicit_span_wl_dir is None and self._hamming_dictionary_policy is not None:
                    self._span_hamming_dictionary_policy = str(
                        getattr(self._hamming_dictionary_policy, "value", self._hamming_dictionary_policy)
                    )
                elif explicit_span_wl_dir is not None:
                    self._span_hamming_dictionary_policy_note = "explicit_span_hamming_wordlist_dir"
                require_selected = bool(scorer_cfg.span_hamming_require_selection)
                self._span_hamming_backend = SpanHammingBackend(
                    config=span_cfg,
                    wordlist_dir=wl_dir,
                    require_selected=require_selected,
                )
                if self._span_hamming_mode is SpanHammingMode.CALIBRATED:
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
                    assets_policy = self._span_hamming_assets_dictionary_policy
                    if assets_policy is None:
                        assets_policy = getattr(self._span_hamming_assets, "dictionary_policy", None)
                    if assets_policy is not None:
                        assets_policy = ensure_hamming_dictionary_policy(assets_policy).value
                    self._span_hamming_assets_dictionary_policy = assets_policy
                    active_policy = self._span_hamming_dictionary_policy
                    if active_policy is None:
                        if self._span_hamming_allow_dictionary_policy_mismatch:
                            self._span_hamming_dictionary_policy_match = None
                            self._span_hamming_dictionary_policy_note = "custom_wordlist_dir_unverified_allowed"
                        else:
                            raise ValueError(
                                "calibrated span-hamming with explicit span_hamming_wordlist_dir requires "
                                "span_hamming_allow_dictionary_policy_mismatch=True"
                            )
                    elif assets_policy is None:
                        if str(active_policy) == "normal":
                            self._span_hamming_dictionary_policy_match = True
                            self._span_hamming_dictionary_policy_note = "legacy_assets_assumed_normal"
                        elif self._span_hamming_allow_dictionary_policy_mismatch:
                            self._span_hamming_dictionary_policy_match = None
                            self._span_hamming_dictionary_policy_note = (
                                "assets_policy_unspecified_nondefault_dictionary_allowed"
                            )
                        else:
                            raise ValueError(
                                "calibrated span-hamming with non-default dictionary policy requires "
                                "span_hamming_assets_dictionary_policy metadata or explicit override"
                            )
                    elif str(active_policy) == str(assets_policy):
                        self._span_hamming_dictionary_policy_match = True
                        self._span_hamming_dictionary_policy_note = "policy_match"
                    elif self._span_hamming_allow_dictionary_policy_mismatch:
                        self._span_hamming_dictionary_policy_match = False
                        self._span_hamming_dictionary_policy_note = "policy_mismatch_allowed"
                    else:
                        raise ValueError(
                            "calibrated span-hamming dictionary policy mismatch: "
                            f"active={active_policy} assets={assets_policy}"
                        )
                    if self._span_hamming_lm_assets_json is not None:
                        self._span_hamming_lm_assets = SpanHammingLmAssetsV2.load(self._span_hamming_lm_assets_json)
                        if self._span_hamming_lm_tail_start_index >= int(self._span_hamming_lm_assets.profile_vector_length):
                            raise ValueError(
                                "span_hamming_lm_tail_start_index must be < profile_vector_length in LM assets"
                            )
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
                    if self._span_hamming_combine_mode is SpanHammingCombineMode.WEIGHTED_SUM:
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
                if self._span_hamming_mode is SpanHammingMode.CALIBRATED:
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
            "lm_weights": scorer_cfg.weight_contract(),
            "hamming_dictionary_policy": (
                str(getattr(self._hamming_dictionary_policy, "value", self._hamming_dictionary_policy))
                if self._hamming_dictionary_policy is not None
                else None
            ),
            "hamming_wordlist_dir": (
                str(self._hamming_wordlist_dir_resolved) if self._hamming_wordlist_dir_resolved is not None else None
            ),
            "span_hamming_enabled": bool(
                self._span_hamming_backend is not None
                and (
                    (self._span_hamming_mode is SpanHammingMode.RAW_BONUS and self._span_hamming_weight != 0.0)
                    or self._span_hamming_mode is SpanHammingMode.CALIBRATED
                )
            ),
            "span_hamming_wordlist_dir": (
                str(self._span_hamming_wordlist_dir_resolved)
                if self._span_hamming_wordlist_dir_resolved is not None
                else None
            ),
            "span_hamming_dictionary_policy": self._span_hamming_dictionary_policy,
            "span_hamming_mode": self._span_hamming_mode.value,
            "span_hamming_assets_dir": (
                str(self._span_hamming_assets_dir) if self._span_hamming_assets_dir is not None else None
            ),
            "span_hamming_assets_dictionary_policy": self._span_hamming_assets_dictionary_policy,
            "span_hamming_dictionary_policy_match": self._span_hamming_dictionary_policy_match,
            "span_hamming_dictionary_policy_note": self._span_hamming_dictionary_policy_note,
            "span_hamming_weight": float(self._span_hamming_weight),
            "span_hamming_combine_mode": self._span_hamming_combine_mode.value,
            "span_hamming_weight_span": float(self._span_hamming_weight_span),
            "span_hamming_weight_char": float(self._span_hamming_weight_char),
            "span_hamming_use_char_channel": bool(self._span_hamming_use_char_channel),
            "span_hamming_ecdf_clamp_min": float(self._span_hamming_ecdf_clamp_min),
            "span_hamming_ecdf_clamp_max": float(self._span_hamming_ecdf_clamp_max),
            "span_hamming_bucket_policy": self._span_hamming_bucket_policy.value,
            "span_hamming_eval_total": 0,
            "span_hamming_eval_active": 0,
            "span_hamming_eval_skipped_char_gate": 0,
            "span_hamming_eval_seconds_total": 0.0,
            "span_hamming_eval_active_seconds_total": 0.0,
            "word_ngram_judge_enabled": bool(self._word_ngram_judge is not None),
            "word_ngram_judge_sqlite_path": (
                str(self._word_ngram_judge_sqlite_path) if self._word_ngram_judge_sqlite_path is not None else None
            ),
            "word_ngram_judge_min_positions": int(self._word_ngram_judge_min_positions),
            "word_ngram_judge_prefix_total_thresholds": tuple(self._word_ngram_judge_prefix_total_thresholds),
            "word_ngram_judge_forced_debug_intervals": bool(self._word_ngram_judge_forced_debug_intervals),
        }
        # Caches for WLI conversions/windows (bounded LRU)
        self._wli_cache_limit = 8
        self._wli_source_cache: "OrderedDict[int, _WliSourceCacheEntry]" = OrderedDict()
        self._wli_window_cache: "OrderedDict[Tuple[int, int], _WliWindowCacheEntry]" = OrderedDict()
        self._diagnostics_enabled: bool = bool(scorer_cfg.diagnostics_enabled)

    def _ensure_ecdf(self) -> ECDFCache:
        if self._ecdf is None:
            self._ecdf = ECDFCache(
                self._ecdf_root,
                prefer_float32=self._ecdf_prefer_float32,
                load_reporter=self._lm_load_reporter,
            )
        return self._ecdf

    def _score_word_ngram_signal(self, *, pt: np.ndarray, span_stats: Any) -> dict[str, Any]:
        judge = getattr(self, "_word_ngram_judge", None)
        if judge is None:
            return {
                "word_ngram_judge_available": False,
                "word_ngram_judge_active": False,
                "word_ngram_judge_inactive_reason": "disabled",
            }
        intervals = tuple(getattr(span_stats, "selected_intervals", ()) or ())
        if not intervals:
            return {
                "word_ngram_judge_available": True,
                "word_ngram_judge_active": False,
                "word_ngram_judge_inactive_reason": "no_selected_intervals",
                "word_ngram_judge_exact_word_count": 0,
                "word_ngram_judge_segment_count": 0,
                "word_ngram_judge_n_positions": 0,
                "word_ngram_judge_trust_score": 0.0,
                "word_ngram_judge_trust_tier": "inactive",
            }
        report = judge.score_candidate(
            text_idx=pt.tolist(),
            selected_intervals=intervals,
            direction=self.direction,
        )
        return {
            "word_ngram_judge_available": bool(report.available),
            "word_ngram_judge_active": bool(report.active),
            "word_ngram_judge_inactive_reason": report.inactive_reason,
            "word_ngram_judge_exact_word_count": int(report.exact_word_count),
            "word_ngram_judge_segment_count": int(report.segment_count),
            "word_ngram_judge_xent_3": report.xent_3,
            "word_ngram_judge_backoff_xent": report.xent_backoff_5_4_3,
            "word_ngram_judge_n_positions": int(report.n_positions),
            "word_ngram_judge_miss_rate": report.miss_rate,
            "word_ngram_judge_used5_rate": report.used5_rate,
            "word_ngram_judge_used4_rate": report.used4_rate,
            "word_ngram_judge_used3_rate": report.used3_rate,
            "word_ngram_judge_prefix_total_mean": float(report.prefix_total_mean),
            "word_ngram_judge_prefix_total_min": float(report.prefix_total_min),
            "word_ngram_judge_prefix_total_ge_1_rate": float(report.prefix_total_ge_1_rate),
            "word_ngram_judge_prefix_total_ge_10_rate": float(report.prefix_total_ge_10_rate),
            "word_ngram_judge_prefix_total_ge_100_rate": float(report.prefix_total_ge_100_rate),
            "word_ngram_judge_trust_score": float(report.trust_score),
            "word_ngram_judge_trust_tier": str(report.trust_tier),
            "word_ngram_judge_report_xent": (
                None if not report.active else report.xent_3
            ),
            "word_ngram_judge_report_backoff_xent": (
                None if not report.active else report.xent_backoff_5_4_3
            ),
        }

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
        self._span_hamming_mode = SpanHammingMode.OFF
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
        def _bump_span_eval(
            *,
            total: int,
            active: int,
            skipped: int,
            seconds_total: float = 0.0,
            seconds_active: float = 0.0,
        ) -> None:
            try:
                prev_total = int(self._telemetry.get("span_hamming_eval_total", 0) or 0)
                prev_active = int(self._telemetry.get("span_hamming_eval_active", 0) or 0)
                prev_skipped = int(self._telemetry.get("span_hamming_eval_skipped_char_gate", 0) or 0)
                prev_seconds_total = float(self._telemetry.get("span_hamming_eval_seconds_total", 0.0) or 0.0)
                prev_seconds_active = float(self._telemetry.get("span_hamming_eval_active_seconds_total", 0.0) or 0.0)
                self._telemetry["span_hamming_eval_total"] = int(prev_total + int(total))
                self._telemetry["span_hamming_eval_active"] = int(prev_active + int(active))
                self._telemetry["span_hamming_eval_skipped_char_gate"] = int(prev_skipped + int(skipped))
                self._telemetry["span_hamming_eval_seconds_total"] = float(
                    max(0.0, prev_seconds_total + float(seconds_total))
                )
                self._telemetry["span_hamming_eval_active_seconds_total"] = float(
                    max(0.0, prev_seconds_active + float(seconds_active))
                )
            except Exception:
                pass

        backend = self._span_hamming_backend
        assets = self._span_hamming_assets
        if backend is None or assets is None:
            raise ValueError("Calibrated span mode requires loaded span backend and assets")
        lm_assets = self._span_hamming_lm_assets
        char_pct: float | None = None
        char_score: float | None = None
        if self._span_hamming_use_char_channel:
            char_pct, char_score = self._score_base_channel_pct(pt=pt, wli_windows=wli_windows)
            if (
                lm_assets is None
                and self._span_hamming_char_pct_min is not None
                and char_pct < float(self._span_hamming_char_pct_min)
            ):
                _bump_span_eval(total=1, active=0, skipped=1, seconds_total=0.0, seconds_active=0.0)
                gate_reasons = ["char_pct_below_min"]
                gate_policy = self._span_hamming_gate_fail_policy.value
                score = float(
                    char_score
                    if (gate_policy == "character_only" and char_score is not None)
                    else self._span_hamming_gate_score_floor
                )
                combined_pct = (
                    float(char_pct)
                    if (gate_policy == "character_only")
                    else float("nan")
                )
                combined_energy = (
                    float(-np.log1p(-float(char_pct)))
                    if (gate_policy == "character_only")
                    else float("nan")
                )
                objective_stats = {
                    "score_mean": float(score),
                    "score_std": 0.0,
                    "n_windows": 1,
                    "span_raw": float("nan"),
                    "span_coverage": float("nan"),
                    "span_quality": float("nan"),
                    "span_x": float("nan"),
                    "span_pct": float("nan"),
                    "span_energy": float("nan"),
                    "char_pct": float(char_pct),
                    "char_score": (None if char_score is None else float(char_score)),
                    "combine_mode": self._span_hamming_combine_mode.value,
                    "combined_pct": float(combined_pct),
                    "combined_energy": float(combined_energy),
                    "span_bucket_length": -1,
                    "span_bucket_direction": str(BaseScorer._dir_name(self.direction)),
                    "gate_failed": True,
                    "gate_reasons": list(gate_reasons),
                    "span_skipped": True,
                    "gate_fail_policy": gate_policy,
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
                        "stat.mean_per_ngram_penalized": float("nan"),
                    },
                    span_hamming_mode="calibrated",
                    span_hamming_combine_mode=self._span_hamming_combine_mode.value,
                    span_hamming_weight_span=float(self._span_hamming_weight_span),
                    span_hamming_weight_char=float(self._span_hamming_weight_char),
                    span_hamming_use_char_channel=bool(self._span_hamming_use_char_channel),
                    span_hamming_raw=float("nan"),
                    span_hamming_coverage=float("nan"),
                    span_hamming_quality=float("nan"),
                    span_hamming_length_bins=(),
                    span_hamming_raw_by_len=(),
                    span_hamming_coverage_by_len=(),
                    span_hamming_quality_by_len=(),
                    span_hamming_x=float("nan"),
                    span_hamming_pct=float("nan"),
                    span_hamming_energy=float("nan"),
                    span_hamming_char_pct=float(char_pct),
                    span_hamming_char_score=(None if char_score is None else float(char_score)),
                    span_hamming_combined_pct=float(combined_pct),
                    span_hamming_combined_energy=float(combined_energy),
                    span_hamming_bucket_length=-1,
                    span_hamming_gate_failed=True,
                    span_hamming_gate_reasons=list(gate_reasons),
                    span_hamming_gate_score_floor=float(self._span_hamming_gate_score_floor),
                    span_hamming_span_skipped=True,
                    span_hamming_gate_fail_policy=gate_policy,
                    span_hamming_eval_total_batch=1,
                    span_hamming_eval_active_batch=0,
                    span_hamming_eval_skipped_char_gate_batch=1,
                    span_lm_enabled=False,
                    span_lm_applied_to_score=False,
                    word_ngram_judge_available=bool(self._word_ngram_judge is not None),
                    word_ngram_judge_active=False,
                    word_ngram_judge_inactive_reason="span_skipped_char_gate",
                )
                return float(score)
        t_span = float(time.perf_counter())
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
            dt_span = max(0.0, float(time.perf_counter() - t_span))
            _bump_span_eval(total=1, active=1, skipped=0, seconds_total=dt_span, seconds_active=dt_span)
            raise ValueError(f"Span backend failed in calibrated mode: {exc}") from exc
        dt_span = max(0.0, float(time.perf_counter() - t_span))
        _bump_span_eval(total=1, active=1, skipped=0, seconds_total=dt_span, seconds_active=dt_span)

        selected_bucket = assets.select_bucket(
            direction=BaseScorer._dir_name(self.direction),
            text_length=int(pt.shape[0]),
        )
        bucket = assets.score_span_raw_in_bucket(
            direction=BaseScorer._dir_name(self.direction),
            length_bucket=int(selected_bucket),
            span_raw=span_raw,
            clamp_min=float(self._span_hamming_ecdf_clamp_min),
            clamp_max=float(self._span_hamming_ecdf_clamp_max),
        )

        lm_score = None
        if lm_assets is not None:
            lm_score = lm_assets.score_profile_margin_l1_in_bucket(
                stats=span_stats,
                direction=BaseScorer._dir_name(self.direction),
                length_bucket=int(selected_bucket),
                clamp_min=float(self._span_hamming_ecdf_clamp_min),
                clamp_max=float(self._span_hamming_ecdf_clamp_max),
                profile_source=self._span_hamming_lm_profile_source.value,
                tail_start_index=int(self._span_hamming_lm_tail_start_index),
            )
        word_ngram_stats = self._score_word_ngram_signal(pt=pt, span_stats=span_stats)

        gate_reasons: list[str] = []
        if span_cov < float(self._span_hamming_coverage_min):
            gate_reasons.append("coverage_below_min")
        if span_q < float(self._span_hamming_quality_min):
            gate_reasons.append("quality_below_min")
        if self._span_hamming_span_pct_min is not None and bucket.span_pct < float(self._span_hamming_span_pct_min):
            gate_reasons.append("span_pct_below_min")
        if (
            self._span_hamming_use_char_channel
            and char_pct is not None
            and self._span_hamming_char_pct_min is not None
            and char_pct < float(self._span_hamming_char_pct_min)
        ):
            gate_reasons.append("char_pct_below_min")
        if self._span_hamming_use_char_channel and char_pct is None:
            char_pct, char_score = self._score_base_channel_pct(pt=pt, wli_windows=wli_windows)
            if self._span_hamming_char_pct_min is not None and char_pct < float(self._span_hamming_char_pct_min):
                gate_reasons.append("char_pct_below_min")
        gate_failed = bool(gate_reasons)

        span_pct = float(bucket.span_pct)
        combine_mode = self._span_hamming_combine_mode.value
        if char_pct is None:
            combined_pct = span_pct
        elif combine_mode == "minimum":
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
        span_energy_base = float(combined_energy)
        profile_energy = float(lm_score.profile_margin_l1_energy) if lm_score is not None else 0.0
        lm_applied_to_score = bool((lm_score is not None) and not gate_failed)
        span_energy_total = (
            float(span_energy_base + float(self._span_hamming_lm_weight) * profile_energy)
            if lm_applied_to_score
            else float(span_energy_base)
        )
        pct_total = float(1.0 - np.exp(-span_energy_total))
        pct_total = float(
            np.clip(
                pct_total,
                float(self._span_hamming_ecdf_clamp_min),
                float(self._span_hamming_ecdf_clamp_max),
            )
        )

        fam = self.objective.family
        gate_policy = self._span_hamming_gate_fail_policy.value
        if gate_failed:
            if gate_policy == "character_only" and char_score is not None:
                score = float(char_score)
            else:
                score = float(self._span_hamming_gate_score_floor)
        else:
            score = float(span_energy_total if fam is ObjectiveFamily.ENERGY else pct_total)

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
            "span_energy_base": float(span_energy_base),
            "span_energy_total": float(span_energy_total),
            "span_pct_total": float(pct_total),
            "span_bucket_length": int(bucket.length_bucket),
            "span_bucket_direction": str(bucket.direction),
            "gate_failed": bool(gate_failed),
            "gate_reasons": list(gate_reasons),
            "gate_fail_policy": gate_policy,
            "span_lm_enabled": bool(lm_score is not None),
            "span_lm_applied_to_score": bool(lm_applied_to_score),
            "word_ngram_judge_active": bool(word_ngram_stats.get("word_ngram_judge_active", False)),
            "word_ngram_judge_report_xent": word_ngram_stats.get("word_ngram_judge_report_xent"),
            "word_ngram_judge_trust_tier": word_ngram_stats.get("word_ngram_judge_trust_tier"),
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
            span_hamming_gate_fail_policy=gate_policy,
            span_hamming_eval_total_batch=1,
            span_hamming_eval_active_batch=1,
            span_hamming_eval_skipped_char_gate_batch=0,
            span_lm_enabled=bool(lm_score is not None),
            span_lm_applied_to_score=bool(lm_applied_to_score),
            span_lm_profile_source=(
                None if lm_score is None else self._span_hamming_lm_profile_source.value
            ),
            span_lm_tail_start_index=(
                None if lm_score is None else int(self._span_hamming_lm_tail_start_index)
            ),
            span_lm_tail_start_index_used_for_score=False,
            span_lm_weight=float(self._span_hamming_lm_weight),
            span_lm_length_bucket=(
                None if lm_score is None else int(lm_score.length_bucket)
            ),
            span_lm_profile_margin_l1_raw=(
                None if lm_score is None else float(lm_score.profile_margin_l1_raw)
            ),
            span_lm_profile_margin_l1_pct_noise=(
                None if lm_score is None else float(lm_score.profile_margin_l1_pct_noise)
            ),
            span_lm_profile_margin_l1_pct_real=(
                None if lm_score is None else lm_score.profile_margin_l1_pct_real
            ),
            span_lm_profile_energy=(
                None if lm_score is None else float(lm_score.profile_margin_l1_energy)
            ),
            span_lm_mean_bin_index_raw=(
                None if lm_score is None else float(lm_score.mean_bin_index_raw)
            ),
            span_lm_mean_bin_length_raw=(
                None if lm_score is None else float(lm_score.mean_bin_length_raw)
            ),
            span_lm_tail_mass_raw=(
                None if lm_score is None else float(lm_score.tail_mass_raw)
            ),
            span_energy_base=float(span_energy_base),
            span_energy_total=float(span_energy_total),
            span_pct_total=float(pct_total),
            **word_ngram_stats,
        )
        return float(score)

    def _apply_span_hamming_bonus(self, base_score: float, pt: np.ndarray) -> float:
        """
        Optionally augment final score with weighted span-hamming signal.
        """
        if self._span_hamming_mode is not SpanHammingMode.RAW_BONUS:
            return float(base_score)
        backend = self._span_hamming_backend
        weight = float(self._span_hamming_weight)
        if backend is None or weight == 0.0:
            return float(base_score)
        t_span = float(time.perf_counter())
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
            dt_span = max(0.0, float(time.perf_counter() - t_span))
            try:
                prev_total = int(self._telemetry.get("span_hamming_eval_total", 0) or 0)
                prev_active = int(self._telemetry.get("span_hamming_eval_active", 0) or 0)
                prev_seconds_total = float(self._telemetry.get("span_hamming_eval_seconds_total", 0.0) or 0.0)
                prev_seconds_active = float(self._telemetry.get("span_hamming_eval_active_seconds_total", 0.0) or 0.0)
                self._telemetry["span_hamming_eval_total"] = int(prev_total + 1)
                self._telemetry["span_hamming_eval_active"] = int(prev_active + 1)
                self._telemetry["span_hamming_eval_seconds_total"] = float(max(0.0, prev_seconds_total + dt_span))
                self._telemetry["span_hamming_eval_active_seconds_total"] = float(max(0.0, prev_seconds_active + dt_span))
            except Exception:
                pass
            return float(base_score)
        dt_span = max(0.0, float(time.perf_counter() - t_span))
        try:
            prev_total = int(self._telemetry.get("span_hamming_eval_total", 0) or 0)
            prev_active = int(self._telemetry.get("span_hamming_eval_active", 0) or 0)
            prev_seconds_total = float(self._telemetry.get("span_hamming_eval_seconds_total", 0.0) or 0.0)
            prev_seconds_active = float(self._telemetry.get("span_hamming_eval_active_seconds_total", 0.0) or 0.0)
            self._telemetry["span_hamming_eval_total"] = int(prev_total + 1)
            self._telemetry["span_hamming_eval_active"] = int(prev_active + 1)
            self._telemetry["span_hamming_eval_seconds_total"] = float(max(0.0, prev_seconds_total + dt_span))
            self._telemetry["span_hamming_eval_active_seconds_total"] = float(max(0.0, prev_seconds_active + dt_span))
        except Exception:
            pass

        bonus = float(weight * span_raw)
        out = float(base_score + bonus)
        word_ngram_stats = self._score_word_ngram_signal(pt=pt, span_stats=span_stats)
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
            stats.update(word_ngram_stats)
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
            **word_ngram_stats,
        )
        return out

    # ---------------------------- public API ----------------------------
    def score(self, plaintext: Iterable[int], wli_windows: Iterable[Tuple[int, int]] | None = None) -> float:
        fam = self.objective.family
        stat = self.objective.stat
        pt_single = _to_u8_1d(plaintext)

        if self._span_hamming_mode is SpanHammingMode.CALIBRATED:
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
                        mode=self._hamming_direction_mode.value,
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
                    mode=self._hamming_direction_mode.value,
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
                    mode=self._hamming_direction_mode.value,
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
                    mode=self._hamming_direction_mode.value,
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
            from rdp.scoring.hamming.anneal import compute_hamming_weight
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
        return [
            (Channel.CHAR if channel == "char" else Channel.WLI, int(n), float(weight))
            for channel, n, weight in self._effective_model_weights(use_word_lengths=self.use_word_breaks)
        ]

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
