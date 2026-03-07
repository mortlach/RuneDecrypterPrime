from __future__ import annotations

import math

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.oracle_policy import (
    derive_stage3_phaseb_char_pct_min,
)


pytestmark = pytest.mark.tier_a


def test_oracle_policy_disabled_returns_not_used() -> None:
    value, source, emit = derive_stage3_phaseb_char_pct_min(
        stage3_phase_switch_enabled=False,
        stage3_phaseb_experiment="c_min_late",
        oracle_s3=0.5,
        scoring_experiment_c_char_pct_min=0.7,
        stage3_span_char_pct_min_override=None,
    )
    assert math.isnan(value)
    assert source == "not_used_explicit_basin_judge"
    assert emit is False


def test_oracle_policy_uses_oracle_minus_clamped_rule() -> None:
    value, source, emit = derive_stage3_phaseb_char_pct_min(
        stage3_phase_switch_enabled=True,
        stage3_phaseb_experiment="c_min_late",
        oracle_s3=0.61,
        scoring_experiment_c_char_pct_min=0.7,
        stage3_span_char_pct_min_override=None,
    )
    assert value == pytest.approx(0.45)
    assert source == "oracle_minus_0.10_clamp_0.30_0.45_not_applied"
    assert emit is True


def test_oracle_policy_uses_profile_default_when_oracle_non_finite() -> None:
    value, source, emit = derive_stage3_phaseb_char_pct_min(
        stage3_phase_switch_enabled=True,
        stage3_phaseb_experiment="c_min_late",
        oracle_s3=float("nan"),
        scoring_experiment_c_char_pct_min=0.37,
        stage3_span_char_pct_min_override=None,
    )
    assert value == pytest.approx(0.37)
    assert source == "profile_default_not_applied"
    assert emit is True


def test_oracle_policy_override_wins() -> None:
    value, source, emit = derive_stage3_phaseb_char_pct_min(
        stage3_phase_switch_enabled=True,
        stage3_phaseb_experiment="c_min_late",
        oracle_s3=0.4,
        scoring_experiment_c_char_pct_min=0.37,
        stage3_span_char_pct_min_override=0.123,
    )
    assert value == pytest.approx(0.123)
    assert source == "diagnostic_override_not_applied"
    assert emit is True
