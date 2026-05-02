from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "verify_candidate1_guard_accept_611_7005.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_outcome import (
    resolve_iteration_outcome,
)


SOURCE_ARTIFACT_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260411T014510194326Z__bench_solve_pipeline_no_wli__9557c0f/"
    "final_instances/fixture_001__p9_c3_l1000__text0__seed611__search7005.json"
)
RUN_LABEL = "candidate1_guard_accept_611_search7005_replay_v1"
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
SELECTED_CANDIDATE_HASH = "8402e41d0897ec0b"
SELECTED_SELECTOR = "score_plus_novelty"
CANDIDATE_STAGE35_CFG_OVERRIDE = {
    "accept_guard_passing_selector_mode": "top_score_then_search",
    "accept_guard_passing_score_band_eps": 0.001,
}


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _truth_match_ratio(
    plaintext_idx: Sequence[Any] | None,
    target_plaintext_idx: Sequence[Any] | None,
) -> float:
    if plaintext_idx is None or target_plaintext_idx is None:
        return float("nan")
    pt = np.asarray(list(plaintext_idx), dtype=np.uint8).reshape(-1)
    target = np.asarray(list(target_plaintext_idx), dtype=np.uint8).reshape(-1)
    if int(pt.size) <= 0 or int(pt.size) != int(target.size):
        return float("nan")
    return float(np.mean(pt == target))


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return _relative_path(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        rows.append(dict(json.loads(text)))
    return rows


def load_selected_phasec_row(
    artifact: Mapping[str, Any],
    *,
    candidate_hash: str,
    selector: str,
) -> dict[str, Any]:
    stage3_diagnostics = dict(artifact.get("stage3_diagnostics", {}) or {})
    phasec_rows = list(stage3_diagnostics.get("phaseC_start_summaries", []) or [])
    for row in phasec_rows:
        row_d = dict(row)
        if str(row_d.get("candidate_hash", "") or "") == str(candidate_hash):
            return dict(row_d, selector=str(selector))
    raise ValueError(
        "Could not find selected phaseC row for candidate hash "
        f"{candidate_hash!r}"
    )


def load_retained_stage35_stage_row(run_dir: Path) -> dict[str, Any]:
    stages_path = run_dir / "stages.json"
    rows = json.loads(stages_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"Expected list payload in {stages_path}")
    for row in rows:
        row_d = dict(row)
        if str(row_d.get("stage", "") or "") == "stage35_substitution_only":
            return row_d
    raise ValueError(f"Missing stage35_substitution_only row in {stages_path}")


def load_retained_followup_finish_row(run_dir: Path) -> dict[str, Any]:
    progress_path = run_dir / "stage35_progress.jsonl"
    rows = _read_jsonl(progress_path)
    for row in reversed(rows):
        row_d = dict(row)
        if str(row_d.get("event", "") or "") == "followup_finish":
            return row_d
    raise ValueError(f"Missing followup_finish event in {progress_path}")


def build_candidate1_comparison_summary(
    *,
    case: Any,
    selected_row: Mapping[str, Any],
    retained_stage_row: Mapping[str, Any],
    retained_followup_row: Mapping[str, Any],
    candidate_payload: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_stage35 = dict(candidate_payload.get("stage35", {}) or {})
    retained_preview_rows = list(
        retained_followup_row.get("archive_preview_rows", []) or []
    )
    retained_top_preview = (
        dict(retained_preview_rows[0]) if len(retained_preview_rows) >= 1 else {}
    )
    retained_second_preview = (
        dict(retained_preview_rows[1]) if len(retained_preview_rows) >= 2 else {}
    )
    candidate_best_candidate_hash = str(
        candidate_stage35.get("best_candidate_hash", "") or ""
    )
    original_run_best_match_ratio = _safe_float(case.artifact.get("best_match_ratio"))
    candidate_resume_best_match_ratio = _safe_float(
        candidate_payload.get("resume_best_match_ratio")
    )
    selected_candidate_final_match = _safe_float(selected_row.get("final_match"))
    selected_candidate_final_score = _safe_float(selected_row.get("final_score"))
    candidate_best_score = _safe_float(candidate_stage35.get("best_score"))
    candidate_best_search_score = _safe_float(
        candidate_stage35.get("best_search_score")
    )
    retained_top_score = _safe_float(retained_stage_row.get("stage35_best_score"))
    retained_top_search_score = _safe_float(
        retained_stage_row.get("stage35_best_search_score")
    )
    baseline_search_score = _safe_float(candidate_stage35.get("baseline_search_score"))

    return {
        "run_label": str(RUN_LABEL),
        "source_artifact_relpath": _relative_path(case.artifact_path),
        "source_run_dir_relpath": _relative_path(case.run_dir),
        "selected_selector": str(selected_row.get("selector", "") or ""),
        "selected_candidate_hash": str(
            selected_row.get("candidate_hash", "") or ""
        ),
        "selected_candidate_source": str(selected_row.get("source", "") or ""),
        "selected_candidate_lane": str(selected_row.get("lane", "") or ""),
        "selected_candidate_source_rank": int(
            selected_row.get("source_rank", 0) or 0
        ),
        "selected_candidate_final_score": float(selected_candidate_final_score),
        "selected_candidate_final_match": float(selected_candidate_final_match),
        "baseline_search_score": float(baseline_search_score),
        "original_run_best_match_ratio": float(original_run_best_match_ratio),
        "retained_accept_passed": int(
            retained_stage_row.get("stage35_accept_passed", 0) or 0
        ),
        "retained_accept_reason": str(
            retained_stage_row.get("stage35_accept_reason", "") or ""
        ),
        "retained_top_archive_score": float(retained_top_score),
        "retained_top_archive_search_score": float(retained_top_search_score),
        "retained_top_preview_candidate_hash": str(
            retained_top_preview.get("candidate_hash", "") or ""
        ),
        "retained_top_preview_score": _safe_float(retained_top_preview.get("score")),
        "retained_top_preview_search_score": _safe_float(
            retained_top_preview.get("search_score")
        ),
        "retained_second_preview_candidate_hash": str(
            retained_second_preview.get("candidate_hash", "") or ""
        ),
        "retained_second_preview_score": _safe_float(
            retained_second_preview.get("score")
        ),
        "retained_second_preview_search_score": _safe_float(
            retained_second_preview.get("search_score")
        ),
        "candidate_accept_passed": int(
            candidate_stage35.get("accept_passed", 0) or 0
        ),
        "candidate_accept_reason": str(
            candidate_stage35.get("accept_reason", "") or ""
        ),
        "candidate_selected_archive_rank": int(
            candidate_stage35.get("selected_archive_rank", 0) or 0
        ),
        "candidate_selected_via_guard_passing_selector": int(
            candidate_stage35.get("selected_via_guard_passing_selector", 0) or 0
        ),
        "candidate_best_candidate_hash": candidate_best_candidate_hash,
        "candidate_best_score": float(candidate_best_score),
        "candidate_best_search_score": float(candidate_best_search_score),
        "candidate_resume_best_match_ratio": float(candidate_resume_best_match_ratio),
        "candidate_matches_retained_second_preview_hash": int(
            1
            if candidate_best_candidate_hash
            and candidate_best_candidate_hash
            == str(retained_second_preview.get("candidate_hash", "") or "")
            else 0
        ),
        "candidate_best_score_minus_retained_top_score": float(
            candidate_best_score - retained_top_score
        ),
        "candidate_best_search_score_minus_retained_top_search_score": float(
            candidate_best_search_score - retained_top_search_score
        ),
        "candidate_resume_best_match_minus_original_run_best_match": float(
            candidate_resume_best_match_ratio - original_run_best_match_ratio
        ),
        "candidate_resume_best_match_minus_selected_candidate_final_match": float(
            candidate_resume_best_match_ratio - selected_candidate_final_match
        ),
    }


def build_projected_no_harm_summary(
    *,
    case: Any,
    projected_payload: Mapping[str, Any],
) -> dict[str, Any]:
    outcome = dict(projected_payload.get("outcome", {}) or {})
    stage3_flow = dict(projected_payload.get("stage3_flow", {}) or {})
    return {
        "run_label": str(RUN_LABEL),
        "source_artifact_relpath": _relative_path(case.artifact_path),
        "source_run_dir_relpath": _relative_path(case.run_dir),
        "original_run_best_match_ratio": _safe_float(case.artifact.get("best_match_ratio")),
        "projected_best_stage": str(projected_payload.get("projected_best_stage", "") or ""),
        "projected_best_match_ratio": _safe_float(
            projected_payload.get("projected_best_match_ratio")
        ),
        "projected_best_score": _safe_float(projected_payload.get("projected_best_score")),
        "projected_stage35_selected": int(stage3_flow.get("stage35_selected", 0) or 0),
        "projected_stage35_best_match": _safe_float(
            stage3_flow.get("stage35_best_match")
        ),
        "projected_stage35_used_for_final_best": int(
            outcome.get("stage35_used_for_final_best", 0) or 0
        ),
        "projected_match_delta_vs_original_run_best": float(
            _safe_float(projected_payload.get("projected_best_match_ratio"))
            - _safe_float(case.artifact.get("best_match_ratio"))
        ),
    }


def write_candidate1_comparison_markdown(
    output_dir: Path,
    *,
    summary: Mapping[str, Any],
) -> None:
    lines = [
        "# Candidate 1 Retained Replay: 611 / search7005",
        "",
        "Question:",
        "- if the stage35 accept step is allowed to choose the best guard-passing archive row, does the retained `611/search7005` case improve materially enough to justify the candidate?",
        "",
        "Retained baseline:",
        f"- selector: `{summary.get('selected_selector')}`",
        f"- selected stage3 candidate: `{summary.get('selected_candidate_hash')}` from `{summary.get('selected_candidate_source')}/{summary.get('selected_candidate_lane')}` rank `{summary.get('selected_candidate_source_rank')}`",
        f"- retained result: accept `{summary.get('retained_accept_passed')}` with reason `{summary.get('retained_accept_reason')}`",
        f"- retained top archive row: score `{summary.get('retained_top_archive_score'):.12f}`, search `{summary.get('retained_top_archive_search_score'):.12f}`",
        f"- retained second preview row: `{summary.get('retained_second_preview_candidate_hash')}` score `{summary.get('retained_second_preview_score'):.12f}`, search `{summary.get('retained_second_preview_search_score'):.12f}`",
        "",
        "Candidate 1 replay:",
        f"- candidate result: accept `{summary.get('candidate_accept_passed')}` with reason `{summary.get('candidate_accept_reason')}`",
        f"- selected archive rank: `{summary.get('candidate_selected_archive_rank')}`",
        f"- selected via guard-passing selector: `{summary.get('candidate_selected_via_guard_passing_selector')}`",
        f"- selected stage35 row: `{summary.get('candidate_best_candidate_hash')}`",
        f"- selected row score/search: `{summary.get('candidate_best_score'):.12f}` / `{summary.get('candidate_best_search_score'):.12f}`",
        f"- replay best match ratio: `{summary.get('candidate_resume_best_match_ratio'):.3f}`",
        "",
        "Readout:",
        f"- candidate matches retained second preview row: `{summary.get('candidate_matches_retained_second_preview_hash')}`",
        f"- score delta versus retained top row: `{summary.get('candidate_best_score_minus_retained_top_score'):.12f}`",
        f"- search-score delta versus retained top row: `{summary.get('candidate_best_search_score_minus_retained_top_search_score'):.12f}`",
        f"- match delta versus original run best: `{summary.get('candidate_resume_best_match_minus_original_run_best_match'):.3f}`",
        f"- match delta versus selected stage3 baseline row: `{summary.get('candidate_resume_best_match_minus_selected_candidate_final_match'):.3f}`",
    ]
    (output_dir / "candidate1_replay_comparison.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def write_projected_no_harm_markdown(
    output_dir: Path,
    *,
    summary: Mapping[str, Any],
) -> None:
    lines = [
        "# Candidate 1 Run-Level No-Harm Projection: 611 / search7005",
        "",
        "Question:",
        "- after the no-harm outcome refinement, does the retained stage3 best still win at the run level when candidate 1 offers a weaker selected stage35 row?",
        "",
        "Projected run-level readout:",
        f"- projected best stage: `{summary.get('projected_best_stage')}`",
        f"- projected best match ratio: `{summary.get('projected_best_match_ratio'):.3f}`",
        f"- projected best score: `{summary.get('projected_best_score'):.12f}`",
        f"- stage35 selected in projection: `{summary.get('projected_stage35_selected')}`",
        f"- projected stage35 best match: `{summary.get('projected_stage35_best_match'):.3f}`",
        f"- stage35 used for final best: `{summary.get('projected_stage35_used_for_final_best')}`",
        f"- match delta versus original run best: `{summary.get('projected_match_delta_vs_original_run_best'):.3f}`",
        "",
        "Interpretation:",
        "- if stage35 is selected but not used for the final best, the no-harm refinement preserved the stronger retained stage3 result while keeping stage35 telemetry.",
    ]
    (output_dir / "candidate1_no_harm_projection_comparison.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_verification() -> dict[str, Any]:
    case = resume_mod.load_artifact_case(artifact_path=SOURCE_ARTIFACT_REL_PATH)
    artifact = dict(case.artifact)
    selected_row = load_selected_phasec_row(
        artifact,
        candidate_hash=SELECTED_CANDIDATE_HASH,
        selector=SELECTED_SELECTOR,
    )
    retained_stage_row = load_retained_stage35_stage_row(case.run_dir)
    retained_followup_row = load_retained_followup_finish_row(case.run_dir)

    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    candidate_output_dir = output_dir / "candidate1_replay"
    candidate_payload = resume_mod.run_stage35_from_selected_trial_row(
        case,
        selected_row=selected_row,
        stage35_cfg_override=CANDIDATE_STAGE35_CFG_OVERRIDE,
        output_dir=candidate_output_dir,
    )
    resume_mod.write_resume_bundle(candidate_payload, output_dir=candidate_output_dir)
    projected_outcome = dict(
        resolve_iteration_outcome(
            stop_reason=str(artifact.get("stop_reason", "unsolved") or "unsolved"),
            solve_match_threshold=float(case.run_config.get("threshold", 0.9) or 0.9),
            dt_i=0.0,
            ev1=0,
            stage2_evals_total=0,
            ev3=0,
            best2_match=0.0,
            best2_score=float("nan"),
            best2_key=None,
            best2_pt=None,
            best2_preview="",
            best3_match=_safe_float(artifact.get("best_match_ratio")),
            best3_score=_safe_float(artifact.get("best_score")),
            best3_key=artifact.get("final_best_key_idx"),
            pt3=np.asarray(
                artifact.get("final_best_plaintext_idx", []) or [],
                dtype=np.uint8,
            ).reshape(-1),
            target_plaintext_idx=artifact.get("target_plaintext_idx"),
            stage35_selected=bool(candidate_payload.get("stage35", {}).get("selected", 0)),
            stage35_best_score=_safe_float(candidate_payload.get("stage35", {}).get("best_score")),
            stage35_best_key=candidate_payload.get("stage35", {}).get("best_key"),
            stage35_best_plaintext_idx=candidate_payload.get("stage35", {}).get(
                "best_plaintext_idx"
            ),
            wli=[],
            stage1_best_score=float("nan"),
            oracle_s1=float("nan"),
            oracle_s2=float("nan"),
            oracle_s3=float("nan"),
            derive_outcome_code_fn=lambda **_: "projected",
            safe_preview_latin_fn=lambda pt, _wli: "".join(chr(int(x) + 65) for x in pt),
        )
    )
    projected_payload = {
        "projected_best_stage": str(projected_outcome.get("best_stage", "") or ""),
        "projected_best_match_ratio": _safe_float(projected_outcome.get("best_match")),
        "projected_best_score": _safe_float(projected_outcome.get("final_best_score")),
        "stage3_flow": {
            "stage35_selected": int(candidate_payload.get("stage35", {}).get("selected", 0) or 0),
            "stage35_best_match": _truth_match_ratio(
                candidate_payload.get("stage35", {}).get("best_plaintext_idx"),
                artifact.get("target_plaintext_idx"),
            ),
        },
        "outcome": dict(projected_outcome),
    }

    comparison_summary = build_candidate1_comparison_summary(
        case=case,
        selected_row=selected_row,
        retained_stage_row=retained_stage_row,
        retained_followup_row=retained_followup_row,
        candidate_payload=candidate_payload,
    )
    projected_no_harm_summary = build_projected_no_harm_summary(
        case=case,
        projected_payload=projected_payload,
    )
    retained_snapshot = {
        "source_artifact_relpath": _relative_path(case.artifact_path),
        "source_run_dir_relpath": _relative_path(case.run_dir),
        "retained_stage35_stage_row": dict(retained_stage_row),
        "retained_followup_finish_row": dict(retained_followup_row),
        "selected_phasec_row": dict(selected_row),
    }
    (output_dir / "retained_snapshot.json").write_text(
        json.dumps(retained_snapshot, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    (output_dir / "candidate1_replay_comparison.json").write_text(
        json.dumps(comparison_summary, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    (output_dir / "candidate1_no_harm_projection_comparison.json").write_text(
        json.dumps(projected_no_harm_summary, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    write_candidate1_comparison_markdown(
        output_dir,
        summary=comparison_summary,
    )
    write_projected_no_harm_markdown(
        output_dir,
        summary=projected_no_harm_summary,
    )
    summary = {
        "output_dir": _relative_path(output_dir),
        "candidate1_replay_dir": _relative_path(candidate_output_dir),
        "selected_candidate_hash": str(
            comparison_summary["selected_candidate_hash"]
        ),
        "candidate_accept_passed": int(
            comparison_summary["candidate_accept_passed"]
        ),
        "candidate_selected_archive_rank": int(
            comparison_summary["candidate_selected_archive_rank"]
        ),
        "candidate_resume_best_match_ratio": float(
            comparison_summary["candidate_resume_best_match_ratio"]
        ),
        "candidate_match_delta_vs_original_run_best": float(
            comparison_summary[
                "candidate_resume_best_match_minus_original_run_best_match"
            ]
        ),
        "projected_best_stage": str(projected_no_harm_summary["projected_best_stage"]),
        "projected_best_match_ratio": float(
            projected_no_harm_summary["projected_best_match_ratio"]
        ),
        "projected_stage35_used_for_final_best": int(
            projected_no_harm_summary["projected_stage35_used_for_final_best"]
        ),
        "projected_match_delta_vs_original_run_best": float(
            projected_no_harm_summary["projected_match_delta_vs_original_run_best"]
        ),
    }
    (output_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    summary = run_verification()
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
