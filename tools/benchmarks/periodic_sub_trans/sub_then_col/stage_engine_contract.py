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


def build_sub_then_col_stage_specs(*, state: Mapping[str, Any]) -> list[StageSpec]:
    scorer_sub = dict(state.get("SCORER_SUB", {}))
    scorer_full = dict(state.get("SCORER_FULL", {}))
    stage3_init = int(state.get("STAGE3_INITIAL_KEYS", 1))
    return [
        StageSpec(
            stage_id="stage_a_col_probe",
            search_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_sub),
            decision_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_sub),
            pool_keep=int(state.get("COL_KEEP", 1)),
            promote_top=int(state.get("COL_KEEP", 1)),
            basin_cap=0,
            params=dict(stage="A", role="col_probe", dedupe_by_basin=False),
        ),
        StageSpec(
            stage_id="stage_b_sub_refine",
            search_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_sub),
            decision_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_sub),
            pool_keep=stage3_init,
            promote_top=max(1, stage3_init // 2),
            basin_cap=0,
            params=dict(stage="B", role="sub_refine", dedupe_by_basin=True),
        ),
        StageSpec(
            stage_id="stage_c_full_refine",
            search_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_full),
            decision_objective=_objective_from_scorer_cfg(scorer_cfg=scorer_full),
            pool_keep=1,
            promote_top=1,
            basin_cap=0,
            params=dict(stage="C", role="full_refine", dedupe_by_basin=True),
        ),
    ]


def build_sub_then_col_policy_spec(*, state: Mapping[str, Any]) -> AdaptivePolicySpec:
    return AdaptivePolicySpec(
        policy_id="sub_then_col_adaptive_policy_v1",
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
    stage_specs = build_sub_then_col_stage_specs(state=state)
    policy_spec = build_sub_then_col_policy_spec(state=state)
    stage_specs_path = run_dir / "stage_specs.json"
    policy_spec_path = run_dir / "policy_spec.json"
    write_json_fn(stage_specs_path, [s.to_json_dict() for s in stage_specs])
    write_json_fn(policy_spec_path, policy_spec.to_json_dict())
    return {
        "stage_specs_path": str(stage_specs_path),
        "policy_spec_path": str(policy_spec_path),
    }
