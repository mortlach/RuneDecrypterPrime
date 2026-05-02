from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "verify_candidate3_phasec_saved_surface_1511_7004.py"
    )


REPO_ROOT = _find_repo_root()
SOURCE_ARTIFACT_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260414T020217422155Z__bench_solve_pipeline_no_wli__9557c0f/"
    "final_instances/fixture_001__p9_c3_l1000__text0__seed1511__search7004.json"
)
RUN_LABEL = "candidate3_phasec_saved_surface_1511_search7004_v1"
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
)


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _safe_str(value: Any) -> str:
    return str(value or "")


def _ordered_saved_surface_identities(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    identities: list[dict[str, Any]] = []
    for start_rank, row in enumerate(rows, start=1):
        lane = "anchor" if int(start_rank) == 1 else "challenger"
        identities.append(
            {
                "start_rank": int(start_rank),
                "lane": str(lane),
                "source": _safe_str(row.get("source")),
                "source_rank": _safe_int(row.get("source_rank")),
                "candidate_hash": _safe_str(row.get("candidate_hash")),
                "selection_bucket": _safe_str(row.get("selection_bucket")),
                "selected_by_phaseb_topk_anchor_policy": _safe_int(
                    row.get("selected_by_phaseb_topk_anchor_policy")
                ),
                "final_match": _safe_float(row.get("final_match")),
            }
        )
    return identities


def _find_first_distinct_phaseb_topk_index(
    rows: Sequence[Mapping[str, Any]],
) -> int:
    if not rows:
        return -1
    anchor_hash = _safe_str(rows[0].get("candidate_hash"))
    for idx, row in enumerate(rows):
        if _safe_str(row.get("source")) != "phaseB_topk":
            continue
        row_hash = _safe_str(row.get("candidate_hash"))
        if row_hash and anchor_hash and row_hash == anchor_hash:
            continue
        return int(idx)
    return -1


def _find_distinct_phaseb_topk_indices(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int | None,
) -> list[int]:
    if not rows:
        return []
    anchor_hash = _safe_str(rows[0].get("candidate_hash"))
    indices: list[int] = []
    for idx, row in enumerate(rows):
        if _safe_str(row.get("source")) != "phaseB_topk":
            continue
        row_hash = _safe_str(row.get("candidate_hash"))
        if idx == 0:
            continue
        if row_hash and anchor_hash and row_hash == anchor_hash:
            continue
        indices.append(int(idx))
        if limit is not None and len(indices) >= int(limit):
            break
    return indices


def _anchor_fixed_frontload_with_priority_indices(
    rows: Sequence[Mapping[str, Any]],
    *,
    priority_indices: Sequence[int],
    front_selection_bucket: str,
) -> list[dict[str, Any]]:
    saved_rows = [
        _normalize_saved_surface_row(row)
        for row in list(rows or [])
        if isinstance(row, Mapping)
    ]
    priority_idx_list = [int(idx) for idx in list(priority_indices or []) if int(idx) > 0]
    if len(saved_rows) <= 1 or not priority_idx_list:
        return saved_rows

    anchor_row = dict(saved_rows[0], lane="anchor")
    priority_rows = [dict(saved_rows[idx]) for idx in priority_idx_list]
    remaining_rows = [
        dict(row)
        for idx, row in enumerate(saved_rows[1:], start=1)
        if idx not in set(priority_idx_list)
    ]

    out_rows: list[dict[str, Any]] = [anchor_row]
    for rank, row in enumerate(priority_rows, start=1):
        out_rows.append(
            dict(
                row,
                lane="challenger",
                selection_bucket=(
                    str(front_selection_bucket)
                    if int(rank) == 1
                    else f"{front_selection_bucket}_extra"
                ),
                selected_by_phaseb_topk_anchor_policy=_safe_int(
                    row.get("selected_by_phaseb_topk_anchor_policy")
                ),
                selected_by_phaseb_topk_frontload_policy=1,
            )
        )
    for row in remaining_rows:
        out_rows.append(
            dict(
                row,
                lane="challenger",
                selected_by_phaseb_topk_anchor_policy=_safe_int(
                    row.get("selected_by_phaseb_topk_anchor_policy")
                ),
                selected_by_phaseb_topk_frontload_policy=_safe_int(
                    row.get("selected_by_phaseb_topk_frontload_policy")
                ),
            )
        )
    return out_rows


def _normalize_saved_surface_row(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(row)
    init_key_idx = payload.get("init_key_idx")
    if (
        "init_key_idx" not in payload
        or not isinstance(init_key_idx, Sequence)
        or isinstance(init_key_idx, (str, bytes, bytearray))
        or not list(init_key_idx)
    ):
        key_vals = payload.get("key")
        if isinstance(key_vals, Sequence) and not isinstance(
            key_vals, (str, bytes, bytearray)
        ):
            payload["init_key_idx"] = [int(value) for value in list(key_vals)]
    return payload


def _reorder_saved_surface_with_priority_indices(
    rows: Sequence[Mapping[str, Any]],
    *,
    priority_indices: Sequence[int],
    front_selection_bucket: str,
    mark_first_as_phaseb_topk_anchor_policy: bool = False,
) -> list[dict[str, Any]]:
    saved_rows = [
        _normalize_saved_surface_row(row)
        for row in list(rows or [])
        if isinstance(row, Mapping)
    ]
    priority_idx_list = [int(idx) for idx in list(priority_indices or []) if int(idx) > 0]
    if len(saved_rows) <= 1 or not priority_idx_list:
        return saved_rows

    anchor_row = dict(saved_rows[0])
    priority_rows = [dict(saved_rows[idx]) for idx in priority_idx_list]
    remaining_rows = [
        dict(row)
        for idx, row in enumerate(saved_rows)
        if idx not in {0, *priority_idx_list}
    ]

    reordered_rows: list[dict[str, Any]] = []
    for rank, row in enumerate(priority_rows, start=1):
        reordered_rows.append(
            dict(
                row,
                lane="anchor" if int(rank) == 1 else "challenger",
                selection_bucket=(
                    str(front_selection_bucket)
                    if int(rank) == 1
                    else f"{front_selection_bucket}_extra"
                ),
                selected_by_phaseb_topk_anchor_policy=(
                    1
                    if bool(mark_first_as_phaseb_topk_anchor_policy) and int(rank) == 1
                    else _safe_int(row.get("selected_by_phaseb_topk_anchor_policy"))
                ),
            )
        )

    reordered_rows.append(
        dict(
            anchor_row,
            lane="challenger",
            selection_bucket="anchor_demoted",
            selected_by_phaseb_topk_anchor_policy=0,
        )
    )
    for row in remaining_rows:
        reordered_rows.append(
            dict(
                row,
                lane="challenger",
                selected_by_phaseb_topk_anchor_policy=_safe_int(
                    row.get("selected_by_phaseb_topk_anchor_policy")
                ),
            )
        )
    return reordered_rows


def build_candidate3_saved_surface_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    saved_rows = [
        _normalize_saved_surface_row(row)
        for row in list(rows or [])
        if isinstance(row, Mapping)
    ]
    priority_indices = _find_distinct_phaseb_topk_indices(saved_rows, limit=1)
    return _reorder_saved_surface_with_priority_indices(
        saved_rows,
        priority_indices=priority_indices,
        front_selection_bucket="phaseb_topk_anchor",
        mark_first_as_phaseb_topk_anchor_policy=True,
    )


def build_phaseb_topk_frontload_two_saved_surface_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    saved_rows = [
        _normalize_saved_surface_row(row)
        for row in list(rows or [])
        if isinstance(row, Mapping)
    ]
    priority_indices = _find_distinct_phaseb_topk_indices(saved_rows, limit=2)
    return _reorder_saved_surface_with_priority_indices(
        saved_rows,
        priority_indices=priority_indices,
        front_selection_bucket="phaseb_topk_frontload",
    )


def build_phaseb_topk_frontload_all_saved_surface_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    saved_rows = [
        _normalize_saved_surface_row(row)
        for row in list(rows or [])
        if isinstance(row, Mapping)
    ]
    priority_indices = _find_distinct_phaseb_topk_indices(saved_rows, limit=None)
    return _reorder_saved_surface_with_priority_indices(
        saved_rows,
        priority_indices=priority_indices,
        front_selection_bucket="phaseb_topk_frontload",
    )


def build_phaseb_topk_frontload_depth_saved_surface_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    frontload_width: int,
) -> list[dict[str, Any]]:
    saved_rows = [
        _normalize_saved_surface_row(row)
        for row in list(rows or [])
        if isinstance(row, Mapping)
    ]
    priority_indices = _find_distinct_phaseb_topk_indices(
        saved_rows,
        limit=int(max(0, int(frontload_width))),
    )
    return _anchor_fixed_frontload_with_priority_indices(
        saved_rows,
        priority_indices=priority_indices,
        front_selection_bucket="phaseb_topk_frontload_depth",
    )


def _pool_replacement_source_priority(row: Mapping[str, Any]) -> tuple[int, int, str]:
    source = _safe_str(row.get("source"))
    source_priority = {
        "phaseB_topk": 0,
        "phaseA_selected": 1,
    }.get(source, 2)
    source_rank = _safe_int(row.get("source_rank"))
    if int(source_rank) <= 0:
        source_rank = 10**9
    return (
        int(source_priority),
        int(source_rank),
        _safe_str(row.get("candidate_hash")),
    )


def _selected_start_weakness_key(
    row: Mapping[str, Any],
    *,
    start_rank: int,
) -> tuple[float, float, int]:
    init_match = _safe_float(row.get("init_match"))
    init_score = _safe_float(row.get("init_score"))
    if not math.isfinite(init_match):
        init_match = float("inf")
    if not math.isfinite(init_score):
        init_score = float("inf")
    return (
        float(init_match),
        float(init_score),
        -int(start_rank),
    )


def _collect_pool_replacement_challengers(
    candidate_pool_rows: Sequence[Mapping[str, Any]],
    *,
    selected_hashes: set[str],
) -> list[dict[str, Any]]:
    challengers: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for row in sorted(
        [dict(item) for item in list(candidate_pool_rows or []) if isinstance(item, Mapping)],
        key=_pool_replacement_source_priority,
    ):
        candidate_hash = _safe_str(row.get("candidate_hash"))
        if not candidate_hash or candidate_hash in selected_hashes or candidate_hash in seen_hashes:
            continue
        challengers.append(
            dict(
                _normalize_saved_surface_row(row),
                selected_by_pool_replacement_policy=1,
            )
        )
        seen_hashes.add(candidate_hash)
    return challengers


def _collect_phaseb_topk_challengers(
    candidate_pool_rows: Sequence[Mapping[str, Any]],
    *,
    selected_hashes: set[str],
) -> list[dict[str, Any]]:
    challengers: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    normalized_rows = [
        (
            idx,
            _normalize_saved_surface_row(dict(item)),
        )
        for idx, item in enumerate(list(candidate_pool_rows or []))
        if isinstance(item, Mapping)
    ]
    for original_idx, row in sorted(
        normalized_rows,
        key=lambda item: (
            0 if _safe_str(item[1].get("source")) == "phaseB_topk" else 1,
            (
                _safe_int(item[1].get("source_rank"))
                if int(_safe_int(item[1].get("source_rank"))) > 0
                else 10**9
            ),
            int(item[0]),
            _safe_str(item[1].get("candidate_hash")),
        ),
    ):
        _ = original_idx
        candidate_hash = _safe_str(row.get("candidate_hash"))
        if _safe_str(row.get("source")) != "phaseB_topk":
            continue
        if not candidate_hash or candidate_hash in selected_hashes or candidate_hash in seen_hashes:
            continue
        challengers.append(
            dict(
                row,
                selected_by_phaseb_topk_quota_policy=1,
                selected_by_phaseb_topk_only_replacement_policy=1,
            )
        )
        seen_hashes.add(candidate_hash)
    return challengers


def build_phasec_pool_replacement_saved_surface_rows(
    start_rows: Sequence[Mapping[str, Any]],
    candidate_pool_rows: Sequence[Mapping[str, Any]],
    *,
    replace_width: int | None,
) -> list[dict[str, Any]]:
    saved_rows = [
        _normalize_saved_surface_row(row)
        for row in list(start_rows or [])
        if isinstance(row, Mapping)
    ]
    if len(saved_rows) <= 1:
        return saved_rows

    anchor_row = dict(saved_rows[0], lane="anchor")
    selected_hashes = {
        _safe_str(row.get("candidate_hash"))
        for row in saved_rows
        if _safe_str(row.get("candidate_hash"))
    }
    challengers = _collect_pool_replacement_challengers(
        candidate_pool_rows,
        selected_hashes=selected_hashes,
    )
    non_anchor_rows = [
        (start_rank, dict(row))
        for start_rank, row in enumerate(saved_rows[1:], start=2)
        if _safe_str(row.get("candidate_hash"))
    ]
    if not challengers or not non_anchor_rows:
        return saved_rows

    if replace_width is None:
        requested_replacements = int(len(non_anchor_rows))
    else:
        requested_replacements = int(max(0, int(replace_width)))
    replace_count = int(
        min(requested_replacements, len(non_anchor_rows), len(challengers))
    )
    if replace_count <= 0:
        return saved_rows

    evicted_rows = sorted(
        non_anchor_rows,
        key=lambda item: _selected_start_weakness_key(
            item[1],
            start_rank=int(item[0]),
        ),
    )[:replace_count]
    evicted_hashes = {
        _safe_str(row.get("candidate_hash"))
        for _start_rank, row in evicted_rows
        if _safe_str(row.get("candidate_hash"))
    }
    challenger_iter = iter(challengers[:replace_count])

    out_rows: list[dict[str, Any]] = [
        dict(anchor_row, selected_by_pool_replacement_policy=0)
    ]
    for row in saved_rows[1:]:
        candidate_hash = _safe_str(row.get("candidate_hash"))
        if candidate_hash in evicted_hashes:
            challenger = next(challenger_iter, None)
            if challenger is None:
                out_rows.append(
                    dict(row, lane="challenger", selected_by_pool_replacement_policy=0)
                )
                continue
            out_rows.append(
                dict(
                    challenger,
                    lane="challenger",
                    selection_bucket="pool_replacement_challenger",
                    selected_by_phaseb_topk_anchor_policy=0,
                    selected_by_pool_replacement_policy=1,
                    replacement_evicted_candidate_hash=candidate_hash,
                    replacement_evicted_source=_safe_str(row.get("source")),
                    replacement_evicted_source_rank=_safe_int(row.get("source_rank")),
                )
            )
            continue
        out_rows.append(
            dict(
                row,
                lane="challenger",
                selected_by_phaseb_topk_anchor_policy=_safe_int(
                    row.get("selected_by_phaseb_topk_anchor_policy")
                ),
                selected_by_pool_replacement_policy=0,
            )
        )
    return out_rows


def build_phasec_pool_replace_width_one_saved_surface_rows(
    start_rows: Sequence[Mapping[str, Any]],
    candidate_pool_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return build_phasec_pool_replacement_saved_surface_rows(
        start_rows,
        candidate_pool_rows,
        replace_width=1,
    )


def build_phasec_pool_replace_width_two_saved_surface_rows(
    start_rows: Sequence[Mapping[str, Any]],
    candidate_pool_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return build_phasec_pool_replacement_saved_surface_rows(
        start_rows,
        candidate_pool_rows,
        replace_width=2,
    )


def build_phasec_pool_replace_width_three_saved_surface_rows(
    start_rows: Sequence[Mapping[str, Any]],
    candidate_pool_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return build_phasec_pool_replacement_saved_surface_rows(
        start_rows,
        candidate_pool_rows,
        replace_width=3,
    )


def build_phasec_pool_replace_width_cap_all_saved_surface_rows(
    start_rows: Sequence[Mapping[str, Any]],
    candidate_pool_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return build_phasec_pool_replacement_saved_surface_rows(
        start_rows,
        candidate_pool_rows,
        replace_width=None,
    )


def build_phaseb_topk_quota_saved_surface_rows(
    start_rows: Sequence[Mapping[str, Any]],
    candidate_pool_rows: Sequence[Mapping[str, Any]],
    *,
    quota_width: int,
) -> list[dict[str, Any]]:
    saved_rows = [
        _normalize_saved_surface_row(row)
        for row in list(start_rows or [])
        if isinstance(row, Mapping)
    ]
    if len(saved_rows) <= 1:
        return saved_rows

    non_anchor_slot_count = int(len(saved_rows) - 1)
    target_quota = int(min(max(0, int(quota_width)), non_anchor_slot_count))
    if target_quota <= 0:
        return saved_rows

    selected_hashes = {
        _safe_str(row.get("candidate_hash"))
        for row in saved_rows
        if _safe_str(row.get("candidate_hash"))
    }
    existing_phaseb_rows = [
        dict(row)
        for row in saved_rows[1:]
        if _safe_str(row.get("source")) == "phaseB_topk" and _safe_str(row.get("candidate_hash"))
    ]
    if int(len(existing_phaseb_rows)) >= int(target_quota):
        return saved_rows

    phaseb_challengers = _collect_phaseb_topk_challengers(
        candidate_pool_rows,
        selected_hashes=selected_hashes,
    )
    if not phaseb_challengers:
        return saved_rows

    phaseb_stream = sorted(
        [
            dict(row, selected_by_phaseb_topk_quota_policy=0)
            for row in existing_phaseb_rows
        ]
        + [
            dict(
                row,
                selection_bucket="phaseb_topk_quota_challenger",
                selected_by_phaseb_topk_quota_policy=1,
            )
            for row in phaseb_challengers
        ],
        key=lambda row: (
            (
                _safe_int(row.get("source_rank"))
                if int(_safe_int(row.get("source_rank"))) > 0
                else 10**9
            ),
            _safe_str(row.get("candidate_hash")),
        ),
    )
    quota_rows: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for row in phaseb_stream:
        candidate_hash = _safe_str(row.get("candidate_hash"))
        if not candidate_hash or candidate_hash in seen_hashes:
            continue
        quota_rows.append(dict(row, lane="challenger"))
        seen_hashes.add(candidate_hash)
        if int(len(quota_rows)) >= int(target_quota):
            break

    if int(len(quota_rows)) < int(target_quota):
        return saved_rows

    out_rows: list[dict[str, Any]] = [dict(saved_rows[0], lane="anchor")]
    out_rows.extend(quota_rows)
    quota_hashes = {
        _safe_str(row.get("candidate_hash"))
        for row in quota_rows
        if _safe_str(row.get("candidate_hash"))
    }
    for row in saved_rows[1:]:
        candidate_hash = _safe_str(row.get("candidate_hash"))
        if candidate_hash in quota_hashes:
            continue
        out_rows.append(
            dict(
                row,
                lane="challenger",
                selected_by_phaseb_topk_quota_policy=_safe_int(
                    row.get("selected_by_phaseb_topk_quota_policy")
                ),
            )
        )
        if int(len(out_rows)) >= int(len(saved_rows)):
            break
    return out_rows[: len(saved_rows)]


def build_phaseb_topk_only_replacement_saved_surface_rows(
    start_rows: Sequence[Mapping[str, Any]],
    candidate_pool_rows: Sequence[Mapping[str, Any]],
    *,
    replace_width: int,
) -> list[dict[str, Any]]:
    saved_rows = [
        _normalize_saved_surface_row(row)
        for row in list(start_rows or [])
        if isinstance(row, Mapping)
    ]
    if len(saved_rows) <= 1:
        return saved_rows

    selected_hashes = {
        _safe_str(row.get("candidate_hash"))
        for row in saved_rows
        if _safe_str(row.get("candidate_hash"))
    }
    challengers = _collect_phaseb_topk_challengers(
        candidate_pool_rows,
        selected_hashes=selected_hashes,
    )
    non_anchor_rows = [
        (start_rank, dict(row))
        for start_rank, row in enumerate(saved_rows[1:], start=2)
        if _safe_str(row.get("candidate_hash"))
    ]
    if not challengers or not non_anchor_rows:
        return saved_rows

    replace_count = int(
        min(
            max(0, int(replace_width)),
            len(non_anchor_rows),
            len(challengers),
        )
    )
    if replace_count <= 0:
        return saved_rows

    evicted_rows = sorted(
        non_anchor_rows,
        key=lambda item: -int(item[0]),
    )[:replace_count]
    evicted_by_hash = {
        _safe_str(row.get("candidate_hash")): (int(start_rank), dict(row))
        for start_rank, row in evicted_rows
        if _safe_str(row.get("candidate_hash"))
    }
    challenger_iter = iter(challengers[:replace_count])

    out_rows: list[dict[str, Any]] = [dict(saved_rows[0], lane="anchor")]
    for start_rank, row in enumerate(saved_rows[1:], start=2):
        candidate_hash = _safe_str(row.get("candidate_hash"))
        evicted_payload = evicted_by_hash.get(candidate_hash)
        if evicted_payload is None:
            out_rows.append(
                dict(
                    row,
                    lane="challenger",
                    selected_by_phaseb_topk_only_replacement_policy=0,
                )
            )
            continue
        challenger = next(challenger_iter, None)
        if challenger is None:
            out_rows.append(
                dict(
                    row,
                    lane="challenger",
                    selected_by_phaseb_topk_only_replacement_policy=0,
                )
            )
            continue
        evicted_start_rank, evicted_row = evicted_payload
        out_rows.append(
            dict(
                challenger,
                lane="challenger",
                selection_bucket="phaseb_topk_only_replacement_challenger",
                selected_by_phaseb_topk_only_replacement_policy=1,
                replacement_evicted_start_rank=int(evicted_start_rank),
                replacement_evicted_candidate_hash=_safe_str(
                    evicted_row.get("candidate_hash")
                ),
                replacement_evicted_source=_safe_str(evicted_row.get("source")),
                replacement_evicted_source_rank=_safe_int(
                    evicted_row.get("source_rank")
                ),
            )
        )
    return out_rows[: len(saved_rows)]


def build_saved_surface_summary(
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    diagnostics = dict(artifact.get("stage3_diagnostics", {}) or {})
    saved_rows = [
        dict(row)
        for row in list(diagnostics.get("phaseC_start_summaries", []) or [])
        if isinstance(row, Mapping)
    ]
    candidate_rows = build_candidate3_saved_surface_rows(saved_rows)
    control_identities = _ordered_saved_surface_identities(saved_rows)
    candidate_identities = _ordered_saved_surface_identities(candidate_rows)
    phaseb_topk_idx = _find_first_distinct_phaseb_topk_index(saved_rows)
    engageable = int(phaseb_topk_idx > 0)
    anchor_row = dict(saved_rows[0]) if saved_rows else {}
    first_phaseb_topk_row = (
        dict(saved_rows[phaseb_topk_idx]) if int(phaseb_topk_idx) > 0 else {}
    )
    anchor_match = _safe_float(anchor_row.get("final_match"))
    phaseb_topk_match = _safe_float(first_phaseb_topk_row.get("final_match"))
    return {
        "run_label": str(RUN_LABEL),
        "source_artifact_relpath": _relative_path(REPO_ROOT / SOURCE_ARTIFACT_REL_PATH),
        "fixture_seed": _safe_int(artifact.get("instance_source_key_seed")),
        "search_seed": _safe_int(artifact.get("search_seed")),
        "phasec_start_policy": _safe_str(diagnostics.get("phaseC_start_policy")),
        "saved_start_count": int(len(saved_rows)),
        "saved_surface_can_engage": int(engageable),
        "saved_surface_phaseb_topk_index": int(phaseb_topk_idx + 1)
        if int(phaseb_topk_idx) >= 0
        else 0,
        "control_anchor_candidate_hash": _safe_str(anchor_row.get("candidate_hash")),
        "control_anchor_final_match": float(anchor_match),
        "control_first_phaseb_topk_candidate_hash": _safe_str(
            first_phaseb_topk_row.get("candidate_hash")
        ),
        "control_first_phaseb_topk_final_match": float(phaseb_topk_match),
        "saved_surface_phaseb_topk_minus_anchor_final_match": float(
            phaseb_topk_match - anchor_match
        ),
        "control_start_identities": control_identities,
        "candidate_start_identities": candidate_identities,
        "scope_note": (
            "candidate ordering is evaluated on the exact saved Phase-C start "
            "surface only; saved final matches remain the retained original-lane "
            "outcomes and do not constitute a fresh candidate replay"
        ),
    }


def write_saved_surface_markdown(
    output_dir: Path,
    *,
    summary: Mapping[str, Any],
) -> None:
    lines = [
        "# Candidate 3 Saved Phase-C Surface: 1511 / search7004",
        "",
        "Question:",
        "- on the exact saved Phase-C start surface, what would candidate 3 change before replay drift enters the picture?",
        "",
        "Scope note:",
        f"- {str(summary.get('scope_note') or '')}",
        "",
        "Top-line read:",
        f"- source artifact: `{summary.get('source_artifact_relpath')}`",
        f"- saved Phase-C start count: `{summary.get('saved_start_count')}`",
        f"- candidate can engage on saved surface: `{summary.get('saved_surface_can_engage')}`",
        f"- first distinct phaseB_topk start rank on saved surface: `{summary.get('saved_surface_phaseb_topk_index')}`",
        f"- retained anchor hash: `{summary.get('control_anchor_candidate_hash')}`",
        f"- retained anchor final match: `{float(summary.get('control_anchor_final_match', float('nan'))):.3f}`",
        f"- first phaseB_topk hash: `{summary.get('control_first_phaseb_topk_candidate_hash')}`",
        f"- first phaseB_topk final match: `{float(summary.get('control_first_phaseb_topk_final_match', float('nan'))):.3f}`",
        (
            "- saved-surface phaseB_topk minus anchor final match: "
            f"`{float(summary.get('saved_surface_phaseb_topk_minus_anchor_final_match', float('nan'))):.3f}`"
        ),
        "",
        "Control ordering:",
        "",
        "| rank | lane | source | source_rank | candidate_hash | final_match |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in list(summary.get("control_start_identities", []) or []):
        lines.append(
            f"| {int(row.get('start_rank', 0) or 0)} | "
            f"{str(row.get('lane', '') or '')} | "
            f"{str(row.get('source', '') or '')} | "
            f"{int(row.get('source_rank', 0) or 0)} | "
            f"{str(row.get('candidate_hash', '') or '')} | "
            f"{float(row.get('final_match', float('nan'))):.3f} |"
        )
    lines.extend(
        [
            "",
            "Candidate ordering on the same saved surface:",
            "",
            "| rank | lane | source | source_rank | candidate_hash | phaseb_topk_anchor_policy | final_match |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in list(summary.get("candidate_start_identities", []) or []):
        lines.append(
            f"| {int(row.get('start_rank', 0) or 0)} | "
            f"{str(row.get('lane', '') or '')} | "
            f"{str(row.get('source', '') or '')} | "
            f"{int(row.get('source_rank', 0) or 0)} | "
            f"{str(row.get('candidate_hash', '') or '')} | "
            f"{int(row.get('selected_by_phaseb_topk_anchor_policy', 0) or 0)} | "
            f"{float(row.get('final_match', float('nan'))):.3f} |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- this is the stable saved-surface reference for candidate3 while full control replay remains Phase-A/Phase-B drifted",
            "- use it to reason about the exact ordering change candidate3 wants, not as evidence of post-swap utility",
        ]
    )
    (output_dir / "candidate3_saved_surface_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_verification() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    artifact_path = REPO_ROOT / SOURCE_ARTIFACT_REL_PATH
    artifact = _load_json(artifact_path)
    summary = build_saved_surface_summary(artifact)
    _write_json(output_dir / "candidate3_saved_surface_summary.json", summary)
    _write_json(
        output_dir / "candidate3_saved_surface_control_rows.json",
        list(summary.get("control_start_identities", []) or []),
    )
    _write_json(
        output_dir / "candidate3_saved_surface_candidate_rows.json",
        list(summary.get("candidate_start_identities", []) or []),
    )
    write_saved_surface_markdown(output_dir, summary=summary)
    run_summary = {
        "output_dir": _relative_path(output_dir),
        "source_artifact_relpath": str(summary.get("source_artifact_relpath") or ""),
        "fixture_seed": _safe_int(summary.get("fixture_seed")),
        "search_seed": _safe_int(summary.get("search_seed")),
        "saved_surface_can_engage": _safe_int(summary.get("saved_surface_can_engage")),
        "saved_surface_phaseb_topk_index": _safe_int(
            summary.get("saved_surface_phaseb_topk_index")
        ),
        "saved_surface_phaseb_topk_minus_anchor_final_match": float(
            summary.get("saved_surface_phaseb_topk_minus_anchor_final_match", float("nan"))
        ),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    print(json.dumps(run_verification(), sort_keys=True))


if __name__ == "__main__":
    main()
