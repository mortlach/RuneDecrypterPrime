from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np


def score_sort_key(value: float) -> tuple[int, float]:
    if np.isfinite(float(value)):
        return (0, float(-value))
    return (1, 0.0)


def landing_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        score_sort_key(float(row.get("score", float("nan")))),
        score_sort_key(float(row.get("search_score", float("nan")))),
        int(row.get("mini_search_step", 0) or 0),
        str(row.get("landing_type", "") or ""),
        tuple(map(int, row.get("key", []) or [])),
    )


def rank_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    ranked = sorted((dict(row) for row in rows), key=landing_sort_key)
    return ranked[: max(0, int(limit))]


def score_band_shortlist(
    rows: Sequence[Mapping[str, Any]],
    *,
    score_eps: float,
) -> list[dict[str, Any]]:
    ranked_rows = [dict(row) for row in rows]
    finite_scores = [
        float(row.get("score", float("nan")))
        for row in ranked_rows
        if np.isfinite(float(row.get("score", float("nan"))))
    ]
    if not finite_scores:
        return ranked_rows
    best_score = float(max(finite_scores))
    eps = float(max(0.0, float(score_eps)))
    shortlist = [
        dict(row)
        for row in ranked_rows
        if np.isfinite(float(row.get("score", float("nan"))))
        and float(row.get("score", float("nan"))) >= float(best_score - eps)
    ]
    if shortlist:
        return shortlist
    return rank_rows(ranked_rows, limit=1)


def row_score_gain(row: Mapping[str, Any], *, current_score: float) -> float:
    score = float(row.get("score", float("nan")))
    if np.isfinite(score) and np.isfinite(float(current_score)):
        return float(score - float(current_score))
    return float("nan")


def row_search_gain(
    row: Mapping[str, Any],
    *,
    current_search_score: float,
) -> float:
    search_score = float(row.get("search_score", float("nan")))
    if np.isfinite(search_score) and np.isfinite(float(current_search_score)):
        return float(search_score - float(current_search_score))
    return float("nan")


def row_match_gain(row: Mapping[str, Any], *, current_match: float) -> float:
    match = float(row.get("match", float("nan")))
    if np.isfinite(match) and np.isfinite(float(current_match)):
        return float(match - float(current_match))
    return float("nan")


def lexical_rank_from_row(row: Mapping[str, Any]) -> tuple[float, float, float]:
    active = 1.0 if bool(row.get("lexical_active", False)) else 0.0
    trust = float(row.get("lexical_trust", float("-inf")))
    if not np.isfinite(trust):
        trust = float("-inf")
    report_xent = float(row.get("lexical_report_xent", float("nan")))
    report_xent_sort = float(-report_xent) if np.isfinite(report_xent) else float("-inf")
    return (active, trust, report_xent_sort)


def pareto_shortlist(
    rows: Sequence[Mapping[str, Any]],
    *,
    current_score: float,
    current_search_score: float,
) -> list[dict[str, Any]]:
    ranked_rows = [dict(row) for row in rows]
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(ranked_rows):
        row_score_delta = row_score_gain(row, current_score=float(current_score))
        row_search_delta = row_search_gain(
            row,
            current_search_score=float(current_search_score),
        )
        dominated = False
        for jdx, other in enumerate(ranked_rows):
            if int(jdx) == int(idx):
                continue
            other_score_delta = row_score_gain(other, current_score=float(current_score))
            other_search_delta = row_search_gain(
                other,
                current_search_score=float(current_search_score),
            )
            if not (np.isfinite(other_score_delta) and np.isfinite(other_search_delta)):
                continue
            if not (np.isfinite(row_score_delta) and np.isfinite(row_search_delta)):
                dominated = True
                break
            if (
                float(other_score_delta) >= float(row_score_delta)
                and float(other_search_delta) >= float(row_search_delta)
                and (
                    float(other_score_delta) > float(row_score_delta)
                    or float(other_search_delta) > float(row_search_delta)
                )
            ):
                dominated = True
                break
        if not dominated:
            out.append(dict(row))
    return out


def _selector_sort_key(
    row: Mapping[str, Any],
    *,
    selector_mode: str,
    current_score: float,
    current_search_score: float,
) -> tuple[Any, ...]:
    score_gain_v = row_score_gain(row, current_score=float(current_score))
    search_gain_v = row_search_gain(
        row,
        current_search_score=float(current_search_score),
    )
    key_t = tuple(map(int, row.get("key", []) or []))
    mode = str(selector_mode)
    if mode == "baseline":
        return (
            score_sort_key(float(row.get("score", float("nan")))),
            score_sort_key(float(row.get("search_score", float("nan")))),
            score_sort_key(float(score_gain_v)),
            key_t,
        )
    if mode == "top_score_then_search":
        return (
            score_sort_key(float(search_gain_v)),
            score_sort_key(float(score_gain_v)),
            score_sort_key(float(row.get("score", float("nan")))),
            key_t,
        )
    if mode == "rescue_shallow_then_search":
        return (
            int(row.get("mini_search_step", 0) or 0),
            score_sort_key(float(search_gain_v)),
            score_sort_key(float(score_gain_v)),
            score_sort_key(float(row.get("score", float("nan")))),
            key_t,
        )
    if mode == "score_band_then_lexical_then_search":
        return (
            tuple(-float(v) for v in lexical_rank_from_row(row)),
            score_sort_key(float(search_gain_v)),
            score_sort_key(float(score_gain_v)),
            score_sort_key(float(row.get("score", float("nan")))),
            key_t,
        )
    if mode == "gain_based":
        return (
            score_sort_key(float(search_gain_v)),
            score_sort_key(float(score_gain_v)),
            score_sort_key(float(row.get("search_score", float("nan")))),
            key_t,
        )
    if mode == "pareto_shortlist":
        return (
            score_sort_key(float(search_gain_v)),
            score_sort_key(float(score_gain_v)),
            score_sort_key(float(row.get("score", float("nan")))),
            key_t,
        )
    raise ValueError(f"unknown selector_mode={selector_mode!r}")


def select_guard_passing_row(
    *,
    passing_rows: Sequence[Mapping[str, Any]],
    selector_mode: str,
    current_score: float,
    current_search_score: float,
    score_band_eps: float = 0.0,
) -> dict[str, Any] | None:
    rows = [dict(row) for row in passing_rows]
    if not rows:
        return None
    mode = str(selector_mode)
    if mode == "baseline":
        return min(
            rows,
            key=lambda row: _selector_sort_key(
                row,
                selector_mode=mode,
                current_score=float(current_score),
                current_search_score=float(current_search_score),
            ),
        )
    if mode == "top_score_then_search":
        shortlist = score_band_shortlist(rows, score_eps=float(score_band_eps))
        return min(
            shortlist,
            key=lambda row: _selector_sort_key(
                row,
                selector_mode=mode,
                current_score=float(current_score),
                current_search_score=float(current_search_score),
            ),
        )
    if mode == "rescue_shallow_then_search":
        shortlist = [
            dict(row)
            for row in rows
            if str(row.get("landing_type", "current") or "current")
            not in {"current", "current_seed"}
        ]
        if not shortlist:
            shortlist = rows
        return min(
            shortlist,
            key=lambda row: _selector_sort_key(
                row,
                selector_mode=mode,
                current_score=float(current_score),
                current_search_score=float(current_search_score),
            ),
        )
    if mode == "score_band_then_lexical_then_search":
        shortlist = score_band_shortlist(rows, score_eps=float(score_band_eps))
        return min(
            shortlist,
            key=lambda row: _selector_sort_key(
                row,
                selector_mode=mode,
                current_score=float(current_score),
                current_search_score=float(current_search_score),
            ),
        )
    if mode == "gain_based":
        return min(
            rows,
            key=lambda row: _selector_sort_key(
                row,
                selector_mode=mode,
                current_score=float(current_score),
                current_search_score=float(current_search_score),
            ),
        )
    if mode == "pareto_shortlist":
        shortlist = pareto_shortlist(
            rows,
            current_score=float(current_score),
            current_search_score=float(current_search_score),
        )
        if not shortlist:
            shortlist = rows
        return min(
            shortlist,
            key=lambda row: _selector_sort_key(
                row,
                selector_mode=mode,
                current_score=float(current_score),
                current_search_score=float(current_search_score),
            ),
        )
    raise ValueError(f"unknown selector_mode={selector_mode!r}")
