from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rune_decrypter_prime.data.liber_primus.lp_main import (
    extract_locator_ct_wli,
    extract_partition_entry_ct_wli,
    glyph_span_from_partition_entry,
    main_transcript_asset_identity,
    page_view_from_ref,
)
from rune_decrypter_prime.data.liber_primus.lp_registry import (
    LPFragmentLocator,
    LPPageRef,
    LPPartitionEntry,
)
from rune_decrypter_prime.data.liber_primus.lp_routes import (
    LPLineReadMode,
    LPLineRuneSelector,
    LPSpiralRoute,
    read_lines,
    spiral_read,
)
from rune_decrypter_prime.data.liber_primus.lp_transcript import LPTranscript
from rune_decrypter_prime.utils.runeglish import Runeglish


@dataclass(frozen=True)
class LPSolverPayload:
    ct_idx: list[int]
    wli: list[list[int]]
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ct_idx": list(self.ct_idx),
            "wli": [list(pair) for pair in self.wli],
            "metadata": dict(self.metadata),
        }


def _source_metadata(source_kind: str) -> dict[str, str]:
    metadata = main_transcript_asset_identity()
    return {
        "source_kind": source_kind,
        "asset_id": metadata["asset_id"],
        "asset_version": metadata["asset_version"],
    }


def payload_from_locator(
    doc: LPTranscript,
    locator: LPFragmentLocator,
    *,
    line_mode: LPLineReadMode | None = None,
    selector: LPLineRuneSelector = LPLineRuneSelector.ALL,
    spiral_route: LPSpiralRoute | None = None,
) -> LPSolverPayload:
    if line_mode is not None and spiral_route is not None:
        raise ValueError("line_mode and spiral_route are mutually exclusive")

    if line_mode is None and spiral_route is None:
        ct_idx, wli = extract_locator_ct_wli(doc, locator)
        metadata = {
            "source": "locator",
            **_source_metadata("liber_primus.locator"),
            "page_scheme": locator.page_ref.scheme.value,
            "page_number": locator.page_ref.number,
            "line": locator.line,
            "line_end": locator.line_end,
            "word": locator.word,
            "word_end": locator.word_end,
            "route": "none",
        }
        return LPSolverPayload(ct_idx=ct_idx, wli=wli, metadata=metadata)

    if locator.word is not None or locator.word_end is not None:
        raise ValueError("routed payload extraction does not support word selectors")

    lines = _locator_line_text(doc, locator)
    if line_mode is not None:
        routed_text = read_lines(lines, mode=line_mode, selector=selector)
        route_name = f"line:{line_mode.value}:{selector.value}"
    else:
        routed_text = spiral_read(lines, route=spiral_route)
        route_name = f"spiral:{spiral_route.direction.value}:{spiral_route.start_corner.value}:{int(spiral_route.skip_empty)}"

    ct_idx, wli = _ct_wli_from_rune_text(routed_text)
    metadata = {
        "source": "locator",
        **_source_metadata("liber_primus.locator"),
        "page_scheme": locator.page_ref.scheme.value,
        "page_number": locator.page_ref.number,
        "line": locator.line,
        "line_end": locator.line_end,
        "word": None,
        "word_end": None,
        "route": route_name,
    }
    return LPSolverPayload(ct_idx=ct_idx, wli=wli, metadata=metadata)


def payload_from_partition_entry(
    doc: LPTranscript,
    entry: LPPartitionEntry,
    *,
    intersect_page_ref: LPPageRef | None = None,
) -> LPSolverPayload:
    if intersect_page_ref is None:
        ct_idx, wli = extract_partition_entry_ct_wli(doc, entry)
        metadata = {
            "source": "partition",
            **_source_metadata("liber_primus.partition"),
            "partition_scheme": entry.scheme.value,
            "partition_ordinal": entry.ordinal.render(),
            "canon_start": entry.start_page.number,
            "canon_end": entry.end_page.number,
            "intersect_page": None,
        }
        return LPSolverPayload(ct_idx=ct_idx, wli=wli, metadata=metadata)

    partition_span = glyph_span_from_partition_entry(doc, entry)
    page = page_view_from_ref(doc, intersect_page_ref)
    intersected = partition_span.intersect(page.glyph_span())
    ct_idx, wli = intersected.ct_wli()
    metadata = {
        "source": "partition",
        **_source_metadata("liber_primus.partition"),
        "partition_scheme": entry.scheme.value,
        "partition_ordinal": entry.ordinal.render(),
        "canon_start": entry.start_page.number,
        "canon_end": entry.end_page.number,
        "intersect_page": {
            "scheme": intersect_page_ref.scheme.value,
            "number": intersect_page_ref.number,
        },
    }
    return LPSolverPayload(ct_idx=ct_idx, wli=wli, metadata=metadata)


def _locator_line_text(doc: LPTranscript, locator: LPFragmentLocator) -> list[str]:
    page = page_view_from_ref(doc, locator.page_ref)
    lines = page.lines()
    if locator.line is None:
        selected = lines
    else:
        start = locator.line
        end = locator.line_end if locator.line_end is not None else locator.line
        if start < 0:
            start = len(lines) + start
        if end < 0:
            end = len(lines) + end
        if not (0 <= start < len(lines)) or not (0 <= end < len(lines)):
            raise IndexError("line selector is out of range")
        if end < start:
            raise ValueError("line_end must be >= line")
        selected = lines[start : end + 1]
    return [line.text(sep="") for line in selected]


def _ct_wli_from_rune_text(text: str) -> tuple[list[int], list[list[int]]]:
    rune2pos = Runeglish.rune2pos
    ct_idx: list[int] = []
    for ch in text:
        pos = rune2pos.get(ch)
        if pos is not None:
            ct_idx.append(pos)
    wli = [[0, 1] for _ in ct_idx]
    return ct_idx, wli


__all__ = [
    "LPSolverPayload",
    "payload_from_locator",
    "payload_from_partition_entry",
]
