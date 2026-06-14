from __future__ import annotations

import math
from enum import StrEnum
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


class ScorerReportDetailKey(StrEnum):
    HAMMING_DICTIONARY = "hamming_dictionary"
    SPAN_HAMMING = "span_hamming"
    SPAN_LM = "span_lm"
    WORD_NGRAMS = "word_ngrams"
    SCORER_LANES = "scorer_lanes"
    STOP_REASON = "stop_reason"
    STOP_CATEGORY = "stop_category"
    ORACLE_USE = "oracle_use"
    TRUTH_DATA_POLICY = "truth_data_policy"
    REPORT_CONTRACT = "report_contract"
    REPORT_BUILDER_DIAGNOSTICS = "report_builder_diagnostics"


class ReportBuilderDiagnosticKey(StrEnum):
    TELEMETRY_ERROR = "telemetry_error"
    LAST_STATS_ERROR = "last_stats_error"


class DiagnosticField(StrEnum):
    TYPE = "type"
    MESSAGE = "message"


class ScorerTelemetryPrefix(StrEnum):
    SPAN_HAMMING = "span_hamming_"
    WORD_NGRAM_JUDGE = "word_ngram_judge_"
    SPAN_LM = "span_lm_"


class ScorerTelemetryKey(StrEnum):
    HAMMING_DICTIONARY_POLICY = "hamming_dictionary_policy"
    SPAN_HAMMING_DICTIONARY_POLICY = "span_hamming_dictionary_policy"
    SPAN_HAMMING_ASSETS_DICTIONARY_POLICY = "span_hamming_assets_dictionary_policy"
    SPAN_HAMMING_DICTIONARY_POLICY_MATCH = "span_hamming_dictionary_policy_match"
    SPAN_HAMMING_DICTIONARY_POLICY_NOTE = "span_hamming_dictionary_policy_note"


REPORT_BUILDER_DIAGNOSTICS_KEY = ScorerReportDetailKey.REPORT_BUILDER_DIAGNOSTICS.value

RESERVED_DETAIL_KEYS = frozenset(key.value for key in ScorerReportDetailKey)
CALLER_FORBIDDEN_DETAIL_KEYS = frozenset({ScorerReportDetailKey.REPORT_BUILDER_DIAGNOSTICS.value})


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

    span_hamming = _section_from_prefix(telemetry, ScorerTelemetryPrefix.SPAN_HAMMING.value)
    if span_hamming:
        out[ScorerReportDetailKey.SPAN_HAMMING.value] = span_hamming

    word_ngrams = _section_from_prefix(telemetry, ScorerTelemetryPrefix.WORD_NGRAM_JUDGE.value)
    if word_ngrams:
        out[ScorerReportDetailKey.WORD_NGRAMS.value] = word_ngrams

    span_lm = _section_from_prefix(telemetry, ScorerTelemetryPrefix.SPAN_LM.value)
    if span_lm:
        out[ScorerReportDetailKey.SPAN_LM.value] = span_lm

    hamming_dictionary: dict[str, Any] = {}
    for key in ScorerTelemetryKey:
        if key.value in telemetry:
            hamming_dictionary[key.value] = telemetry[key.value]
    if hamming_dictionary:
        out[ScorerReportDetailKey.HAMMING_DICTIONARY.value] = hamming_dictionary

    return out


def _merge_detail_sections(
    base: Mapping[str, Any],
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    out = _safe_mapping(base)
    for key, value in _safe_mapping(extra).items():
        if key in CALLER_FORBIDDEN_DETAIL_KEYS:
            raise ValueError(f"extra_details cannot supply generated report detail section: {key}")
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
        DiagnosticField.TYPE.value: type(exc).__name__,
        DiagnosticField.MESSAGE.value: str(exc),
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
        diagnostics[ReportBuilderDiagnosticKey.TELEMETRY_ERROR.value] = _exception_diagnostic(exc)
        telemetry = {}

    metrics: dict[str, float] = {}
    try:
        if hasattr(scorer, "last_stats") and callable(scorer.last_stats):
            metrics.update(_safe_float_metrics(scorer.last_stats()))
    except Exception as exc:  # pragma: no cover - exact exception type is scorer-defined
        diagnostics[ReportBuilderDiagnosticKey.LAST_STATS_ERROR.value] = _exception_diagnostic(exc)
    metrics.update(_safe_float_metrics(extra_metrics or {}))

    derived_details = _derived_details_from_telemetry(telemetry)
    if diagnostics:
        derived_details[ScorerReportDetailKey.REPORT_BUILDER_DIAGNOSTICS.value] = diagnostics
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
