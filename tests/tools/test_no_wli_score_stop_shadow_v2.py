from __future__ import annotations

import json
import warnings
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.score_stop_shadow_v2 import (
    extract_score_stop_shadow_v2 as shadow_mod,
)


def _write_artifact(
    path: Path,
    *,
    period: int = 5,
    columns: int = 1,
    key_seed: int = 611,
    best_stage: str = "stage3_full_refine",
    best_match_ratio: float = 1.0,
    stage35_accept_reason: str = "",
    baseline_differs: int | None = None,
    baseline_source: str = "",
    include_space_map_v1: bool = True,
) -> None:
    space_map_v1 = (
        {
            "run_id": path.parents[1].name,
            "partial_state_rows": [],
            "pool_summaries": [],
        }
        if include_space_map_v1
        else {}
    )
    payload = {
        "period": int(period),
        "columns": int(columns),
        "key_seed": int(key_seed),
        "best_stage": str(best_stage),
        "best_match_ratio": float(best_match_ratio),
        "stage3_diagnostics": {
            "space_map_v1": space_map_v1,
            "stage35_accept_reason": str(stage35_accept_reason),
            "stage35_baseline_candidate_source": str(baseline_source),
        },
    }
    if baseline_differs is not None:
        payload["stage3_diagnostics"][
            "stage35_baseline_differs_from_phasec_score_winner"
        ] = int(baseline_differs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_default_family_panel_targets_cover_solved_control_plus_eight_hard_seeds() -> None:
    assert tuple(
        int(dict(cfg).get("key_seed", 0))
        for cfg in list(shadow_mod.FAMILY_PANEL_TARGETS or [])
    ) == (511, 411, 611, 711, 811, 911, 1011, 1111, 1211)


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
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "score_panel_v1")

    paths = shadow_mod.discover_artifact_paths()

    assert paths == [new_path]


def test_discover_artifact_paths_family_panel_selects_matching_targets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    solved_path = (
        tmp_path
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "20261231T235959999999Z__bench_solve_pipeline_no_wli__solved"
        / "final_instances"
        / "fixture_solved.json"
    )
    reject_path = (
        tmp_path
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "20261231T235959999998Z__bench_solve_pipeline_no_wli__reject"
        / "final_instances"
        / "fixture_reject.json"
    )
    _write_artifact(
        solved_path,
        period=5,
        columns=1,
        key_seed=511,
        best_match_ratio=1.0,
        include_space_map_v1=False,
    )
    _write_artifact(
        reject_path,
        period=9,
        columns=3,
        key_seed=811,
        best_match_ratio=0.47,
        best_stage="stage3_full_refine",
        stage35_accept_reason="search_score_drop_guard_failed",
        baseline_differs=1,
        include_space_map_v1=True,
    )
    monkeypatch.setattr(shadow_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "family_panel_v1")
    monkeypatch.setattr(
        shadow_mod,
        "FAMILY_PANEL_TARGETS",
        (
            {
                "label": "solved_control",
                "period": 5,
                "columns": 1,
                "key_seed": 511,
                "min_best_match": 0.999,
                "require_space_map_v1": False,
            },
            {
                "label": "selector_sensitive_reject",
                "period": 9,
                "columns": 3,
                "key_seed": 811,
                "max_best_match": 0.60,
                "require_stage35_accept_reason": "search_score_drop_guard_failed",
                "require_baseline_differs": 1,
                "require_space_map_v1": True,
            },
        ),
    )

    paths = shadow_mod.discover_artifact_paths()

    assert paths == [solved_path, reject_path]


def test_artifact_matches_target_can_require_best_stage_and_baseline_source() -> None:
    artifact = {
        "period": 9,
        "columns": 3,
        "key_seed": 1211,
        "best_stage": "stage3_full_refine",
        "best_match_ratio": 0.304,
        "stage3_diagnostics": {
            "space_map_v1": {"run_id": "run_1211"},
            "stage35_accept_reason": "search_score_drop_guard_failed",
            "stage35_baseline_differs_from_phasec_score_winner": 0,
            "stage35_baseline_candidate_source": "phaseA_selected",
        },
    }

    assert shadow_mod._artifact_matches_target(
        artifact,
        target_cfg={
            "period": 9,
            "columns": 3,
            "key_seed": 1211,
            "max_best_match": 0.35,
            "require_best_stage": "stage3_full_refine",
            "require_stage35_accept_reason": "search_score_drop_guard_failed",
            "require_baseline_differs": 0,
            "require_baseline_source": "phaseA_selected",
            "require_space_map_v1": True,
        },
    )


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


def test_annotate_shadow_rows_persists_diagnostics_for_non_firing_rows(
    monkeypatch,
) -> None:
    rows = [
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "phaseC_start",
            "stage_rank": 1,
            "candidate_hash": "h1",
            "family_id": "fam_a",
            "replay_word_ngram_active": True,
            "replay_word_ngram_trust_score": 0.10,
            "replay_word_ngram_report_xent": 20.0,
        },
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "phaseC_start",
            "stage_rank": 2,
            "candidate_hash": "h2",
            "family_id": "fam_b",
            "replay_word_ngram_active": True,
            "replay_word_ngram_trust_score": 0.05,
            "replay_word_ngram_report_xent": 21.0,
        },
    ]
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "family_panel_v1")
    monkeypatch.setattr(shadow_mod, "TRUST_SCORE_FLOORS", (0.30,))
    monkeypatch.setattr(shadow_mod, "REPORT_XENT_CEILINGS", (24.0,))
    monkeypatch.setattr(shadow_mod, "RIVAL_MARGIN_FLOORS", (0.00,))
    monkeypatch.setattr(shadow_mod, "FAMILY_SUPPORT_FLOORS", (1,))

    out_rows = shadow_mod._annotate_shadow_rows(rows)

    first = dict(out_rows[0])
    assert int(first["shadow_high_score_would_dump"]) == 0
    assert str(first["shadow_primary_axis"]) == "word_ngram_trust"
    assert float(first["shadow_best_rival_family_margin"]) == 0.05
    assert int(first["shadow_family_support_count"]) == 0
    assert int(first["shadow_diag_trust_pass"]) == 0
    assert int(first["shadow_diag_xent_pass"]) == 1
    assert int(first["shadow_diag_family_support_pass"]) == 0
    assert "trust_below_floor" in list(first["shadow_diag_blockers"])
    assert "family_support_below_floor" in list(first["shadow_diag_blockers"])


def test_annotate_shadow_rows_persists_late_family_persistence_metrics(
    monkeypatch,
) -> None:
    rows = [
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "phaseC_start",
            "stage_rank": 1,
            "candidate_hash": "h1",
            "family_id": "fam_a",
            "replay_word_ngram_active": True,
            "replay_word_ngram_trust_score": 0.10,
            "replay_word_ngram_report_xent": 20.0,
        },
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "stage35_seed",
            "stage_rank": 1,
            "candidate_hash": "h2",
            "family_id": "fam_a",
            "replay_word_ngram_active": True,
            "replay_word_ngram_trust_score": 0.12,
            "replay_word_ngram_report_xent": 19.0,
        },
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "stage35_archive",
            "stage_rank": 1,
            "candidate_hash": "h3",
            "family_id": "fam_a",
            "replay_word_ngram_active": True,
            "replay_word_ngram_trust_score": 0.14,
            "replay_word_ngram_report_xent": 18.0,
        },
    ]
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "family_panel_v1")
    monkeypatch.setattr(shadow_mod, "TRUST_SCORE_FLOORS", (0.30,))
    monkeypatch.setattr(shadow_mod, "REPORT_XENT_CEILINGS", (24.0,))
    monkeypatch.setattr(shadow_mod, "RIVAL_MARGIN_FLOORS", (0.00,))
    monkeypatch.setattr(shadow_mod, "FAMILY_SUPPORT_FLOORS", (1,))

    out_rows = shadow_mod._annotate_shadow_rows(rows)

    first = dict(out_rows[0])
    assert int(first["shadow_late_family_persistence_count"]) == 3
    assert list(first["shadow_late_family_persistence_boundaries"]) == [
        "phaseC_start",
        "stage35_seed",
        "stage35_archive",
    ]
    assert int(first["shadow_late_family_persistence_pass"]) == 1
    assert int(first["shadow_late_family_reaches_archive"]) == 1
    assert str(first["shadow_late_family_first_boundary"]) == "phaseC_start"
    assert str(first["shadow_late_family_last_boundary"]) == "stage35_archive"


def test_annotate_shadow_rows_can_fire_archive_search_uplift_dump(
    monkeypatch,
) -> None:
    rows = [
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "phaseC_start",
            "stage_rank": 1,
            "candidate_hash": "h_phasec",
            "family_id": "fam_a",
            "replay_word_ngram_active": True,
            "replay_word_ngram_trust_score": 0.05,
            "replay_word_ngram_report_xent": 20.0,
            "replay_search_score": -12.00,
            "replay_full_score": 0.20,
        },
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "stage35_archive",
            "stage_rank": 1,
            "candidate_hash": "h_archive",
            "family_id": "fam_a",
            "replay_word_ngram_active": True,
            "replay_word_ngram_trust_score": 0.10,
            "replay_word_ngram_report_xent": 20.0,
            "replay_search_score": -11.70,
            "replay_full_score": 0.19,
        },
    ]
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "family_panel_v1")
    monkeypatch.setattr(shadow_mod, "TRUST_SCORE_FLOORS", (0.30,))
    monkeypatch.setattr(shadow_mod, "REPORT_XENT_CEILINGS", (24.0,))
    monkeypatch.setattr(shadow_mod, "RIVAL_MARGIN_FLOORS", (0.00,))
    monkeypatch.setattr(shadow_mod, "FAMILY_SUPPORT_FLOORS", (1,))
    monkeypatch.setattr(shadow_mod, "CONTINUATION_SEARCH_UPLIFT_FLOORS", (0.15,))

    out_rows = shadow_mod._annotate_shadow_rows(rows)

    archive_row = next(row for row in out_rows if str(row.get("candidate_hash")) == "h_archive")
    assert str(archive_row["shadow_high_score_rule_id"]) == "archive_search_uplift0.15"
    assert int(archive_row["shadow_high_score_would_dump"]) == 1
    assert round(float(archive_row["shadow_late_family_search_uplift"]), 6) == 0.30
    assert float(archive_row["shadow_late_family_phasec_search_score"]) == -12.0
    assert float(archive_row["shadow_late_family_current_boundary_best_search_score"]) == -11.7


def test_annotate_shadow_rows_does_not_fire_archive_search_uplift_when_negative(
    monkeypatch,
) -> None:
    rows = [
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "phaseC_start",
            "stage_rank": 1,
            "candidate_hash": "h_phasec",
            "family_id": "fam_a",
            "replay_word_ngram_active": True,
            "replay_word_ngram_trust_score": 0.05,
            "replay_word_ngram_report_xent": 20.0,
            "replay_search_score": -11.80,
            "replay_full_score": 0.20,
        },
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "stage35_archive",
            "stage_rank": 1,
            "candidate_hash": "h_archive",
            "family_id": "fam_a",
            "replay_word_ngram_active": True,
            "replay_word_ngram_trust_score": 0.10,
            "replay_word_ngram_report_xent": 20.0,
            "replay_search_score": -12.10,
            "replay_full_score": 0.19,
        },
    ]
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "family_panel_v1")
    monkeypatch.setattr(shadow_mod, "TRUST_SCORE_FLOORS", (0.30,))
    monkeypatch.setattr(shadow_mod, "REPORT_XENT_CEILINGS", (24.0,))
    monkeypatch.setattr(shadow_mod, "RIVAL_MARGIN_FLOORS", (0.00,))
    monkeypatch.setattr(shadow_mod, "FAMILY_SUPPORT_FLOORS", (1,))
    monkeypatch.setattr(shadow_mod, "CONTINUATION_SEARCH_UPLIFT_FLOORS", (0.15,))

    out_rows = shadow_mod._annotate_shadow_rows(rows)

    archive_row = next(row for row in out_rows if str(row.get("candidate_hash")) == "h_archive")
    assert str(archive_row["shadow_high_score_rule_id"]) == ""
    assert int(archive_row["shadow_high_score_would_dump"]) == 0
    assert round(float(archive_row["shadow_late_family_search_uplift"]), 6) == -0.30


def test_annotate_shadow_rows_keeps_continuation_metrics_on_trust_rule_hit(
    monkeypatch,
) -> None:
    rows = [
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "phaseC_start",
            "stage_rank": 1,
            "candidate_hash": "h_phasec",
            "family_id": "fam_a",
            "replay_word_ngram_active": True,
            "replay_word_ngram_trust_score": 0.35,
            "replay_word_ngram_report_xent": 18.0,
            "replay_search_score": -12.00,
            "replay_full_score": 0.20,
        },
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "stage35_archive",
            "stage_rank": 1,
            "candidate_hash": "h_archive",
            "family_id": "fam_a",
            "replay_word_ngram_active": True,
            "replay_word_ngram_trust_score": 0.40,
            "replay_word_ngram_report_xent": 17.0,
            "replay_search_score": -11.70,
            "replay_full_score": 0.22,
        },
    ]
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "family_panel_v1")
    monkeypatch.setattr(shadow_mod, "TRUST_SCORE_FLOORS", (0.30,))
    monkeypatch.setattr(shadow_mod, "REPORT_XENT_CEILINGS", (24.0,))
    monkeypatch.setattr(shadow_mod, "RIVAL_MARGIN_FLOORS", (0.00,))
    monkeypatch.setattr(shadow_mod, "FAMILY_SUPPORT_FLOORS", (1,))
    monkeypatch.setattr(shadow_mod, "CONTINUATION_SEARCH_UPLIFT_FLOORS", (0.15,))

    out_rows = shadow_mod._annotate_shadow_rows(rows)

    archive_row = next(row for row in out_rows if str(row.get("candidate_hash")) == "h_archive")
    assert str(archive_row["shadow_high_score_rule_id"]) == "trust0.30_xent24.00_margin0.00_support1"
    assert round(float(archive_row["shadow_late_family_search_uplift"]), 6) == 0.30
    assert float(archive_row["shadow_late_family_phasec_search_score"]) == -12.0


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


def test_annotate_stability_family_panel_requires_two_boundaries(
    monkeypatch,
) -> None:
    rows = [
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "phaseC_start",
            "stage_rank": 1,
            "candidate_hash": "h1",
            "family_id": "fam_a",
            "shadow_high_score_rule_id": "trust0.30_xent24.00_margin0.00_support1",
            "shadow_high_score_would_dump": 1,
        },
        {
            "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/fixture.json",
            "stage_boundary": "stage35_seed",
            "stage_rank": 1,
            "candidate_hash": "h2",
            "family_id": "fam_a",
            "shadow_high_score_rule_id": "trust0.30_xent24.00_margin0.00_support1",
            "shadow_high_score_would_dump": 1,
        },
    ]
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "family_panel_v1")

    out_rows = shadow_mod._annotate_stability(rows)

    stable_rows = [
        dict(row)
        for row in out_rows
        if int(row.get("shadow_stability_would_stop", 0) or 0) == 1
    ]
    assert len(stable_rows) == 1
    assert str(stable_rows[0]["candidate_hash"]) == "h2"
    assert str(stable_rows[0]["shadow_stability_rule_id"]) == (
        "family_boundary_support_2"
    )
    assert str(stable_rows[0]["shadow_first_trigger_stage_boundary"]) == "stage35_seed"
    assert int(stable_rows[0]["shadow_family_boundary_support_count"]) == 2


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


def test_collect_candidate_rows_family_panel_keeps_late_boundaries_only(
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
                        "stage_boundary": "phaseC_pool",
                        "candidate_hash": "pp1",
                        "stage_rank": 1,
                    },
                    {
                        "stage_boundary": "phaseC_pool",
                        "candidate_hash": "pp2",
                        "stage_rank": 2,
                    },
                    {
                        "stage_boundary": "phaseC_pool",
                        "candidate_hash": "pp3",
                        "stage_rank": 3,
                    },
                    {
                        "stage_boundary": "phaseC_start",
                        "candidate_hash": "ps1",
                        "stage_rank": 1,
                    },
                    {
                        "stage_boundary": "stage35_seed",
                        "candidate_hash": "sd1",
                        "stage_rank": 1,
                    },
                    {
                        "stage_boundary": "stage35_archive",
                        "candidate_hash": "ar1",
                        "stage_rank": 1,
                    },
                ]
            }
        }
    }
    monkeypatch.setattr(shadow_mod, "ANALYSIS_MODE", "family_panel_v1")
    monkeypatch.setattr(shadow_mod, "FAMILY_PANEL_MAX_ROWS_PER_BOUNDARY", 2)

    rows = shadow_mod.collect_candidate_rows(artifact)

    assert [str(row["candidate_hash"]) for row in rows] == [
        "pp1",
        "pp2",
        "ps1",
        "sd1",
        "ar1",
    ]


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
