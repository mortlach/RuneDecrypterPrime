# ============================================================
# rune_decrypter_prime/utils/runeglish.py
# Minimal “Runeglish” utilities for 29-rune mapping and WLI handling.
# Provides Latin↔Rune↔Position conversions and simple tokenisation.
# ============================================================

from __future__ import annotations
from typing import List, Sequence, Iterable
import re

from rdp.core.types import Direction, TextDirection, ensure_direction

class Runeglish:
    _BIGRAMS = {'TH', 'EO', 'NG', 'OE', 'AE', 'IA', 'IO', 'EA'}
    _TRIGRAM = 'ING'

    runes = [
        "ᚠ", "ᚢ", "ᚦ", "ᚩ", "ᚱ", "ᚳ", "ᚷ", "ᚹ", "ᚻ", "ᚾ", "ᛁ", "ᛂ", "ᛇ", "ᛈ", "ᛉ", "ᛋ", "ᛏ",
        "ᛒ", "ᛖ", "ᛗ", "ᛚ", "ᛝ", "ᛟ", "ᛞ", "ᚪ", "ᚫ", "ᚣ", "ᛡ", "ᛠ"
    ]
    positions = list(range(len(runes)))
    latin_canon = [
        "F", "U", "TH", "O", "R", "C", "G", "W", "H", "N", "I", "J", "EO", "P", "X", "S",
        "T", "B", "E", "M", "L", "(I)NG", "OE", "D", "A", "AE", "Y", "IO", "EA"
    ]

    # Rune ↔ Position
    rune2pos = {r: p for p, r in enumerate(runes)}
    rune2pos["ᛄ"] = rune2pos["ᛂ"]  # alias
    pos2rune = {p: r for p, r in enumerate(runes)}

    # Rune ↔ Latin
    rune2latin = {r: l for r, l in zip(runes, latin_canon)}
    rune2latin["ᛄ"] = rune2latin["ᛂ"]  # alias
    latin2rune = {l: r for l, r in zip(latin_canon, runes)}
    latin2pos = {l: p for p, l in enumerate(latin_canon)}
    pos2latin = {p: l for p, l in enumerate(latin_canon)}

    # Normalisation mappings
    latin2rune.update({
        'ING': latin2rune["(I)NG"],
        'NG':  latin2rune["(I)NG"],
        'Z':   latin2rune["S"],
        'K':   latin2rune["C"],
        'Q':   latin2rune["C"],
        'IA':  latin2rune["IO"],
        'V':   latin2rune["U"],
    })
    latin2pos.update({
        'ING': latin2pos["(I)NG"],
        'NG':  latin2pos["(I)NG"],
        'Z':   latin2pos["S"],
        'K':   latin2pos["C"],
        'Q':   latin2pos["C"],
        'IA':  latin2pos["IO"],
        'V':   latin2pos["U"],
    })

    @staticmethod
    def latin_to_rune(latin: str) -> str:
        """Map canonical Latin token → rune (fallback to input if unknown)."""
        return Runeglish.latin2rune.get(latin, latin)

    @staticmethod
    def latin_to_pos(latin: str) -> int:
        """Map canonical Latin token → position (fallback to input if unknown)."""
        return Runeglish.latin2pos.get(latin, latin)

    @staticmethod
    def rune_to_latin(rune: str) -> str:
        """Map rune → canonical Latin token (fallback to input if unknown)."""
        return Runeglish.rune2latin.get(rune, rune)

    @staticmethod
    def rune_to_latin(rune_or_runes: str) -> str:  # Note: later def overrides earlier (kept for back-compat)
        """
        Accepts a rune string (or any iterable of runes) and returns Latin tokens.
        Unknown runes are returned unchanged.
        """
        def _one(r: str) -> str:
            return Runeglish.rune2latin.get(r, r)
        if isinstance(rune_or_runes, Iterable) and not isinstance(rune_or_runes, (str, bytes)):
            return "".join(_one(p) for p in rune_or_runes)
        return _one(rune_or_runes)

    @staticmethod
    def rune_to_pos(runes: str) -> list[int]:
        """
        Convert a rune string into a list of positions.
        - "ᛞ"   -> [pos]
        - "ᛞᛁᛋ" -> [pos, pos, pos]
        """
        if not isinstance(runes, str):
            raise TypeError(f"rune_to_pos expects str, got {type(runes)}")
        return [Runeglish.rune2pos[ch] for ch in runes]

    @staticmethod
    def pos_to_rune(pos_or_positions) -> str:
        """
        Accepts an int (single position) OR an iterable of ints.
        - int  -> returns the single rune (str)
        - iterable[int] -> returns the concatenated rune string
        Unknown positions are rendered as their decimal string.
        """
        def _one(p: int) -> str:
            return Runeglish.pos2rune.get(int(p), str(int(p)))
        if isinstance(pos_or_positions, Iterable) and not isinstance(pos_or_positions, (str, bytes)):
            return "".join(_one(p) for p in pos_or_positions)
        return _one(pos_or_positions)

    @staticmethod
    def pos_to_latin(pos: int) -> str:
        """Map position → canonical Latin token."""
        return Runeglish.pos2latin.get(pos, pos)

    @staticmethod
    def translate_to_gematria(word: str) -> str:
        """
        Translate a Latin word into its rune string using the house rules:
        - Uppercase; QU→KW; apply normalisation (V→U, Z→S, K/Q→C, IA→IO, etc.).
        - Greedy tokenisation preferring 'ING', then allowed bigrams, else single letters.
        - Quotes are ignored.
        """
        word = word.upper().replace("QU", "KW").translate(str.maketrans({"Q": "K"}))
        res: list[str] = []
        i = 0
        while i < len(word):
            if word[i:i+3] == Runeglish._TRIGRAM:
                res.append(Runeglish._TRIGRAM); i += 3; continue
            if word[i:i+2] in Runeglish._BIGRAMS:
                res.append(word[i:i+2]); i += 2; continue
            if word[i] in {"'", '"'}:
                i += 1; continue
            res.append(word[i]); i += 1
        return ''.join([Runeglish.latin_to_rune(l) for l in res])

    @staticmethod
    def get_wli_data_str(runewords_string: str) -> List[List[int]]:
        """Compute WLI from a rune-words string (words separated by spaces)."""
        words = runewords_string.split(" ")
        return [[i, len(word)] for word in words for i, _ in enumerate(word)]

    @staticmethod
    def get_wli_data_list(runewords: List[str]) -> List[List[int]]:
        """Compute WLI from a list of rune words."""
        return [[i, len(word)] for word in runewords for i, _ in enumerate(word)]

    @staticmethod
    def to_rune_latin(
        pt: Sequence[int],
        wli: Sequence[Sequence[int]] | None,
        limit: int | None = None,
        *,
        direction: str | object = "ltr",
    ) -> str:
        """Render positions as Latin text, respecting WLI and encoding direction."""
        dir_value = getattr(direction, "value", direction)
        dir_text = str(dir_value).strip().lower()

        def _display_word(tokens: list[str]) -> str:
            if dir_text != "rtl" or wli is None:
                return ''.join(tokens)
            # Inverse of encode_english_to_runes(..., direction="rtl"):
            # encoded tokens are in display order, but multigraph boundaries were
            # chosen after reversing the source word.
            source_order = ''.join(tokens[::-1]).replace("(I)NG", "ING")
            return source_order[::-1]

        words, cur = [], []
        for i, sym in enumerate(pt):
            cur.append(Runeglish.pos_to_latin(sym))
            if wli is not None and wli[i][0] == wli[i][1] - 1:
                words.append(_display_word(cur)); cur = []
            if limit and len(' '.join(words)) >= limit:
                break
        if cur:
            words.append(_display_word(cur))
        return ' '.join(words)

    @staticmethod
    def to_rune(pt: Sequence[int], wli: Sequence[Sequence[int]], limit: int | None = None) -> str:
        """Render positions as runes, respecting WLI word breaks."""
        words, cur = [], []
        for i, sym in enumerate(pt):
            cur.append(Runeglish.pos_to_rune(sym))
            if wli is not None and wli[i][0] == wli[i][1] - 1:
                words.append(''.join(cur)); cur = []
            if limit and len(' '.join(words)) >= limit:
                break
        if cur:
            words.append(''.join(cur))
        return ' '.join(words)

    @staticmethod
    def size() -> int:
        return len(Runeglish.runes)

    @staticmethod
    def encode_english_to_runes(
        text: str,
        *,
        direction: Direction | TextDirection | str = Direction.LTR,
    ) -> tuple[list[int], list[list[int]], str]:
        """
        Canonical English → (indices, WLI, rune string).

        Rules
        -----
        • Punctuation: removed (word separators).
        • QU → KW, then class normalisation applies (V→U, Z→S, IA→IO, K/Q→C).
        • Greedy tokenisation: 'ING' trigram, then any of BIGRAMS, else single letter.
        • direction="rtl" reverses the token sequence *inside each word* before encoding.
        • Output WLI is a flat list of [pos_in_word, word_len] entries.
        """
        clean = (text
                 .replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
                 .replace("—", " ").replace("–", " "))
        words_raw = re.findall(r"[A-Za-z]+", clean)

        idx_out: list[int] = []
        wli_out: list[list[int]] = []
        rune_words: list[str] = []

        BIG = Runeglish._BIGRAMS
        TRI = Runeglish._TRIGRAM
        l2pos = Runeglish.latin_to_pos
        pos2r = Runeglish.pos_to_rune

        encoding_direction = ensure_direction(direction)

        for raw in words_raw:
            if encoding_direction is Direction.RTL:
                raw = raw[::-1]

            w = raw.upper().replace("QU", "KW")

            tokens: list[str] = []
            i = 0
            L = len(w)
            while i < L:
                if i + 3 <= L and w[i:i+3] == TRI:
                    tokens.append(TRI); i += 3; continue
                if i + 2 <= L and w[i:i+2] in BIG:
                    tokens.append(w[i:i+2]); i += 2; continue
                tokens.append(w[i]); i += 1

            if encoding_direction is Direction.RTL:
                tokens.reverse()

            word_idx: list[int] = []
            for t in tokens:
                pos = l2pos(t)
                if isinstance(pos, int):
                    word_idx.append(pos)
            if not word_idx:
                continue

            m = len(word_idx)
            wli_out.extend([[j, m] for j in range(m)])

            idx_out.extend(word_idx)
            rune_word = "".join(pos2r(p) for p in word_idx)
            rune_words.append(rune_word)

        rune_str = " ".join(rune_words)
        return idx_out, wli_out, rune_str

# TODO: There are two `rune_to_latin` defs; the latter overrides the former.
#       Keep as-is for back-compat; consider consolidating in a future major version.
