from __future__ import annotations

from typing import Any, Callable, Dict, Sequence

import numpy as np


def run_stage12_pipeline(
    *,
    tier: Any,
    text_id: int,
    key_seed: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    true_sub: np.ndarray,
    sub_len: int,
    wli: Sequence[Sequence[int]],
    direction: Any,
    scorer_stage1: Dict[str, Any],
    scorer_stage1_runtime: Any,
    sub_cipher: Any,
    scorer_stage2: Dict[str, Any],
    scorer_stage2_runtime: Any,
    scorer_stage2_pass1_primary_runtime: Any | None,
    scorer_stage2_pass1_fallback_runtime: Any | None,
    full_cipher: Any,
    scorer_stage2_judge_cfg: Dict[str, Any],
    scorer_stage2_judge_runtime: Any,
    scorer_full_runtime: Any,
    oracle_assist_selection_effective: bool,
    run_stage1_substitution_fn: Callable[..., Dict[str, Any]],
    run_stage2_search_fn: Callable[..., Dict[str, Any]],
    finalize_stage2_archive_fn: Callable[..., Dict[str, Any]],
    mark_oracle_decision_use_fn: Callable[[], None],
    stages: list[Dict[str, Any]],
) -> Dict[str, Any]:
    stage1_results = run_stage1_substitution_fn(
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        true_sub=np.asarray(true_sub, dtype=np.int16),
        sub_len=int(sub_len),
        wli=wli,
        direction=direction,
        scorer_stage1=dict(scorer_stage1),
        scorer_stage1_runtime=scorer_stage1_runtime,
        sub_cipher=sub_cipher,
        stages=stages,
    )
    sub_candidates = list(stage1_results.get("sub_candidates", []))
    sub_key_match = float(stage1_results.get("sub_key_match", 0.0))
    stage1_best_score = float(stage1_results.get("stage1_best_score", float("nan")))
    ev1 = int(stage1_results.get("evals", 0))

    stage2_search = run_stage2_search_fn(
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        wli=wli,
        sub_candidates=sub_candidates,
        direction=direction,
        full_cipher=full_cipher,
        sub_cipher=sub_cipher,
        scorer_stage2=dict(scorer_stage2),
        scorer_stage2_runtime=scorer_stage2_runtime,
        scorer_stage2_pass1_primary_runtime=scorer_stage2_pass1_primary_runtime,
        scorer_stage2_pass1_fallback_runtime=scorer_stage2_pass1_fallback_runtime,
        stages=stages,
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        mark_oracle_decision_use=mark_oracle_decision_use_fn,
    )

    best2_match = float(stage2_search.get("best2_match", float("-inf")))
    best2_score = float(stage2_search.get("best2_score", float("-inf")))
    best2_key = stage2_search.get("best2_key", None)
    best2_pt = stage2_search.get("best2_pt", None)
    best2_preview = str(stage2_search.get("best2_preview", ""))
    stage2_evals_total = int(stage2_search.get("stage2_evals_total", 0))
    stage2_archive = dict(stage2_search.get("stage2_archive", {}))
    stage2_archive_keep = int(stage2_search.get("stage2_archive_keep", 1))
    stage2_promote_top = int(stage2_search.get("stage2_promote_top", 1))
    stage2_entry_score = float(stage2_search.get("stage2_entry_score", float("-inf")))
    stage2_continue_to_gate = bool(stage2_search.get("stage2_continue_to_gate", False))
    stage2_continue_stop_reason = str(stage2_search.get("stage2_continue_stop_reason", ""))

    stage2_finalize = finalize_stage2_archive_fn(
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        stage2_archive=stage2_archive,
        stage2_archive_keep=int(stage2_archive_keep),
        stage2_promote_top=int(stage2_promote_top),
        best2_key=(list(map(int, best2_key)) if best2_key is not None else None),
        best2_pt=(list(map(int, best2_pt)) if best2_pt is not None else None),
        best2_preview=str(best2_preview),
        best2_score=float(best2_score),
        best2_match=float(best2_match),
        scorer_stage2=dict(scorer_stage2),
        scorer_stage2_judge_cfg=dict(scorer_stage2_judge_cfg),
        scorer_stage2_judge_runtime=scorer_stage2_judge_runtime,
        scorer_full_runtime=scorer_full_runtime,
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        mark_oracle_decision_use=mark_oracle_decision_use_fn,
    )

    best2_match = float(stage2_finalize.get("best2_match", float(best2_match)))
    best2_score = float(stage2_finalize.get("best2_score", float(best2_score)))
    best2_key = stage2_finalize.get("best2_key", best2_key)
    best2_pt = stage2_finalize.get("best2_pt", best2_pt)
    best2_preview = str(stage2_finalize.get("best2_preview", best2_preview))
    stage2_ranked = list(stage2_finalize.get("stage2_ranked", []))
    stage2_promoted = list(stage2_finalize.get("stage2_promoted", []))
    stage2_entry_score = float(stage2_finalize.get("stage2_entry_score", float("-inf")))
    stage2_entry_score_judge = float(stage2_finalize.get("stage2_entry_score_judge", float("-inf")))
    stage2_score_match_spearman = float(
        stage2_finalize.get("stage2_score_match_spearman", float("nan"))
    )
    stage2_stage3_space_match = bool(
        stage2_finalize.get("stage2_stage3_space_match", False)
    )
    stage2_topk_payload = list(stage2_finalize.get("stage2_topk_payload", []))
    stage2_topk_has_best_match = bool(
        stage2_finalize.get("stage2_topk_has_best_match", False)
    )

    return dict(
        sub_candidates=sub_candidates,
        sub_key_match=float(sub_key_match),
        stage1_best_score=float(stage1_best_score),
        ev1=int(ev1),
        best2_match=float(best2_match),
        best2_score=float(best2_score),
        best2_key=best2_key,
        best2_pt=best2_pt,
        best2_preview=str(best2_preview),
        stage2_evals_total=int(stage2_evals_total),
        stage2_archive=stage2_archive,
        stage2_archive_keep=int(stage2_archive_keep),
        stage2_promote_top=int(stage2_promote_top),
        stage2_entry_score=float(stage2_entry_score),
        stage2_continue_to_gate=bool(stage2_continue_to_gate),
        stage2_continue_stop_reason=str(stage2_continue_stop_reason),
        stage2_ranked=stage2_ranked,
        stage2_promoted=stage2_promoted,
        stage2_entry_score_judge=float(stage2_entry_score_judge),
        stage2_score_match_spearman=float(stage2_score_match_spearman),
        stage2_stage3_space_match=bool(stage2_stage3_space_match),
        stage2_topk_payload=stage2_topk_payload,
        stage2_topk_has_best_match=bool(stage2_topk_has_best_match),
    )
