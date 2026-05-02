from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root")


REPO_ROOT = _find_repo_root()
RUN_LABEL = "stage35_accept_gate_broader_offline_audit_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)

SHALLOW_FRONTIER_ROWS = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/"
    "stage35_guard_selector_frontier_runtime_rows.csv"
)
DEEPENING_ROWS = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/"
    "stage35_guard_selector_frontier_deepening_rows.csv"
)


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([dict(row) for row in rows])


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalize_rows(source_name: str, rows: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        retained = _safe_float(row.get("retained_best_match_ratio"))
        selected = _safe_float(row.get("selected_start_match_ratio"))
        resume = _safe_float(row.get("resume_best_match_ratio"))
        stage35_selected = _safe_int(row.get("stage35_selected"))
        gated_vs_retained = resume if stage35_selected else retained
        gated_vs_selected = resume if stage35_selected else selected
        out.append(
            {
                "run_label": RUN_LABEL,
                "source_name": source_name,
                "fixture_seed": _safe_int(row.get("fixture_seed")),
                "search_seed": _safe_int(row.get("search_seed")),
                "candidate_rank": _safe_int(row.get("candidate_rank")),
                "candidate_hash": str(row.get("candidate_hash") or ""),
                "retained_best_match_ratio": retained,
                "selected_start_match_ratio": selected,
                "resume_best_match_ratio": resume,
                "stage35_selected": stage35_selected,
                "stage35_accept_reason": str(row.get("stage35_accept_reason") or ""),
                "resume_minus_retained": _safe_float(row.get("resume_minus_retained")),
                "resume_minus_selected": _safe_float(row.get("resume_minus_selected")),
                "accept_gate_match_vs_retained_fallback": gated_vs_retained,
                "accept_gate_delta_vs_retained": gated_vs_retained - retained,
                "accept_gate_match_vs_selected_fallback": gated_vs_selected,
                "accept_gate_delta_vs_selected": gated_vs_selected - selected,
            }
        )
    return out


def _summary_for(source_name: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    selected_rows = [row for row in rows if int(row["stage35_selected"]) == 1]
    return {
        "run_label": RUN_LABEL,
        "source_name": source_name,
        "row_count": len(rows),
        "stage35_selected_count": len(selected_rows),
        "stage35_not_selected_count": len(rows) - len(selected_rows),
        "accepted_negative_vs_retained_count": sum(
            1 for row in selected_rows if float(row["resume_minus_retained"]) < 0.0
        ),
        "accepted_negative_vs_selected_count": sum(
            1 for row in selected_rows if float(row["resume_minus_selected"]) < 0.0
        ),
        "accept_gate_negative_vs_retained_count": sum(
            1 for row in rows if float(row["accept_gate_delta_vs_retained"]) < 0.0
        ),
        "accept_gate_negative_vs_selected_count": sum(
            1 for row in rows if float(row["accept_gate_delta_vs_selected"]) < 0.0
        ),
        "accept_gate_mean_delta_vs_retained": (
            sum(float(row["accept_gate_delta_vs_retained"]) for row in rows)
            / max(1, len(rows))
        ),
        "accept_gate_mean_delta_vs_selected": (
            sum(float(row["accept_gate_delta_vs_selected"]) for row in rows)
            / max(1, len(rows))
        ),
    }


def _build_readout(summary: Mapping[str, Any], summaries: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Stage35 Accept Gate Broader Offline Audit v1",
        "",
        "Question:",
        "",
        "- Does the two-cell Stage 3.5 accept-pass fallback lead survive a broader "
        "offline stress test on retained Stage 3.5 frontier outputs?",
        "",
        "Summary:",
        "",
        f"- total rows: `{summary['row_count']}`",
        f"- accepted rows: `{summary['stage35_selected_count']}`",
        f"- accept-gate negatives versus retained: "
        f"`{summary['accept_gate_negative_vs_retained_count']}`",
        f"- accept-gate negatives versus selected start: "
        f"`{summary['accept_gate_negative_vs_selected_count']}`",
        "",
        "By source:",
        "",
    ]
    for row in summaries:
        lines.extend(
            [
                f"- `{row['source_name']}`:",
                f"  - rows: `{row['row_count']}`",
                f"  - accepted: `{row['stage35_selected_count']}`",
                f"  - accepted negatives versus retained: "
                f"`{row['accepted_negative_vs_retained_count']}`",
                f"  - accepted negatives versus selected: "
                f"`{row['accepted_negative_vs_selected_count']}`",
            ]
        )
    lines.extend(
        [
            "",
            "Decision:",
            "",
            f"- `{summary['decision']}`",
            "",
            "Recommended next:",
            "",
            f"- `{summary['recommended_next']}`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_study() -> dict[str, Any]:
    started = time.perf_counter()
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    rows = []
    rows.extend(_normalize_rows("frontier_runtime_harvest", _read_csv(SHALLOW_FRONTIER_ROWS)))
    rows.extend(_normalize_rows("frontier_deepening_harvest", _read_csv(DEEPENING_ROWS)))
    summaries = [
        _summary_for("frontier_runtime_harvest", [r for r in rows if r["source_name"] == "frontier_runtime_harvest"]),
        _summary_for("frontier_deepening_harvest", [r for r in rows if r["source_name"] == "frontier_deepening_harvest"]),
    ]
    summary = _summary_for("combined", rows)
    summary.update(
        {
            "status": "completed",
            "output_dir": _repo_rel(output_dir),
            "source_files": [_repo_rel(SHALLOW_FRONTIER_ROWS), _repo_rel(DEEPENING_ROWS)],
            "decision": "close_stage35_accept_pass_as_general_safety_gate",
            "recommended_next": "return_to_offline_feature_design_or_new_mechanism_no_runtime",
            "elapsed_seconds": float(time.perf_counter() - started),
            "updated_utc": _utc_now_text(),
        }
    )
    _write_csv(output_dir / "stage35_accept_gate_broader_offline_audit_rows.csv", rows)
    _write_csv(
        output_dir / "stage35_accept_gate_broader_offline_audit_source_summary_rows.csv",
        summaries,
    )
    _write_json(output_dir / "stage35_accept_gate_broader_offline_audit_summary.json", summary)
    (output_dir / "stage35_accept_gate_broader_offline_audit_readout.md").write_text(
        _build_readout(summary, summaries),
        encoding="utf-8",
    )
    _write_json(output_dir / "run_summary.json", summary)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_study()


if __name__ == "__main__":
    main()
