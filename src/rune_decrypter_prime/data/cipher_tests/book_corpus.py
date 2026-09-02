"""Load deterministic passages from the packaged cipher-test book corpus."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any

import numpy as np

from rdp.core.types import Direction, ensure_direction


@dataclass(frozen=True, slots=True)
class BookCorpus:
    book: str
    direction: Direction
    plaintext: np.ndarray
    wli: np.ndarray
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class BookPassage:
    book: str
    direction: Direction
    start_word: int
    word_count: int
    plaintext: np.ndarray
    wli: np.ndarray


def _books_root():
    return resources.files(__package__).joinpath("books")


def available_books() -> tuple[str, ...]:
    root = _books_root()
    ltr_suffix = "_ltr.npz"
    rtl_suffix = "_rtl.npz"
    ltr = {
        item.name[: -len(ltr_suffix)]
        for item in root.iterdir()
        if item.name.endswith(ltr_suffix)
    }
    rtl = {
        item.name[: -len(rtl_suffix)]
        for item in root.iterdir()
        if item.name.endswith(rtl_suffix)
    }
    if ltr != rtl:
        missing_ltr = sorted(rtl - ltr)
        missing_rtl = sorted(ltr - rtl)
        raise ValueError(
            f"incomplete book direction pairs: missing_ltr={missing_ltr}, "
            f"missing_rtl={missing_rtl}"
        )
    return tuple(sorted(ltr))


def _validate_wli(pt: np.ndarray, wli: np.ndarray) -> None:
    if pt.dtype != np.uint8 or pt.ndim != 1:
        raise ValueError("pt_nose_data must be a one-dimensional uint8 array")
    if wli.dtype != np.uint8 or wli.shape != (pt.size, 2):
        raise ValueError("wli_nose_data must be uint8 with shape [len(pt), 2]")
    if pt.size and int(pt.max()) > 28:
        raise ValueError("NOSE plaintext contains a value outside 0..28")
    if not len(wli):
        return
    positions = wli[:, 0].astype(np.int16)
    lengths = wli[:, 1].astype(np.int16)
    if positions[0] != 0 or np.any(lengths <= 0) or np.any(positions >= lengths):
        raise ValueError("WLI contains an invalid position or word length")
    continuing = positions[1:] != 0
    if np.any(positions[1:][continuing] != positions[:-1][continuing] + 1):
        raise ValueError("WLI positions are not contiguous within a word")
    if np.any(lengths[1:][continuing] != lengths[:-1][continuing]):
        raise ValueError("WLI word length changes within a word")
    boundaries = ~continuing
    if np.any(positions[:-1][boundaries] + 1 != lengths[:-1][boundaries]):
        raise ValueError("WLI word ends are inconsistent")
    if positions[-1] + 1 != lengths[-1]:
        raise ValueError("WLI ends in a partial word")


def load_book(book: str, direction: Direction | str) -> BookCorpus:
    selected = ensure_direction(direction)
    resource = _books_root().joinpath(f"{book}_{selected.value}.npz")
    if not resource.is_file():
        raise FileNotFoundError(f"No packaged {selected.value} corpus for book {book!r}")
    with resource.open("rb") as handle, np.load(handle, allow_pickle=False) as data:
        pt = np.asarray(data["pt_nose_data"], dtype=np.uint8).reshape(-1).copy()
        raw_wli = np.asarray(data["wli_nose_data"], dtype=np.uint8)
        if raw_wli.size != pt.size * 2:
            raise ValueError("plaintext and flattened WLI lengths disagree")
        wli = raw_wli.reshape(-1, 2).copy()
    _validate_wli(pt, wli)

    metadata_resource = _books_root().joinpath(f"{book}.json")
    metadata = json.loads(metadata_resource.read_text(encoding="utf-8"))
    if str(metadata.get("book_id")) != book:
        raise ValueError("book metadata identity mismatch")
    expected = int(metadata[f"{selected.value}_token_count"])
    if expected != len(pt):
        raise ValueError("book metadata token count mismatch")
    return BookCorpus(book, selected, pt, wli, metadata)


def select_passage(
    corpus: BookCorpus,
    *,
    seed: int,
    target_runes: int,
    tolerance_runes: int,
) -> BookPassage:
    if int(target_runes) <= 0:
        raise ValueError("target_runes must be positive")
    if int(tolerance_runes) < 0:
        raise ValueError("tolerance_runes must be non-negative")
    starts = np.flatnonzero(corpus.wli[:, 0] == 0)
    lengths = corpus.wli[starts, 1].astype(np.int64)
    if not len(starts):
        raise ValueError("book corpus contains no words")
    cumulative = np.concatenate(([0], np.cumsum(lengths)))
    viable = np.flatnonzero(cumulative[-1] - cumulative[:-1] >= target_runes - tolerance_runes)
    if not len(viable):
        raise ValueError("book corpus is too short for requested passage")
    rng = np.random.default_rng(int(seed))
    start_word = int(rng.choice(viable))
    totals = cumulative[start_word + 1 :] - cumulative[start_word]
    word_count = int(np.argmin(np.abs(totals - int(target_runes))) + 1)
    rune_start = int(cumulative[start_word])
    rune_end = int(cumulative[start_word + word_count])
    pt = corpus.plaintext[rune_start:rune_end].copy()
    wli = corpus.wli[rune_start:rune_end].copy()
    if abs(len(pt) - int(target_runes)) > int(tolerance_runes):
        raise ValueError(
            f"no whole-word passage lies within {tolerance_runes} runes of "
            f"target {target_runes}; closest passage has {len(pt)} runes"
        )
    _validate_wli(pt, wli)
    return BookPassage(corpus.book, corpus.direction, start_word, word_count, pt, wli)


__all__ = ["BookCorpus", "BookPassage", "available_books", "load_book", "select_passage"]
