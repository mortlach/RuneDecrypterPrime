"""Helpers for the master LP transcript (page catalogue + section matching)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

from rune_decrypter_prime.data.liber_primus.lp_data import LPSection, LP_DATA
from rune_decrypter_prime.data.liber_primus.lp_transcript import LPTranscript
from rune_decrypter_prime.utils.runeglish import Runeglish

MASTER_TRANSCRIPT = Path(__file__).with_name("liber-primus__transcription--master.txt")
CANON_PAGE_COUNT = 58
CANON_SUFFIX = ".jpg"


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


def load_master_transcript(*, attach_catalogue: bool = True) -> LPTranscript:
    doc = LPTranscript.from_file(MASTER_TRANSCRIPT)
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
    "MASTER_TRANSCRIPT",
    "RuneGlyphIndex",
    "RuneWordIndex",
    "SectionMatch",
    "attach_default_page_catalogue",
    "extract_section_ct_wli",
    "extract_section_ct_wli_by_id",
    "load_master_transcript",
    "match_lp_section",
    "match_lp_sections",
]
