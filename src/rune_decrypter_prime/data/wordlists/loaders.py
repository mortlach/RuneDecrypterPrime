from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, Sequence

from rune_decrypter_prime.api.word_crib_config import WordCribConfig
from rune_decrypter_prime.core.types import Direction, ensure_direction
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.scoring.hamming.loader import load_raw1grams_wordlists

_DATA_DIR = Path(__file__).resolve().parent


def _normalize_direction(direction: Direction | str) -> Direction:
    if isinstance(direction, Direction):
        return direction
    return ensure_direction(direction)


def _slug_for(direction: Direction | str) -> str:
    d = _normalize_direction(direction)
    return d.value.lower()


def load_short_word_csv(
    *,
    length: int,
    direction: Direction | str,
    base_dir: Path | None = None,
) -> Dict[str, float]:
    """
    Load a single short-word CSV file (latin_word, rune_word, rune_indices, weight)
    and return a {latin_word: weight} dictionary.
    """
    path = (base_dir or _DATA_DIR) / f"short_words_{_slug_for(direction)}_len{int(length)}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Short-word list not found: {path}")
    out: Dict[str, float] = {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            latin = (row.get("latin_word") or "").strip().upper()
            if not latin:
                continue
            indices = tuple(int(tok) for tok in (row.get("rune_indices") or "").split())
            if indices:
                encoded, _, _ = Runeglish.encode_english_to_runes(latin, direction=_normalize_direction(direction).value)
                if tuple(encoded) != indices:
                    raise ValueError(
                        f"CSV entry for '{latin}' does not match encoded indices {encoded} vs {indices}"
                    )
            weight = float(row.get("weight", 0) or 0)
            out[latin] = out.get(latin, 0.0) + weight
    return out


def load_short_word_dictionary(
    *,
    lengths: Sequence[int] = (1, 2, 3),
    direction: Direction | str,
    base_dir: Path | None = None,
) -> Dict[int, Dict[str, float]]:
    """
    Load multiple length tables for a given direction.
    """
    tables: Dict[int, Dict[str, float]] = {}
    for length in lengths:
        tables[int(length)] = load_short_word_csv(length=int(length), direction=direction, base_dir=base_dir)
    return tables


def load_word_crib_config_from_csv(
    *,
    direction: Direction | str,
    lengths: Sequence[int] = (1, 2, 3),
    base_dir: Path | None = None,
    max_short_length: int | None = None,
) -> WordCribConfig:
    """
    Convenience helper: load the short word lists and create an enabled WordCribConfig.
    """
    tables = load_short_word_dictionary(lengths=lengths, direction=direction, base_dir=base_dir)
    if max_short_length is None:
        max_short_length = max(tables.keys(), default=0)
    return WordCribConfig(
        enabled=True,
        max_short_length=int(max_short_length),
        short_word_dict=tables,
        per_word_cribs={},
    )


def _wordlist_to_short_dict(wordlists: Dict[int, Sequence[Sequence[int]]], *, direction: Direction) -> Dict[int, Dict[str, float]]:
    """
    Convert raw1grams-style wordlists (len -> [[rune_idx...]]) into a
    short_word_dict mapping len -> {latin_word: weight}.
    We assign weight=1.0 per entry to avoid overweighting by raw counts.
    """
    tables: Dict[int, Dict[str, float]] = {}
    for length, words in (wordlists or {}).items():
        out: Dict[str, float] = {}
        for word in words:
            latin = "".join(Runeglish.pos_to_latin(int(p)) for p in word)
            if not latin:
                continue
            # Ensure the Latin form round-trips to the same rune length for this direction.
            encoded, _, _ = Runeglish.encode_english_to_runes(latin, direction=direction.value)
            if len(encoded) != len(word):
                continue
            out[latin] = out.get(latin, 0.0) + 1.0
        if out:
            tables[int(length)] = out
    return tables


def load_word_crib_config_from_raw1grams(
    *,
    direction: Direction | str,
    lengths: Sequence[int] = (1, 2, 3),
    base_dir: Path | None = None,
    max_short_length: int | None = None,
) -> WordCribConfig:
    """
    Build a WordCribConfig directly from the raw1grams wordlists used by the
    Hamming backend, ensuring CSP and Hamming share the same lexical source.
    """
    dir_norm = _normalize_direction(direction)
    # Build both LTR/RTL so we can pick the requested direction reliably.
    wl_ltr, wl_rtl = load_raw1grams_wordlists(base_dir, build_rtl=True)
    wl = wl_rtl if dir_norm is Direction.RTL else wl_ltr
    filtered = {int(k): v for k, v in wl.items() if int(k) in set(int(x) for x in lengths)}
    tables = _wordlist_to_short_dict(filtered, direction=dir_norm)
    if max_short_length is None:
        max_short_length = max(tables.keys(), default=0)
    return WordCribConfig(
        enabled=True,
        max_short_length=int(max_short_length),
        short_word_dict=tables,
        per_word_cribs={},
    )
