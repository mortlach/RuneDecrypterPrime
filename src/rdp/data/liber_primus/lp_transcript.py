from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from rdp.data.runeglish import Runeglish

# -----------------------------
# Format model
# -----------------------------

@dataclass(frozen=True)
class Delimiters:
    """
    File-format delimiters (usually read from the header).
    """
    word: str = "-"
    three_dot: str = ","
    clause: str = "."
    paragraph: str = "&"
    segment: str = "$"
    chapter: str = "§"
    line: str = "/"
    page: str = "%"

    # punctuation that breaks words but does NOT create new structural containers
    extra_punct: Tuple[str, ...] = (";", '"', "'")

    @property
    def structural_markers(self) -> set[str]:
        return {self.paragraph, self.segment, self.chapter, self.page, self.line}

    @property
    def punctuation(self) -> set[str]:
        return {self.three_dot, self.clause, *self.extra_punct}

    @property
    def word_breakers(self) -> set[str]:
        # Anything here ends the current word (if any).
        return {self.word, *self.punctuation}


@dataclass(frozen=True)
class WordRec:
    text: str
    g_start: int
    g_end: int
    chapter: int
    page: int
    line: int
    word_in_line: int


@dataclass(frozen=True)
class LineRec:
    chapter: int
    page: int
    line_in_page: int
    word_start: int
    word_end: int
    g_start: int
    g_end: int


@dataclass(frozen=True)
class PageRec:
    chapter: int
    page_in_chapter: int
    line_start: int
    line_end: int
    word_start: int
    word_end: int
    g_start: int
    g_end: int


@dataclass(frozen=True)
class SectionRec:
    split: str
    section_id: int
    word_start: int
    word_end: int
    label: str = ""


@dataclass(frozen=True)
class DocPos:
    chapter: int
    page: int
    line: int
    word: int
    glyph_in_word: int


@dataclass(frozen=True)
class GlyphSpan:
    doc: "LPTranscript"
    g_start: int
    g_end: int

    def text(self) -> str:
        return "".join(self.doc.glyphs[self.g_start:self.g_end])

    def intersect(self, other: "GlyphSpan") -> "GlyphSpan":
        if self.doc is not other.doc:
            raise ValueError("GlyphSpan.intersect expects spans from the same document")
        start = max(self.g_start, other.g_start)
        end = min(self.g_end, other.g_end)
        if end < start:
            end = start
        return GlyphSpan(self.doc, start, end)

    def word_ids(self) -> List[int]:
        if self.g_start >= self.g_end:
            return []
        w0 = self.doc._glyph_to_word[self.g_start]
        w1 = self.doc._glyph_to_word[self.g_end - 1]
        return list(range(w0, w1 + 1))

    def words(self, *, trim: bool = False) -> List[str]:
        if not trim:
            return [self.doc.words[w].text for w in self.word_ids()]
        if self.g_start >= self.g_end:
            return []
        out: List[str] = []
        cur_word_id: Optional[int] = None
        cur_chars: List[str] = []
        for g in range(self.g_start, self.g_end):
            word_id = self.doc._glyph_to_word[g]
            if cur_word_id is None:
                cur_word_id = word_id
            if word_id != cur_word_id:
                if cur_chars:
                    out.append("".join(cur_chars))
                cur_chars = []
                cur_word_id = word_id
            cur_chars.append(self.doc.glyphs[g])
        if cur_chars:
            out.append("".join(cur_chars))
        return out

    def ct_wli(self) -> tuple[List[int], List[List[int]]]:
        if self.g_start >= self.g_end:
            return [], []
        rune2pos = Runeglish.rune2pos
        ct_idx: List[int] = []
        wli: List[List[int]] = []
        cur_word_id: Optional[int] = None
        cur_word: List[int] = []
        for g in range(self.g_start, self.g_end):
            pos = rune2pos.get(self.doc.glyphs[g])
            if pos is None:
                continue
            word_id = self.doc._glyph_to_word[g]
            if cur_word_id is None:
                cur_word_id = word_id
            if word_id != cur_word_id:
                word_len = len(cur_word)
                wli.extend([[i, word_len] for i in range(word_len)])
                ct_idx.extend(cur_word)
                cur_word = []
                cur_word_id = word_id
            cur_word.append(pos)
        if cur_word:
            word_len = len(cur_word)
            wli.extend([[i, word_len] for i in range(word_len)])
            ct_idx.extend(cur_word)
        return ct_idx, wli


# -----------------------------
# Main parser
# -----------------------------

class LPTranscript:
    """
    Robust parser for the LP-style transcript format.

    Key idea:
      * Keep ONE canonical stream (glyphs / words), with fast index maps.
      * Build hierarchical containers (pages / lines) as spans into that stream.
      * Everything you ask for (page/line/word/section/character-window) becomes a slice.
    """

    def __init__(self, *, delimiters: Delimiters, raw_text: str) -> None:
        self.delims = delimiters
        self.raw = raw_text

        # canonical streams
        self.glyphs: List[str] = []        # glyph-only (no delimiters)
        self.words: List[WordRec] = []     # word spans into glyphs
        self.lines: List[LineRec] = []
        self.pages: List[PageRec] = []

        # fast index maps
        self._glyph_to_word: List[int] = []
        self._glyph_in_word: List[int] = []
        self._word_to_line: List[int] = []
        self._word_to_page: List[int] = []
        self._line_to_page: List[int] = []
        self._loc_to_word: Dict[Tuple[int, int, int, int], int] = {}

        # user-defined section splits
        self._splits: Dict[str, List[SectionRec]] = {}

        # optional page metadata (canon names, etc.)
        self._page_catalogue: Dict[int, Dict[str, str]] = {}
        self._canon_to_page: Dict[str, int] = {}

        self._parse()

    # ---------- construction ----------

    @classmethod
    def from_file(cls, path: str | Path, *, delimiters: Delimiters | None = None) -> "LPTranscript":
        p = Path(path)
        raw_text = p.read_text(encoding="utf-8")
        delims = delimiters or cls._parse_delimiter_header(raw_text)
        return cls(delimiters=delims, raw_text=raw_text)

    @staticmethod
    def _parse_delimiter_header(raw_text: str) -> Delimiters:
        """
        Parses the header block:

            Delimiters
            Word     : -
            Three-dot symbol: ,
            Clause   : .
            Paragraph: &
            Segment  : $
            Chapter  : §
            Line     : /
            Page     : %
        """
        lines = raw_text.splitlines()
        if not lines or not lines[0].strip().lower().startswith("delimiters"):
            return Delimiters()

        mapping: Dict[str, str] = {}
        for ln in lines[1:15]:
            if ":" not in ln:
                continue
            k, v = ln.split(":", 1)
            k = k.strip().lower()
            v = v.strip()
            if v:
                mapping[k] = v[0]

        return Delimiters(
            word=mapping.get("word", "-"),
            three_dot=mapping.get("three-dot symbol", ","),
            clause=mapping.get("clause", "."),
            paragraph=mapping.get("paragraph", "&"),
            segment=mapping.get("segment", "$"),
            chapter=mapping.get("chapter", "§"),
            line=mapping.get("line", "/"),
            page=mapping.get("page", "%"),
        )

    # ---------- basic views ----------

    def summary(self) -> str:
        return f"LPTranscript(pages={len(self.pages)}, lines={len(self.lines)}, words={len(self.words)}, glyphs={len(self.glyphs)})"

    def page(self, page_id: int) -> "PageView":
        return PageView(self, page_id)

    def line(self, line_id: int) -> "LineView":
        return LineView(self, line_id)

    def word(self, word_id: int) -> "WordView":
        return WordView(self, word_id)

    # ---------- random access helpers ----------

    def word_id_at(self, *, chapter: int, page: int, line: int, word_in_line: int) -> int:
        key = (chapter, page, line, word_in_line)
        if key not in self._loc_to_word:
            raise KeyError(f"No word at {key}")
        return self._loc_to_word[key]

    def glyph_pos(self, glyph_index: int) -> DocPos:
        """
        glyph_index can be negative (counting backwards from the end).
        """
        if glyph_index < 0:
            glyph_index = len(self.glyphs) + glyph_index
        if not (0 <= glyph_index < len(self.glyphs)):
            raise IndexError("glyph_index out of range")

        w = self._glyph_to_word[glyph_index]
        line_id = self.line_id_at_glyph(glyph_index)
        lr = self.lines[line_id]
        return DocPos(
            chapter=lr.chapter,
            page=lr.page,
            line=lr.line_in_page,
            word=w,
            glyph_in_word=self._glyph_in_word[glyph_index],
        )

    def line_id_at_glyph(self, glyph_index: int) -> int:
        if glyph_index < 0:
            glyph_index = len(self.glyphs) + glyph_index
        if not (0 <= glyph_index < len(self.glyphs)):
            raise IndexError("glyph_index out of range")
        for line_id, rec in enumerate(self.lines):
            if rec.g_start <= glyph_index < rec.g_end:
                return line_id
        raise ValueError(f"No line covers glyph index {glyph_index}")

    def glyph_span(self, start: int, length: int) -> GlyphSpan:
        """
        start can be negative (counting backwards from the end).
        """
        if length < 0:
            raise ValueError("length must be >= 0")
        n = len(self.glyphs)
        if start < 0:
            start = n + start
        start = max(0, min(n, start))
        end = max(0, min(n, start + length))
        return GlyphSpan(self, start, end)

    def around_glyph(self, centre: int, left: int, right: int) -> GlyphSpan:
        """
        Convenience: window around a glyph index.
        """
        if centre < 0:
            centre = len(self.glyphs) + centre
        start = max(0, centre - left)
        end = min(len(self.glyphs), centre + right + 1)
        return GlyphSpan(self, start, end)

    # ---------- page catalogue / canon names ----------

    def attach_page_catalogue(self, source: str | Path | Dict[int, Dict[str, str]]) -> None:
        if isinstance(source, (str, Path)):
            p = Path(source)
            data = p.read_text(encoding="utf-8")
            mapping = json.loads(data)
        else:
            mapping = source

        page_catalogue: Dict[int, Dict[str, str]] = {}
        canon_to_page: Dict[str, int] = {}

        for key, meta in mapping.items():
            page_id = int(key)
            if not isinstance(meta, dict):
                raise TypeError("page catalogue entries must be dicts")
            canon = meta.get("canon")
            if canon:
                canon_to_page[str(canon)] = page_id
            page_catalogue[page_id] = {k: str(v) for k, v in meta.items()}

        self._page_catalogue = page_catalogue
        self._canon_to_page = canon_to_page

    def page_id_by_canon(self, canon_name: str) -> int:
        if canon_name not in self._canon_to_page:
            raise KeyError(f"No page mapped for canon name '{canon_name}'")
        return self._canon_to_page[canon_name]

    def page_by_canon(self, canon_name: str) -> "PageView":
        return self.page(self.page_id_by_canon(canon_name))

    def page_canon_name(self, page_id: int) -> Optional[str]:
        meta = self._page_catalogue.get(page_id)
        if not meta:
            return None
        return meta.get("canon")

    def page_meta(self, page_id: int) -> Optional[Dict[str, str]]:
        return self._page_catalogue.get(page_id)

    def page_label(self, page_id: int) -> str:
        meta = self._page_catalogue.get(page_id, {})
        label = meta.get("label") or meta.get("canon")
        return label or f"page-{page_id}"

    # ---------- section splits (custom markers / red-rune-derived boundaries) ----------

    def list_splits(self) -> List[str]:
        return sorted(self._splits.keys())

    def add_split_from_boundaries(
        self,
        name: str,
        *,
        boundaries_word_ids: Sequence[int],
        start_section_id: int = 0,
        labels: Optional[Sequence[str]] = None,
    ) -> None:
        """
        boundaries_word_ids: strictly increasing list of word indices where each section starts.
        Example: [0, 120, 250, len(words)]  -> 3 sections.
        """
        if name in self._splits:
            raise KeyError(f"Split '{name}' already exists.")

        b = list(boundaries_word_ids)
        if not b or b[0] != 0:
            raise ValueError("boundaries_word_ids must start with 0")
        if b[-1] != len(self.words):
            raise ValueError("boundaries_word_ids must end with len(words)")
        if any(b[i] >= b[i + 1] for i in range(len(b) - 1)):
            raise ValueError("boundaries_word_ids must be strictly increasing")

        sections: List[SectionRec] = []
        for i in range(len(b) - 1):
            label = labels[i] if labels and i < len(labels) else ""
            sections.append(
                SectionRec(
                    split=name,
                    section_id=start_section_id + i,
                    word_start=b[i],
                    word_end=b[i + 1],
                    label=label,
                )
            )
        self._splits[name] = sections

    def add_split_by_word_patterns(
        self,
        name: str,
        *,
        patterns: Sequence[Sequence[str]],
        start_section_id: int = 0,
        include_match_word: bool = True,
    ) -> None:
        """
        Build split boundaries by finding each (multi-word) pattern in the transcript word stream.

        Useful for:
          * custom markers you inject as special "words"
          * “section starts” that are identifiable as fixed word sequences
        """
        if name in self._splits:
            raise KeyError(f"Split '{name}' already exists.")

        word_texts = [w.text for w in self.words]
        starts: List[int] = []

        for pat in patterns:
            pat = list(pat)
            if not pat:
                continue

            for i in range(0, len(word_texts) - len(pat) + 1):
                if word_texts[i:i + len(pat)] == pat:
                    starts.append(i if include_match_word else i + len(pat))
                    break

        boundaries = sorted(set([0, *starts, len(self.words)]))
        self.add_split_from_boundaries(name, boundaries_word_ids=boundaries, start_section_id=start_section_id)

    def section(self, split: str, section_id: int) -> "SectionView":
        if split not in self._splits:
            raise KeyError(f"Unknown split '{split}'. Known: {self.list_splits()}")
        for s in self._splits[split]:
            if s.section_id == section_id:
                return SectionView(self, s)
        raise KeyError(f"No section_id={section_id} in split '{split}'.")

    def section_by_label(self, *, split: str, label: str) -> "SectionView":
        if split not in self._splits:
            raise KeyError(f"Unknown split '{split}'. Known: {self.list_splits()}")
        matches = [s for s in self._splits[split] if s.label == label]
        if not matches:
            raise KeyError(f"No section label '{label}' in split '{split}'.")
        if len(matches) > 1:
            raise KeyError(f"Multiple sections with label '{label}' in split '{split}'.")
        return SectionView(self, matches[0])

    # ---------- parsing ----------

    def _parse(self) -> None:
        lines = self.raw.splitlines()

        # Body starts after the blank line following the delimiter legend.
        body_start = 0
        if lines and lines[0].strip().lower().startswith("delimiters"):
            for i, ln in enumerate(lines):
                if i > 0 and ln.strip() == "":
                    body_start = i + 1
                    break

        chapter = 0
        page = 0
        line_in_page = 0

        cur_word_chars: List[str] = []
        cur_word_g_start: Optional[int] = None
        cur_word_start_chapter: Optional[int] = None
        cur_word_start_page: Optional[int] = None
        cur_word_start_line: Optional[int] = None
        cur_word_start_word_in_line: Optional[int] = None
        cur_word_start_line_id: Optional[int] = None
        cur_word_start_page_id: Optional[int] = None
        word_in_line = 0

        line_word_start = 0
        line_g_start = 0

        page_line_start = 0
        page_word_start = 0
        page_g_start = 0

        def flush_word() -> None:
            nonlocal cur_word_chars, cur_word_g_start
            nonlocal cur_word_start_chapter, cur_word_start_page, cur_word_start_line
            nonlocal cur_word_start_word_in_line, cur_word_start_line_id, cur_word_start_page_id
            if not cur_word_chars:
                cur_word_g_start = None
                return

            text = "".join(cur_word_chars)
            g_start = cur_word_g_start if cur_word_g_start is not None else len(self.glyphs) - len(cur_word_chars)
            g_end = g_start + len(cur_word_chars)

            start_chapter = 0 if cur_word_start_chapter is None else cur_word_start_chapter
            start_page = 0 if cur_word_start_page is None else cur_word_start_page
            start_line = 0 if cur_word_start_line is None else cur_word_start_line
            start_word_in_line = 0 if cur_word_start_word_in_line is None else cur_word_start_word_in_line

            w_idx = len(self.words)
            wrec = WordRec(
                text=text,
                g_start=g_start,
                g_end=g_end,
                chapter=start_chapter,
                page=start_page,
                line=start_line,
                word_in_line=start_word_in_line,
            )
            self.words.append(wrec)
            self._loc_to_word[(start_chapter, start_page, start_line, start_word_in_line)] = w_idx

            for j in range(g_start, g_end):
                self._glyph_to_word.append(w_idx)
                self._glyph_in_word.append(j - g_start)

            if cur_word_start_line_id is not None:
                self._word_to_line.append(cur_word_start_line_id)
            if cur_word_start_page_id is not None:
                self._word_to_page.append(cur_word_start_page_id)

            cur_word_chars = []
            cur_word_g_start = None
            cur_word_start_chapter = None
            cur_word_start_page = None
            cur_word_start_line = None
            cur_word_start_word_in_line = None
            cur_word_start_line_id = None
            cur_word_start_page_id = None

        def flush_line(force_advance: bool) -> None:
            """
            force_advance=True preserves explicit blank lines if the transcript ever contains them.
            """
            nonlocal line_word_start, line_g_start, word_in_line, line_in_page

            word_end = len(self.words)
            g_end = len(self.glyphs)
            has_content = (word_end > line_word_start) or (g_end > line_g_start)

            if has_content:
                l_idx = len(self.lines)
                self.lines.append(
                    LineRec(
                        chapter=chapter,
                        page=page,
                        line_in_page=line_in_page,
                        word_start=line_word_start,
                        word_end=word_end,
                        g_start=line_g_start,
                        g_end=g_end,
                    )
                )
                self._line_to_page.append(len(self.pages))  # provisional until page closes

            if has_content or force_advance:
                line_in_page += 1
                word_in_line = 0
                line_word_start = len(self.words)
                line_g_start = len(self.glyphs)

        def flush_page(force_advance: bool) -> None:
            nonlocal page_line_start, page_word_start, page_g_start, page, line_in_page
            flush_line(force_advance=False)

            line_end = len(self.lines)
            word_end = len(self.words)
            g_end = len(self.glyphs)
            has_content = (line_end > page_line_start) or (word_end > page_word_start) or (g_end > page_g_start)

            if has_content:
                p_idx = len(self.pages)
                self.pages.append(
                    PageRec(
                        chapter=chapter,
                        page_in_chapter=page,
                        line_start=page_line_start,
                        line_end=line_end,
                        word_start=page_word_start,
                        word_end=word_end,
                        g_start=page_g_start,
                        g_end=g_end,
                    )
                )
                for li in range(page_line_start, line_end):
                    self._line_to_page[li] = p_idx

            if has_content or force_advance:
                page += 1
                line_in_page = 0
                page_line_start = len(self.lines)
                page_word_start = len(self.words)
                page_g_start = len(self.glyphs)

        def start_new_chapter() -> None:
            nonlocal chapter, page, line_in_page, page_line_start, page_word_start, page_g_start
            flush_page(force_advance=False)
            chapter += 1
            page = 0
            line_in_page = 0
            page_line_start = len(self.lines)
            page_word_start = len(self.words)
            page_g_start = len(self.glyphs)

        def hard_break() -> None:
            flush_line(force_advance=False)

        for raw_ln in lines[body_start:]:
            ln = raw_ln.strip()
            if not ln:
                continue

            # If you begin annotating the transcript, these are safe to ignore:
            if ln.startswith("#") or ln.startswith("//"):
                continue

            # Marker lines (standalone):
            if ln == self.delims.paragraph or ln == self.delims.segment:
                hard_break()
                continue
            if ln == self.delims.page:
                flush_page(force_advance=False)
                continue
            if ln == self.delims.chapter:
                start_new_chapter()
                continue

            # Content line: scan chars; '/' is authoritative for line breaks.
            for ch in ln:
                if ch.isspace():
                    continue

                if ch == self.delims.line:
                    flush_line(force_advance=True)
                    continue
                if ch == self.delims.page:
                    flush_page(force_advance=True)
                    continue
                if ch == self.delims.chapter:
                    start_new_chapter()
                    continue
                if ch == self.delims.paragraph or ch == self.delims.segment:
                    hard_break()
                    continue

                if ch in self.delims.word_breakers:
                    flush_word()
                    continue

                # otherwise, a glyph
                if cur_word_g_start is None:
                    cur_word_g_start = len(self.glyphs)
                    cur_word_start_chapter = chapter
                    cur_word_start_page = page
                    cur_word_start_line = line_in_page
                    cur_word_start_word_in_line = word_in_line
                    cur_word_start_line_id = len(self.lines)
                    cur_word_start_page_id = len(self.pages)
                    word_in_line += 1
                self.glyphs.append(ch)
                cur_word_chars.append(ch)

        # Finalise any trailing content
        flush_word()
        flush_page(force_advance=False)
        self._rebuild_word_ranges()

    def _rebuild_word_ranges(self) -> None:
        if not self.words or not self.glyphs:
            return

        def _range_for_span(g_start: int, g_end: int) -> Tuple[int, int]:
            if g_start >= g_end:
                if g_start == 0:
                    return 0, 0
                last = self._glyph_to_word[g_start - 1]
                return last + 1, last + 1
            w_start = self._glyph_to_word[g_start]
            w_end = self._glyph_to_word[g_end - 1] + 1
            return w_start, w_end

        new_lines: List[LineRec] = []
        for rec in self.lines:
            w_start, w_end = _range_for_span(rec.g_start, rec.g_end)
            new_lines.append(
                LineRec(
                    chapter=rec.chapter,
                    page=rec.page,
                    line_in_page=rec.line_in_page,
                    word_start=w_start,
                    word_end=w_end,
                    g_start=rec.g_start,
                    g_end=rec.g_end,
                )
            )
        self.lines = new_lines

        new_pages: List[PageRec] = []
        for rec in self.pages:
            w_start, w_end = _range_for_span(rec.g_start, rec.g_end)
            new_pages.append(
                PageRec(
                    chapter=rec.chapter,
                    page_in_chapter=rec.page_in_chapter,
                    line_start=rec.line_start,
                    line_end=rec.line_end,
                    word_start=w_start,
                    word_end=w_end,
                    g_start=rec.g_start,
                    g_end=rec.g_end,
                )
            )
        self.pages = new_pages


# -----------------------------
# Views (chainable access)
# -----------------------------

@dataclass(frozen=True)
class WordView:
    doc: LPTranscript
    word_id: int

    @property
    def rec(self) -> WordRec:
        return self.doc.words[self.word_id]

    def text(self) -> str:
        return self.rec.text

    def glyph_span(self) -> GlyphSpan:
        return GlyphSpan(self.doc, self.rec.g_start, self.rec.g_end)


@dataclass(frozen=True)
class LineView:
    doc: LPTranscript
    line_id: int

    @property
    def rec(self) -> LineRec:
        return self.doc.lines[self.line_id]

    def words(self) -> List[WordView]:
        return [WordView(self.doc, wi) for wi in range(self.rec.word_start, self.rec.word_end)]

    def text(self, sep: str = " ") -> str:
        return sep.join(self.doc.words[wi].text for wi in range(self.rec.word_start, self.rec.word_end))

    def glyph_span(self) -> GlyphSpan:
        return GlyphSpan(self.doc, self.rec.g_start, self.rec.g_end)


@dataclass(frozen=True)
class PageView:
    doc: LPTranscript
    page_id: int

    @property
    def rec(self) -> PageRec:
        return self.doc.pages[self.page_id]

    def lines(self) -> List[LineView]:
        return [LineView(self.doc, li) for li in range(self.rec.line_start, self.rec.line_end)]

    def text(self, sep: str = " ", line_sep: str = "\n") -> str:
        return line_sep.join(l.text(sep=sep) for l in self.lines())

    def glyph_span(self) -> GlyphSpan:
        return GlyphSpan(self.doc, self.rec.g_start, self.rec.g_end)

    @property
    def canon_name(self) -> Optional[str]:
        return self.doc.page_canon_name(self.page_id)

    @property
    def label(self) -> str:
        return self.doc.page_label(self.page_id)


@dataclass(frozen=True)
class SectionView:
    doc: LPTranscript
    rec: SectionRec

    def words(self) -> List[WordView]:
        return [WordView(self.doc, wi) for wi in range(self.rec.word_start, self.rec.word_end)]

    def local_word_index(self, word_id: int) -> int:
        if not (self.rec.word_start <= word_id < self.rec.word_end):
            raise ValueError("word_id not in this section")
        return word_id - self.rec.word_start

    def text(self, sep: str = " ", line_sep: str = "\n") -> str:
        # group by global line boundaries
        out_lines: List[str] = []
        cur_line: Optional[int] = None
        cur_words: List[str] = []

        for wi in range(self.rec.word_start, self.rec.word_end):
            li = self.doc._word_to_line[wi]
            if cur_line is None:
                cur_line = li
            if li != cur_line:
                out_lines.append(sep.join(cur_words))
                cur_words = [self.doc.words[wi].text]
                cur_line = li
            else:
                cur_words.append(self.doc.words[wi].text)

        if cur_words:
            out_lines.append(sep.join(cur_words))

        return line_sep.join(out_lines)

    def glyph_span(self) -> GlyphSpan:
        if self.rec.word_start == self.rec.word_end:
            return GlyphSpan(self.doc, 0, 0)
        g_start = self.doc.words[self.rec.word_start].g_start
        g_end = self.doc.words[self.rec.word_end - 1].g_end
        return GlyphSpan(self.doc, g_start, g_end)
