from __future__ import annotations

import json
import warnings
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.score_stop_shadow_v2 import (
    extract_score_stop_shadow_v2 as shadow_mod,
)


def _write_artifact(path: Path, *, period: int = 5, columns: int = 1) -> None:
    payload = {
        "period": int(period),
        "columns": int(columns),
        "key_seed": 611,
        "best_stage": "stage3_full_refine",
        "best_match_ratio": 1.0,
        "stage3_diagnostics": {
            "space_map_v1": {
                "run_id": path.parents[1].name,
                "partial_state_rows": [],
                "pool_summaries": [],
            }
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_discover_artifact_paths_prefers_newest_runs_before_cap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    old_path = (
        tmp_path
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "20260101T000000000000Z__bench_solve_pipeline_no_wli__old"
        / "final_instances"
        / "fixture_old.json"
    )
    new_path = (
        tmp_path
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "20261231T235959999999Z__bench_solve_pipeline_no_wli__new"
        / "final_instances"
        / "fixture_new.json"
    )
    _write_artifact(old_path)
    _write_artifact(new_path)
    monkeypatch.setattr(shadow_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(shadow_mod, "MAX_ARTIFACTS", 1)

    paths = shadow_mod.discover_artifact_paths()

    assert paths == [new_path]


def test_build_run_shadow_summary_keeps_dump_and_stop_separate() -> None:
    artifact_path = Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/"
        "20260101T000000000000Z__bench_solve_pipeline_no_wli__abc/"
        "final_instances/fixture.json"
    )
    artifact = {
        "best_stage": "stage3_full_refine",
        "best_match_ratio": 0.5,
        "period": 9,
        "columns": 3,
        "key_seed": 411,
        "stage3_diagnostics": {
            "space_map_v1": {"run_id": "run_abc"},
        },
    }

    summaries = shadow_mod.build_run_shadow_summary(
        artifact_path,
        artifact,
        [
            {
                "stage_boundary": "phaseC_start",
                "stage_rank": 2,
                "candidate_hash": "dump_hash",
                "family_id": "fam_a",
                "shadow_primary_axis": "word_ngram_trust",
                "shadow_high_score_rule_id": "trust0.95_xent2.00_margin0.02_support1",
                "shadow_high_score_would_dump": 1,
                "shadow_stability_rule_id": "",
                "shadow_stability_would_stop": 0,
                "replay_truth_match": 0.5,
                "replay_data_gap_flags": [],
            }
        ],
    )

    assert len(summaries) == 1
    assert int(summaries[0]["would_dump"]) == 1
    assert int(summaries[0]["would_stop"]) == 0
    assert str(summaries[0]["would_stop_stage_boundary"]) == ""
    assert str(summaries[0]["shadow_false_stop_label"]) == ""


def test_annotate_stability_uses_strongest_satisfied_boundary_threshold() -> None:
    rows = [
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "stage2_promoted",
            "stage_rank": 1,
            "candidate_hash": "h1",
            "family_id": "fam_a",
            "shadow_high_score_rule_id": "trust0.95_xent2.00_margin0.02_support1",
            "shadow_high_score_would_dump": 1,
        },
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "stage3_prep",
            "stage_rank": 1,
            "candidate_hash": "h2",
            "family_id": "fam_a",
            "shadow_high_score_rule_id": "trust0.95_xent2.00_margin0.02_support1",
            "shadow_high_score_would_dump": 1,
        },
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "phaseC_pool",
            "stage_rank": 1,
            "candidate_hash": "h3",
            "family_id": "fam_a",
            "shadow_high_score_rule_id": "trust0.95_xent2.00_margin0.02_support1",
            "shadow_high_score_would_dump": 1,
        },
    ]

    out_rows = shadow_mod._annotate_stability(rows)

    stable_rows = [
        dict(row)
        for row in out_rows
        if int(row.get("shadow_stability_would_stop", 0) or 0) == 1
    ]
    assert len(stable_rows) == 1
    assert str(stable_rows[0]["candidate_hash"]) == "h3"
    assert str(stable_rows[0]["shadow_stability_rule_id"]) == (
        "family_boundary_support_3"
    )
    assert str(stable_rows[0]["shadow_first_trigger_stage_boundary"]) == "phaseC_pool"
    assert int(stable_rows[0]["shadow_family_boundary_support_count"]) == 3


def test_collect_candidate_rows_score_panel_caps_rows_per_late_boundary(
    monkeypatch,
) -> None:
    artifact = {
        "stage3_diagnostics": {
            "space_map_v1": {
                "partial_state_rows": [
                    {
                        "stage_boundary": "stage2_promoted",
                        "candidate_hash": "s2",
                        "stage_rank": 1,
                    },
                    {
                        "stage_boundary": "phaseC_start",
                        "candidate_hash": "pc1",
                        "stage_rank": 1,
                    },
                    {
                        "stage_boundary": "phaseC_start",
                        "candidate_hash": "pc2",
                        "stage_rank": 2,
                    },
                    {
                        "stage_boundary": "phaseC_start",
                        "candidate_hash": "pc3",
                        "stage_rank": 3,
                    },
                    {
                        "stage_boundary": "stage35_seed",
                        "candidate_hash": "sd1",
                        "stage_rank": 1,
                    },
                ]
            }
        }
    }
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "score_panel_v1")
    monkeypatch.setattr(shadow_mod, "SCORE_PANEL_MAX_ROWS_PER_BOUNDARY", 2)

    rows = shadow_mod.collect_candidate_rows(artifact)

    assert [str(row["candidate_hash"]) for row in rows] == ["pc1", "pc2", "sd1"]


def test_collect_candidate_rows_fallback_includes_legacy_topk_rows(monkeypatch) -> None:
    artifact = {
        "stage2_topk": [
            {
                "rank": 1,
                "key_idx": [2, 0, 1],
                "plaintext_idx": [1, 2, 3],
                "score_judge": -4.5,
                "score_stage2": -5.5,
                "match_ratio": 0.25,
            },
        ],
        "stage3_topk": [
            {
                "rank": 1,
                "end_hash": "stage3_hash_a",
                "source": "phaseB_topk",
                "key_idx": [1, 0, 2],
                "plaintext_idx": [4, 5, 6],
                "score_judge": 0.75,
                "score_raw": -1.25,
                "match_ratio": 0.997,
            },
        ],
        "stage3_diagnostics": {
            "phaseC_start_summaries": [],
        },
    }
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "score_panel_v1")
    monkeypatch.setattr(shadow_mod, "SCORE_PANEL_MAX_ROWS_PER_BOUNDARY", 2)

    rows = shadow_mod.collect_candidate_rows(artifact)

    assert [str(row["stage_boundary"]) for row in rows] == ["stage2_topk", "stage3_topk"]
    assert str(rows[0]["candidate_hash"])
    assert str(rows[1]["candidate_hash"]) == "stage3_hash_a"
    assert rows[0]["final_key_idx"] == [2, 0, 1]
    assert rows[0]["final_plaintext_idx"] == [1, 2, 3]
    assert rows[1]["final_key_idx"] == [1, 0, 2]
    assert rows[1]["final_plaintext_idx"] == [4, 5, 6]
    assert float(rows[0]["final_search_score"]) == -5.5
    assert float(rows[1]["final_search_score"]) == -1.25
    assert rows[0]["replay_data_gap_flags"] == [
        "fallback_row_source",
        "missing_space_map_v1",
    ]


def test_collect_candidate_rows_fallback_enriches_phasec_start_from_stage3_topk(
    monkeypatch,
) -> None:
    artifact = {
        "stage3_topk": [
            {
                "rank": 1,
                "end_hash": "phasec_hash_a",
                "key_idx": [2, 1, 0],
                "plaintext_idx": [6, 5, 4],
                "score_judge": 0.75,
                "score_raw": -1.25,
                "match_ratio": 0.58,
            },
        ],
        "stage3_diagnostics": {
            "phaseC_start_summaries": [
                {
                    "candidate_hash": "phasec_hash_a",
                    "source": "phaseB_topk",
                    "source_rank": 1,
                    "start_idx": 1,
                    "final_score": 0.77,
                    "final_search_score": -1.11,
                    "final_match": 0.60,
                }
            ]
        },
    }
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "score_panel_v1")
    monkeypatch.setattr(shadow_mod, "SCORE_PANEL_MAX_ROWS_PER_BOUNDARY", 2)

    rows = shadow_mod.collect_candidate_rows(artifact)

    phasec_rows = [
        dict(row)
        for row in rows
        if str(row.get("stage_boundary", "")) == "phaseC_start"
    ]
    assert len(phasec_rows) == 1
    assert phasec_rows[0]["final_key_idx"] == [2, 1, 0]
    assert phasec_rows[0]["final_plaintext_idx"] == [6, 5, 4]


def test_build_threshold_sweep_summary_ignores_all_nan_runtime_proxy_without_warning() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        summary = shadow_mod.build_threshold_sweep_summary(
            [
                {
                    "shadow_rule_id": "trust0.30_xent24.00_margin0.00_support1",
                    "would_stop": 0,
                    "would_stop_false_positive": 0,
                    "would_stop_before_true_solution": 0,
                    "run_type": "solved_control",
                    "saved_runtime_seconds_proxy": float("nan"),
                }
            ]
        )

    rows = list(dict(summary).get("run_rule_rows", []) or [])
    assert len(rows) == 1
    assert str(rows[0]["shadow_rule_id"]) == "trust0.30_xent24.00_margin0.00_support1"
    assert str(rows[0]["mean_saved_runtime_seconds_proxy"]) == "nan"
