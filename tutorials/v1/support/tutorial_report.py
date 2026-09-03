from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA = "rdp_tutorial_run_report.v1"


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes, Path, Mapping)):
        return []
    if hasattr(value, "tolist"):
        try:
            return list(value.tolist())
        except Exception:
            return []
    if isinstance(value, Sequence):
        return list(value)
    return []


def _int_list(value: Any) -> list[int] | None:
    items = _as_list(value)
    if not items:
        return None
    try:
        return [int(item) for item in items]
    except Exception:
        return None


def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        item = int(value)
    except Exception:
        return None
    return item if item >= 0 else None


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _preview_text(value: Any, limit: int) -> str:
    text = "" if value is None else str(value)
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"


def _match_ratio(found: Any, reference: Any) -> float | None:
    found_items = _int_list(found)
    ref_items = _int_list(reference)
    if not found_items or not ref_items:
        return None
    denom = max(len(found_items), len(ref_items))
    if denom <= 0:
        return None
    limit = min(len(found_items), len(ref_items))
    return sum(1 for idx in range(limit) if found_items[idx] == ref_items[idx]) / float(denom)


def _report_json(solver_report: Any) -> dict[str, Any]:
    if solver_report is None:
        return {}
    if hasattr(solver_report, "to_json_dict"):
        data = solver_report.to_json_dict()
        return dict(data) if isinstance(data, Mapping) else {}
    return _as_dict(solver_report)


def _summary_json(summary: Any) -> dict[str, Any]:
    if summary is None:
        return {}
    if hasattr(summary, "to_json_dict"):
        data = summary.to_json_dict()
        return dict(data) if isinstance(data, Mapping) else {}
    return _as_dict(summary)


def _compact_mapping(data: Mapping[str, Any], allowed: Sequence[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in allowed:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, (str, bool, int, float)):
            out[key] = value
    return out


def _scorer_lanes_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, list):
        return {"lanes": list(value)}
    return {}


def build_tutorial_run_report(
    *,
    title: str,
    cipher: str,
    solution: Any,
    solver_report: Any = None,
    benchmark_summary: Any = None,
    match_ok: bool | None = None,
    app_version: str | None = None,
    key_idx: Sequence[int] | None = None,
    key_len: int | None = None,
    ct_idx: Sequence[int] | None = None,
    ct_rune: str | None = None,
    pt_rune_ref: str | None = None,
    pt_idx_ref: Sequence[int] | None = None,
    preview_len: int = 160,
) -> dict[str, Any]:
    """Return a compact, JSON-safe tutorial report payload.

    The payload is intentionally small and stable.  It is for tutorial display
    and release evidence, not for replaying a run.  Full solver details remain
    in the solver report object/file.
    """
    report = _report_json(solver_report)
    benchmark = _summary_json(benchmark_summary)
    details = _as_dict(report.get("details"))
    meta = _as_dict(getattr(solution, "meta", None))
    telemetry = _as_dict(meta.get("telemetry"))

    found_key = _int_list(getattr(solution, "key", None))
    expected_key = _int_list(key_idx)
    plaintext_idx = _int_list(
        getattr(solution, "plaintext_idx", getattr(solution, "plaintext", None))
    )
    ratio = _first_present(benchmark.get("match_ratio"), _match_ratio(plaintext_idx, pt_idx_ref))
    recovered = bool(match_ok) if match_ok is not None else (None if ratio is None else float(ratio) >= 0.97)

    solver_section = {
        "name": _first_present(
            report.get("solver"), _as_dict(meta.get("solver")).get("name")
        ),
        "stop_reason": _first_present(
            _as_dict(report.get("status")).get("stop_reason"),
            getattr(solution, "stop_reason", None),
        ),
        "score": _safe_float(
            _first_present(report.get("best_score"), getattr(solution, "score", None))
        ),
        "step": _safe_int(
            _first_present(report.get("steps"), getattr(solution, "step", None))
        ),
        "evals": _safe_int(
            _first_present(report.get("evaluations"), getattr(solution, "evals", None))
        ),
        "tokens_processed": _safe_int(
            _first_present(report.get("tokens_processed"), getattr(solution, "tokens_processed", None))
        ),
    }
    solver_section = {key: value for key, value in solver_section.items() if value is not None}

    timings = _compact_mapping(
        {
            "wall_time_s": _first_present(
                report.get("wall_time_seconds"),
                getattr(solution, "wall_time_s", None),
            ),
            "decrypt_time_s": _first_present(
                report.get("decrypt_time_seconds"),
                getattr(solution, "decrypt_time_s", None),
            ),
            "score_time_s": _first_present(
                report.get("score_time_seconds"),
                getattr(solution, "score_time_s", None),
            ),
        },
        ("wall_time_s", "decrypt_time_s", "score_time_s"),
    )

    key_section: dict[str, Any] = {
        "length": key_len if key_len is not None else (len(found_key) if found_key is not None else None),
        "expected": expected_key,
        "found": found_key,
    }
    if expected_key is not None and found_key is not None:
        key_section["exact"] = found_key == expected_key
    key_section = {key: value for key, value in key_section.items() if value is not None}

    scorer_lanes = _scorer_lanes_payload(details.get("scorer_lanes", meta.get("scorer_lanes")))

    return {
        "schema": SCHEMA,
        "title": str(title),
        "app_version": app_version,
        "cipher": str(cipher),
        "recovered": recovered,
        "match_ratio": ratio,
        "solver": solver_section,
        "key": key_section,
        "benchmark": benchmark,
        "timings_s": timings,
        "telemetry": {"present": bool(telemetry)},
        "solver_report": {
            "present": bool(report),
            "stop_category": _as_dict(report.get("status")).get("stop_category"),
            "scorer_lanes": scorer_lanes,
        },
        "previews": {
            "ciphertext_runes": _preview_text(ct_rune, preview_len),
            "plaintext_runes": _preview_text(getattr(solution, "plaintext_rune", ""), preview_len),
            "reference_runes": _preview_text(pt_rune_ref, preview_len),
            "ciphertext_idx_head": (_int_list(ct_idx) or [])[:32],
            "plaintext_idx_head": (plaintext_idx or [])[:32],
        },
    }


def render_tutorial_run_report(report: Mapping[str, Any]) -> list[str]:
    """Render the compact tutorial report as deterministic console lines."""
    solver = _as_dict(report.get("solver"))
    key = _as_dict(report.get("key"))
    benchmark = _as_dict(report.get("benchmark"))
    solver_report = _as_dict(report.get("solver_report"))
    timings = _as_dict(report.get("timings_s"))
    previews = _as_dict(report.get("previews"))

    line = "─" * 72
    lines = [
        line,
        f"RDP tutorial report · {report.get('title', '')}",
        line,
        f"schema      : {report.get('schema')}",
        f"cipher      : {report.get('cipher')}",
        f"recovered   : {report.get('recovered')}",
    ]
    if report.get("match_ratio") is not None:
        lines.append(f"match_ratio : {float(report['match_ratio']):.3f}")
    if solver:
        lines.append(f"solver      : {solver}")
    if key:
        lines.append(f"key         : {key}")
    if benchmark:
        lines.append(f"benchmark  : {benchmark}")
    if timings:
        lines.append(f"timings_s   : {timings}")
    if solver_report:
        lines.append(f"report      : {solver_report}")
    if previews.get("plaintext_runes"):
        lines.extend(["plaintext   :", str(previews["plaintext_runes"])])
    if previews.get("reference_runes"):
        lines.extend(["reference   :", str(previews["reference_runes"])])
    app_version = report.get("app_version")
    if app_version:
        lines.append(f"app_version : {app_version}")
    lines.append(line)
    return lines


def print_tutorial_run_report(**kwargs: Any) -> dict[str, Any]:
    """Build, print, and return the compact tutorial report payload."""
    report = build_tutorial_run_report(**kwargs)
    for line in render_tutorial_run_report(report):
        print(line)
    return report


__all__ = [
    "SCHEMA",
    "build_tutorial_run_report",
    "print_tutorial_run_report",
    "render_tutorial_run_report",
]
