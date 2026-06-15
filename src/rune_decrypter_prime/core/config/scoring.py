# ============================================================
# rune_decrypter_prime/core/config.py
# Unified dataclasses for cipher/scorer/solver/run configs.
# ============================================================

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Literal, TypeVar
import math

from rune_decrypter_prime.core.types import (
    ScorerImpl,
    Direction,
    FloatDType,
    SeMode,
    ObjectiveFamily,
    Stat,
    ObjectiveSpec,
    AvgWindowPolicy,
    ensure_direction,
    ensure_float_dtype,
    ensure_scorer_impl,
    ensure_se_mode,
    ensure_objective_family,
    ensure_stat,
    ensure_avg_window_policy,
)
from rune_decrypter_prime.core.config.hard_crib import HardCribConfig, normalize_hard_crib_config
from rune_decrypter_prime.core.component_contracts import ScorerLaneName
from rune_decrypter_prime.core.hamming_dictionary_policy import (
    HammingDictionaryPolicy,
    ensure_hamming_dictionary_policy,
)


_ScoringModeT = TypeVar("_ScoringModeT", bound=StrEnum)


def _ensure_scoring_mode(
    enum_cls: type[_ScoringModeT],
    value: _ScoringModeT | str | None,
    *,
    field_name: str,
    default: _ScoringModeT,
    lower: bool = True,
) -> _ScoringModeT:
    if isinstance(value, enum_cls):
        return value
    text = default.value if value is None else str(value).strip()
    if lower:
        text = text.lower()
    try:
        return enum_cls(text)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_cls)
        raise ValueError(f"{field_name} must be one of: {allowed}") from exc


class HammingDirectionMode(StrEnum):
    MATCH = "match"
    BOTH = "both"


class SpanHammingMode(StrEnum):
    OFF = "off"
    RAW_BONUS = "raw_bonus"
    CALIBRATED = "calibrated"


class SpanHammingBucketPolicy(StrEnum):
    NEAREST_SMALLER_TIE = "nearest_smaller_tie"


class SpanHammingCombineMode(StrEnum):
    MIN = "min"
    WEIGHTED_SUM = "weighted_sum"


class SpanHammingGateFailPolicy(StrEnum):
    SCORE_FLOOR = "score_floor"
    CHAR_ONLY = "char_only"


class SpanHammingLmProfileSource(StrEnum):
    SPAN_RAW_BY_LEN = "span_raw_by_len"
    CHARS_COVERED_BY_LEN = "chars_covered_by_len"


def ensure_hamming_direction_mode(value: HammingDirectionMode | str | None) -> HammingDirectionMode:
    return _ensure_scoring_mode(
        HammingDirectionMode,
        value,
        field_name="hamming_direction_mode",
        default=HammingDirectionMode.MATCH,
    )


def ensure_span_hamming_mode(value: SpanHammingMode | str | None) -> SpanHammingMode:
    return _ensure_scoring_mode(
        SpanHammingMode,
        value,
        field_name="span_hamming_mode",
        default=SpanHammingMode.OFF,
    )


def ensure_span_hamming_bucket_policy(
    value: SpanHammingBucketPolicy | str | None,
) -> SpanHammingBucketPolicy:
    return _ensure_scoring_mode(
        SpanHammingBucketPolicy,
        value,
        field_name="span_hamming_bucket_policy",
        default=SpanHammingBucketPolicy.NEAREST_SMALLER_TIE,
    )


def ensure_span_hamming_combine_mode(
    value: SpanHammingCombineMode | str | None,
) -> SpanHammingCombineMode:
    return _ensure_scoring_mode(
        SpanHammingCombineMode,
        value,
        field_name="span_hamming_combine_mode",
        default=SpanHammingCombineMode.MIN,
    )


def ensure_span_hamming_gate_fail_policy(
    value: SpanHammingGateFailPolicy | str | None,
) -> SpanHammingGateFailPolicy:
    return _ensure_scoring_mode(
        SpanHammingGateFailPolicy,
        value,
        field_name="span_hamming_gate_fail_policy",
        default=SpanHammingGateFailPolicy.SCORE_FLOOR,
    )


def ensure_span_hamming_lm_profile_source(
    value: SpanHammingLmProfileSource | str | None,
) -> SpanHammingLmProfileSource:
    return _ensure_scoring_mode(
        SpanHammingLmProfileSource,
        value,
        field_name="span_hamming_lm_profile_source",
        default=SpanHammingLmProfileSource.SPAN_RAW_BY_LEN,
        lower=False,
    )


def _objective_from_string(spec: str) -> ObjectiveSpec:
    """
    Accept legacy strings like "pct.logp.win10" and convert them to ObjectiveSpec.
    """
    if spec is None:
        raise ValueError("objective string cannot be None")
    text = str(spec).strip().lower()
    if not text:
        raise ValueError("objective string cannot be empty")
    parts = [token for token in text.replace("/", ".").split(".") if token]
    family = ensure_objective_family(parts[0])
    stat = None
    win = None
    for token in parts[1:]:
        if token.startswith("win"):
            try:
                win = int(token[3:])
            except ValueError as exc:
                raise ValueError(f"Invalid window token '{token}' in objective string '{spec}'") from exc
            continue
        stat = ensure_stat(token)
    return ObjectiveSpec(family=family, stat=stat, win=win)

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
    n_char: int = 2
    n_wli: int  = 2
    win: int = 10
    stride: int = 1
    se_mode: SeMode = SeMode.NOSE
    weights: Tuple[float, float] = (0.25, 0.75)   # (w_char, w_wli)
    maximize: bool = True
    encoding_dir: Direction = Direction.LTR
    char_weights: Dict[int, float] = field(default_factory=lambda: {2: 0.5})
    wli_weights: Dict[int, float] = field(default_factory=lambda: {2: 0.5})
    impl: Optional[ScorerImpl] = ScorerImpl.AUTO
    compute_dtype: FloatDType | Literal["float32", "float64"] = "float32"
    acc_dtype: FloatDType | Literal["float32", "float64"] = "float64"
    dtype: FloatDType | Literal["float32", "float64"] | None = None
    objective: ObjectiveSpec = ObjectiveSpec(family=ObjectiveFamily.PCT,stat=Stat.LOGP,win=10)
    avg_window_policy: AvgWindowPolicy | Literal["fixed_win", "full_text"] = AvgWindowPolicy.FIXED_WIN
    ecdf_clamp_min: float = 1e-6
    ecdf_clamp_max: float = 1.0 - 1e-6
    diagnostics_enabled: bool = False
    hard_crib: Optional[HardCribConfig | Dict[str, Any]] = None
    # Optional Hamming scorer component
    hamming_enabled: bool = False
    hamming_dictionary_policy: HammingDictionaryPolicy | str = HammingDictionaryPolicy.NORMAL
    hamming_dictionary_policy_root: Path | None = None
    hamming_wordlist_dir: Path | None = None
    hamming_build_rtl: bool = False
    hamming_weight: float | None = None
    hamming_weight_max: float = 0.01
    hamming_ramp_start_frac: float = 0.2
    hamming_ramp_end_frac: float = 0.7
    hamming_max_hd: int = 1_000_000
    hamming_length_weights: Dict[int, float] = field(default_factory=dict)
    hamming_direction_mode: HammingDirectionMode | str = HammingDirectionMode.MATCH
    # Optional span-hamming scorer component
    span_hamming_enabled: bool = False
    span_hamming_wordlist_dir: Path | None = None
    span_hamming_weight: float = 0.0
    span_hamming_len_min: int = 3
    span_hamming_len_max: int = 14
    span_hamming_max_hd: int = 2
    span_hamming_start_stride: int = 1
    span_hamming_max_windows_total: int = 0
    span_hamming_max_candidates_per_window: int = 256
    span_hamming_max_intervals_considered_per_start: int = 4
    span_hamming_min_quality_threshold: float = 1e-9
    span_hamming_debug_return_intervals: bool = False
    span_hamming_require_selected: bool = True
    # Calibrated span channel (source-driven; no CLI)
    span_hamming_mode: SpanHammingMode | str = SpanHammingMode.OFF
    span_hamming_assets_dir: Path | None = None
    span_hamming_assets_dictionary_policy: HammingDictionaryPolicy | str | None = None
    span_hamming_allow_dictionary_policy_mismatch: bool = False
    span_hamming_bucket_policy: SpanHammingBucketPolicy | str = SpanHammingBucketPolicy.NEAREST_SMALLER_TIE
    span_hamming_ecdf_clamp_min: float | None = None
    span_hamming_ecdf_clamp_max: float | None = None
    span_hamming_combine_mode: SpanHammingCombineMode | str = SpanHammingCombineMode.MIN
    span_hamming_weight_span: float = 1.0
    span_hamming_weight_char: float = 0.0
    span_hamming_coverage_min: float = 0.0
    span_hamming_quality_min: float = 0.0
    span_hamming_span_pct_min: float | None = None
    span_hamming_char_pct_min: float | None = None
    span_hamming_gate_fail_policy: SpanHammingGateFailPolicy | str = SpanHammingGateFailPolicy.SCORE_FLOOR
    span_hamming_gate_score_floor: float | None = None
    # Optional LM/profile extension over calibrated span.
    span_hamming_lm_assets_json: Path | None = None
    span_hamming_lm_profile_source: SpanHammingLmProfileSource | str = SpanHammingLmProfileSource.SPAN_RAW_BY_LEN
    span_hamming_lm_tail_start_index: int = 5
    span_hamming_lm_weight: float = 0.0
    # Optional word-ngram judge side-channel (report-only in slice 1).
    word_ngram_judge_enabled: bool = False
    word_ngram_judge_sqlite_path: Path | None = None
    word_ngram_judge_alpha: float = 0.4
    word_ngram_judge_miss_logp: float = -20.0
    word_ngram_judge_min_positions: int = 12
    word_ngram_judge_prefix_total_thresholds: Tuple[int, ...] = (1, 10, 100)

    def __post_init__(self) -> None:
        if self.encoding_dir is not None:
            self.encoding_dir = ensure_direction(self.encoding_dir)
        if self.impl is not None:
            self.impl = ensure_scorer_impl(self.impl)
        if self.se_mode is not None:
            self.se_mode = ensure_se_mode(self.se_mode)
        if self.avg_window_policy is not None:
            self.avg_window_policy = ensure_avg_window_policy(self.avg_window_policy)
        if self.compute_dtype is not None:
            self.compute_dtype = ensure_float_dtype(self.compute_dtype)
        if self.acc_dtype is not None:
            self.acc_dtype = ensure_float_dtype(self.acc_dtype)
        if self.dtype is not None:
            self.dtype = ensure_float_dtype(self.dtype)
        if self.dtype is None:
            self.dtype = self.acc_dtype

        obj = getattr(self, "objective", None)
        if isinstance(obj, dict):
            fam = ensure_objective_family(obj.get("family", ObjectiveFamily.PCT))
            stat_val = obj.get("stat")
            stat = ensure_stat(stat_val) if stat_val is not None else None
            win = obj.get("win")
            self.objective = ObjectiveSpec(family=fam, stat=stat, win=win)
        elif isinstance(obj, str):
            self.objective = _objective_from_string(obj)
        elif isinstance(obj, ObjectiveSpec):
            fam = ensure_objective_family(obj.family)
            stat = ensure_stat(obj.stat) if obj.stat is not None else None
            self.objective = ObjectiveSpec(family=fam, stat=stat, win=obj.win)

        if isinstance(self.hamming_wordlist_dir, (str, bytes)):
            self.hamming_wordlist_dir = Path(self.hamming_wordlist_dir)
        if isinstance(self.hamming_dictionary_policy_root, (str, bytes)):
            self.hamming_dictionary_policy_root = Path(self.hamming_dictionary_policy_root)
        if isinstance(self.span_hamming_wordlist_dir, (str, bytes)):
            self.span_hamming_wordlist_dir = Path(self.span_hamming_wordlist_dir)
        if isinstance(self.span_hamming_assets_dir, (str, bytes)):
            self.span_hamming_assets_dir = Path(self.span_hamming_assets_dir)
        if isinstance(self.span_hamming_lm_assets_json, (str, bytes)):
            self.span_hamming_lm_assets_json = Path(self.span_hamming_lm_assets_json)
        if isinstance(self.word_ngram_judge_sqlite_path, (str, bytes)):
            self.word_ngram_judge_sqlite_path = Path(self.word_ngram_judge_sqlite_path)
        self.hamming_direction_mode = ensure_hamming_direction_mode(self.hamming_direction_mode)
        self.hamming_ramp_start_frac = float(self.hamming_ramp_start_frac)
        self.hamming_ramp_end_frac = float(self.hamming_ramp_end_frac)
        self.span_hamming_weight = float(self.span_hamming_weight)
        self.span_hamming_len_min = int(self.span_hamming_len_min)
        self.span_hamming_len_max = int(self.span_hamming_len_max)
        self.span_hamming_max_hd = int(self.span_hamming_max_hd)
        self.span_hamming_start_stride = int(self.span_hamming_start_stride)
        self.span_hamming_max_windows_total = int(self.span_hamming_max_windows_total)
        self.span_hamming_max_candidates_per_window = int(self.span_hamming_max_candidates_per_window)
        self.span_hamming_max_intervals_considered_per_start = int(self.span_hamming_max_intervals_considered_per_start)
        self.span_hamming_min_quality_threshold = float(self.span_hamming_min_quality_threshold)
        if self.span_hamming_len_min < 1:
            raise ValueError("span_hamming_len_min must be >= 1")
        if self.span_hamming_len_max < self.span_hamming_len_min:
            raise ValueError("span_hamming_len_max must be >= span_hamming_len_min")
        if self.span_hamming_max_hd < 0:
            raise ValueError("span_hamming_max_hd must be >= 0")
        if self.span_hamming_start_stride < 1:
            raise ValueError("span_hamming_start_stride must be >= 1")
        if self.span_hamming_max_windows_total < 0:
            raise ValueError("span_hamming_max_windows_total must be >= 0")
        if self.span_hamming_max_candidates_per_window < 1:
            raise ValueError("span_hamming_max_candidates_per_window must be >= 1")
        if self.span_hamming_max_intervals_considered_per_start < 1:
            raise ValueError("span_hamming_max_intervals_considered_per_start must be >= 1")
        if not (0.0 <= self.span_hamming_min_quality_threshold <= 1.0):
            raise ValueError("span_hamming_min_quality_threshold must be in [0,1]")
        self.span_hamming_mode = ensure_span_hamming_mode(self.span_hamming_mode)
        if self.span_hamming_assets_dictionary_policy is not None:
            self.span_hamming_assets_dictionary_policy = ensure_hamming_dictionary_policy(
                self.span_hamming_assets_dictionary_policy
            )
        self.span_hamming_bucket_policy = ensure_span_hamming_bucket_policy(
            self.span_hamming_bucket_policy
        )
        self.span_hamming_combine_mode = ensure_span_hamming_combine_mode(
            self.span_hamming_combine_mode
        )
        self.span_hamming_gate_fail_policy = ensure_span_hamming_gate_fail_policy(
            self.span_hamming_gate_fail_policy
        )
        self.span_hamming_weight_span = float(self.span_hamming_weight_span)
        self.span_hamming_weight_char = float(self.span_hamming_weight_char)
        self.span_hamming_coverage_min = float(self.span_hamming_coverage_min)
        self.span_hamming_quality_min = float(self.span_hamming_quality_min)
        if not (0.0 <= self.span_hamming_coverage_min <= 1.0):
            raise ValueError("span_hamming_coverage_min must be in [0,1]")
        if not (0.0 <= self.span_hamming_quality_min <= 1.0):
            raise ValueError("span_hamming_quality_min must be in [0,1]")
        if self.span_hamming_span_pct_min is not None:
            self.span_hamming_span_pct_min = float(self.span_hamming_span_pct_min)
            if not (0.0 <= self.span_hamming_span_pct_min <= 1.0):
                raise ValueError("span_hamming_span_pct_min must be in [0,1]")
        if self.span_hamming_char_pct_min is not None:
            self.span_hamming_char_pct_min = float(self.span_hamming_char_pct_min)
            if not (0.0 <= self.span_hamming_char_pct_min <= 1.0):
                raise ValueError("span_hamming_char_pct_min must be in [0,1]")
        if self.span_hamming_ecdf_clamp_min is not None:
            self.span_hamming_ecdf_clamp_min = float(self.span_hamming_ecdf_clamp_min)
            if not (0.0 < self.span_hamming_ecdf_clamp_min < 1.0):
                raise ValueError("span_hamming_ecdf_clamp_min must be in (0,1)")
        if self.span_hamming_ecdf_clamp_max is not None:
            self.span_hamming_ecdf_clamp_max = float(self.span_hamming_ecdf_clamp_max)
            if not (0.0 < self.span_hamming_ecdf_clamp_max < 1.0):
                raise ValueError("span_hamming_ecdf_clamp_max must be in (0,1)")
        if self.span_hamming_ecdf_clamp_min is not None and self.span_hamming_ecdf_clamp_max is not None:
            if not (self.span_hamming_ecdf_clamp_min < self.span_hamming_ecdf_clamp_max):
                raise ValueError("span_hamming_ecdf_clamp_min must be < span_hamming_ecdf_clamp_max")
        if self.span_hamming_gate_score_floor is not None:
            self.span_hamming_gate_score_floor = float(self.span_hamming_gate_score_floor)
        self.span_hamming_lm_profile_source = ensure_span_hamming_lm_profile_source(
            self.span_hamming_lm_profile_source
        )
        self.span_hamming_lm_tail_start_index = int(self.span_hamming_lm_tail_start_index)
        if self.span_hamming_lm_tail_start_index < 0:
            raise ValueError("span_hamming_lm_tail_start_index must be >= 0")
        self.span_hamming_lm_weight = float(self.span_hamming_lm_weight)
        if self.span_hamming_lm_weight != 0.0 and self.span_hamming_lm_assets_json is None:
            raise ValueError(
                "span_hamming_lm_assets_json is required when span_hamming_lm_weight is non-zero"
            )
        self.word_ngram_judge_enabled = bool(self.word_ngram_judge_enabled)
        self.word_ngram_judge_alpha = float(self.word_ngram_judge_alpha)
        if not (0.0 < self.word_ngram_judge_alpha <= 1.0):
            raise ValueError("word_ngram_judge_alpha must be in (0,1]")
        self.word_ngram_judge_miss_logp = float(self.word_ngram_judge_miss_logp)
        self.word_ngram_judge_min_positions = int(self.word_ngram_judge_min_positions)
        if self.word_ngram_judge_min_positions < 0:
            raise ValueError("word_ngram_judge_min_positions must be >= 0")
        self.word_ngram_judge_prefix_total_thresholds = tuple(
            int(v) for v in self.word_ngram_judge_prefix_total_thresholds
        )
        if any(int(v) < 0 for v in self.word_ngram_judge_prefix_total_thresholds):
            raise ValueError("word_ngram_judge_prefix_total_thresholds must be >= 0")
        if self.word_ngram_judge_enabled and self.word_ngram_judge_sqlite_path is None:
            raise ValueError(
                "word_ngram_judge_sqlite_path is required when word_ngram_judge_enabled is true"
            )
        if self.hamming_dictionary_policy is not None:
            self.hamming_dictionary_policy = ensure_hamming_dictionary_policy(self.hamming_dictionary_policy)

        obj = getattr(self, "objective", None)
        if isinstance(obj, ObjectiveSpec) and obj.family in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
            if obj.stat is None:
                obj = ObjectiveSpec(family=obj.family, stat=Stat.LOGP, win=obj.win)
                self.objective = obj
            if obj.win is None:
                legacy_win = getattr(self, "win", None)
                if legacy_win is None:
                    raise ValueError("ObjectiveSpec.win is required for pct/energy objectives.")
                self.objective = ObjectiveSpec(family=obj.family, stat=obj.stat, win=int(legacy_win))
                obj = self.objective
            if int(obj.win) != 10:
                raise ValueError("pct/energy objectives only support win=10 in the current LM tables.")
            self.win = int(obj.win)
        if isinstance(obj, ObjectiveSpec) and obj.family is ObjectiveFamily.AVG:
            if obj.stat is None:
                obj = ObjectiveSpec(family=obj.family, stat=Stat.LOGP, win=obj.win)
                self.objective = obj
            if obj.win is None:
                legacy_win = getattr(self, "win", None)
                if legacy_win is None:
                    raise ValueError("ObjectiveSpec.win is required for avg objectives.")
                obj = ObjectiveSpec(family=obj.family, stat=obj.stat, win=int(legacy_win))
                self.objective = obj
            self.win = int(obj.win)

        self.stride = int(self.stride or 1)
        if self.stride <= 0:
            raise ValueError("stride must be >= 1")

        self.char_weights = self._normalise_channel_weights(self.char_weights, 'char_weights')
        self.wli_weights = self._normalise_channel_weights(self.wli_weights, 'wli_weights')
        self.hard_crib = normalize_hard_crib_config(self.hard_crib)

        if not bool(self.maximize):
            raise ValueError("maximize must be True; objectives are defined as higher-is-better")
        self.maximize = True

    def requested_scorer_lanes(self) -> tuple[ScorerLaneName, ...]:
        """Return optional scorer lanes explicitly requested by this config.

        This method is configuration-only. It must not import scorer backends,
        read assets, construct scorer objects, or change runtime scoring.
        """
        lanes: list[ScorerLaneName] = []

        hamming_weight = self.hamming_weight
        if bool(self.hamming_enabled) or (
            hamming_weight is not None and float(hamming_weight) != 0.0
        ):
            lanes.append(ScorerLaneName.HAMMING)

        span_mode = self.span_hamming_mode
        raw_span_requested = (
            span_mode is SpanHammingMode.RAW_BONUS
            or bool(self.span_hamming_enabled)
            or float(self.span_hamming_weight) != 0.0
        )

        if span_mode is SpanHammingMode.CALIBRATED:
            lanes.append(ScorerLaneName.SPAN_HAMMING_CALIBRATED)
        elif raw_span_requested:
            lanes.append(ScorerLaneName.SPAN_HAMMING_RAW)

        if bool(self.word_ngram_judge_enabled):
            lanes.append(ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY)

        return tuple(lanes)

    def asdict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["model_root"] = str(self.model_root) if isinstance(self.model_root, Path) else self.model_root
        out["smoothing"] = self.smoothing
        out["alpha"] = self.alpha
        out["oov_policy"] = self.oov_policy
        out["include_char"] = self.include_char
        out["use_word_breaks"] = self.use_word_breaks
        out["n_char"] = self.n_char
        out["n_wli"] = self.n_wli
        out["win"] = self.win
        out["stride"] = self.stride
        out["se_mode"] = self.se_mode.value if isinstance(self.se_mode, SeMode) else self.se_mode
        out["objective"] = {
            "family": (
                self.objective.family.value
                if isinstance(self.objective.family, ObjectiveFamily)
                else self.objective.family
            ),
            "stat": (
                self.objective.stat.value
                if isinstance(self.objective.stat, Stat)
                else self.objective.stat
            ) if self.objective.stat is not None else None,
            "win": (int(self.objective.win) if self.objective.win is not None else None),
        }
        out["avg_window_policy"] = (
            self.avg_window_policy.value
            if isinstance(self.avg_window_policy, AvgWindowPolicy)
            else self.avg_window_policy
        )
        out["maximize"] = self.maximize
        out["encoding_dir"] = self.encoding_dir.value if isinstance(self.encoding_dir, Direction) else self.encoding_dir
        out["weights"] = [float(v) for v in tuple(self.weights or ())]
        out["char_weights"] = {str(int(k)): float(v) for k, v in dict(self.char_weights or {}).items()}
        out["wli_weights"] = {str(int(k)): float(v) for k, v in dict(self.wli_weights or {}).items()}
        out["impl"] = self.impl.value if isinstance(self.impl, ScorerImpl) else self.impl
        out["compute_dtype"] = self.compute_dtype.value if isinstance(self.compute_dtype, FloatDType) else self.compute_dtype
        out["acc_dtype"] = self.acc_dtype.value if isinstance(self.acc_dtype, FloatDType) else self.acc_dtype
        out["dtype"] = self.dtype.value if isinstance(self.dtype, FloatDType) else self.dtype
        out["ecdf_clamp_min"] = self.ecdf_clamp_min
        out["ecdf_clamp_max"] = self.ecdf_clamp_max
        out["diagnostics_enabled"] = self.diagnostics_enabled
        out["hard_crib"] = self.hard_crib.asdict() if isinstance(self.hard_crib, HardCribConfig) else None
        out["hamming_enabled"] = self.hamming_enabled
        out["hamming_dictionary_policy"] = (
            self.hamming_dictionary_policy.value
            if isinstance(self.hamming_dictionary_policy, HammingDictionaryPolicy)
            else self.hamming_dictionary_policy
        )
        out["hamming_dictionary_policy_root"] = (
            str(self.hamming_dictionary_policy_root)
            if isinstance(self.hamming_dictionary_policy_root, Path)
            else self.hamming_dictionary_policy_root
        )
        out["hamming_wordlist_dir"] = str(self.hamming_wordlist_dir) if isinstance(self.hamming_wordlist_dir, Path) else self.hamming_wordlist_dir
        out["hamming_build_rtl"] = self.hamming_build_rtl
        out["hamming_weight"] = self.hamming_weight
        out["hamming_weight_max"] = self.hamming_weight_max
        out["hamming_ramp_start_frac"] = self.hamming_ramp_start_frac
        out["hamming_ramp_end_frac"] = self.hamming_ramp_end_frac
        out["hamming_max_hd"] = self.hamming_max_hd
        out["hamming_length_weights"] = {
            str(int(k)): float(v) for k, v in dict(self.hamming_length_weights or {}).items()
        }
        out["hamming_direction_mode"] = self.hamming_direction_mode.value
        out["span_hamming_enabled"] = self.span_hamming_enabled
        out["span_hamming_wordlist_dir"] = str(self.span_hamming_wordlist_dir) if isinstance(self.span_hamming_wordlist_dir, Path) else self.span_hamming_wordlist_dir
        out["span_hamming_weight"] = self.span_hamming_weight
        out["span_hamming_len_min"] = self.span_hamming_len_min
        out["span_hamming_len_max"] = self.span_hamming_len_max
        out["span_hamming_max_hd"] = self.span_hamming_max_hd
        out["span_hamming_start_stride"] = self.span_hamming_start_stride
        out["span_hamming_max_windows_total"] = self.span_hamming_max_windows_total
        out["span_hamming_max_candidates_per_window"] = self.span_hamming_max_candidates_per_window
        out["span_hamming_max_intervals_considered_per_start"] = self.span_hamming_max_intervals_considered_per_start
        out["span_hamming_min_quality_threshold"] = self.span_hamming_min_quality_threshold
        out["span_hamming_debug_return_intervals"] = self.span_hamming_debug_return_intervals
        out["span_hamming_require_selected"] = self.span_hamming_require_selected
        out["span_hamming_mode"] = self.span_hamming_mode.value
        out["span_hamming_assets_dir"] = str(self.span_hamming_assets_dir) if isinstance(self.span_hamming_assets_dir, Path) else self.span_hamming_assets_dir
        out["span_hamming_assets_dictionary_policy"] = (
            self.span_hamming_assets_dictionary_policy.value
            if isinstance(self.span_hamming_assets_dictionary_policy, HammingDictionaryPolicy)
            else self.span_hamming_assets_dictionary_policy
        )
        out["span_hamming_allow_dictionary_policy_mismatch"] = bool(
            self.span_hamming_allow_dictionary_policy_mismatch
        )
        out["span_hamming_bucket_policy"] = self.span_hamming_bucket_policy.value
        out["span_hamming_ecdf_clamp_min"] = self.span_hamming_ecdf_clamp_min
        out["span_hamming_ecdf_clamp_max"] = self.span_hamming_ecdf_clamp_max
        out["span_hamming_combine_mode"] = self.span_hamming_combine_mode.value
        out["span_hamming_weight_span"] = self.span_hamming_weight_span
        out["span_hamming_weight_char"] = self.span_hamming_weight_char
        out["span_hamming_coverage_min"] = self.span_hamming_coverage_min
        out["span_hamming_quality_min"] = self.span_hamming_quality_min
        out["span_hamming_span_pct_min"] = self.span_hamming_span_pct_min
        out["span_hamming_char_pct_min"] = self.span_hamming_char_pct_min
        out["span_hamming_gate_fail_policy"] = self.span_hamming_gate_fail_policy.value
        out["span_hamming_gate_score_floor"] = self.span_hamming_gate_score_floor
        out["span_hamming_lm_assets_json"] = (
            str(self.span_hamming_lm_assets_json)
            if isinstance(self.span_hamming_lm_assets_json, Path)
            else self.span_hamming_lm_assets_json
        )
        out["span_hamming_lm_profile_source"] = self.span_hamming_lm_profile_source.value
        out["span_hamming_lm_tail_start_index"] = self.span_hamming_lm_tail_start_index
        out["span_hamming_lm_weight"] = self.span_hamming_lm_weight
        out["word_ngram_judge_enabled"] = bool(self.word_ngram_judge_enabled)
        out["word_ngram_judge_sqlite_path"] = (
            str(self.word_ngram_judge_sqlite_path)
            if isinstance(self.word_ngram_judge_sqlite_path, Path)
            else self.word_ngram_judge_sqlite_path
        )
        out["word_ngram_judge_alpha"] = self.word_ngram_judge_alpha
        out["word_ngram_judge_miss_logp"] = self.word_ngram_judge_miss_logp
        out["word_ngram_judge_min_positions"] = self.word_ngram_judge_min_positions
        out["word_ngram_judge_prefix_total_thresholds"] = [
            int(v) for v in tuple(self.word_ngram_judge_prefix_total_thresholds)
        ]
        return out



    @staticmethod
    def _normalise_channel_weights(weights: Any, field_name: str) -> Dict[int, float]:
        if weights in (None, {}):
            return {}
        if isinstance(weights, dict):
            iterable = weights.items()
        elif isinstance(weights, (list, tuple)):
            iterable = weights
        else:
            raise TypeError(f"{field_name} must be a dict or list of (n, weight) pairs as documented")

        normalised: Dict[int, float] = {}
        for item in iterable:
            if isinstance(item, dict):
                if len(item) != 1:
                    raise ValueError(f"{field_name} dict entries must contain a single (n, weight) mapping")
                ((key, value),) = item.items()
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                key, value = item
            else:
                raise TypeError(f"{field_name} entries must be (n, weight) pairs")

            try:
                n_val = int(key)
            except Exception as exc:
                raise TypeError(f"{field_name} keys must be integers (n-gram length)") from exc
            if n_val <= 0:
                raise ValueError(f"{field_name} keys must be positive integers per scoring docs")

            try:
                weight_val = float(value)
            except Exception as exc:
                raise TypeError(f"{field_name} values must be numeric weights") from exc
            if not math.isfinite(weight_val):
                raise ValueError(f"{field_name} weights must be finite numbers")

            normalised[n_val] = weight_val

        return normalised
