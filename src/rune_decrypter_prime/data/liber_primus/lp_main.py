"""Helpers for the main LP transcript (page catalogue + section matching)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional, Sequence, Tuple

from rune_decrypter_prime.data.asset_paths import (
    find_repo_root,
    resolve_assets_path,
    to_repo_relative,
)
from rune_decrypter_prime.data.liber_primus.lp_data import LPSection, LP_DATA
from rune_decrypter_prime.data.liber_primus.lp_registry import (
    LPFragmentLocator,
    LPPageRef,
    LPPartitionEntry,
    LPResolutionContext,
    resolve_page_ref,
    resolve_relative_index,
)
from rune_decrypter_prime.data.liber_primus.lp_routes import (
    LPLineReadMode,
    LPLineRuneSelector,
    read_lines,
)
from rune_decrypter_prime.data.liber_primus.lp_transcript import LPTranscript
from rune_decrypter_prime.utils.runeglish import Runeglish

_DEFAULT_LP_ASSETS_REL = Path("liber_primus")
_MAIN_TRANSCRIPT_NAME = "liber-primus__transcription--master.txt"
MAIN_TRANSCRIPT_ASSET_ID = "liber_primus.main_transcript"


def default_main_transcript_path() -> Path:
    return resolve_assets_path(str(_DEFAULT_LP_ASSETS_REL), _MAIN_TRANSCRIPT_NAME, start=Path(__file__))


MAIN_TRANSCRIPT = default_main_transcript_path()
CANON_PAGE_COUNT = 58
CANON_SUFFIX = ".jpg"


def main_transcript_asset_identity() -> dict[str, str]:
    asset_id, asset_version = _cached_main_transcript_asset_identity()
    return {
        "asset_id": asset_id,
        "asset_version": asset_version,
    }


@lru_cache(maxsize=1)
def _cached_main_transcript_asset_identity() -> tuple[str, str]:
    root = find_repo_root(Path(__file__))
    manifest_path = root / "assets_manifest_v1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest.get("required_assets")
    if not isinstance(rows, list):
        raise RuntimeError("assets_manifest_v1.json required_assets must be a list")
    matches = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("asset_id") == MAIN_TRANSCRIPT_ASSET_ID
    ]
    if len(matches) != 1:
        raise RuntimeError(_main_transcript_manifest_error("expected exactly one manifest row"))
    row = matches[0]
    asset_version = row.get("asset_version")
    if not isinstance(asset_version, str) or not asset_version:
        raise RuntimeError(_main_transcript_manifest_error("asset_version must be defined"))
    if row.get("version_scheme") != "sha256":
        raise RuntimeError(_main_transcript_manifest_error("version_scheme must be 'sha256'"))
    if row.get("sha256") != asset_version:
        raise RuntimeError(_main_transcript_manifest_error("asset_version must match sha256"))
    return MAIN_TRANSCRIPT_ASSET_ID, asset_version


def _main_transcript_manifest_error(detail: str) -> str:
    return f"Manifest row for asset_id={MAIN_TRANSCRIPT_ASSET_ID!r}: {detail}"


@dataclass(frozen=True)
class RuneWordIndex:
    word_ids: Tuple[int, ...]
    rune_words: Tuple[Tuple[int, ...], ...]

    @classmethod
    def from_doc(cls, doc: LPTranscript) -> "RuneWordIndex":
        rune2pos = Runeglish.rune2pos
        word_ids: list[int] = []
        rune_words: list[Tuple[int, ...]] = []
        for word_id, word in enumerate(doc.words):
            positions = [rune2pos[ch] for ch in word.text if ch in rune2pos]
            if not positions:
                continue
            word_ids.append(word_id)
            rune_words.append(tuple(positions))
        return cls(tuple(word_ids), tuple(rune_words))


@dataclass(frozen=True)
class RuneGlyphIndex:
    glyph_ids: Tuple[int, ...]
    rune_positions: Tuple[int, ...]

    @classmethod
    def from_doc(cls, doc: LPTranscript) -> "RuneGlyphIndex":
        rune2pos = Runeglish.rune2pos
        glyph_ids: list[int] = []
        rune_positions: list[int] = []
        for glyph_id, ch in enumerate(doc.glyphs):
            pos = rune2pos.get(ch)
            if pos is None:
                continue
            glyph_ids.append(glyph_id)
            rune_positions.append(pos)
        return cls(tuple(glyph_ids), tuple(rune_positions))


@dataclass(frozen=True)
class SectionMatch:
    section_id: int
    split: str
    start_index: int
    end_index: int
    glyph_id_start: int
    glyph_id_end: int
    word_id_start: int
    word_id_end: int
    page_start: int
    page_end: int
    canon_start: Optional[int]
    canon_end: Optional[int]

    def page_ids(self) -> list[int]:
        return list(range(self.page_start, self.page_end + 1))


def make_resolution_context(doc: LPTranscript) -> LPResolutionContext:
    return LPResolutionContext(total_pages=len(doc.pages), canon_page_count=CANON_PAGE_COUNT)


def resolve_typed_page_ref(doc: LPTranscript, page_ref: LPPageRef) -> int:
    return resolve_page_ref(page_ref, context=make_resolution_context(doc))


def page_view_from_ref(doc: LPTranscript, page_ref: LPPageRef):
    return doc.page(resolve_typed_page_ref(doc, page_ref))


def glyph_span_from_locator(doc: LPTranscript, locator: LPFragmentLocator):
    page_view = page_view_from_ref(doc, locator.page_ref)

    if locator.line is None:
        if locator.word is not None or locator.word_end is not None:
            raise ValueError("word selectors require locator.line")
        return page_view.glyph_span()

    lines = page_view.lines()
    line_start_ix = resolve_relative_index(len(lines), locator.line)
    line_end_ix = line_start_ix
    if locator.line_end is not None:
        line_end_ix = resolve_relative_index(len(lines), locator.line_end)
    if line_end_ix < line_start_ix:
        raise ValueError("line_end must be >= line")

    selected_lines = lines[line_start_ix:line_end_ix + 1]
    if not selected_lines:
        return doc.glyph_span(0, 0)

    if locator.word is None and locator.word_end is None:
        g_start = selected_lines[0].rec.g_start
        g_end = selected_lines[-1].rec.g_end
        return doc.glyph_span(g_start, g_end - g_start)

    if len(selected_lines) != 1:
        raise ValueError("word selectors are supported only for a single selected line")

    words = selected_lines[0].words()
    word_start_ix = resolve_relative_index(len(words), locator.word if locator.word is not None else 0)
    word_end_ix = word_start_ix
    if locator.word_end is not None:
        word_end_ix = resolve_relative_index(len(words), locator.word_end)
    if word_end_ix < word_start_ix:
        raise ValueError("word_end must be >= word")

    selected_words = words[word_start_ix:word_end_ix + 1]
    if not selected_words:
        return doc.glyph_span(0, 0)
    g_start = selected_words[0].rec.g_start
    g_end = selected_words[-1].rec.g_end
    return doc.glyph_span(g_start, g_end - g_start)


def extract_locator_ct_wli(doc: LPTranscript, locator: LPFragmentLocator) -> tuple[list[int], list[list[int]]]:
    return glyph_span_from_locator(doc, locator).ct_wli()


def glyph_span_from_partition_entry(doc: LPTranscript, entry: LPPartitionEntry):
    start_canon, end_canon = entry.canon_page_range()
    start_page = page_view_from_ref(doc, LPPageRef.canon_page(start_canon))
    end_page = page_view_from_ref(doc, LPPageRef.canon_page(end_canon))
    return doc.glyph_span(start_page.rec.g_start, end_page.rec.g_end - start_page.rec.g_start)


def extract_partition_entry_ct_wli(doc: LPTranscript, entry: LPPartitionEntry) -> tuple[list[int], list[list[int]]]:
    return glyph_span_from_partition_entry(doc, entry).ct_wli()


def route_locator_lines_text(
    doc: LPTranscript,
    locator: LPFragmentLocator,
    *,
    mode: LPLineReadMode,
    selector: LPLineRuneSelector = LPLineRuneSelector.ALL,
) -> str:
    if locator.word is not None or locator.word_end is not None:
        raise ValueError("route_locator_lines_text supports line/page locators only")
    page_view = page_view_from_ref(doc, locator.page_ref)
    lines = page_view.lines()
    if locator.line is not None:
        start_ix = resolve_relative_index(len(lines), locator.line)
        end_ix = start_ix if locator.line_end is None else resolve_relative_index(len(lines), locator.line_end)
        if end_ix < start_ix:
            raise ValueError("line_end must be >= line")
        lines = lines[start_ix:end_ix + 1]
    line_text = [line.text(sep="") for line in lines]
    return read_lines(line_text, mode=mode, selector=selector)


def load_main_transcript(*, attach_catalogue: bool = True) -> LPTranscript:
    if not MAIN_TRANSCRIPT.exists():
        rel = to_repo_relative(MAIN_TRANSCRIPT, start=Path(__file__))
        raise FileNotFoundError(f"Liber Primus main transcript not found: {rel}")
    doc = LPTranscript.from_file(MAIN_TRANSCRIPT)
    if attach_catalogue:
        attach_default_page_catalogue(doc)
    return doc


def attach_default_page_catalogue(
    doc: LPTranscript,
    *,
    canon_count: int = CANON_PAGE_COUNT,
    canon_suffix: str = CANON_SUFFIX,
    pre_label_prefix: str | None = "front",
) -> int:
    offset = len(doc.pages) - canon_count
    if offset < 0:
        raise ValueError(f"Transcript has {len(doc.pages)} pages; cannot map {canon_count} canon pages.")

    mapping: dict[int, dict[str, str]] = {}
    for page_id in range(len(doc.pages)):
        meta: dict[str, str] = {}
        if page_id >= offset:
            canon_num = page_id - offset
            canon = f"{canon_num}{canon_suffix}"
            meta["canon"] = canon
            meta["label"] = canon
        elif pre_label_prefix:
            meta["label"] = f"{pre_label_prefix}-{page_id}"

        if meta:
            mapping[page_id] = meta

    doc.attach_page_catalogue(mapping)
    return offset


def match_lp_section(
    doc: LPTranscript,
    section: LPSection,
    *,
    rune_index: RuneGlyphIndex | None = None,
) -> SectionMatch:
    index = rune_index or RuneGlyphIndex.from_doc(doc)
    needle = list(section.ct_idx)
    start = _find_subsequence(index.rune_positions, needle)
    if start is None:
        raise ValueError(f"Unable to locate section {section.section_id} in transcript rune stream.")

    end = start + len(needle)
    glyph_id_start = index.glyph_ids[start]
    glyph_id_end = index.glyph_ids[end - 1]
    word_id_start = doc._glyph_to_word[glyph_id_start]
    word_id_end = doc._glyph_to_word[glyph_id_end]
    page_start = _page_id_for_glyph(doc, glyph_id_start)
    page_end = _page_id_for_glyph(doc, glyph_id_end)
    canon_start = _canon_number(doc.page_canon_name(page_start))
    canon_end = _canon_number(doc.page_canon_name(page_end))

    return SectionMatch(
        section_id=section.section_id,
        split=section.split,
        start_index=start,
        end_index=end,
        glyph_id_start=glyph_id_start,
        glyph_id_end=glyph_id_end,
        word_id_start=word_id_start,
        word_id_end=word_id_end,
        page_start=page_start,
        page_end=page_end,
        canon_start=canon_start,
        canon_end=canon_end,
    )


def match_lp_sections(
    doc: LPTranscript,
    *,
    split: str = "page",
    rune_index: RuneGlyphIndex | None = None,
) -> dict[int, SectionMatch]:
    index = rune_index or RuneGlyphIndex.from_doc(doc)
    matches: dict[int, SectionMatch] = {}
    for section_id in LP_DATA.list_sections(split=split):
        section = LP_DATA.get_section(section_id, split=split)
        matches[section_id] = match_lp_section(doc, section, rune_index=index)
    return matches


def extract_section_ct_wli(
    doc: LPTranscript,
    section: LPSection,
    *,
    rune_index: RuneGlyphIndex | None = None,
) -> tuple[list[int], list[list[int]]]:
    index = rune_index or RuneGlyphIndex.from_doc(doc)
    needle = list(section.ct_idx)
    start = _find_subsequence(index.rune_positions, needle)
    if start is None:
        raise ValueError(f"Unable to locate section {section.section_id} in transcript rune stream.")
    end = start + len(needle)
    glyph_ids = index.glyph_ids[start:end]
    return _ct_wli_from_glyph_ids(doc, glyph_ids)


def extract_section_ct_wli_by_id(
    doc: LPTranscript,
    *,
    section_id: int,
    split: str = "page",
    rune_index: RuneGlyphIndex | None = None,
) -> tuple[list[int], list[list[int]]]:
    section = LP_DATA.get_section(section_id, split=split)
    return extract_section_ct_wli(doc, section, rune_index=rune_index)


def _find_subsequence(
    haystack: Sequence[int],
    needle: Sequence[int],
) -> Optional[int]:
    if not needle or len(needle) > len(haystack):
        return None
    needle_tuple = tuple(needle)
    first = needle_tuple[0]
    max_start = len(haystack) - len(needle)
    for i in range(max_start + 1):
        if haystack[i] != first:
            continue
        if haystack[i:i + len(needle)] == needle_tuple:
            return i
    return None


def _ct_wli_from_glyph_ids(
    doc: LPTranscript,
    glyph_ids: Sequence[int],
) -> tuple[list[int], list[list[int]]]:
    rune2pos = Runeglish.rune2pos
    ct_idx: list[int] = []
    wli: list[list[int]] = []
    cur_word_id: int | None = None
    cur_word_positions: list[int] = []
    for glyph_id in glyph_ids:
        pos = rune2pos.get(doc.glyphs[glyph_id])
        if pos is None:
            continue
        word_id = doc._glyph_to_word[glyph_id]
        if cur_word_id is None:
            cur_word_id = word_id
        if word_id != cur_word_id:
            word_len = len(cur_word_positions)
            wli.extend([[i, word_len] for i in range(word_len)])
            ct_idx.extend(cur_word_positions)
            cur_word_positions = []
            cur_word_id = word_id
        cur_word_positions.append(pos)
    if cur_word_positions:
        word_len = len(cur_word_positions)
        wli.extend([[i, word_len] for i in range(word_len)])
        ct_idx.extend(cur_word_positions)
    return ct_idx, wli


def _canon_number(canon_name: Optional[str]) -> Optional[int]:
    if not canon_name:
        return None
    stem = canon_name.split(".", 1)[0]
    if stem.isdigit():
        return int(stem)
    return None


def _page_id_for_glyph(doc: LPTranscript, glyph_id: int) -> int:
    for page_id, rec in enumerate(doc.pages):
        if rec.g_start <= glyph_id < rec.g_end:
            return page_id
    raise ValueError(f"No page covers glyph index {glyph_id}")


__all__ = [
    "CANON_PAGE_COUNT",
    "CANON_SUFFIX",
    "MAIN_TRANSCRIPT",
    "RuneGlyphIndex",
    "RuneWordIndex",
    "SectionMatch",
    "attach_default_page_catalogue",
    "extract_locator_ct_wli",
    "extract_partition_entry_ct_wli",
    "extract_section_ct_wli",
    "extract_section_ct_wli_by_id",
    "glyph_span_from_locator",
    "glyph_span_from_partition_entry",
    "load_main_transcript",
    "make_resolution_context",
    "match_lp_section",
    "match_lp_sections",
    "page_view_from_ref",
    "resolve_typed_page_ref",
    "route_locator_lines_text",
]
