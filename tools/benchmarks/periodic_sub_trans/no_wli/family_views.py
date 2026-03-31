from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence


FAMILY_VIEWS: tuple[dict[str, Any], ...] = (
    {"id": "exact_key", "kind": "exact_key"},
    {"id": "exact_tail", "kind": "exact_tail"},
    {"id": "near_tail_h1", "kind": "near_tail", "tail_hamming_max": 1},
    {
        "id": "prefix_hamming_le_24",
        "kind": "prefix_hamming",
        "prefix_hamming_max": 24,
    },
)


def find_family_view(view_id: str) -> dict[str, Any] | None:
    normalized = str(view_id).strip().lower()
    for view in FAMILY_VIEWS:
        if str(view.get("id", "")).strip().lower() == normalized:
            return dict(view)
    return None


def _tail_tuple(key_idx: Sequence[int] | None, *, columns: int) -> tuple[int, ...] | None:
    if key_idx is None:
        return None
    key_t = tuple(int(v) for v in key_idx)
    if not key_t:
        return None
    cols_i = max(1, int(columns))
    if cols_i >= len(key_t):
        return key_t
    return key_t[-cols_i:]


def _prefix_tuple(key_idx: Sequence[int] | None, *, columns: int) -> tuple[int, ...] | None:
    if key_idx is None:
        return None
    key_t = tuple(int(v) for v in key_idx)
    if not key_t:
        return None
    cols_i = max(1, int(columns))
    if cols_i >= len(key_t):
        return key_t
    return key_t[:-cols_i]


def _hamming_distance(lhs: Sequence[int], rhs: Sequence[int]) -> int:
    left = tuple(int(v) for v in lhs)
    right = tuple(int(v) for v in rhs)
    if len(left) != len(right):
        return max(len(left), len(right))
    return sum(int(a != b) for a, b in zip(left, right))


def _row_key_tuple(row: Mapping[str, Any]) -> tuple[int, ...] | None:
    key_idx = row.get("key_idx", row.get("key"))
    if key_idx is None:
        return None
    return tuple(int(v) for v in key_idx)


def _row_tail_tuple(row: Mapping[str, Any], *, columns: int) -> tuple[int, ...] | None:
    return _tail_tuple(_row_key_tuple(row), columns=columns)


def _row_prefix_tuple(row: Mapping[str, Any], *, columns: int) -> tuple[int, ...] | None:
    return _prefix_tuple(_row_key_tuple(row), columns=columns)


def _feature_for_view(
    row: Mapping[str, Any],
    *,
    family_view: Mapping[str, Any],
    columns: int,
) -> Any:
    view_kind = str(family_view.get("kind", ""))
    if view_kind == "exact_key":
        feature = _row_key_tuple(row)
        if feature is None:
            candidate_hash = str(row.get("candidate_hash", "") or "")
            if candidate_hash:
                return candidate_hash
        return feature
    if view_kind == "exact_tail":
        return _row_tail_tuple(row, columns=columns)
    if view_kind == "near_tail":
        return _row_tail_tuple(row, columns=columns)
    if view_kind == "prefix_hamming":
        return _row_prefix_tuple(row, columns=columns)
    return None


def family_view_distance(
    lhs: Mapping[str, Any],
    rhs: Mapping[str, Any],
    *,
    family_view: Mapping[str, Any],
    columns: int,
) -> int | None:
    left_feature = _feature_for_view(lhs, family_view=family_view, columns=columns)
    right_feature = _feature_for_view(rhs, family_view=family_view, columns=columns)
    if left_feature is None or right_feature is None:
        return None
    view_kind = str(family_view.get("kind", ""))
    if view_kind in {"exact_key", "exact_tail"}:
        return 0 if left_feature == right_feature else 1
    return int(_hamming_distance(left_feature, right_feature))


def rows_share_family(
    lhs: Mapping[str, Any],
    rhs: Mapping[str, Any],
    *,
    family_view: Mapping[str, Any],
    columns: int,
) -> bool | None:
    distance = family_view_distance(
        lhs,
        rhs,
        family_view=family_view,
        columns=columns,
    )
    if distance is None:
        return None
    view_kind = str(family_view.get("kind", ""))
    if view_kind in {"exact_key", "exact_tail"}:
        return bool(int(distance) == 0)
    if view_kind == "near_tail":
        return bool(int(distance) <= int(family_view.get("tail_hamming_max", 1) or 1))
    if view_kind == "prefix_hamming":
        return bool(
            int(distance)
            <= int(family_view.get("prefix_hamming_max", 24) or 24)
        )
    return None


def _component_ids(edge_pairs: Iterable[tuple[int, int]], *, size: int) -> list[int]:
    parent = list(range(size))

    def _find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def _union(lhs: int, rhs: int) -> None:
        left_root = _find(lhs)
        right_root = _find(rhs)
        if left_root == right_root:
            return
        if left_root < right_root:
            parent[right_root] = left_root
        else:
            parent[left_root] = right_root

    for lhs, rhs in edge_pairs:
        _union(int(lhs), int(rhs))

    roots: dict[int, int] = {}
    ids: list[int] = []
    next_id = 0
    for idx in range(size):
        root = _find(idx)
        if root not in roots:
            roots[root] = next_id
            next_id += 1
        ids.append(int(roots[root]))
    return ids


def cluster_family_ids(
    rows: Sequence[Mapping[str, Any]],
    *,
    family_view: Mapping[str, Any],
    columns: int,
) -> tuple[dict[str, str], int]:
    view_kind = str(family_view.get("kind", ""))
    row_ids = [str(row["row_id"]) for row in rows]
    assignments: dict[str, str] = {}
    eligible_ids: list[str] = []
    eligible_features: list[Any] = []

    for row in rows:
        row_id = str(row["row_id"])
        feature = _feature_for_view(row, family_view=family_view, columns=columns)
        if feature is None:
            continue
        eligible_ids.append(row_id)
        eligible_features.append(feature)

    if not eligible_ids:
        return assignments, int(len(row_ids))

    if view_kind in {"exact_key", "exact_tail"}:
        family_lookup: dict[Any, int] = {}
        next_id = 0
        for row_id, feature in zip(eligible_ids, eligible_features):
            if feature not in family_lookup:
                family_lookup[feature] = next_id
                next_id += 1
            assignments[row_id] = f"f{family_lookup[feature]}"
        return assignments, int(len(row_ids) - len(eligible_ids))

    edge_pairs: list[tuple[int, int]] = []
    if view_kind == "near_tail":
        tail_hamming_max = int(family_view.get("tail_hamming_max", 1) or 1)
        for lhs in range(len(eligible_features)):
            for rhs in range(lhs + 1, len(eligible_features)):
                if _hamming_distance(eligible_features[lhs], eligible_features[rhs]) <= tail_hamming_max:
                    edge_pairs.append((lhs, rhs))
    elif view_kind == "prefix_hamming":
        prefix_hamming_max = int(family_view.get("prefix_hamming_max", 24) or 24)
        for lhs in range(len(eligible_features)):
            for rhs in range(lhs + 1, len(eligible_features)):
                if len(eligible_features[lhs]) != len(eligible_features[rhs]):
                    continue
                if _hamming_distance(eligible_features[lhs], eligible_features[rhs]) <= prefix_hamming_max:
                    edge_pairs.append((lhs, rhs))

    family_ids = _component_ids(edge_pairs, size=len(eligible_ids))
    for row_id, fam_id in zip(eligible_ids, family_ids):
        assignments[row_id] = f"f{int(fam_id)}"
    return assignments, int(len(row_ids) - len(eligible_ids))
