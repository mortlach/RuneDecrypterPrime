from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_no_wli_runtime_history_reference_v1 as hist_mod,
)


pytestmark = pytest.mark.tier_a


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_runtime_row_uses_fallback_profile_and_mode(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_x"
    _write_json(
        run_dir / "best" / "best_instance.json",
        {
            "run_id": "run_x",
            "instance_input_mode": "fixed_ciphertext",
            "period": 9,
            "columns": 3,
            "length": 1000,
            "instance_source_key_seed": 1111,
            "search_seed": 7002,
            "total_seconds": 7200.0,
            "best_match_ratio": 0.75,
            "best_stage": "stage3_full_refine",
            "status": "unsolved",
            "outcome_code": "unsolved",
            "stage35_requested_cfg": 0,
            "stage35_rounds_completed": 0,
            "stage35_selected": 0,
        },
    )
    _write_json(
        run_dir / "run_manifest.json",
        {
            "generated_utc": "2026-01-01T00:00:00+00:00",
            "completed_utc": "2026-01-01T02:00:00+00:00",
            "mode": "adaptive_fixture_v1",
            "profile_id": "",
            "scoring_experiment": {"profile": "c_min_late"},
        },
    )
    _write_json(
        run_dir / "run_config.json",
        {
            "profile": "no_wli_profile_x",
            "mode": "adaptive_fixture_v1",
            "scorer_schedule": {
                "stage1": "A",
                "stage2": "M",
                "stage3": "B",
            },
        },
    )
    _write_json(
        run_dir / "policy_spec.json",
        {
            "policy_id": "no_wli_adaptive_policy_v1",
            "params": {"profile": "no_wli_profile_x", "run_mode": "adaptive_fixture_v1"},
        },
    )

    row = hist_mod.load_runtime_row(run_dir / "best" / "best_instance.json")

    assert row["profile_id"] == "no_wli_profile_x"
    assert row["mode"] == "adaptive_fixture_v1"
    assert row["policy_id"] == "no_wli_adaptive_policy_v1"
    assert row["scoring_profile"] == "c_min_late"
    assert row["elapsed_hours"] == pytest.approx(2.0)


def test_summarize_group_counts_and_ranges() -> None:
    rows = [
        {"shape_key": "fixed|p9|c3|l1000", "instance_input_mode": "fixed", "period": 9, "columns": 3, "length": 1000, "elapsed_hours": 2.0, "best_match_ratio": 0.4},
        {"shape_key": "fixed|p9|c3|l1000", "instance_input_mode": "fixed", "period": 9, "columns": 3, "length": 1000, "elapsed_hours": 4.0, "best_match_ratio": 0.5},
    ]

    summary = hist_mod.summarize_group(rows, ("shape_key", "instance_input_mode", "period", "columns", "length"))

    assert summary == [
        {
            "shape_key": "fixed|p9|c3|l1000",
            "instance_input_mode": "fixed",
            "period": 9,
            "columns": 3,
            "length": 1000,
            "run_count": 2,
            "min_hours": 2.0,
            "mean_hours": 3.0,
            "max_hours": 4.0,
            "min_best_match_ratio": 0.4,
            "mean_best_match_ratio": 0.45,
            "max_best_match_ratio": 0.5,
        }
    ]
