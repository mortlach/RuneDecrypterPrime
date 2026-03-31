from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import iteration_finalize as finalize_mod
from tools.benchmarks.periodic_sub_trans.no_wli.runner_bridges import (
    build_iteration_payloads_bridge,
)


pytestmark = pytest.mark.tier_a


def test_finalize_writes_topk_word_ngram_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        finalize_mod,
        "resolve_iteration_outcome",
        lambda **_: dict(
            best_match=0.5,
            best_stage="stage3",
            status="ok",
            total_evals=7,
            final_best_key_idx=[1, 0, 2],
            final_best_plaintext_idx=[10, 11, 12],
            final_best_score=1.23,
            preview_best="abc",
            outcome_code="ok",
            oracle_scores_payload={},
            score_minus_oracle_payload={},
        ),
    )
    monkeypatch.setattr(
        finalize_mod,
        "score_word_ngram_report_for_plaintext",
        lambda **_: dict(
            word_ngram_judge_active=True,
            word_ngram_judge_n_positions=5,
            word_ngram_judge_report_xent=1.1,
            word_ngram_judge_trust_score=0.2,
            word_ngram_judge_trust_tier="low",
            word_ngram_judge_inactive_reason="",
        ),
    )
    monkeypatch.setattr(
        finalize_mod,
        "score_word_ngram_report_for_topk_rows",
        lambda **kwargs: [
            {"rank": int(row.get("rank", 0)), "word_ngram_report": {"word_ngram_judge_active": True}}
            for row in list(kwargs.get("topk_rows", []))
        ],
    )

    captured: dict[str, object] = {}

    def _commit(*, inst_row, artifact_payload, status_key):
        captured["inst_row"] = dict(inst_row)
        captured["artifact_payload"] = dict(artifact_payload)
        captured["status_key"] = str(status_key)

    finalize_mod.finalize_iteration_and_commit(
        tier=SimpleNamespace(period=1, columns=1),
        text_id=1,
        key_seed=2,
        off=0,
        offset_used=0,
        stop_reason="done",
        solve_match_threshold=0.95,
        t0_i=0.0,
        ev1=1,
        stage2_evals_total=2,
        ev3=3,
        best2_match=0.1,
        best2_score=0.2,
        best2_key=[1, 2],
        best2_pt=[3, 4],
        best2_preview="p2",
        best3_match=0.3,
        best3_score=0.4,
        best3_key=[1, 2, 3],
        pt3=np.asarray([1, 2, 3], dtype=np.uint8),
        wli=[],
        stage1_best_score=0.0,
        oracle_s1=0.0,
        oracle_s2=0.0,
        oracle_s3=0.0,
        stage2_gap_to_oracle=0.0,
        stage3_band_name="mid",
        stage3_basin_judge_span_calls_total=0,
        stage3_basin_judge_span_calls_active=0,
        stage3_basin_judge_span_calls_rejected_or_gated=0,
        stage3_basin_judge_span_seconds_total=0.0,
        stage3_basin_judge_unique_end_hash=0,
        oracle_mode="off",
        oracle_consulted_in_decisions=False,
        sub_key_match=0.0,
        ct_idx=np.asarray([1, 2, 3], dtype=np.uint8),
        pt_idx=np.asarray([1, 2, 3], dtype=np.uint8),
        target_key_idx=[1, 1, 1],
        stage2_topk_payload=[{"rank": 1, "plaintext_idx": [1, 2, 3]}],
        stage2_topk_has_best_match=True,
        stage2_diagnostics={},
        stage3_topk_payload=[{"rank": 1, "plaintext_idx": [4, 5, 6]}],
        stage3_diagnostics={},
        stage35_selected=True,
        stage35_best_score=1.5,
        stage35_best_key=[9, 8, 7],
        stage35_best_plaintext_idx=[1, 2, 3],
        stage35_archive_rows=[{"archive_rank": 1, "key_idx": [9, 8, 7]}],
        stage35_seed_rows=[{"seed_rank": 1, "key_idx": [1, 0, 2]}],
        build_iteration_payloads_fn=lambda **_: ({}, {}),
        commit_iteration_with_checkpoint_fn=_commit,
        instances=[],
        derive_outcome_code_fn=lambda **_: "ok",
        safe_preview_latin_fn=lambda *_: "",
        scorer_word_ngram_report_runtime=object(),
        require_batch_scoring=True,
    )

    artifact_payload = dict(captured.get("artifact_payload", {}))
    inst_row = dict(captured.get("inst_row", {}))
    assert "word_ngram_report" in artifact_payload
    assert "stage2_topk_word_ngram_report" in artifact_payload
    assert "stage3_topk_word_ngram_report" in artifact_payload
    assert artifact_payload["target_key_idx"] == [1, 1, 1]
    assert bool(artifact_payload["truth_diagnostics"]["available"]) is True
    assert int(artifact_payload["truth_diagnostics"]["key_hamming_total"]) == 2
    assert int(inst_row["truth_key_hamming_total"]) == 2
    assert len(list(artifact_payload["stage2_topk_word_ngram_report"])) == 1
    assert len(list(artifact_payload["stage3_topk_word_ngram_report"])) == 1
    assert list(artifact_payload["stage35_archive"]) == [
        {"archive_rank": 1, "key_idx": [9, 8, 7]}
    ]
    assert list(artifact_payload["stage35_seed_rows"]) == [
        {"seed_rank": 1, "key_idx": [1, 0, 2]}
    ]


def test_finalize_recovery_path_keeps_phasec_artifacts_and_validity_markers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        finalize_mod,
        "resolve_iteration_outcome",
        lambda **_: dict(
            best_match=0.761,
            best_stage="stage3_full_refine",
            status="unsolved",
            total_evals=123,
            final_best_key_idx=[1, 2, 3, 4],
            final_best_plaintext_idx=[10, 11, 12, 13],
            final_best_score=0.3324,
            preview_best="recovery-preview",
            outcome_code="unsolved",
            oracle_scores_payload={},
            score_minus_oracle_payload={},
        ),
    )
    monkeypatch.setattr(
        finalize_mod,
        "score_word_ngram_report_for_plaintext",
        lambda **_: dict(
            word_ngram_judge_active=False,
            word_ngram_judge_n_positions=0,
            word_ngram_judge_report_xent=None,
            word_ngram_judge_trust_score=None,
            word_ngram_judge_trust_tier="inactive",
            word_ngram_judge_inactive_reason="disabled",
        ),
    )
    monkeypatch.setattr(
        finalize_mod,
        "score_word_ngram_report_for_topk_rows",
        lambda **_: [],
    )

    captured: dict[str, object] = {}

    def _commit(*, inst_row, artifact_payload, status_key):
        captured["inst_row"] = dict(inst_row)
        captured["artifact_payload"] = dict(artifact_payload)
        captured["status_key"] = str(status_key)

    tier = SimpleNamespace(name="fixture_fixture_001_p9_c3_l1000", period=9, columns=3, length=1000)
    state = {
        "SOLVE_MATCH_THRESHOLD": 0.95,
        "PROFILE": "no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        "PIPELINE_RUN_MODE": "adaptive_fixture_v1",
        "_canonical_run_mode": lambda mode: str(mode),
        "ENCODING_DIR": "ltr",
        "ORDER": "sub_then_col",
        "ALPHABET_SIZE": 29,
        "SAVE_STAGE3_TOPK": True,
    }

    finalize_mod.finalize_iteration_and_commit(
        tier=tier,
        text_id=0,
        key_seed=511,
        off=0,
        offset_used=0,
        stop_reason="completed_pipeline",
        solve_match_threshold=0.95,
        t0_i=0.0,
        ev1=1,
        stage2_evals_total=20,
        ev3=30,
        best2_match=0.70,
        best2_score=0.25,
        best2_key=[1, 2, 3, 4],
        best2_pt=[10, 11, 12, 13],
        best2_preview="best2",
        best3_match=0.761,
        best3_score=0.3324,
        best3_key=[1, 2, 3, 4],
        pt3=np.asarray([10, 11, 12, 13], dtype=np.uint8),
        wli=[],
        stage1_best_score=0.1,
        oracle_s1=0.0,
        oracle_s2=0.0,
        oracle_s3=0.0,
        stage2_gap_to_oracle=0.0,
        stage3_band_name="recovery",
        stage3_basin_judge_span_calls_total=5,
        stage3_basin_judge_span_calls_active=5,
        stage3_basin_judge_span_calls_rejected_or_gated=0,
        stage3_basin_judge_span_seconds_total=0.5,
        stage3_basin_judge_unique_end_hash=8,
        oracle_mode="off",
        oracle_consulted_in_decisions=False,
        sub_key_match=0.0,
        ct_idx=np.asarray([1, 2, 3, 4], dtype=np.uint8),
        pt_idx=np.asarray([10, 11, 12, 13], dtype=np.uint8),
        target_key_idx=[1, 2, 3, 4],
        stage2_topk_payload=[],
        stage2_topk_has_best_match=False,
        stage2_diagnostics={},
        stage3_topk_payload=[
            {"rank": 1, "match_ratio": 0.757, "score_raw": -10.1, "plaintext_idx": [10, 11, 12, 13]}
        ],
        stage3_diagnostics={
            "phaseC_enabled_cfg": 1,
            "phaseC_ran": 1,
            "phaseC_start_policy": "novel_challenger_v1",
            "phaseC_checkpoint_jsonl_name": "phasec_start_checkpoints.jsonl",
            "phaseC_checkpoint_rows_written": 6,
            "phaseC_start_keys_used": 6,
            "phaseC_novel_view_id": "prefix_hamming_le_24",
            "phaseC_anchor_candidate_hash": "anchor-hash",
            "phaseC_candidate_pool_eligible_novel_count": 4,
            "phaseC_candidate_pool_eligible_novel_row_count": 7,
            "phaseC_candidate_pool_eligible_novel_source_counts": {
                "phaseB_topk": 2,
                "phaseA_selected": 5,
            },
            "phaseC_start_eligible_novel_count": 2,
            "phaseC_selected_novel_challenger_count": 2,
            "phaseC_eligible_novel_not_selected_count": 2,
            "phaseC_selected_novel_challenger_hashes": ["cand-a", "cand-b"],
            "phaseC_final_winner_lane": "challenger",
            "phaseC_start_summaries": [
                {
                    "start_idx": 1,
                    "lane": "anchor",
                    "source": "stage3_best_phaseB",
                    "source_rank": 1,
                    "candidate_hash": "anchor-hash",
                    "init_key_idx": [1, 2],
                    "init_plaintext_idx": [3, 4],
                    "final_key_idx": [5, 6],
                    "final_plaintext_idx": [7, 8],
                    "selection_bucket": "anchor",
                    "selected_by_novel_policy": 0,
                    "eligible_novel_challenger": 0,
                    "novelty_distance_to_anchor": 0,
                    "novelty_min_distance_to_selected_challenger": None,
                },
                {
                    "start_idx": 2,
                    "lane": "challenger",
                    "source": "phaseB_topk",
                    "source_rank": 2,
                    "candidate_hash": "cand-a",
                    "init_key_idx": [9, 10],
                    "init_plaintext_idx": [11, 12],
                    "final_key_idx": [13, 14],
                    "final_plaintext_idx": [15, 16],
                    "selection_bucket": "novel_reserved",
                    "selected_by_novel_policy": 1,
                    "eligible_novel_challenger": 1,
                    "novelty_distance_to_anchor": 8,
                    "novelty_min_distance_to_selected_challenger": None,
                },
            ],
            "stage35_requested_cfg": 0,
            "stage35_enabled_cfg": 0,
            "stage35_ran": 0,
            "stage35_proof_valid": 1,
            "stage35_proof_invalid_reason": "",
            "stage35_selected": 0,
            "stage35_archive_count": 0,
        },
        stage35_selected=False,
        stage35_best_score=float("nan"),
        stage35_best_key=None,
        stage35_best_plaintext_idx=None,
        stage35_archive_rows=[],
        stage35_seed_rows=[],
        build_iteration_payloads_fn=lambda **kwargs: build_iteration_payloads_bridge(
            state=state,
            **kwargs,
        ),
        commit_iteration_with_checkpoint_fn=_commit,
        instances=[],
        derive_outcome_code_fn=lambda **_: "unsolved",
        safe_preview_latin_fn=lambda *_: "",
        scorer_word_ngram_report_runtime=None,
        require_batch_scoring=True,
    )

    artifact_payload = dict(captured.get("artifact_payload", {}))
    inst_row = dict(captured.get("inst_row", {}))
    assert artifact_payload["best_stage"] == "stage3_full_refine"
    assert artifact_payload["stage3_diagnostics"]["phaseC_ran"] == 1
    assert artifact_payload["stage3_diagnostics"]["phaseC_start_policy"] == "novel_challenger_v1"
    assert (
        artifact_payload["stage3_diagnostics"]["phaseC_novel_view_id"]
        == "prefix_hamming_le_24"
    )
    assert (
        artifact_payload["stage3_diagnostics"]["phaseC_anchor_candidate_hash"]
        == "anchor-hash"
    )
    assert artifact_payload["stage3_diagnostics"]["phaseC_candidate_pool_eligible_novel_count"] == 4
    assert artifact_payload["stage3_diagnostics"]["phaseC_selected_novel_challenger_count"] == 2
    assert artifact_payload["stage3_diagnostics"]["phaseC_selected_novel_challenger_hashes"] == [
        "cand-a",
        "cand-b",
    ]
    assert (
        artifact_payload["stage3_diagnostics"]["phaseC_checkpoint_jsonl_name"]
        == "phasec_start_checkpoints.jsonl"
    )
    assert artifact_payload["stage3_diagnostics"]["phaseC_checkpoint_rows_written"] == 6
    assert artifact_payload["stage3_diagnostics"]["phaseC_start_summaries"][1]["selection_bucket"] == "novel_reserved"
    assert artifact_payload["stage3_diagnostics"]["phaseC_start_summaries"][1]["selected_by_novel_policy"] == 1
    assert artifact_payload["stage35_requested_cfg"] == 0
    assert artifact_payload["stage35_proof_valid"] == 1
    assert artifact_payload["stage35_proof_invalid_reason"] == ""
    assert artifact_payload["stage35_archive"] == []
    assert artifact_payload["stage35_seed_rows"] == []
    assert inst_row["stage35_requested_cfg"] == 0
    assert inst_row["stage35_proof_valid"] == 1
    assert inst_row["stage35_archive_count"] == 0
