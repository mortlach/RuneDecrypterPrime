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
        "verify_candidate3_phasec_saved_surface_exact_1111_7001.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    verify_candidate3_phasec_saved_surface_1511_7004 as saved_surface_mod,
    verify_candidate3_phasec_saved_surface_exact_1511_7004 as exact_mod,
)


SOURCE_ARTIFACT_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260411T185426399988Z__bench_solve_pipeline_no_wli__9557c0f/"
    "final_instances/fixture_001__p9_c3_l1000__text0__seed1111__search7001.json"
)
RUN_LABEL = "candidate3_phasec_saved_surface_exact_1111_search7001_v1"
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
    saved_rows = exact_mod._load_saved_start_rows(case.artifact)
    control_rows = exact_mod._prepare_saved_start_rows(saved_rows)
    candidate_rows = saved_surface_mod.build_candidate3_saved_surface_rows(saved_rows)

    _write_json(
        output_dir / "attempt_manifest.json",
        {
            "run_label": str(RUN_LABEL),
            "source_artifact_relpath": _relative_path(case.artifact_path),
            "source_run_dir_relpath": _relative_path(case.run_dir),
            "scope_note": (
                "saved-surface exact replay uses retained phaseC_start_summaries "
                "directly and supports rescue-disabled cases only"
            ),
            "start_surface_count": int(len(saved_rows)),
        },
    )

    control_summary = exact_mod.run_saved_surface_phasec_replay(
        case=case,
        saved_rows=control_rows,
        replay_label="saved_surface_control",
    )
    candidate_summary = exact_mod.run_saved_surface_phasec_replay(
        case=case,
        saved_rows=candidate_rows,
        replay_label="saved_surface_candidate3",
    )
    comparison_summary = exact_mod.build_comparison_summary(
        case=case,
        control_summary=control_summary,
        candidate_summary=candidate_summary,
    )
    comparison_summary = dict(comparison_summary, run_label=str(RUN_LABEL))

    _write_json(output_dir / "control_saved_surface_summary.json", control_summary)
    _write_json(output_dir / "candidate_saved_surface_summary.json", candidate_summary)
    _write_json(output_dir / "comparison_summary.json", comparison_summary)
    _write_json(
        output_dir / "control_saved_surface_start_rows.json",
        list(control_summary.get("start_summaries", []) or []),
    )
    _write_json(
        output_dir / "candidate_saved_surface_start_rows.json",
        list(candidate_summary.get("start_summaries", []) or []),
    )
    exact_mod.write_markdown(
        output_dir,
        comparison_summary=comparison_summary,
        control_summary=control_summary,
        candidate_summary=candidate_summary,
    )

    run_summary = {
        "output_dir": _relative_path(output_dir),
        "source_artifact_relpath": _relative_path(case.artifact_path),
        "fixture_seed": int(case.artifact.get("instance_source_key_seed", 0) or 0),
        "search_seed": int(case.artifact.get("search_seed", 0) or 0),
        "retained_stage3_reference_match_ratio": float(
            comparison_summary.get("retained_stage3_reference_match_ratio", float("nan"))
        ),
        "control_best_match_ratio": float(
            comparison_summary.get("control_best_match_ratio", float("nan"))
        ),
        "candidate_best_match_ratio": float(
            comparison_summary.get("candidate_best_match_ratio", float("nan"))
        ),
        "candidate_minus_control_best_match_ratio": float(
            comparison_summary.get("candidate_minus_control_best_match_ratio", float("nan"))
        ),
        "candidate_reordered_surface": int(
            comparison_summary.get("candidate_reordered_surface", 0) or 0
        ),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    print(json.dumps(run_verification(), sort_keys=True))


if __name__ == "__main__":
    main()
