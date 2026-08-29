"""Strict enums and dataclasses shared across the core/engine pipeline."""
from __future__ import annotations
import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from numbers import Integral, Real
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Optional, TypeAlias

import numpy as np

# Central dtype for key material (needs >255 for bigram/permutation keys)
KEY_DTYPE = np.int16

# Immutable public boundary values. Runtime NumPy arrays are materialised only
# after these values have passed strict validation.
JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
RuneIndices: TypeAlias = tuple[int, ...]
ConcreteKey: TypeAlias = tuple[int, ...]
InitialKeys: TypeAlias = tuple[ConcreteKey, ...]
WordLengthInfo: TypeAlias = tuple[tuple[int, int], ...]
IndexPermutation: TypeAlias = tuple[int, ...]
ProgressCallback: TypeAlias = Callable[[Mapping[str, JsonValue]], None]
FrozenValue: TypeAlias = JsonPrimitive | tuple[Any, ...]
FrozenParameterItems: TypeAlias = tuple[tuple[str, FrozenValue], ...]


def _strict_public_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be an integer")
    return int(value)


def normalize_rune_indices(values: Sequence[int], *, field_name: str = "indices") -> RuneIndices:
    if isinstance(values, (str, bytes, Path)) or not isinstance(values, Sequence):
        raise TypeError(f"{field_name} must be an ordered sequence of integers")
    copied = tuple(_strict_public_int(value, f"{field_name}[{index}]") for index, value in enumerate(values))
    for index, value in enumerate(copied):
        if value < 0 or value > 28:
            raise ValueError(f"{field_name}[{index}] must be in [0..28]")
    return copied


def normalize_concrete_key(value: Sequence[int], *, field_name: str = "key") -> ConcreteKey:
    if type(value) is not tuple:
        raise TypeError(f"{field_name} must be ConcreteKey (tuple[int, ...])")
    copied = tuple(_strict_public_int(item, f"{field_name}[{index}]") for index, item in enumerate(value))
    if not copied:
        raise ValueError(f"{field_name} must not be empty")
    return copied


def normalize_initial_keys(value: Sequence[Sequence[int]], *, field_name: str = "initial_keys") -> InitialKeys:
    if type(value) is not tuple:
        raise TypeError(f"{field_name} must be InitialKeys (tuple[ConcreteKey, ...])")
    return tuple(normalize_concrete_key(item, field_name=f"{field_name}[{index}]") for index, item in enumerate(value))


def freeze_json_value(value: object, field_name: str) -> FrozenValue:
    if value is None or type(value) in {str, bool, int}:
        return value
    if isinstance(value, Real) and not isinstance(value, bool):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError(f"{field_name} must contain only finite floats")
        return 0.0 if result == 0.0 else result
    if isinstance(value, Enum):
        return freeze_json_value(value.value, field_name)
    if isinstance(value, Path):
        raise TypeError(f"{field_name} must not contain paths")
    if isinstance(value, Mapping):
        items: list[tuple[str, FrozenValue]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{field_name} mapping keys must be strings")
            items.append((key, freeze_json_value(item, f"{field_name}.{key}")))
        return tuple(items)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(freeze_json_value(item, f"{field_name}[{index}]") for index, item in enumerate(value))
    raise TypeError(f"{field_name} contains unsupported value {type(value).__name__}")


def freeze_parameter_items(values: Mapping[str, object], field_name: str = "parameters") -> FrozenParameterItems:
    if not isinstance(values, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) for key in values):
        raise TypeError(f"{field_name} mapping keys must be strings")
    return tuple(
        (key, freeze_json_value(value, f"{field_name}.{key}"))
        for key, value in values.items()
    )


def _looks_like_frozen_items(value: tuple[object, ...]) -> bool:
    return bool(value) and all(
        isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
        for item in value
    )


def thaw_frozen_value(
    value: FrozenValue,
    *,
    json_compatible: bool,
    preserve_pairs: bool = False,
) -> object:
    if not isinstance(value, tuple):
        return value
    if not preserve_pairs and _looks_like_frozen_items(value):
        return {
            str(key): thaw_frozen_value(item, json_compatible=json_compatible)
            for key, item in value  # type: ignore[misc]
        }
    values = tuple(
        thaw_frozen_value(item, json_compatible=json_compatible)
        for item in value
    )
    return list(values) if json_compatible else values


def thaw_parameter_items(
    items: FrozenParameterItems,
    *,
    json_compatible: bool = False,
    pair_sequence_keys: frozenset[str] = frozenset(),
) -> dict[str, object]:
    return {
        key: thaw_frozen_value(
            value,
            json_compatible=json_compatible,
            preserve_pairs=key in pair_sequence_keys,
        )
        for key, value in items
    }


def readonly_parameters(
    items: FrozenParameterItems,
    *,
    pair_sequence_keys: frozenset[str] = frozenset(),
) -> Mapping[str, object]:
    return MappingProxyType(
        thaw_parameter_items(items, pair_sequence_keys=pair_sequence_keys)
    )


def replay_key(prefix: str, payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{prefix}/v1/{hashlib.sha256(encoded).hexdigest()}"


class TextDirection(StrEnum):
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"


class ComputeDevice(StrEnum):
    CPU = "cpu"
    CUDA = "cuda"


class WordLengthPolicy(StrEnum):
    DISABLED = "disabled"
    INFER = "infer"
    REQUIRE = "require"


class FinalCipherKind(StrEnum):
    VIGENERE = "vigenere"
    AUTOKEY = "autokey"
    COLUMNAR = "columnar"
    RAIL_FENCE = "rail_fence"
    SUBSTITUTION = "substitution"
    PERIODIC_SUBSTITUTION = "periodic_substitution"
    PERIODIC_COLUMNAR = "periodic_columnar"
    TWO_PERIOD_VIGENERE = "two_period_vigenere"
    PERIODIC_WITH_FIXED_STREAM = "periodic_with_fixed_stream"
    PERIODIC_WITH_PRIME_STREAM = "periodic_with_prime_stream"
    TWO_PERIOD_STREAMS = "two_period_streams"


class FinalKeyKind(StrEnum):
    REPEATING = "repeating"
    REPEATING_RANGE = "repeating_range"
    PERMUTATION = "permutation"
    SCALAR = "scalar"
    PERIODIC_SUBSTITUTION = "periodic_substitution"
    PERIODIC_COLUMNAR = "periodic_columnar"


class SolverKind(StrEnum):
    BEAM_SEARCH = "beam_search"
    GENETIC_ALGORITHM = "genetic_algorithm"
    SIMULATED_ANNEALING = "simulated_annealing"
    HYBRID = "hybrid"
    KAEDING = "kaeding"
    TWO_PERIOD_CRIBS = "two_period_cribs"


class BeamExpansionMode(StrEnum):
    EXHAUSTIVE = "exhaustive"
    SAMPLE = "sample"
    SWEEP = "sweep"


class KaedingBlockSchedule(StrEnum):
    RANDOM = "random"
    ROUND_ROBIN = "round_robin"


class KaedingSlipPolicy(StrEnum):
    FIXED_INTERVAL = "fixed_interval"
    ON_STALL = "on_stall"


class InterruptorMode(StrEnum):
    DISABLED = "disabled"
    EXACT = "exact"
    SEARCH = "search"


class FinalInterruptorSearchStrategy(StrEnum):
    AUTO = "auto"
    BRUTE_FORCE = "brute_force"
    KEY_OPERATIONS = "key_operations"


class PeriodicColumnarOrder(StrEnum):
    COLUMNAR_THEN_SUBSTITUTION = "columnar_then_substitution"
    SUBSTITUTION_THEN_COLUMNAR = "substitution_then_columnar"


class ScheduledStreamSchedule(StrEnum):
    OVERLAY = "overlay"
    ALTERNATING = "alternating"
    MASK = "mask"


class ScheduledStreamOperation(StrEnum):
    ADD = "add"
    ADD_SUBTRACT = "add_subtract"
    SUBTRACT_ADD = "subtract_add"
    BEAUFORT_SUM = "beaufort_sum"


class SmoothingMethod(StrEnum):
    NONE = "none"
    LIDSTONE = "lidstone"
    JEFFREYS = "jeffreys"
    AUTO_GOOD_TURING = "auto_good_turing"


class OutOfVocabularyPolicy(StrEnum):
    FLOOR_MINIMUM_SEEN = "floor_minimum_seen"
    LIDSTONE = "lidstone"


class LanguageModelBoundaryMode(StrEnum):
    EXCLUDE_BOUNDARIES = "exclude_boundaries"
    INCLUDE_BOUNDARIES = "include_boundaries"


class ScoreDirection(StrEnum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class ScorerBackend(StrEnum):
    AUTO = "auto"
    NUMPY = "numpy"
    TORCH = "torch"
    UNIFIED = "unified"


class ScoringObjectiveKind(StrEnum):
    PERCENTILE = "percentile"
    AVERAGE = "average"
    NEGATIVE_LOG_PROBABILITY = "negative_log_probability"


class ScoreStatistic(StrEnum):
    LOG_PROBABILITY = "log_probability"
    Z_SCORE_SUM = "z_score_sum"
    MEDIAN_ABSOLUTE_DEVIATION_SUM = "median_absolute_deviation_sum"


class AverageWindowPolicy(StrEnum):
    FIXED_WINDOW = "fixed_window"
    FULL_TEXT = "full_text"


class HammingTextDirectionMode(StrEnum):
    MATCH_TEXT = "match_text"
    BOTH = "both"


class SpanHammingMode(StrEnum):
    OFF = "off"
    RAW_BONUS = "raw_bonus"
    CALIBRATED = "calibrated"


class SpanHammingBucketPolicy(StrEnum):
    NEAREST_SMALLER_ON_TIE = "nearest_smaller_on_tie"


class SpanHammingCombineMode(StrEnum):
    MINIMUM = "minimum"
    WEIGHTED_SUM = "weighted_sum"


class SpanHammingGateFailurePolicy(StrEnum):
    SCORE_FLOOR = "score_floor"
    CHARACTER_ONLY = "character_only"


class SpanHammingLanguageModelProfileSource(StrEnum):
    RAW_SPAN_BY_LENGTH = "raw_span_by_length"
    CHARACTERS_COVERED_BY_LENGTH = "characters_covered_by_length"

class Direction(Enum):
    """Canonical text-encoding direction for the pipeline.
    Core uses this Enum only (never raw strings). When serialized to JSON,
    use .value to emit 'ltr' or 'rtl' for readability.
    """
    LTR = "ltr"
    RTL = "rtl"

class Device(Enum):
    """Execution device. Core can branch on this; API remains forgiving."""
    CPU = "cpu"
    CUDA = "cuda"

class ScorerImpl(Enum):
    """Execution device. Core uses this API remains forgiving."""
    NUMPY = "numpy"
    TORCH = "torch"
    UNIFIED = "unified"
    AUTO = "auto"

class FloatDType(StrEnum):
    """Canonical float dtype for scoring/telemetry knobs."""
    FLOAT32 = "float32"
    FLOAT64 = "float64"


class ScorerName(Enum):
    """Canonical scorer families recognised by the config layer."""
    RUNE = "rune"

class SolverName(Enum):
    """Optimizer device. Core uses this API remains forgiving."""
    BEAM  = "beam"
    GA  = "ga"
    SA  = "sa"
    HYBRID  = "hybrid"
    KAEDING = "kaeding"


class InterruptorSearchStrategy(Enum):
    """Search strategy for interruptor positions."""
    AUTO = "auto"
    BRUTEFORCE = "bruteforce"
    KEYOPS = "keyops"


class CipherKind(Enum):
    """Canonical cipher family for strict branching in the core.
    UI may keep string fields, but the core uses this Enum only.
    """
    WRAPPER = "wrapper"      # Named core cipher exposed via wrappers/registry
    USER_MAP2 = "user_map2"  # ct = f(pt, k)
    USER_MAP3 = "user_map3"  # ct = f(pt, k1, k2)
    LOOKUP = "lookup"        # ct = table[pt, k] or similar

class KeyKind(Enum):
    """Canonical key plan for strict branching in the core.
    Avoid magic strings in engine/cipher builders.
    """
    REPEAT = "repeat"        # periodic stream of length K
    OTP = "otp"              # explicit stream
    CONST = "const"          # broadcast constant value
    PERM = "perm"            # permutation key (bijective)
    MATRIX2X2 = "matrix2x2"  # 2×2 matrix (e.g., Hill-2)
    MATRIX = "matrix"        # general matrix
    AFFINE = "affine"        # (a, b) pair when used as key parts
    SCALAR = "scalar"        # single int modulo N
    BLOCK = "block"          # structured/block key (reserved)
    KEYSTREAM = "keystream"  # pre-generated stream (alias of OTP at core level)

class KeyOpsFamily(Enum):
    """KeyOps families recognised by the core/keyops registry."""
    PERMUTATION = "permutation"
    VECTOR = "vector"
    COMPOSITE = "composite"
    AFFINE = "affine"
    MATRIX = "matrix"

@dataclass(frozen=True)
class PipelineCfg:
    """Strict pipeline config carried inside core."""
    text_encoding_direction: Direction = Direction.LTR
    # Core expects a true permutation over ciphertext token indices or None.
    # API normalizes various user formats to this canonical list[int] in PR2.
    text_permutation: Optional[list[int]] = None

@dataclass(frozen=True)
class SolveCfg:
    """Strict top-level config for the solver engine (core-facing only)."""
    seed: int = 42
    device: Device = Device.CPU
    telemetry_on: bool = True

    # Budgets/patience standardization (wired in PR12; defined now for clarity)
    eval_budget: int = 10_000
    time_budget_s: float = 10.0
    patience_steps: int = 250
    improvement_threshold: float = 0.0

    # Pipeline (direction & permutation)
    pipeline: PipelineCfg = field(default_factory=PipelineCfg)


def _coerce_enum_value(enum_cls, value, *, aliases=None, param_name="value"):
    if isinstance(value, enum_cls):
        return value
    if value is None:
        raise TypeError(f"{param_name} must be {enum_cls.__name__}, got None")
    aliases = aliases or {}
    key = str(value).strip().lower()
    target = aliases.get(key)
    if target is not None:
        if isinstance(target, enum_cls):
            return target
        key = str(target).strip().lower()
    for member in enum_cls:
        if member.value == key:
            return member
    raise ValueError(f"Unknown {param_name}: {value!r}")


def ensure_direction(value) -> Direction:
    if isinstance(value, TextDirection):
        return (
            Direction.LTR
            if value is TextDirection.LEFT_TO_RIGHT
            else Direction.RTL
        )
    return _coerce_enum_value(Direction, value, aliases={
        "forward": Direction.LTR,
        "fwd": Direction.LTR,
        "reverse": Direction.RTL,
        "rev": Direction.RTL,
    }, param_name="direction")


def ensure_device(value) -> Device:
    if isinstance(value, Device):
        return value
    if value is None:
        raise TypeError("device must be Device or str, got None")
    key = str(value).strip().lower()
    if key.startswith("cuda") or key in {"gpu"}:
        return Device.CUDA
    if key == "torch":
        return Device.CPU
    return Device.CPU


def ensure_solver_name(value) -> SolverName:
    return _coerce_enum_value(SolverName, value, param_name="solver kind")


def ensure_scorer_name(value) -> ScorerName:
    return _coerce_enum_value(ScorerName, value, param_name="scorer name")


def ensure_scorer_impl(value) -> ScorerImpl:
    return _coerce_enum_value(ScorerImpl, value, param_name="scorer impl")

def ensure_float_dtype(value) -> FloatDType:
    return _coerce_enum_value(FloatDType, value, aliases={
        "f32": FloatDType.FLOAT32,
        "fp32": FloatDType.FLOAT32,
        "32": FloatDType.FLOAT32,
        "float32": FloatDType.FLOAT32,
        "f64": FloatDType.FLOAT64,
        "fp64": FloatDType.FLOAT64,
        "64": FloatDType.FLOAT64,
        "float64": FloatDType.FLOAT64,
    }, param_name="float dtype")


def ensure_keyops_family(value) -> KeyOpsFamily:
    return _coerce_enum_value(KeyOpsFamily, value, aliases={
        "perm": KeyOpsFamily.PERMUTATION,
        "param": KeyOpsFamily.COMPOSITE,
        "composite": KeyOpsFamily.COMPOSITE,
        "interruptor": KeyOpsFamily.COMPOSITE,
        "interruptors": KeyOpsFamily.COMPOSITE,
    }, param_name="keyops family")


def ensure_interruptor_search_strategy(value) -> InterruptorSearchStrategy:
    return _coerce_enum_value(
        InterruptorSearchStrategy,
        value,
        param_name="interruptor search strategy",
    )



def ensure_cipher_kind(value) -> CipherKind:
    return _coerce_enum_value(CipherKind, value, param_name="cipher kind")


def ensure_key_kind(value) -> KeyKind:
    return _coerce_enum_value(KeyKind, value, param_name="key kind")



def parse_optimizer_kind(val) -> SolverName:
    return ensure_solver_name(val)

def parse_device(val) -> Device:
    if val is None:
        return Device.CPU
    return ensure_device(val)



from enum import Enum
from dataclasses import dataclass
from typing import Optional

class SeMode(Enum):
    NOSE = "nose"
    WISE = "wise"

class Channel(Enum):
    CHAR = "char"
    WLI = "wli"

class ObjectiveFamily(Enum):
    PCT = "pct"
    AVG = "avg"
    ENERGY = "energy"     # kept as explicit alias
    NEGLOGP = "neglogp"   # scalar legacy

class Stat(Enum):
    LOGP = "logp"
    ZSUM = "zsum"
    MADSUM = "madsum"


class AvgWindowPolicy(Enum):
    FIXED_WIN = "fixed_win"
    FULL_TEXT = "full_text"

@dataclass(frozen=True)
class ObjectiveSpec:
    family: ObjectiveFamily
    stat: Optional[Stat] = None     # None for NEGLOGP
    win: Optional[int] = None       # required for PCT/ENERGY families


def ensure_se_mode(value) -> SeMode:
    return _coerce_enum_value(SeMode, value, param_name="se_mode")


def ensure_objective_family(value) -> ObjectiveFamily:
    return _coerce_enum_value(ObjectiveFamily, value, param_name="objective family")


def ensure_stat(value) -> Stat:
    return _coerce_enum_value(Stat, value, param_name="stat")


def ensure_avg_window_policy(value) -> AvgWindowPolicy:
    return _coerce_enum_value(
        AvgWindowPolicy,
        value,
        aliases={
            "win": AvgWindowPolicy.FIXED_WIN,
            "window": AvgWindowPolicy.FIXED_WIN,
            "fulltext": AvgWindowPolicy.FULL_TEXT,
            "full": AvgWindowPolicy.FULL_TEXT,
        },
        param_name="avg window policy",
    )
