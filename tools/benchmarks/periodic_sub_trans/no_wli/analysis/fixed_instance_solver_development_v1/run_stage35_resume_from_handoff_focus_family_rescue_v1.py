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
        "run_stage35_resume_from_handoff_focus_family_rescue_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


RUN_LABEL = "stage35_resume_from_handoff_focus_family_rescue_v1"
RUN_MODE = "smoke_preflight"
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

# Smoke-only cap: validate selected-row loading, scorer construction, progress
# and partial-output writeback without launching the real local-rescue search.
SMOKE_STAGE35_CFG_OVERRIDE: dict[str, Any] = {
    "seed_keep": 2,
    "beam_width": 2,
    "archive_keep": 4,
    "rounds": 0,
    "mini_search_steps": 1,
    "mini_search_beam_width": 2,
    "mini_search_top_symbols": 4,
    "mini_search_final_keep": 1,
    "max_runtime_seconds": 30,
    "max_evals": 0,
}


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _relative_text(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
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
        "stage35_status": str(
            stage35.get("status", "") or stage35.get("outcome_status", "") or ""
        ),
        "stage35_reason": str(
            stage35.get("reason", "") or stage35.get("outcome_reason", "") or ""
        ),
        "stage35_selected": _safe_int(stage35.get("selected")),
        "stage35_accept_reason": str(stage35.get("accept_reason", "") or ""),
        "stage35_archive_rows": len(list(stage35.get("archive_rows", []) or [])),
        "stage35_seed_rows_scored": len(
            list(stage35.get("seed_rows_scored", []) or [])
        ),
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
        "science_claim": "none_smoke_preflight_only",
        "recommended_next": (
            "write_runtime_budget_for_real_7005_micro_canary_before_launch"
        ),
    }


def build_readout(summary_row: Mapping[str, Any]) -> str:
    lines = [
        "# Stage35 Resume From Handoff Focus-Family Rescue v1 Smoke Preflight",
        "",
        "Purpose:",
        "- validate selected-row late-stage resume plumbing for `1111/search7005`",
        "- write partial-state and progress artefacts",
        "- avoid launching the real local-rescue science run",
        "",
        "Configuration:",
        f"- candidate hash: `{summary_row['candidate_hash']}`",
        f"- selected source: `{summary_row['selected_source']}`",
        f"- selected lane: `{summary_row['selected_lane']}`",
        "- Stage 3.5 override:",
        "  - `rounds = 0`",
        "  - `seed_keep = 2`",
        "  - `beam_width = 2`",
        "  - `max_runtime_seconds = 30`",
        "",
        "Result:",
        f"- retained best: `{summary_row['retained_best_match_ratio']:.3f}`",
        f"- selected row start: `{summary_row['selected_candidate_final_match']:.3f}`",
        f"- smoke resume best: `{summary_row['resume_best_match_ratio']:.3f}`",
        f"- elapsed seconds: `{summary_row['elapsed_seconds']:.3f}`",
        f"- progress events written: `{summary_row['stage35_progress_events_written']}`",
        f"- partial dumps written: `{summary_row['stage35_partial_dump_write_count']}`",
        "",
        "Interpretation:",
        "- selected-row loading and Stage 3.5 writeback plumbing are usable",
        "- this is not a science result because local-rescue rounds were disabled",
        "- no real micro-canary has been launched",
        "",
        "Recommended Next:",
        "- write a runtime budget and stop condition for the real `1111/search7005` selected-best-frontier micro-canary",
        "- ask before launch if the estimate is about an hour or more",
    ]
    return "\n".join(lines).rstrip() + "\n"


def run_smoke_preflight() -> dict[str, Any]:
    case = resume_mod.load_artifact_case(artifact_path=SOURCE_ARTIFACT_REL_PATH)
    selected_row = load_selected_phasec_row(
        case,
        candidate_hash=TARGET_CANDIDATE_HASH,
        selector=TARGET_SELECTOR,
    )
    retained_best_match_ratio = _safe_float(case.artifact.get("best_match_ratio"))

    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}__{RUN_MODE}"
    candidate_output_dir = output_dir / "search7005_selected_best_frontier_smoke"
    output_dir.mkdir(parents=True, exist_ok=False)

    started = time.perf_counter()
    payload = resume_mod.run_stage35_from_selected_trial_row(
        case,
        selected_row=selected_row,
        stage35_cfg_override=SMOKE_STAGE35_CFG_OVERRIDE,
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
    _write_csv(output_dir / "stage35_resume_smoke_preflight_rows.csv", [summary_row])
    _write_json(
        output_dir / "stage35_resume_smoke_preflight_summary.json",
        {
            "run_label": RUN_LABEL,
            "run_mode": RUN_MODE,
            "output_dir": _relative_path(output_dir),
            "candidate_output_dir": _relative_path(candidate_output_dir),
            "runtime_launched": 1,
            "real_science_runtime_launched": 0,
            "elapsed_seconds": float(elapsed_seconds),
            "recommended_next": str(summary_row["recommended_next"]),
        },
    )
    (output_dir / "stage35_resume_smoke_preflight_readout.md").write_text(
        build_readout(summary_row),
        encoding="utf-8",
    )
    return {
        "run_label": RUN_LABEL,
        "run_mode": RUN_MODE,
        "output_dir": _relative_path(output_dir),
        "elapsed_seconds": float(elapsed_seconds),
        "real_science_runtime_launched": 0,
    }


def main() -> None:
    print(json.dumps(run_smoke_preflight(), sort_keys=True))


if __name__ == "__main__":
    main()
