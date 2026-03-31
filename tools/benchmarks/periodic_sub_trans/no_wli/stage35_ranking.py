from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np


def _score_sort_key(value: float) -> tuple[int, float]:
    if np.isfinite(float(value)):
        return (0, float(-value))
    return (1, 0.0)


def _row_key(row: Mapping[str, Any]) -> tuple[int, ...]:
    return tuple(
        map(
            int,
            row.get("key_idx", row.get("key", []) or []) or [],
        )
    )


def stage35_candidate_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    seed_priority_group = row.get("seed_priority_group", 99)
    target_slice = row.get("target_slice", 10**9)
    return (
        _score_sort_key(float(row.get("score", float("nan")))),
        _score_sort_key(float(row.get("search_score", float("nan")))),
        int(row.get("depth", 0) or 0),
        int(99 if seed_priority_group is None else seed_priority_group),
        str(row.get("seed_source", row.get("source", "")) or ""),
        int(10**9 if target_slice is None else target_slice),
        _row_key(row),
    )


def rank_stage35_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    ranked = sorted((dict(row) for row in rows), key=stage35_candidate_sort_key)
    if limit is None:
        return ranked
    return ranked[: max(0, int(limit))]


def dedupe_stage35_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    best_by_key: dict[tuple[int, ...], dict[str, Any]] = {}
    for row in rows:
        key_t = _row_key(row)
        prev = best_by_key.get(key_t, None)
        row_d = dict(row)
        if prev is None or stage35_candidate_sort_key(row_d) < stage35_candidate_sort_key(prev):
            best_by_key[key_t] = row_d
    return rank_stage35_rows(list(best_by_key.values()))


def substitution_hamming_distance(
    key_a: Sequence[int],
    key_b: Sequence[int],
    *,
    prefix_len: int,
) -> int:
    prefix_i = int(max(0, int(prefix_len)))
    lhs = list(map(int, key_a[:prefix_i]))
    rhs = list(map(int, key_b[:prefix_i]))
    return int(sum(1 for av, bv in zip(lhs, rhs) if int(av) != int(bv)))


def stage35_archive_diversity(
    rows: Sequence[Mapping[str, Any]],
    *,
    prefix_len: int,
    top_n: int = 8,
) -> dict[str, Any]:
    ranked = rank_stage35_rows(rows, limit=int(max(0, int(top_n))))
    keys = [_row_key(row) for row in ranked]
    unique_keys = int(len(set(keys)))
    seed_sources = {
        str(row.get("seed_source", row.get("source", "")) or "") for row in ranked
    }
    target_slices = {
        int(row.get("target_slice"))
        for row in ranked
        if row.get("target_slice", None) is not None
    }
    pair_distances: list[int] = []
    for idx, key_i in enumerate(keys):
        for jdx in range(idx + 1, len(keys)):
            pair_distances.append(
                substitution_hamming_distance(
                    key_i,
                    keys[jdx],
                    prefix_len=int(prefix_len),
                )
            )
    return dict(
        top_n=int(len(ranked)),
        unique_keys=int(unique_keys),
        unique_seed_sources=int(len(seed_sources)),
        unique_target_slices=int(len(target_slices)),
        mean_substitution_hamming=(
            float(np.mean(np.asarray(pair_distances, dtype=np.float64)))
            if pair_distances
            else 0.0
        ),
        max_substitution_hamming=(max(pair_distances) if pair_distances else 0),
    )
