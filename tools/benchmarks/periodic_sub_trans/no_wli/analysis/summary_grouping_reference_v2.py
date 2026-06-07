from __future__ import annotations

"""Reference summary grouping for strict O3 known-damage calibration outputs."""

import math
from dataclasses import dataclass
from statistics import median
from typing import Any, Iterable, Mapping


def actual_changed_fraction_bin(value: float | str, *, width: float = 0.10) -> str:
    if value == "" or value is None:
        return ""
    x = float(value)
    if x < 0.0:
        raise ValueError("changed fraction must be non-negative")
    lower = math.floor((x + 1e-12) / width) * width
    upper = lower + width
    return f"{lower:.2f}-{upper:.2f}"


def null_class_for_row(row: Mapping[str, Any]) -> str:
    existing = str(row.get("null_class", "") or "")
    if existing:
        return existing
    source_kind = str(row.get("source_kind", "") or "")
    model = str(row.get("model_name", row.get("damage_model", row.get("null_model", ""))) or "")
    if source_kind == "clean" or model == "clean":
        return "clean"
    if source_kind == "damaged" or model.endswith("substitution"):
        return "damaged"
    if model.startswith("block_shuffle_"):
        return "hard_local_order_control"
    if model in {"uniform_random", "global_frequency_random", "within_chunk_shuffle"}:
        return "ordinary_null"
    return source_kind or "unknown"


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * q))
    return float(ordered[max(0, min(len(ordered) - 1, idx))])


def _stats(values: list[float], prefix: str) -> dict[str, Any]:
    if not values:
        return {
            f"{prefix}_mean": "",
            f"{prefix}_stddev": "",
            f"{prefix}_stderr": "",
            f"{prefix}_ci95_low": "",
            f"{prefix}_ci95_high": "",
            f"{prefix}_min": "",
            f"{prefix}_p10": "",
            f"{prefix}_median": "",
            f"{prefix}_p90": "",
            f"{prefix}_max": "",
        }
    n = len(values)
    mean = sum(values) / float(n)
    var = sum((x - mean) ** 2 for x in values) / float(max(1, n - 1))
    stddev = math.sqrt(max(0.0, var)) if n > 1 else 0.0
    stderr = stddev / math.sqrt(float(n)) if n else 0.0
    ci = 1.96 * stderr
    return {
        f"{prefix}_mean": f"{mean:.12g}",
        f"{prefix}_stddev": f"{stddev:.12g}",
        f"{prefix}_stderr": f"{stderr:.12g}",
        f"{prefix}_ci95_low": f"{mean - ci:.12g}",
        f"{prefix}_ci95_high": f"{mean + ci:.12g}",
        f"{prefix}_min": f"{min(values):.12g}",
        f"{prefix}_p10": f"{_quantile(values, 0.10):.12g}",
        f"{prefix}_median": f"{median(values):.12g}",
        f"{prefix}_p90": f"{_quantile(values, 0.90):.12g}",
        f"{prefix}_max": f"{max(values):.12g}",
    }


def calibration_summary_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in rows:
        lens = str(row.get("lens_name", ""))
        source_kind = str(row.get("source_kind", ""))
        model = str(row.get("model_name", row.get("damage_model", row.get("null_model", ""))) or "")
        null_class = null_class_for_row(row)
        requested = str(row.get("requested_damage_level", row.get("damage_level", "")) or "")
        changed = _float_or_none(row.get("actual_changed_fraction", row.get("changed_fraction", "")))
        changed_bin = actual_changed_fraction_bin(changed) if changed is not None else ""
        key = (lens, source_kind, model, null_class, requested, changed_bin)
        bucket = groups.setdefault(key, {"selected_weight": [], "changed_fraction": []})
        selected = _float_or_none(row.get("selected_weight", row.get("selected_weight_sum", "")))
        if selected is not None:
            bucket["selected_weight"].append(selected)
        if changed is not None:
            bucket["changed_fraction"].append(changed)

    out: list[dict[str, Any]] = []
    for key in sorted(groups):
        lens, source_kind, model, null_class, requested, changed_bin = key
        bucket = groups[key]
        out.append(
            {
                "lens_name": lens,
                "source_kind": source_kind,
                "model_name": model,
                "null_class": null_class,
                "requested_damage_level": requested,
                "actual_changed_fraction_bin": changed_bin,
                "count": len(bucket["selected_weight"]),
                **_stats(bucket["selected_weight"], "selected_weight"),
                **_stats(bucket["changed_fraction"], "changed_fraction"),
            }
        )
    return out
