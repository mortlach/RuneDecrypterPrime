from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from tools.benchmarks.config.no_wli_pipeline_profiles import get_no_wli_pipeline_profile
from tools.benchmarks.periodic_sub_trans.common.policy_spec import AdaptivePolicySpec
from tools.benchmarks.periodic_sub_trans.common.stage_spec import ObjectiveRef, StageSpec


def _objective_from_label(*, label: str, family: str = "char_ngram") -> ObjectiveRef:
    return ObjectiveRef(
        objective_id=str(label),
        family=str(family),
        normalisation="avg",
        window_policy="full_text",
        calibration_id="",
    )


def build_no_wli_stage_specs(*, state: Mapping[str, Any]) -> list[StageSpec]:
    stage1_label = str(state.get("SCORER_STAGE1_LABEL", "A_char1"))
    stage2_label = str(state.get("SCORER_STAGE2_LABEL", "M_char12"))
    stage3_label = str(state.get("SCORER_STAGE3_LABEL", "B_char34"))
    return [
        StageSpec(
            stage_id="stage_a_discovery",
            search_objective=_objective_from_label(label=stage1_label),
            decision_objective=_objective_from_label(label=stage1_label),
            pool_keep=int(state.get("STAGE12_ARCHIVE_KEEP", 192)),
            promote_top=int(state.get("STAGE12_PROMOTE_TOP", 96)),
            basin_cap=0,
            params=dict(stage="A", role="discovery", dedupe_by_basin=False),
        ),
        StageSpec(
            stage_id="stage_b_promotion",
            search_objective=_objective_from_label(label=stage2_label),
            decision_objective=_objective_from_label(label=stage2_label),
            pool_keep=int(state.get("STAGE2_ARCHIVE_KEEP", state.get("STAGE12_ARCHIVE_KEEP", 192))),
            promote_top=int(state.get("STAGE2_PROMOTE_TOP", state.get("STAGE12_PROMOTE_TOP", 96))),
            basin_cap=0,
            params=dict(stage="B", role="promotion", dedupe_by_basin=True),
        ),
        StageSpec(
            stage_id="stage_c_refine",
            search_objective=_objective_from_label(label=stage3_label),
            decision_objective=_objective_from_label(label=stage3_label),
            pool_keep=int(state.get("SAVE_STAGE3_TOPK_LIMIT", 16)),
            promote_top=1,
            basin_cap=0,
            params=dict(stage="C", role="refine", dedupe_by_basin=True),
        ),
    ]


def build_no_wli_stage_specs_from_profile(
    *,
    profile_id: str,
    state: Mapping[str, Any],
) -> list[StageSpec]:
    profile = get_no_wli_pipeline_profile(str(profile_id))
    profile_state = dict(state)
    profile_state["SCORER_STAGE1_LABEL"] = str(profile.scorer_schedule.stage1_label)
    profile_state["SCORER_STAGE2_LABEL"] = str(profile.scorer_schedule.stage2_label)
    profile_state["SCORER_STAGE3_LABEL"] = str(profile.scorer_schedule.stage3_label)
    profile_state["STAGE12_ARCHIVE_KEEP"] = int(profile.stage12_archive_keep)
    profile_state["STAGE12_PROMOTE_TOP"] = int(profile.stage12_promote_top)
    return build_no_wli_stage_specs(state=profile_state)


def build_no_wli_policy_spec(*, state: Mapping[str, Any]) -> AdaptivePolicySpec:
    return AdaptivePolicySpec(
        policy_id="no_wli_adaptive_policy_v1",
        tie_band_eps=float(state.get("STAGE3_SPAN_BASIN_JUDGE_TIE_EPS", 0.0)),
        ambiguity_expand_top_k=int(state.get("STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS", 0)),
        period_scale={},
        columns_scale={},
        params=dict(
            run_mode=str(state.get("PIPELINE_RUN_MODE", "")),
            profile=str(state.get("PROFILE", "")),
        ),
    )


def write_stage_engine_contract_artifacts(
    *,
    run_dir: Path,
    state: Mapping[str, Any],
    write_json_fn,
) -> dict[str, str]:
    stage_specs = build_no_wli_stage_specs(state=state)
    policy_spec = build_no_wli_policy_spec(state=state)
    stage_specs_path = run_dir / "stage_specs.json"
    policy_spec_path = run_dir / "policy_spec.json"
    write_json_fn(stage_specs_path, [s.to_json_dict() for s in stage_specs])
    write_json_fn(policy_spec_path, policy_spec.to_json_dict())
    return {
        "stage_specs_path": str(stage_specs_path),
        "policy_spec_path": str(policy_spec_path),
    }
