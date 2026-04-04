from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.family_views import (
    cluster_family_ids,
    family_view_distance,
    find_family_view,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage35_candidate_archive import (
    stable_key_hash,
)


SPACE_MAP_RECORD_VERSION = "space_map_v1"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _safe_str(value: Any) -> str:
    return str(value or "")


def _coerce_int_list(value: Any) -> list[int]:
    if value is None:
        return []
    try:
        return [int(x) for x in list(value)]
    except (TypeError, ValueError):
        return []


def _candidate_hash_for_row(row: Mapping[str, Any]) -> str:
    row_d = dict(row or {})
    candidate_hash = _safe_str(row_d.get("candidate_hash", ""))
    if candidate_hash:
        return candidate_hash
    key_idx = _coerce_int_list(
        row_d.get(
            "final_key_idx",
            row_d.get("key_idx", row_d.get("key", [])),
        )
    )
    return str(stable_key_hash(key_idx)) if key_idx else ""


def _row_family_id(row: Mapping[str, Any]) -> str:
    row_d = dict(row or {})
    family_id = _safe_str(row_d.get("family_id", ""))
    if family_id:
        return family_id
    return _safe_str(row_d.get("end_hash", "")) or _candidate_hash_for_row(row_d)


def _row_source(row: Mapping[str, Any]) -> str:
    row_d = dict(row or {})
    return (
        _safe_str(row_d.get("source", ""))
        or _safe_str(row_d.get("stage3_source", ""))
        or _safe_str(row_d.get("seed_source", ""))
    )


def _row_stage_rank(row: Mapping[str, Any], fallback_rank: int) -> int:
    row_d = dict(row or {})
    for field_name in (
        "stage_rank",
        "archive_rank",
        "seed_rank",
        "start_idx",
        "stage3_rank",
    ):
        value = row_d.get(field_name, None)
        if value is not None:
            return _safe_int(value, fallback_rank)
    return int(fallback_rank)


def _row_source_rank(row: Mapping[str, Any]) -> int:
    row_d = dict(row or {})
    for field_name in ("source_rank", "seed_priority_rank", "probe_seed_rank"):
        value = row_d.get(field_name, None)
        if value is not None:
            return _safe_int(value, 0)
    return 0


def _row_is_selected(row: Mapping[str, Any]) -> bool:
    return bool(_safe_int(dict(row or {}).get("selected", 1), 1) == 1)


def _row_key_for_relation(row: Mapping[str, Any]) -> list[int]:
    row_d = dict(row or {})
    return _coerce_int_list(
        row_d.get(
            "final_key_idx",
            row_d.get("key_idx", row_d.get("key", [])),
        )
    )


def _annotate_rows_for_space_map(
    rows: Sequence[Mapping[str, Any]],
    *,
    stage_boundary: str,
    family_view_id: str,
    columns: int,
    anchor_row: Mapping[str, Any] | None,
    fallback_parent_candidate_hash: str = "",
    continued_best_candidate_hash: str = "",
    continued_best_score: float = float("nan"),
    continued_best_match: float = float("nan"),
    next_stage_accept_reason: str = "",
) -> list[dict[str, Any]]:
    out_rows = [dict(row) for row in list(rows or []) if isinstance(row, Mapping)]
    family_view_id_s = _safe_str(family_view_id) or "exact_key"
    family_view = find_family_view(family_view_id_s) or find_family_view("exact_key")
    anchor_row_d = dict(anchor_row or {})
    if anchor_row_d and "key_idx" not in anchor_row_d:
        anchor_row_d["key_idx"] = _row_key_for_relation(anchor_row_d)
    anchor_hash = _candidate_hash_for_row(anchor_row_d) if anchor_row_d else ""

    family_input_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(out_rows, start=1):
        row_d = dict(row)
        if "key_idx" not in row_d:
            row_d["key_idx"] = _row_key_for_relation(row_d)
        candidate_hash = _candidate_hash_for_row(row_d)
        row_id = f"{_safe_str(stage_boundary)}:{idx}:{candidate_hash or idx}"
        family_input_rows.append(
            dict(
                row_id=str(row_id),
                key_idx=_row_key_for_relation(row_d),
                candidate_hash=str(candidate_hash),
            )
        )
        out_rows[int(idx) - 1] = dict(row_d, candidate_hash=str(candidate_hash))

    family_assignments: dict[str, str] = {}
    if family_view is not None and family_input_rows:
        family_assignments, _ = cluster_family_ids(
            family_input_rows,
            family_view=family_view,
            columns=int(columns),
        )

    for idx, row in enumerate(out_rows, start=1):
        row_d = dict(row)
        if "key_idx" not in row_d:
            row_d["key_idx"] = _row_key_for_relation(row_d)
        candidate_hash = _candidate_hash_for_row(row_d)
        row_id = f"{_safe_str(stage_boundary)}:{idx}:{candidate_hash or idx}"
        parent_hash = _safe_str(
            row_d.get("parent_candidate_hash", row_d.get("parent_hash", ""))
        )
        parent_link_kind = _safe_str(row_d.get("parent_link_kind", ""))
        if not parent_hash and fallback_parent_candidate_hash:
            fallback_parent = _safe_str(fallback_parent_candidate_hash)
            if fallback_parent and str(candidate_hash) != str(fallback_parent):
                parent_hash = str(fallback_parent)
                if not parent_link_kind:
                    parent_link_kind = "fallback_anchor"

        if anchor_row_d and str(candidate_hash) == str(anchor_hash):
            distance_to_anchor = 0.0
            if not parent_link_kind:
                parent_link_kind = "root"
        elif anchor_row_d and family_view is not None:
            distance_raw = family_view_distance(
                row_d,
                anchor_row_d,
                family_view=family_view,
                columns=int(columns),
            )
            distance_to_anchor = (
                float(distance_raw)
                if distance_raw is not None
                else _safe_float(
                    row_d.get(
                        "distance_to_anchor",
                        row_d.get("novelty_distance_to_anchor", float("nan")),
                    )
                )
            )
        else:
            distance_to_anchor = _safe_float(
                row_d.get(
                    "distance_to_anchor",
                    row_d.get("novelty_distance_to_anchor", float("nan")),
                )
            )
        if not parent_link_kind:
            parent_link_kind = "observed" if parent_hash else "root"

        family_id = _safe_str(row_d.get("family_id", ""))
        family_id_kind = _safe_str(row_d.get("family_id_kind", ""))
        if not family_id:
            family_id = _safe_str(family_assignments.get(str(row_id), ""))
            if family_id and not family_id_kind:
                family_id_kind = "run_local_cluster"
        if not family_id:
            family_id = _row_family_id(row_d)
            if family_id and not family_id_kind:
                family_id_kind = "hash_fallback"
        if family_id and not family_id_kind:
            family_id_kind = "saved_row"

        if continued_best_candidate_hash and str(candidate_hash) == str(
            fallback_parent_candidate_hash
        ):
            row_d.setdefault(
                "continued_best_candidate_hash",
                str(continued_best_candidate_hash),
            )
            row_d.setdefault("continued_best_score", float(continued_best_score))
            row_d.setdefault("continued_best_match", float(continued_best_match))
            row_d.setdefault(
                "next_stage_accept_reason",
                _safe_str(next_stage_accept_reason),
            )

        out_rows[int(idx) - 1] = dict(
            row_d,
            parent_candidate_hash=str(parent_hash),
            parent_link_kind=str(parent_link_kind),
            distance_to_anchor=float(distance_to_anchor),
            family_view_id=str(family_view_id_s),
            family_id=str(family_id),
            family_id_kind=str(family_id_kind),
        )
    return out_rows


def _coerce_stage3_prep_rows(
    *,
    stage3_prep_live: Mapping[str, Any],
) -> list[dict[str, Any]]:
    stage3_prep = dict(stage3_prep_live or {})
    init_keys = [
        _coerce_int_list(key_vals)
        for key_vals in list(stage3_prep.get("init3", []) or [])
    ]
    promoted_keys = [
        _coerce_int_list(key_vals)
        for key_vals in list(stage3_prep.get("promoted_keys", []) or [])
    ]
    promoted_hash_ranks = {
        str(stable_key_hash(key_vals)): int(idx)
        for idx, key_vals in enumerate(promoted_keys, start=1)
        if key_vals
    }

    out_rows: list[dict[str, Any]] = []
    for idx, key_vals in enumerate(init_keys, start=1):
        if not key_vals:
            continue
        candidate_hash = str(stable_key_hash(key_vals))
        is_promoted_seed = str(candidate_hash) in promoted_hash_ranks
        out_rows.append(
            dict(
                candidate_hash=str(candidate_hash),
                key_idx=list(key_vals),
                init_key_idx=list(key_vals),
                final_key_idx=list(key_vals),
                source=(
                    "stage2_promoted"
                    if bool(is_promoted_seed)
                    else "stage3_init_mutation"
                ),
                source_rank=int(promoted_hash_ranks.get(str(candidate_hash), 0)),
                stage_rank=int(idx),
                eligible=1,
            )
        )
    return out_rows


def _pairwise_key_distance_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    key_rows = [
        np.asarray(
            _coerce_int_list(
                dict(row).get("final_key_idx", dict(row).get("key_idx", []))
            ),
            dtype=np.int16,
        ).reshape(-1)
        for row in list(rows or [])
    ]
    key_rows = [arr for arr in key_rows if int(arr.size) > 0]
    distances: list[float] = []
    for idx, lhs in enumerate(key_rows):
        for rhs in key_rows[idx + 1 :]:
            if int(lhs.size) != int(rhs.size):
                continue
            distances.append(float(np.mean(lhs != rhs)))
    if not distances:
        return dict(
            selected_pairwise_distance_min=float("nan"),
            selected_pairwise_distance_mean=float("nan"),
        )
    return dict(
        selected_pairwise_distance_min=float(min(distances)),
        selected_pairwise_distance_mean=float(np.mean(np.asarray(distances, dtype=np.float64))),
    )


def _top_band_rows_for_pool(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    row_dicts = [dict(row) for row in list(rows or []) if isinstance(row, Mapping)]
    selected_count = int(sum(1 for row in row_dicts if _row_is_selected(row)))
    if selected_count <= 0:
        return []
    ranked_rows = sorted(
        row_dicts,
        key=lambda row: (
            _safe_int(
                dict(row).get(
                    "selection_rank",
                    dict(row).get("stage_rank", dict(row).get("source_rank", 0)),
                ),
                0,
            ),
            _candidate_hash_for_row(row),
        ),
    )
    return ranked_rows[: int(selected_count)]


def build_partial_state_row(
    *,
    row: Mapping[str, Any],
    stage_boundary: str,
    run_id: str = "",
    tier_name: str = "",
    text_id: int = 0,
    key_seed: int = 0,
    replay_config_ref: str = "",
    selection_policy: str = "",
    selected_candidate_hashes: Sequence[str] = (),
    admitted_candidate_hashes: Sequence[str] = (),
    rejected_candidate_hashes: Sequence[str] = (),
    reject_reasons_by_hash: Mapping[str, str] | None = None,
    fallback_rank: int = 0,
) -> dict[str, Any]:
    row_d = dict(row or {})
    candidate_hash = _candidate_hash_for_row(row_d)
    selected_set = {str(x) for x in list(selected_candidate_hashes or []) if str(x)}
    admitted_set = {str(x) for x in list(admitted_candidate_hashes or []) if str(x)}
    rejected_set = {str(x) for x in list(rejected_candidate_hashes or []) if str(x)}
    reject_reasons = {
        str(k): _safe_str(v) for k, v in dict(reject_reasons_by_hash or {}).items()
    }
    init_key_idx = _coerce_int_list(
        row_d.get("init_key_idx", row_d.get("key_idx", row_d.get("key", [])))
    )
    final_key_idx = _coerce_int_list(
        row_d.get("final_key_idx", row_d.get("key_idx", row_d.get("key", [])))
    )
    init_plaintext_idx = _coerce_int_list(
        row_d.get(
            "init_plaintext_idx",
            row_d.get("plaintext_idx", row_d.get("pt", [])),
        )
    )
    final_plaintext_idx = _coerce_int_list(
        row_d.get(
            "final_plaintext_idx",
            row_d.get("plaintext_idx", row_d.get("pt", [])),
        )
    )
    init_score = _safe_float(row_d.get("init_score", row_d.get("score", float("nan"))))
    final_score = _safe_float(
        row_d.get("final_score", row_d.get("score", float("nan")))
    )
    init_search_score = _safe_float(
        row_d.get("init_search_score", row_d.get("search_score", float("nan")))
    )
    final_search_score = _safe_float(
        row_d.get("final_search_score", row_d.get("search_score", float("nan")))
    )
    init_match = _safe_float(row_d.get("init_match", row_d.get("match", float("nan"))))
    final_match = _safe_float(
        row_d.get("final_match", row_d.get("match", float("nan")))
    )
    family_id = _row_family_id(row_d)
    family_id_kind = _safe_str(row_d.get("family_id_kind", ""))
    if not family_id_kind:
        family_id_kind = "saved_row" if _safe_str(row_d.get("family_id", "")) else "hash_fallback"
    return dict(
        record_version=str(SPACE_MAP_RECORD_VERSION),
        run_id=_safe_str(run_id),
        tier_name=_safe_str(tier_name),
        text_id=int(text_id),
        key_seed=int(key_seed),
        stage_boundary=_safe_str(stage_boundary),
        candidate_hash=str(candidate_hash),
        parent_candidate_hash=_safe_str(
            row_d.get("parent_candidate_hash", row_d.get("parent_hash", ""))
        ),
        parent_link_kind=_safe_str(row_d.get("parent_link_kind", "")),
        source=_row_source(row_d),
        lane=_safe_str(row_d.get("lane", "")),
        source_rank=_row_source_rank(row_d),
        stage_rank=_row_stage_rank(row_d, fallback_rank),
        init_key_idx=list(init_key_idx),
        init_plaintext_idx=list(init_plaintext_idx),
        final_key_idx=list(final_key_idx),
        final_plaintext_idx=list(final_plaintext_idx),
        replay_config_ref=_safe_str(replay_config_ref),
        init_score=float(init_score),
        final_score=float(final_score),
        init_search_score=float(init_search_score),
        final_search_score=float(final_search_score),
        score_gain=float(
            _safe_float(row_d.get("score_gain", final_score - init_score))
        ),
        init_match=float(init_match),
        final_match=float(final_match),
        match_gain=float(
            _safe_float(row_d.get("match_gain", final_match - init_match))
        ),
        pool_member=1,
        eligible=_safe_int(
            row_d.get(
                "eligible",
                row_d.get(
                    "eligible_novel_challenger",
                    1,
                ),
            ),
            1,
        ),
        selected=int(1 if str(candidate_hash) in selected_set else 0),
        selection_policy=_safe_str(selection_policy),
        selection_rank=_row_stage_rank(row_d, fallback_rank),
        rejected=int(1 if str(candidate_hash) in rejected_set else 0),
        reject_reason=_safe_str(reject_reasons.get(str(candidate_hash), "")),
        admitted_by_next_stage=int(1 if str(candidate_hash) in admitted_set else 0),
        next_stage_accept_reason=_safe_str(
            row_d.get("next_stage_accept_reason", "")
        ),
        continued_best_candidate_hash=_safe_str(
            row_d.get("continued_best_candidate_hash", "")
        ),
        continued_best_score=_safe_float(
            row_d.get("continued_best_score", float("nan"))
        ),
        continued_best_match=_safe_float(
            row_d.get("continued_best_match", float("nan"))
        ),
        start_hash=_safe_str(row_d.get("start_hash", "")) or str(candidate_hash),
        end_hash=_safe_str(row_d.get("end_hash", "")) or str(candidate_hash),
        family_view_id=_safe_str(row_d.get("family_view_id", "candidate_hash_exact")),
        family_id=str(family_id),
        family_id_kind=str(family_id_kind),
        within_family_rank=_safe_int(row_d.get("within_family_rank", 0), 0),
        distance_to_anchor=_safe_float(
            row_d.get(
                "distance_to_anchor",
                row_d.get("novelty_distance_to_anchor", float("nan")),
            )
        ),
        nearest_selected_distance=_safe_float(
            row_d.get("nearest_selected_distance", float("nan"))
        ),
        nearest_better_truth_distance=_safe_float(
            row_d.get("nearest_better_truth_distance", float("nan"))
        ),
        preview_text=_safe_str(row_d.get("preview_text", row_d.get("preview", ""))),
        word_ngram_summary=dict(row_d.get("word_ngram_summary", {}) or {}),
        lexical_request_count=_safe_int(
            row_d.get("lexical_request_count", row_d.get("lex_req_delta", 0)),
            0,
        ),
        lexical_threshold_skip_count=_safe_int(
            row_d.get(
                "lexical_threshold_skip_count",
                row_d.get("lex_threshold_skip_delta", 0),
            ),
            0,
        ),
        lexical_tie_count=_safe_int(
            row_d.get("lexical_tie_count", row_d.get("lex_tie", 0)),
            0,
        ),
    )


def build_pool_summary_row(
    *,
    rows: Sequence[Mapping[str, Any]],
    stage_boundary: str,
    run_id: str = "",
    tier_name: str = "",
    text_id: int = 0,
    key_seed: int = 0,
    pool_id: str = "",
    pool_status: str = "available",
    selection_policy: str = "",
    family_view_id: str = "candidate_hash_exact",
    anchor_candidate_hash: str = "",
) -> dict[str, Any]:
    row_dicts = [dict(row) for row in list(rows or []) if isinstance(row, Mapping)]
    family_ids = [_row_family_id(row) for row in row_dicts if _row_family_id(row)]
    family_counts = Counter(family_ids)
    selected_rows = [row for row in row_dicts if _row_is_selected(row)]
    selected_family_ids = [
        _row_family_id(row) for row in selected_rows if _row_family_id(row)
    ]
    top_band_rows = _top_band_rows_for_pool(row_dicts)
    top_band_family_ids = [
        _row_family_id(row) for row in top_band_rows if _row_family_id(row)
    ]
    source_counts = Counter(_row_source(row) or "unknown" for row in row_dicts)
    lane_counts = Counter(_safe_str(row.get("lane", "")) or "unknown" for row in row_dicts)
    distance_values = [
        _safe_float(
            row.get(
                "distance_to_anchor",
                row.get("novelty_distance_to_anchor", float("nan")),
            )
        )
        for row in row_dicts
    ]
    finite_distances = [
        float(value) for value in distance_values if np.isfinite(float(value))
    ]
    pairwise_summary = _pairwise_key_distance_summary(selected_rows)
    row_count = int(len(row_dicts))
    return dict(
        record_version=str(SPACE_MAP_RECORD_VERSION),
        run_id=_safe_str(run_id),
        tier_name=_safe_str(tier_name),
        text_id=int(text_id),
        key_seed=int(key_seed),
        stage_boundary=_safe_str(stage_boundary),
        pool_id=_safe_str(pool_id),
        pool_status=_safe_str(pool_status or "available"),
        selection_policy=_safe_str(selection_policy),
        family_view_id=_safe_str(family_view_id or "candidate_hash_exact"),
        row_count=int(row_count),
        eligible_row_count=int(
            sum(
                1
                for row in row_dicts
                if _safe_int(
                    row.get(
                        "eligible",
                        row.get("eligible_novel_challenger", 1),
                    ),
                    1,
                )
                == 1
            )
        ),
        selected_row_count=int(
            sum(1 for row in row_dicts if _safe_int(row.get("selected", 1), 1) == 1)
        ),
        unique_candidate_hash_count=int(
            len({_candidate_hash_for_row(row) for row in row_dicts if _candidate_hash_for_row(row)})
        ),
        unique_start_hash_count=int(
            len(
                {
                    _safe_str(row.get("start_hash", "")) or _candidate_hash_for_row(row)
                    for row in row_dicts
                }
            )
        ),
        unique_end_hash_count=int(
            len(
                {
                    _safe_str(row.get("end_hash", "")) or _candidate_hash_for_row(row)
                    for row in row_dicts
                }
            )
        ),
        source_counts=dict(source_counts),
        lane_counts=dict(lane_counts),
        family_count=int(len(family_counts)),
        selected_family_count=int(len(set(selected_family_ids))),
        top_band_family_count=int(len(set(top_band_family_ids))),
        largest_family_share=float(
            max(family_counts.values()) / float(max(1, row_count))
            if family_counts
            else 0.0
        ),
        anchor_candidate_hash=_safe_str(anchor_candidate_hash),
        mean_distance_to_anchor=float(
            np.mean(np.asarray(finite_distances, dtype=np.float64))
            if finite_distances
            else float("nan")
        ),
        min_distance_to_anchor=float(
            min(finite_distances) if finite_distances else float("nan")
        ),
        max_distance_to_anchor=float(
            max(finite_distances) if finite_distances else float("nan")
        ),
        selected_pairwise_distance_min=float(
            pairwise_summary["selected_pairwise_distance_min"]
        ),
        selected_pairwise_distance_mean=float(
            pairwise_summary["selected_pairwise_distance_mean"]
        ),
        next_stage_started_count=0,
        next_stage_admitted_count=0,
        next_stage_rejected_count=0,
        best_continued_candidate_hash="",
        best_continued_score=float("nan"),
        best_continued_match=float("nan"),
    )


def build_late_space_map_payload(
    *,
    run_id: str = "",
    tier_name: str,
    text_id: int,
    key_seed: int,
    columns: int = 0,
    stage3_diagnostics: Mapping[str, Any],
    stage2_promoted_rows: Sequence[Mapping[str, Any]] | None = None,
    stage3_prep_live: Mapping[str, Any] | None = None,
    stage35_seed_rows: Sequence[Mapping[str, Any]] | None,
    stage35_archive_rows: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    stage3_diag = dict(stage3_diagnostics or {})
    phasec_ran = _safe_int(stage3_diag.get("phaseC_ran", 0), 0)
    phasec_rows = [
        dict(row)
        for row in list(stage3_diag.get("phaseC_start_summaries", []) or [])
        if isinstance(row, Mapping)
    ]
    phasec_pool_rows = [
        dict(row)
        for row in list(stage3_diag.get("phaseC_candidate_pool_rows", []) or [])
        if isinstance(row, Mapping)
    ]
    stage2_rows = [
        dict(row)
        for row in list(stage2_promoted_rows or [])
        if isinstance(row, Mapping)
    ]
    stage3_prep_rows = _coerce_stage3_prep_rows(
        stage3_prep_live=dict(stage3_prep_live or {})
    )
    seed_rows = [
        dict(row)
        for row in list(stage35_seed_rows or [])
        if isinstance(row, Mapping)
    ]
    archive_rows = [
        dict(row)
        for row in list(stage35_archive_rows or [])
        if isinstance(row, Mapping)
    ]
    family_view_id = _safe_str(
        stage3_diag.get("phaseC_novel_view_id", "prefix_hamming_le_24")
    ) or "exact_key"
    phasec_anchor_hash = _safe_str(stage3_diag.get("phaseC_anchor_candidate_hash", ""))
    baseline_hash = _safe_str(stage3_diag.get("stage35_baseline_candidate_hash", ""))
    best_hash = _safe_str(stage3_diag.get("stage35_best_candidate_hash", ""))
    accept_passed = _safe_int(stage3_diag.get("stage35_accept_passed", 0), 0)
    accept_reason = _safe_str(stage3_diag.get("stage35_accept_reason", ""))
    stage2_anchor_row = dict(stage2_rows[0]) if stage2_rows else {}
    stage2_anchor_hash = (
        _candidate_hash_for_row(stage2_anchor_row) if stage2_anchor_row else ""
    )
    stage3_anchor_row = (
        dict(stage3_prep_rows[0])
        if stage3_prep_rows
        else dict(stage2_anchor_row)
    )
    stage3_anchor_hash = (
        _candidate_hash_for_row(stage3_anchor_row) if stage3_anchor_row else ""
    )
    stage3_promoted_key_tuples = {
        tuple(_coerce_int_list(key_vals))
        for key_vals in list(dict(stage3_prep_live or {}).get("promoted_keys", []) or [])
        if _coerce_int_list(key_vals)
    }
    stage3_promoted_hashes = {
        _candidate_hash_for_row(row)
        for row in stage2_rows
        if tuple(_row_key_for_relation(row)) in stage3_promoted_key_tuples
        and _candidate_hash_for_row(row)
    }
    if not stage3_promoted_hashes:
        stage3_promoted_hashes = {
            str(stable_key_hash(list(key_t)))
            for key_t in stage3_promoted_key_tuples
            if key_t
        }
    phasec_anchor_row = next(
        (
            dict(row)
            for row in phasec_rows
            if _candidate_hash_for_row(row) == str(phasec_anchor_hash)
        ),
        dict(phasec_rows[0])
        if phasec_rows
        else (dict(phasec_pool_rows[0]) if phasec_pool_rows else {}),
    )
    baseline_seed_anchor_row = next(
        (
            dict(row)
            for row in seed_rows
            if _candidate_hash_for_row(row) == str(baseline_hash)
        ),
        dict(seed_rows[0]) if seed_rows else dict(phasec_anchor_row),
    )
    archive_anchor_row = next(
        (
            dict(row)
            for row in archive_rows
            if _candidate_hash_for_row(row) == str(baseline_hash)
        ),
        dict(baseline_seed_anchor_row),
    )
    stage2_rows = _annotate_rows_for_space_map(
        stage2_rows,
        stage_boundary="stage2_promoted",
        family_view_id=family_view_id,
        columns=int(columns),
        anchor_row=stage2_anchor_row,
    )
    stage3_prep_rows = _annotate_rows_for_space_map(
        stage3_prep_rows,
        stage_boundary="stage3_prep",
        family_view_id=family_view_id,
        columns=int(columns),
        anchor_row=stage3_anchor_row,
        fallback_parent_candidate_hash=str(stage3_anchor_hash),
    )
    phasec_pool_rows = _annotate_rows_for_space_map(
        phasec_pool_rows,
        stage_boundary="phaseC_pool",
        family_view_id=family_view_id,
        columns=int(columns),
        anchor_row=phasec_anchor_row,
        fallback_parent_candidate_hash=str(phasec_anchor_hash),
    )
    phasec_rows = _annotate_rows_for_space_map(
        phasec_rows,
        stage_boundary="phaseC_start",
        family_view_id=family_view_id,
        columns=int(columns),
        anchor_row=phasec_anchor_row,
        fallback_parent_candidate_hash=str(phasec_anchor_hash),
    )
    seed_rows = _annotate_rows_for_space_map(
        seed_rows,
        stage_boundary="stage35_seed",
        family_view_id=family_view_id,
        columns=int(columns),
        anchor_row=baseline_seed_anchor_row,
        fallback_parent_candidate_hash=str(baseline_hash),
        continued_best_candidate_hash=str(best_hash),
        continued_best_score=_safe_float(
            stage3_diag.get("stage35_best_score", float("nan"))
        ),
        continued_best_match=_safe_float(
            stage3_diag.get("stage35_best_match", float("nan"))
        ),
        next_stage_accept_reason=str(accept_reason),
    )
    archive_rows = _annotate_rows_for_space_map(
        archive_rows,
        stage_boundary="stage35_archive",
        family_view_id=family_view_id,
        columns=int(columns),
        anchor_row=archive_anchor_row,
        fallback_parent_candidate_hash=str(baseline_hash),
    )
    phasec_selected_hashes = [_candidate_hash_for_row(row) for row in phasec_rows]
    stage35_selected_hashes = [baseline_hash] if baseline_hash else []
    archive_selected_hashes = [best_hash] if best_hash else []
    admitted_hashes = [baseline_hash] if baseline_hash and accept_passed == 1 else []
    rejected_hashes = [baseline_hash] if baseline_hash and accept_passed != 1 else []
    reject_reasons = {baseline_hash: accept_reason} if baseline_hash and accept_passed != 1 else {}

    partial_rows: list[dict[str, Any]] = []
    partial_rows.extend(
        build_partial_state_row(
            row=row,
            stage_boundary="stage2_promoted",
            run_id=run_id,
            tier_name=tier_name,
            text_id=int(text_id),
            key_seed=int(key_seed),
            replay_config_ref="stage2_promoted",
            selection_policy="stage2_promoted_rank",
            selected_candidate_hashes=[
                _candidate_hash_for_row(promoted_row)
                for promoted_row in stage2_rows
            ],
            admitted_candidate_hashes=sorted(stage3_promoted_hashes),
            fallback_rank=idx,
        )
        for idx, row in enumerate(stage2_rows, start=1)
    )
    stage3_prep_selection_policy = _safe_str(
        dict(stage3_prep_live or {}).get(
            "stage3_entry_allocation_policy",
            "stage3_prep_init",
        )
    ) or "stage3_prep_init"
    partial_rows.extend(
        build_partial_state_row(
            row=row,
            stage_boundary="stage3_prep",
            run_id=run_id,
            tier_name=tier_name,
            text_id=int(text_id),
            key_seed=int(key_seed),
            replay_config_ref="stage3_prep_live.init3",
            selection_policy=str(stage3_prep_selection_policy),
            selected_candidate_hashes=[
                _candidate_hash_for_row(prep_row)
                for prep_row in stage3_prep_rows
            ],
            fallback_rank=idx,
        )
        for idx, row in enumerate(stage3_prep_rows, start=1)
    )
    partial_rows.extend(
        build_partial_state_row(
            row=row,
            stage_boundary="phaseC_pool",
            run_id=run_id,
            tier_name=tier_name,
            text_id=int(text_id),
            key_seed=int(key_seed),
            replay_config_ref="phaseC_candidate_pool_rows",
            selection_policy=_safe_str(
                stage3_diag.get("phaseC_start_policy", "source_order")
            ),
            selected_candidate_hashes=phasec_selected_hashes,
            admitted_candidate_hashes=admitted_hashes,
            rejected_candidate_hashes=rejected_hashes,
            reject_reasons_by_hash=reject_reasons,
            fallback_rank=idx,
        )
        for idx, row in enumerate(phasec_pool_rows, start=1)
    )
    partial_rows.extend(
        build_partial_state_row(
            row=row,
            stage_boundary="phaseC_start",
            run_id=run_id,
            tier_name=tier_name,
            text_id=int(text_id),
            key_seed=int(key_seed),
            replay_config_ref="phaseC_start_summaries",
            selection_policy=_safe_str(
                stage3_diag.get("phaseC_start_policy", "source_order")
            ),
            selected_candidate_hashes=phasec_selected_hashes,
            admitted_candidate_hashes=admitted_hashes,
            rejected_candidate_hashes=rejected_hashes,
            reject_reasons_by_hash=reject_reasons,
            fallback_rank=idx,
        )
        for idx, row in enumerate(phasec_rows, start=1)
    )
    partial_rows.extend(
        build_partial_state_row(
            row=row,
            stage_boundary="stage35_seed",
            run_id=run_id,
            tier_name=tier_name,
            text_id=int(text_id),
            key_seed=int(key_seed),
            replay_config_ref="stage35_seed_rows",
            selection_policy=_safe_str(
                stage3_diag.get("stage35_baseline_selector", "legacy")
            ),
            selected_candidate_hashes=stage35_selected_hashes,
            admitted_candidate_hashes=admitted_hashes,
            rejected_candidate_hashes=rejected_hashes,
            reject_reasons_by_hash=reject_reasons,
            fallback_rank=idx,
        )
        for idx, row in enumerate(seed_rows, start=1)
    )
    partial_rows.extend(
        build_partial_state_row(
            row=row,
            stage_boundary="stage35_archive",
            run_id=run_id,
            tier_name=tier_name,
            text_id=int(text_id),
            key_seed=int(key_seed),
            replay_config_ref="stage35_archive_rows",
            selection_policy="stage35_archive_rank",
            selected_candidate_hashes=archive_selected_hashes,
            admitted_candidate_hashes=archive_selected_hashes
            if accept_passed == 1
            else (),
            fallback_rank=idx,
        )
        for idx, row in enumerate(archive_rows, start=1)
    )

    pool_summaries = [
        build_pool_summary_row(
            rows=partial_rows_for_stage,
            stage_boundary=stage_name,
            run_id=run_id,
            tier_name=tier_name,
            text_id=int(text_id),
            key_seed=int(key_seed),
            pool_id=stage_name,
            pool_status=(
                "not_run"
                if stage_name in {"phaseC_pool", "phaseC_start"}
                and phasec_ran != 1
                and not partial_rows_for_stage
                else (
                    "not_run"
                    if stage_name == "stage3_prep"
                    and not dict(stage3_prep_live or {})
                    and not partial_rows_for_stage
                    else (
                        "empty"
                        if not partial_rows_for_stage
                        else "available"
                    )
                )
            ),
            selection_policy=selection_policy,
            family_view_id=str(family_view_id),
            anchor_candidate_hash=(
                str(stage2_anchor_hash)
                if stage_name == "stage2_promoted"
                else (
                    str(stage3_anchor_hash)
                    if stage_name == "stage3_prep"
                    else (
                        str(baseline_hash)
                        if stage_name in {"stage35_seed", "stage35_archive"}
                        else str(phasec_anchor_hash)
                    )
                )
            ),
        )
        for stage_name, selection_policy, partial_rows_for_stage in (
            (
                "stage2_promoted",
                "stage2_promoted_rank",
                [
                    row
                    for row in partial_rows
                    if row["stage_boundary"] == "stage2_promoted"
                ],
            ),
            (
                "stage3_prep",
                str(stage3_prep_selection_policy),
                [
                    row
                    for row in partial_rows
                    if row["stage_boundary"] == "stage3_prep"
                ],
            ),
            (
                "phaseC_pool",
                _safe_str(stage3_diag.get("phaseC_start_policy", "source_order")),
                [row for row in partial_rows if row["stage_boundary"] == "phaseC_pool"],
            ),
            (
                "phaseC_start",
                _safe_str(stage3_diag.get("phaseC_start_policy", "source_order")),
                [row for row in partial_rows if row["stage_boundary"] == "phaseC_start"],
            ),
            (
                "stage35_seed",
                _safe_str(stage3_diag.get("stage35_baseline_selector", "legacy")),
                [row for row in partial_rows if row["stage_boundary"] == "stage35_seed"],
            ),
            (
                "stage35_archive",
                "stage35_archive_rank",
                [row for row in partial_rows if row["stage_boundary"] == "stage35_archive"],
            ),
        )
    ]
    stage35_seed_summary = next(
        row
        for row in pool_summaries
        if row.get("stage_boundary", "") == "stage35_seed"
    )
    stage35_seed_summary["next_stage_started_count"] = int(len(seed_rows))
    stage35_seed_summary["next_stage_admitted_count"] = int(
        1 if accept_passed == 1 and baseline_hash else 0
    )
    stage35_seed_summary["next_stage_rejected_count"] = int(
        1 if accept_passed != 1 and baseline_hash else 0
    )
    stage35_seed_summary["best_continued_candidate_hash"] = str(best_hash)
    stage35_seed_summary["best_continued_score"] = _safe_float(
        stage3_diag.get("stage35_best_score", float("nan"))
    )
    stage35_seed_summary["best_continued_match"] = _safe_float(
        stage3_diag.get("stage35_best_match", float("nan"))
    )
    return dict(
        record_version=str(SPACE_MAP_RECORD_VERSION),
        run_id=_safe_str(run_id),
        partial_state_rows=partial_rows,
        pool_summaries=pool_summaries,
    )
