from __future__ import annotations

import csv
import json
import math
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
RUN_LABEL = "stage3_entry_const_local_depth_downstream_selection_audit_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)

TARGETS = [
    {
        "search_seed": 7005,
        "run_output_dir": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1"
        ),
        "cell_dir": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/"
            "cell_0001_1111_search7005_const_local_depth"
        ),
    },
    {
        "search_seed": 7004,
        "run_output_dir": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1"
        ),
        "cell_dir": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1/"
            "cell_0001_1111_search7004_const_local_depth"
        ),
    },
]


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(dict(json.loads(line)))
    return rows


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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


def _safe_float(value: Any, default: float = math.nan) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _best_phasec_row(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    if not rows:
        return {}
    return max(rows, key=lambda row: _safe_float(row.get("final_match"), -1.0))


def _find_phasec_row(
    rows: Sequence[Mapping[str, Any]], candidate_hash: str
) -> Mapping[str, Any]:
    for row in rows:
        if _safe_str(row.get("candidate_hash")) == candidate_hash:
            return row
    return {}


def _archive_rows(
    *,
    search_seed: int,
    flow: Mapping[str, Any],
    retained_best: float,
    candidate_final: float,
) -> list[dict[str, Any]]:
    baseline_search = _safe_float(flow.get("stage35_baseline_search_score"))
    best_hash = _safe_str(flow.get("stage35_best_candidate_hash"))
    best_match = _safe_float(flow.get("stage35_best_match"))
    rows: list[dict[str, Any]] = []
    for raw in list(flow.get("stage35_archive_rows") or []):
        archive_hash = _safe_str(raw.get("candidate_hash"))
        archive_search = _safe_float(raw.get("search_score"))
        archive_match = best_match if archive_hash == best_hash else math.nan
        rows.append(
            {
                "run_label": RUN_LABEL,
                "search_seed": search_seed,
                "archive_rank": _safe_int(raw.get("archive_rank")),
                "candidate_hash": archive_hash,
                "score": _safe_float(raw.get("score")),
                "search_score": archive_search,
                "search_score_delta_vs_baseline": archive_search - baseline_search,
                "would_pass_search_guard": int(archive_search >= baseline_search),
                "known_match_if_stage35_best": archive_match,
                "known_delta_vs_retained": archive_match - retained_best,
                "known_delta_vs_candidate_final": archive_match - candidate_final,
                "target_slice": _safe_int(raw.get("target_slice")),
                "seed_source": _safe_str(raw.get("seed_source")),
                "stage3_source": _safe_str(raw.get("stage3_source")),
                "move_type": _safe_str(raw.get("move_type")),
            }
        )
    return rows


def _cell_row(target: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    search_seed = _safe_int(target["search_seed"])
    run_output_dir = REPO_ROOT / _safe_str(target["run_output_dir"])
    cell_dir = REPO_ROOT / _safe_str(target["cell_dir"])
    run_summary = _read_json(
        run_output_dir
        / f"stage3_entry_const_local_depth_handoff_{search_seed}_summary.json"
    )
    flow = _read_json(cell_dir / "stage3_flow.json")
    phasea = _read_json(cell_dir / "phasea_gate_snapshot.json")
    phasec_rows = _read_jsonl(cell_dir / "phasec_start_checkpoints.jsonl")
    stage35 = _read_json(cell_dir / "stage35_partial_state.json")

    retained_best = _safe_float(run_summary.get("retained_best_match_ratio"))
    candidate_final = _safe_float(run_summary.get("resume_best_match_ratio"))
    phasea_best_hash = _safe_str(phasea.get("phaseA_best_final_candidate_hash"))
    phasea_best_match = _safe_float(phasea.get("phaseA_best_final_match"))
    phasec_for_phasea_best = _find_phasec_row(phasec_rows, phasea_best_hash)
    phasec_best = _best_phasec_row(phasec_rows)
    stage35_accept = _safe_int(flow.get("stage35_accept_passed"))
    stage35_best_match = _safe_float(flow.get("stage35_best_match"))
    stage35_baseline_match = _safe_float(flow.get("stage35_baseline_candidate_final_match"))
    gate_uses_candidate = stage35_accept
    gated_match = candidate_final if gate_uses_candidate else retained_best

    row = {
        "run_label": RUN_LABEL,
        "search_seed": search_seed,
        "run_output_dir": _repo_rel(run_output_dir),
        "cell_dir": _repo_rel(cell_dir),
        "status": _safe_str(run_summary.get("status")),
        "elapsed_seconds": _safe_float(run_summary.get("elapsed_seconds")),
        "retained_best_match": retained_best,
        "candidate_final_match": candidate_final,
        "candidate_delta_vs_retained": candidate_final - retained_best,
        "candidate_best_stage": _safe_str(run_summary.get("resume_best_stage")),
        "phasea_best_hash": phasea_best_hash,
        "phasea_best_match": phasea_best_match,
        "phasea_delta_vs_retained": phasea_best_match - retained_best,
        "phasec_for_phasea_best_final_match": _safe_float(
            phasec_for_phasea_best.get("final_match")
        ),
        "phasec_for_phasea_best_match_gain": _safe_float(
            phasec_for_phasea_best.get("match_gain")
        ),
        "phasec_best_hash": _safe_str(phasec_best.get("candidate_hash")),
        "phasec_best_match": _safe_float(phasec_best.get("final_match")),
        "phasec_best_delta_vs_retained": _safe_float(phasec_best.get("final_match"))
        - retained_best,
        "phasec_start_count": len(phasec_rows),
        "phasec_negative_start_count": sum(
            1 for row in phasec_rows if _safe_float(row.get("match_gain")) < 0.0
        ),
        "phasec_nonnegative_start_count": sum(
            1 for row in phasec_rows if _safe_float(row.get("match_gain")) >= 0.0
        ),
        "stage35_accept_passed": stage35_accept,
        "stage35_accept_reason": _safe_str(flow.get("stage35_accept_reason")),
        "stage35_baseline_hash": _safe_str(flow.get("stage35_baseline_candidate_hash")),
        "stage35_baseline_match": stage35_baseline_match,
        "stage35_best_hash": _safe_str(flow.get("stage35_best_candidate_hash")),
        "stage35_best_match": stage35_best_match,
        "stage35_best_delta_vs_retained": stage35_best_match - retained_best,
        "stage35_best_delta_vs_baseline": stage35_best_match - stage35_baseline_match,
        "stage35_selected": _safe_int(flow.get("stage35_selected")),
        "stage35_partial_selected_candidate_hash": _safe_str(
            stage35.get("selected_candidate_hash")
        ),
        "stage35_selected_archive_rank": _safe_int(
            stage35.get("selected_archive_rank")
        ),
        "stage35_runtime_seconds": _safe_float(flow.get("stage35_runtime_seconds")),
        "posthoc_accept_only_if_stage35_accepts_uses_candidate": gate_uses_candidate,
        "posthoc_accept_only_if_stage35_accepts_match": gated_match,
        "posthoc_accept_only_if_stage35_accepts_delta_vs_retained": gated_match
        - retained_best,
        "interpretation": "",
    }
    if search_seed == 7005:
        row["interpretation"] = (
            "stage35_accept_passed kept the small candidate improvement"
        )
    elif search_seed == 7004:
        row["interpretation"] = (
            "stage35 guard failed; fallback-to-retained would avoid the final regression"
        )
    archive = _archive_rows(
        search_seed=search_seed,
        flow=flow,
        retained_best=retained_best,
        candidate_final=candidate_final,
    )
    return row, archive


def _build_readout(summary: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Stage3 Entry Constant-Local-Depth Downstream Selection Audit v1",
        "",
        "Question:",
        "",
        "- Why did the structurally active constant-local-depth handoff branch keep a "
        "small `7005` gain but regress on `7004`, and is there an offline safety "
        "gate worth carrying forward?",
        "",
        "Coverage:",
        "",
        f"- cells: `{summary['cell_count']}`",
        f"- positive candidate cells: `{summary['candidate_positive_count']}`",
        f"- negative candidate cells: `{summary['candidate_negative_count']}`",
        "",
        "Cell results:",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"- `1111/search{row['search_seed']}`:",
                f"  - retained: `{float(row['retained_best_match']):.3f}`",
                f"  - candidate final: `{float(row['candidate_final_match']):.3f}`",
                f"  - delta: `{float(row['candidate_delta_vs_retained']):+.3f}`",
                f"  - Phase-A best: `{float(row['phasea_best_match']):.3f}`",
                f"  - Stage 3.5 accept: `{row['stage35_accept_passed']}` "
                f"({row['stage35_accept_reason']})",
            ]
        )
    lines.extend(
        [
            "",
            "Posthoc gate check:",
            "",
            "- Gate: use the widened-entry candidate only when Stage 3.5 accept passes; "
            "otherwise fall back to retained.",
            f"- kept candidates: `{summary['posthoc_gate_kept_candidate_count']}`",
            f"- fallback cells: `{summary['posthoc_gate_fallback_count']}`",
            f"- gated negative cells: `{summary['posthoc_gate_negative_count']}`",
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
    rows: list[dict[str, Any]] = []
    archive_rows: list[dict[str, Any]] = []
    for target in TARGETS:
        row, archive = _cell_row(target)
        rows.append(row)
        archive_rows.extend(archive)
    candidate_negative_count = sum(
        1 for row in rows if float(row["candidate_delta_vs_retained"]) < 0.0
    )
    posthoc_gate_negative_count = sum(
        1
        for row in rows
        if float(row["posthoc_accept_only_if_stage35_accepts_delta_vs_retained"]) < 0.0
    )
    summary = {
        "run_label": RUN_LABEL,
        "status": "completed",
        "output_dir": _repo_rel(output_dir),
        "cell_count": len(rows),
        "archive_row_count": len(archive_rows),
        "candidate_positive_count": sum(
            1 for row in rows if float(row["candidate_delta_vs_retained"]) > 0.0
        ),
        "candidate_negative_count": candidate_negative_count,
        "posthoc_gate_kept_candidate_count": sum(
            1
            for row in rows
            if int(row["posthoc_accept_only_if_stage35_accepts_uses_candidate"]) == 1
        ),
        "posthoc_gate_fallback_count": sum(
            1
            for row in rows
            if int(row["posthoc_accept_only_if_stage35_accepts_uses_candidate"]) == 0
        ),
        "posthoc_gate_negative_count": posthoc_gate_negative_count,
        "decision": (
            "do_not_reopen_runtime_from_this_audit"
            if candidate_negative_count
            else "insufficient_positive_only_signal"
        ),
        "recommended_next": (
            "test_stage35_accept_gate_offline_on_broader_retained_handoff_outputs"
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
        "updated_utc": _utc_now_text(),
    }
    _write_csv(
        output_dir / "stage3_entry_const_local_depth_downstream_selection_cell_rows.csv",
        rows,
    )
    _write_csv(
        output_dir
        / "stage3_entry_const_local_depth_downstream_selection_archive_rows.csv",
        archive_rows,
    )
    _write_json(
        output_dir / "stage3_entry_const_local_depth_downstream_selection_summary.json",
        summary,
    )
    (output_dir / "stage3_entry_const_local_depth_downstream_selection_readout.md").write_text(
        _build_readout(summary, rows),
        encoding="utf-8",
    )
    _write_json(output_dir / "run_summary.json", summary)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_study()


if __name__ == "__main__":
    main()
