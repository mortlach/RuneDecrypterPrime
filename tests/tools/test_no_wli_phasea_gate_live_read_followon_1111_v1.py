from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1 as mod,
)


pytestmark = pytest.mark.tier_a


def test_gate_verdict_uses_current_threshold() -> None:
    assert mod._gate_verdict(0.30) == "keep"
    assert mod._gate_verdict(0.299) == "filter"
    assert mod._gate_verdict(float("nan")) == "unknown"


def test_find_latest_predecessor_dir_uses_started_at_utc(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(mod, "OUTPUT_BASE_DIR", tmp_path)

    older_dir = tmp_path / "20260423T000000Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1"
    newer_dir = tmp_path / "20260424T000000Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1"
    older_dir.mkdir(parents=True)
    newer_dir.mkdir(parents=True)
    (older_dir / "attempt_status.json").write_text(
        json.dumps({"started_at_utc": "2026-04-23T00:00:00Z"}),
        encoding="utf-8",
    )
    (newer_dir / "attempt_status.json").write_text(
        json.dumps({"started_at_utc": "2026-04-24T00:00:00Z"}),
        encoding="utf-8",
    )

    out = mod._find_latest_predecessor_dir()

    assert out == newer_dir


def test_build_row_from_output_dir_reads_gate_snapshot_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    output_dir = tmp_path / "output" / "run1"
    resume_bundle = output_dir / "resume_bundle"
    resume_bundle.mkdir(parents=True)
    (output_dir / "attempt_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "elapsed": "01:00:00",
                "elapsed_seconds": 3600.0,
                "started_at_utc": "2026-04-23T10:00:00Z",
                "phasea_gate_snapshot_json_relpath": "output/run1/resume_bundle/phasea_gate_snapshot.json",
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "run_summary.json").write_text(
        json.dumps(
            {
                "search_seed": 7003,
                "baseline_best_match_ratio": 0.408,
                "retained_stage3_reference_match_ratio": 0.323,
                "resume_best_match_ratio": 0.476,
                "match_delta_vs_baseline": 0.068,
                "match_delta_vs_retained_stage3_reference": 0.153,
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "selected_family_low_edge_exact_replay_summary.json").write_text(
        json.dumps({"candidate_truth_delta_vs_baseline_row": 0.070}),
        encoding="utf-8",
    )
    (resume_bundle / "phasea_gate_snapshot.json").write_text(
        json.dumps(
            {
                "ts_utc": "2026-04-23T10:10:00Z",
                "phaseA_rank1_init_match": 0.490,
                "phaseA_best_init_match": 0.490,
                "phaseA_best_final_match": 0.476,
                "phaseA_rank1_plateau_would_stop": 0,
                "phaseB_ready_reason": "passed",
                "phaseB_ran": 1,
            }
        ),
        encoding="utf-8",
    )

    row = mod._build_row_from_output_dir(
        output_dir_relpath="output/run1",
        cell_origin="followon_matrix",
    )

    assert row["search_seed"] == 7003
    assert row["phasea_gate_snapshot_present"] == 1
    assert row["phasea_gate_snapshot_usable"] == 1
    assert row["gate_verdict"] == "keep"
    assert row["expected_gate_verdict"] == "keep"
    assert row["gate_verdict_matches_expected"] == 1
    assert row["phasea_gate_snapshot_elapsed_seconds"] == pytest.approx(600.0)
    assert row["phasea_gate_snapshot_elapsed_share"] == pytest.approx(1.0 / 6.0)


def test_build_live_read_recommendation_advances_for_full_match() -> None:
    rows = [
        {
            "phasea_gate_snapshot_present": 1,
            "phasea_gate_snapshot_usable": 1,
            "gate_verdict_matches_expected": 1,
            "phasea_gate_snapshot_elapsed_seconds": 600.0,
            "phasea_gate_snapshot_elapsed_share": 0.25,
        },
        {
            "phasea_gate_snapshot_present": 1,
            "phasea_gate_snapshot_usable": 1,
            "gate_verdict_matches_expected": 1,
            "phasea_gate_snapshot_elapsed_seconds": 720.0,
            "phasea_gate_snapshot_elapsed_share": 0.30,
        },
    ]

    out = mod.build_live_read_recommendation(rows)

    assert out["recommendation"] == "advance"
    assert out["snapshot_present_count"] == 2
    assert out["snapshot_usable_count"] == 2
    assert out["verdict_match_count"] == 2
    assert out["mean_phasea_gate_snapshot_elapsed_seconds"] == pytest.approx(660.0)


def test_build_live_read_recommendation_holds_for_unusable_snapshot() -> None:
    rows = [
        {
            "phasea_gate_snapshot_present": 1,
            "phasea_gate_snapshot_usable": 0,
            "gate_verdict_matches_expected": 0,
            "phasea_gate_snapshot_elapsed_seconds": 3200.0,
            "phasea_gate_snapshot_elapsed_share": 0.89,
        }
    ]

    out = mod.build_live_read_recommendation(rows)

    assert out["recommendation"] == "hold"
    assert out["snapshot_present_count"] == 1
    assert out["snapshot_usable_count"] == 0
