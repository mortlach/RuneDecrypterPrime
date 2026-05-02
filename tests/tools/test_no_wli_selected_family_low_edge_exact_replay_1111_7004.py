from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004 as replay_mod,
)


pytestmark = pytest.mark.tier_a


def test_build_stage2_resume_override_uses_candidate_fields() -> None:
    base_resume = resume_mod.Stage2ResumeInputs(
        best2_key=[1, 2, 3],
        best2_pt=[4, 5, 6],
        best2_score=1.2,
        best2_match=0.12,
        best2_preview="base",
        stage2_promoted=[{"key": [1, 2, 3], "score": 1.2, "match": 0.12}],
        stage2_entry_score=1.2,
        stage2_entry_score_judge=1.3,
        stage2_topk_row_count=8,
        stage2_promote_top_cfg=16,
        stage2_promoted_from_topk_count=4,
    )
    override = replay_mod._build_stage2_resume_override(
        {"stage2_resume": base_resume},
        override_row={
            "key": [9, 9, 9],
            "score_stage2": 7.5,
            "truth_match": 0.75,
        },
    )

    assert override.best2_key == [9, 9, 9]
    assert override.best2_score == 7.5
    assert override.best2_match == 0.75
    assert override.stage2_topk_row_count == 8
    assert override.stage2_promote_top_cfg == 16


def test_source_artifact_relpath_comes_from_inventory() -> None:
    relpath = replay_mod._source_artifact_relpath(search_seed=replay_mod.SEARCH_SEED)

    assert str(relpath).replace("\\", "/").endswith(
        "20260412T031328680128Z__bench_solve_pipeline_no_wli__9557c0f/"
        "final_instances/fixture_001__p9_c3_l1000__text0__seed1111__search7004.json"
    )


def test_run_verification_writes_attempt_status_with_resume_progress_paths(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(replay_mod, "OUTPUT_BASE_DIR", tmp_path / "out")
    monkeypatch.setattr(replay_mod, "_utc_label", lambda: "20260423T120000Z")
    fake_case = SimpleNamespace(
        artifact_path=tmp_path / "run" / "final_instances" / "toy.json",
        run_dir=tmp_path / "run",
        run_config={"stage3": {}},
        artifact={"columns": 1, "best_match_ratio": 0.5, "best_stage": "stage3_full_refine"},
    )
    monkeypatch.setattr(
        replay_mod,
        "_source_artifact_relpath",
        lambda search_seed=replay_mod.SEARCH_SEED: fake_case.artifact_path,
    )
    monkeypatch.setattr(replay_mod.resume_mod, "load_artifact_case", lambda artifact_path: fake_case)
    monkeypatch.setattr(
        replay_mod.resume_mod,
        "prepare_stage3_resume_inputs_from_case",
        lambda case, run_config, prefer_saved_stage3_prep=True: {
            "stage2_resume": replay_mod.resume_mod.Stage2ResumeInputs(
                best2_key=[1, 2, 3],
                best2_pt=[0, 1, 2],
                best2_score=1.0,
                best2_match=0.1,
                best2_preview="abc",
                stage2_promoted=[{"key": [1, 2, 3]}],
                stage2_entry_score=1.0,
                stage2_entry_score_judge=1.0,
                stage2_topk_row_count=1,
                stage2_promote_top_cfg=1,
                stage2_promoted_from_topk_count=1,
            ),
            "stage3_prep": {"init3_n": 1, "stage3_promoted_keys_count": 1},
        },
    )
    monkeypatch.setattr(
        replay_mod.resume_mod,
        "_build_stage3_prep_from_stage2_resume",
        lambda resume, artifact, run_config: {
            "init3_n": 1,
            "stage3_promoted_keys_count": 1,
        },
    )
    baseline_row = {
        "row_id": "baseline",
        "key": [1, 2, 3],
        "score_stage2": 1.0,
        "truth_match": 0.1,
    }
    candidate_row = {
        "row_id": "candidate",
        "key": [3, 2, 1],
        "score_stage2": 1.2,
        "truth_match": 0.2,
    }
    monkeypatch.setattr(replay_mod.policy_mod, "_topk_rows", lambda final_instance: [baseline_row, candidate_row])
    monkeypatch.setattr(
        replay_mod.policy_mod,
        "_family_rows_for_selected",
        lambda rows, columns: ("family", baseline_row, [baseline_row, candidate_row]),
    )
    monkeypatch.setattr(
        replay_mod.policy_mod,
        "select_selected_family_low_edge_row",
        lambda family_rows, selected_row, score_band_eps: candidate_row,
    )
    monkeypatch.setattr(
        replay_mod.resume_mod,
        "run_stage3_resume_from_artifact",
        lambda *args, **kwargs: {
            "resume_best_match_ratio": 0.6,
            "resume_best_stage": "stage3_full_refine",
            "resume_best_score": 2.0,
            "resume_source": "selected_family_low_edge_eps_0p016_override",
            "stage35_enabled_effective": 0,
            "stage3_resume_status_json_relpath": "output/mock/stage3_resume_status.json",
            "stage3_resume_progress_jsonl_relpath": "output/mock/stage3_resume_progress.jsonl",
            "phasea_gate_snapshot_json_relpath": "output/mock/phasea_gate_snapshot.json",
            "phasec_start_checkpoint_relpath": "output/mock/phasec_start_checkpoints.jsonl",
        },
    )
    monkeypatch.setattr(replay_mod.resume_mod, "write_resume_bundle", lambda payload, output_dir: None)
    monkeypatch.setattr(
        replay_mod,
        "build_exact_replay_summary",
        lambda **kwargs: {
            "run_label": replay_mod.RUN_LABEL,
            "source_artifact_relpath": "output/mock/source.json",
            "source_run_dir_relpath": "output/mock/run",
            "fixture_seed": replay_mod.FIXTURE_SEED,
            "search_seed": replay_mod.SEARCH_SEED,
            "candidate_policy_id": replay_mod.POLICY_ID,
            "family_view_id": replay_mod.POLICY_FAMILY_VIEW_ID,
            "score_band_eps": replay_mod.POLICY_SCORE_BAND_EPS,
            "baseline_best_stage": "stage3_full_refine",
            "baseline_best_match_ratio": 0.5,
            "retained_stage3_reference_match_ratio": 0.5,
            "retained_stage3_reference_source": "saved",
            "retained_stage3_reference_stage3_source": "phaseB",
            "resume_best_stage": "stage3_full_refine",
            "resume_best_match_ratio": 0.6,
            "resume_best_score": 2.0,
            "match_delta_vs_baseline": 0.1,
            "match_delta_vs_retained_stage3_reference": 0.1,
            "resume_source": "selected_family_low_edge_eps_0p016_override",
            "stage35_enabled_effective": 0,
            "baseline_row_id": "baseline",
            "baseline_row_truth_match": 0.1,
            "candidate_row_id": "candidate",
            "candidate_row_truth_match": 0.2,
            "candidate_truth_delta_vs_baseline_row": 0.1,
            "candidate_init3_count": 1,
            "candidate_stage3_promoted_keys_count": 1,
        },
    )
    monkeypatch.setattr(replay_mod, "write_exact_replay_markdown", lambda output_dir, summary: None)

    summary = replay_mod.run_verification(
        phasea_provisional_gate_action_decider=lambda snapshot: {
            "action_contract_id": "phasea_checkpoint_refined_both_v1",
            "action_stop_now": 0,
        }
    )

    assert str(summary["stage3_resume_status_json_relpath"]).endswith("stage3_resume_status.json")
    attempt_status = json.loads(
        (
            tmp_path
            / "out"
            / "20260423T120000Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1"
            / "attempt_status.json"
        ).read_text(encoding="utf-8")
    )
    assert attempt_status["status"] == "completed"
    assert attempt_status["completed"] == 1
    assert attempt_status["phasea_provisional_gate_action_enabled"] == 1
    assert str(attempt_status["stage3_resume_progress_jsonl_relpath"]).endswith(
        "stage3_resume_progress.jsonl"
    )
    assert str(attempt_status["phasea_gate_snapshot_json_relpath"]).endswith(
        "phasea_gate_snapshot.json"
    )
