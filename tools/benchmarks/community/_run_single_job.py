from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Dict

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.benchmarks.community._campaign_common import load_json, write_json
from tools.benchmarks.community.config import (
    apply_profile_overrides_to_pipeline_module,
    load_profile_catalog_from_dict,
)
from tools.benchmarks.periodic_sub_trans.common.core_enums import (
    BenchmarkOrder,
    InstanceStatus,
    InstanceStopReason,
    PipelineRunMode,
)

DEFAULT_LENGTH = 2376
CAMPAIGN_DEVICE = "cpu"
CAMPAIGN_SCORER_IMPL = "numpy"
_ORDER_TO_RUNNER: Dict[str, Dict[str, str]] = {
    BenchmarkOrder.COL_THEN_SUB.value: {
        "module_name": "tools.benchmarks.periodic_sub_trans.col_then_sub.runner",
        "flavor": "col_then_sub",
        "run_mode": PipelineRunMode.FULL.value,
    },
    BenchmarkOrder.SUB_THEN_COL.value: {
        "module_name": "tools.benchmarks.periodic_sub_trans.sub_then_col.runner",
        "flavor": "sub_then_col",
        "run_mode": PipelineRunMode.FOCUS_SUB_THEN_COL.value,
    },
}


def _find_fixture_length(campaign_config: dict[str, Any], *, text_fixture_id: str, repo_root: Path) -> int:
    fixtures = campaign_config.get("fixtures", [])
    if not isinstance(fixtures, list):
        return DEFAULT_LENGTH
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            continue
        if str(fixture.get("text_fixture_id")) != str(text_fixture_id):
            continue
        direct = fixture.get("length")
        if isinstance(direct, int) and direct > 0:
            return int(direct)
        rel_path = fixture.get("path")
        if isinstance(rel_path, str) and rel_path.strip():
            fixture_path = (repo_root / rel_path).resolve()
            if fixture_path.exists():
                try:
                    data = json.loads(fixture_path.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
                if isinstance(data, dict):
                    for key in ("length", "text_length", "plaintext_length"):
                        val = data.get(key)
                        if isinstance(val, int) and val > 0:
                            return int(val)
    return DEFAULT_LENGTH

def _configure_module_for_campaign_job(
    *,
    module: ModuleType,
    job: dict[str, Any],
    campaign_config: dict[str, Any],
    profile_catalog: dict[str, Any],
    repo_root: Path,
    runner_spec: dict[str, str] | None = None,
) -> None:
    order = str(job["order"])
    run_seed = int(job["run_seed"])
    period = int(job["period"])
    columns = int(job["columns"])
    text_fixture_id = str(job["text_fixture_id"])
    profile_id = str(job["profile_id"])
    resolved_runner = dict(runner_spec) if runner_spec is not None else _ORDER_TO_RUNNER.get(order)
    if resolved_runner is None:
        raise ValueError(f"unsupported order: {order}")
    run_mode = str(resolved_runner["run_mode"])
    profile_name = f"community_{profile_id}"
    heartbeat_seconds = 3600

    profile_catalog_obj = load_profile_catalog_from_dict(profile_catalog)
    profile = profile_catalog_obj.get_profile(profile_id)
    apply_profile_overrides_to_pipeline_module(module, profile)

    length = _find_fixture_length(campaign_config, text_fixture_id=text_fixture_id, repo_root=repo_root)
    tier_name = f"community_{order}_p{period}_c{columns}_l{length}"

    configure_fn = getattr(module, "configure_campaign_run", None)
    if not callable(configure_fn):
        raise ValueError(
            "pipeline module missing configure_campaign_run(...) entrypoint"
        )
    configure_fn(
        run_seed=int(run_seed),
        period=int(period),
        columns=int(columns),
        length=int(length),
        tier_name=str(tier_name),
        run_mode=str(run_mode),
        profile_name=str(profile_name),
        heartbeat_seconds=int(heartbeat_seconds),
        autoskip_proven=False,
        force_rerun_proven=True,
        avoid_repeat_fail=False,
        text_offsets=[0],
        tiers_regex_override=None,
        scorer_impl=str(CAMPAIGN_SCORER_IMPL),
        scorer_stage3_impl_avg_fulltext=str(CAMPAIGN_SCORER_IMPL),
    )


def _pick_run_dir(pre_dirs: set[Path], post_dirs: set[Path]) -> Path:
    new_dirs = sorted(post_dirs - pre_dirs, key=lambda p: p.name)
    if new_dirs:
        return new_dirs[-1]
    if post_dirs:
        return sorted(post_dirs, key=lambda p: p.name)[-1]
    raise RuntimeError("no pipeline run directory found")


def _list_flavor_run_dirs(*, output_root: Path, flavor: str) -> set[Path]:
    base = output_root / "periodic_sub_trans" / str(flavor)
    if not base.exists():
        return set()
    return {p for p in base.iterdir() if p.is_dir()}


def _score_or_none(value: Any) -> float | None:
    try:
        score = float(value)
    except Exception:
        return None
    if not math.isfinite(score):
        return None
    return score


def _stage_num(best_stage: str) -> int:
    text = str(best_stage or "").lower()
    if "stage3" in text:
        return 3
    if "stage2" in text:
        return 2
    if "stage1" in text:
        return 1
    return 0


def _map_status(status: str) -> str:
    raw = str(status).strip().lower()
    if raw in {
        InstanceStatus.SOLVED.value,
        InstanceStatus.UNSOLVED.value,
        InstanceStatus.STALLED.value,
    }:
        return raw
    if raw == InstanceStatus.SKIPPED_PROVEN.value:
        return InstanceStatus.ERROR.value
    return InstanceStatus.ERROR.value


def _map_stop_reason(raw_stop_reason: str, *, mapped_status: str, best_stage: str, stage3_best_score: float | None) -> str:
    raw = str(raw_stop_reason or "").strip().lower()
    if mapped_status == InstanceStatus.SOLVED.value:
        return "solved_threshold_met"
    if raw in {"solved_stage2", "solved_stage3", InstanceStopReason.SOLVED_STAGE_B.value, InstanceStopReason.SOLVED_STAGE_C.value}:
        return "solved_threshold_met"
    if raw == InstanceStopReason.STALLED_NO_IMPROVE.value:
        return "plateau_detected"
    if raw.startswith(InstanceStopReason.AUTOSKIP_PROVEN.value):
        return "invalid_config"
    if raw == InstanceStopReason.COMPLETED_PIPELINE.value:
        if _stage_num(best_stage) >= 3 or stage3_best_score is not None:
            return "stage3_budget_exhausted"
        return "stage2_budget_exhausted"
    return "exception_raised"


def _extract_stage_best_scores(stages: list[dict[str, Any]]) -> tuple[float | None, float | None, float | None]:
    s1: list[float] = []
    s2: list[float] = []
    s3: list[float] = []
    for row in stages:
        stage_name = str(row.get("stage", "")).lower()
        score = _score_or_none(row.get("score"))
        if score is None:
            continue
        if stage_name.startswith("stage1"):
            s1.append(score)
        elif stage_name.startswith("stage2"):
            s2.append(score)
        elif stage_name.startswith("stage3"):
            s3.append(score)
    return (
        (max(s1) if s1 else None),
        (max(s2) if s2 else None),
        (max(s3) if s3 else None),
    )


def _build_result_row(
    *,
    job: dict[str, Any],
    inst: dict[str, Any],
    stages: list[dict[str, Any]],
    fastlm_present: bool,
    run_dir: Path,
) -> dict[str, Any]:
    stage1_best, stage2_best, stage3_best = _extract_stage_best_scores(stages)
    mapped_status = _map_status(str(inst.get("status", "")))
    best_stage = str(inst.get("best_stage", "") or "")
    mapped_stop = _map_stop_reason(
        str(inst.get("stop_reason", "")),
        mapped_status=mapped_status,
        best_stage=best_stage,
        stage3_best_score=stage3_best,
    )
    row = {
        "campaign_id": str(job["campaign_id"]),
        "job_id": str(job["job_id"]),
        "git_sha": str(job["git_sha"]),
        "text_fixture_id": str(job["text_fixture_id"]),
        "period": int(job["period"]),
        "columns": int(job["columns"]),
        "order": str(job["order"]),
        "profile_id": str(job["profile_id"]),
        "run_seed": int(job["run_seed"]),
        "replicate_idx": int(job["replicate_idx"]),
        "config_fingerprint": str(job["config_fingerprint"]),
        "status": mapped_status,
        "stop_reason": mapped_stop,
        "best_match_ratio": float(inst.get("best_match_ratio", 0.0) or 0.0),
        "best_stage": int(_stage_num(best_stage)),
        "total_seconds": float(inst.get("total_seconds", 0.0) or 0.0),
        "total_evals": int(inst.get("total_evals", 0) or 0),
        "stage1_best_score": stage1_best,
        "stage2_best_score": stage2_best,
        "stage3_best_score": stage3_best,
        "output_run_dir": str(run_dir),
        "device": str(CAMPAIGN_DEVICE),
        "scoring_backend": str(CAMPAIGN_SCORER_IMPL),
        "fastlm_present": bool(fastlm_present),
    }
    return row


def run_single_job(
    *,
    job: dict[str, Any],
    campaign_config: dict[str, Any],
    profile_catalog: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    order = str(job["order"])
    runner_spec = _ORDER_TO_RUNNER.get(order)
    if runner_spec is None:
        raise ValueError(f"unsupported order: {order}")
    module_name = str(runner_spec["module_name"])
    flavor = str(runner_spec["flavor"])

    try:
        importlib.import_module("rune_decrypter_prime.scoring.language_model._fastlm")
        fastlm_present = True
    except Exception:
        fastlm_present = False

    pipeline_module = importlib.import_module(module_name)
    _configure_module_for_campaign_job(
        module=pipeline_module,
        job=job,
        campaign_config=campaign_config,
        profile_catalog=profile_catalog,
        repo_root=repo_root,
        runner_spec=runner_spec,
    )

    out_root = repo_root / "output" / "tools" / "benchmarks"
    out_root.mkdir(parents=True, exist_ok=True)
    pre_dirs = _list_flavor_run_dirs(output_root=out_root, flavor=flavor)
    start = time.time()
    pipeline_module.main()
    elapsed = float(time.time() - start)
    post_dirs = _list_flavor_run_dirs(output_root=out_root, flavor=flavor)
    run_dir = _pick_run_dir(pre_dirs, post_dirs)

    instances_path = run_dir / "instances.json"
    stages_path = run_dir / "stages.json"
    if not instances_path.exists():
        raise RuntimeError(f"missing instances.json in run directory: {run_dir}")
    instances = json.loads(instances_path.read_text(encoding="utf-8"))
    stages = json.loads(stages_path.read_text(encoding="utf-8")) if stages_path.exists() else []
    if not isinstance(instances, list) or not instances:
        raise RuntimeError(f"instances.json has no rows: {instances_path}")
    if not isinstance(stages, list):
        stages = []

    inst = instances[-1]
    row = _build_result_row(job=job, inst=inst, stages=stages, fastlm_present=fastlm_present, run_dir=run_dir)
    row["total_seconds"] = float(max(float(row["total_seconds"]), elapsed))
    return row


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single campaign job via existing pipeline scripts.")
    parser.add_argument("--job-json", type=Path, required=True, help="path to one manifest job row json")
    parser.add_argument("--campaign-config", type=Path, required=True, help="path to campaign config json")
    parser.add_argument("--profile-catalog", type=Path, required=True, help="path to profile catalog json")
    parser.add_argument("--output-json", type=Path, required=True, help="path to write job result payload json")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3], help="repo root")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    payload: Dict[str, Any]
    try:
        job = load_json(args.job_json)
        campaign_config = load_json(args.campaign_config)
        profile_catalog = load_json(args.profile_catalog)
        row = run_single_job(
            job=job,
            campaign_config=campaign_config,
            profile_catalog=profile_catalog,
            repo_root=args.repo_root.resolve(),
        )
        payload = {"ok": True, "row": row}
    except Exception as exc:
        payload = {
            "ok": False,
            "error_type": exc.__class__.__name__,
            "error": str(exc),
        }
    write_json(args.output_json, payload)
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
