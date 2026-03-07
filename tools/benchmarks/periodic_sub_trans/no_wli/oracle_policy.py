from __future__ import annotations

from typing import Tuple

import numpy as np


def derive_stage3_phaseb_char_pct_min(
    *,
    stage3_phase_switch_enabled: bool,
    stage3_phaseb_experiment: str,
    oracle_s3: float,
    scoring_experiment_c_char_pct_min: float,
    stage3_span_char_pct_min_override: float | None,
) -> Tuple[float, str, bool]:
    """Derive Phase-B char_pct_min policy without mutating runtime behavior."""
    value = float("nan")
    source = "not_used_explicit_basin_judge"
    should_emit = False
    if bool(stage3_phase_switch_enabled) and str(stage3_phaseb_experiment) == "c_min_late":
        should_emit = True
        if np.isfinite(float(oracle_s3)):
            value = float(np.clip(float(oracle_s3) - 0.10, 0.30, 0.45))
            source = "oracle_minus_0.10_clamp_0.30_0.45_not_applied"
        else:
            value = float(scoring_experiment_c_char_pct_min)
            source = "profile_default_not_applied"
        if stage3_span_char_pct_min_override is not None:
            value = float(stage3_span_char_pct_min_override)
            source = "diagnostic_override_not_applied"
    return value, source, bool(should_emit)
