from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from numbers import Integral
from pathlib import Path
from types import MappingProxyType
from typing import Any

from rdp.api.specs import CipherSpec, KeySpec, SolverSpec
from rune_decrypter_prime.core.config.interruptor import InterruptorConfig
from rune_decrypter_prime.core.config.logging_config import LoggingConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rdp.core.types import (
    ComputeDevice,
    IndexPermutation,
    InitialKeys,
    JsonObject,
    TextDirection,
    WordLengthInfo,
    WordLengthPolicy,
    normalize_initial_keys,
)


LP_SOURCE_KINDS = frozenset(
    {
        "liber_primus.label",
        "liber_primus.locator",
        "liber_primus.partition",
    }
)

_JSON_PRIMITIVE_TYPES = (str, int, float, bool, type(None))
_LP_LOCATOR_BASE_KEYS = frozenset(
    {
        "page_scheme",
        "page_number",
        "line",
        "line_end",
        "word",
        "word_end",
        "route_kind",
    }
)
_LP_LOCATOR_ROUTE_KEYS = {
    "none": _LP_LOCATOR_BASE_KEYS,
    "line": _LP_LOCATOR_BASE_KEYS | frozenset({"line_mode", "line_selector"}),
    "spiral": _LP_LOCATOR_BASE_KEYS
    | frozenset({"spiral_direction", "spiral_start_corner", "spiral_skip_empty"}),
}
_LP_PARTITION_KEYS = frozenset(
    {
        "partition_scheme",
        "partition_ordinal",
        "canon_start",
        "canon_end",
        "intersect_page_scheme",
        "intersect_page_number",
    }
)
_LP_LABEL_KEYS = frozenset({"label"})


def _require_text(value: Any, field_name: str) -> str:
    if isinstance(value, Path) or not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _require_index(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be an integer")
    item = int(value)
    if item < 0 or item > 28:
        raise ValueError(f"{field_name} must be in [0..28]")
    return item


def _require_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be an integer")
    return int(value)


def _require_optional_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    return _require_int(value, field_name)


def _require_wli_index(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be an integer")
    return int(value)


def _require_ordered_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, Path, Mapping)) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be an ordered sequence")
    return value


def _require_wli_pair(value: Any, field_name: str) -> tuple[int, int]:
    pair = _require_ordered_sequence(value, field_name)
    if len(pair) != 2:
        raise ValueError(f"{field_name} must contain exactly two items")
    pos = _require_wli_index(pair[0], f"{field_name}[0]")
    word_len = _require_wli_index(pair[1], f"{field_name}[1]")
    if pos < 0:
        raise ValueError(f"{field_name}[0] must be >= 0")
    if word_len <= 0:
        raise ValueError(f"{field_name}[1] must be > 0")
    if pos >= word_len:
        raise ValueError(f"{field_name}[0] must be < {field_name}[1]")
    return pos, word_len


def _copy_json_primitive_mapping(
    value: Mapping[str, Any] | None,
    field_name: str,
) -> MappingProxyType[str, Any]:
    if value is None:
        return MappingProxyType({})
    if isinstance(value, Path) or not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")

    copied: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(key, Path) or not isinstance(key, str):
            raise TypeError(f"{field_name} keys must be strings")
        if not key:
            raise ValueError(f"{field_name} keys must not be empty")
        if isinstance(item, Path) or not isinstance(item, _JSON_PRIMITIVE_TYPES):
            raise TypeError(f"{field_name} values must be JSON primitives")
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError(f"{field_name} float values must be finite")
        copied[key] = item
    return MappingProxyType(copied)


def _enum_values(enum_type: type[Any]) -> frozenset[str]:
    return frozenset(item.value for item in enum_type)


def _require_enum_value(value: Any, allowed: frozenset[str], field_name: str) -> str:
    text = _require_text(value, field_name)
    if text not in allowed:
        raise ValueError(f"{field_name} is not supported: {text}")
    return text


def _require_exact_keys(ref: Mapping[str, Any], required: frozenset[str], field_name: str) -> None:
    keys = frozenset(ref.keys())
    missing = sorted(required - keys)
    extra = sorted(keys - required)
    if missing:
        raise ValueError(f"{field_name} is missing keys: {', '.join(missing)}")
    if extra:
        raise ValueError(f"{field_name} has unsupported keys: {', '.join(extra)}")


def _validate_lp_page_ref(
    ref: Mapping[str, Any],
    *,
    scheme_key: str,
    number_key: str,
    field_name: str,
) -> None:
    from rune_decrypter_prime.data.liber_primus.lp_registry import LPBuiltInPageScheme

    scheme = _require_enum_value(ref[scheme_key], _enum_values(LPBuiltInPageScheme), scheme_key)
    number = _require_int(ref[number_key], number_key)
    if scheme == LPBuiltInPageScheme.BOUND_BOOK_PAGE.value:
        if number < 1:
            raise ValueError(f"{field_name}.{number_key} must be >= 1")
    elif number < 0:
        raise ValueError(f"{field_name}.{number_key} must be >= 0")


def _validate_lp_locator_ref(ref: Mapping[str, Any]) -> None:
    from rune_decrypter_prime.data.liber_primus.lp_routes import (
        LPLineReadMode,
        LPLineRuneSelector,
        LPSpiralDirection,
        LPSpiralStartCorner,
    )

    route_kind = _require_enum_value(ref.get("route_kind"), frozenset(_LP_LOCATOR_ROUTE_KEYS), "route_kind")
    _require_exact_keys(ref, _LP_LOCATOR_ROUTE_KEYS[route_kind], "ref")
    _validate_lp_page_ref(ref, scheme_key="page_scheme", number_key="page_number", field_name="ref")

    line = _require_optional_int(ref["line"], "line")
    line_end = _require_optional_int(ref["line_end"], "line_end")
    word = _require_optional_int(ref["word"], "word")
    word_end = _require_optional_int(ref["word_end"], "word_end")
    if line is None and line_end is not None:
        raise ValueError("line_end must be None when line is None")
    if word is None and word_end is not None:
        raise ValueError("word_end must be None when word is None")
    if line is not None and line < 0:
        raise ValueError("line must be >= 0")
    if line_end is not None and line_end < line:
        raise ValueError("line_end must be >= line")
    if word is not None and word < 0:
        raise ValueError("word must be >= 0")
    if word_end is not None and word_end < word:
        raise ValueError("word_end must be >= word")

    if route_kind == "line":
        if word is not None or word_end is not None:
            raise ValueError("line routed locator refs do not support word selectors")
        _require_enum_value(ref["line_mode"], _enum_values(LPLineReadMode), "line_mode")
        _require_enum_value(ref["line_selector"], _enum_values(LPLineRuneSelector), "line_selector")
    elif route_kind == "spiral":
        if word is not None or word_end is not None:
            raise ValueError("spiral routed locator refs do not support word selectors")
        _require_enum_value(ref["spiral_direction"], _enum_values(LPSpiralDirection), "spiral_direction")
        _require_enum_value(ref["spiral_start_corner"], _enum_values(LPSpiralStartCorner), "spiral_start_corner")
        if not isinstance(ref["spiral_skip_empty"], bool):
            raise TypeError("spiral_skip_empty must be a bool")


def _validate_partition_ordinal(value: Any) -> None:
    text = _require_text(value, "partition_ordinal")
    parts = text.split("-")
    if not parts:
        raise ValueError("partition_ordinal must not be empty")
    for part in parts:
        if not part.isdecimal() or int(part) <= 0:
            raise ValueError("partition_ordinal parts must be positive integers")


def _validate_lp_partition_ref(ref: Mapping[str, Any]) -> None:
    from rune_decrypter_prime.data.liber_primus.lp_registry import LPBuiltInPartitionScheme

    _require_exact_keys(ref, _LP_PARTITION_KEYS, "ref")
    _require_enum_value(ref["partition_scheme"], _enum_values(LPBuiltInPartitionScheme), "partition_scheme")
    _validate_partition_ordinal(ref["partition_ordinal"])
    canon_start = _require_int(ref["canon_start"], "canon_start")
    canon_end = _require_int(ref["canon_end"], "canon_end")
    if canon_start < 0:
        raise ValueError("canon_start must be >= 0")
    if canon_end < canon_start:
        raise ValueError("canon_end must be >= canon_start")

    intersect_scheme = ref["intersect_page_scheme"]
    intersect_number = ref["intersect_page_number"]
    if intersect_scheme is None and intersect_number is None:
        return
    if intersect_scheme is None or intersect_number is None:
        raise ValueError("intersect_page_scheme and intersect_page_number must both be None or both be populated")
    _validate_lp_page_ref(
        ref,
        scheme_key="intersect_page_scheme",
        number_key="intersect_page_number",
        field_name="ref",
    )


def _validate_lp_label_ref(ref: Mapping[str, Any]) -> None:
    _require_exact_keys(ref, _LP_LABEL_KEYS, "ref")
    label = _require_text(ref["label"], "label")
    if label.startswith("recipe."):
        raise ValueError("label must be an LP source label, not a solve recipe label")


def _validate_source_ref(source_kind: str, ref: Mapping[str, Any]) -> None:
    if source_kind == "liber_primus.label":
        _validate_lp_label_ref(ref)
    elif source_kind == "liber_primus.locator":
        _validate_lp_locator_ref(ref)
    elif source_kind == "liber_primus.partition":
        _validate_lp_partition_ref(ref)


@dataclass(frozen=True, slots=True)
class RawTextInput:
    """Raw ciphertext text supplied at the API boundary.

    The text is validated as a non-empty string and is normalised later by the
    RunSpec routing layer. File paths and other objects are rejected here so the
    input source remains explicit.
    """

    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _require_text(self.text, "text"))


@dataclass(frozen=True, slots=True)
class RuneIndexInput:
    """Pre-normalised ciphertext indices, optionally with WLI pairs.

    `ct_idx` is copied to an immutable tuple of rune indices in the inclusive
    range 0..28. `wli`, when supplied, must be the same length as `ct_idx` and
    must contain ordered `(position, word_length)` pairs.
    """

    indices: Sequence[int]
    word_lengths: WordLengthInfo | None = None

    def __post_init__(self) -> None:
        ct_idx_input = _require_ordered_sequence(self.indices, "indices")
        ct_idx = tuple(
            _require_index(item, f"indices[{index}]")
            for index, item in enumerate(ct_idx_input)
        )
        if not ct_idx:
            raise ValueError("indices must not be empty")

        wli: tuple[tuple[int, int], ...] | None
        if self.word_lengths is None:
            wli = None
        else:
            wli_input = _require_ordered_sequence(self.word_lengths, "word_lengths")
            wli_items: list[tuple[int, int]] = []
            for index, pair in enumerate(wli_input):
                wli_items.append(_require_wli_pair(pair, f"word_lengths[{index}]"))
            wli = tuple(wli_items)
            if len(wli) != len(ct_idx):
                raise ValueError("word_lengths length must match indices length")

        object.__setattr__(self, "indices", ct_idx)
        object.__setattr__(self, "word_lengths", wli)

    @property
    def ct_idx(self) -> tuple[int, ...]:
        return tuple(self.indices)

    @property
    def wli(self) -> WordLengthInfo | None:
        return self.word_lengths


@dataclass(frozen=True, slots=True)
class SourceReferenceInput:
    """Reference to a resolver-owned source input.

    The identity fields name the source kind, asset id, and asset version.
    `ref` is restricted to flat JSON primitive metadata so reports can remain
    portable and free of local path objects. Liber Primus references receive
    stricter shape validation according to `source_kind`.
    """

    source_kind: str
    asset_id: str
    asset_version: str
    reference: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        source_kind = _require_text(self.source_kind, "source_kind")
        asset_id = _require_text(self.asset_id, "asset_id")
        asset_version = _require_text(self.asset_version, "asset_version")
        if source_kind.startswith("liber_primus.") and source_kind not in LP_SOURCE_KINDS:
            raise ValueError(f"unsupported LP source_kind: {source_kind}")

        ref = _copy_json_primitive_mapping(self.reference, "reference")
        _validate_source_ref(source_kind, ref)

        object.__setattr__(self, "source_kind", source_kind)
        object.__setattr__(self, "asset_id", asset_id)
        object.__setattr__(self, "asset_version", asset_version)
        object.__setattr__(self, "reference", ref)

    @property
    def ref(self) -> Mapping[str, Any]:
        return self.reference


ProblemInput = RawTextInput | RuneIndexInput | SourceReferenceInput

@dataclass(frozen=True, slots=True)
class RunSpec:
    """Immutable public run request.

    RunSpec binds one explicit problem input to a cipher spec, key spec,
    solver spec, scorer selection, logging config, text direction, device, and
    telemetry toggle. It validates only the request contract; materialisation
    and execution happen later in the routing and engine layers.
    """

    problem_input: ProblemInput
    cipher: CipherSpec
    key_space: KeySpec
    solver: SolverSpec
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    initial_keys: InitialKeys | None = None
    logging: LoggingConfig | None = None
    word_length_policy: WordLengthPolicy = WordLengthPolicy.INFER
    text_direction: TextDirection = TextDirection.RIGHT_TO_LEFT
    compute_device: ComputeDevice = ComputeDevice.CPU
    telemetry_enabled: bool = True
    text_permutation: IndexPermutation | None = None
    interruptors: InterruptorConfig | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.problem_input, (RawTextInput, RuneIndexInput, SourceReferenceInput)):
            raise TypeError("problem_input must be RawTextInput, RuneIndexInput, or SourceReferenceInput")
        if not isinstance(self.cipher, CipherSpec):
            raise TypeError("cipher must be a CipherSpec")
        if not isinstance(self.key_space, KeySpec):
            raise TypeError("key_space must be a KeySpec")
        if not isinstance(self.solver, SolverSpec):
            raise TypeError("solver must be a SolverSpec")
        from rune_decrypter_prime.core.config.cipher import expected_concrete_key_length
        expected_concrete_key_length(self.cipher, self.key_space)
        if not isinstance(self.scoring, ScoringConfig):
            raise TypeError("scoring must be a ScoringConfig")
        if self.logging is not None and not isinstance(self.logging, LoggingConfig):
            raise TypeError("logging must be a LoggingConfig or None")
        if not isinstance(self.word_length_policy, WordLengthPolicy):
            raise TypeError("word_length_policy must be WordLengthPolicy")
        if not isinstance(self.text_direction, TextDirection):
            raise TypeError("text_direction must be TextDirection")
        if not isinstance(self.compute_device, ComputeDevice):
            raise TypeError("compute_device must be ComputeDevice")
        if type(self.telemetry_enabled) is not bool:
            raise TypeError("telemetry_enabled must be a bool")
        if self.initial_keys is not None:
            object.__setattr__(self, "initial_keys", normalize_initial_keys(self.initial_keys))
        if self.text_permutation is not None:
            permutation = tuple(_require_int(value, "text_permutation") for value in self.text_permutation)
            if sorted(permutation) != list(range(len(permutation))):
                raise ValueError("text_permutation must be a permutation of 0..n-1")
            if isinstance(self.problem_input, RuneIndexInput) and len(permutation) != len(self.problem_input.indices):
                raise ValueError("text_permutation length must match RuneIndexInput.indices")
            object.__setattr__(self, "text_permutation", permutation)
        if self.interruptors is not None and not isinstance(self.interruptors, InterruptorConfig):
            raise TypeError("interruptors must be InterruptorConfig or None")


__all__ = [
    "RuneIndexInput",
    "ProblemInput",
    "RawTextInput",
    "RunSpec",
    "SourceReferenceInput",
]
