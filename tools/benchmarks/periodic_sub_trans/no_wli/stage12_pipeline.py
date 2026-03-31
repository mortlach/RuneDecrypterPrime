from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Sequence

import numpy as np


_STAGE1_RESULT_REQUIRED_KEYS = (
    "sub_candidates",
    "sub_key_match",
    "stage1_best_score",
    "evals",
)

_STAGE2_SEARCH_REQUIRED_KEYS = (
    "best2_match",
    "best2_score",
    "best2_key",
    "best2_pt",
    "best2_preview",
    "stage2_evals_total",
    "stage2_archive",
    "stage2_archive_keep",
    "stage2_promote_top",
    "stage2_entry_score",
    "stage2_continue_to_gate",
    "stage2_continue_stop_reason",
)

_STAGE2_FINALIZE_REQUIRED_KEYS = (
    "best2_match",
    "best2_score",
    "best2_key",
    "best2_pt",
    "best2_preview",
    "stage2_ranked",
    "stage2_promoted",
    "stage2_entry_score",
    "stage2_entry_score_judge",
    "stage2_score_match_spearman",
    "stage2_stage3_space_match",
    "stage2_topk_payload",
    "stage2_topk_has_best_match",
)


def _require_mapping(*, payload: Any, stage_name: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError(
            f"{stage_name} must return a mapping, got {type(payload).__name__}"
        )
    return payload


def _require_keys(
    *,
    payload: Mapping[str, Any],
    stage_name: str,
    required_keys: Sequence[str],
) -> None:
    missing = [str(key) for key in required_keys if key not in payload]
    if missing:
        raise KeyError(
            f"{stage_name} missing required keys: {', '.join(missing)}"
        )


def _require_list(
    *,
    payload: Mapping[str, Any],
    key: str,
    stage_name: str,
) -> list[Any]:
    value = payload[key]
    if not isinstance(value, list):
        raise TypeError(
            f"{stage_name}.{key} must be a list, got {type(value).__name__}"
        )
    return list(value)


def _require_mapping_value(
    *,
    payload: Mapping[str, Any],
    key: str,
    stage_name: str,
) -> Mapping[Any, Any]:
    value = payload[key]
    if not isinstance(value, Mapping):
        raise TypeError(
            f"{stage_name}.{key} must be a mapping, got {type(value).__name__}"
        )
    return value


def _require_optional_list(
    *,
    payload: Mapping[str, Any],
    key: str,
    stage_name: str,
) -> list[Any] | None:
    value = payload[key]
    if value is None:
        return None
    if not isinstance(value, list):
        raise TypeError(
            f"{stage_name}.{key} must be a list or None, got {type(value).__name__}"
        )
    return list(value)


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
    stage1_results = _require_mapping(
        payload=run_stage1_substitution_fn(
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
        ),
        stage_name="run_stage1_substitution_fn",
    )
    _require_keys(
        payload=stage1_results,
        stage_name="run_stage1_substitution_fn",
        required_keys=_STAGE1_RESULT_REQUIRED_KEYS,
    )
    sub_candidates = _require_list(
        payload=stage1_results,
        key="sub_candidates",
        stage_name="run_stage1_substitution_fn",
    )
    sub_key_match = float(stage1_results["sub_key_match"])
    stage1_best_score = float(stage1_results["stage1_best_score"])
    ev1 = int(stage1_results["evals"])

    stage2_search = _require_mapping(
        payload=run_stage2_search_fn(
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
        ),
        stage_name="run_stage2_search_fn",
    )
    _require_keys(
        payload=stage2_search,
        stage_name="run_stage2_search_fn",
        required_keys=_STAGE2_SEARCH_REQUIRED_KEYS,
    )

    best2_match = float(stage2_search["best2_match"])
    best2_score = float(stage2_search["best2_score"])
    best2_key = _require_optional_list(
        payload=stage2_search,
        key="best2_key",
        stage_name="run_stage2_search_fn",
    )
    best2_pt = _require_optional_list(
        payload=stage2_search,
        key="best2_pt",
        stage_name="run_stage2_search_fn",
    )
    best2_preview = str(stage2_search["best2_preview"])
    stage2_evals_total = int(stage2_search["stage2_evals_total"])
    stage2_archive = dict(
        _require_mapping_value(
            payload=stage2_search,
            key="stage2_archive",
            stage_name="run_stage2_search_fn",
        )
    )
    stage2_archive_keep = int(stage2_search["stage2_archive_keep"])
    stage2_promote_top = int(stage2_search["stage2_promote_top"])
    stage2_entry_score = float(stage2_search["stage2_entry_score"])
    stage2_continue_to_gate = bool(stage2_search["stage2_continue_to_gate"])
    stage2_continue_stop_reason = str(stage2_search["stage2_continue_stop_reason"])

    stage2_finalize = _require_mapping(
        payload=finalize_stage2_archive_fn(
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
        ),
        stage_name="finalize_stage2_archive_fn",
    )
    _require_keys(
        payload=stage2_finalize,
        stage_name="finalize_stage2_archive_fn",
        required_keys=_STAGE2_FINALIZE_REQUIRED_KEYS,
    )

    best2_match = float(stage2_finalize["best2_match"])
    best2_score = float(stage2_finalize["best2_score"])
    best2_key = _require_optional_list(
        payload=stage2_finalize,
        key="best2_key",
        stage_name="finalize_stage2_archive_fn",
    )
    best2_pt = _require_optional_list(
        payload=stage2_finalize,
        key="best2_pt",
        stage_name="finalize_stage2_archive_fn",
    )
    best2_preview = str(stage2_finalize["best2_preview"])
    stage2_ranked = _require_list(
        payload=stage2_finalize,
        key="stage2_ranked",
        stage_name="finalize_stage2_archive_fn",
    )
    stage2_promoted = _require_list(
        payload=stage2_finalize,
        key="stage2_promoted",
        stage_name="finalize_stage2_archive_fn",
    )
    stage2_entry_score = float(stage2_finalize["stage2_entry_score"])
    stage2_entry_score_judge = float(stage2_finalize["stage2_entry_score_judge"])
    stage2_score_match_spearman = float(stage2_finalize["stage2_score_match_spearman"])
    stage2_stage3_space_match = bool(stage2_finalize["stage2_stage3_space_match"])
    stage2_topk_payload = _require_list(
        payload=stage2_finalize,
        key="stage2_topk_payload",
        stage_name="finalize_stage2_archive_fn",
    )
    stage2_topk_has_best_match = bool(stage2_finalize["stage2_topk_has_best_match"])

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
