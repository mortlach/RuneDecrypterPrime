from __future__ import annotations

import csv
import json
import math
import sys
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
        "extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1.py"
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


RUN_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1"
)
QUESTION = (
    "Across the retained fixed 1111/search7001-7005 family, does "
    "phaseA_best_init_match persist early enough and cleanly enough that the "
    "next provisional rule should be a direct best_init threshold rather than "
    "the current composite rank1-or-best rule?"
)
SUSPICION = (
    "The provisional checkpoint surface is mostly one-field: "
    "phaseA_best_init_match should stay stable from restart16 onward and "
    "separate filtered from kept 1111 lanes on the full retained family."
)
MAIN_ALTERNATIVE = (
    "The apparent separation may collapse once the missing 7004 provisional "
    "lane is filled, or richer checkpoint fields may still be needed."
)
DECISION_RULE = (
    "Advance only if the full retained 1111 family shows a stable early "
    "phaseA_best_init_match separation with one concrete threshold candidate. "
    "Refine if the signal is promising but too narrow or incomplete. Hold if "
    "the full-family provisional surface does not support a cleaner rule than "
    "the current composite threshold."
)
CHECKPOINT_COUNTS = (16, 32, 48, 64)
FILTERED_SEEDS = (7001, 7002)
KEPT_SEEDS = (7003, 7004, 7005)
SEARCH_SEEDS = FILTERED_SEEDS + KEPT_SEEDS
EXPECTED_GATE_VERDICT_BY_SEED = {
    7001: "filter",
    7002: "filter",
    7003: "keep",
    7004: "keep",
    7005: "keep",
}
REFERENCE_BUNDLE_DIR = (
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
REFERENCE_ROWS_CSV = (
    REFERENCE_BUNDLE_DIR / "selected_family_low_edge_phasea_gate_live_read_followon_rows.csv"
)
CHILD_OUTPUT_DIR_BY_SEED = {
    7001: (
        REPO_ROOT
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "analysis"
        / "fixed_instance_solver_development_v1"
        / "20260424T193014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirm_exact_replay_1111_search7001_v1"
    ),
    7002: (
        REPO_ROOT
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "analysis"
        / "fixed_instance_solver_development_v1"
        / "20260424T175849Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_exact_replay_1111_search7002_v1"
    ),
    7003: (
        REPO_ROOT
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "analysis"
        / "fixed_instance_solver_development_v1"
        / "20260424T183152Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_exact_replay_1111_search7003_v1"
    ),
    7004: (
        REPO_ROOT
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "analysis"
        / "fixed_instance_solver_development_v1"
        / "20260424T203709Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1"
    ),
    7005: (
        REPO_ROOT
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "analysis"
        / "fixed_instance_solver_development_v1"
        / "20260424T195256Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirm_exact_replay_1111_search7005_v1"
    ),
}
FIELD_CANDIDATES = (
    "phaseA_rank1_init_match",
    "phaseA_rank1_final_match",
    "phaseA_best_init_match",
    "phaseA_best_final_match",
    "phaseA_rank1_plateau_would_stop",
)
FIELD_PRIORITY = {
    "phaseA_best_init_match": 0,
    "phaseA_best_final_match": 1,
    "phaseA_rank1_init_match": 2,
    "phaseA_rank1_final_match": 3,
    "phaseA_rank1_plateau_would_stop": 4,
}
NEXT_BRANCH_ADVANCE = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_threshold_action_canary"
)
NEXT_BRANCH_REFINE = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_richer_field_refinement"
)
PERSIST_EPS = 1e-12


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_label() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


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


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(float(seconds))))
    hours, rem = divmod(total_seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {_relative_path(path)}")
    fieldnames = list(dict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _append_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True))
            handle.write("\n")


def _print_progress(message: str) -> None:
    print(f"[{_utc_now_iso()}] {message}", flush=True)


def _load_reference_rows() -> dict[int, dict[str, Any]]:
    rows = list(csv.DictReader(REFERENCE_ROWS_CSV.open(encoding="utf-8")))
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        seed = _safe_int(row.get("search_seed"))
        if seed not in SEARCH_SEEDS:
            continue
        out[seed] = {
            "search_seed": seed,
            "baseline_best_match_ratio": _safe_float(row.get("baseline_best_match_ratio")),
            "retained_stage3_reference_match_ratio": _safe_float(
                row.get("retained_stage3_reference_match_ratio")
            ),
            "late_gate_elapsed_share": _safe_float(
                row.get("phasea_gate_snapshot_elapsed_share")
            ),
            "late_gate_best_init_match": _safe_float(row.get("phasea_best_init_match")),
            "expected_gate_verdict": _safe_str(row.get("expected_gate_verdict")),
        }
    missing = [seed for seed in SEARCH_SEEDS if seed not in out]
    if missing:
        raise RuntimeError(f"Missing reference rows for seeds: {missing}")
    return out


def _load_checkpoint_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing checkpoint file: {_relative_path(path)}")
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(dict(json.loads(line)))
    return rows


def _load_attempt_status(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing attempt_status.json: {_relative_path(path)}")
    return _load_json(path)


def _build_rows(
    *,
    reference_rows: Mapping[int, Mapping[str, Any]],
    child_output_dir_by_seed: Mapping[int, Path],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for search_seed in SEARCH_SEEDS:
        child_dir = child_output_dir_by_seed[int(search_seed)]
        attempt_status = _load_attempt_status(child_dir / "attempt_status.json")
        checkpoints = _load_checkpoint_rows(
            child_dir / "resume_bundle" / "phasea_provisional_gate_snapshots.jsonl"
        )
        checkpoints_by_count = {
            _safe_int(row.get("phaseA_checkpoint_restart_count")): dict(row)
            for row in checkpoints
            if _safe_int(row.get("phaseA_checkpoint_restart_count")) in CHECKPOINT_COUNTS
        }
        missing_counts = [
            checkpoint
            for checkpoint in CHECKPOINT_COUNTS
            if checkpoint not in checkpoints_by_count
        ]
        if missing_counts:
            raise RuntimeError(
                f"Missing checkpoints for search{search_seed}: {missing_counts}"
            )
        reference_row = reference_rows[int(search_seed)]
        for checkpoint_count in CHECKPOINT_COUNTS:
            checkpoint = checkpoints_by_count[int(checkpoint_count)]
            row = {
                "search_seed": int(search_seed),
                "lane_role": (
                    "filtered" if int(search_seed) in FILTERED_SEEDS else "kept"
                ),
                "expected_gate_verdict": _safe_str(
                    reference_row.get("expected_gate_verdict")
                ),
                "status": _safe_str(attempt_status.get("status")),
                "output_dir": _relative_path(child_dir),
                "elapsed_seconds": _safe_float(attempt_status.get("elapsed_seconds")),
                "elapsed": _safe_str(attempt_status.get("elapsed")),
                "checkpoint_restart_count": int(checkpoint_count),
                "checkpoint_elapsed_seconds": _safe_float(
                    checkpoint.get("phaseA_checkpoint_elapsed_seconds")
                ),
                "checkpoint_elapsed_share": (
                    _safe_float(checkpoint.get("phaseA_checkpoint_elapsed_seconds"))
                    / _safe_float(attempt_status.get("elapsed_seconds"))
                    if _safe_float(attempt_status.get("elapsed_seconds")) > 0.0
                    else float("nan")
                ),
                "late_gate_elapsed_share": _safe_float(
                    reference_row.get("late_gate_elapsed_share")
                ),
                "checkpoint_share_improvement_vs_late_gate": (
                    _safe_float(reference_row.get("late_gate_elapsed_share"))
                    - (
                        _safe_float(checkpoint.get("phaseA_checkpoint_elapsed_seconds"))
                        / _safe_float(attempt_status.get("elapsed_seconds"))
                    )
                    if _safe_float(attempt_status.get("elapsed_seconds")) > 0.0
                    else float("nan")
                ),
                "late_gate_best_init_match": _safe_float(
                    reference_row.get("late_gate_best_init_match")
                ),
                "baseline_best_match_ratio": _safe_float(
                    reference_row.get("baseline_best_match_ratio")
                ),
                "retained_stage3_reference_match_ratio": _safe_float(
                    reference_row.get("retained_stage3_reference_match_ratio")
                ),
                "current_resume_best_match_ratio": _safe_float(
                    attempt_status.get("resume_best_match_ratio")
                ),
            }
            for field_name in FIELD_CANDIDATES:
                row[field_name] = (
                    _safe_float(checkpoint.get(field_name))
                    if field_name != "phaseA_rank1_plateau_would_stop"
                    else _safe_int(checkpoint.get(field_name))
                )
            rows.append(row)
    return rows


def _field_statistics(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows_by_seed: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        rows_by_seed.setdefault(_safe_int(row.get("search_seed")), []).append(dict(row))

    summaries: list[dict[str, Any]] = []
    for field_name in FIELD_CANDIDATES:
        lane_value_by_seed: dict[int, float] = {}
        persistent_all_lanes = 1
        coverage_complete = 1
        for search_seed in SEARCH_SEEDS:
            seed_rows = sorted(
                rows_by_seed.get(int(search_seed), []),
                key=lambda item: _safe_int(item.get("checkpoint_restart_count")),
            )
            if len(seed_rows) != len(CHECKPOINT_COUNTS):
                coverage_complete = 0
                persistent_all_lanes = 0
                continue
            values = [_safe_float(row.get(field_name)) for row in seed_rows]
            if any(not math.isfinite(value) for value in values):
                coverage_complete = 0
                persistent_all_lanes = 0
                continue
            if max(values) - min(values) > float(PERSIST_EPS):
                persistent_all_lanes = 0
            lane_value_by_seed[int(search_seed)] = float(values[0])

        filtered_values = [
            lane_value_by_seed[seed]
            for seed in FILTERED_SEEDS
            if seed in lane_value_by_seed
        ]
        kept_values = [
            lane_value_by_seed[seed] for seed in KEPT_SEEDS if seed in lane_value_by_seed
        ]
        filtered_max = (
            max(filtered_values) if len(filtered_values) == len(FILTERED_SEEDS) else float("nan")
        )
        kept_min = (
            min(kept_values) if len(kept_values) == len(KEPT_SEEDS) else float("nan")
        )
        gap = (
            float(kept_min - filtered_max)
            if math.isfinite(filtered_max) and math.isfinite(kept_min)
            else float("nan")
        )
        separating = int(
            1
            if coverage_complete
            and persistent_all_lanes
            and math.isfinite(gap)
            and gap > 0.0
            else 0
        )
        summaries.append(
            {
                "field_name": field_name,
                "coverage_complete": int(coverage_complete),
                "persistent_all_lanes": int(persistent_all_lanes),
                "filtered_max": filtered_max,
                "kept_min": kept_min,
                "separation_gap": gap,
                "separates_filtered_vs_kept": separating,
                "threshold_midpoint": (
                    float((filtered_max + kept_min) / 2.0)
                    if separating
                    else float("nan")
                ),
                "lane_value_search7001": lane_value_by_seed.get(7001, float("nan")),
                "lane_value_search7002": lane_value_by_seed.get(7002, float("nan")),
                "lane_value_search7003": lane_value_by_seed.get(7003, float("nan")),
                "lane_value_search7004": lane_value_by_seed.get(7004, float("nan")),
                "lane_value_search7005": lane_value_by_seed.get(7005, float("nan")),
            }
        )
    return summaries


def _select_field_candidate(
    field_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    candidates = [
        dict(row)
        for row in field_rows
        if _safe_int(row.get("separates_filtered_vs_kept")) == 1
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda row: (
            FIELD_PRIORITY.get(_safe_str(row.get("field_name")), 999),
            -_safe_float(row.get("separation_gap")),
        )
    )
    return dict(candidates[0])


def _build_summary(
    *,
    rows: Sequence[Mapping[str, Any]],
    field_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selected_field = _select_field_candidate(field_rows)
    coverage_complete = int(len({int(row["search_seed"]) for row in rows}) == len(SEARCH_SEEDS))
    if selected_field is None:
        recommendation = "hold"
        next_branch = NEXT_BRANCH_REFINE
        reason = (
            "the full retained provisional family did not yield a stable "
            "separating checkpoint field"
        )
    else:
        gap = _safe_float(selected_field.get("separation_gap"))
        if coverage_complete and gap >= 0.01:
            recommendation = "advance"
            next_branch = NEXT_BRANCH_ADVANCE
            reason = (
                "phaseA_best_init_match persists from restart16 onward and "
                "separates filtered from kept lanes on the full retained 1111 family"
            )
        else:
            recommendation = "refine"
            next_branch = NEXT_BRANCH_REFINE
            reason = (
                "a stable separating checkpoint field exists, but the full-family "
                "gap is too narrow or incomplete for immediate action reopening"
            )
    return {
        "question": QUESTION,
        "suspicion": SUSPICION,
        "alternative": MAIN_ALTERNATIVE,
        "decision_rule": DECISION_RULE,
        "completed_seeds": int(len({int(row["search_seed"]) for row in rows})),
        "stable_field_count": int(
            sum(1 for row in field_rows if _safe_int(row.get("persistent_all_lanes")) == 1)
        ),
        "stable_separating_field_count": int(
            sum(
                1
                for row in field_rows
                if _safe_int(row.get("separates_filtered_vs_kept")) == 1
            )
        ),
        "selected_field_name": _safe_str(
            selected_field.get("field_name") if selected_field else ""
        ),
        "selected_filtered_max": _safe_float(
            selected_field.get("filtered_max") if selected_field else float("nan")
        ),
        "selected_kept_min": _safe_float(
            selected_field.get("kept_min") if selected_field else float("nan")
        ),
        "selected_gap": _safe_float(
            selected_field.get("separation_gap") if selected_field else float("nan")
        ),
        "selected_threshold_midpoint": _safe_float(
            selected_field.get("threshold_midpoint") if selected_field else float("nan")
        ),
        "selected_checkpoint_support": ",".join(str(value) for value in CHECKPOINT_COUNTS),
        "recommendation": recommendation,
        "next_branch": next_branch,
        "reason": reason,
    }


def _build_readout(
    *,
    summary: Mapping[str, Any],
    field_rows: Sequence[Mapping[str, Any]],
) -> str:
    lines = [
        "# Phase-A Checkpoint Field-Persistence Audit",
        "",
        "Question:",
        f"- {QUESTION}",
        "",
        "Outcome:",
        f"- recommendation: `{_safe_str(summary.get('recommendation'))}`",
        f"- selected field: `{_safe_str(summary.get('selected_field_name'))}`",
        f"- selected filtered max: `{_safe_float(summary.get('selected_filtered_max')):.3f}`",
        f"- selected kept min: `{_safe_float(summary.get('selected_kept_min')):.3f}`",
        f"- selected gap: `{_safe_float(summary.get('selected_gap')):.3f}`",
        f"- threshold midpoint: `{_safe_float(summary.get('selected_threshold_midpoint')):.3f}`",
        f"- reason: {_safe_str(summary.get('reason'))}",
        "",
        "Field scan:",
    ]
    for row in field_rows:
        lines.extend(
            [
                f"- `{_safe_str(row.get('field_name'))}`",
                f"  - persistent all lanes: `{_safe_int(row.get('persistent_all_lanes'))}`",
                f"  - separates filtered vs kept: `{_safe_int(row.get('separates_filtered_vs_kept'))}`",
                f"  - filtered max: `{_safe_float(row.get('filtered_max')):.3f}`",
                f"  - kept min: `{_safe_float(row.get('kept_min')):.3f}`",
                f"  - gap: `{_safe_float(row.get('separation_gap')):.3f}`",
                f"  - search7001: `{_safe_float(row.get('lane_value_search7001')):.3f}`",
                f"  - search7002: `{_safe_float(row.get('lane_value_search7002')):.3f}`",
                f"  - search7003: `{_safe_float(row.get('lane_value_search7003')):.3f}`",
                f"  - search7004: `{_safe_float(row.get('lane_value_search7004')):.3f}`",
                f"  - search7005: `{_safe_float(row.get('lane_value_search7005')):.3f}`",
            ]
        )
    return "\n".join(lines) + "\n"


def run_audit(
    *,
    output_dir: Path | None = None,
    child_output_dir_by_seed: Mapping[int, Path] | None = None,
) -> dict[str, Any]:
    actual_output_dir = output_dir or (
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
    actual_output_dir.mkdir(parents=True, exist_ok=False)
    actual_child_dirs = dict(child_output_dir_by_seed or CHILD_OUTPUT_DIR_BY_SEED)

    rows_csv_path = (
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_field_persistence_rows.csv"
    )
    rows_jsonl_path = (
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_field_persistence_rows.jsonl"
    )
    field_csv_path = (
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_field_persistence_field_summary.csv"
    )
    summary_path = (
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_field_persistence_summary.json"
    )
    recommendation_path = (
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_field_persistence_recommendation.json"
    )
    readout_path = (
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_field_persistence_readout.md"
    )

    reference_rows = _load_reference_rows()
    rows = _build_rows(
        reference_rows=reference_rows,
        child_output_dir_by_seed=actual_child_dirs,
    )
    field_rows = _field_statistics(rows)
    summary = _build_summary(rows=rows, field_rows=field_rows)
    recommendation = {
        "recommendation": _safe_str(summary.get("recommendation")),
        "next_branch": _safe_str(summary.get("next_branch")),
        "selected_field_name": _safe_str(summary.get("selected_field_name")),
        "selected_threshold_midpoint": _safe_float(
            summary.get("selected_threshold_midpoint")
        ),
        "reason": _safe_str(summary.get("reason")),
    }

    _write_csv(rows_csv_path, rows)
    _append_jsonl(rows_jsonl_path, rows)
    _write_csv(field_csv_path, field_rows)
    _write_json(summary_path, summary)
    _write_json(recommendation_path, recommendation)
    readout_path.write_text(
        _build_readout(summary=summary, field_rows=field_rows), encoding="utf-8"
    )
    refresh_catalog_safely()
    return {
        "output_dir": _relative_path(actual_output_dir),
        "summary_path": _relative_path(summary_path),
        "recommendation": _safe_str(summary.get("recommendation")),
        "selected_field_name": _safe_str(summary.get("selected_field_name")),
        "selected_threshold_midpoint": _safe_float(
            summary.get("selected_threshold_midpoint")
        ),
        "reason": _safe_str(summary.get("reason")),
    }


def main() -> None:
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} question={json.dumps(QUESTION)}"
    )
    result = run_audit()
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} recommendation={result['recommendation']} "
        f"selected_field={result['selected_field_name']} "
        f"threshold={result['selected_threshold_midpoint']:.6f} "
        f"output_dir={result['output_dir']}"
    )


if __name__ == "__main__":
    main()
