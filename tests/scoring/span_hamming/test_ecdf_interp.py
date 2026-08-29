from __future__ import annotations
import numpy as np
import pytest
from rune_decrypter_prime.scoring.span_hamming.ecdf_interp import (
    clamp_pct,
    energy_to_pct,
    fix_strict_increasing_breakpoints,
    interp_pct,
    pct_to_energy,
)

pytestmark = pytest.mark.tier_a


def test_fix_strict_increasing_breakpoints_dedupes_deterministically() -> None:
    bp = np.asarray([1.0, 1.0, 1.0, 2.0], dtype=np.float64)
    fixed1 = fix_strict_increasing_breakpoints(bp)
    fixed2 = fix_strict_increasing_breakpoints(bp)
    assert np.all(np.diff(fixed1) > 0.0)
    assert np.array_equal(fixed1, fixed2)


def test_interp_pct_uses_boundary_values() -> None:
    bp = np.asarray([0.0, 1.0], dtype=np.float64)
    q = np.asarray([0.1, 0.9], dtype=np.float64)
    assert interp_pct(-1.0, bp, q) == pytest.approx(0.1, abs=1e-12)
    assert interp_pct(2.0, bp, q) == pytest.approx(0.9, abs=1e-12)
    assert interp_pct(0.5, bp, q) == pytest.approx(0.5, abs=1e-12)


def test_pct_energy_roundtrip() -> None:
    p = 0.73
    e = pct_to_energy(p)
    p2 = energy_to_pct(e)
    assert p2 == pytest.approx(p, abs=1e-12)


def test_clamp_pct() -> None:
    assert clamp_pct(0.0, 1e-06, 1.0 - 1e-06) == pytest.approx(1e-06, abs=1e-12)
    assert clamp_pct(1.0, 1e-06, 1.0 - 1e-06) == pytest.approx(1.0 - 1e-06, abs=1e-12)
