from __future__ import annotations

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
        "extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1.py"
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
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1 as base_mod,
)


RUN_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1"
)
QUESTION = (
    "If full checkpoint persistence from restart16 is too strict because "
    "filtered 7002 is still moving, what is the earliest checkpoint window "
    "where the retained 1111 family becomes stable enough to support a clean "
    "best_init threshold?"
)
SUSPICION = (
    "phaseA_best_init_match should become stable and separating from "
    "restart32 onward, yielding one honest earlier-than-late threshold."
)
MAIN_ALTERNATIVE = (
    "Even after allowing a later stabilization window, the full retained family "
    "may still not support a clean best_init threshold."
)
DECISION_RULE = (
    "Advance only if a stable separating best_init window appears at restart32 "
    "or earlier. Refine if the first stable separating window is later but "
    "still materially earlier than the late gate. Hold if no stable separating "
    "window exists."
)
WINDOW_STARTS = (16, 32, 48, 64)
NEXT_BRANCH_ADVANCE = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_canary"
)
NEXT_BRANCH_REFINE = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_refinement"
)


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
    return base_mod._safe_float(value)


def _safe_int(value: Any) -> int:
    return base_mod._safe_int(value)


def _safe_str(value: Any) -> str:
    return base_mod._safe_str(value)


def _write_json(path: Path, payload: Any) -> None:
    base_mod._write_json(path, payload)


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    base_mod._write_csv(path, rows)


def _append_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    base_mod._append_jsonl(path, rows)


def _print_progress(message: str) -> None:
    print(f"[{_utc_now_iso()}] {message}", flush=True)


def _window_statistics(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows_by_seed: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        rows_by_seed.setdefault(_safe_int(row.get("search_seed")), []).append(dict(row))

    summary_rows: list[dict[str, Any]] = []
    for field_name in base_mod.FIELD_CANDIDATES:
        for window_start in WINDOW_STARTS:
            lane_value_by_seed: dict[int, float] = {}
            coverage_complete = 1
            persistent_all_lanes = 1
            for search_seed in base_mod.SEARCH_SEEDS:
                seed_rows = sorted(
                    [
                        dict(row)
                        for row in rows_by_seed.get(int(search_seed), [])
                        if _safe_int(row.get("checkpoint_restart_count")) >= int(window_start)
                    ],
                    key=lambda row: _safe_int(row.get("checkpoint_restart_count")),
                )
                expected_count = len(
                    [
                        checkpoint
                        for checkpoint in base_mod.CHECKPOINT_COUNTS
                        if checkpoint >= int(window_start)
                    ]
                )
                if len(seed_rows) != expected_count:
                    coverage_complete = 0
                    persistent_all_lanes = 0
                    continue
                values = [_safe_float(row.get(field_name)) for row in seed_rows]
                if any(not math.isfinite(value) for value in values):
                    coverage_complete = 0
                    persistent_all_lanes = 0
                    continue
                if max(values) - min(values) > float(base_mod.PERSIST_EPS):
                    persistent_all_lanes = 0
                lane_value_by_seed[int(search_seed)] = float(values[-1])

            filtered_values = [
                lane_value_by_seed[seed]
                for seed in base_mod.FILTERED_SEEDS
                if seed in lane_value_by_seed
            ]
            kept_values = [
                lane_value_by_seed[seed]
                for seed in base_mod.KEPT_SEEDS
                if seed in lane_value_by_seed
            ]
            filtered_max = (
                max(filtered_values)
                if len(filtered_values) == len(base_mod.FILTERED_SEEDS)
                else float("nan")
            )
            kept_min = (
                min(kept_values)
                if len(kept_values) == len(base_mod.KEPT_SEEDS)
                else float("nan")
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

            window_rows = [
                dict(row)
                for row in rows
                if _safe_int(row.get("checkpoint_restart_count")) == int(window_start)
            ]
            mean_window_share = (
                float(
                    sum(_safe_float(row.get("checkpoint_elapsed_share")) for row in window_rows)
                    / len(window_rows)
                )
                if window_rows
                else float("nan")
            )
            mean_window_improvement = (
                float(
                    sum(
                        _safe_float(row.get("checkpoint_share_improvement_vs_late_gate"))
                        for row in window_rows
                    )
                    / len(window_rows)
                )
                if window_rows
                else float("nan")
            )
            summary_rows.append(
                {
                    "field_name": field_name,
                    "window_start_restart_count": int(window_start),
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
                    "mean_window_elapsed_share": mean_window_share,
                    "mean_window_share_improvement_vs_late_gate": mean_window_improvement,
                    "lane_value_search7001": lane_value_by_seed.get(7001, float("nan")),
                    "lane_value_search7002": lane_value_by_seed.get(7002, float("nan")),
                    "lane_value_search7003": lane_value_by_seed.get(7003, float("nan")),
                    "lane_value_search7004": lane_value_by_seed.get(7004, float("nan")),
                    "lane_value_search7005": lane_value_by_seed.get(7005, float("nan")),
                }
            )
    return summary_rows


def _select_candidate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        dict(row)
        for row in rows
        if _safe_int(row.get("separates_filtered_vs_kept")) == 1
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda row: (
            _safe_int(row.get("window_start_restart_count")),
            base_mod.FIELD_PRIORITY.get(_safe_str(row.get("field_name")), 999),
            -_safe_float(row.get("separation_gap")),
        )
    )
    return dict(candidates[0])


def _build_summary(window_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    selected = _select_candidate(window_rows)
    if selected is None:
        recommendation = "hold"
        next_branch = NEXT_BRANCH_REFINE
        reason = "no stable separating checkpoint window exists on the full retained family"
    else:
        window_start = _safe_int(selected.get("window_start_restart_count"))
        if window_start <= 32:
            recommendation = "advance"
            next_branch = NEXT_BRANCH_ADVANCE
            reason = (
                "phaseA_best_init_match becomes stable and separating from restart32 "
                "onward with meaningful timing headroom versus the late gate"
            )
        else:
            recommendation = "refine"
            next_branch = NEXT_BRANCH_REFINE
            reason = (
                "a stable separating checkpoint window exists, but it begins later "
                "than restart32"
            )
    return {
        "question": QUESTION,
        "suspicion": SUSPICION,
        "alternative": MAIN_ALTERNATIVE,
        "decision_rule": DECISION_RULE,
        "stable_separating_window_count": int(
            sum(1 for row in window_rows if _safe_int(row.get("separates_filtered_vs_kept")) == 1)
        ),
        "selected_field_name": _safe_str(selected.get("field_name") if selected else ""),
        "selected_window_start_restart_count": _safe_int(
            selected.get("window_start_restart_count") if selected else 0
        ),
        "selected_filtered_max": _safe_float(
            selected.get("filtered_max") if selected else float("nan")
        ),
        "selected_kept_min": _safe_float(
            selected.get("kept_min") if selected else float("nan")
        ),
        "selected_gap": _safe_float(
            selected.get("separation_gap") if selected else float("nan")
        ),
        "selected_threshold_midpoint": _safe_float(
            selected.get("threshold_midpoint") if selected else float("nan")
        ),
        "selected_mean_window_elapsed_share": _safe_float(
            selected.get("mean_window_elapsed_share") if selected else float("nan")
        ),
        "selected_mean_window_share_improvement_vs_late_gate": _safe_float(
            selected.get("mean_window_share_improvement_vs_late_gate")
            if selected
            else float("nan")
        ),
        "recommendation": recommendation,
        "next_branch": next_branch,
        "reason": reason,
    }


def _build_readout(
    *,
    summary: Mapping[str, Any],
    window_rows: Sequence[Mapping[str, Any]],
) -> str:
    lines = [
        "# Phase-A Checkpoint Stabilization-Window Audit",
        "",
        "Question:",
        f"- {QUESTION}",
        "",
        "Outcome:",
        f"- recommendation: `{_safe_str(summary.get('recommendation'))}`",
        f"- selected field: `{_safe_str(summary.get('selected_field_name'))}`",
        f"- selected window: `restart{_safe_int(summary.get('selected_window_start_restart_count'))}`",
        f"- filtered max: `{_safe_float(summary.get('selected_filtered_max')):.3f}`",
        f"- kept min: `{_safe_float(summary.get('selected_kept_min')):.3f}`",
        f"- gap: `{_safe_float(summary.get('selected_gap')):.3f}`",
        f"- threshold midpoint: `{_safe_float(summary.get('selected_threshold_midpoint')):.3f}`",
        f"- mean elapsed share: `{_safe_float(summary.get('selected_mean_window_elapsed_share')):.3f}`",
        f"- mean share improvement vs late gate: `{_safe_float(summary.get('selected_mean_window_share_improvement_vs_late_gate')):.3f}`",
        f"- reason: {_safe_str(summary.get('reason'))}",
        "",
        "Window scan:",
    ]
    for row in window_rows:
        lines.extend(
            [
                f"- `{_safe_str(row.get('field_name'))}` from `restart{_safe_int(row.get('window_start_restart_count'))}`",
                f"  - persistent all lanes: `{_safe_int(row.get('persistent_all_lanes'))}`",
                f"  - separates filtered vs kept: `{_safe_int(row.get('separates_filtered_vs_kept'))}`",
                f"  - filtered max: `{_safe_float(row.get('filtered_max')):.3f}`",
                f"  - kept min: `{_safe_float(row.get('kept_min')):.3f}`",
                f"  - gap: `{_safe_float(row.get('separation_gap')):.3f}`",
                f"  - mean elapsed share: `{_safe_float(row.get('mean_window_elapsed_share')):.3f}`",
                f"  - mean share improvement: `{_safe_float(row.get('mean_window_share_improvement_vs_late_gate')):.3f}`",
            ]
        )
    return "\n".join(lines) + "\n"


def run_audit(*, output_dir: Path | None = None) -> dict[str, Any]:
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

    rows = base_mod._build_rows(
        reference_rows=base_mod._load_reference_rows(),
        child_output_dir_by_seed=base_mod.CHILD_OUTPUT_DIR_BY_SEED,
    )
    window_rows = _window_statistics(rows)
    summary = _build_summary(window_rows)
    recommendation = {
        "recommendation": _safe_str(summary.get("recommendation")),
        "next_branch": _safe_str(summary.get("next_branch")),
        "selected_field_name": _safe_str(summary.get("selected_field_name")),
        "selected_window_start_restart_count": _safe_int(
            summary.get("selected_window_start_restart_count")
        ),
        "selected_threshold_midpoint": _safe_float(
            summary.get("selected_threshold_midpoint")
        ),
        "reason": _safe_str(summary.get("reason")),
    }

    _write_csv(
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_stabilization_window_rows.csv",
        window_rows,
    )
    _append_jsonl(
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_stabilization_window_rows.jsonl",
        window_rows,
    )
    _write_json(
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_stabilization_window_summary.json",
        summary,
    )
    _write_json(
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_stabilization_window_recommendation.json",
        recommendation,
    )
    (
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_stabilization_window_readout.md"
    ).write_text(
        _build_readout(summary=summary, window_rows=window_rows), encoding="utf-8"
    )
    refresh_catalog_safely()
    return {
        "output_dir": _relative_path(actual_output_dir),
        "recommendation": _safe_str(summary.get("recommendation")),
        "selected_field_name": _safe_str(summary.get("selected_field_name")),
        "selected_window_start_restart_count": _safe_int(
            summary.get("selected_window_start_restart_count")
        ),
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
        f"window_start=restart{result['selected_window_start_restart_count']} "
        f"threshold={result['selected_threshold_midpoint']:.6f} "
        f"output_dir={result['output_dir']}"
    )


if __name__ == "__main__":
    main()
