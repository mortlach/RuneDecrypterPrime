from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from rune_decrypter_prime.scoring.word_ngrams.sqlite_model import (
    make_prefix_key,
    make_token_ngram_key,
)


def word_tokens_from_idx_and_wli(
    text_idx: Sequence[int],
    wli: Sequence[Sequence[int]],
) -> tuple[bytes, ...]:
    values = [int(v) for v in text_idx]
    marks = [[int(x) for x in pair] for pair in wli]
    if len(values) != len(marks):
        raise ValueError("text_idx and wli must have the same length")
    tokens: list[bytes] = []
    cur: list[int] = []
    for sym, pair in zip(values, marks):
        if len(pair) != 2:
            raise ValueError("wli entries must be [pos_in_word, word_len]")
        pos_in_word, word_len = int(pair[0]), int(pair[1])
        cur.append(int(sym))
        if pos_in_word == word_len - 1:
            tokens.append(bytes(cur))
            cur = []
    if cur:
        raise ValueError("wli ended with an incomplete word")
    return tuple(tokens)


def wli_pairs_from_flat_array(
    flat_wli: Sequence[int] | np.ndarray,
) -> tuple[tuple[int, int], ...]:
    raw = np.asarray(flat_wli, dtype=np.int64).reshape(-1)
    if raw.size % 2 != 0:
        raise ValueError("flat WLI array must have even length")
    pairs = raw.reshape(-1, 2)
    return tuple((int(pair[0]), int(pair[1])) for pair in pairs)


@dataclass(frozen=True)
class RuneTokenWordNgramMemoryModel:
    counts_by_n: Mapping[int, Mapping[bytes, int]]
    totals_by_prefix_len: Mapping[int, Mapping[bytes, int]]

    @classmethod
    def from_token_sequences(
        cls,
        sequences: Iterable[Sequence[bytes]],
        *,
        orders: Sequence[int] = (3, 4, 5),
    ) -> "RuneTokenWordNgramMemoryModel":
        counts: dict[int, dict[bytes, int]] = {int(n): {} for n in orders}
        totals: dict[int, dict[bytes, int]] = {int(n) - 1: {} for n in orders}
        for seq in sequences:
            tokens = [bytes(tok) for tok in seq if bytes(tok)]
            for n in orders:
                width = int(n)
                if width < 2:
                    raise ValueError("orders must be >= 2")
                for idx in range(0, len(tokens) - width + 1):
                    gram = tuple(tokens[idx : idx + width])
                    key = make_token_ngram_key(gram)
                    prefix = make_prefix_key(gram[:-1])
                    counts[width][key] = int(counts[width].get(key, 0) + 1)
                    totals[width - 1][prefix] = int(
                        totals[width - 1].get(prefix, 0) + 1
                    )
        return cls(counts_by_n=counts, totals_by_prefix_len=totals)

    @classmethod
    def from_wli_corpora(
        cls,
        corpora: Iterable[tuple[Sequence[int], Sequence[Sequence[int]]]],
        *,
        orders: Sequence[int] = (3, 4, 5),
    ) -> "RuneTokenWordNgramMemoryModel":
        sequences = [
            word_tokens_from_idx_and_wli(text_idx, wli) for text_idx, wli in corpora
        ]
        return cls.from_token_sequences(sequences, orders=orders)

    @classmethod
    def from_tokenized_npz_paths(
        cls,
        npz_paths: Iterable[Path],
        *,
        pt_key: str = "pt_nose_data",
        wli_key: str = "wli_nose_data",
        orders: Sequence[int] = (3, 4, 5),
    ) -> "RuneTokenWordNgramMemoryModel":
        sequences: list[tuple[bytes, ...]] = []
        for fp in npz_paths:
            path = Path(fp).expanduser().resolve()
            with np.load(path, allow_pickle=True) as data:
                text_idx = np.asarray(data[pt_key], dtype=np.uint8).reshape(-1)
                wli_pairs = wli_pairs_from_flat_array(
                    np.asarray(data[wli_key], dtype=np.uint8)
                )
            sequences.append(word_tokens_from_idx_and_wli(text_idx, wli_pairs))
        return cls.from_token_sequences(sequences, orders=orders)

    def get_ngram_count(self, n: int, key: bytes) -> int:
        return int(self.counts_by_n.get(int(n), {}).get(bytes(key), 0))

    def get_prefix_total(self, n_minus_1: int, prefix: bytes) -> int:
        return int(
            self.totals_by_prefix_len.get(int(n_minus_1), {}).get(bytes(prefix), 0)
        )


__all__ = [
    "RuneTokenWordNgramMemoryModel",
    "wli_pairs_from_flat_array",
    "word_tokens_from_idx_and_wli",
]
