from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_phaseb_challenger_supply_retake_microbatch_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_phaseb_challenger_supply_matrix_v1 as base_extract,
    run_phaseb_challenger_supply_retake_microbatch_v1 as run_mod,
)


RUN_LABEL = run_mod.RUN_LABEL
OUTPUT_BASE_DIR = base_extract.OUTPUT_BASE_DIR


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _plan_payload() -> dict[str, Any]:
    plan_path = REPO_ROOT / run_mod.MATRIX_CONTROL_FILES.plan_output_path
    if not plan_path.exists():
        raise FileNotFoundError(
            f"Missing runtime plan output: {base_extract._relative_path(plan_path)}"
        )
    payload = _read_json(plan_path)
    experiment_run_id = base_extract._safe_str(payload.get("experiment_run_id"))
    if experiment_run_id != str(run_mod.EXPERIMENT_RUN_ID):
        raise ValueError(
            "Unexpected experiment_run_id in plan output: "
            f"expected {run_mod.EXPERIMENT_RUN_ID} got {experiment_run_id}"
        )
    return payload


def build_microbatch_row() -> dict[str, Any]:
    plan_payload = _plan_payload()
    jobs = list(plan_payload.get("jobs", []) or [])
    if len(jobs) != 1:
        raise ValueError(
            f"Expected exactly one job in microbatch plan, found {len(jobs)}"
        )
    preset_summary_by_id = base_extract._plan_preset_summary_by_id(plan_payload)
    job = dict(jobs[0])
    preset_id = base_extract._safe_str(job.get("stage3_tuning_preset_id"))
    preset_summary = dict(preset_summary_by_id[preset_id])
    expected_fingerprint = base_extract._expected_fingerprint_for_job(
        job=job,
        preset_summary=preset_summary,
    )
    window_start, window_end = base_extract._runtime_window(plan_payload)
    matched_runs = base_extract._candidate_runs_by_fingerprint(
        {expected_fingerprint},
        window_start=window_start,
        window_end=window_end,
    )
    matched = matched_runs.get(expected_fingerprint)
    if matched is None:
        raise FileNotFoundError(
            "Missing completed runtime job for microbatch: "
            + "|".join(
                [
                    preset_id,
                    base_extract._safe_str(job.get("instance_fixture_id")),
                    f"search{base_extract._safe_int(job.get('search_seed'))}",
                ]
            )
        )

    best_instance = dict(matched["best_instance"])
    supply = base_extract._supply_metrics(best_instance)
    fixture_seed = base_extract._safe_int(best_instance.get("instance_source_key_seed"))
    search_seed = base_extract._safe_int(best_instance.get("search_seed"))
    baseline = dict(base_extract._baseline_rows_by_case()[(fixture_seed, search_seed)])
    run_manifest = dict(matched.get("run_manifest", {}))

    return {
        "experiment_run_id": run_mod.EXPERIMENT_RUN_ID,
        "preset_id": preset_id,
        "config_label": base_extract._safe_str(preset_summary.get("summary_label")),
        "phaseb_top_n": base_extract._safe_int(preset_summary.get("phaseb_top_n")),
        "stage3_topk_limit": base_extract._safe_int(preset_summary.get("stage3_topk_limit")),
        "fixture_seed": int(fixture_seed),
        "search_seed": int(search_seed),
        "benchmark_case_role": base_extract._safe_str(baseline.get("benchmark_case_role")),
        "run_dir": base_extract._relative_path(Path(matched["run_dir"])),
        "elapsed_seconds": base_extract._safe_float(run_manifest.get("elapsed_seconds")),
        "best_match_ratio": base_extract._safe_float(best_instance.get("best_match_ratio")),
        "retained_best_match_ratio": base_extract._safe_float(
            baseline.get("retained_best_match_ratio")
        ),
        "best_match_delta_vs_retained": (
            base_extract._safe_float(best_instance.get("best_match_ratio"))
            - base_extract._safe_float(baseline.get("retained_best_match_ratio"))
        ),
        "phaseb_topk_saved_count": base_extract._safe_int(
            supply.get("phaseb_topk_saved_count")
        ),
        "phaseb_topk_saved_unique_end_hash": base_extract._safe_int(
            supply.get("phaseb_topk_saved_unique_end_hash")
        ),
        "non_anchor_selected_phaseb_topk_count": base_extract._safe_int(
            supply.get("non_anchor_selected_phaseb_topk_count")
        ),
        "non_selected_phaseb_topk_challenger_count": base_extract._safe_int(
            supply.get("non_selected_phaseb_topk_challenger_count")
        ),
        "non_selected_phaseb_topk_true_spare_unique_challenger_count": base_extract._safe_int(
            supply.get("non_selected_phaseb_topk_true_spare_unique_challenger_count")
        ),
        "non_selected_phaseb_topk_duplicate_of_selected_count": base_extract._safe_int(
            supply.get("non_selected_phaseb_topk_duplicate_of_selected_count")
        ),
        "non_selected_phaseb_topk_true_spare_hashes": list(
            supply.get("non_selected_phaseb_topk_true_spare_hashes", [])
        ),
        "quota_engageable": base_extract._safe_int(supply.get("quota_engageable")),
        "replacement_engageable": base_extract._safe_int(
            supply.get("replacement_engageable")
        ),
        "phasec_winner_candidate_hash": base_extract._safe_str(
            supply.get("phasec_winner_candidate_hash")
        ),
        "phasec_winner_source": base_extract._safe_str(
            supply.get("phasec_winner_source")
        ),
        "phasec_winner_lane": base_extract._safe_str(supply.get("phasec_winner_lane")),
    }


def _write_markdown(output_dir: Path, row: dict[str, Any]) -> None:
    continue_recommendation = (
        "continue"
        if int(row.get("non_selected_phaseb_topk_true_spare_unique_challenger_count", 0)) > 0
        else "stop"
    )
    lines = [
        "# Phase-B Challenger Supply Retake Microbatch v1",
        "",
        "Question:",
        "- can a time-budgeted saved-supply canary create real spare retained `phaseB_topk` challengers on `1111/search7002` before a deeper retry is justified?",
        "",
        "Microbatch:",
        f"- case: `{int(row.get('fixture_seed', 0))}/search{int(row.get('search_seed', 0))}`",
        f"- config: `{base_extract._safe_str(row.get('config_label'))}`",
        f"- run_dir: `{base_extract._safe_str(row.get('run_dir'))}`",
        "",
        "Readout:",
        f"- elapsed_hours: `{base_extract._safe_float(row.get('elapsed_seconds')) / 3600.0:.2f}`",
        f"- best_match_ratio: `{base_extract._safe_float(row.get('best_match_ratio')):.3f}`",
        f"- best_match_delta_vs_retained: `{base_extract._safe_float(row.get('best_match_delta_vs_retained')):.3f}`",
        f"- phaseB_topk_saved_count: `{int(row.get('phaseb_topk_saved_count', 0))}`",
        f"- phaseB_topk_saved_unique_end_hash: `{int(row.get('phaseb_topk_saved_unique_end_hash', 0))}`",
        f"- true_spare_challengers: `{int(row.get('non_selected_phaseb_topk_true_spare_unique_challenger_count', 0))}`",
        f"- duplicate_non_selected_phaseB_topk: `{int(row.get('non_selected_phaseb_topk_duplicate_of_selected_count', 0))}`",
        f"- winner: `{base_extract._safe_str(row.get('phasec_winner_source'))}/{base_extract._safe_str(row.get('phasec_winner_lane'))}`",
        "",
        "Recommendation:",
        f"- `{continue_recommendation}`",
        (
            "- continue only if a real spare challenger appeared or the cheaper canary clearly justifies a deeper retry"
            if continue_recommendation == "continue"
            else "- stop the supply retake early if runtime stays expensive and true spare challengers stay at `0`"
        ),
    ]
    (output_dir / "phaseb_challenger_supply_retake_microbatch_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_extract() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{base_extract._utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    row = build_microbatch_row()
    summary = {
        "run_label": RUN_LABEL,
        "experiment_run_id": run_mod.EXPERIMENT_RUN_ID,
        "panel_path": base_extract._relative_path(REPO_ROOT / run_mod.MICROBATCH_PANEL_PATH),
        "output_dir": base_extract._relative_path(output_dir),
        "row": row,
    }
    base_extract._write_json(output_dir / "phaseb_challenger_supply_retake_microbatch_summary.json", summary)
    base_extract._write_json(output_dir / "phaseb_challenger_supply_retake_microbatch_row.json", row)
    _write_markdown(output_dir, row)

    run_summary = {
        "output_dir": base_extract._relative_path(output_dir),
        "fixture_seed": int(row.get("fixture_seed", 0)),
        "search_seed": int(row.get("search_seed", 0)),
        "preset_id": base_extract._safe_str(row.get("preset_id")),
    }
    base_extract._write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
