from __future__ import annotations

import math
from typing import Any, Mapping

from rune_decrypter_prime.core.types import (
    ObjectiveFamily,
    ObjectiveSpec,
    Stat,
    ensure_objective_family,
    ensure_stat,
)
from rune_decrypter_prime.scoring.base_scorer import parse_objective
from rune_decrypter_prime.scoring.scorer_report import ScorerReport


def _objective_spec_from_any(value: Any, *, fallback_win: int = 10) -> ObjectiveSpec:
    if isinstance(value, ObjectiveSpec):
        fam = ensure_objective_family(value.family)
        stat = ensure_stat(value.stat) if value.stat is not None else None
        win = int(value.win) if value.win is not None else None
        if fam in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
            if stat is None:
                stat = Stat.LOGP
            if win is None:
                win = int(fallback_win)
        if fam is ObjectiveFamily.AVG:
            if stat is None:
                stat = Stat.LOGP
            if win is None:
                win = int(fallback_win)
        return ObjectiveSpec(family=fam, stat=stat, win=win)

    if isinstance(value, Mapping):
        fam = ensure_objective_family(value.get("family", ObjectiveFamily.PCT))
        stat_raw = value.get("stat")
        stat = ensure_stat(stat_raw) if stat_raw is not None else None
        win_raw = value.get("win")
        win = int(win_raw) if win_raw is not None else None
        return _objective_spec_from_any(
            ObjectiveSpec(family=fam, stat=stat, win=win),
            fallback_win=fallback_win,
        )

    if isinstance(value, str):
        fam_raw, stat_raw, win_raw = parse_objective(value)
        fam = ensure_objective_family(fam_raw)
        stat = ensure_stat(stat_raw) if stat_raw is not None else None
        win = int(win_raw) if win_raw is not None else None
        return _objective_spec_from_any(
            ObjectiveSpec(family=fam, stat=stat, win=win),
            fallback_win=fallback_win,
        )

    return ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=int(fallback_win))


def _safe_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(k): v for k, v in value.items()}
    return {}


def _safe_float_metrics(value: Any) -> dict[str, float]:
    out: dict[str, float] = {}
    if not isinstance(value, Mapping):
        return out
    for k, v in value.items():
        try:
            f = float(v)
        except Exception:
            continue
        if not math.isfinite(f):
            continue
        out[str(k)] = f
    return out


def build_scorer_report(
    *,
    scorer: Any,
    objective_str: str,
    score: float,
    raw_score: float | None = None,
    cost_ms: float | None = None,
    extra_metrics: Mapping[str, float] | None = None,
    extra_details: Mapping[str, Any] | None = None,
) -> ScorerReport:
    fallback_win = int(getattr(scorer, "win", 10) or 10)
    objective_raw = objective_str or getattr(scorer, "objective", None)
    objective_spec = _objective_spec_from_any(objective_raw, fallback_win=fallback_win)

    telemetry: dict[str, Any] = {}
    try:
        if hasattr(scorer, "telemetry") and callable(scorer.telemetry):
            telemetry = _safe_mapping(scorer.telemetry())
    except Exception:
        telemetry = {}

    metrics: dict[str, float] = {}
    try:
        if hasattr(scorer, "last_stats") and callable(scorer.last_stats):
            metrics.update(_safe_float_metrics(scorer.last_stats()))
    except Exception:
        pass
    metrics.update(_safe_float_metrics(extra_metrics or {}))

    details = _safe_mapping(extra_details or {})
    return ScorerReport(
        objective_str=str(objective_str or ""),
        objective_spec=objective_spec,
        score=float(score),
        raw_score=(float(raw_score) if raw_score is not None else None),
        telemetry=telemetry,
        metrics=metrics,
        cost_ms=(float(cost_ms) if cost_ms is not None else None),
        details=details,
    )

