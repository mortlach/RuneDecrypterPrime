from __future__ import annotations

import json
import math
import sys
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
        "verify_candidate3_phasec_anchor_swap_exact_replay_611_7004.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


SOURCE_ARTIFACT_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260410T222724274436Z__bench_solve_pipeline_no_wli__9557c0f/"
    "final_instances/fixture_001__p9_c3_l1000__text0__seed611__search7004.json"
)
RUN_LABEL = "candidate3_phasec_anchor_swap_611_search7004_exact_stage3_replay_v1"
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
RUN_CONFIG_OVERRIDE = {
    "stage3": {
        "two_phase": {
            "phase_c": {
                "start_policy": "phaseb_topk_anchor_swap_v1",
            }
        }
    }
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


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_str(value: Any) -> str:
    return str(value or "")


def _start_row(flow: Mapping[str, Any], index: int) -> Mapping[str, Any]:
    rows = list(flow.get("phaseC_start_summaries", []) or [])
    if index < len(rows):
        return dict(rows[index])
    return {}


def _first_phaseb_topk_row(flow: Mapping[str, Any]) -> Mapping[str, Any]:
    for row in list(flow.get("phaseC_start_summaries", []) or []):
        if _safe_str(row.get("source")) == "phaseB_topk":
            return dict(row)
    return {}


def _first_finite_match_row(
    rows: list[Mapping[str, Any]],
) -> Mapping[str, Any]:
    best_row: Mapping[str, Any] = {}
    best_match = float("-inf")
    for row in rows:
        match_ratio = _safe_float(row.get("match_ratio"))
        if math.isfinite(match_ratio) and match_ratio > best_match:
            best_match = match_ratio
            best_row = dict(row)
    return dict(best_row)


def extract_retained_stage3_reference(
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    diagnostics = dict(artifact.get("stage3_diagnostics", {}) or {})
    best_truth_start = dict(diagnostics.get("phaseC_best_truth_start_summary", {}) or {})
    best_truth_match = _safe_float(best_truth_start.get("final_match"))
    if math.isfinite(best_truth_match):
        return {
            "match_ratio": float(best_truth_match),
            "source": "phaseC_best_truth_start_summary",
            "stage3_source": _safe_str(best_truth_start.get("source")),
            "candidate_hash": _safe_str(best_truth_start.get("candidate_hash")),
            "source_rank": _safe_int(best_truth_start.get("source_rank")),
        }

    disagreement = dict(diagnostics.get("phaseC_truth_disagreement_summary", {}) or {})
    disagreement_match = _safe_float(disagreement.get("best_truth_match"))
    if math.isfinite(disagreement_match):
        return {
            "match_ratio": float(disagreement_match),
            "source": "phaseC_truth_disagreement_summary",
            "stage3_source": _safe_str(disagreement.get("best_truth_source")),
            "candidate_hash": _safe_str(disagreement.get("best_truth_candidate_hash")),
            "source_rank": 0,
        }

    truth_diag_rows = [
        dict(row)
        for row in list((artifact.get("truth_diagnostics", {}) or {}).get(
            "stage3_topk_truth_diagnostics",
            [],
        ) or [])
    ]
    truth_diag_best = _first_finite_match_row(truth_diag_rows)
    truth_diag_match = _safe_float(truth_diag_best.get("match_ratio"))
    if math.isfinite(truth_diag_match):
        return {
            "match_ratio": float(truth_diag_match),
            "source": "truth_diagnostics.stage3_topk_truth_diagnostics",
            "stage3_source": _safe_str(truth_diag_best.get("source")),
            "candidate_hash": _safe_str(truth_diag_best.get("candidate_hash")),
            "source_rank": _safe_int(truth_diag_best.get("rank")),
        }

    stage3_topk_rows = [dict(row) for row in list(artifact.get("stage3_topk", []) or [])]
    stage3_topk_best = _first_finite_match_row(stage3_topk_rows)
    stage3_topk_match = _safe_float(stage3_topk_best.get("match_ratio"))
    if math.isfinite(stage3_topk_match):
        return {
            "match_ratio": float(stage3_topk_match),
            "source": "stage3_topk",
            "stage3_source": _safe_str(stage3_topk_best.get("source")),
            "candidate_hash": _safe_str(stage3_topk_best.get("candidate_hash")),
            "source_rank": _safe_int(stage3_topk_best.get("rank")),
        }

    artifact_best_match = _safe_float(artifact.get("best_match_ratio"))
    return {
        "match_ratio": float(artifact_best_match),
        "source": "artifact_best_fallback",
        "stage3_source": _safe_str(artifact.get("best_stage")),
        "candidate_hash": "",
        "source_rank": 0,
    }


def build_candidate3_exact_replay_summary(
    *,
    case: Any,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    flow = dict(payload.get("stage3_flow", {}) or {})
    outcome = dict(payload.get("outcome", {}) or {})
    anchor_row = _start_row(flow, 0)
    first_phaseb_row = _first_phaseb_topk_row(flow)
    retained_stage3_reference = extract_retained_stage3_reference(case.artifact)
    baseline_best_match_ratio = _safe_float(case.artifact.get("best_match_ratio"))
    resume_best_match_ratio = _safe_float(payload.get("resume_best_match_ratio"))
    anchor_match = _safe_float(anchor_row.get("final_match"))
    phaseb_match = _safe_float(first_phaseb_row.get("final_match"))
    return {
        "run_label": str(RUN_LABEL),
        "source_artifact_relpath": _relative_path(case.artifact_path),
        "source_run_dir_relpath": _relative_path(case.run_dir),
        "fixture_seed": _safe_int(case.artifact.get("instance_source_key_seed")),
        "search_seed": _safe_int(case.artifact.get("search_seed")),
        "baseline_best_stage": _safe_str(case.artifact.get("best_stage")),
        "baseline_best_match_ratio": float(baseline_best_match_ratio),
        "retained_stage3_reference_match_ratio": float(
            _safe_float(retained_stage3_reference.get("match_ratio"))
        ),
        "retained_stage3_reference_source": _safe_str(
            retained_stage3_reference.get("source")
        ),
        "retained_stage3_reference_stage3_source": _safe_str(
            retained_stage3_reference.get("stage3_source")
        ),
        "retained_stage3_reference_candidate_hash": _safe_str(
            retained_stage3_reference.get("candidate_hash")
        ),
        "retained_stage3_reference_source_rank": _safe_int(
            retained_stage3_reference.get("source_rank")
        ),
        "resume_best_stage": _safe_str(payload.get("resume_best_stage")),
        "resume_best_match_ratio": float(resume_best_match_ratio),
        "resume_best_score": _safe_float(payload.get("resume_best_score")),
        "match_delta_vs_baseline": float(
            resume_best_match_ratio - baseline_best_match_ratio
        ),
        "match_delta_vs_retained_stage3_reference": float(
            resume_best_match_ratio
            - _safe_float(retained_stage3_reference.get("match_ratio"))
        ),
        "resume_source": _safe_str(payload.get("resume_source")),
        "stage35_enabled_effective": _safe_int(
            payload.get("stage35_enabled_effective")
        ),
        "phasec_ran": _safe_int(flow.get("phaseC_ran")),
        "phasec_start_keys_used": _safe_int(flow.get("phaseC_start_keys_used")),
        "phasec_start_policy": _safe_str(flow.get("phaseC_start_policy")),
        "anchor_source": _safe_str(anchor_row.get("source")),
        "anchor_candidate_hash": _safe_str(anchor_row.get("candidate_hash")),
        "anchor_final_match": float(anchor_match),
        "anchor_selected_by_phaseb_topk_anchor_policy": _safe_int(
            anchor_row.get("selected_by_phaseb_topk_anchor_policy")
        ),
        "first_phaseb_topk_source_rank": _safe_int(first_phaseb_row.get("source_rank")),
        "first_phaseb_topk_candidate_hash": _safe_str(
            first_phaseb_row.get("candidate_hash")
        ),
        "first_phaseb_topk_final_match": float(phaseb_match),
        "first_phaseb_topk_selected_by_phaseb_topk_anchor_policy": _safe_int(
            first_phaseb_row.get("selected_by_phaseb_topk_anchor_policy")
        ),
        "phaseb_topk_minus_anchor_final_match": float(phaseb_match - anchor_match),
        "outcome_status": _safe_str(outcome.get("status")),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_candidate3_exact_replay_markdown(
    output_dir: Path,
    *,
    summary: Mapping[str, Any],
) -> None:
    fixture_seed = _safe_int(summary.get("fixture_seed"))
    search_seed = _safe_int(summary.get("search_seed"))
    lines = [
        f"# Candidate 3 Exact Retained Replay: {fixture_seed} / search{search_seed}",
        "",
        "Question:",
        (
            f"- if the Phase-C anchor-swap policy is turned on for retained "
            f"`{fixture_seed}/search{search_seed}`, does the exact Stage-3 replay "
            "improve on the retained Stage-3 reference or materially change the "
            "Phase-C start ordering?"
        ),
        "",
        "Configuration:",
        f"- start policy: `{summary.get('phasec_start_policy')}`",
        f"- stage35 enabled: `{summary.get('stage35_enabled_effective')}`",
        "",
        "Retained baseline versus replay:",
        f"- source: `{summary.get('source_artifact_relpath')}`",
        f"- baseline best: `{summary.get('baseline_best_stage')}` / `{summary.get('baseline_best_match_ratio'):.3f}`",
        (
            "- retained Stage-3 reference: "
            f"`{summary.get('retained_stage3_reference_source')}` / "
            f"`{summary.get('retained_stage3_reference_stage3_source')}` / "
            f"`{summary.get('retained_stage3_reference_match_ratio'):.3f}`"
        ),
        f"- replay best: `{summary.get('resume_best_stage')}` / `{summary.get('resume_best_match_ratio'):.3f}`",
        f"- match delta versus baseline: `{summary.get('match_delta_vs_baseline'):.3f}`",
        (
            "- match delta versus retained Stage-3 reference: "
            f"`{summary.get('match_delta_vs_retained_stage3_reference'):.3f}`"
        ),
        f"- outcome status: `{summary.get('outcome_status')}`",
        "",
        "Replay start ordering:",
        f"- anchor source: `{summary.get('anchor_source')}`",
        f"- anchor candidate hash: `{summary.get('anchor_candidate_hash')}`",
        f"- anchor final match: `{summary.get('anchor_final_match'):.3f}`",
        "- first phaseB_topk start:",
        f"  - source rank: `{summary.get('first_phaseb_topk_source_rank')}`",
        f"  - candidate hash: `{summary.get('first_phaseb_topk_candidate_hash')}`",
        f"  - final match: `{summary.get('first_phaseb_topk_final_match'):.3f}`",
        f"- phaseB-topk minus anchor final match: `{summary.get('phaseb_topk_minus_anchor_final_match'):.3f}`",
        f"- anchor selected by policy: `{summary.get('anchor_selected_by_phaseb_topk_anchor_policy')}`",
        f"- first phaseB_topk selected by policy: `{summary.get('first_phaseb_topk_selected_by_phaseb_topk_anchor_policy')}`",
        "",
        "Scope note:",
        "- stage35 stays disabled so the read stays focused on the candidate3 Phase-C ordering mechanism",
    ]
    (output_dir / "candidate3_exact_replay_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_verification() -> dict[str, Any]:
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
            "run_config_override": dict(RUN_CONFIG_OVERRIDE),
            "scope_note": (
                "exact retained pass keeps stage35 disabled so the read stays "
                "focused on the candidate3 Phase-C anchor ordering mechanism"
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
    summary = build_candidate3_exact_replay_summary(case=case, payload=payload)
    _write_json(output_dir / "candidate3_exact_replay_summary.json", summary)
    write_candidate3_exact_replay_markdown(output_dir, summary=summary)
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
