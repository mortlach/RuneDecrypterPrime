from __future__ import annotations

import math
from typing import Any, Mapping


def select_stage3_band(
    *,
    dynamic_bands: list[Mapping[str, Any]],
    gap_to_oracle: float,
) -> dict[str, Any]:
    gap = float(gap_to_oracle)
    for band in dynamic_bands:
        if gap <= float(band.get("max_gap", 1e9)):
            return dict(band)
    if not dynamic_bands:
        return {}
    return dict(dynamic_bands[-1])


def select_stage3_default_band(
    *,
    dynamic_bands: list[Mapping[str, Any]],
    preferred_name: str = "mid",
) -> dict[str, Any]:
    preferred = str(preferred_name).strip().lower()
    for band in dynamic_bands:
        if str(band.get("name", "")).strip().lower() == preferred:
            return dict(band)
    if not dynamic_bands:
        return {}
    return dict(dynamic_bands[-1])


def resolve_stage3_gap_and_band(
    *,
    dynamic_bands: list[Mapping[str, Any]],
    stage2_gate_score: float,
    oracle_stage3_score: float,
    oracle_decision_paths_enabled: bool,
) -> tuple[float, dict[str, Any], bool]:
    if (
        bool(oracle_decision_paths_enabled)
        and math.isfinite(float(stage2_gate_score))
        and math.isfinite(float(oracle_stage3_score))
    ):
        gap = max(0.0, float(oracle_stage3_score) - float(stage2_gate_score))
        return gap, select_stage3_band(dynamic_bands=dynamic_bands, gap_to_oracle=gap), True
    gap = float("nan")
    return gap, select_stage3_default_band(dynamic_bands=dynamic_bands), False
