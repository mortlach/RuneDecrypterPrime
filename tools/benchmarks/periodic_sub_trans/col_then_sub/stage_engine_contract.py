from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from tools.benchmarks.periodic_sub_trans.common.policy_spec import AdaptivePolicySpec
from tools.benchmarks.periodic_sub_trans.common.stage_spec import ObjectiveRef, StageSpec


def _objective_from_scorer_cfg(*, scorer_cfg: Mapping[str, Any]) -> ObjectiveRef:
    objective_id = str(scorer_cfg.get("objective", "pct.logp.win10"))
    norm = "avg" if ".avg." in objective_id or objective_id.startswith("avg.") else "pct"
    window = "full_text" if "fulltext" in objective_id or "full_text" in objective_id else "win10"
    return ObjectiveRef(
        objective_id=objective_id,
        family="char_ngram",
        normalisation=norm,
        window_policy=window,
    )


def build_col_then_sub_stage_specs(*, state: Mapping[str, Any]) -> list[StageSpec]:
    scorer_stage1 = dict(state.get("SCORER_STAGE1", {}))
    scorer_stage23 = dict(state.get("SCORER_FULL", {}))
    return [
        StageSpec(
            stage_id="stage_a_sub_discovery",
            search_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_stage1),
            decision_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_stage1),
            pool_keep=int(state.get("STAGE12_ARCHIVE_KEEP", 1)),
            promote_top=int(state.get("STAGE12_PROMOTE_TOP", 1)),
            basin_cap=0,
            params=dict(stage="A", role="sub_discovery", dedupe_by_basin=False),
        ),
        StageSpec(
            stage_id="stage_b_col_search",
            search_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_stage23),
            decision_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_stage23),
            pool_keep=int(state.get("STAGE12_ARCHIVE_KEEP", 1)),
            promote_top=int(state.get("STAGE12_PROMOTE_TOP", 1)),
            basin_cap=0,
            params=dict(stage="B", role="col_search", dedupe_by_basin=True),
        ),
        StageSpec(
            stage_id="stage_c_full_refine",
            search_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_stage23),
            decision_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_stage23),
            pool_keep=int(state.get("STAGE3_INITIAL_KEYS", 1)),
            promote_top=1,
            basin_cap=0,
            params=dict(stage="C", role="full_refine", dedupe_by_basin=True),
        ),
    ]


def build_col_then_sub_policy_spec(*, state: Mapping[str, Any]) -> AdaptivePolicySpec:
    return AdaptivePolicySpec(
        policy_id="col_then_sub_adaptive_policy_v1",
        tie_band_eps=0.0,
        ambiguity_expand_top_k=0,
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
    stage_specs = build_col_then_sub_stage_specs(state=state)
    policy_spec = build_col_then_sub_policy_spec(state=state)
    stage_specs_path = run_dir / "stage_specs.json"
    policy_spec_path = run_dir / "policy_spec.json"
    write_json_fn(stage_specs_path, [s.to_json_dict() for s in stage_specs])
    write_json_fn(policy_spec_path, policy_spec.to_json_dict())
    return {
        "stage_specs_path": str(stage_specs_path),
        "policy_spec_path": str(policy_spec_path),
    }
