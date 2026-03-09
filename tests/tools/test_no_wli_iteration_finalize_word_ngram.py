from __future__ import annotations

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import iteration_finalize as finalize_mod


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
        tier=None,
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
        stage2_topk_payload=[{"rank": 1, "plaintext_idx": [1, 2, 3]}],
        stage2_topk_has_best_match=True,
        stage2_diagnostics={},
        stage3_topk_payload=[{"rank": 1, "plaintext_idx": [4, 5, 6]}],
        stage3_diagnostics={},
        build_iteration_payloads_fn=lambda **_: ({}, {}),
        commit_iteration_with_checkpoint_fn=_commit,
        instances=[],
        derive_outcome_code_fn=lambda **_: "ok",
        safe_preview_latin_fn=lambda *_: "",
        scorer_word_ngram_report_runtime=object(),
        require_batch_scoring=True,
    )

    artifact_payload = dict(captured.get("artifact_payload", {}))
    assert "word_ngram_report" in artifact_payload
    assert "stage2_topk_word_ngram_report" in artifact_payload
    assert "stage3_topk_word_ngram_report" in artifact_payload
    assert len(list(artifact_payload["stage2_topk_word_ngram_report"])) == 1
    assert len(list(artifact_payload["stage3_topk_word_ngram_report"])) == 1
