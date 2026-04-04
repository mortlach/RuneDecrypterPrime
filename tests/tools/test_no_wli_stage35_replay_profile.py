from __future__ import annotations

from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    profile_stage35_replay_hotspots as profile_mod,
)


def test_build_profile_cases_filters_to_expected_fixture_and_selector_pairs() -> None:
    rows = [
        {
            "fixture_label": "control",
            "selector": "legacy",
            "candidate_hash": "legacy-hash",
            "source_artifact_path": "output/mock/control.json",
            "source": "stage3_best_phaseB",
            "lane": "anchor",
            "replay_material_complete": 1,
        },
        {
            "fixture_label": "control",
            "selector": "score_plus_novelty",
            "candidate_hash": "candidate-hash",
            "source_artifact_path": "output/mock/control.json",
            "source": "phaseA_selected",
            "lane": "challenger",
            "replay_material_complete": 1,
        },
        {
            "fixture_label": "control",
            "selector": "score_plus_novelty",
            "candidate_hash": "candidate-hash-newer",
            "source_artifact_path": "output/mock/control_v2.json",
            "source": "phaseA_selected",
            "lane": "challenger",
            "replay_material_complete": 1,
        },
        {
            "fixture_label": "candidate",
            "selector": "oracle_best_explored",
            "candidate_hash": "oracle-hash",
            "source_artifact_path": "output/mock/candidate.json",
            "source": "phaseA_selected",
            "lane": "challenger",
            "replay_material_complete": 1,
        },
        {
            "fixture_label": "candidate",
            "selector": "legacy",
            "candidate_hash": "missing-material",
            "source_artifact_path": "output/mock/candidate.json",
            "source": "stage3_best_phaseB",
            "lane": "anchor",
            "replay_material_complete": 0,
        },
    ]

    cases = profile_mod.build_profile_cases(rows)

    assert [(case.fixture_label, case.selector) for case in cases] == [
        ("control", "legacy"),
        ("control", "score_plus_novelty"),
    ]
    control_candidate = next(case for case in cases if case.selector == "score_plus_novelty")
    assert control_candidate.artifact_relpath == "output/mock/control_v2.json"
    assert control_candidate.candidate_hash == "candidate-hash-newer"


def test_run_profile_case_reports_wallclock_and_stage35_fields() -> None:
    profile_case = profile_mod.Stage35ProfileCase(
        fixture_label="candidate",
        selector="score_plus_novelty",
        artifact_relpath="output/mock/candidate.json",
        candidate_hash="9002ee09917e5a0d",
        source="phaseA_selected",
        lane="challenger",
        selected_row={
            "fixture_label": "candidate",
            "selector": "score_plus_novelty",
            "candidate_hash": "9002ee09917e5a0d",
            "source_artifact_path": "output/mock/candidate.json",
            "source": "phaseA_selected",
            "lane": "challenger",
            "replay_material_complete": 1,
        },
    )

    out = profile_mod.run_profile_case(
        profile_case,
        stage35_cfg_override={"rounds": 1, "beam_width": 2},
        load_case_fn=lambda *, artifact_path: {"artifact_path": str(artifact_path)},
        batch_eval_chunk_size=512,
        runner_fn=lambda artifact_case, *, selected_row, stage35_cfg_override, batch_eval_chunk_size: {
            "selected_candidate_final_match": 0.418,
            "selected_candidate_final_score": 0.172845,
            "resume_best_match_ratio": 0.496,
            "resume_best_score": 0.281,
            "stage35": {
                "accept_passed": 1,
                "accept_reason": "accepted",
                "archive_count": 3,
                "seed_count": 2,
                "rounds_completed": 1,
                "evals": 17,
                "runtime_seconds": 0.125,
                "telemetry": {
                    "row_scoring_seconds": 0.05,
                    "batch_score_seconds": 0.03,
                    "mini_search_total_seconds": 0.08,
                    "archive_update_seconds": 0.01,
                    "archive_rank_seconds": 0.004,
                    "beam_rank_seconds": 0.002,
                    "average_batch_size": 4.0,
                    "average_proposals_generated_per_mini": 7.5,
                    "average_rows_scored_per_mini": 6.0,
                    "average_rows_kept_per_mini": 1.5,
                    "mini_search_duplicate_proposals_skipped": 11,
                    "row_scoring_input_keys_total": 17,
                    "row_scoring_normalized_unique_keys_total": 13,
                    "row_scoring_normalized_duplicate_keys_total": 4,
                },
                "best_candidate_hash": "d9430723f54e973e",
                "best_seed_source": "phasec_phaseb_challenger",
                "best_stage3_source": "phaseA_selected",
                "best_lane": "challenger",
                "best_source_rank": 2,
                "truth_gain_vs_selected_row": 0.078,
            },
        },
    )

    assert out["case_config_id"] == "candidate__score_plus_novelty__chunk512"
    assert out["case_id"] == "candidate__score_plus_novelty"
    assert out["batch_eval_chunk_size"] == 512
    assert out["accept_passed"] == 1
    assert out["accept_reason"] == "accepted"
    assert out["evals"] == 17
    assert out["best_candidate_hash"] == "d9430723f54e973e"
    assert out["selected_truth_match"] == 0.418
    assert out["resume_best_truth_match"] == 0.496
    assert out["truth_gain_vs_selected"] == 0.078
    assert out["wallclock_seconds"] >= 0.0
    assert out["telemetry_row_scoring_seconds"] == 0.05
    assert out["telemetry_average_batch_size"] == 4.0
    assert out["telemetry_mini_search_duplicate_proposals_skipped"] == 11
    assert out["telemetry_row_scoring_input_keys_total"] == 17
    assert out["telemetry_row_scoring_normalized_unique_keys_total"] == 13
    assert out["telemetry_row_scoring_normalized_duplicate_keys_total"] == 4


def test_summarize_profile_rows_reports_fastest_and_slowest_cases() -> None:
    out = profile_mod.summarize_profile_rows(
        [
            {
                "case_id": "control__legacy",
                "accept_passed": 0,
                "wallclock_seconds": 2.0,
            },
            {
                "case_id": "candidate__score_plus_novelty",
                "accept_passed": 1,
                "wallclock_seconds": 5.0,
            },
        ]
    )

    assert out["case_count"] == 2
    assert out["accepted_case_count"] == 1
    assert out["fastest_case_id"] == "control__legacy"
    assert out["slowest_case_id"] == "candidate__score_plus_novelty"
    assert out["slowest_wallclock_seconds"] == 5.0


def test_discover_selected_rows_path_prefers_repo_configured_stageb_file(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_repo_root = tmp_path
    preferred = fake_repo_root / profile_mod.PREFERRED_SELECTED_ROWS_PATH
    preferred.parent.mkdir(parents=True, exist_ok=True)
    preferred.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(profile_mod, "REPO_ROOT", fake_repo_root)

    out = profile_mod.discover_selected_rows_path()

    assert out == preferred
