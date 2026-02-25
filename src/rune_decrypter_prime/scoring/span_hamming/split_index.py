from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple


def partition_slices(word_length: int, n_parts: int) -> Tuple[Tuple[int, int], ...]:
    if word_length < 1:
        raise ValueError("word_length must be >= 1")
    if n_parts < 1:
        raise ValueError("n_parts must be >= 1")
    if n_parts > word_length:
        raise ValueError("n_parts cannot exceed word_length")

    base = word_length // n_parts
    remainder = word_length % n_parts
    out = []
    cursor = 0
    for part_id in range(n_parts):
        width = base + (1 if part_id < remainder else 0)
        start = cursor
        end = cursor + width
        out.append((start, end))
        cursor = end
    return tuple(out)


@dataclass(frozen=True)
class LengthSplitIndex:
    length: int
    max_hd: int
    words: Tuple[Tuple[int, ...], ...]
    n_parts: int
    part_slices: Tuple[Tuple[int, int], ...]
    buckets: Dict[Tuple[int, Tuple[int, ...]], Tuple[int, ...]]

    @classmethod
    def build(
        cls,
        length: int,
        words: Iterable[Sequence[int]],
        *,
        max_hd: int,
    ) -> "LengthSplitIndex":
        sorted_words = sorted({tuple(int(x) for x in word) for word in words})
        if not sorted_words:
            return cls(
                length=int(length),
                max_hd=int(max_hd),
                words=tuple(),
                n_parts=0,
                part_slices=tuple(),
                buckets={},
            )

        if any(len(word) != length for word in sorted_words):
            raise ValueError("all words must match the declared length")

        n_parts = min(int(length), int(max_hd) + 1)
        part_slices = partition_slices(int(length), n_parts)
        mutable: Dict[Tuple[int, Tuple[int, ...]], list[int]] = {}

        for word_id, word in enumerate(sorted_words):
            for part_id, (start, end) in enumerate(part_slices):
                key = (part_id, word[start:end])
                mutable.setdefault(key, []).append(word_id)

        buckets: Dict[Tuple[int, Tuple[int, ...]], Tuple[int, ...]] = {
            key: tuple(ids) for key, ids in mutable.items()
        }
        return cls(
            length=int(length),
            max_hd=int(max_hd),
            words=tuple(sorted_words),
            n_parts=int(n_parts),
            part_slices=part_slices,
            buckets=buckets,
        )

    def candidate_word_ids(self, window: Sequence[int]) -> Tuple[int, ...]:
        if self.n_parts == 0:
            return tuple()
        if len(window) != self.length:
            raise ValueError("window length does not match index length")

        window_tuple = tuple(int(x) for x in window)
        candidate_ids: set[int] = set()
        for part_id, (start, end) in enumerate(self.part_slices):
            key = (part_id, window_tuple[start:end])
            ids = self.buckets.get(key)
            if ids:
                candidate_ids.update(ids)
        return tuple(sorted(candidate_ids))

