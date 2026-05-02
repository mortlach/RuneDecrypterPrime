from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage35_resume_from_handoff_focus_family_rescue_real_7004_guard_selector_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage35_resume_from_handoff_focus_family_rescue_real_7005_v1 as base_run,
)


RUN_LABEL = "stage35_resume_from_handoff_focus_family_rescue_real_7004_guard_selector_v1"
RUN_MODE = "real_selected_best_frontier_one_round_guard_selector"
SOURCE_ARTIFACT_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260412T031328680128Z__bench_solve_pipeline_no_wli__9557c0f/"
    "best/best_instance.json"
)
TARGET_FIXTURE_SEED = 1111
TARGET_SEARCH_SEED = 7004
TARGET_CANDIDATE_HASH = "6858f26bdc4c4d1f"
TARGET_SELECTOR = "score_plus_novelty"

STAGE35_CFG_OVERRIDE: dict[str, Any] = dict(base_run.REAL_STAGE35_CFG_OVERRIDE)
STAGE35_CFG_OVERRIDE.update(
    {
        "accept_guard_passing_selector_mode": "top_score_then_search",
    }
)


def build_readout(summary_row: dict[str, Any]) -> str:
    lines = [
        "# Stage35 Resume From Handoff Focus-Family Rescue v1 Real 7004 Guard-Selector Run",
        "",
        "Purpose:",
        "- run the secondary guard-selector confirmation on `1111/search7004`",
        "- avoid recomputing upstream stages",
        "- preserve progress and partial-state artefacts",
        "",
        "Configuration:",
        f"- candidate hash: `{summary_row['candidate_hash']}`",
        f"- selected source: `{summary_row['selected_source']}`",
        f"- selected lane: `{summary_row['selected_lane']}`",
        "- Stage 3.5 override:",
        "  - `rounds = 1`",
        "  - `seed_keep = 2`",
        "  - `beam_width = 1`",
        "  - `archive_keep = 12`",
        "  - `max_runtime_seconds = 0`",
        "  - `accept_guard_passing_selector_mode = top_score_then_search`",
        "",
        "Result:",
        f"- status: `{summary_row['stage35_status']}`",
        f"- retained best: `{summary_row['retained_best_match_ratio']:.3f}`",
        f"- selected row start: `{summary_row['selected_candidate_final_match']:.3f}`",
        f"- resume best: `{summary_row['resume_best_match_ratio']:.3f}`",
        f"- delta versus retained: `{summary_row['resume_minus_retained']:+.3f}`",
        f"- delta versus selected start: `{summary_row['resume_minus_selected']:+.3f}`",
        f"- accept reason: `{summary_row['stage35_accept_reason']}`",
        f"- elapsed seconds: `{summary_row['elapsed_seconds']:.3f}`",
        f"- rounds completed: `{summary_row['stage35_rounds_completed']}`",
        f"- evals: `{summary_row['stage35_evals']}`",
        f"- progress events written: `{summary_row['stage35_progress_events_written']}`",
        f"- partial dumps written: `{summary_row['stage35_partial_dump_write_count']}`",
        "",
        "Recommended Next:",
        "- extract the completed bundle and compare it against retained `0.423` and selected-row start `0.432`",
        "- use this as the secondary confirmation read for the guard-selector branch",
    ]
    return "\n".join(lines).rstrip() + "\n"


def run_guard_selector_7004() -> dict[str, Any]:
    base_run.RUN_LABEL = RUN_LABEL
    base_run.RUN_MODE = RUN_MODE
    base_run.SOURCE_ARTIFACT_REL_PATH = SOURCE_ARTIFACT_REL_PATH
    base_run.TARGET_FIXTURE_SEED = TARGET_FIXTURE_SEED
    base_run.TARGET_SEARCH_SEED = TARGET_SEARCH_SEED
    base_run.TARGET_CANDIDATE_HASH = TARGET_CANDIDATE_HASH
    base_run.TARGET_SELECTOR = TARGET_SELECTOR
    base_run.REAL_STAGE35_CFG_OVERRIDE = dict(STAGE35_CFG_OVERRIDE)

    case = base_run.resume_mod.load_artifact_case(
        artifact_path=SOURCE_ARTIFACT_REL_PATH
    )
    selected_row = base_run.load_selected_phasec_row(
        case,
        candidate_hash=TARGET_CANDIDATE_HASH,
        selector=TARGET_SELECTOR,
    )
    retained_best_match_ratio = base_run._safe_float(
        case.artifact.get("best_match_ratio")
    )

    output_dir = (
        base_run.OUTPUT_BASE_DIR / f"{base_run._utc_label()}__{RUN_LABEL}__{RUN_MODE}"
    )
    candidate_output_dir = output_dir / "search7004_selected_best_frontier_guard_selector"
    output_dir.mkdir(parents=True, exist_ok=False)

    started = time.perf_counter()
    payload = base_run.resume_mod.run_stage35_from_selected_trial_row(
        case,
        selected_row=selected_row,
        stage35_cfg_override=STAGE35_CFG_OVERRIDE,
        output_dir=candidate_output_dir,
    )
    elapsed_seconds = float(time.perf_counter() - started)
    base_run.resume_mod.write_resume_bundle(payload, output_dir=candidate_output_dir)

    summary_row = base_run.build_summary_row(
        output_dir=output_dir,
        candidate_output_dir=candidate_output_dir,
        elapsed_seconds=elapsed_seconds,
        selected_row=selected_row,
        retained_best_match_ratio=retained_best_match_ratio,
        payload=payload,
    )
    base_run._write_csv(output_dir / "stage35_resume_real_7004_rows.csv", [summary_row])
    base_run._write_json(
        output_dir / "stage35_resume_real_7004_summary.json",
        {
            "run_label": RUN_LABEL,
            "run_mode": RUN_MODE,
            "output_dir": base_run._relative_path(output_dir),
            "candidate_output_dir": base_run._relative_path(candidate_output_dir),
            "runtime_launched": 1,
            "runtime_cap_seconds": 0,
            "natural_stop_condition": "one_bounded_stage35_round_completed",
            "elapsed_seconds": float(elapsed_seconds),
            "recommended_next": "extract_readout_then_close_or_widen_guard_selector_branch",
        },
    )
    (output_dir / "stage35_resume_real_7004_readout.md").write_text(
        build_readout(summary_row),
        encoding="utf-8",
    )
    return {
        "run_label": RUN_LABEL,
        "run_mode": RUN_MODE,
        "output_dir": base_run._relative_path(output_dir),
        "elapsed_seconds": float(elapsed_seconds),
        "runtime_cap_seconds": 0,
    }


def main() -> None:
    print(json.dumps(run_guard_selector_7004(), sort_keys=True))


if __name__ == "__main__":
    main()
