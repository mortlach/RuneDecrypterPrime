from __future__ import annotations

from importlib import import_module
from typing import Dict, List, Sequence

import numpy as np

from rdp.core.types import Direction, ensure_direction

Wordlist = Dict[int, List[List[int]]]


def _load_hamming_extension():
    try:
        return import_module("rdp.scoring.hamming._hamming")
    except Exception:  # pragma: no cover - handled by the explicit runtime error
        return None


class HammingBackend:
    """
    Thin wrapper around the C++ Hamming implementation.

    - Accepts LTR and optional RTL dictionaries (word length -> list of rune-index words).
    - Computes per-word minimum Hamming distance and aggregates across the plaintext.
    - Optional length-based weights and max_hd short-circuit.
    """

    def __init__(
        self,
        wordlists_ltr: Wordlist | None,
        wordlists_rtl: Wordlist | None = None,
        *,
        max_hd: int | None = None,
        length_weights: Dict[int, float] | None = None,
    ) -> None:
        extension = _load_hamming_extension()
        if extension is None:
            raise ImportError("rdp.scoring.hamming._hamming is not built; run setup_hamming.py")

        self._hamming_ltr = self._build_backend(extension, wordlists_ltr) if wordlists_ltr else None
        self._hamming_rtl = self._build_backend(extension, wordlists_rtl) if wordlists_rtl else None
        self._max_hd = int(max_hd) if max_hd is not None else (2 ** 31 - 1)
        self._len_weights = {int(k): float(v) for k, v in (length_weights or {}).items()}

    @staticmethod
    def _build_backend(extension, wordlists: Wordlist | None):
        if not wordlists:
            return None
        h = extension.Hamming()
        for length, words in wordlists.items():
            norm = [list(map(int, w)) for w in words]
            if norm:
                h.update_all_words_index(int(length), norm)
        return h

    @staticmethod
    def _split_words(runes: Sequence[int], wli: Sequence[Sequence[int]]):
        runes_list = list(map(int, runes))
        wli_list = [list(map(int, row)) for row in wli]
        words: List[List[int]] = []
        word_wli: List[List[List[int]]] = []
        cur_r: List[int] = []
        cur_w: List[List[int]] = []

        for r, w in zip(runes_list, wli_list):
            pos = int(w[0])
            if pos == 0 and cur_r:
                words.append(cur_r)
                word_wli.append(cur_w)
                cur_r = [r]
                cur_w = [w]
            else:
                cur_r.append(r)
                cur_w.append(w)
        if cur_r:
            words.append(cur_r)
            word_wli.append(cur_w)
        return words, word_wli

    def _word_penalty(self, backend, runes_word: Sequence[int], wli_word: Sequence[Sequence[int]]) -> float:
        try:
            hd = backend.get_min_hamming_distance(runes_word, wli_word)
        except Exception:
            # If the length is unseen or any other backend issue occurs, fall back to full mismatch.
            hd = len(wli_word)
        weight = self._len_weights.get(len(wli_word), 1.0)
        return float(weight * hd)

    def _total_for_backend(self, backend, words, wlis) -> float:
        total = 0.0
        for r_word, w_word in zip(words, wlis):
            total += self._word_penalty(backend, r_word, w_word)
            if total > self._max_hd:
                break
        return total

    def total_min_hd_stats(
        self,
        runes: Sequence[int] | np.ndarray,
        wli: Sequence[Sequence[int]] | np.ndarray,
        *,
        direction: Direction | str = Direction.LTR,
        mode: str = "match",
    ) -> Dict[str, float]:
        """
        Return both total HD and average-per-word HD for scoring.
        """
        words, wlis = self._split_words(runes, wli)
        if not words:
            return {"total_hd": 0.0, "avg_hd_word": 0.0, "n_words": 0.0}

        dir_enum = ensure_direction(direction)
        totals: list[float] = []

        def _eval(backend):
            return self._total_for_backend(backend, words, wlis)

        if mode == "both" and self._hamming_ltr is not None and self._hamming_rtl is not None:
            totals.append(_eval(self._hamming_ltr))
            totals.append(_eval(self._hamming_rtl))
            total_hd = min(totals)
        elif dir_enum is Direction.RTL and self._hamming_rtl is not None:
            total_hd = _eval(self._hamming_rtl)
        elif self._hamming_ltr is not None:
            total_hd = _eval(self._hamming_ltr)
        elif self._hamming_rtl is not None:
            total_hd = _eval(self._hamming_rtl)
        else:
            total_hd = 0.0

        n_words = float(len(words))
        avg_hd = float(total_hd) / max(1.0, n_words)
        return {"total_hd": float(total_hd), "avg_hd_word": avg_hd, "n_words": n_words}

    def total_min_hd(
        self,
        runes: Sequence[int] | np.ndarray,
        wli: Sequence[Sequence[int]] | np.ndarray,
        *,
        direction: Direction | str = Direction.LTR,
        mode: str = "match",  # "match" -> follow direction; "both" -> min(ltr, rtl)
    ) -> float:
        return float(self.total_min_hd_stats(runes, wli, direction=direction, mode=mode)["total_hd"])
