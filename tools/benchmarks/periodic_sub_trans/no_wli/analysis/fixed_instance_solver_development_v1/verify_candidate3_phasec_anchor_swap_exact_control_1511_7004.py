from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "verify_candidate3_phasec_anchor_swap_exact_control_1511_7004.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    verify_candidate3_phasec_anchor_swap_exact_control_611_7004 as control_mod,
    verify_candidate3_phasec_anchor_swap_exact_replay_611_7004 as exact_mod,
)


SOURCE_ARTIFACT_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260414T020217422155Z__bench_solve_pipeline_no_wli__9557c0f/"
    "final_instances/fixture_001__p9_c3_l1000__text0__seed1511__search7004.json"
)
RUN_LABEL = "candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1"
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
)
ENABLE_STAGE35 = False
RUN_CONFIG_OVERRIDE = None


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def run_verification() -> dict[str, object]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    case = resume_mod.load_artifact_case(artifact_path=REPO_ROOT / SOURCE_ARTIFACT_REL_PATH)
    resume_bundle_dir = output_dir / "resume_bundle"
    resume_bundle_dir.mkdir(parents=True, exist_ok=False)
    _write_json(
        output_dir / "attempt_manifest.json",
        {
            "run_label": str(RUN_LABEL),
            "source_artifact_relpath": _relative_path(case.artifact_path),
            "source_run_dir_relpath": _relative_path(case.run_dir),
            "enable_stage35": int(1 if bool(ENABLE_STAGE35) else 0),
            "run_config_override": None,
            "scope_note": (
                "control retained replay keeps stage35 disabled and leaves the "
                "retained Phase-C start policy unchanged"
            ),
        },
    )
    payload = resume_mod.run_stage3_resume_from_artifact(
        case,
        output_dir=resume_bundle_dir,
        run_config_override=RUN_CONFIG_OVERRIDE,
        enable_stage35=ENABLE_STAGE35,
    )
    resume_mod.write_resume_bundle(payload, output_dir=resume_bundle_dir)
    summary = exact_mod.build_candidate3_exact_replay_summary(case=case, payload=payload)
    summary = dict(summary, run_label=str(RUN_LABEL))
    _write_json(output_dir / "candidate3_exact_control_summary.json", summary)
    control_mod.write_control_markdown(output_dir, summary=summary)
    run_summary = {
        "output_dir": _relative_path(output_dir),
        "resume_bundle_dir": _relative_path(resume_bundle_dir),
        "source_artifact_relpath": str(summary["source_artifact_relpath"]),
        "fixture_seed": int(summary["fixture_seed"]),
        "search_seed": int(summary["search_seed"]),
        "baseline_best_match_ratio": float(summary["baseline_best_match_ratio"]),
        "retained_stage3_reference_match_ratio": float(
            summary["retained_stage3_reference_match_ratio"]
        ),
        "resume_best_match_ratio": float(summary["resume_best_match_ratio"]),
        "match_delta_vs_baseline": float(summary["match_delta_vs_baseline"]),
        "match_delta_vs_retained_stage3_reference": float(
            summary["match_delta_vs_retained_stage3_reference"]
        ),
        "phasec_start_policy": str(summary["phasec_start_policy"]),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    summary = run_verification()
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
