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

RESERVED_DETAIL_KEYS = frozenset({
    "hamming_dictionary",
    "span_hamming",
    "span_lm",
    "word_ngrams",
    "scorer_lanes",
    "stop_reason",
    "stop_category",
    "oracle_use",
    "truth_data_policy",
    "report_contract",
})

REPORT_BUILDER_DIAGNOSTICS_KEY = "report_builder_diagnostics"


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
        except (TypeError, ValueError):
            continue
        if not math.isfinite(f):
            continue
        out[str(k)] = f
    return out


def _section_from_prefix(data: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in data.items():
        key = str(k)
        if key.startswith(prefix):
            out[key[len(prefix):]] = v
    return out


def _derived_details_from_telemetry(telemetry: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}

    span_hamming = _section_from_prefix(telemetry, "span_hamming_")
    if span_hamming:
        out["span_hamming"] = span_hamming

    word_ngrams = _section_from_prefix(telemetry, "word_ngram_judge_")
    if word_ngrams:
        out["word_ngrams"] = word_ngrams

    span_lm = _section_from_prefix(telemetry, "span_lm_")
    if span_lm:
        out["span_lm"] = span_lm

    hamming_dictionary: dict[str, Any] = {}
    for key in (
        "hamming_dictionary_policy",
        "span_hamming_dictionary_policy",
        "span_hamming_assets_dictionary_policy",
        "span_hamming_dictionary_policy_match",
        "span_hamming_dictionary_policy_note",
    ):
        if key in telemetry:
            hamming_dictionary[key] = telemetry[key]
    if hamming_dictionary:
        out["hamming_dictionary"] = hamming_dictionary

    return out


def _merge_detail_sections(
    base: Mapping[str, Any],
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    out = _safe_mapping(base)
    for key, value in _safe_mapping(extra).items():
        if key in out and key in RESERVED_DETAIL_KEYS:
            raise ValueError(f"extra_details cannot overwrite generated report detail section: {key}")
        if key in out and isinstance(out[key], Mapping) and isinstance(value, Mapping):
            merged = dict(out[key])
            merged.update(dict(value))
            out[key] = merged
        else:
            out[key] = value
    return out


def _exception_diagnostic(exc: Exception) -> dict[str, str]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
    }


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

    diagnostics: dict[str, Any] = {}
    telemetry: dict[str, Any] = {}
    try:
        if hasattr(scorer, "telemetry") and callable(scorer.telemetry):
            telemetry = _safe_mapping(scorer.telemetry())
    except Exception as exc:  # pragma: no cover - exact exception type is scorer-defined
        diagnostics["telemetry_error"] = _exception_diagnostic(exc)
        telemetry = {}

    metrics: dict[str, float] = {}
    try:
        if hasattr(scorer, "last_stats") and callable(scorer.last_stats):
            metrics.update(_safe_float_metrics(scorer.last_stats()))
    except Exception as exc:  # pragma: no cover - exact exception type is scorer-defined
        diagnostics["last_stats_error"] = _exception_diagnostic(exc)
    metrics.update(_safe_float_metrics(extra_metrics or {}))

    derived_details = _derived_details_from_telemetry(telemetry)
    if diagnostics:
        derived_details[REPORT_BUILDER_DIAGNOSTICS_KEY] = diagnostics
    details = _merge_detail_sections(derived_details, _safe_mapping(extra_details or {}))
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
