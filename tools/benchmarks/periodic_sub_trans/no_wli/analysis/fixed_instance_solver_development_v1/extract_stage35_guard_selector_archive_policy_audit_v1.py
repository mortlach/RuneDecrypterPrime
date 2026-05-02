from __future__ import annotations

import csv
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
        "extract_stage35_guard_selector_archive_policy_audit_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


RUN_LABEL = "stage35_guard_selector_archive_policy_audit_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)

CASES: list[dict[str, Any]] = [
    {
        "case_label": "accepted_positive_7005",
        "fixture_seed": 1111,
        "search_seed": 7005,
        "artifact_relpath": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260412T053512632846Z__bench_solve_pipeline_no_wli__9557c0f/"
            "best/best_instance.json"
        ),
        "payload_relpath": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260429T145906Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/"
            "search7005_selected_best_frontier_real/summary.json"
        ),
        "stage35_relpath": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260429T145906Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/"
            "search7005_selected_best_frontier_real/stage35_summary.json"
        ),
    },
    {
        "case_label": "blocked_secondary_7004",
        "fixture_seed": 1111,
        "search_seed": 7004,
        "artifact_relpath": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260412T031328680128Z__bench_solve_pipeline_no_wli__9557c0f/"
            "best/best_instance.json"
        ),
        "payload_relpath": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260429T150415Z__stage35_resume_from_handoff_focus_family_rescue_real_7004_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/"
            "search7004_selected_best_frontier_guard_selector/summary.json"
        ),
        "stage35_relpath": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260429T150415Z__stage35_resume_from_handoff_focus_family_rescue_real_7004_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/"
            "search7004_selected_best_frontier_guard_selector/stage35_summary.json"
        ),
    },
]


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _read_json(relpath: str) -> dict[str, Any]:
    return json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(result):
        return float(default)
    return result


def _truth_match(plaintext_idx: Any, target_plaintext_idx: Any) -> float:
    pt = [int(x) for x in list(plaintext_idx or [])]
    target = [int(x) for x in list(target_plaintext_idx or [])]
    if not pt or not target:
        return 0.0
    count = min(len(pt), len(target))
    if count <= 0:
        return 0.0
    same = sum(1 for idx in range(count) if int(pt[idx]) == int(target[idx]))
    return float(same / len(target))


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def build_case_rows(case_cfg: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    artifact = _read_json(str(case_cfg["artifact_relpath"]))
    payload = _read_json(str(case_cfg["payload_relpath"]))
    stage35 = _read_json(str(case_cfg["stage35_relpath"]))
    target_plaintext = artifact.get("target_plaintext_idx", []) or []

    selected_start = _safe_float(payload.get("selected_candidate_final_match"))
    accepted_resume = _safe_float(payload.get("resume_best_match_ratio"))
    retained = _safe_float(artifact.get("best_match_ratio"))
    baseline_score = _safe_float(stage35.get("baseline_score"))
    baseline_search_score = _safe_float(stage35.get("baseline_search_score"))

    rows: list[dict[str, Any]] = []
    for raw_row in list(stage35.get("archive_rows", []) or []):
        row = dict(raw_row)
        score = _safe_float(row.get("score"))
        search_score = _safe_float(row.get("search_score"))
        truth = _truth_match(row.get("plaintext_idx", []), target_plaintext)
        score_delta = score - baseline_score
        search_delta = search_score - baseline_search_score
        truth_delta = truth - selected_start
        guard_passing = int(score_delta >= 0.0 and search_delta >= 0.0)
        non_noop = int(abs(score_delta) > 1e-12 or abs(search_delta) > 1e-12)
        rows.append(
            {
                "case_label": str(case_cfg["case_label"]),
                "fixture_seed": int(case_cfg["fixture_seed"]),
                "search_seed": int(case_cfg["search_seed"]),
                "archive_rank": int(row.get("archive_rank", 0) or 0),
                "candidate_hash": str(row.get("candidate_hash", "") or ""),
                "truth_match": round(float(truth), 6),
                "truth_delta_vs_selected": round(float(truth_delta), 6),
                "score": round(float(score), 12),
                "score_delta_vs_baseline": round(float(score_delta), 12),
                "search_score": round(float(search_score), 12),
                "search_delta_vs_baseline": round(float(search_delta), 12),
                "guard_passing": guard_passing,
                "non_noop": non_noop,
                "truth_positive": int(truth_delta > 0.0),
                "blocked_truth_positive": int(
                    truth_delta > 0.0 and score_delta >= 0.0 and search_delta < 0.0
                ),
                "lane": str(row.get("lane", "") or ""),
                "seed_source": str(row.get("seed_source", "") or ""),
                "stage3_source": str(row.get("stage3_source", "") or ""),
                "target_slice": row.get("target_slice", ""),
            }
        )

    truth_positive_rows = [row for row in rows if int(row["truth_positive"]) == 1]
    blocked_truth_positive_rows = [
        row for row in rows if int(row["blocked_truth_positive"]) == 1
    ]
    guard_passing_non_noop_rows = [
        row for row in rows if int(row["guard_passing"]) == 1 and int(row["non_noop"]) == 1
    ]
    best_truth = max(rows, key=lambda row: float(row["truth_match"])) if rows else {}
    case_summary = {
        "case_label": str(case_cfg["case_label"]),
        "fixture_seed": int(case_cfg["fixture_seed"]),
        "search_seed": int(case_cfg["search_seed"]),
        "retained_best_match_ratio": retained,
        "selected_row_start_match_ratio": selected_start,
        "accepted_resume_match_ratio": accepted_resume,
        "accepted_minus_selected": accepted_resume - selected_start,
        "stage35_selected": int(stage35.get("selected", 0) or 0),
        "stage35_accept_reason": str(stage35.get("accept_reason", "") or ""),
        "stage35_selected_archive_rank": int(
            stage35.get("selected_archive_rank", 0) or 0
        ),
        "archive_rows": len(rows),
        "guard_passing_non_noop_rows": len(guard_passing_non_noop_rows),
        "truth_positive_rows": len(truth_positive_rows),
        "blocked_truth_positive_rows": len(blocked_truth_positive_rows),
        "best_truth_archive_rank": int(best_truth.get("archive_rank", 0) or 0),
        "best_truth_candidate_hash": str(best_truth.get("candidate_hash", "") or ""),
        "best_truth_match": _safe_float(best_truth.get("truth_match")),
        "best_truth_delta_vs_selected": _safe_float(
            best_truth.get("truth_delta_vs_selected")
        ),
        "best_truth_search_delta_vs_baseline": _safe_float(
            best_truth.get("search_delta_vs_baseline")
        ),
    }
    return rows, case_summary


def build_readout(case_summaries: list[dict[str, Any]], output_dir: Path) -> str:
    lines = [
        "# Stage35 Guard-Selector Archive Policy Audit v1",
        "",
        "Question:",
        "",
        "- across the completed `7005` and `7004` selected-row guard-selector archives,",
        "  is the strict nonnegative search-score guard selecting useful rows or blocking",
        "  truth-positive local proposals?",
        "",
        "Inputs:",
    ]
    for case in CASES:
        lines.append(f"- `{case['stage35_relpath']}`")
    lines.extend(
        [
            "",
            "Case Summary:",
            "",
            "| case | accepted | accepted delta vs selected | guard-passing non-noop rows | truth-positive rows | blocked truth-positive rows | best truth row | best truth delta |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for row in case_summaries:
        lines.append(
            "| "
            f"`{row['case_label']}` | "
            f"`{row['stage35_selected']}` | "
            f"`{row['accepted_minus_selected']:+.3f}` | "
            f"`{row['guard_passing_non_noop_rows']}` | "
            f"`{row['truth_positive_rows']}` | "
            f"`{row['blocked_truth_positive_rows']}` | "
            f"`{row['best_truth_archive_rank']}:{row['best_truth_candidate_hash']}` | "
            f"`{row['best_truth_delta_vs_selected']:+.3f}` |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- strict guard-selector fallback works on `7005` and accepts a truth-positive",
            "  guard-passing alternate",
            "- strict guard-selector fallback does not repeat on `7004`: no non-no-op",
            "  archive row passes the search-score guard",
            "- `7004` still contains a truth-positive local row, but it is blocked by",
            "  search-score decline",
            "- this is a policy boundary rather than a runtime failure",
            "",
            "Recommended Next:",
            "",
            "- stop strict guard-selector runtime for now",
            "- if the branch continues, run a broader offline guard-relaxation audit over",
            "  retained Stage 3.5 archives before any more runtime",
            "- the audit should look for non-truth features that separate the `7004`",
            "  rank-6 truth-positive row from rank-1 truth regressions",
            "",
            "Output files:",
            "",
            f"- `{_repo_rel(output_dir / 'stage35_guard_selector_archive_policy_audit_rows.csv')}`",
            f"- `{_repo_rel(output_dir / 'stage35_guard_selector_archive_policy_audit_case_summary.csv')}`",
            f"- `{_repo_rel(output_dir / 'stage35_guard_selector_archive_policy_audit_summary.json')}`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_audit() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    all_rows: list[dict[str, Any]] = []
    case_summaries: list[dict[str, Any]] = []
    for case_cfg in CASES:
        rows, summary = build_case_rows(case_cfg)
        all_rows.extend(rows)
        case_summaries.append(summary)

    _write_csv(output_dir / "stage35_guard_selector_archive_policy_audit_rows.csv", all_rows)
    _write_csv(
        output_dir / "stage35_guard_selector_archive_policy_audit_case_summary.csv",
        case_summaries,
    )
    summary_payload = {
        "run_label": RUN_LABEL,
        "output_dir": _repo_rel(output_dir),
        "cases": len(case_summaries),
        "archive_rows": len(all_rows),
        "accepted_positive_cases": sum(
            1 for row in case_summaries if int(row["stage35_selected"]) == 1
        ),
        "cases_with_blocked_truth_positive_rows": sum(
            1 for row in case_summaries if int(row["blocked_truth_positive_rows"]) > 0
        ),
        "recommended_next": (
            "stop_strict_guard_selector_runtime_and_design_broader_offline_guard_relaxation_audit"
        ),
    }
    _write_json(
        output_dir / "stage35_guard_selector_archive_policy_audit_summary.json",
        summary_payload,
    )
    (output_dir / "stage35_guard_selector_archive_policy_audit_readout.md").write_text(
        build_readout(case_summaries, output_dir),
        encoding="utf-8",
    )
    return summary_payload


def main() -> None:
    print(json.dumps(run_audit(), sort_keys=True))


if __name__ == "__main__":
    main()
