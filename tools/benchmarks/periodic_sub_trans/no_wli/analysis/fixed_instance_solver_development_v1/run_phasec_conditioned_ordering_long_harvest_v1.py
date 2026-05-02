from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_phasec_conditioned_ordering_long_harvest_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    explore_phasec_saved_surface_phaseb_mass_and_frontload_matrix_v1 as base_mod,
)


RUN_LABEL = "phasec_conditioned_ordering_long_harvest_v1"

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

TARGET_CASES: tuple[tuple[int, int], ...] = (
    (1111, 7004),
    (611, 7003),
    (1511, 7005),
    (1511, 7003),
)

SELECTED_POLICY_NAMES: tuple[str, ...] = (
    "source_order",
    "phaseb_topk_anchor_swap_v1",
    "phaseb_topk_frontload_all_v1",
    "phaseb_topk_frontload_1_v1",
    "phaseb_topk_frontload_2_v1",
    "phaseb_topk_frontload_4_v1",
    "phaseb_topk_frontload_8_v1",
    "phaseb_topk_quota_1_v1",
    "phaseb_topk_quota_2_v1",
    "phaseb_topk_quota_4_v1",
    "phaseb_topk_quota_8_v1",
    "phaseb_topk_replace_width_1_v1",
    "phaseb_topk_replace_width_2_v1",
    "phaseb_topk_replace_width_4_v1",
    "phaseb_topk_replace_width_8_v1",
)

MAX_WALLCLOCK_SECONDS = 36 * 60 * 60
PARTIAL_OUTPUT_IS_VALID = 1
CAP_CHECK_GRANULARITY = "after_each_policy_unit"


class HarvestStop(Exception):
    """Raised after a completed policy unit when the wallclock cap is reached."""


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(value: Any) -> int:
    return base_mod._safe_int(value)


def _safe_float(value: Any) -> float:
    return base_mod._safe_float(value)


def _safe_str(value: Any) -> str:
    return base_mod._safe_str(value)


def _relative_path(path: Path) -> str:
    return base_mod._relative_path(path)


def _format_duration(seconds: float) -> str:
    return base_mod._format_duration(seconds)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True))
            handle.write("\n")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(dict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload: dict[str, Any] = {}
            for key, value in dict(row).items():
                if isinstance(value, float) and not math.isfinite(value):
                    payload[key] = ""
                elif isinstance(value, (list, dict)):
                    payload[key] = json.dumps(value, sort_keys=True)
                else:
                    payload[key] = value
            writer.writerow(payload)


def _emit_event(output_dir: Path, event: Mapping[str, Any]) -> None:
    path = output_dir / "matrix_run_events.jsonl"
    payload = {"timestamp_utc": _utc_now(), **dict(event)}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True))
        handle.write("\n")


def _print_progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] {message}", flush=True)


def _target_case_key(row: Mapping[str, Any]) -> tuple[int, int]:
    return (_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed")))


def _load_target_case_specs() -> list[dict[str, Any]]:
    by_key = {
        _target_case_key(row): dict(row)
        for row in base_mod._load_case_specs()
    }
    missing = [case_key for case_key in TARGET_CASES if case_key not in by_key]
    if missing:
        raise ValueError(f"Missing target case specs from source matrix: {missing!r}")
    return [dict(by_key[case_key]) for case_key in TARGET_CASES]


def _load_selected_policy_specs() -> list[dict[str, Any]]:
    by_name = {
        _safe_str(row.get("policy_name")): dict(row)
        for row in base_mod._build_policy_specs()
    }
    missing = [name for name in SELECTED_POLICY_NAMES if name not in by_name]
    if missing:
        raise ValueError(f"Missing selected policy specs: {missing!r}")
    return [dict(by_name[name]) for name in SELECTED_POLICY_NAMES]


def _build_config_payload() -> dict[str, Any]:
    return {
        "run_label": RUN_LABEL,
        "target_cases": [
            {"fixture_seed": int(fixture), "search_seed": int(search)}
            for fixture, search in TARGET_CASES
        ],
        "selected_policy_names": list(SELECTED_POLICY_NAMES),
        "max_wallclock_seconds": int(MAX_WALLCLOCK_SECONDS),
        "partial_output_is_valid": int(PARTIAL_OUTPUT_IS_VALID),
        "cap_check_granularity": str(CAP_CHECK_GRANULARITY),
        "source_matrix_summary_relpath": (
            base_mod.SOURCE_MATRIX_SUMMARY_REL_PATH.as_posix()
        ),
    }


def _write_readout(
    *,
    output_dir: Path,
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    recommendation: Mapping[str, Any],
    run_state: Mapping[str, Any],
) -> None:
    lines: list[str] = [
        "# Phase-C Conditioned Ordering Long Harvest v1",
        "",
        "Purpose:",
        "- collect detailed saved-surface / route / policy evidence for a small number of named cells",
        "- decide whether Phase-C ordering should become a conditioned rule rather than a global policy",
        "",
        "Status:",
        f"- status: `{_safe_str(run_state.get('status'))}`",
        f"- recommendation: `{_safe_str(recommendation.get('recommendation'))}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        f"- completed policy units: `{_safe_int(run_state.get('completed_policy_units'))}` / `{_safe_int(run_state.get('total_policy_units'))}`",
        f"- bundle complete: `{_safe_int(run_state.get('bundle_complete'))}`",
        f"- elapsed: `{_safe_str(run_state.get('elapsed_hhmmss'))}`",
        "",
        "Target cases:",
    ]
    for fixture, search in TARGET_CASES:
        lines.append(f"- `{fixture}/search{search}`")

    lines.extend(
        [
            "",
            "Policy families:",
            "",
            "| family | best policy | width | usable gates | positive | neutral | negative | mean vs best reorder | changed surfaces | winner changes |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in list(summary.get("policy_family_summary_rows", []) or []):
        lines.append(
            f"| `{_safe_str(row.get('policy_family'))}` | "
            f"`{_safe_str(row.get('best_policy_name'))}` | "
            f"`{_safe_str(row.get('best_requested_width')) or '-'} ` | "
            f"`{_safe_int(row.get('best_usable_decision_gate_cases'))}` | "
            f"`{_safe_int(row.get('best_positive_on_gate'))}` | "
            f"`{_safe_int(row.get('best_neutral_on_gate'))}` | "
            f"`{_safe_int(row.get('best_negative_on_gate'))}` | "
            f"`{_safe_float(row.get('best_mean_vs_best_reorder_on_gate')):.3f}` | "
            f"`{_safe_int(row.get('best_selected_surface_changed_cases'))}` | "
            f"`{_safe_int(row.get('best_winner_identity_changed_cases'))}` |"
        )

    lines.extend(
        [
            "",
            "Best usable-gate policy by case:",
            "",
            "| case | best policy | family | best match | delta | flat read |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in list(summary.get("best_policy_by_case_rows", []) or []):
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}/search{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_str(row.get('best_policy_name'))}` | "
            f"`{_safe_str(row.get('best_policy_family'))}` | "
            f"`{_safe_float(row.get('best_candidate_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('best_candidate_minus_control')):.3f}` | "
            f"`{_safe_str(row.get('best_flat_delta_case_class'))}` |"
        )

    lines.extend(
        [
            "",
            "Completed policy rows:",
            "",
            "| case | policy | group | width | control | candidate | delta | changed | winner changed | read |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}/search{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_str(row.get('policy_name'))}` | "
            f"`{_safe_str(row.get('policy_group'))}` | "
            f"`{_safe_str(row.get('requested_width')) or '-'} ` | "
            f"`{_safe_float(row.get('control_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('candidate_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('candidate_minus_control_best_match_ratio')):.3f}` | "
            f"`{_safe_str(row.get('selected_surface_change_class'))}` | "
            f"`{_safe_int(row.get('winner_identity_changed'))}` | "
            f"`{_safe_str(row.get('decision_gate_read'))}` |"
        )

    (output_dir / "phasec_conditioned_ordering_long_harvest_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def _build_run_state(
    *,
    output_dir: Path,
    status: str,
    started_at_utc: str,
    elapsed_seconds: float,
    total_cases: int,
    total_policy_units: int,
    completed_cases: int,
    completed_policy_units: int,
    rows: Sequence[Mapping[str, Any]],
    recommendation: Mapping[str, Any],
    stop_reason: str,
) -> dict[str, Any]:
    bundle_complete = int(completed_policy_units == total_policy_units)
    return {
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "status": str(status),
        "started_at_utc": str(started_at_utc),
        "updated_at_utc": _utc_now(),
        "elapsed_seconds": float(elapsed_seconds),
        "elapsed_hhmmss": _format_duration(elapsed_seconds),
        "total_cases": int(total_cases),
        "completed_cases": int(completed_cases),
        "total_policy_units": int(total_policy_units),
        "completed_policy_units": int(completed_policy_units),
        "bundle_complete": int(bundle_complete),
        "partial_output_is_valid": int(PARTIAL_OUTPUT_IS_VALID),
        "row_count": int(len(rows)),
        "stop_reason": str(stop_reason),
        "recommendation": dict(recommendation),
        "config": _build_config_payload(),
    }


def _write_snapshot(
    *,
    output_dir: Path,
    rows: Sequence[Mapping[str, Any]],
    started_at_utc: str,
    started_at_monotonic: float,
    total_cases: int,
    total_policy_units: int,
    completed_cases: int,
    completed_policy_units: int,
    status: str,
    stop_reason: str,
) -> dict[str, Any]:
    elapsed_seconds = monotonic() - started_at_monotonic
    annotated_rows = base_mod.annotate_against_best_reorder_control(rows)
    annotated_rows = sorted(
        [dict(row) for row in annotated_rows],
        key=lambda row: (
            _safe_int(row.get("fixture_seed")),
            _safe_int(row.get("search_seed")),
            _safe_str(row.get("policy_family")),
            _safe_str(row.get("requested_width")),
            _safe_str(row.get("policy_name")),
        ),
    )

    if annotated_rows:
        summary = base_mod.build_summary(annotated_rows)
        base_recommendation = base_mod.build_recommendation(summary=summary)
    else:
        summary = {
            "run_label": RUN_LABEL,
            "case_count": 0,
            "policy_summary_rows": [],
            "policy_family_summary_rows": [],
            "best_policy_by_case_rows": [],
        }
        base_recommendation = {
            "recommendation": "hold",
            "best_policy_family": "",
            "best_policy_name": "",
            "best_requested_width": "",
            "reason": "No policy rows have completed yet.",
        }

    bundle_complete = int(completed_policy_units == total_policy_units)
    if not bundle_complete:
        recommendation = {
            **dict(base_recommendation),
            "recommendation": "hold",
            "reason": (
                "Partial harvest only; completed rows are saved and usable for "
                "inspection, but the planned microbatch is not complete."
            ),
            "base_recommendation_on_completed_rows": dict(base_recommendation),
        }
    else:
        recommendation = dict(base_recommendation)

    summary = {
        **dict(summary),
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "source_matrix_summary_relpath": (
            base_mod.SOURCE_MATRIX_SUMMARY_REL_PATH.as_posix()
        ),
        "recommendation": dict(recommendation),
        "config": _build_config_payload(),
    }

    run_state = _build_run_state(
        output_dir=output_dir,
        status=status,
        started_at_utc=started_at_utc,
        elapsed_seconds=elapsed_seconds,
        total_cases=total_cases,
        total_policy_units=total_policy_units,
        completed_cases=completed_cases,
        completed_policy_units=completed_policy_units,
        rows=annotated_rows,
        recommendation=recommendation,
        stop_reason=stop_reason,
    )

    _write_jsonl(
        output_dir / "phasec_conditioned_ordering_long_harvest_case_rows.jsonl",
        annotated_rows,
    )
    _write_csv(
        output_dir / "phasec_conditioned_ordering_long_harvest_case_rows.csv",
        annotated_rows,
    )
    _write_csv(
        output_dir / "phasec_conditioned_ordering_long_harvest_policy_summary_rows.csv",
        list(summary.get("policy_summary_rows", []) or []),
    )
    _write_csv(
        output_dir / "phasec_conditioned_ordering_long_harvest_family_summary_rows.csv",
        list(summary.get("policy_family_summary_rows", []) or []),
    )
    _write_json(
        output_dir / "phasec_conditioned_ordering_long_harvest_summary.json",
        summary,
    )
    _write_json(
        output_dir / "phasec_conditioned_ordering_long_harvest_recommendation.json",
        recommendation,
    )
    _write_json(output_dir / "matrix_run_state.json", run_state)
    _write_json(
        output_dir / "run_summary.json",
        {
            "output_dir": _relative_path(output_dir),
            "status": str(status),
            "recommendation": _safe_str(recommendation.get("recommendation")),
            "completed_policy_units": int(completed_policy_units),
            "total_policy_units": int(total_policy_units),
            "bundle_complete": int(bundle_complete),
        },
    )
    _write_readout(
        output_dir=output_dir,
        rows=annotated_rows,
        summary=summary,
        recommendation=recommendation,
        run_state=run_state,
    )
    return run_state


def _check_cap(*, started_at_monotonic: float) -> None:
    elapsed = monotonic() - started_at_monotonic
    if elapsed >= float(MAX_WALLCLOCK_SECONDS):
        raise HarvestStop(
            "wallclock cap reached after a completed policy unit: "
            f"{_format_duration(elapsed)}"
        )


def run_harvest() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    cases_dir = output_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    started_at_utc = _utc_now()
    started_at_monotonic = monotonic()
    case_specs = _load_target_case_specs()
    policy_specs = _load_selected_policy_specs()

    total_cases = int(len(case_specs))
    total_policy_units = int(total_cases * len(policy_specs))
    completed_cases = 0
    completed_policy_units = 0
    rows: list[dict[str, Any]] = []
    status = "running"
    stop_reason = ""

    _write_json(output_dir / "run_config.json", _build_config_payload())
    _emit_event(
        output_dir,
        {
            "event": "run_started",
            "run_label": RUN_LABEL,
            "status": status,
            "total_cases": total_cases,
            "total_policy_units": total_policy_units,
            "output_dir": _relative_path(output_dir),
        },
    )
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} "
        f"output_dir={_relative_path(output_dir)} "
        f"cases={total_cases} "
        f"policies={len(policy_specs)} "
        f"units={total_policy_units} "
        f"cap={_format_duration(MAX_WALLCLOCK_SECONDS)}"
    )

    try:
        for case_index, case_spec in enumerate(case_specs, start=1):
            bundle_relpath = _safe_str(case_spec.get("bundle_relpath"))
            source_artifact_relpath = _safe_str(case_spec.get("source_artifact_relpath"))
            fixture_seed = _safe_int(case_spec.get("fixture_seed"))
            search_seed = _safe_int(case_spec.get("search_seed"))
            bundle_path = REPO_ROOT / bundle_relpath
            case_dir = cases_dir / f"fixture_{fixture_seed}__search{search_seed}"
            case_dir.mkdir(parents=True, exist_ok=False)

            _emit_event(
                output_dir,
                {
                    "event": "case_started",
                    "case_index": case_index,
                    "total_cases": total_cases,
                    "fixture_seed": fixture_seed,
                    "search_seed": search_seed,
                    "status": status,
                },
            )
            _print_progress(
                "case_started "
                f"case={case_index}/{total_cases} "
                f"fixture={fixture_seed} "
                f"search={search_seed} "
                f"elapsed={_format_duration(monotonic() - started_at_monotonic)}"
            )

            control_summary = base_mod._load_json(
                bundle_path / "control_saved_surface_summary.json"
            )
            anchor_swap_candidate_summary = base_mod._load_json(
                bundle_path / "candidate_saved_surface_summary.json"
            )
            anchor_swap_comparison_summary = base_mod._load_json(
                bundle_path / "comparison_summary.json"
            )
            case = base_mod.resume_mod.load_artifact_case(
                artifact_path=REPO_ROOT / source_artifact_relpath
            )
            saved_rows = base_mod.exact_mod._load_saved_start_rows(case.artifact)
            candidate_pool_rows = base_mod._load_saved_candidate_pool_rows(case.artifact)

            _write_json(
                case_dir / "case_manifest.json",
                {
                    "fixture_seed": int(fixture_seed),
                    "search_seed": int(search_seed),
                    "bundle_relpath": str(bundle_relpath),
                    "source_artifact_relpath": str(source_artifact_relpath),
                    "saved_start_count": int(len(saved_rows)),
                    "saved_candidate_pool_row_count": int(len(candidate_pool_rows)),
                },
            )

            for policy_index, policy_spec in enumerate(policy_specs, start=1):
                policy_name = _safe_str(policy_spec.get("policy_name"))
                policy_group = _safe_str(policy_spec.get("policy_group"))
                policy_family = _safe_str(policy_spec.get("policy_family"))
                requested_width = _safe_str(policy_spec.get("requested_width"))
                policy_started_at = monotonic()

                _emit_event(
                    output_dir,
                    {
                        "event": "policy_started",
                        "case_index": case_index,
                        "policy_index": policy_index,
                        "fixture_seed": fixture_seed,
                        "search_seed": search_seed,
                        "policy_name": policy_name,
                        "completed_policy_units": completed_policy_units,
                        "total_policy_units": total_policy_units,
                        "status": status,
                    },
                )

                if _safe_str(policy_spec.get("mode")) == "source_order":
                    candidate_rows = list(saved_rows)
                    candidate_summary = base_mod._clone_source_order_candidate_summary(
                        control_summary
                    )
                    comparison_summary = base_mod._build_source_order_comparison_summary(
                        control_summary=control_summary,
                        anchor_swap_comparison_summary=anchor_swap_comparison_summary,
                        source_artifact_relpath=source_artifact_relpath,
                    )
                elif _safe_str(policy_spec.get("mode")) == "existing_anchor_swap":
                    candidate_rows = None
                    candidate_summary = dict(anchor_swap_candidate_summary)
                    comparison_summary = dict(anchor_swap_comparison_summary)
                else:
                    builder = policy_spec.get("builder")
                    if not callable(builder):
                        raise TypeError(
                            f"Policy builder missing or not callable: {policy_name}"
                        )
                    candidate_rows = builder(saved_rows, candidate_pool_rows)
                    candidate_summary = base_mod.exact_mod.run_saved_surface_phasec_replay(
                        case=case,
                        saved_rows=candidate_rows,
                        replay_label=str(policy_name),
                    )
                    comparison_summary = base_mod.exact_mod.build_comparison_summary(
                        case=case,
                        control_summary=control_summary,
                        candidate_summary=candidate_summary,
                    )

                diagnostics = base_mod.build_surface_diagnostics(
                    control_summary=control_summary,
                    candidate_summary=candidate_summary,
                    comparison_summary=comparison_summary,
                    candidate_rows=candidate_rows,
                    policy_group=policy_group,
                )
                row = base_mod.build_policy_row(
                    policy_name=policy_name,
                    policy_group=policy_group,
                    policy_family=policy_family,
                    requested_width=requested_width,
                    bundle_relpath=bundle_relpath,
                    comparison_summary=comparison_summary,
                    diagnostics=diagnostics,
                )
                rows.append(row)

                policy_stub = f"{policy_index:02d}__{policy_name}"
                _write_json(
                    case_dir / f"{policy_stub}__candidate_saved_surface_summary.json",
                    candidate_summary,
                )
                _write_json(
                    case_dir / f"{policy_stub}__comparison_summary.json",
                    comparison_summary,
                )
                _write_json(
                    case_dir / f"{policy_stub}__surface_diagnostics.json",
                    diagnostics,
                )

                completed_policy_units += 1
                elapsed = monotonic() - started_at_monotonic
                eta_seconds = (
                    (elapsed / completed_policy_units)
                    * (total_policy_units - completed_policy_units)
                    if completed_policy_units > 0
                    else float("nan")
                )

                _emit_event(
                    output_dir,
                    {
                        "event": "policy_finished",
                        "case_index": case_index,
                        "policy_index": policy_index,
                        "fixture_seed": fixture_seed,
                        "search_seed": search_seed,
                        "policy_name": policy_name,
                        "completed_policy_units": completed_policy_units,
                        "total_policy_units": total_policy_units,
                        "candidate_minus_control_best_match_ratio": _safe_float(
                            comparison_summary.get(
                                "candidate_minus_control_best_match_ratio"
                            )
                        ),
                        "flat_delta_case_class": _safe_str(
                            diagnostics.get("flat_delta_case_class")
                        ),
                        "winner_identity_changed": _safe_int(
                            diagnostics.get("winner_identity_changed")
                        ),
                        "status": status,
                    },
                )
                _print_progress(
                    "policy_finished "
                    f"unit={completed_policy_units}/{total_policy_units} "
                    f"case={case_index}/{total_cases} "
                    f"fixture={fixture_seed} "
                    f"search={search_seed} "
                    f"policy={policy_name} "
                    f"delta={_safe_float(comparison_summary.get('candidate_minus_control_best_match_ratio')):.3f} "
                    f"change={_safe_str(diagnostics.get('flat_delta_case_class'))} "
                    f"winner_changed={_safe_int(diagnostics.get('winner_identity_changed'))} "
                    f"elapsed={_format_duration(elapsed)} "
                    f"eta={_format_duration(eta_seconds)} "
                    f"policy_runtime={_format_duration(monotonic() - policy_started_at)}"
                )

                _write_snapshot(
                    output_dir=output_dir,
                    rows=rows,
                    started_at_utc=started_at_utc,
                    started_at_monotonic=started_at_monotonic,
                    total_cases=total_cases,
                    total_policy_units=total_policy_units,
                    completed_cases=completed_cases,
                    completed_policy_units=completed_policy_units,
                    status=status,
                    stop_reason=stop_reason,
                )
                _check_cap(started_at_monotonic=started_at_monotonic)

            completed_cases += 1
            _emit_event(
                output_dir,
                {
                    "event": "case_finished",
                    "case_index": case_index,
                    "total_cases": total_cases,
                    "fixture_seed": fixture_seed,
                    "search_seed": search_seed,
                    "completed_cases": completed_cases,
                    "status": status,
                },
            )

        status = "completed"
        stop_reason = "completed_all_planned_policy_units"

    except HarvestStop as exc:
        status = "capped"
        stop_reason = str(exc)

    except Exception as exc:
        status = "failed"
        stop_reason = f"{type(exc).__name__}: {exc}"
        _emit_event(
            output_dir,
            {
                "event": "run_failed",
                "status": status,
                "stop_reason": stop_reason,
                "completed_policy_units": completed_policy_units,
                "total_policy_units": total_policy_units,
            },
        )
        final_state = _write_snapshot(
            output_dir=output_dir,
            rows=rows,
            started_at_utc=started_at_utc,
            started_at_monotonic=started_at_monotonic,
            total_cases=total_cases,
            total_policy_units=total_policy_units,
            completed_cases=completed_cases,
            completed_policy_units=completed_policy_units,
            status=status,
            stop_reason=stop_reason,
        )
        raise RuntimeError(json.dumps(final_state, sort_keys=True)) from exc

    final_state = _write_snapshot(
        output_dir=output_dir,
        rows=rows,
        started_at_utc=started_at_utc,
        started_at_monotonic=started_at_monotonic,
        total_cases=total_cases,
        total_policy_units=total_policy_units,
        completed_cases=completed_cases,
        completed_policy_units=completed_policy_units,
        status=status,
        stop_reason=stop_reason,
    )

    _emit_event(
        output_dir,
        {
            "event": "run_finished",
            "status": status,
            "recommendation": _safe_str(
                final_state.get("recommendation", {}).get("recommendation")
            ),
            "completed_policy_units": completed_policy_units,
            "total_policy_units": total_policy_units,
            "bundle_complete": _safe_int(final_state.get("bundle_complete")),
            "output_dir": _relative_path(output_dir),
        },
    )
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} "
        f"status={status} "
        f"elapsed={_safe_str(final_state.get('elapsed_hhmmss'))} "
        f"recommendation={_safe_str(final_state.get('recommendation', {}).get('recommendation'))} "
        f"completed_units={completed_policy_units}/{total_policy_units} "
        f"output_dir={_relative_path(output_dir)}"
    )
    return dict(final_state)


def main() -> None:
    print(json.dumps(run_harvest(), sort_keys=True))


if __name__ == "__main__":
    main()