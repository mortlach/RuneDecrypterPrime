from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_stageb_continuation import (
    load_and_write_stageb_continuation_report,
    run_selected_trial_row_continuations,
)


pytestmark = pytest.mark.tier_a


def test_run_selected_trial_row_continuations_filters_to_stageb_selectors() -> None:
    captured: list[dict[str, object]] = []

    def _fake_runner(case, *, selected_row):
        _ = case
        captured.append(dict(selected_row))
        return {
            "fixture_label": selected_row["fixture_label"],
            "selector": selected_row["selector"],
            "artifact_relpath": selected_row["source_artifact_path"],
            "selected_candidate_hash": selected_row["candidate_hash"],
            "selected_candidate_source": selected_row["source"],
            "selected_candidate_lane": selected_row["lane"],
            "selected_candidate_final_match": selected_row["final_match"],
            "selected_candidate_final_score": selected_row["final_score"],
            "replay_material_complete": selected_row["replay_material_complete"],
            "resume_best_match_ratio": selected_row["final_match"],
            "resume_best_score": selected_row["final_score"],
            "stage35": {"selected": 0, "accept_reason": "accepted"},
        }

    rows = [
        {
            "fixture_label": "control",
            "fixture_id": "fixture_control",
            "source_artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/case.json",
            "selector": "legacy",
            "candidate_hash": "winner-hash",
            "source": "stage3_best_phaseB",
            "lane": "anchor",
            "final_match": 0.039,
            "final_score": 0.191,
            "replay_material_complete": 1,
        },
        {
            "fixture_label": "control",
            "fixture_id": "fixture_control",
            "source_artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/case.json",
            "selector": "oracle_best_explored",
            "candidate_hash": "truth-hash",
            "source": "phaseA_selected",
            "lane": "challenger",
            "final_match": 0.418,
            "final_score": 0.173,
            "replay_material_complete": 1,
        },
    ]

    import tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_stageb_continuation as cont_mod

    class _FakeCase:
        pass

    orig_loader = cont_mod.resume_mod.load_artifact_case
    cont_mod.resume_mod.load_artifact_case = lambda artifact_path: _FakeCase()
    try:
        out = run_selected_trial_row_continuations(
            selected_rows=rows,
            runner_fn=_fake_runner,
        )
    finally:
        cont_mod.resume_mod.load_artifact_case = orig_loader

    assert len(out) == 1
    assert len(captured) == 1
    assert str(captured[0]["selector"]) == "legacy"


def test_load_and_write_stageb_continuation_report_writes_summary(
    tmp_path: Path,
) -> None:
    selected_rows_path = tmp_path / "selected_trial_material_rows.json"
    selected_rows_path.write_text(
        json.dumps(
            [
                {
                    "fixture_label": "control",
                    "fixture_id": "fixture_control",
                    "source_artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/case.json",
                    "selector": "legacy",
                    "candidate_hash": "winner-hash",
                    "source": "stage3_best_phaseB",
                    "lane": "anchor",
                    "final_match": 0.039,
                    "final_score": 0.191,
                    "replay_material_complete": 1,
                },
                {
                    "fixture_label": "control",
                    "fixture_id": "fixture_control",
                    "source_artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/run/final_instances/case.json",
                    "selector": "score_plus_novelty",
                    "candidate_hash": "truth-hash",
                    "source": "phaseA_selected",
                    "lane": "challenger",
                    "final_match": 0.418,
                    "final_score": 0.173,
                    "replay_material_complete": 1,
                },
            ]
        ),
        encoding="utf-8",
    )

    def _fake_runner(case, *, selected_row):
        _ = case
        return {
            "fixture_label": selected_row["fixture_label"],
            "selector": selected_row["selector"],
            "artifact_relpath": selected_row["source_artifact_path"],
            "selected_candidate_hash": selected_row["candidate_hash"],
            "selected_candidate_source": selected_row["source"],
            "selected_candidate_lane": selected_row["lane"],
            "selected_candidate_final_match": selected_row["final_match"],
            "selected_candidate_final_score": selected_row["final_score"],
            "replay_material_complete": selected_row["replay_material_complete"],
            "resume_best_match_ratio": selected_row["final_match"],
            "resume_best_score": selected_row["final_score"],
            "stage35": {
                "selected": 1,
                "accept_reason": "accepted",
                "best_candidate_hash": selected_row["candidate_hash"],
                "archive_count": 1,
                "seed_count": 1,
                "rounds_completed": 1,
                "evals": 2,
                "runtime_seconds": 0.1,
            },
        }

    import tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_stageb_continuation as cont_mod

    class _FakeCase:
        pass

    orig_loader = cont_mod.resume_mod.load_artifact_case
    cont_mod.resume_mod.load_artifact_case = lambda artifact_path: _FakeCase()
    try:
        summary = load_and_write_stageb_continuation_report(
            selected_rows_path=selected_rows_path,
            output_dir=tmp_path / "out",
            runner_fn=_fake_runner,
        )
    finally:
        cont_mod.resume_mod.load_artifact_case = orig_loader

    assert int(summary["row_count"]) == 2
    assert (tmp_path / "out" / "continuation_results.json").exists()
    assert (tmp_path / "out" / "summary.json").exists()
    assert (tmp_path / "out" / "summary.md").exists()
