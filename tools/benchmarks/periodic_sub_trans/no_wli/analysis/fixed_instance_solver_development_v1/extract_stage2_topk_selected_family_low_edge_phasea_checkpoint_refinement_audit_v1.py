from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (  # noqa: E402
    refresh_catalog_safely,
)


RUN_LABEL = "stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1"
MECHANISM_LAYER = "selection"
RANK1_THRESHOLD = 0.30
BEST_THRESHOLD_CANDIDATES = (0.40, 0.42, 0.44, 0.45, 0.46, 0.48, 0.49)
LATE_FAMILY_BUNDLE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
    / "20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1"
)
LATE_FAMILY_ROWS_CSV = (
    LATE_FAMILY_BUNDLE_DIR / "selected_family_low_edge_phasea_gate_live_read_followon_rows.csv"
)
PROVISIONAL_BUNDLE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
    / "20260424T175849Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1"
)
PROVISIONAL_ROWS_CSV = (
    PROVISIONAL_BUNDLE_DIR / "selected_family_low_edge_phasea_earlier_emission_rows.csv"
)


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _utc_label() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _timestamp() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _print_progress(message: str) -> None:
    print(f"[{_timestamp()}] {message}", flush=True)


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_str(value: Any) -> str:
    return str(value or "")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True))
            handle.write("\n")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {_relative_path(path)}")
    fieldnames = list(dict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def _mean(values: Sequence[float]) -> float:
    finite = [value for value in values if value == value]
    if not finite:
        return float("nan")
    return float(sum(finite) / float(len(finite)))


def _gate_verdict(
    *,
    rank1_init_match: Any,
    best_init_match: Any,
    rank1_threshold: float,
    best_threshold: float,
) -> str:
    rank1_value = _safe_float(rank1_init_match)
    best_value = _safe_float(best_init_match)
    if rank1_value == rank1_value and rank1_value >= float(rank1_threshold):
        return "keep"
    if best_value == best_value and best_value >= float(best_threshold):
        return "keep"
    return "filter"


def _rule_id(*, rank1_threshold: float, best_threshold: float) -> str:
    rank1_text = f"{rank1_threshold:.2f}".replace(".", "p")
    best_text = f"{best_threshold:.2f}".replace(".", "p")
    return f"rank1_ge_{rank1_text}_or_best_ge_{best_text}"


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _build_late_family_rows() -> list[dict[str, Any]]:
    raw_rows = _read_csv_rows(LATE_FAMILY_ROWS_CSV)
    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        rows.append(
            {
                "search_seed": _safe_int(row.get("search_seed")),
                "phasea_rank1_init_match": _safe_float(
                    row.get("phasea_rank1_init_match")
                ),
                "phasea_best_init_match": _safe_float(
                    row.get("phasea_best_init_match")
                ),
                "expected_gate_verdict": _safe_str(row.get("expected_gate_verdict")),
                "phasea_gate_snapshot_elapsed_share": _safe_float(
                    row.get("phasea_gate_snapshot_elapsed_share")
                ),
            }
        )
    rows.sort(key=lambda row: _safe_int(row.get("search_seed")))
    return rows


def _build_provisional_rows() -> list[dict[str, Any]]:
    raw_rows = _read_csv_rows(PROVISIONAL_ROWS_CSV)
    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        rows.append(
            {
                "search_seed": _safe_int(row.get("search_seed")),
                "output_dir": _safe_str(row.get("output_dir")),
                "checkpoint_restart_count": _safe_int(
                    row.get("checkpoint_restart_count")
                ),
                "checkpoint_elapsed_share": _safe_float(
                    row.get("checkpoint_elapsed_share")
                ),
                "checkpoint_share_improvement_vs_late_gate": _safe_float(
                    row.get("checkpoint_share_improvement_vs_late_gate")
                ),
                "late_gate_elapsed_share": _safe_float(
                    row.get("late_gate_elapsed_share")
                ),
                "phasea_rank1_init_match": _safe_float(row.get("gate_metric_value")),
                "expected_gate_verdict": _safe_str(row.get("expected_gate_verdict")),
            }
        )

    for row in rows:
        search_seed = _safe_int(row.get("search_seed"))
        child_dir = REPO_ROOT / Path(
            _safe_str(
                row.get(
                    "output_dir",
                    "",
                )
            )
        )
        snapshots_path = (
            child_dir / "resume_bundle" / "phasea_provisional_gate_snapshots.jsonl"
        )
        matching_snapshot: dict[str, Any] | None = None
        for line in snapshots_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            snapshot = json.loads(line)
            if _safe_int(snapshot.get("phaseA_checkpoint_restart_count")) != _safe_int(
                row.get("checkpoint_restart_count")
            ):
                continue
            matching_snapshot = dict(snapshot)
            break
        if matching_snapshot is None:
            raise RuntimeError(
                f"Missing provisional snapshot for search_seed={search_seed} "
                f"checkpoint={row['checkpoint_restart_count']}"
            )
        row["phasea_best_init_match"] = _safe_float(
            matching_snapshot.get("phaseA_best_init_match")
        )
        row["phasea_best_final_match"] = _safe_float(
            matching_snapshot.get("phaseA_best_final_match")
        )

    rows.sort(
        key=lambda row: (
            _safe_int(row.get("checkpoint_restart_count")),
            _safe_int(row.get("search_seed")),
        )
    )
    return rows


def _collect_interval_bounds(
    *,
    late_family_rows: Sequence[Mapping[str, Any]],
    provisional_rows: Sequence[Mapping[str, Any]],
    rank1_threshold: float,
) -> dict[str, float]:
    filtered_best_values: list[float] = []
    rescued_keep_best_values: list[float] = []

    for row in late_family_rows:
        expected = _safe_str(row.get("expected_gate_verdict"))
        best_value = _safe_float(row.get("phasea_best_init_match"))
        if expected == "filter" and best_value == best_value:
            filtered_best_values.append(best_value)

    for row in provisional_rows:
        expected = _safe_str(row.get("expected_gate_verdict"))
        best_value = _safe_float(row.get("phasea_best_init_match"))
        rank1_value = _safe_float(row.get("phasea_rank1_init_match"))
        if expected == "filter" and best_value == best_value:
            filtered_best_values.append(best_value)
        if (
            expected == "keep"
            and rank1_value == rank1_value
            and rank1_value < float(rank1_threshold)
            and best_value == best_value
        ):
            rescued_keep_best_values.append(best_value)

    filtered_best_max = max(filtered_best_values, default=float("nan"))
    rescued_keep_best_min = min(rescued_keep_best_values, default=float("nan"))
    midpoint = float("nan")
    if filtered_best_max == filtered_best_max and rescued_keep_best_min == rescued_keep_best_min:
        midpoint = float(filtered_best_max + rescued_keep_best_min) / 2.0

    return {
        "filtered_best_max": float(filtered_best_max),
        "rescued_keep_best_min": float(rescued_keep_best_min),
        "safe_interval_midpoint": float(midpoint),
    }


def _evaluate_candidate_rule(
    *,
    rank1_threshold: float,
    best_threshold: float,
    late_family_rows: Sequence[Mapping[str, Any]],
    provisional_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    late_match_count = 0
    late_override_count = 0
    for row in late_family_rows:
        rank1_value = _safe_float(row.get("phasea_rank1_init_match"))
        best_value = _safe_float(row.get("phasea_best_init_match"))
        observed = _gate_verdict(
            rank1_init_match=rank1_value,
            best_init_match=best_value,
            rank1_threshold=rank1_threshold,
            best_threshold=best_threshold,
        )
        expected = _safe_str(row.get("expected_gate_verdict"))
        if observed == expected:
            late_match_count += 1
        rank1_only_verdict = (
            "keep" if rank1_value == rank1_value and rank1_value >= rank1_threshold else "filter"
        )
        if observed != rank1_only_verdict:
            late_override_count += 1

    provisional_match_rows: list[dict[str, Any]] = []
    for row in provisional_rows:
        rank1_value = _safe_float(row.get("phasea_rank1_init_match"))
        best_value = _safe_float(row.get("phasea_best_init_match"))
        observed = _gate_verdict(
            rank1_init_match=rank1_value,
            best_init_match=best_value,
            rank1_threshold=rank1_threshold,
            best_threshold=best_threshold,
        )
        expected = _safe_str(row.get("expected_gate_verdict"))
        provisional_match_rows.append(
            {
                "search_seed": _safe_int(row.get("search_seed")),
                "checkpoint_restart_count": _safe_int(
                    row.get("checkpoint_restart_count")
                ),
                "observed_gate_verdict": observed,
                "expected_gate_verdict": expected,
                "verdict_matches_expected": int(1 if observed == expected else 0),
                "checkpoint_elapsed_share": _safe_float(
                    row.get("checkpoint_elapsed_share")
                ),
                "checkpoint_share_improvement_vs_late_gate": _safe_float(
                    row.get("checkpoint_share_improvement_vs_late_gate")
                ),
                "late_gate_elapsed_share": _safe_float(
                    row.get("late_gate_elapsed_share")
                ),
            }
        )

    provisional_by_checkpoint: dict[int, list[dict[str, Any]]] = {}
    for row in provisional_match_rows:
        checkpoint = _safe_int(row.get("checkpoint_restart_count"))
        provisional_by_checkpoint.setdefault(checkpoint, []).append(dict(row))

    shared_checkpoint_count = 0
    earliest_shared_checkpoint = 0
    earliest_shared_rows: list[dict[str, Any]] = []
    for checkpoint in sorted(provisional_by_checkpoint):
        rows = list(provisional_by_checkpoint[checkpoint])
        if len(rows) < 2:
            continue
        if all(_safe_int(row.get("verdict_matches_expected")) == 1 for row in rows):
            shared_checkpoint_count += 1
            if earliest_shared_checkpoint == 0:
                earliest_shared_checkpoint = int(checkpoint)
                earliest_shared_rows = rows

    return {
        "rule_id": _rule_id(
            rank1_threshold=rank1_threshold,
            best_threshold=best_threshold,
        ),
        "rank1_threshold": float(rank1_threshold),
        "best_threshold": float(best_threshold),
        "late_family_row_count": int(len(late_family_rows)),
        "late_family_match_count": int(late_match_count),
        "late_family_all_match": int(1 if late_match_count == len(late_family_rows) else 0),
        "late_override_count": int(late_override_count),
        "shared_checkpoint_count": int(shared_checkpoint_count),
        "earliest_shared_checkpoint_restart_count": int(earliest_shared_checkpoint),
        "earliest_shared_checkpoint_elapsed_share": _mean(
            [
                _safe_float(row.get("checkpoint_elapsed_share"))
                for row in earliest_shared_rows
            ]
        ),
        "earliest_shared_checkpoint_share_improvement_vs_late_gate": _mean(
            [
                _safe_float(
                    row.get("checkpoint_share_improvement_vs_late_gate")
                )
                for row in earliest_shared_rows
            ]
        ),
    }


def _build_summary(
    *,
    candidate_rows: Sequence[Mapping[str, Any]],
    interval_bounds: Mapping[str, Any],
) -> dict[str, Any]:
    viable_rows = [
        dict(row)
        for row in candidate_rows
        if _safe_int(row.get("late_family_all_match")) == 1
        and _safe_int(row.get("shared_checkpoint_count")) > 0
    ]
    midpoint = _safe_float(interval_bounds.get("safe_interval_midpoint"))
    viable_rows.sort(
        key=lambda row: (
            _safe_int(row.get("earliest_shared_checkpoint_restart_count")),
            abs(_safe_float(row.get("best_threshold")) - midpoint)
            if midpoint == midpoint
            else float("inf"),
            _safe_int(row.get("late_override_count")),
            _safe_float(row.get("best_threshold")),
        )
    )
    if viable_rows:
        best_row = dict(viable_rows[0])
        recommendation = "advance"
        next_branch = (
            "stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe"
        )
        reason = (
            "a refined provisional rule matches the trusted late family labels "
            "and recovers a shared early checkpoint on the provisional canaries"
        )
    else:
        best_row = {}
        recommendation = "hold"
        next_branch = (
            "stage2_topk_selected_family_low_edge_phasea_checkpoint_persistence_refinement"
        )
        reason = (
            "no refined rule over the currently persisted provisional fields "
            "matches both the trusted late family and the provisional canaries"
        )

    return {
        "candidate_rule_count": int(len(candidate_rows)),
        "late_family_row_count": 5,
        "provisional_canary_count": 2,
        "rank1_threshold": float(RANK1_THRESHOLD),
        "filtered_best_max": _safe_float(interval_bounds.get("filtered_best_max")),
        "rescued_keep_best_min": _safe_float(
            interval_bounds.get("rescued_keep_best_min")
        ),
        "safe_interval_midpoint": _safe_float(
            interval_bounds.get("safe_interval_midpoint")
        ),
        "recommendation": str(recommendation),
        "next_branch": str(next_branch),
        "reason": str(reason),
        "selected_rule_id": _safe_str(best_row.get("rule_id")),
        "selected_best_threshold": _safe_float(best_row.get("best_threshold")),
        "selected_earliest_shared_checkpoint_restart_count": _safe_int(
            best_row.get("earliest_shared_checkpoint_restart_count")
        ),
        "selected_earliest_shared_checkpoint_elapsed_share": _safe_float(
            best_row.get("earliest_shared_checkpoint_elapsed_share")
        ),
        "selected_earliest_shared_checkpoint_share_improvement_vs_late_gate": _safe_float(
            best_row.get("earliest_shared_checkpoint_share_improvement_vs_late_gate")
        ),
        "selected_late_override_count": _safe_int(best_row.get("late_override_count")),
    }


def _build_readout(
    *,
    summary: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> str:
    lines = [
        "# Phase-A Checkpoint Refinement Audit",
        "",
        "Question:",
        "- Can a refined provisional checkpoint rule recover the trusted fixed-family labels before the current late gate surface?",
        "",
        "Coverage:",
        f"- candidate rules tested: `{_safe_int(summary.get('candidate_rule_count'))}`",
        f"- recommendation: `{_safe_str(summary.get('recommendation'))}`",
        f"- reason: {_safe_str(summary.get('reason'))}",
        "",
        "Interval read:",
        f"- max filtered provisional/late `best_init`: `{_safe_float(summary.get('filtered_best_max')):.3f}`",
        f"- min rescued kept provisional `best_init`: `{_safe_float(summary.get('rescued_keep_best_min')):.3f}`",
        f"- interval midpoint: `{_safe_float(summary.get('safe_interval_midpoint')):.3f}`",
        "",
    ]
    selected_rule_id = _safe_str(summary.get("selected_rule_id"))
    if selected_rule_id:
        lines.extend(
            [
                "Selected rule:",
                f"- `{selected_rule_id}`",
                f"- earliest shared checkpoint: `restart{_safe_int(summary.get('selected_earliest_shared_checkpoint_restart_count'))}`",
                f"- mean checkpoint elapsed share: `{_safe_float(summary.get('selected_earliest_shared_checkpoint_elapsed_share')):.3f}`",
                f"- mean share improvement vs late gate: `{_safe_float(summary.get('selected_earliest_shared_checkpoint_share_improvement_vs_late_gate')):.3f}`",
                "",
            ]
        )

    lines.append("Candidate rule sweep:")
    for row in candidate_rows:
        lines.extend(
            [
                f"- `{_safe_str(row.get('rule_id'))}`",
                f"  - late family matches: `{_safe_int(row.get('late_family_match_count'))}` / `{_safe_int(row.get('late_family_row_count'))}`",
                f"  - shared checkpoints: `{_safe_int(row.get('shared_checkpoint_count'))}`",
                f"  - earliest shared checkpoint: `restart{_safe_int(row.get('earliest_shared_checkpoint_restart_count'))}`",
                f"  - share improvement: `{_safe_float(row.get('earliest_shared_checkpoint_share_improvement_vs_late_gate')):.3f}`",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    started_at = _utc_now()
    output_dir = (
        REPO_ROOT
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "analysis"
        / "fixed_instance_solver_development_v1"
        / f"{_utc_label()}__{RUN_LABEL}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} output_dir={_relative_path(output_dir)} "
        f"late_family_bundle={_relative_path(LATE_FAMILY_BUNDLE_DIR)} "
        f"provisional_bundle={_relative_path(PROVISIONAL_BUNDLE_DIR)} "
        f"rank1_threshold={RANK1_THRESHOLD:.2f}"
    )

    late_family_rows = _build_late_family_rows()
    provisional_rows = _build_provisional_rows()
    interval_bounds = _collect_interval_bounds(
        late_family_rows=late_family_rows,
        provisional_rows=provisional_rows,
        rank1_threshold=RANK1_THRESHOLD,
    )

    candidate_rows = [
        _evaluate_candidate_rule(
            rank1_threshold=RANK1_THRESHOLD,
            best_threshold=float(best_threshold),
            late_family_rows=late_family_rows,
            provisional_rows=provisional_rows,
        )
        for best_threshold in BEST_THRESHOLD_CANDIDATES
    ]
    candidate_rows.sort(key=lambda row: _safe_float(row.get("best_threshold")))
    summary = _build_summary(candidate_rows=candidate_rows, interval_bounds=interval_bounds)
    recommendation = {
        "recommendation": _safe_str(summary.get("recommendation")),
        "next_branch": _safe_str(summary.get("next_branch")),
        "reason": _safe_str(summary.get("reason")),
        "selected_rule_id": _safe_str(summary.get("selected_rule_id")),
        "selected_best_threshold": _safe_float(summary.get("selected_best_threshold")),
    }

    rows_csv_path = (
        output_dir
        / "selected_family_low_edge_phasea_checkpoint_refinement_candidate_rows.csv"
    )
    rows_jsonl_path = (
        output_dir
        / "selected_family_low_edge_phasea_checkpoint_refinement_candidate_rows.jsonl"
    )
    summary_path = (
        output_dir / "selected_family_low_edge_phasea_checkpoint_refinement_summary.json"
    )
    recommendation_path = (
        output_dir
        / "selected_family_low_edge_phasea_checkpoint_refinement_recommendation.json"
    )
    readout_path = (
        output_dir / "selected_family_low_edge_phasea_checkpoint_refinement_readout.md"
    )

    _write_csv(rows_csv_path, candidate_rows)
    _write_jsonl(rows_jsonl_path, candidate_rows)
    _write_json(summary_path, summary)
    _write_json(recommendation_path, recommendation)
    readout_path.write_text(
        _build_readout(summary=summary, candidate_rows=candidate_rows),
        encoding="utf-8",
    )
    refresh_catalog_safely()

    elapsed_seconds = max(0.0, (_utc_now() - started_at).total_seconds())
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} elapsed_seconds={elapsed_seconds:.1f} "
        f"recommendation={_safe_str(summary.get('recommendation'))} "
        f"selected_rule={_safe_str(summary.get('selected_rule_id'))} "
        f"output_dir={_relative_path(output_dir)}"
    )


if __name__ == "__main__":
    main()
