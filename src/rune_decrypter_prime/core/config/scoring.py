"""Immutable public scoring request and objective contracts."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from rdp.core.component_contracts import ScoringLane
from rune_decrypter_prime.core.config.hard_crib import (
    HardCribConfig,
    normalize_hard_crib_config,
)
from rdp.core.hamming_dictionary_policy import HammingDictionaryPolicy
from rdp.core.types import (
    AverageWindowPolicy,
    FloatDType,
    HammingTextDirectionMode,
    JsonObject,
    LanguageModelBoundaryMode,
    OutOfVocabularyPolicy,
    ScoreDirection,
    ScoreStatistic,
    ScorerBackend,
    ScoringObjectiveKind,
    SmoothingMethod,
    SpanHammingBucketPolicy,
    SpanHammingCombineMode,
    SpanHammingGateFailurePolicy,
    SpanHammingLanguageModelProfileSource,
    SpanHammingMode,
)


def ensure_hamming_text_direction_mode(value: object) -> HammingTextDirectionMode:
    return _enum_value(HammingTextDirectionMode, value, "hamming_text_direction_mode")  # type: ignore[return-value]


def ensure_span_hamming_mode(value: object) -> SpanHammingMode:
    return _enum_value(SpanHammingMode, value, "span_hamming_mode")  # type: ignore[return-value]


def ensure_span_hamming_bucket_policy(value: object) -> SpanHammingBucketPolicy:
    return _enum_value(SpanHammingBucketPolicy, value, "span_hamming_bucket_policy")  # type: ignore[return-value]


def ensure_span_hamming_combine_mode(value: object) -> SpanHammingCombineMode:
    return _enum_value(SpanHammingCombineMode, value, "span_hamming_combine_mode")  # type: ignore[return-value]


def ensure_span_hamming_gate_failure_policy(value: object) -> SpanHammingGateFailurePolicy:
    return _enum_value(SpanHammingGateFailurePolicy, value, "span_hamming_gate_failure_policy")  # type: ignore[return-value]


def ensure_span_hamming_language_model_profile_source(
    value: object,
) -> SpanHammingLanguageModelProfileSource:
    return _enum_value(
        SpanHammingLanguageModelProfileSource,
        value,
        "span_hamming_language_model_profile_source",
    )  # type: ignore[return-value]


def _enum_value(enum_type: type[Enum], value: object, field_name: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    raise TypeError(f"{field_name} must be {enum_type.__name__}")


def _finite_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def _positive_int(value: object, field_name: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    minimum = 0 if allow_zero else 1
    if value < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    return value


def _path(value: object, field_name: str) -> Path | None:
    if value is None or isinstance(value, Path):
        return value
    raise TypeError(f"{field_name} must be Path or None")


def _weight_map(
    value: Mapping[int, float] | None,
    field_name: str,
    *,
    allow_none: bool = True,
) -> Mapping[int, float] | None:
    if value is None:
        if allow_none:
            return None
        value = {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    normalised: dict[int, float] = {}
    for key, weight in value.items():
        if isinstance(key, bool) or not isinstance(key, int) or key < 1:
            raise ValueError(f"{field_name} keys must be positive integers")
        number = _finite_float(weight, f"{field_name}[{key}]")
        if number < 0.0:
            raise ValueError(f"{field_name} weights must be non-negative")
        normalised[int(key)] = number
    return MappingProxyType(normalised)


@dataclass(frozen=True, slots=True)
class ScoringObjective:
    kind: ScoringObjectiveKind
    statistic: ScoreStatistic | None = None
    window_size: int | None = None

    def __post_init__(self) -> None:
        _enum_value(ScoringObjectiveKind, self.kind, "kind")
        if self.statistic is not None:
            _enum_value(ScoreStatistic, self.statistic, "statistic")
        if self.window_size is not None:
            _positive_int(self.window_size, "window_size")
        if self.kind is ScoringObjectiveKind.PERCENTILE:
            if self.statistic is None or self.window_size is None:
                raise ValueError("percentile objectives require statistic and window_size")
        elif self.kind is ScoringObjectiveKind.AVERAGE:
            if self.statistic is not ScoreStatistic.LOG_PROBABILITY or self.window_size is not None:
                raise ValueError("average objective is log probability over the full text")
        elif self.kind is ScoringObjectiveKind.NEGATIVE_LOG_PROBABILITY:
            if self.statistic is not None or self.window_size is not None:
                raise ValueError("negative-log-probability objective has no statistic or window_size")

    @classmethod
    def percentile_log_probability(cls, *, window_size: int = 10) -> ScoringObjective:
        return cls(ScoringObjectiveKind.PERCENTILE, ScoreStatistic.LOG_PROBABILITY, window_size)

    @classmethod
    def percentile_z_score_sum(cls, *, window_size: int = 10) -> ScoringObjective:
        return cls(ScoringObjectiveKind.PERCENTILE, ScoreStatistic.Z_SCORE_SUM, window_size)

    @classmethod
    def percentile_median_absolute_deviation_sum(
        cls, *, window_size: int = 10
    ) -> ScoringObjective:
        return cls(
            ScoringObjectiveKind.PERCENTILE,
            ScoreStatistic.MEDIAN_ABSOLUTE_DEVIATION_SUM,
            window_size,
        )

    @classmethod
    def average_log_probability(cls) -> ScoringObjective:
        return cls(ScoringObjectiveKind.AVERAGE, ScoreStatistic.LOG_PROBABILITY)

    @classmethod
    def negative_log_probability(cls) -> ScoringObjective:
        return cls(ScoringObjectiveKind.NEGATIVE_LOG_PROBABILITY)

    def to_dict(self) -> JsonObject:
        return {
            "kind": self.kind.value,
            "statistic": self.statistic.value if self.statistic is not None else None,
            "window_size": self.window_size,
        }


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    language_model_root: Path | None = None
    smoothing: SmoothingMethod = SmoothingMethod.AUTO_GOOD_TURING
    smoothing_alpha: float = 0.5
    out_of_vocabulary_policy: OutOfVocabularyPolicy = OutOfVocabularyPolicy.FLOOR_MINIMUM_SEEN
    character_lane_enabled: bool = True
    word_length_lane_enabled: bool = True
    character_ngram_order: int = 2
    word_length_ngram_order: int = 2
    window_size: int = 10
    stride: int = 1
    boundary_mode: LanguageModelBoundaryMode = LanguageModelBoundaryMode.EXCLUDE_BOUNDARIES
    base_lane_weights: tuple[float, float] | None = None
    score_direction: ScoreDirection = ScoreDirection.MAXIMIZE
    character_order_weights: Mapping[int, float] | None = None
    word_length_order_weights: Mapping[int, float] | None = None
    backend: ScorerBackend = ScorerBackend.AUTO
    compute_dtype: FloatDType = FloatDType.FLOAT32
    accumulator_dtype: FloatDType = FloatDType.FLOAT64
    objective: ScoringObjective = field(default_factory=ScoringObjective.percentile_log_probability)
    average_window_policy: AverageWindowPolicy = AverageWindowPolicy.FIXED_WINDOW
    ecdf_clamp_minimum: float = 1e-6
    ecdf_clamp_maximum: float = 1.0 - 1e-6
    diagnostics_enabled: bool = False
    hard_crib: HardCribConfig | None = None
    hamming_enabled: bool = False
    hamming_dictionary_policy: HammingDictionaryPolicy = HammingDictionaryPolicy.NORMAL
    hamming_dictionary_root: Path | None = None
    hamming_wordlist_directory: Path | None = None
    hamming_build_right_to_left: bool = False
    hamming_weight: float | None = None
    hamming_maximum_weight: float = 0.01
    hamming_ramp_start_fraction: float = 0.2
    hamming_ramp_end_fraction: float = 0.7
    hamming_maximum_distance: int = 1_000_000
    hamming_length_weights: Mapping[int, float] = field(default_factory=dict)
    hamming_text_direction_mode: HammingTextDirectionMode = HammingTextDirectionMode.MATCH_TEXT
    span_hamming_enabled: bool = False
    span_hamming_wordlist_directory: Path | None = None
    span_hamming_weight: float = 0.0
    span_hamming_minimum_length: int = 3
    span_hamming_maximum_length: int = 14
    span_hamming_maximum_distance: int = 2
    span_hamming_start_stride: int = 1
    span_hamming_maximum_windows: int = 0
    span_hamming_maximum_candidates_per_window: int = 256
    span_hamming_maximum_intervals_per_start: int = 4
    span_hamming_minimum_quality: float = 1e-9
    span_hamming_return_debug_intervals: bool = False
    span_hamming_require_selection: bool = True
    span_hamming_mode: SpanHammingMode = SpanHammingMode.OFF
    span_hamming_assets_directory: Path | None = None
    span_hamming_assets_dictionary_policy: HammingDictionaryPolicy | None = None
    span_hamming_allow_dictionary_mismatch: bool = False
    span_hamming_bucket_policy: SpanHammingBucketPolicy = SpanHammingBucketPolicy.NEAREST_SMALLER_ON_TIE
    span_hamming_ecdf_clamp_minimum: float | None = None
    span_hamming_ecdf_clamp_maximum: float | None = None
    span_hamming_combine_mode: SpanHammingCombineMode = SpanHammingCombineMode.MINIMUM
    span_hamming_span_weight: float = 1.0
    span_hamming_character_weight: float = 0.0
    span_hamming_minimum_coverage: float = 0.0
    span_hamming_minimum_gate_quality: float = 0.0
    span_hamming_minimum_span_percentile: float | None = None
    span_hamming_minimum_character_percentile: float | None = None
    span_hamming_gate_failure_policy: SpanHammingGateFailurePolicy = SpanHammingGateFailurePolicy.SCORE_FLOOR
    span_hamming_gate_score_floor: float | None = None
    span_hamming_language_model_assets: Path | None = None
    span_hamming_language_model_profile_source: SpanHammingLanguageModelProfileSource = SpanHammingLanguageModelProfileSource.RAW_SPAN_BY_LENGTH
    span_hamming_language_model_tail_start: int = 5
    span_hamming_language_model_weight: float = 0.0
    word_ngram_judge_enabled: bool = False
    word_ngram_judge_database: Path | None = None
    word_ngram_judge_alpha: float = 0.4
    word_ngram_judge_missing_log_probability: float = -20.0
    word_ngram_judge_minimum_positions: int = 12
    word_ngram_judge_prefix_thresholds: tuple[int, ...] = (1, 10, 100)

    def __post_init__(self) -> None:
        enum_fields: tuple[tuple[str, type[Enum]], ...] = (
            ("smoothing", SmoothingMethod),
            ("out_of_vocabulary_policy", OutOfVocabularyPolicy),
            ("boundary_mode", LanguageModelBoundaryMode),
            ("score_direction", ScoreDirection),
            ("backend", ScorerBackend),
            ("compute_dtype", FloatDType),
            ("accumulator_dtype", FloatDType),
            ("average_window_policy", AverageWindowPolicy),
            ("hamming_dictionary_policy", HammingDictionaryPolicy),
            ("hamming_text_direction_mode", HammingTextDirectionMode),
            ("span_hamming_mode", SpanHammingMode),
            ("span_hamming_bucket_policy", SpanHammingBucketPolicy),
            ("span_hamming_combine_mode", SpanHammingCombineMode),
            ("span_hamming_gate_failure_policy", SpanHammingGateFailurePolicy),
            ("span_hamming_language_model_profile_source", SpanHammingLanguageModelProfileSource),
        )
        for name, enum_type in enum_fields:
            _enum_value(enum_type, getattr(self, name), name)
        if not isinstance(self.objective, ScoringObjective):
            raise TypeError("objective must be ScoringObjective")
        if self.span_hamming_assets_dictionary_policy is not None:
            _enum_value(
                HammingDictionaryPolicy,
                self.span_hamming_assets_dictionary_policy,
                "span_hamming_assets_dictionary_policy",
            )

        for name in (
            "language_model_root",
            "hamming_dictionary_root",
            "hamming_wordlist_directory",
            "span_hamming_wordlist_directory",
            "span_hamming_assets_directory",
            "span_hamming_language_model_assets",
            "word_ngram_judge_database",
        ):
            object.__setattr__(self, name, _path(getattr(self, name), name))

        for name in (
            "character_ngram_order",
            "word_length_ngram_order",
            "window_size",
            "stride",
            "span_hamming_minimum_length",
            "span_hamming_maximum_length",
            "span_hamming_start_stride",
            "span_hamming_maximum_candidates_per_window",
            "span_hamming_maximum_intervals_per_start",
        ):
            _positive_int(getattr(self, name), name)
        for name in (
            "hamming_maximum_distance",
            "span_hamming_maximum_distance",
            "span_hamming_maximum_windows",
            "span_hamming_language_model_tail_start",
            "word_ngram_judge_minimum_positions",
        ):
            _positive_int(getattr(self, name), name, allow_zero=True)
        if self.span_hamming_maximum_length < self.span_hamming_minimum_length:
            raise ValueError("span_hamming_maximum_length must be >= span_hamming_minimum_length")

        for name in (
            "smoothing_alpha",
            "ecdf_clamp_minimum",
            "ecdf_clamp_maximum",
            "hamming_maximum_weight",
            "hamming_ramp_start_fraction",
            "hamming_ramp_end_fraction",
            "span_hamming_weight",
            "span_hamming_minimum_quality",
            "span_hamming_span_weight",
            "span_hamming_character_weight",
            "span_hamming_minimum_coverage",
            "span_hamming_minimum_gate_quality",
            "span_hamming_language_model_weight",
            "word_ngram_judge_alpha",
            "word_ngram_judge_missing_log_probability",
        ):
            object.__setattr__(self, name, _finite_float(getattr(self, name), name))
        for name in (
            "hamming_weight",
            "span_hamming_ecdf_clamp_minimum",
            "span_hamming_ecdf_clamp_maximum",
            "span_hamming_minimum_span_percentile",
            "span_hamming_minimum_character_percentile",
            "span_hamming_gate_score_floor",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _finite_float(value, name))
        if not 0.0 < self.ecdf_clamp_minimum < self.ecdf_clamp_maximum < 1.0:
            raise ValueError("ECDF clamps must satisfy 0 < minimum < maximum < 1")
        for name in (
            "hamming_ramp_start_fraction",
            "hamming_ramp_end_fraction",
            "span_hamming_minimum_quality",
            "span_hamming_minimum_coverage",
            "span_hamming_minimum_gate_quality",
        ):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.hamming_ramp_start_fraction > self.hamming_ramp_end_fraction:
            raise ValueError("hamming ramp start must not exceed its end")

        pair = self.base_lane_weights
        if pair is not None:
            if type(pair) is not tuple or len(pair) != 2:
                raise TypeError("base_lane_weights must be tuple[float, float] or None")
            pair = tuple(_finite_float(value, "base_lane_weights") for value in pair)
            if any(value < 0.0 for value in pair) or sum(pair) <= 0.0:
                raise ValueError("base_lane_weights must be non-negative with a positive total")
            object.__setattr__(self, "base_lane_weights", pair)

        character_weights = _weight_map(self.character_order_weights, "character_order_weights")
        word_length_weights = _weight_map(self.word_length_order_weights, "word_length_order_weights")
        if pair is not None and (character_weights or word_length_weights):
            raise ValueError("base_lane_weights cannot be combined with per-order weights")
        object.__setattr__(self, "character_order_weights", character_weights)
        object.__setattr__(self, "word_length_order_weights", word_length_weights)
        object.__setattr__(
            self,
            "hamming_length_weights",
            _weight_map(self.hamming_length_weights, "hamming_length_weights", allow_none=False),
        )
        object.__setattr__(self, "hard_crib", normalize_hard_crib_config(self.hard_crib))

        thresholds = self.word_ngram_judge_prefix_thresholds
        if type(thresholds) is not tuple:
            raise TypeError("word_ngram_judge_prefix_thresholds must be tuple[int, ...]")
        for index, value in enumerate(thresholds):
            _positive_int(value, f"word_ngram_judge_prefix_thresholds[{index}]", allow_zero=True)
        if self.word_ngram_judge_enabled and self.word_ngram_judge_database is None:
            raise ValueError("word_ngram_judge_database is required when its lane is enabled")
        if self.span_hamming_language_model_weight and self.span_hamming_language_model_assets is None:
            raise ValueError("span_hamming_language_model_assets is required for a non-zero LM weight")

        self.effective_lm_model_weights()

    @classmethod
    def from_dict(cls, values: JsonObject, /) -> ScoringConfig:
        if not isinstance(values, dict):
            raise TypeError("values must be a dict")
        known = {item.name for item in fields(cls)}
        unknown = sorted(set(values) - known)
        if unknown:
            raise ValueError(f"unknown ScoringConfig fields: {', '.join(unknown)}")
        payload: dict[str, Any] = dict(values)
        enum_fields: dict[str, type[Enum]] = {
            "smoothing": SmoothingMethod,
            "out_of_vocabulary_policy": OutOfVocabularyPolicy,
            "boundary_mode": LanguageModelBoundaryMode,
            "score_direction": ScoreDirection,
            "backend": ScorerBackend,
            "compute_dtype": FloatDType,
            "accumulator_dtype": FloatDType,
            "average_window_policy": AverageWindowPolicy,
            "hamming_dictionary_policy": HammingDictionaryPolicy,
            "hamming_text_direction_mode": HammingTextDirectionMode,
            "span_hamming_mode": SpanHammingMode,
            "span_hamming_assets_dictionary_policy": HammingDictionaryPolicy,
            "span_hamming_bucket_policy": SpanHammingBucketPolicy,
            "span_hamming_combine_mode": SpanHammingCombineMode,
            "span_hamming_gate_failure_policy": SpanHammingGateFailurePolicy,
            "span_hamming_language_model_profile_source": SpanHammingLanguageModelProfileSource,
        }
        for name, enum_type in enum_fields.items():
            if name in payload and payload[name] is not None:
                payload[name] = enum_type(payload[name])
        if "objective" in payload and isinstance(payload["objective"], dict):
            objective = payload["objective"]
            payload["objective"] = ScoringObjective(
                kind=ScoringObjectiveKind(objective["kind"]),
                statistic=(ScoreStatistic(objective["statistic"]) if objective.get("statistic") else None),
                window_size=objective.get("window_size"),
            )
        for name in (
            "language_model_root",
            "hamming_dictionary_root",
            "hamming_wordlist_directory",
            "span_hamming_wordlist_directory",
            "span_hamming_assets_directory",
            "span_hamming_language_model_assets",
            "word_ngram_judge_database",
        ):
            if payload.get(name) is not None:
                payload[name] = Path(str(payload[name]))
        if "word_ngram_judge_prefix_thresholds" in payload:
            payload["word_ngram_judge_prefix_thresholds"] = tuple(payload["word_ngram_judge_prefix_thresholds"])
        if payload.get("base_lane_weights") is not None:
            payload["base_lane_weights"] = tuple(payload["base_lane_weights"])
        for name in (
            "character_order_weights",
            "word_length_order_weights",
            "hamming_length_weights",
        ):
            if isinstance(payload.get(name), Mapping):
                payload[name] = {int(key): value for key, value in payload[name].items()}
        return cls(**payload)

    def requested_scorer_lanes(self) -> tuple[ScoringLane, ...]:
        lanes: list[ScoringLane] = []
        if self.hamming_enabled or (self.hamming_weight is not None and self.hamming_weight != 0.0):
            lanes.append(ScoringLane.HAMMING)
        if self.span_hamming_mode is SpanHammingMode.CALIBRATED:
            lanes.append(ScoringLane.SPAN_HAMMING_CALIBRATED)
        elif (
            self.span_hamming_mode is SpanHammingMode.RAW_BONUS
            or self.span_hamming_enabled
            or self.span_hamming_weight != 0.0
        ):
            lanes.append(ScoringLane.SPAN_HAMMING_RAW)
        if self.word_ngram_judge_enabled:
            lanes.append(ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY)
        return tuple(lanes)

    def effective_lm_model_weights(
        self, *, use_word_lengths: bool | None = None
    ) -> tuple[tuple[str, int, float], ...]:
        use_word_lengths_now = self.word_length_lane_enabled if use_word_lengths is None else use_word_lengths
        models: list[tuple[str, int, float]] = []
        if self.base_lane_weights is not None:
            character_weight, word_length_weight = self.base_lane_weights
            if self.character_lane_enabled and character_weight > 0.0:
                models.append(("char", self.character_ngram_order, character_weight))
            if use_word_lengths_now and word_length_weight > 0.0:
                models.append(("wli", self.word_length_ngram_order, word_length_weight))
        else:
            character_weights = self.character_order_weights
            word_length_weights = self.word_length_order_weights
            if character_weights is None and word_length_weights is None:
                character_weights = MappingProxyType({2: 0.5})
                word_length_weights = MappingProxyType({2: 0.5})
            if self.character_lane_enabled:
                models.extend(("char", order, weight) for order, weight in (character_weights or {}).items() if weight > 0.0)
            if use_word_lengths_now:
                models.extend(("wli", order, weight) for order, weight in (word_length_weights or {}).items() if weight > 0.0)
        total = sum(weight for _channel, _order, weight in models)
        if total <= 0.0:
            raise ValueError("no active language-model weights remain after channel selection")
        return tuple((channel, order, weight / total) for channel, order, weight in models)

    def weight_contract(self) -> JsonObject:
        return {
            "requested": {
                "base_lane_weights": list(self.base_lane_weights) if self.base_lane_weights is not None else None,
                "character_order_weights": dict(self.character_order_weights or {}),
                "word_length_order_weights": dict(self.word_length_order_weights or {}),
            },
            "effective_lm_models": [
                {"channel": channel, "n": order, "weight": weight}
                for channel, order, weight in self.effective_lm_model_weights()
            ],
        }

    def to_dict(self) -> JsonObject:
        def encode(value: object) -> object:
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, ScoringObjective):
                return value.to_dict()
            if isinstance(value, HardCribConfig):
                return value.asdict()
            if isinstance(value, Mapping):
                return {str(key): encode(item) for key, item in value.items()}
            if isinstance(value, tuple):
                return [encode(item) for item in value]
            return value

        return {item.name: encode(getattr(self, item.name)) for item in fields(self)}  # type: ignore[return-value]

    def asdict(self) -> JsonObject:
        return self.to_dict()

    def __hash__(self) -> int:
        return hash(json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")))
