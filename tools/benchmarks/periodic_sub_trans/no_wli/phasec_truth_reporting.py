from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return float(out)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _finite_or_none(value: Any) -> float | None:
    out = _safe_float(value)
    return float(out) if math.isfinite(float(out)) else None


def _normalize_row(row_obj: Mapping[str, Any]) -> Dict[str, Any]:
    row = dict(row_obj)
    return dict(
        start_idx=_safe_int(row.get("start_idx", 0), 0),
        lane=str(row.get("lane", "") or ""),
        source=str(row.get("source", "") or ""),
        source_rank=_safe_int(row.get("source_rank", 0), 0),
        candidate_hash=str(row.get("candidate_hash", "") or ""),
        selection_bucket=str(row.get("selection_bucket", "") or ""),
        selected_by_novel_policy=_safe_int(
            row.get("selected_by_novel_policy", 0), 0
        ),
        eligible_novel_challenger=_safe_int(
            row.get("eligible_novel_challenger", 0), 0
        ),
        novelty_distance_to_anchor=(
            _safe_int(row.get("novelty_distance_to_anchor"))
            if row.get("novelty_distance_to_anchor", None) is not None
            else None
        ),
        novelty_min_distance_to_selected_challenger=(
            _safe_int(row.get("novelty_min_distance_to_selected_challenger"))
            if row.get("novelty_min_distance_to_selected_challenger", None) is not None
            else None
        ),
        init_match=_finite_or_none(row.get("init_match")),
        final_match=_finite_or_none(row.get("final_match")),
        init_score=_finite_or_none(row.get("init_score")),
        final_score=_finite_or_none(row.get("final_score")),
        match_gain=_finite_or_none(row.get("match_gain")),
        score_gain=_finite_or_none(row.get("score_gain")),
        became_global_best=_safe_int(row.get("became_global_best", 0), 0),
        overtook_anchor=_safe_int(row.get("overtook_anchor", 0), 0),
    )


def _score_match_start_key(row: Mapping[str, Any]) -> tuple[float, float, int]:
    final_score = _safe_float(row.get("final_score"))
    final_match = _safe_float(row.get("final_match"))
    return (
        final_score if math.isfinite(final_score) else float("-inf"),
        final_match if math.isfinite(final_match) else float("-inf"),
        _safe_int(row.get("start_idx", 0), 0),
    )


def _truth_start_key(row: Mapping[str, Any]) -> tuple[float, float, int]:
    final_match = _safe_float(row.get("final_match"))
    final_score = _safe_float(row.get("final_score"))
    return (
        final_match if math.isfinite(final_match) else float("-inf"),
        final_score if math.isfinite(final_score) else float("-inf"),
        _safe_int(row.get("start_idx", 0), 0),
    )


def _select_score_winner_row(
    *,
    rows: Sequence[Mapping[str, Any]],
    phasec_final_winner_lane: str,
    phasec_final_winner_source: str,
) -> Dict[str, Any] | None:
    became_global_best_rows = [
        dict(row)
        for row in rows
        if _safe_int(row.get("became_global_best", 0), 0) == 1
    ]
    if became_global_best_rows:
        return dict(became_global_best_rows[-1])

    matching_rows = [
        dict(row)
        for row in rows
        if str(row.get("lane", "") or "") == str(phasec_final_winner_lane or "")
        and str(row.get("source", "") or "") == str(phasec_final_winner_source or "")
    ]
    if matching_rows:
        return dict(max(matching_rows, key=_score_match_start_key))

    if rows:
        return dict(max(rows, key=_score_match_start_key))
    return None


def _select_best_truth_row(
    rows: Sequence[Mapping[str, Any]],
    *,
    exclude_candidate_hash: str = "",
) -> Dict[str, Any] | None:
    filtered_rows = [
        dict(row)
        for row in rows
        if (
            not exclude_candidate_hash
            or str(row.get("candidate_hash", "") or "") != str(exclude_candidate_hash)
        )
        and math.isfinite(_safe_float(row.get("final_match")))
    ]
    if not filtered_rows:
        return None
    return dict(max(filtered_rows, key=_truth_start_key))


def build_phasec_truth_reporting(
    *,
    phasec_start_summaries: Sequence[Mapping[str, Any]] | None,
    phasec_final_winner_lane: str = "",
    phasec_final_winner_source: str = "",
) -> Dict[str, Any]:
    rows = [
        _normalize_row(row)
        for row in list(phasec_start_summaries or [])
        if isinstance(row, Mapping)
    ]
    if not rows:
        return dict(
            phaseC_truth_reporting_available=0,
            phaseC_score_selected_winner_summary={},
            phaseC_best_truth_start_summary={},
            phaseC_best_truth_challenger_summary={},
            phaseC_truth_disagreement_summary=dict(
                available=0,
                winner_and_best_truth_differ=0,
                best_truth_challenger_available=0,
                winner_candidate_hash="",
                best_truth_candidate_hash="",
                best_truth_challenger_candidate_hash="",
                winner_truth_match=None,
                best_truth_match=None,
                best_truth_challenger_match=None,
                winner_score=None,
                best_truth_score=None,
                best_truth_challenger_score=None,
                truth_gap_best_truth_vs_winner=None,
                truth_gap_best_truth_challenger_vs_winner=None,
                score_gap_best_truth_vs_winner=None,
                score_gap_best_truth_challenger_vs_winner=None,
                winner_source="",
                best_truth_source="",
                best_truth_challenger_source="",
                winner_lane="",
                best_truth_lane="",
                best_truth_challenger_lane="",
                winner_selection_bucket="",
                best_truth_selection_bucket="",
                best_truth_challenger_selection_bucket="",
                winner_selected_by_novel_policy=0,
                best_truth_selected_by_novel_policy=0,
                best_truth_challenger_selected_by_novel_policy=0,
            ),
        )

    score_winner = _select_score_winner_row(
        rows=rows,
        phasec_final_winner_lane=str(phasec_final_winner_lane or ""),
        phasec_final_winner_source=str(phasec_final_winner_source or ""),
    )
    best_truth = _select_best_truth_row(rows)
    winner_hash = (
        str(score_winner.get("candidate_hash", "") or "") if score_winner else ""
    )
    best_truth_challenger = _select_best_truth_row(
        rows,
        exclude_candidate_hash=str(winner_hash),
    )

    winner_match = (
        _finite_or_none(score_winner.get("final_match")) if score_winner else None
    )
    winner_score = (
        _finite_or_none(score_winner.get("final_score")) if score_winner else None
    )
    best_truth_match = (
        _finite_or_none(best_truth.get("final_match")) if best_truth else None
    )
    best_truth_score = (
        _finite_or_none(best_truth.get("final_score")) if best_truth else None
    )
    best_truth_challenger_match = (
        _finite_or_none(best_truth_challenger.get("final_match"))
        if best_truth_challenger
        else None
    )
    best_truth_challenger_score = (
        _finite_or_none(best_truth_challenger.get("final_score"))
        if best_truth_challenger
        else None
    )

    def _gap(lhs: float | None, rhs: float | None) -> float | None:
        if lhs is None or rhs is None:
            return None
        return float(lhs) - float(rhs)

    return dict(
        phaseC_truth_reporting_available=1,
        phaseC_score_selected_winner_summary=dict(score_winner or {}),
        phaseC_best_truth_start_summary=dict(best_truth or {}),
        phaseC_best_truth_challenger_summary=dict(best_truth_challenger or {}),
        phaseC_truth_disagreement_summary=dict(
            available=1,
            winner_and_best_truth_differ=int(
                1
                if (
                    score_winner is not None
                    and best_truth is not None
                    and str(score_winner.get("candidate_hash", "") or "")
                    != str(best_truth.get("candidate_hash", "") or "")
                )
                else 0
            ),
            best_truth_challenger_available=int(
                1 if best_truth_challenger is not None else 0
            ),
            winner_candidate_hash=str(
                score_winner.get("candidate_hash", "") if score_winner else ""
            ),
            best_truth_candidate_hash=str(
                best_truth.get("candidate_hash", "") if best_truth else ""
            ),
            best_truth_challenger_candidate_hash=str(
                best_truth_challenger.get("candidate_hash", "")
                if best_truth_challenger
                else ""
            ),
            winner_truth_match=winner_match,
            best_truth_match=best_truth_match,
            best_truth_challenger_match=best_truth_challenger_match,
            winner_score=winner_score,
            best_truth_score=best_truth_score,
            best_truth_challenger_score=best_truth_challenger_score,
            truth_gap_best_truth_vs_winner=_gap(best_truth_match, winner_match),
            truth_gap_best_truth_challenger_vs_winner=_gap(
                best_truth_challenger_match,
                winner_match,
            ),
            score_gap_best_truth_vs_winner=_gap(best_truth_score, winner_score),
            score_gap_best_truth_challenger_vs_winner=_gap(
                best_truth_challenger_score,
                winner_score,
            ),
            winner_source=str(score_winner.get("source", "") if score_winner else ""),
            best_truth_source=str(best_truth.get("source", "") if best_truth else ""),
            best_truth_challenger_source=str(
                best_truth_challenger.get("source", "")
                if best_truth_challenger
                else ""
            ),
            winner_lane=str(score_winner.get("lane", "") if score_winner else ""),
            best_truth_lane=str(best_truth.get("lane", "") if best_truth else ""),
            best_truth_challenger_lane=str(
                best_truth_challenger.get("lane", "")
                if best_truth_challenger
                else ""
            ),
            winner_selection_bucket=str(
                score_winner.get("selection_bucket", "") if score_winner else ""
            ),
            best_truth_selection_bucket=str(
                best_truth.get("selection_bucket", "") if best_truth else ""
            ),
            best_truth_challenger_selection_bucket=str(
                best_truth_challenger.get("selection_bucket", "")
                if best_truth_challenger
                else ""
            ),
            winner_selected_by_novel_policy=_safe_int(
                score_winner.get("selected_by_novel_policy", 0), 0
            )
            if score_winner
            else 0,
            best_truth_selected_by_novel_policy=_safe_int(
                best_truth.get("selected_by_novel_policy", 0), 0
            )
            if best_truth
            else 0,
            best_truth_challenger_selected_by_novel_policy=_safe_int(
                best_truth_challenger.get("selected_by_novel_policy", 0), 0
            )
            if best_truth_challenger
            else 0,
        ),
    )
