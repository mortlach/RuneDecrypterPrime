from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Mapping, Sequence

import numpy as np


ALPHABET_SIZE = 29
LENGTH_BUCKETS = ((8, 9, "8-9"), (10, 11, "10-11"), (12, 14, "12-14"), (15, 17, "15-17"), (18, None, "18+"))


@dataclass(frozen=True)
class SortedBlockIndex:
    blocks: tuple[tuple[int, int], ...]
    sorted_keys: tuple[np.ndarray, ...]
    sorted_row_indexes: tuple[np.ndarray, ...]

    @property
    def allocated_bytes(self) -> int:
        return sum(array.nbytes for array in self.sorted_keys + self.sorted_row_indexes)


def length_bucket(length: int) -> str:
    for lower, upper, label in LENGTH_BUCKETS:
        if length >= lower and (upper is None or length <= upper):
            return label
    raise ValueError(f"phrase length is below N3C study minimum: {length}")


def split_three_blocks(length: int) -> tuple[tuple[int, int], ...]:
    if length < 3:
        raise ValueError("partition filter requires at least three tokens")
    q, r = divmod(length, 3)
    sizes = [q + (1 if index < r else 0) for index in range(3)]
    out = []
    start = 0
    for size in sizes:
        out.append((start, start + size))
        start += size
    return tuple(out)


def exact_word_structured_match(
    window: Sequence[int],
    phrase: Sequence[int],
    word_lengths: Sequence[int],
    *,
    max_total_hd: int = 2,
    max_word_hd: int = 1,
) -> tuple[int, ...] | None:
    if len(window) != len(phrase) or sum(word_lengths) != len(phrase):
        return None
    offset = 0
    word_hds: list[int] = []
    for word_length in word_lengths:
        end = offset + int(word_length)
        distance = sum(left != right for left, right in zip(window[offset:end], phrase[offset:end]))
        if distance > max_word_hd:
            return None
        word_hds.append(distance)
        offset = end
    return tuple(word_hds) if sum(word_hds) <= max_total_hd else None


def brute_force_hits(
    candidate_tokens: Sequence[int],
    phrase_rows: np.ndarray,
    word_lengths: Sequence[int],
    *,
    max_total_hd: int = 2,
    max_word_hd: int = 1,
) -> set[tuple[int, int]]:
    phrase_length = phrase_rows.shape[1]
    hits: set[tuple[int, int]] = set()
    for start in range(len(candidate_tokens) - phrase_length + 1):
        window = candidate_tokens[start:start + phrase_length]
        for phrase_index, phrase in enumerate(phrase_rows):
            if exact_word_structured_match(
                window, phrase.tolist(), word_lengths, max_total_hd=max_total_hd, max_word_hd=max_word_hd
            ) is not None:
                hits.add((start, phrase_index))
    return hits


def generated_neighbour_keys(
    window: Sequence[int],
    word_lengths: Sequence[int],
    *,
    alphabet_size: int = ALPHABET_SIZE,
) -> set[bytes]:
    if sum(word_lengths) != len(window):
        raise ValueError("word lengths do not cover candidate window")
    base = tuple(int(token) for token in window)
    keys = {bytes(base)}
    word_by_position: list[int] = []
    for word_index, word_length in enumerate(word_lengths):
        word_by_position.extend([word_index] * int(word_length))
    alternatives = {
        position: tuple(token for token in range(alphabet_size) if token != base[position])
        for position in range(len(base))
    }
    for position, values in alternatives.items():
        for value in values:
            changed = list(base)
            changed[position] = value
            keys.add(bytes(changed))
    for left, right in combinations(range(len(base)), 2):
        if word_by_position[left] == word_by_position[right]:
            continue
        for left_value in alternatives[left]:
            for right_value in alternatives[right]:
                changed = list(base)
                changed[left] = left_value
                changed[right] = right_value
                keys.add(bytes(changed))
    return keys


def candidate_keyed_hits(
    candidate_tokens: Sequence[int],
    phrase_rows: np.ndarray,
    word_lengths: Sequence[int],
) -> tuple[set[tuple[int, int]], int, int]:
    lookup: dict[bytes, list[int]] = defaultdict(list)
    for phrase_index, phrase in enumerate(phrase_rows):
        lookup[bytes(phrase.tolist())].append(phrase_index)
    phrase_length = phrase_rows.shape[1]
    hits: set[tuple[int, int]] = set()
    generated_count = 0
    unique_keys: set[bytes] = set()
    for start in range(len(candidate_tokens) - phrase_length + 1):
        window = candidate_tokens[start:start + phrase_length]
        keys = generated_neighbour_keys(window, word_lengths)
        generated_count += len(keys)
        unique_keys.update(keys)
        for key in keys:
            for phrase_index in lookup.get(key, ()):
                if exact_word_structured_match(window, phrase_rows[phrase_index].tolist(), word_lengths) is not None:
                    hits.add((start, phrase_index))
    return hits, generated_count, len(unique_keys)


def partition_filter_hits(
    candidate_tokens: Sequence[int],
    phrase_rows: np.ndarray,
    word_lengths: Sequence[int],
    *,
    max_total_hd: int = 2,
    max_word_hd: int = 1,
    allowed_start_ranges: Sequence[tuple[int, int]] | None = None,
) -> tuple[set[tuple[int, int]], int]:
    phrase_length = phrase_rows.shape[1]
    blocks = split_three_blocks(phrase_length)
    indexes: list[dict[bytes, list[int]]] = [defaultdict(list) for _ in blocks]
    for phrase_index, phrase in enumerate(phrase_rows):
        for block_index, (start, end) in enumerate(blocks):
            indexes[block_index][bytes(phrase[start:end].tolist())].append(phrase_index)
    hits: set[tuple[int, int]] = set()
    proposed_count = 0
    for start in range(len(candidate_tokens) - phrase_length + 1):
        if allowed_start_ranges is not None and not any(lower <= start < upper for lower, upper in allowed_start_ranges):
            continue
        window = candidate_tokens[start:start + phrase_length]
        proposed: set[int] = set()
        for block_index, (block_start, block_end) in enumerate(blocks):
            proposed.update(indexes[block_index].get(bytes(window[block_start:block_end]), ()))
        proposed_count += len(proposed)
        for phrase_index in proposed:
            if exact_word_structured_match(
                window, phrase_rows[phrase_index].tolist(), word_lengths,
                max_total_hd=max_total_hd, max_word_hd=max_word_hd,
            ) is not None:
                hits.add((start, phrase_index))
    return hits, proposed_count


def build_sorted_block_index(phrase_rows: np.ndarray) -> SortedBlockIndex:
    if phrase_rows.ndim != 2 or phrase_rows.shape[0] == 0:
        raise ValueError("phrase rows must be a non-empty two-dimensional array")
    blocks = split_three_blocks(int(phrase_rows.shape[1]))
    keys: list[np.ndarray] = []
    row_indexes: list[np.ndarray] = []
    for start, end in blocks:
        block_rows = np.ascontiguousarray(phrase_rows[:, start:end])
        key_dtype = np.dtype((np.void, block_rows.dtype.itemsize * block_rows.shape[1]))
        block_keys = block_rows.view(key_dtype).reshape(-1)
        order = np.argsort(block_keys, kind="stable")
        keys.append(block_keys[order])
        row_indexes.append(order.astype(np.int64, copy=False))
    return SortedBlockIndex(blocks=blocks, sorted_keys=tuple(keys), sorted_row_indexes=tuple(row_indexes))


def vectorized_word_structured_match_indexes(
    window: Sequence[int],
    phrase_rows: np.ndarray,
    phrase_indexes: Sequence[int],
    word_lengths: Sequence[int],
    *,
    max_total_hd: int = 2,
    max_word_hd: int = 1,
) -> np.ndarray:
    indexes = np.asarray(tuple(phrase_indexes), dtype=np.int64)
    if indexes.size == 0:
        return indexes
    window_array = np.asarray(window, dtype=phrase_rows.dtype)
    mismatches = phrase_rows[indexes] != window_array
    total_hds = mismatches.sum(axis=1)
    allowed = total_hds <= max_total_hd
    offset = 0
    for word_length in word_lengths:
        end = offset + int(word_length)
        allowed &= mismatches[:, offset:end].sum(axis=1) <= max_word_hd
        offset = end
    return indexes[allowed]


def vectorized_word_structured_match_details(
    window: Sequence[int],
    phrase_rows: np.ndarray,
    phrase_indexes: Sequence[int],
    word_lengths: Sequence[int],
    *,
    max_total_hd: int = 2,
    max_word_hd: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    indexes = np.asarray(tuple(phrase_indexes), dtype=np.int64)
    if indexes.size == 0:
        return indexes, np.zeros((0, len(tuple(word_lengths))), dtype=np.uint8)
    word_lengths_tuple = tuple(int(value) for value in word_lengths)
    window_array = np.asarray(window, dtype=phrase_rows.dtype)
    mismatches = phrase_rows[indexes] != window_array
    word_hds = []
    offset = 0
    for word_length in word_lengths_tuple:
        end = offset + word_length
        word_hds.append(mismatches[:, offset:end].sum(axis=1))
        offset = end
    word_hd_array = np.stack(word_hds, axis=1).astype(np.uint8, copy=False)
    total_hds = word_hd_array.sum(axis=1)
    allowed = (total_hds <= max_total_hd) & (word_hd_array.max(axis=1) <= max_word_hd)
    return indexes[allowed], word_hd_array[allowed]


def sorted_block_partition_hits(
    candidate_tokens: Sequence[int],
    phrase_rows: np.ndarray,
    word_lengths: Sequence[int],
    index: SortedBlockIndex,
    *,
    max_total_hd: int = 2,
    max_word_hd: int = 1,
    allowed_start_ranges: Sequence[tuple[int, int]] | None = None,
) -> tuple[set[tuple[int, int]], int]:
    phrase_length = phrase_rows.shape[1]
    hits: set[tuple[int, int]] = set()
    proposed_count = 0
    token_dtype = phrase_rows.dtype
    for start in range(len(candidate_tokens) - phrase_length + 1):
        if allowed_start_ranges is not None and not any(lower <= start < upper for lower, upper in allowed_start_ranges):
            continue
        window = candidate_tokens[start:start + phrase_length]
        proposed: set[int] = set()
        for block_index, (block_start, block_end) in enumerate(index.blocks):
            block = np.asarray(window[block_start:block_end], dtype=token_dtype)
            key_dtype = np.dtype((np.void, block.dtype.itemsize * block.shape[0]))
            key = block.view(key_dtype)[0]
            sorted_keys = index.sorted_keys[block_index]
            lower = int(np.searchsorted(sorted_keys, key, side="left"))
            upper = int(np.searchsorted(sorted_keys, key, side="right"))
            proposed.update(int(value) for value in index.sorted_row_indexes[block_index][lower:upper])
        proposed_count += len(proposed)
        verified = vectorized_word_structured_match_indexes(
            window, phrase_rows, proposed, word_lengths,
            max_total_hd=max_total_hd, max_word_hd=max_word_hd,
        )
        hits.update((start, int(phrase_index)) for phrase_index in verified)
    return hits, proposed_count


def sorted_block_partition_hit_details(
    candidate_tokens: Sequence[int],
    phrase_rows: np.ndarray,
    word_lengths: Sequence[int],
    index: SortedBlockIndex,
    *,
    max_total_hd: int = 2,
    max_word_hd: int = 1,
) -> tuple[list[tuple[int, int, tuple[int, ...]]], int]:
    phrase_length = phrase_rows.shape[1]
    hits: list[tuple[int, int, tuple[int, ...]]] = []
    proposed_count = 0
    token_dtype = phrase_rows.dtype
    for start in range(len(candidate_tokens) - phrase_length + 1):
        window = candidate_tokens[start:start + phrase_length]
        proposed: set[int] = set()
        for block_index, (block_start, block_end) in enumerate(index.blocks):
            block = np.asarray(window[block_start:block_end], dtype=token_dtype)
            key_dtype = np.dtype((np.void, block.dtype.itemsize * block.shape[0]))
            key = block.view(key_dtype)[0]
            sorted_keys = index.sorted_keys[block_index]
            lower = int(np.searchsorted(sorted_keys, key, side="left"))
            upper = int(np.searchsorted(sorted_keys, key, side="right"))
            proposed.update(int(value) for value in index.sorted_row_indexes[block_index][lower:upper])
        proposed_count += len(proposed)
        verified_indexes, word_hds = vectorized_word_structured_match_details(
            window, phrase_rows, proposed, word_lengths,
            max_total_hd=max_total_hd, max_word_hd=max_word_hd,
        )
        hits.extend(
            (start, int(phrase_index), tuple(int(value) for value in word_hds[row_index]))
            for row_index, phrase_index in enumerate(verified_indexes)
        )
    return hits, proposed_count


def cluster_hit_spans(spans: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    ordered = sorted(set(spans))
    if not ordered:
        return []
    clusters = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start <= clusters[-1][1]:
            clusters[-1][1] = max(clusters[-1][1], end)
        else:
            clusters.append([start, end])
    return [(start, end) for start, end in clusters]


def annotated_cluster_hit_rows(hits: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    ordered = sorted(
        (
            int(row["start_offset"]),
            int(row["end_offset"]),
            bool(row["is_exact"]),
            str(row.get("length_bucket", "")),
            str(row.get("logical_group_id", "")),
        )
        for row in hits
    )
    if not ordered:
        return []
    clusters: list[dict[str, object]] = []
    current = {
        "start_offset": ordered[0][0],
        "end_offset": ordered[0][1],
        "raw_hit_count": 0,
        "exact_hit_count": 0,
        "length_buckets": set(),
        "logical_group_ids": set(),
    }
    for start, end, is_exact, bucket, group_id in ordered:
        if start > int(current["end_offset"]):
            clusters.append(current)
            current = {
                "start_offset": start,
                "end_offset": end,
                "raw_hit_count": 0,
                "exact_hit_count": 0,
                "length_buckets": set(),
                "logical_group_ids": set(),
            }
        current["end_offset"] = max(int(current["end_offset"]), end)
        current["raw_hit_count"] = int(current["raw_hit_count"]) + 1
        if is_exact:
            current["exact_hit_count"] = int(current["exact_hit_count"]) + 1
        if bucket:
            current["length_buckets"].add(bucket)  # type: ignore[union-attr]
        if group_id:
            current["logical_group_ids"].add(group_id)  # type: ignore[union-attr]
    clusters.append(current)
    out: list[dict[str, object]] = []
    for index, cluster in enumerate(clusters, start=1):
        length_buckets = sorted(cluster["length_buckets"])  # type: ignore[arg-type]
        logical_group_ids = sorted(cluster["logical_group_ids"])  # type: ignore[arg-type]
        exact_hit_count = int(cluster["exact_hit_count"])
        out.append({
            "cluster_id": index,
            "start_offset": int(cluster["start_offset"]),
            "end_offset": int(cluster["end_offset"]),
            "raw_hit_count": int(cluster["raw_hit_count"]),
            "exact_hit_count": exact_hit_count,
            "has_exact": exact_hit_count > 0,
            "length_buckets_present": ",".join(length_buckets),
            "logical_group_count": len(logical_group_ids),
        })
    return out


def semantic_pair_id(trial_id: str, candidate_a_id: str, candidate_b_id: str) -> str:
    left, right = sorted((candidate_a_id, candidate_b_id))
    return f"{trial_id}|{left}|{right}"
