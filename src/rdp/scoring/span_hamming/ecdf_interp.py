from __future__ import annotations

from typing import Sequence

import numpy as np


def fix_strict_increasing_breakpoints(bp: Sequence[float]) -> np.ndarray:
    out = np.asarray(bp, dtype=np.float64).copy()
    if out.ndim != 1:
        raise ValueError("breakpoints must be 1D")
    if out.size < 2:
        raise ValueError("breakpoints must contain at least 2 points")
    for i in range(1, out.size):
        if out[i] <= out[i - 1]:
            out[i] = np.nextafter(out[i - 1], np.inf)
    if not bool(np.all(np.diff(out) > 0.0)):
        raise ValueError("failed to enforce strictly increasing breakpoints")
    return out


def interp_pct(x: float, breakpoints: Sequence[float], q: Sequence[float]) -> float:
    xp = np.asarray(breakpoints, dtype=np.float64)
    qp = np.asarray(q, dtype=np.float64)
    if xp.ndim != 1 or qp.ndim != 1:
        raise ValueError("breakpoints and q must be 1D")
    if xp.size != qp.size:
        raise ValueError("breakpoints/q size mismatch")
    if xp.size < 2:
        raise ValueError("breakpoints and q must contain at least 2 points")
    if not bool(np.all(np.diff(xp) > 0.0)):
        raise ValueError("breakpoints must be strictly increasing")
    if not bool(np.all(np.diff(qp) > 0.0)):
        raise ValueError("q must be strictly increasing")
    return float(np.interp(float(x), xp, qp, left=float(qp[0]), right=float(qp[-1])))


def clamp_pct(p: float, clamp_min: float, clamp_max: float) -> float:
    p_min = float(clamp_min)
    p_max = float(clamp_max)
    if not (0.0 < p_min < p_max < 1.0):
        raise ValueError("clamp_min/clamp_max must satisfy 0 < min < max < 1")
    return float(np.clip(float(p), p_min, p_max))


def pct_to_energy(p: float) -> float:
    return float(-np.log1p(-float(p)))


def energy_to_pct(e: float) -> float:
    return float(1.0 - np.exp(-float(e)))


__all__ = [
    "fix_strict_increasing_breakpoints",
    "interp_pct",
    "clamp_pct",
    "pct_to_energy",
    "energy_to_pct",
]
