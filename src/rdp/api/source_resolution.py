from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Integral
from pathlib import Path
from types import MappingProxyType
from typing import Any

from rdp.api.run_spec import SourceReferenceInput


SUPPORTED_SOURCE_KINDS = frozenset(
    {
        "liber_primus.label",
        "liber_primus.locator",
        "liber_primus.partition",
    }
)

_JSON_PRIMITIVE_TYPES = (str, int, float, bool, type(None))


@dataclass(frozen=True, slots=True)
class ResolvedSourceInput:
    ct_idx: Sequence[int]
    wli: Sequence[Sequence[int]] | None
    source_ref: SourceReferenceInput
    source_metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.source_ref, SourceReferenceInput):
            raise TypeError("source_ref must be a SourceReferenceInput")

        ct_idx = _copy_ct_idx(self.ct_idx)
        wli = _copy_wli(self.wli, expected_len=len(ct_idx))
        source_metadata = _copy_path_free_metadata(
            self.source_metadata, "source_metadata"
        )

        object.__setattr__(self, "ct_idx", ct_idx)
        object.__setattr__(self, "wli", wli)
        object.__setattr__(self, "source_metadata", source_metadata)


def resolve_source_input_ref(source_ref: SourceReferenceInput) -> ResolvedSourceInput:
    if not isinstance(source_ref, SourceReferenceInput):
        raise TypeError("source_ref must be a SourceReferenceInput")

    if source_ref.source_kind == "liber_primus.label":
        return _resolve_lp_label(source_ref)
    if source_ref.source_kind == "liber_primus.locator":
        return _resolve_lp_locator(source_ref)
    if source_ref.source_kind == "liber_primus.partition":
        return _resolve_lp_partition(source_ref)

    raise ValueError(
        f"unsupported source_kind for resolution: {source_ref.source_kind}"
    )


def _resolve_lp_label(source_ref: SourceReferenceInput) -> ResolvedSourceInput:
    _validate_lp_main_identity(source_ref)

    from rune_decrypter_prime.data.liber_primus.lp_source_catalogue import (
        payload_from_label,
    )

    payload = payload_from_label(source_ref.ref["label"])
    return ResolvedSourceInput(
        ct_idx=payload.ct_idx,
        wli=payload.wli,
        source_ref=source_ref,
        source_metadata=payload.metadata,
    )


def _resolve_lp_locator(source_ref: SourceReferenceInput) -> ResolvedSourceInput:
    _validate_lp_main_identity(source_ref)

    from rune_decrypter_prime.data.liber_primus.lp_adapter import payload_from_locator
    from rune_decrypter_prime.data.liber_primus.lp_main import load_main_transcript
    from rune_decrypter_prime.data.liber_primus.lp_registry import LPFragmentLocator
    from rune_decrypter_prime.data.liber_primus.lp_routes import (
        LPLineReadMode,
        LPLineRuneSelector,
        LPSpiralDirection,
        LPSpiralRoute,
        LPSpiralStartCorner,
    )

    ref = source_ref.ref
    locator = LPFragmentLocator(
        page_ref=_lp_page_ref(ref, scheme_key="page_scheme", number_key="page_number"),
        line=ref["line"],
        line_end=ref["line_end"],
        word=ref["word"],
        word_end=ref["word_end"],
    )
    doc = load_main_transcript()
    route_kind = ref["route_kind"]
    if route_kind == "none":
        payload = payload_from_locator(doc, locator)
    elif route_kind == "line":
        payload = payload_from_locator(
            doc,
            locator,
            line_mode=LPLineReadMode(ref["line_mode"]),
            selector=LPLineRuneSelector(ref["line_selector"]),
        )
    elif route_kind == "spiral":
        payload = payload_from_locator(
            doc,
            locator,
            spiral_route=LPSpiralRoute(
                direction=LPSpiralDirection(ref["spiral_direction"]),
                start_corner=LPSpiralStartCorner(ref["spiral_start_corner"]),
                skip_empty=ref["spiral_skip_empty"],
            ),
        )
    else:
        raise ValueError(f"unsupported LP locator route_kind: {route_kind}")

    return ResolvedSourceInput(
        ct_idx=payload.ct_idx,
        wli=payload.wli,
        source_ref=source_ref,
        source_metadata=payload.metadata,
    )


def _resolve_lp_partition(source_ref: SourceReferenceInput) -> ResolvedSourceInput:
    _validate_lp_main_identity(source_ref)

    from rune_decrypter_prime.data.liber_primus.lp_adapter import (
        payload_from_partition_entry,
    )
    from rune_decrypter_prime.data.liber_primus.lp_main import load_main_transcript
    from rune_decrypter_prime.data.liber_primus.lp_registry import (
        LPBuiltInPartitionScheme,
        LPPageRef,
        LPPartitionEntry,
        LPSectionOrdinal,
    )

    ref = source_ref.ref
    ordinal = LPSectionOrdinal.of(
        *(int(part) for part in ref["partition_ordinal"].split("-"))
    )
    entry = LPPartitionEntry(
        scheme=LPBuiltInPartitionScheme(ref["partition_scheme"]),
        ordinal=ordinal,
        start_page=LPPageRef.canon_page(ref["canon_start"]),
        end_page=LPPageRef.canon_page(ref["canon_end"]),
    )
    intersect_page_ref = None
    if ref["intersect_page_scheme"] is not None:
        intersect_page_ref = _lp_page_ref(
            ref,
            scheme_key="intersect_page_scheme",
            number_key="intersect_page_number",
        )

    payload = payload_from_partition_entry(
        load_main_transcript(),
        entry,
        intersect_page_ref=intersect_page_ref,
    )
    return ResolvedSourceInput(
        ct_idx=payload.ct_idx,
        wli=payload.wli,
        source_ref=source_ref,
        source_metadata=payload.metadata,
    )


def _validate_lp_main_identity(source_ref: SourceReferenceInput) -> None:
    from rune_decrypter_prime.data.liber_primus.lp_main import (
        MAIN_TRANSCRIPT_ASSET_ID,
        main_transcript_asset_identity,
    )

    if source_ref.asset_id != MAIN_TRANSCRIPT_ASSET_ID:
        raise ValueError(
            f"source_ref.asset_id must be {MAIN_TRANSCRIPT_ASSET_ID!r} for LP resolution"
        )

    identity = main_transcript_asset_identity()
    if source_ref.asset_version != identity["asset_version"]:
        raise ValueError(
            "source_ref.asset_version does not match current LP main transcript asset_version"
        )


def _lp_page_ref(ref: Mapping[str, Any], *, scheme_key: str, number_key: str):
    from rune_decrypter_prime.data.liber_primus.lp_registry import (
        LPBuiltInPageScheme,
        LPPageRef,
    )

    return LPPageRef(
        scheme=LPBuiltInPageScheme(ref[scheme_key]),
        number=ref[number_key],
    )


def _copy_ct_idx(value: Any) -> tuple[int, ...]:
    ct_idx_input = _require_ordered_sequence(value, "ct_idx")
    ct_idx = tuple(
        _require_token(item, f"ct_idx[{index}]")
        for index, item in enumerate(ct_idx_input)
    )
    if not ct_idx:
        raise ValueError("ct_idx must not be empty")
    return ct_idx


def _copy_wli(value: Any, *, expected_len: int) -> tuple[tuple[int, int], ...] | None:
    if value is None:
        return None

    wli_input = _require_ordered_sequence(value, "wli")
    wli = tuple(
        _require_wli_pair(pair, f"wli[{index}]") for index, pair in enumerate(wli_input)
    )
    if len(wli) != expected_len:
        raise ValueError("wli length must match ct_idx length")
    return wli


def _require_ordered_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, Path, Mapping)) or not isinstance(
        value, Sequence
    ):
        raise TypeError(f"{field_name} must be an ordered sequence")
    return value


def _require_token(value: Any, field_name: str) -> int:
    item = _require_int(value, field_name)
    if item < 0 or item > 28:
        raise ValueError(f"{field_name} must be in [0..28]")
    return item


def _require_wli_pair(value: Any, field_name: str) -> tuple[int, int]:
    pair = _require_ordered_sequence(value, field_name)
    if len(pair) != 2:
        raise ValueError(f"{field_name} must contain exactly two items")
    pos = _require_int(pair[0], f"{field_name}[0]")
    word_len = _require_int(pair[1], f"{field_name}[1]")
    if pos < 0:
        raise ValueError(f"{field_name}[0] must be >= 0")
    if word_len <= 0:
        raise ValueError(f"{field_name}[1] must be > 0")
    if pos >= word_len:
        raise ValueError(f"{field_name}[0] must be < {field_name}[1]")
    return pos, word_len


def _require_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be an integer")
    return int(value)


def _copy_path_free_metadata(value: Any, field_name: str) -> MappingProxyType[str, Any]:
    if isinstance(value, Path) or not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")

    copied: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(key, Path) or not isinstance(key, str):
            raise TypeError(f"{field_name} keys must be strings")
        if not key:
            raise ValueError(f"{field_name} keys must not be empty")
        copied[key] = _copy_path_free_metadata_value(item, f"{field_name}.{key}")
    return MappingProxyType(copied)


def _copy_path_free_metadata_value(value: Any, field_name: str) -> Any:
    if isinstance(value, Path):
        raise TypeError(f"{field_name} must not be a Path")
    if isinstance(value, Mapping):
        return _copy_path_free_metadata(value, field_name)
    if isinstance(value, (list, tuple)):
        return tuple(
            _copy_path_free_metadata_value(item, f"{field_name}[]") for item in value
        )
    if not isinstance(value, _JSON_PRIMITIVE_TYPES):
        raise TypeError(f"{field_name} must be JSON-compatible")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{field_name} float values must be finite")
    return value


__all__ = [
    "ResolvedSourceInput",
    "SUPPORTED_SOURCE_KINDS",
    "resolve_source_input_ref",
]
