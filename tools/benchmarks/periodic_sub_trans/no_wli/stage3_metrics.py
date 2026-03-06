from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


def extract_kaeding_metrics(kaeding_obj: Any) -> Dict[str, float]:
    if not isinstance(kaeding_obj, dict):
        return dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        )
    slip_count = int(kaeding_obj.get("slip_count", 0) or 0)
    accept_rate = float(kaeding_obj.get("accept_rate", float("nan")))
    slips_list = kaeding_obj.get("slips", [])
    slip_accept_count = 0
    if isinstance(slips_list, list):
        for rec in slips_list:
            if not isinstance(rec, dict):
                continue
            raw_before = float(rec.get("raw_before", float("nan")))
            raw_after = float(rec.get("raw_after", float("nan")))
            if np.isfinite(raw_before) and np.isfinite(raw_after) and raw_after > raw_before:
                slip_accept_count += 1
    slip_accept_rate = float(slip_accept_count) / float(max(1, slip_count)) if slip_count > 0 else float("nan")
    phase_attempts_total = 0
    phase_improves_total = 0
    phase_best_delta_max = float("nan")
    per_phase = kaeding_obj.get("per_phase", {})
    if isinstance(per_phase, dict) and per_phase:
        delta_vals: List[float] = []
        for rec in per_phase.values():
            if not isinstance(rec, dict):
                continue
            phase_attempts_total += int(rec.get("attempts", 0) or 0)
            phase_improves_total += int(rec.get("improves", 0) or 0)
            d = rec.get("best_delta_raw", None)
            if d is not None and np.isfinite(float(d)):
                delta_vals.append(float(d))
        if delta_vals:
            phase_best_delta_max = float(max(delta_vals))
    return dict(
        slip_count=int(slip_count),
        slip_accept_count=int(slip_accept_count),
        slip_accept_rate=float(slip_accept_rate),
        accept_rate=float(accept_rate),
        phase_attempts_total=int(phase_attempts_total),
        phase_improves_total=int(phase_improves_total),
        phase_best_delta_max=float(phase_best_delta_max),
    )
