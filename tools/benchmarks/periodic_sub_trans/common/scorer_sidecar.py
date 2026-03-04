from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from rune_decrypter_prime.core.types import ObjectiveSpec
from rune_decrypter_prime.scoring.scorer_report_builder import build_scorer_report


def _objective_string_from_scorer(scorer: Any, fallback: str) -> str:
    obj = getattr(scorer, "objective", None)
    if isinstance(obj, str) and obj.strip():
        return obj.strip()
    if isinstance(obj, Mapping):
        family = obj.get("family")
        stat = obj.get("stat")
        win = obj.get("win")
    elif isinstance(obj, ObjectiveSpec):
        family = obj.family
        stat = obj.stat
        win = obj.win
    else:
        return fallback

    fam_text = getattr(family, "value", family)
    stat_text = getattr(stat, "value", stat) if stat is not None else None
    if fam_text is None:
        return fallback
    parts = [str(fam_text)]
    if stat_text is not None:
        parts.append(str(stat_text))
    if win is not None:
        parts.append(f"win{int(win)}")
    return ".".join(parts)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return str(value)


def append_scorer_report_jsonl(
    path: Path,
    *,
    scorer: Any,
    score: float,
    raw_score: float | None = None,
    cost_ms: float | None = None,
    objective_str: str = "pct.logp.win10",
    extra_metrics: Mapping[str, float] | None = None,
    extra_details: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective_text = _objective_string_from_scorer(scorer, objective_str)
    report = build_scorer_report(
        scorer=scorer,
        objective_str=objective_text,
        score=float(score),
        raw_score=(None if raw_score is None else float(raw_score)),
        cost_ms=(None if cost_ms is None else float(cost_ms)),
        extra_metrics=extra_metrics,
        extra_details=extra_details,
    )
    row: dict[str, Any] = {"report": report.to_json_dict()}
    if context:
        row["context"] = _json_safe(dict(context))

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=True) + "\n")
    return row
