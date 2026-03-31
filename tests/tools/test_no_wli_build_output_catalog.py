from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import build_output_catalog as cat_mod


pytestmark = pytest.mark.tier_a


def test_catalog_artifact_helpers_fallback_to_stage3_diagnostics() -> None:
    artifact = {
        "best_match_ratio": 0.794,
        "best_score": 0.3534,
        "period": 9,
        "columns": 3,
        "length": 1000,
        "key_seed": 511,
        "stage3_diagnostics": {
            "stage35_selected": 1,
        },
    }

    assert cat_mod._artifact_seed(artifact) == 511
    assert cat_mod._artifact_stage35_selected(artifact) == 1


def test_build_run_manifest_counts_nested_stage35_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "no_wli"
    catalog_root = tmp_path / "catalog"
    run_dir = source_root / "20260322T001521766633Z__bench_solve_pipeline_no_wli__55b7159"
    final_dir = run_dir / "final_instances"
    final_dir.mkdir(parents=True)
    (run_dir / "run_config.json").write_text("{}", encoding="utf-8")
    artifact = {
        "best_match_ratio": 0.794,
        "best_score": 0.3534210925874578,
        "best_stage": "stage35_substitution_only",
        "period": 9,
        "columns": 3,
        "length": 1000,
        "key_seed": 511,
        "stage3_diagnostics": {
            "stage35_selected": 1,
        },
    }
    (final_dir / "fixture_fixture_001_p9_c3_l1000__text0__seed511.json").write_text(
        json.dumps(artifact),
        encoding="utf-8",
    )

    monkeypatch.setattr(cat_mod, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(cat_mod, "CATALOG_ROOT", catalog_root)

    run_rows = cat_mod._build_run_manifest()
    assert len(run_rows) == 1
    assert int(run_rows[0]["stage35_selected_count"]) == 1

    notable = cat_mod._build_notable_artifacts(run_rows)
    best_p9 = list(notable["best_p9_c3"])
    assert len(best_p9) == 1
    assert int(best_p9[0]["stage35_selected"]) == 1
    assert int(best_p9[0]["seed"]) == 511
