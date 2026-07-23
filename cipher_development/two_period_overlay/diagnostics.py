from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from cipher_development.shared.archive import (
    CandidateArchive,
    archive_content_hash,
)
from cipher_development.two_period_overlay.config import DECISION_SCORE


def _hamming(left: Sequence[int], right: Sequence[int]) -> int:
    if len(left) != len(right):
        raise ValueError("Hamming vectors must have equal length")
    return sum(int(a) != int(b) for a, b in zip(left, right, strict=True))


def _entropy(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    counts = Counter(int(value) for value in values)
    total = len(values)
    return float(-sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    ))


def _quantiles(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        raise ValueError("diagnostics require at least one score")
    points = (0.0, 0.25, 0.5, 0.75, 1.0)
    labels = ("min", "q25", "median", "q75", "max")
    return {
        label: float(np.quantile(array, point))
        for label, point in zip(labels, points, strict=True)
    }


def discovery_diagnostics(
    archive: CandidateArchive,
    restart_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(archive, CandidateArchive):
        raise TypeError("archive must be a CandidateArchive")
    records = tuple(sorted(archive.records, key=lambda record: record.candidate_id))
    if not records:
        raise ValueError("discovery diagnostics require at least one candidate")
    rows = tuple(dict(row) for row in restart_rows)
    if not rows:
        raise ValueError("discovery diagnostics require restart evidence")

    candidate_ids = tuple(record.candidate_id for record in records)
    affine = {
        record.candidate_id: tuple(int(value) for value in record.payload["variables"])
        for record in records
    }
    expanded = {
        record.candidate_id: tuple(int(value) for value in record.payload["expanded_key"])
        for record in records
    }
    scores = {
        record.candidate_id: float(record.scores[DECISION_SCORE])
        for record in records
    }

    affine_matrix: list[list[int]] = []
    expanded_matrix: list[list[int]] = []
    nearest: dict[str, int | None] = {}
    for left_id in candidate_ids:
        affine_row: list[int] = []
        expanded_row: list[int] = []
        other_affine: list[int] = []
        for right_id in candidate_ids:
            affine_distance = _hamming(affine[left_id], affine[right_id])
            expanded_distance = _hamming(expanded[left_id], expanded[right_id])
            affine_row.append(affine_distance)
            expanded_row.append(expanded_distance)
            if right_id != left_id:
                other_affine.append(affine_distance)
        affine_matrix.append(affine_row)
        expanded_matrix.append(expanded_row)
        nearest[left_id] = None if not other_affine else min(other_affine)

    finite_nearest = [value for value in nearest.values() if value is not None]
    nearest_summary = {
        "minimum": None if not finite_nearest else int(min(finite_nearest)),
        "median": None if not finite_nearest else float(np.median(finite_nearest)),
        "maximum": None if not finite_nearest else int(max(finite_nearest)),
    }

    dimension = len(next(iter(affine.values())))
    coordinate_coverage = []
    for index in range(dimension):
        values = [affine[candidate_id][index] for candidate_id in candidate_ids]
        counts = Counter(values)
        coordinate_coverage.append({
            "index": index,
            "distinct_values": len(counts),
            "entropy_bits": _entropy(values),
            "value_counts": {
                str(value): counts[value] for value in sorted(counts)
            },
        })

    best_record = archive.records[0]
    best_id = best_record.candidate_id
    radii = tuple(sorted({radius for radius in (0, 1, 2, 4, 8) if radius <= dimension}))
    within_radius = {
        str(radius): sum(
            _hamming(affine[best_id], affine[candidate_id]) <= radius
            for candidate_id in candidate_ids
        )
        for radius in radii
    }
    restart_candidate_ids = [str(row["candidate_id"]) for row in rows]
    unique_restart_ids = set(restart_candidate_ids)

    return {
        "schema": "rdp.two_period_overlay.discovery_diagnostics.v1",
        "source_archive_hash": archive_content_hash(archive),
        "candidate_ids": list(candidate_ids),
        "candidate_count": len(candidate_ids),
        "restart_count": len(rows),
        "exact_duplicate_count": len(restart_candidate_ids) - len(unique_restart_ids),
        "affine_dimension": dimension,
        "affine_hamming_matrix": affine_matrix,
        "expanded_key_hamming_matrix": expanded_matrix,
        "nearest_neighbour_affine_hamming": nearest,
        "nearest_neighbour_summary": nearest_summary,
        "coordinate_coverage": coordinate_coverage,
        "score_quantiles": _quantiles(list(scores.values())),
        "score_vs_nearest_neighbour": [
            {
                "candidate_id": candidate_id,
                "score": scores[candidate_id],
                "nearest_affine_hamming": nearest[candidate_id],
            }
            for candidate_id in candidate_ids
        ],
        "best_candidate_id": best_id,
        "within_affine_hamming_radius_of_best": within_radius,
    }
