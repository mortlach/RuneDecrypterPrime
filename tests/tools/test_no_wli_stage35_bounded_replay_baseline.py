from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli import (
    run_stage35_bounded_replay_baseline as bounded_mod,
)


def test_build_case_summary_row_reports_stage35_status_and_paths() -> None:
    out = bounded_mod.build_case_summary_row(
        {
            "fixture_label": "candidate",
            "selector": "score_plus_novelty",
            "artifact_relpath": "output/mock/candidate.json",
            "selected_candidate_hash": "trial-hash",
            "selected_candidate_source": "phaseA_selected",
            "selected_candidate_lane": "challenger",
            "selected_candidate_final_score": 0.172845,
            "selected_candidate_final_match": 0.418,
            "replay_material_complete": 1,
            "resume_best_match_ratio": 0.496,
            "resume_best_score": 0.281,
            "stage35_partial_state_relpath": "output/mock/stage35_partial_state.json",
            "stage35_progress_jsonl_relpath": "output/mock/stage35_progress.jsonl",
            "stage35": {
                "accept_passed": 1,
                "accept_reason": "accepted",
                "outcome_status": "completed",
                "outcome_reason": "",
                "completed": 1,
                "capped": 0,
                "runtime_seconds": 8.15,
                "evals": 4352,
                "rounds_completed": 1,
                "archive_count": 12,
                "seed_count": 2,
                "truth_gain_vs_selected_row": 0.078,
                "truth_gain_vs_phasec_score_winner": 0.457,
                "progress_events_written": 4,
                "partial_dump_write_count": 4,
            },
        }
    )

    assert out["case_id"] == "candidate__score_plus_novelty"
    assert out["accept_passed"] == 1
    assert out["outcome_status"] == "completed"
    assert out["completed"] == 1
    assert out["capped"] == 0
    assert out["runtime_seconds"] == 8.15
    assert out["progress_events_written"] == 4
    assert str(out["stage35_partial_state_relpath"]).endswith(
        "stage35_partial_state.json"
    )


def test_build_fixture_split_rows_reports_preserved_acceptance_split() -> None:
    out = bounded_mod.build_fixture_split_rows(
        [
            {
                "fixture_label": "control",
                "selector": "legacy",
                "accept_passed": 0,
                "accept_reason": "search_score_drop_guard_failed",
                "completed": 1,
                "capped": 0,
            },
            {
                "fixture_label": "control",
                "selector": "score_plus_novelty",
                "accept_passed": 1,
                "accept_reason": "accepted",
                "completed": 1,
                "capped": 0,
            },
            {
                "fixture_label": "candidate",
                "selector": "legacy",
                "accept_passed": 0,
                "accept_reason": "search_score_drop_guard_failed",
                "completed": 1,
                "capped": 0,
            },
            {
                "fixture_label": "candidate",
                "selector": "score_plus_novelty",
                "accept_passed": 1,
                "accept_reason": "accepted",
                "completed": 1,
                "capped": 0,
            },
        ]
    )

    assert [row["fixture_label"] for row in out] == ["candidate", "control"]
    assert all(int(row["acceptance_split_preserved"]) == 1 for row in out)
    candidate_row = next(row for row in out if row["fixture_label"] == "candidate")
    assert candidate_row["legacy_accept_reason"] == "search_score_drop_guard_failed"
    assert candidate_row["candidate_accept_reason"] == "accepted"
