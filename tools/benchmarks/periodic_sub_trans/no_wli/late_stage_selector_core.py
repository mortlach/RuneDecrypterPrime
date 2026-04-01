from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, Mapping, Sequence


SUPPORTED_STAGE35_BASELINE_SELECTORS: tuple[str, ...] = (
    "legacy",
    "score_plus_novelty",
)


def _safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float(default)
    return float(out)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _finite_or_zero(value: Any) -> float:
    out = _safe_float(value)
    return float(out) if math.isfinite(out) else 0.0


def _key_tuple(value: Any) -> tuple[int, ...]:
    return tuple(int(x) for x in list(value or []))


def normalize_stage35_baseline_selector(selector: str | None) -> str:
    normalized = str(selector or "").strip().lower()
    if not normalized:
        normalized = "legacy"
    if normalized not in SUPPORTED_STAGE35_BASELINE_SELECTORS:
        allowed = ", ".join(SUPPORTED_STAGE35_BASELINE_SELECTORS)
        raise ValueError(
            f"unsupported Stage 3.5 baseline selector '{normalized}'; "
            f"expected one of: {allowed}"
        )
    return normalized


@dataclass(frozen=True)
class ScorePlusNoveltySelectorConfig:
    final_score_weight: float = 1.0
    score_gain_weight: float = 0.75
    novelty_distance_weight: float = 0.0001
    eligible_novel_bonus: float = 0.005
    non_anchor_bonus: float = 0.015
    phasea_selected_bonus: float = 0.003
    source_rank_penalty_weight: float = 0.002
    anchor_penalty: float = 0.01


def build_score_plus_novelty_selector_config() -> ScorePlusNoveltySelectorConfig:
    return ScorePlusNoveltySelectorConfig()


def normalize_phasec_live_selector_row(row_obj: Mapping[str, Any]) -> Dict[str, Any]:
    row = dict(row_obj or {})
    lane = str(row.get("lane", "") or "")
    source = str(row.get("source", "") or "")
    return dict(
        start_idx=_safe_int(row.get("start_idx", 0), 0),
        lane=lane,
        source=source,
        source_rank=_safe_int(row.get("source_rank", 0), 0),
        candidate_hash=str(row.get("candidate_hash", "") or ""),
        final_key_idx=list(map(int, row.get("final_key_idx", []) or [])),
        final_plaintext_idx=list(map(int, row.get("final_plaintext_idx", []) or [])),
        final_score=(
            float(_safe_float(row.get("final_score")))
            if math.isfinite(_safe_float(row.get("final_score")))
            else None
        ),
        final_match=(
            float(_safe_float(row.get("final_match")))
            if math.isfinite(_safe_float(row.get("final_match")))
            else None
        ),
        score_gain=(
            float(_safe_float(row.get("score_gain")))
            if math.isfinite(_safe_float(row.get("score_gain")))
            else None
        ),
        eligible_novel_challenger=_safe_int(
            row.get("eligible_novel_challenger", 0),
            0,
        ),
        novelty_distance_to_anchor=(
            _safe_int(row.get("novelty_distance_to_anchor"))
            if row.get("novelty_distance_to_anchor", None) is not None
            else None
        ),
        is_anchor=int(1 if lane == "anchor" else 0),
        is_non_anchor=int(1 if lane != "anchor" else 0),
        is_phasea_selected=int(1 if source == "phaseA_selected" else 0),
    )


def _legacy_sort_key(row_obj: Mapping[str, Any]) -> tuple[float, float, int]:
    row = normalize_phasec_live_selector_row(row_obj)
    final_score = _safe_float(row.get("final_score"), float("-inf"))
    final_match = _safe_float(row.get("final_match"), float("-inf"))
    source_rank = _safe_int(row.get("source_rank", 0), 0)
    return (
        final_score if math.isfinite(final_score) else float("-inf"),
        final_match if math.isfinite(final_match) else float("-inf"),
        -int(source_rank),
    )


def select_legacy_phasec_winner_row(
    phasec_start_summaries: Sequence[Mapping[str, Any]] | None,
) -> Dict[str, Any]:
    rows = [
        normalize_phasec_live_selector_row(row)
        for row in list(phasec_start_summaries or [])
        if isinstance(row, Mapping)
    ]
    return dict(max(rows, key=_legacy_sort_key, default={}))


def select_phasec_score_winner_row(
    *,
    phasec_start_summaries: Sequence[Mapping[str, Any]] | None,
    best3_key: Sequence[int] | None,
    phasec_final_winner_lane: str = "",
    phasec_final_winner_source: str = "",
) -> Dict[str, Any]:
    rows = [
        normalize_phasec_live_selector_row(row)
        for row in list(phasec_start_summaries or [])
        if isinstance(row, Mapping)
    ]
    if not rows:
        return {}
    best3_key_t = _key_tuple(best3_key)
    if best3_key_t:
        key_matches = [
            dict(row)
            for row in rows
            if _key_tuple(row.get("final_key_idx", [])) == best3_key_t
        ]
        if key_matches:
            return dict(max(key_matches, key=_legacy_sort_key))
    lane = str(phasec_final_winner_lane or "")
    source = str(phasec_final_winner_source or "")
    if lane or source:
        matching_rows = [
            dict(row)
            for row in rows
            if str(row.get("lane", "") or "") == lane
            and str(row.get("source", "") or "") == source
        ]
        if matching_rows:
            return dict(max(matching_rows, key=_legacy_sort_key))
    return select_legacy_phasec_winner_row(rows)


def score_plus_novelty_phasec_row(
    row_obj: Mapping[str, Any],
    *,
    config: ScorePlusNoveltySelectorConfig | None = None,
) -> float:
    cfg = config or build_score_plus_novelty_selector_config()
    row = normalize_phasec_live_selector_row(row_obj)
    score = 0.0
    score += cfg.final_score_weight * _finite_or_zero(row.get("final_score"))
    score += cfg.score_gain_weight * _finite_or_zero(row.get("score_gain"))
    score += cfg.novelty_distance_weight * float(
        max(_safe_int(row.get("novelty_distance_to_anchor", 0), 0), 0)
    )
    score += cfg.eligible_novel_bonus * float(
        _safe_int(row.get("eligible_novel_challenger", 0), 0)
    )
    score += cfg.non_anchor_bonus * float(_safe_int(row.get("is_non_anchor", 0), 0))
    score += cfg.phasea_selected_bonus * float(
        _safe_int(row.get("is_phasea_selected", 0), 0)
    )
    score -= cfg.source_rank_penalty_weight * float(
        max(_safe_int(row.get("source_rank", 1), 1) - 1, 0)
    )
    score -= cfg.anchor_penalty * float(_safe_int(row.get("is_anchor", 0), 0))
    return float(score)


def select_score_plus_novelty_phasec_row(
    phasec_start_summaries: Sequence[Mapping[str, Any]] | None,
    *,
    config: ScorePlusNoveltySelectorConfig | None = None,
) -> Dict[str, Any]:
    cfg = config or build_score_plus_novelty_selector_config()
    rows = [
        normalize_phasec_live_selector_row(row)
        for row in list(phasec_start_summaries or [])
        if isinstance(row, Mapping)
    ]
    scored_rows: list[Dict[str, Any]] = []
    for row in rows:
        row_out = dict(row)
        row_out["experimental_score"] = score_plus_novelty_phasec_row(
            row_out,
            config=cfg,
        )
        scored_rows.append(row_out)
    return dict(
        max(
            scored_rows,
            key=lambda row: (
                _safe_float(row.get("experimental_score"), float("-inf")),
                _safe_float(row.get("final_score"), float("-inf")),
                _safe_float(row.get("final_match"), float("-inf")),
                -_safe_int(row.get("source_rank", 0), 0),
            ),
            default={},
        )
    )


def select_stage35_baseline_row(
    *,
    phasec_start_summaries: Sequence[Mapping[str, Any]] | None,
    selector: str | None,
    phasec_score_winner_row: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    selector_name = normalize_stage35_baseline_selector(selector)
    if selector_name == "legacy":
        return dict(phasec_score_winner_row or {})
    return select_score_plus_novelty_phasec_row(phasec_start_summaries)
