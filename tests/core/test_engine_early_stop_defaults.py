from __future__ import annotations

import pytest

from rune_decrypter_prime.core.engine.engine import _with_early_stop_defaults
from rune_decrypter_prime.core.types import SolverName


pytestmark = pytest.mark.tier_a


def test_engine_defaults_apply_when_plateau_missing():
    out = _with_early_stop_defaults(SolverName.GA, {})
    assert out["plateau_rounds"] == 24
    assert out["plateau_min_delta"] == pytest.approx(1e-6)


def test_engine_defaults_do_not_override_explicit_values():
    out = _with_early_stop_defaults(
        SolverName.KAEDING,
        {"plateau_rounds": 111, "plateau_min_delta": 0.0},
    )
    assert out["plateau_rounds"] == 111
    assert out["plateau_min_delta"] == pytest.approx(0.0)

