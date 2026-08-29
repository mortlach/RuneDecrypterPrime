from __future__ import annotations

def compute_hamming_weight(progress: float, w_max: float, ramp_start: float, ramp_end: float) -> float:
    """
    Piecewise-linear ramp:
      - 0 for tau < ramp_start
      - linear to w_max between ramp_start and ramp_end
      - w_max for tau >= ramp_end
    """
    try:
        tau = float(progress)
    except Exception:
        tau = 0.0
    try:
        w_m = float(w_max)
    except Exception:
        w_m = 0.0
    try:
        r0 = float(ramp_start)
        r1 = float(ramp_end)
    except Exception:
        r0, r1 = 0.0, 1.0
    if r1 < r0:
        r0, r1 = r1, r0
    if tau <= r0:
        return 0.0
    if tau >= r1:
        return w_m
    # interpolate
    frac = (tau - r0) / max(r1 - r0, 1e-9)
    return w_m * frac
