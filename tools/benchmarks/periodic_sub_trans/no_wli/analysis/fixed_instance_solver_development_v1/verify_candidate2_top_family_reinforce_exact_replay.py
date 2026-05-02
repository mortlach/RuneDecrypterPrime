from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "verify_candidate2_top_family_reinforce_exact_replay.py"
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
    "20260411T014510194326Z__bench_solve_pipeline_no_wli__9557c0f/"
    "final_instances/fixture_001__p9_c3_l1000__text0__seed611__search7005.json"
)
RUN_LABEL = "candidate2_top_family_reinforce_611_search7005_exact_stage3_replay_v1"
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
CANDIDATE2_RUN_CONFIG_OVERRIDE = {
    "stage3": {
        "two_phase": {
            "family_preservation": {
                "policy": "reinforce_top_family_v1",
                "family_view_id": "prefix_hamming_le_24",
                "reserved_slots": 2,
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


def _family_counts_label(rows: Sequence[Mapping[str, Any]]) -> str:
    counts = Counter(
        str(row.get("family_id", "") or "")
        for row in rows
        if str(row.get("family_id", "") or "")
    )
    if not counts:
        return ""
    return ", ".join(
        f"{family_id}:{int(count)}"
        for family_id, count in sorted(
            counts.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )
    )


def build_candidate2_exact_replay_summary(
    *,
    case: Any,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    flow = dict(payload.get("stage3_flow", {}) or {})
    outcome = dict(payload.get("outcome", {}) or {})
    downstream_summaries = list(flow.get("phaseB_downstream_selected_summaries", []) or [])
    baseline_best_match_ratio = _safe_float(case.artifact.get("best_match_ratio"))
    resume_best_match_ratio = _safe_float(payload.get("resume_best_match_ratio"))
    return {
        "run_label": str(RUN_LABEL),
        "source_artifact_relpath": _relative_path(case.artifact_path),
        "source_run_dir_relpath": _relative_path(case.run_dir),
        "fixture_seed": _safe_int(case.artifact.get("instance_source_key_seed")),
        "search_seed": _safe_int(case.artifact.get("search_seed")),
        "baseline_best_stage": str(case.artifact.get("best_stage", "") or ""),
        "baseline_best_match_ratio": float(baseline_best_match_ratio),
        "resume_best_stage": str(payload.get("resume_best_stage", "") or ""),
        "resume_best_match_ratio": float(resume_best_match_ratio),
        "resume_best_score": _safe_float(payload.get("resume_best_score")),
        "match_delta_vs_baseline": float(
            resume_best_match_ratio - baseline_best_match_ratio
        ),
        "resume_source": str(payload.get("resume_source", "") or ""),
        "stage35_enabled_effective": _safe_int(
            payload.get("stage35_enabled_effective")
        ),
        "phaseb_family_preservation_policy": str(
            flow.get("phaseB_family_preservation_policy", "") or ""
        ),
        "phaseb_family_view_id": str(flow.get("phaseB_family_view_id", "") or ""),
        "phaseb_family_reserved_slots": _safe_int(
            flow.get("phaseB_family_reserved_slots")
        ),
        "phaseb_family_count_in_top_band": _safe_int(
            flow.get("phaseB_family_count_in_top_band")
        ),
        "phaseb_family_preserved_count": _safe_int(
            flow.get("phaseB_family_preserved_count")
        ),
        "phaseb_family_reservation_applied": _safe_int(
            flow.get("phaseB_family_reservation_applied")
        ),
        "phaseb_downstream_selected_count": _safe_int(
            flow.get("phaseB_downstream_selected_count")
        ),
        "phaseb_downstream_selected_unique_end_hash": _safe_int(
            flow.get("phaseB_downstream_selected_unique_end_hash")
        ),
        "phaseb_downstream_selected_family_counts": _family_counts_label(
            downstream_summaries
        ),
        "phasec_ran": _safe_int(flow.get("phaseC_ran")),
        "phasec_start_keys_used": _safe_int(flow.get("phaseC_start_keys_used")),
        "phasec_start_policy": str(flow.get("phaseC_start_policy", "") or ""),
        "outcome_stage35_used_for_final_best": _safe_int(
            outcome.get("stage35_used_for_final_best")
        ),
        "outcome_status": str(outcome.get("status", "") or ""),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_candidate2_exact_replay_markdown(
    output_dir: Path,
    *,
    summary: Mapping[str, Any],
) -> None:
    lines = [
        "# Candidate 2 Exact Retained Replay: 611 / search7005",
        "",
        "Question:",
        "- if the Phase-B top-family reinforcement hook is turned on for the retained `611/search7005` case, does the exact Stage-3 replay produce a better run-level result or a materially different downstream selection shape?",
        "",
        "Configuration:",
        f"- runtime proxy: `{summary.get('phaseb_family_preservation_policy')}`",
        f"- family view: `{summary.get('phaseb_family_view_id')}`",
        f"- reserved slots: `{summary.get('phaseb_family_reserved_slots')}`",
        f"- stage35 enabled: `{summary.get('stage35_enabled_effective')}`",
        "",
        "Baseline versus replay:",
        f"- source: `{summary.get('source_artifact_relpath')}`",
        f"- baseline best: `{summary.get('baseline_best_stage')}` / `{summary.get('baseline_best_match_ratio'):.3f}`",
        f"- replay best: `{summary.get('resume_best_stage')}` / `{summary.get('resume_best_match_ratio'):.3f}`",
        f"- match delta versus baseline: `{summary.get('match_delta_vs_baseline'):.3f}`",
        f"- outcome status: `{summary.get('outcome_status')}`",
        "",
        "Replay family diagnostics:",
        f"- top-band family count: `{summary.get('phaseb_family_count_in_top_band')}`",
        f"- preserved family count: `{summary.get('phaseb_family_preserved_count')}`",
        f"- reservation applied: `{summary.get('phaseb_family_reservation_applied')}`",
        f"- downstream selected count: `{summary.get('phaseb_downstream_selected_count')}`",
        f"- downstream selected unique end hash count: `{summary.get('phaseb_downstream_selected_unique_end_hash')}`",
        f"- downstream selected family counts: `{summary.get('phaseb_downstream_selected_family_counts') or 'na'}`",
        f"- phaseC ran: `{summary.get('phasec_ran')}`",
        f"- phaseC start keys used: `{summary.get('phasec_start_keys_used')}`",
        f"- phaseC start policy: `{summary.get('phasec_start_policy')}`",
        "",
        "Scope note:",
        "- this is an exact retained Stage-3 replay on one case, not a broad multi-case verification yet",
        "- stage35 stays disabled in this first exact pass so the read stays focused on the candidate2 Stage-3 mechanism",
    ]
    (output_dir / "candidate2_exact_replay_readout.md").write_text(
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
            "run_config_override": dict(CANDIDATE2_RUN_CONFIG_OVERRIDE),
            "scope_note": (
                "first exact retained pass keeps stage35 disabled so the read stays "
                "focused on the candidate2 Stage-3 mechanism"
            ),
        },
    )
    payload = resume_mod.run_stage3_resume_from_artifact(
        case,
        output_dir=resume_bundle_dir,
        run_config_override=CANDIDATE2_RUN_CONFIG_OVERRIDE,
        enable_stage35=ENABLE_STAGE35,
    )
    resume_mod.write_resume_bundle(payload, output_dir=resume_bundle_dir)
    summary = build_candidate2_exact_replay_summary(case=case, payload=payload)
    _write_json(output_dir / "candidate2_exact_replay_summary.json", summary)
    write_candidate2_exact_replay_markdown(output_dir, summary=summary)
    run_summary = {
        "output_dir": _relative_path(output_dir),
        "resume_bundle_dir": _relative_path(resume_bundle_dir),
        "source_artifact_relpath": str(summary["source_artifact_relpath"]),
        "fixture_seed": int(summary["fixture_seed"]),
        "search_seed": int(summary["search_seed"]),
        "baseline_best_match_ratio": float(summary["baseline_best_match_ratio"]),
        "resume_best_match_ratio": float(summary["resume_best_match_ratio"]),
        "match_delta_vs_baseline": float(summary["match_delta_vs_baseline"]),
        "stage35_enabled_effective": int(summary["stage35_enabled_effective"]),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    summary = run_verification()
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
