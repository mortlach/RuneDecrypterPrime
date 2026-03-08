from __future__ import annotations

from pathlib import Path

import pytest

import rune_decrypter_prime as rdp


pytestmark = pytest.mark.tier_a


def _read(rel_path: str) -> str:
    root = Path(rdp.__file__).resolve().parents[2]
    return (root / rel_path).read_text(encoding="utf-8")


def test_col_then_sub_oracle_decision_paths_are_guarded() -> None:
    text = _read("tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py")
    # stop-score (stage1) decision path guard
    assert "stage1_oracle_guard = bool(" in text
    assert "oracle_decision_paths_enabled" in text
    # prune/gate band selection decision path guard
    assert (
        "if bool(oracle_decision_paths_enabled) and np.isfinite(stage2_gate_score) and np.isfinite(oracle_s23):"
        in text
    )
    # stop-score (stage3) decision path guard
    assert "if bool(oracle_decision_paths_enabled) and bool(STAGE3_USE_ORACLE_GUIDE_STOP):" in text


def test_sub_then_col_oracle_decision_paths_are_guarded() -> None:
    text = _read("tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py")
    # stop-score (stage3) decision path guard
    assert "if bool(oracle_decision_paths_enabled) and bool(STAGE3_USE_ORACLE_GUIDE_STOP):" in text
    # consulted flag is tracked separately from enabled capability
    assert "oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions)" in text


def test_no_wli_oracle_off_cannot_enable_decision_paths() -> None:
    text = _read("tools/benchmarks/periodic_sub_trans/no_wli/run_environment.py")
    assert 'oracle_decision_paths_enabled = bool(oracle_mode == "benchmark_only")' in text
    assert (
        "oracle_assist_selection_effective = bool(\n"
        "        oracle_decision_paths_enabled and bool(oracle_assist_selection_requested)\n"
        "    )"
    ) in text


def test_no_wli_promotion_winner_oracle_usage_guarded() -> None:
    text = _read("tools/benchmarks/periodic_sub_trans/no_wli/stage2_search.py")
    # promote/winner path chooses oracle-assisted branch only when explicitly effective.
    assert "if bool(oracle_assist_selection_effective):" in text
    assert "mark_oracle_decision_use()" in text
    assert "else:\n            better = bool(" in text


def test_no_wli_stage3_band_oracle_usage_guarded() -> None:
    text = _read("tools/benchmarks/periodic_sub_trans/no_wli/stage3_band_policy.py")
    assert "bool(oracle_decision_paths_enabled)" in text
    assert "return gap, select_stage3_band(dynamic_bands=dynamic_bands, gap_to_oracle=gap), True" in text
    assert "return gap, select_stage3_default_band(dynamic_bands=dynamic_bands), False" in text

