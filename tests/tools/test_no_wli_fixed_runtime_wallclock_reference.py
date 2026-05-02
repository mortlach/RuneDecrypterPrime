from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_fixed_runtime_wallclock_reference_v1 as wallclock_mod,
)


pytestmark = pytest.mark.tier_a


def _write_best_instance(path: Path, *, fixture_seed: int, search_seed: int, total_seconds: float, best_match_ratio: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "instance_input_mode": "fixed_ciphertext",
        "period": 9,
        "columns": 3,
        "length": 1000,
        "instance_source_key_seed": fixture_seed,
        "search_seed": search_seed,
        "total_seconds": total_seconds,
        "best_match_ratio": best_match_ratio,
        "best_stage": "stage3_full_refine",
        "status": "unsolved",
        "outcome_code": "unsolved",
        "run_id": f"run_{fixture_seed}_{search_seed}_{int(total_seconds)}",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_completed_fixed_runtime_rows_filters_and_sorts(tmp_path: Path) -> None:
    _write_best_instance(
        tmp_path / "a" / "best_instance.json",
        fixture_seed=1111,
        search_seed=7002,
        total_seconds=7200.0,
        best_match_ratio=0.75,
    )
    _write_best_instance(
        tmp_path / "b" / "best_instance.json",
        fixture_seed=611,
        search_seed=7001,
        total_seconds=3600.0,
        best_match_ratio=0.33,
    )
    wrong = {
        "instance_input_mode": "generated",
        "period": 9,
        "columns": 3,
        "length": 1000,
    }
    wrong_path = tmp_path / "c" / "best_instance.json"
    wrong_path.parent.mkdir(parents=True, exist_ok=True)
    wrong_path.write_text(json.dumps(wrong), encoding="utf-8")

    rows = wallclock_mod.load_completed_fixed_runtime_rows(tmp_path)

    assert [(row["fixture_seed"], row["search_seed"]) for row in rows] == [
        (611, 7001),
        (1111, 7002),
    ]
    assert rows[0]["elapsed_hours"] == pytest.approx(1.0)
    assert rows[1]["elapsed_hours"] == pytest.approx(2.0)


def test_summarize_group_builds_mean_min_max() -> None:
    rows = [
        {"fixture_seed": 611, "search_seed": 7002, "elapsed_hours": 2.0, "best_match_ratio": 0.4},
        {"fixture_seed": 611, "search_seed": 7002, "elapsed_hours": 4.0, "best_match_ratio": 0.5},
        {"fixture_seed": 1111, "search_seed": 7002, "elapsed_hours": 3.0, "best_match_ratio": 0.7},
    ]

    summary = wallclock_mod.summarize_group(rows, ("fixture_seed", "search_seed"))

    assert summary == [
        {
            "fixture_seed": 611,
            "search_seed": 7002,
            "run_count": 2,
            "min_hours": 2.0,
            "mean_hours": 3.0,
            "max_hours": 4.0,
            "min_best_match_ratio": 0.4,
            "mean_best_match_ratio": 0.45,
            "max_best_match_ratio": 0.5,
        },
        {
            "fixture_seed": 1111,
            "search_seed": 7002,
            "run_count": 1,
            "min_hours": 3.0,
            "mean_hours": 3.0,
            "max_hours": 3.0,
            "min_best_match_ratio": 0.7,
            "mean_best_match_ratio": 0.7,
            "max_best_match_ratio": 0.7,
        },
    ]
