from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Sequence, Tuple

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.iteration_outcome import (
    resolve_iteration_outcome,
)
from tools.benchmarks.periodic_sub_trans.no_wli.word_ngram_report import (
    score_word_ngram_report_for_plaintext,
)


def finalize_iteration_and_commit(
    *,
    tier: Any,
    text_id: int,
    key_seed: int,
    off: int,
    offset_used: int,
    stop_reason: str,
    solve_match_threshold: float,
    t0_i: float,
    ev1: int,
    stage2_evals_total: int,
    ev3: int,
    best2_match: float,
    best2_score: float,
    best2_key: Sequence[int] | None,
    best2_pt: Sequence[int] | None,
    best2_preview: str,
    best3_match: float,
    best3_score: float,
    best3_key: Sequence[int] | None,
    pt3: np.ndarray,
    wli: Sequence[Sequence[int]],
    stage1_best_score: float,
    oracle_s1: float,
    oracle_s2: float,
    oracle_s3: float,
    stage2_gap_to_oracle: float,
    stage3_band_name: str,
    stage3_basin_judge_span_calls_total: int,
    stage3_basin_judge_span_calls_active: int,
    stage3_basin_judge_span_calls_rejected_or_gated: int,
    stage3_basin_judge_span_seconds_total: float,
    stage3_basin_judge_unique_end_hash: int,
    oracle_mode: str,
    oracle_consulted_in_decisions: bool,
    sub_key_match: float,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    stage2_topk_payload: List[Dict[str, Any]],
    stage2_topk_has_best_match: bool,
    stage2_diagnostics: Dict[str, Any],
    stage3_topk_payload: List[Dict[str, Any]],
    stage3_diagnostics: Dict[str, Any],
    build_iteration_payloads_fn: Callable[..., Tuple[Dict[str, Any], Dict[str, Any]]],
    commit_iteration_with_checkpoint_fn: Callable[..., None],
    instances: List[Dict[str, Any]],
    derive_outcome_code_fn: Callable[..., str],
    safe_preview_latin_fn: Callable[[Any, Any], str],
    scorer_word_ngram_report_runtime: Any | None = None,
    require_batch_scoring: bool = True,
) -> Dict[str, Any]:
    dt_i = float(time.time() - t0_i)
    iteration_outcome = resolve_iteration_outcome(
        stop_reason=str(stop_reason),
        solve_match_threshold=float(solve_match_threshold),
        dt_i=float(dt_i),
        ev1=int(ev1),
        stage2_evals_total=int(stage2_evals_total),
        ev3=int(ev3),
        best2_match=float(best2_match),
        best2_score=float(best2_score),
        best2_key=best2_key,
        best2_pt=best2_pt,
        best2_preview=str(best2_preview),
        best3_match=float(best3_match),
        best3_score=float(best3_score),
        best3_key=best3_key,
        pt3=np.asarray(pt3, dtype=np.uint8),
        wli=wli,
        stage1_best_score=float(stage1_best_score),
        oracle_s1=float(oracle_s1),
        oracle_s2=float(oracle_s2),
        oracle_s3=float(oracle_s3),
        derive_outcome_code_fn=derive_outcome_code_fn,
        safe_preview_latin_fn=safe_preview_latin_fn,
    )
    best_match = float(iteration_outcome["best_match"])
    best_stage = str(iteration_outcome["best_stage"])
    status = str(iteration_outcome["status"])
    total_evals = int(iteration_outcome["total_evals"])
    final_best_key_idx = iteration_outcome.get("final_best_key_idx", None)
    final_best_plaintext_idx = iteration_outcome.get("final_best_plaintext_idx", None)
    final_best_score = float(iteration_outcome["final_best_score"])
    preview_best = str(iteration_outcome["preview_best"])
    outcome_code = str(iteration_outcome["outcome_code"])
    oracle_scores_payload = dict(iteration_outcome.get("oracle_scores_payload", {}))
    score_minus_oracle_payload = dict(
        iteration_outcome.get("score_minus_oracle_payload", {})
    )
    word_ngram_report = score_word_ngram_report_for_plaintext(
        scorer_runtime=scorer_word_ngram_report_runtime,
        plaintext_idx=final_best_plaintext_idx,
        wli=wli,
        require_batch_scoring=bool(require_batch_scoring),
    )

    inst_row, artifact_payload = build_iteration_payloads_fn(
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        off=int(off),
        offset_used=int(offset_used),
        status=str(status),
        stop_reason=str(stop_reason),
        best_stage=str(best_stage),
        best_match=float(best_match),
        sub_key_match=float(sub_key_match),
        best2_match=float(best2_match),
        best3_match=float(best3_match),
        stage2_gap_to_oracle=float(stage2_gap_to_oracle),
        stage3_band_name=str(stage3_band_name),
        stage3_basin_judge_span_calls_total=int(stage3_basin_judge_span_calls_total),
        stage3_basin_judge_span_calls_active=int(stage3_basin_judge_span_calls_active),
        stage3_basin_judge_span_calls_rejected_or_gated=int(
            stage3_basin_judge_span_calls_rejected_or_gated
        ),
        stage3_basin_judge_span_seconds_total=float(
            stage3_basin_judge_span_seconds_total
        ),
        stage3_basin_judge_unique_end_hash=int(stage3_basin_judge_unique_end_hash),
        oracle_mode=str(oracle_mode),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        dt_i=float(dt_i),
        total_evals=int(total_evals),
        preview_best=str(preview_best),
        outcome_code=str(outcome_code),
        final_best_score=float(final_best_score),
        oracle_scores=oracle_scores_payload,
        score_minus_oracle=score_minus_oracle_payload,
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        final_best_key_idx=final_best_key_idx,
        final_best_plaintext_idx=final_best_plaintext_idx,
        stage2_topk_payload=stage2_topk_payload,
        stage2_topk_has_best_match=bool(stage2_topk_has_best_match),
        stage2_diagnostics=stage2_diagnostics,
        stage3_topk_payload=stage3_topk_payload,
        stage3_diagnostics=stage3_diagnostics,
    )
    inst_row.update(
        word_ngram_judge_active=bool(word_ngram_report.get("word_ngram_judge_active", False)),
        word_ngram_judge_n_positions=int(
            word_ngram_report.get("word_ngram_judge_n_positions", 0) or 0
        ),
        word_ngram_judge_report_xent=word_ngram_report.get("word_ngram_judge_report_xent"),
        word_ngram_judge_trust_score=word_ngram_report.get("word_ngram_judge_trust_score"),
        word_ngram_judge_trust_tier=str(
            word_ngram_report.get("word_ngram_judge_trust_tier", "") or ""
        ),
        word_ngram_judge_inactive_reason=str(
            word_ngram_report.get("word_ngram_judge_inactive_reason", "") or ""
        ),
    )
    artifact_payload["word_ngram_report"] = dict(word_ngram_report)
    instances.append(dict(inst_row))
    commit_iteration_with_checkpoint_fn(
        inst_row=inst_row,
        artifact_payload=artifact_payload,
        status_key=str(status),
    )
    return dict(
        dt_i=float(dt_i),
        status=str(status),
        best_stage=str(best_stage),
        best_match=float(best_match),
        total_evals=int(total_evals),
        outcome_code=str(outcome_code),
    )
