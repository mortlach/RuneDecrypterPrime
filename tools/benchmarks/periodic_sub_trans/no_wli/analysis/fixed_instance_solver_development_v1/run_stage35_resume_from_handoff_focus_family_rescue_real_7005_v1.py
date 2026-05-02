from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage35_resume_from_handoff_focus_family_rescue_real_7005_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


RUN_LABEL = "stage35_resume_from_handoff_focus_family_rescue_real_7005_v1"
RUN_MODE = "real_selected_best_frontier_one_round"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)

SOURCE_ARTIFACT_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260412T053512632846Z__bench_solve_pipeline_no_wli__9557c0f/"
    "best/best_instance.json"
)
TARGET_FIXTURE_SEED = 1111
TARGET_SEARCH_SEED = 7005
TARGET_CANDIDATE_HASH = "c9e69b90b779e318"
TARGET_SELECTOR = "score_plus_novelty"

# Real first cell: no runtime/eval cap, natural stop after one bounded Stage 3.5
# round using the retained same-lane bounded Stage 3.5 shape.
REAL_STAGE35_CFG_OVERRIDE: dict[str, Any] = {
    "seed_keep": 2,
    "beam_width": 1,
    "archive_keep": 12,
    "rounds": 1,
    "mini_search_steps": 1,
    "mini_search_beam_width": 2,
    "mini_search_top_symbols": 10,
    "mini_search_final_keep": 2,
    "mini_search_keep_all_rows": 0,
    "max_runtime_seconds": 0,
    "max_evals": 0,
}


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _relative_text(value: Any) -> str:
    text = str(value or "")
    return text.replace("\\", "/")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if result != result:
        return float(default)
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_selected_phasec_row(
    case: Any,
    *,
    candidate_hash: str,
    selector: str,
) -> dict[str, Any]:
    rows = resume_mod.load_phasec_frontier_rows(
        artifact_path=case.artifact_path,
        artifact=case.artifact,
    )
    for row in rows:
        row_d = dict(row)
        row_hashes = {
            str(row_d.get("candidate_hash", "") or ""),
            str(row_d.get("end_hash", "") or ""),
            str(row_d.get("start_hash", "") or ""),
        }
        if str(candidate_hash) in row_hashes:
            return dict(row_d, selector=str(selector))
    raise ValueError(f"Selected candidate hash not found: {candidate_hash}")


def _stage35_status(stage35: Mapping[str, Any]) -> str:
    return str(stage35.get("status", "") or stage35.get("outcome_status", "") or "")


def _stage35_reason(stage35: Mapping[str, Any]) -> str:
    return str(stage35.get("reason", "") or stage35.get("outcome_reason", "") or "")


def build_summary_row(
    *,
    output_dir: Path,
    candidate_output_dir: Path,
    elapsed_seconds: float,
    selected_row: Mapping[str, Any],
    retained_best_match_ratio: float,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    stage35 = dict(payload.get("stage35", {}) or {})
    retained = _safe_float(retained_best_match_ratio)
    selected_match = _safe_float(payload.get("selected_candidate_final_match"))
    resume_match = _safe_float(payload.get("resume_best_match_ratio"))
    telemetry = dict(stage35.get("telemetry", {}) or {})
    return {
        "run_label": RUN_LABEL,
        "run_mode": RUN_MODE,
        "fixture_seed": TARGET_FIXTURE_SEED,
        "search_seed": TARGET_SEARCH_SEED,
        "candidate_hash": TARGET_CANDIDATE_HASH,
        "selector": TARGET_SELECTOR,
        "output_dir": _relative_path(output_dir),
        "candidate_output_dir": _relative_path(candidate_output_dir),
        "artifact_relpath": _relative_text(payload.get("artifact_relpath", "")),
        "retained_best_match_ratio": retained,
        "selected_candidate_final_match": selected_match,
        "resume_best_match_ratio": resume_match,
        "resume_minus_retained": resume_match - retained,
        "resume_minus_selected": resume_match - selected_match,
        "selected_source": str(selected_row.get("source", "") or ""),
        "selected_lane": str(selected_row.get("lane", "") or ""),
        "stage35_status": _stage35_status(stage35),
        "stage35_reason": _stage35_reason(stage35),
        "stage35_selected": _safe_int(stage35.get("selected")),
        "stage35_accept_reason": str(stage35.get("accept_reason", "") or ""),
        "stage35_rounds_completed": _safe_int(stage35.get("rounds_completed")),
        "stage35_evals": _safe_int(stage35.get("evals")),
        "stage35_archive_rows": len(list(stage35.get("archive_rows", []) or [])),
        "stage35_seed_rows_scored": len(
            list(stage35.get("seed_rows_scored", []) or [])
        ),
        "stage35_mini_search_count": _safe_int(telemetry.get("mini_search_count")),
        "stage35_rows_scored": _safe_int(telemetry.get("mini_search_rows_scored")),
        "stage35_progress_events_written": _safe_int(
            stage35.get("progress_events_written")
        ),
        "stage35_partial_dump_write_count": _safe_int(
            stage35.get("partial_dump_write_count")
        ),
        "stage35_progress_jsonl_relpath": _relative_text(
            payload.get("stage35_progress_jsonl_relpath", "")
        ),
        "stage35_partial_state_relpath": _relative_text(
            payload.get("stage35_partial_state_relpath", "")
        ),
        "elapsed_seconds": float(elapsed_seconds),
        "runtime_launched": 1,
        "natural_stop_condition": "one_bounded_stage35_round_completed",
        "runtime_cap_seconds": 0,
        "recommended_next": (
            "extract_readout_then_decide_whether_7004_secondary_confirmation_is_worth_running"
        ),
    }


def build_readout(summary_row: Mapping[str, Any]) -> str:
    lines = [
        "# Stage35 Resume From Handoff Focus-Family Rescue v1 Real 7005 Run",
        "",
        "Purpose:",
        "- run the first real selected-best-frontier late-stage comparison on `1111/search7005`",
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
        "",
        "Result:",
        f"- status: `{summary_row['stage35_status']}`",
        f"- retained best: `{summary_row['retained_best_match_ratio']:.3f}`",
        f"- selected row start: `{summary_row['selected_candidate_final_match']:.3f}`",
        f"- resume best: `{summary_row['resume_best_match_ratio']:.3f}`",
        f"- delta versus retained: `{summary_row['resume_minus_retained']:+.3f}`",
        f"- delta versus selected start: `{summary_row['resume_minus_selected']:+.3f}`",
        f"- elapsed seconds: `{summary_row['elapsed_seconds']:.3f}`",
        f"- rounds completed: `{summary_row['stage35_rounds_completed']}`",
        f"- evals: `{summary_row['stage35_evals']}`",
        f"- progress events written: `{summary_row['stage35_progress_events_written']}`",
        f"- partial dumps written: `{summary_row['stage35_partial_dump_write_count']}`",
        "",
        "Recommended Next:",
        "- extract the completed bundle and compare it against the retained `0.372` and selected-row start `0.416`",
        "- decide whether the smaller `1111/search7004` selected-row headroom is worth a secondary confirmation run",
    ]
    return "\n".join(lines).rstrip() + "\n"


def run_real_7005() -> dict[str, Any]:
    case = resume_mod.load_artifact_case(artifact_path=SOURCE_ARTIFACT_REL_PATH)
    selected_row = load_selected_phasec_row(
        case,
        candidate_hash=TARGET_CANDIDATE_HASH,
        selector=TARGET_SELECTOR,
    )
    retained_best_match_ratio = _safe_float(case.artifact.get("best_match_ratio"))

    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}__{RUN_MODE}"
    candidate_output_dir = output_dir / "search7005_selected_best_frontier_real"
    output_dir.mkdir(parents=True, exist_ok=False)

    started = time.perf_counter()
    payload = resume_mod.run_stage35_from_selected_trial_row(
        case,
        selected_row=selected_row,
        stage35_cfg_override=REAL_STAGE35_CFG_OVERRIDE,
        output_dir=candidate_output_dir,
    )
    elapsed_seconds = float(time.perf_counter() - started)
    resume_mod.write_resume_bundle(payload, output_dir=candidate_output_dir)

    summary_row = build_summary_row(
        output_dir=output_dir,
        candidate_output_dir=candidate_output_dir,
        elapsed_seconds=elapsed_seconds,
        selected_row=selected_row,
        retained_best_match_ratio=retained_best_match_ratio,
        payload=payload,
    )
    _write_csv(output_dir / "stage35_resume_real_7005_rows.csv", [summary_row])
    _write_json(
        output_dir / "stage35_resume_real_7005_summary.json",
        {
            "run_label": RUN_LABEL,
            "run_mode": RUN_MODE,
            "output_dir": _relative_path(output_dir),
            "candidate_output_dir": _relative_path(candidate_output_dir),
            "runtime_launched": 1,
            "runtime_cap_seconds": 0,
            "natural_stop_condition": "one_bounded_stage35_round_completed",
            "elapsed_seconds": float(elapsed_seconds),
            "recommended_next": str(summary_row["recommended_next"]),
        },
    )
    (output_dir / "stage35_resume_real_7005_readout.md").write_text(
        build_readout(summary_row),
        encoding="utf-8",
    )
    return {
        "run_label": RUN_LABEL,
        "run_mode": RUN_MODE,
        "output_dir": _relative_path(output_dir),
        "elapsed_seconds": float(elapsed_seconds),
        "runtime_cap_seconds": 0,
    }


def main() -> None:
    print(json.dumps(run_real_7005(), sort_keys=True))


if __name__ == "__main__":
    main()
