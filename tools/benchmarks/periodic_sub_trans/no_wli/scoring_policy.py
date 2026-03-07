from __future__ import annotations

from typing import Any, Dict


def scorer_objective_summary(scorer_cfg: Dict[str, Any]) -> str:
    obj = str(scorer_cfg.get("objective", "unknown"))
    policy = scorer_cfg.get("avg_window_policy", None)
    if policy and str(policy).strip().lower() == "full_text":
        win_cfg = "na"
        marker = ".win"
        pos = obj.rfind(marker)
        if pos >= 0:
            suffix = obj[pos + len(marker) :]
            if suffix.isdigit():
                win_cfg = suffix
        if obj.startswith("avg.logp"):
            return (
                f"avg.logp (policy=full_text,span=full_text,"
                f"win_configured={win_cfg},win_effective=FULL_TEXT)"
            )
        return (
            f"{obj} (policy=full_text,span=full_text,"
            f"win_configured={win_cfg},win_effective=FULL_TEXT)"
        )
    if policy:
        return f"{obj} policy={policy}"
    return obj


def is_avg_fulltext_scorer(scorer_cfg: Dict[str, Any]) -> bool:
    obj = str(scorer_cfg.get("objective", "")).strip().lower()
    policy = str(scorer_cfg.get("avg_window_policy", "")).strip().lower()
    return obj.startswith("avg.logp") and policy == "full_text"


def objective_space_key(scorer_cfg: Dict[str, Any]) -> str:
    obj = str(scorer_cfg.get("objective", "")).strip().lower()
    if obj.startswith("avg."):
        return "avg"
    if obj.startswith("pct.") or obj.startswith("energy."):
        return "pct_energy"
    if obj.startswith("neglogp"):
        return "neglogp"
    return obj.split(".", 1)[0] if obj else "unknown"


def effective_stage3_impl(
    scorer_cfg: Dict[str, Any],
    *,
    scorer_impl: str,
    scorer_stage3_impl_avg_fulltext: str,
) -> str:
    if is_avg_fulltext_scorer(scorer_cfg):
        return str(scorer_stage3_impl_avg_fulltext)
    return str(scorer_impl)


def stage2_judge_pool_limit(
    *,
    ranked_count: int,
    archive_keep: int,
    stage2_scorer_cfg: Dict[str, Any] | None,
    stage3_scorer_cfg: Dict[str, Any],
    stage2_promote_by_stage3_judge: bool,
    stage2_entry_band_by_stage3_judge: bool,
    save_stage2_topk: int,
) -> int:
    ranked_n = max(0, int(ranked_count))
    if ranked_n <= 0:
        return 0
    stage2_stage3_space_match = True
    if stage2_scorer_cfg is not None:
        stage2_stage3_space_match = (
            objective_space_key(dict(stage2_scorer_cfg))
            == objective_space_key(dict(stage3_scorer_cfg))
        )
    stage3_span_calibrated = (
        str(stage3_scorer_cfg.get("span_hamming_mode", "off")).strip().lower()
        == "calibrated"
    )
    if (not bool(stage2_promote_by_stage3_judge)) and (
        not bool(stage2_entry_band_by_stage3_judge)
    ):
        if not stage2_stage3_space_match:
            target = max(1, int(archive_keep))
        else:
            target = max(1, int(save_stage2_topk))
        return max(1, min(ranked_n, target))
    if is_avg_fulltext_scorer(stage3_scorer_cfg) or stage3_span_calibrated or (
        not stage2_stage3_space_match
    ):
        target = max(1, int(archive_keep))
    else:
        target = max(1, int(save_stage2_topk))
    return max(1, min(ranked_n, target))


def guard_no_ecdf_usage(
    *,
    scorer_runtime: Any,
    scorer_cfg: Dict[str, Any],
    stage_label: str,
    require_no_ecdf_for_avg_fulltext: bool,
) -> None:
    if not is_avg_fulltext_scorer(scorer_cfg):
        return
    if not bool(require_no_ecdf_for_avg_fulltext):
        return
    ecdf_attr = getattr(scorer_runtime, "_ecdf", None)
    if ecdf_attr is not None:
        raise RuntimeError(
            f"[pipeline_no_wli] ECDF guard failed: stage={stage_label} "
            f"objective={scorer_cfg.get('objective')} "
            "avg_window_policy=full_text unexpectedly has initialized ECDF."
        )
    if hasattr(scorer_runtime, "_ensure_ecdf"):
        def _ecdf_forbidden(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError(
                f"[pipeline_no_wli] ECDF guard failed: stage={stage_label} "
                f"objective={scorer_cfg.get('objective')} "
                "avg_window_policy=full_text attempted ECDF access."
            )

        setattr(scorer_runtime, "_ensure_ecdf", _ecdf_forbidden)
