# ============================================================
# File: rune_decrypter_prime/ui/normalize.py
# Purpose: Normalize user text into ndarray[uint8] indices (0..28),
#          build WLI, and render helpers for tutorials/UI.
#
# Representation conventions (stable contract)
# --------------------------------------------
# 1) Canonical crypto inputs/outputs (preferred):
#    • Rune string (29-letter runic alphabet): "ᚦᛖᚱᛖ ..."
#    • Indices: List[int] / np.ndarray[np.uint8], values in [0..28]
#
# 2) Convenience input (accepted but converted before solve):
#    • English (26 letters) -> convert word-by-word using
#      Runeglish.translate_to_gematria (Latin->runes), then map runes->indices.
#
# 3) Display-only (NEVER used for crypto):
#    • Latin-canon string with digraphs: "TH", "(I)NG", "EO", ...
#      Use Runeglish.to_rune(indices, wli) to render this for humans.
#
# WLI policy:
#  • If input is a string (runes or English), WLI is derived from spaces
#    (per-word lengths).
#  • If input is indices, default WLI is a single word of length L.
#  • UI returns WLI as a plain Python list[list[int]] to avoid NumPy
#    truthiness pitfalls in downstream code.
# ============================================================

from __future__ import annotations
from typing import Union, Sequence, List, Optional
import numpy as np
from rune_decrypter_prime.utils.runeglish import Runeglish

from rune_decrypter_prime.utils.runeglish import Runeglish  # preferred path
# ----------------------------- helpers -----------------------------
#todo multiple copies use RUneglish
def _as_uint8_1d(xs: Sequence[int]) -> np.ndarray:
    return np.asarray(list(xs), dtype=np.uint8).reshape(-1)
#todo multiple copies use RUneglish
def _string_has_runes(s: str) -> bool:
    if Runeglish is None:
        return False
    runes = set(getattr(Runeglish, "runes", []))
    return any(ch in runes for ch in s)
#todo multiple copies use RUneglish
def _rune_word_to_indices(rune_word: str) -> List[int]:
    """Map a rune-character word (no spaces) -> indices via rune2position."""
    idx: List[int] = []
    for ch in rune_word:
        pos = Runeglish.rune_to_pos(ch)  # type: ignore[union-attr]
        if not isinstance(pos, int):
            raise TypeError(f"Unknown rune character '{ch}'.")
        idx.append(int(pos))
    return idx

import unicodedata

def _english_word_to_runes(word: str) -> str:
    """
    Normalize an input token to plain A–Z before rune translation.

    Rules:
      - Case-insensitive (folded to upper).
      - Non-ASCII letters, digits, punctuation, whitespace, emoji → removed.
      - Accented Latin letters are stripped of diacritics; characters outside A–Z are dropped.
      - If nothing remains after filtering, returns "".

    This guarantees only [A–Z] reaches Runeglish.translate_to_gematria.
    """
    if not isinstance(word, str) or not word:
        return ""

    # Compatibility fold + strip combining marks (é → e, ñ → n, etc.).
    # Note: ligatures and some special letters that don't map to A–Z are dropped by the A–Z filter.
    s = unicodedata.normalize("NFKD", word).upper()
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    # Keep strictly A–Z.
    ascii_letters = "".join(ch for ch in s if "A" <= ch <= "Z")

    if not ascii_letters:
        return ""

    try:
        # translate_to_gematria already handles digraphs on clean A–Z input.
        return Runeglish.translate_to_gematria(ascii_letters)  # type: ignore[union-attr]
    except Exception:
        # Bulletproof: never propagate translator failures upstream.
        return ""


def _wli_from_rune_words(words_rune: List[str]) -> List[List[int]]:
    """WLI rows [i, L] for each rune in each word (word lengths in runes)."""
    out: List[List[int]] = []
    for rw in words_rune:
        L = len(rw)
        for i in range(L):
            out.append([i, L])
    return out

def runes_from_indices(idx: Sequence[int], wli: Optional[Sequence[Sequence[int]]] = None) -> str:
    """
    Render rune characters from indices (grouped by WLI).
    This is NOT the Latin-canon. For Latin-canon, use Runeglish.to_rune(indices, wli).
    """
    idx = list(map(int, idx))
    if Runeglish is None:
        return ""
    if wli is None:
        # Single-word render
        return "".join(Runeglish.pos_to_rune(i) for i in idx)  # type: ignore[union-attr]

    out_words: List[str] = []
    cur: List[str] = []
    for i, sym in enumerate(idx):
        cur.append(Runeglish.pos_to_rune(sym))  # type: ignore[union-attr]
        if wli[i][0] == wli[i][1] - 1:
            out_words.append("".join(cur))
            cur = []
    if cur:
        out_words.append("".join(cur))
    return " ".join(out_words)


# ------------------------- public API (stable) -------------------------

# rune_decrypter_prime/ui/normalize.py

from typing import Union, Sequence, List, Tuple, Optional
import numpy as np
from rune_decrypter_prime.utils.runeglish import Runeglish


# def normalize_ciphertext(
#     text: Union[str, np.ndarray, list[int], tuple[int, ...]],
#     wli_data: Optional[Sequence[Sequence[int]]] = None,
# ) -> Tuple[np.ndarray, List[List[int]]]:
#     """
#     Convert user ciphertext input into (indices, WLI).
#
#     Accepted inputs
#     ---------------
#     • Rune string (29 alphabet, spaces optional)
#     • English string (26 letters; converted word-by-word to runes)
#     • Sequence of ints (already rune indices 0..28)
#
#     WLI rules
#     ---------
#     • If input is indices and caller gives `wli_data`, we trust it.
#     • If input is indices and no `wli_data`, default to a single-word WLI.
#     • If input is string, WLI inferred from spaces after conversion.
#     """
#
#     # Case: np.ndarray of ints
#     if isinstance(text, np.ndarray):
#         ct = text.astype(np.uint8).reshape(-1)
#         if wli_data is not None:
#             wli = list(map(list, wli_data))
#         else:
#             wli = [[i, len(ct)] for i in range(len(ct))]
#         return ct, wli
#
#     # Case: list/tuple of ints
#     if isinstance(text, (list, tuple)) and all(isinstance(x, (int, np.integer)) for x in text):
#         ct = np.asarray(text, dtype=np.uint8).reshape(-1)
#         if wli_data is not None:
#             wli = list(map(list, wli_data))
#         else:
#             wli = [[i, len(ct)] for i in range(len(ct))]
#         return ct, wli
#
#     # Case: string
#     if isinstance(text, str):
#         words = [w for w in text.split() if w]
#
#         # Rune string
#         runeset = set(getattr(Runeglish, "runes", []))
#         if any(ch in runeset for ch in text):
#             ct: List[int] = []
#             for w in words:
#                 for ch in w:
#                     pos = Runeglish.rune_to_pos(ch)
#                     # todo meh Runeglish.rune_to_pos has two rturn types
#                     if not isinstance(pos[0], int):
#                         raise ValueError(f"Unknown rune character: {ch}")
#                     ct.append(pos)
#             wli = _wli_from_rune_words(words)
#             return np.asarray(ct, dtype=np.uint8), wli
#
#         # English string → rune string → indices
#         rune_words = [Runeglish.translate_to_gematria(w.upper()) for w in words]
#         ct: List[int] = []
#         for rw in rune_words:
#             for ch in rw:
#                 pos = Runeglish.rune_to_pos(ch)
#                 ct.append(int(pos))
#         wli = _wli_from_rune_words(rune_words)
#         return np.asarray(ct, dtype=np.uint8), wli
#
#     raise TypeError(f"Unsupported ciphertext type: {type(text)}")

def normalize_ciphertext(
    text: Union[str, np.ndarray, list[int], tuple[int, ...]],
    wli_data: Optional[Sequence[Sequence[int]]] = None,
) -> Tuple[np.ndarray, List[List[int]]]:
    """
    Convert user ciphertext input into (indices, WLI).

    Accepted inputs
    ---------------
    • Rune string (29 alphabet, spaces optional)
    • English string (A–Z; converted word-by-word to runes)
    • Sequence of ints (already rune indices 0..28)

    WLI rules
    ---------
    • If input is indices and caller gives `wli_data`, we trust it.
    • If input is indices and no `wli_data`, default to a single-word WLI.
    • If input is string, WLI is inferred from spaces after conversion.
    """
    # 0) ndarray of ints
    if isinstance(text, np.ndarray):
        ct = text.astype(np.uint8).reshape(-1)
        if wli_data is not None:
            wli = [list(p) for p in wli_data]
        else:
            L = int(ct.size)
            wli = [[i, L] for i in range(L)]
        return ct, wli

    # 1) list/tuple of ints
    if isinstance(text, (list, tuple)) and all(isinstance(x, (int, np.integer)) for x in text):
        ct = np.asarray(text, dtype=np.uint8).reshape(-1)
        if wli_data is not None:
            wli = [list(p) for p in wli_data]
        else:
            L = int(ct.size)
            wli = [[i, L] for i in range(L)]
        return ct, wli

    # 2) string: either a rune string or English
    if isinstance(text, str):
        words = [w for w in text.split() if w]

        # Decide: rune string vs English
        runeset = set(getattr(Runeglish, "runes", []))
        is_rune_string = any(ch in runeset for ch in text)

        if is_rune_string:
            # Rune string → indices
            all_idx: list[int] = []
            for w in words:
                try:
                    # rune_to_pos returns list[int] for the WHOLE word
                    idx_word = Runeglish.rune_to_pos(w)  # list[int]
                except KeyError as e:
                    raise ValueError(f"Unknown rune character: {e.args[0]}") from None
                all_idx.extend(idx_word)
            wli = _wli_from_rune_words(words)
            return np.asarray(all_idx, dtype=np.uint8), wli

        # English string → rune string (per our transliteration) → indices
        rune_words: list[str] = [Runeglish.translate_to_gematria(w.upper()) for w in words]
        all_idx: list[int] = []
        for rw in rune_words:
            try:
                all_idx.extend(Runeglish.rune_to_pos(rw))  # list[int]
            except KeyError as e:
                raise ValueError(f"English→rune produced unknown rune: {e.args[0]}") from None
        wli = _wli_from_rune_words(rune_words)
        return np.asarray(all_idx, dtype=np.uint8), wli

    # 3) fallback
    raise TypeError(f"Unsupported ciphertext type: {type(text)}")


def _wli_from_rune_words(words_rune: List[str]) -> List[List[int]]:
    """WLI rows [i, L] for each rune in each word."""
    out: List[List[int]] = []
    for rw in words_rune:
        L = len(rw)
        out.extend([[i, L] for i in range(L)])
    return out

import unicodedata
import numpy as np
from typing import List, Union

# --- helpers ---

# def _string_has_runes(s: str) -> bool:
#     """True if any char is a rune glyph recognized by Runeglish."""
#     if Runeglish is None:
#         return False
#     return any(ch in Runeglish.runes for ch in s)  # type: ignore[union-attr]
#
# def _rune_word_to_indices(s: str) -> List[int]:
#     """Map any rune glyphs in s to positions; ignore non-rune chars."""
#     return [
#         Runeglish.rune_to_pos(ch)                   # type: ignore[union-attr]
#         for ch in s
#         if ch in Runeglish.runes                 # type: ignore[union-attr]
#     ]

# def _clean_english(word: str) -> str:
#     """Strip accents, keep only A–Z, uppercase."""
#     w = unicodedata.normalize("NFKD", word)
#     w = "".join(ch for ch in w if not unicodedata.combining(ch))
#     w = "".join(ch for ch in w.upper() if "A" <= ch <= "Z")
#     return w
#
# def _english_word_to_runes(word: str) -> str:
#     """English (A–Z only) → rune string via gematria."""
#     w = _clean_english(word)
#     if not w or Runeglish is None:
#         return ""
#     return Runeglish.translate_to_gematria(w)         # type: ignore[union-attr]
#
# def _as_uint8_1d(seq) -> np.ndarray:
#     return np.asarray(seq, dtype=np.uint8).reshape(-1)

# --- main ---

def to_indices(text: Union[str, np.ndarray, list, tuple]) -> np.ndarray:
    """
    Convert text to indices (uint8, shape=(L,)) in the canonical 29-alphabet.

    Accepts:
      • rune glyph string (preferred canonical; punctuation/space ignored)
      • English (A–Z) string (cleaned → translate_to_gematria → runes)
      • list[int]/tuple[int]/np.ndarray[int-like]

    NEVER pass Latin “display” digraph strings (TH, (I)NG, EO, ...).
    """
    if isinstance(text, np.ndarray):
        return text.astype(np.uint8, copy=False).reshape(-1)
    if isinstance(text, (list, tuple)):
        return np.asarray(text, dtype=np.uint8).reshape(-1)

    if isinstance(text, str):
        if Runeglish is None:
            raise TypeError("String → indices requires Runeglish; pass indices or enable Runeglish.")

        # Rune path: if any rune glyph is present, parse per character.
        if _string_has_runes(text):
            return _as_uint8_1d(Runeglish.rune_to_pos(text))
            #return _as_uint8_1d(_rune_word_to_indices(text))

        # English path: split into words, clean to A–Z, then convert each word.
        flat: List[int] = []
        for w in (w for w in text.split() if w):
            rword = _english_word_to_runes(w)
            if rword:
                flat.extend(Runeglish.rune_to_pos(rword))
                #flat.extend(_rune_word_to_indices(rword))
        return _as_uint8_1d(flat)

    raise TypeError(f"Unsupported text type: {type(text)}")


# def to_indices(text: Union[str, np.ndarray, list, tuple]) -> np.ndarray: """ Convert text into indices (dtype=uint8, shape=(L,)) in the canonical 29 alphabet. Accepts: • rune string (preferred canonical) • English (26 letters) string (converted via translate_to_gematria) • list[int]/tuple[int]/np.ndarray[int-like] NEVER pass Latin-canon display strings (TH, (I)NG, EO, ...) here. Raises TypeError for unsupported inputs or when Runeglish is unavailable for strings. """ # arrays pass-through if isinstance(text, np.ndarray): return text.astype(np.uint8, copy=False).reshape(-1) # list/tuple pass-through as ints if isinstance(text, (list, tuple)): return np.asarray(text, dtype=np.uint8).reshape(-1) # string paths if isinstance(text, str): if Runeglish is None: raise TypeError("String → indices requires Runeglish; pass indices or enable Runeglish.") words = [w for w in text.split() if w] # Rune string (canonical) if _string_has_runes(text): flat: List[int] = [] for w in words: flat.extend(_rune_word_to_indices(w)) return _as_uint8_1d(flat) # English (26 letters): convert each word to runes first flat2: List[int] = [] for w in words: rword = _english_word_to_runes(w) flat2.extend(_rune_word_to_indices(rword)) return _as_uint8_1d(flat2) raise TypeError(f"Unsupported text type: {type(text)}")

def wli_from_text(text: str) -> List[List[int]]:
    """
    Build WLI (word-breaks) from a string:
      • Rune string → split on spaces; lengths measured in rune chars.
      • English string → convert each word to runes; lengths measured in rune chars.
    For indices inputs, use make_single_word_wli(L).
    """
    if Runeglish is None:
        arr = to_indices(text)
        return make_single_word_wli(int(arr.size))
    if _string_has_runes(text):
        words_rune = [w for w in text.split() if w]
    else:
        words_rune = [_english_word_to_runes(w) for w in text.split() if w]
    return _wli_from_rune_words(words_rune)


def make_single_word_wli(L: int) -> List[List[int]]:
    """Single-word WLI of length L: [[i, L] for i in 0..L-1]."""
    L = int(L)
    return [[i, L] for i in range(L)]
