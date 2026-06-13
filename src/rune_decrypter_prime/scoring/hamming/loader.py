from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from rune_decrypter_prime.data.asset_paths import resolve_assets_path, to_repo_relative
from rune_decrypter_prime.utils.runeglish import Runeglish


Wordlist = Dict[int, List[List[int]]]

_DEFAULT_HAMMING_ASSETS_REL = Path("hamming_raw_1g")


def default_hamming_dir() -> Path:
    """
    Resolve the default hamming raw-1g asset directory.

    This is intentionally a function, not an import-time constant, so installed
    wheels can import the hamming package/native extension without requiring a
    repository checkout or asset manifest next to site-packages.
    """
    return resolve_assets_path(str(_DEFAULT_HAMMING_ASSETS_REL), start=Path(__file__))


def _normalize_dir(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _freeze_wordlists(wordlists: Wordlist | None) -> Optional[Tuple[Tuple[int, Tuple[Tuple[int, ...], ...]], ...]]:
    if not wordlists:
        return None
    frozen: List[Tuple[int, Tuple[Tuple[int, ...], ...]]] = []
    for length, words in sorted(wordlists.items()):
        frozen.append((int(length), tuple(tuple(map(int, w)) for w in words)))
    return tuple(frozen)


def _thaw_wordlists(frozen: Optional[Tuple[Tuple[int, Tuple[Tuple[int, ...], ...]], ...]]) -> Wordlist:
    out: Wordlist = {}
    if not frozen:
        return out
    for length, words in frozen:
        out[int(length)] = [list(w) for w in words]
    return out


def _parse_row(row: Sequence[str], *, require_selected: bool) -> Tuple[str, List[int]] | None:
    if len(row) < 5:
        return None
    english = (row[0] or "").strip()
    selected_flag = (row[2] or "").strip()
    if require_selected and selected_flag != "1":
        return None
    rune_string = row[3]
    try:
        rune_indices = Runeglish.rune_to_pos(rune_string)
    except Exception:
        return None
    return english, rune_indices


@lru_cache(maxsize=4)
def _load_cached(wordlist_dir: str, build_rtl: bool, require_selected: bool) -> Tuple[
    Optional[Tuple[Tuple[int, Tuple[Tuple[int, ...], ...]], ...]],
    Optional[Tuple[Tuple[int, Tuple[Tuple[int, ...], ...]], ...]],
]:
    base = _normalize_dir(wordlist_dir)
    files = sorted(base.glob("raw1grams_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No raw1grams_*.csv files found under {to_repo_relative(base, start=Path(__file__))}"
        )

    wordlists_ltr: Wordlist = {}
    wordlists_rtl: Wordlist = {} if build_rtl else {}

    for fp in files:
        with fp.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            for row in reader:
                parsed = _parse_row(row, require_selected=require_selected)
                if parsed is None:
                    continue
                english, rune_indices = parsed
                ln = len(rune_indices)
                if ln == 0:
                    continue
                wordlists_ltr.setdefault(ln, []).append(rune_indices)

                if build_rtl:
                    try:
                        rtl_idx, _, _ = Runeglish.encode_english_to_runes(english, direction="rtl")
                        rtl_list = list(map(int, rtl_idx))
                        if rtl_list:
                            wordlists_rtl.setdefault(len(rtl_list), []).append(rtl_list)
                    except Exception:
                        # Fallback: reverse the LTR indices to keep coverage.
                        wordlists_rtl.setdefault(ln, []).append(list(reversed(rune_indices)))

    return _freeze_wordlists(wordlists_ltr), _freeze_wordlists(wordlists_rtl if build_rtl else None)


def load_raw1grams_wordlists(
    wordlist_dir: str | Path | None = None,
    *,
    build_rtl: bool = False,
    require_selected: bool = True,
) -> Tuple[Wordlist, Wordlist | None]:
    """
    Load the Rune wordlists from raw1grams_XX.csv files.

    Returns (ltr_wordlists, rtl_wordlists | None), where each dict maps
    word length -> list of rune-index words.

    If wordlist_dir is None, defaults to `assets/hamming_raw_1g/`.
    """
    base = wordlist_dir if wordlist_dir is not None else default_hamming_dir()
    frozen_ltr, frozen_rtl = _load_cached(str(_normalize_dir(base)), build_rtl, require_selected)
    return _thaw_wordlists(frozen_ltr), _thaw_wordlists(frozen_rtl)
