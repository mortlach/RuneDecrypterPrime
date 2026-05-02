from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
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
        "Could not locate repo root from run_phasec_multi_thread_long_harvest_v1.py"
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


RUN_LABEL = "phasec_multi_thread_long_harvest_v1"

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

MAX_WALLCLOCK_SECONDS = 25 * 60 * 60
PARTIAL_OUTPUT_IS_VALID = 1
CAP_CHECK_GRANULARITY = "after_each_policy_unit"

PASS_PLAN: tuple[tuple[int, str], ...] = (
    (1, "full_width_atlas"),
    (2, "stability_repeat_pass"),
    (3, "stability_repeat_pass"),
)

# Leave empty to use every policy from base_mod._build_policy_specs().
# This should currently be 27 policies:
# source_order, anchor_swap, frontload_all, frontload_1..8, quota_1..8, replace_1..8.
SELECTED_POLICY_NAMES: tuple[str, ...] = ()

# Leave empty to use every source-matrix case from base_mod._load_case_specs().
# To restrict manually, use e.g. ((1111, 7004), (611, 7003)).
SELECTED_CASES: tuple[tuple[int, int], ...] = ()


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


def _json_safe(value: Any) -> Any:
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_json_safe(dict(row)), sort_keys=True))
            handle.write("\n")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in dict(row).keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload: dict[str, Any] = {}
            for key in fieldnames:
                value = dict(row).get(key, "")
                if isinstance(value, float) and not math.isfinite(value):
                    payload[key] = ""
                elif isinstance(value, (list, dict)):
                    payload[key] = json.dumps(_json_safe(value), sort_keys=True)
                else:
                    payload[key] = value
            writer.writerow(payload)


def _emit_event(output_dir: Path, event: Mapping[str, Any]) -> None:
    path = output_dir / "matrix_run_events.jsonl"
    payload = {"timestamp_utc": _utc_now(), **dict(event)}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_json_safe(payload), sort_keys=True))
        handle.write("\n")


def _print_progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] {message}", flush=True)


def _case_key(row: Mapping[str, Any]) -> tuple[int, int]:
    return (_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed")))


def _load_selected_case_specs() -> list[dict[str, Any]]:
    case_specs = [dict(row) for row in base_mod._load_case_specs()]
    if not SELECTED_CASES:
        return case_specs

    by_key = {_case_key(row): dict(row) for row in case_specs}
    missing = [case_key for case_key in SELECTED_CASES if case_key not in by_key]
    if missing:
        raise ValueError(f"Missing selected case specs from source matrix: {missing!r}")
    return [dict(by_key[case_key]) for case_key in SELECTED_CASES]


def _load_selected_policy_specs() -> list[dict[str, Any]]:
    policy_specs = [dict(row) for row in base_mod._build_policy_specs()]
    if not SELECTED_POLICY_NAMES:
        return policy_specs

    by_name = {_safe_str(row.get("policy_name")): dict(row) for row in policy_specs}
    missing = [name for name in SELECTED_POLICY_NAMES if name not in by_name]
    if missing:
        raise ValueError(f"Missing selected policy specs: {missing!r}")
    return [dict(by_name[name]) for name in SELECTED_POLICY_NAMES]


def _policy_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        _safe_str(row.get("policy_family")),
        _safe_str(row.get("requested_width")),
        _safe_str(row.get("policy_name")),
    )


def _run_unit_count(case_specs: Sequence[Mapping[str, Any]], policy_specs: Sequence[Mapping[str, Any]]) -> int:
    return int(len(PASS_PLAN) * len(case_specs) * len(policy_specs))


def _build_config_payload(
    *,
    case_specs: Sequence[Mapping[str, Any]],
    policy_specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "run_label": RUN_LABEL,
        "max_wallclock_seconds": int(MAX_WALLCLOCK_SECONDS),
        "partial_output_is_valid": int(PARTIAL_OUTPUT_IS_VALID),
        "cap_check_granularity": str(CAP_CHECK_GRANULARITY),
        "pass_plan": [
            {"pass_index": int(pass_index), "science_thread": str(science_thread)}
            for pass_index, science_thread in PASS_PLAN
        ],
        "case_count": int(len(case_specs)),
        "policy_count": int(len(policy_specs)),
        "total_policy_units": int(_run_unit_count(case_specs, policy_specs)),
        "selected_cases": [
            {
                "fixture_seed": _safe_int(row.get("fixture_seed")),
                "search_seed": _safe_int(row.get("search_seed")),
            }
            for row in case_specs
        ],
        "selected_policy_names": [
            _safe_str(row.get("policy_name")) for row in policy_specs
        ],
        "source_matrix_summary_relpath": (
            base_mod.SOURCE_MATRIX_SUMMARY_REL_PATH.as_posix()
        ),
    }


def _mean(values: Sequence[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return float("nan")
    return float(sum(finite) / len(finite))


def _max(values: Sequence[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return float("nan")
    return float(max(finite))


def _min(values: Sequence[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return float("nan")
    return float(min(finite))


def _group_rows(
    rows: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(dict(row).get(field) for field in fields)].append(dict(row))
    return dict(grouped)


def _build_pass_summary_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    grouped = _group_rows(rows, ["pass_index", "science_thread"])
    for (pass_index, science_thread), group_rows in sorted(grouped.items()):
        usable_rows = [
            row for row in group_rows if _safe_int(row.get("usable_decision_gate")) == 1
        ]
        deltas = [
            _safe_float(row.get("candidate_minus_control_best_match_ratio"))
            for row in usable_rows
        ]
        vs_reorder = [
            _safe_float(row.get("vs_best_reorder_delta"))
            for row in usable_rows
        ]
        out.append(
            {
                "pass_index": _safe_int(pass_index),
                "science_thread": _safe_str(science_thread),
                "row_count": int(len(group_rows)),
                "usable_row_count": int(len(usable_rows)),
                "case_count": int(
                    len(
                        {
                            (
                                _safe_int(row.get("fixture_seed")),
                                _safe_int(row.get("search_seed")),
                            )
                            for row in group_rows
                        }
                    )
                ),
                "policy_count": int(
                    len({_safe_str(row.get("policy_name")) for row in group_rows})
                ),
                "mean_delta_on_gate": _mean(deltas),
                "mean_vs_best_reorder_on_gate": _mean(vs_reorder),
                "positive_on_gate": int(
                    sum(
                        1
                        for row in usable_rows
                        if _safe_str(row.get("candidate_effect")) == "positive"
                    )
                ),
                "neutral_on_gate": int(
                    sum(
                        1
                        for row in usable_rows
                        if _safe_str(row.get("candidate_effect")) == "neutral"
                    )
                ),
                "negative_on_gate": int(
                    sum(
                        1
                        for row in usable_rows
                        if _safe_str(row.get("candidate_effect")) == "negative"
                    )
                ),
                "selected_surface_changed_count": int(
                    sum(_safe_int(row.get("selected_surface_changed")) for row in group_rows)
                ),
                "winner_identity_changed_count": int(
                    sum(_safe_int(row.get("winner_identity_changed")) for row in group_rows)
                ),
            }
        )
    return out


def _build_science_thread_summary_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    grouped = _group_rows(rows, ["science_thread"])
    for (science_thread,), group_rows in sorted(grouped.items()):
        usable_rows = [
            row for row in group_rows if _safe_int(row.get("usable_decision_gate")) == 1
        ]
        deltas = [
            _safe_float(row.get("candidate_minus_control_best_match_ratio"))
            for row in usable_rows
        ]
        vs_reorder = [
            _safe_float(row.get("vs_best_reorder_delta"))
            for row in usable_rows
        ]
        out.append(
            {
                "science_thread": _safe_str(science_thread),
                "row_count": int(len(group_rows)),
                "usable_row_count": int(len(usable_rows)),
                "pass_count": int(len({_safe_int(row.get("pass_index")) for row in group_rows})),
                "case_count": int(
                    len(
                        {
                            (
                                _safe_int(row.get("fixture_seed")),
                                _safe_int(row.get("search_seed")),
                            )
                            for row in group_rows
                        }
                    )
                ),
                "policy_count": int(
                    len({_safe_str(row.get("policy_name")) for row in group_rows})
                ),
                "mean_delta_on_gate": _mean(deltas),
                "mean_vs_best_reorder_on_gate": _mean(vs_reorder),
                "positive_on_gate": int(
                    sum(
                        1
                        for row in usable_rows
                        if _safe_str(row.get("candidate_effect")) == "positive"
                    )
                ),
                "neutral_on_gate": int(
                    sum(
                        1
                        for row in usable_rows
                        if _safe_str(row.get("candidate_effect")) == "neutral"
                    )
                ),
                "negative_on_gate": int(
                    sum(
                        1
                        for row in usable_rows
                        if _safe_str(row.get("candidate_effect")) == "negative"
                    )
                ),
                "selected_surface_changed_count": int(
                    sum(_safe_int(row.get("selected_surface_changed")) for row in group_rows)
                ),
                "winner_identity_changed_count": int(
                    sum(_safe_int(row.get("winner_identity_changed")) for row in group_rows)
                ),
            }
        )
    return out


def _build_repeat_consistency_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    grouped = _group_rows(rows, ["fixture_seed", "search_seed", "policy_name"])
    for (fixture_seed, search_seed, policy_name), group_rows in sorted(grouped.items()):
        scores = [
            _safe_float(row.get("candidate_best_match_ratio"))
            for row in group_rows
        ]
        deltas = [
            _safe_float(row.get("candidate_minus_control_best_match_ratio"))
            for row in group_rows
        ]
        winner_hashes = [
            _safe_str(row.get("candidate_winner_candidate_hash"))
            for row in group_rows
        ]
        surface_classes = [
            _safe_str(row.get("selected_surface_change_class"))
            for row in group_rows
        ]
        score_min = _min(scores)
        score_max = _max(scores)
        delta_min = _min(deltas)
        delta_max = _max(deltas)
        distinct_score_values = sorted(
            {
                f"{score:.12f}"
                for score in scores
                if math.isfinite(score)
            }
        )
        distinct_delta_values = sorted(
            {
                f"{delta:.12f}"
                for delta in deltas
                if math.isfinite(delta)
            }
        )
        distinct_winner_hashes = sorted({item for item in winner_hashes if item})
        distinct_surface_classes = sorted({item for item in surface_classes if item})
        out.append(
            {
                "fixture_seed": _safe_int(fixture_seed),
                "search_seed": _safe_int(search_seed),
                "policy_name": _safe_str(policy_name),
                "pass_count": int(len(group_rows)),
                "completed_pass_indices": sorted(
                    [_safe_int(row.get("pass_index")) for row in group_rows]
                ),
                "score_min": score_min,
                "score_max": score_max,
                "score_range": (
                    float(score_max - score_min)
                    if math.isfinite(score_min) and math.isfinite(score_max)
                    else float("nan")
                ),
                "delta_min": delta_min,
                "delta_max": delta_max,
                "delta_range": (
                    float(delta_max - delta_min)
                    if math.isfinite(delta_min) and math.isfinite(delta_max)
                    else float("nan")
                ),
                "distinct_score_value_count": int(len(distinct_score_values)),
                "distinct_delta_value_count": int(len(distinct_delta_values)),
                "distinct_winner_hash_count": int(len(distinct_winner_hashes)),
                "distinct_surface_class_count": int(len(distinct_surface_classes)),
                "score_consistent": int(1 if len(distinct_score_values) <= 1 else 0),
                "delta_consistent": int(1 if len(distinct_delta_values) <= 1 else 0),
                "winner_consistent": int(1 if len(distinct_winner_hashes) <= 1 else 0),
                "surface_class_consistent": int(
                    1 if len(distinct_surface_classes) <= 1 else 0
                ),
                "distinct_score_values": distinct_score_values,
                "distinct_delta_values": distinct_delta_values,
                "distinct_winner_hashes": distinct_winner_hashes,
                "distinct_surface_classes": distinct_surface_classes,
            }
        )
    return out


def _build_long_recommendation(
    *,
    bundle_complete: int,
    completed_policy_units: int,
    total_policy_units: int,
    base_recommendation: Mapping[str, Any],
    repeat_consistency_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    inconsistent_rows = [
        row
        for row in repeat_consistency_rows
        if _safe_int(row.get("pass_count")) > 1
        and (
            _safe_int(row.get("score_consistent")) != 1
            or _safe_int(row.get("delta_consistent")) != 1
            or _safe_int(row.get("winner_consistent")) != 1
        )
    ]

    if inconsistent_rows:
        return {
            "recommendation": "investigate_nondeterminism",
            "next_branch_label": "phasec_repeatability_mismatch_review_v1",
            "reason": (
                "Repeated saved-surface replay rows changed score, delta, or winner. "
                "Inspect repeat consistency before interpreting policy effects."
            ),
            "inconsistent_repeat_row_count": int(len(inconsistent_rows)),
            "base_recommendation_on_completed_rows": dict(base_recommendation),
        }

    if bundle_complete != 1:
        return {
            "recommendation": "hold",
            "next_branch_label": "",
            "reason": (
                "Long harvest is partial. Completed rows are valid, but the planned "
                f"unit set is not complete: {completed_policy_units}/{total_policy_units}."
            ),
            "base_recommendation_on_completed_rows": dict(base_recommendation),
        }

    base_value = _safe_str(base_recommendation.get("recommendation"))
    if base_value in {"promote", "refine"}:
        return {
            "recommendation": "review",
            "next_branch_label": "phasec_conditioned_ordering_rule_review_v1",
            "reason": (
                "The completed harvest has candidate policy signal in the base "
                "summary. Review manually before designing a conditioned rule; do "
                "not promote a global policy automatically."
            ),
            "base_recommendation_on_completed_rows": dict(base_recommendation),
        }

    if base_value == "close":
        return {
            "recommendation": "close_or_hold",
            "next_branch_label": "",
            "reason": (
                "Completed long harvest did not show a candidate family beating "
                "the reorder-only controls, and repeated rows were stable."
            ),
            "base_recommendation_on_completed_rows": dict(base_recommendation),
        }

    return {
        "recommendation": "review",
        "next_branch_label": "manual_phasec_long_harvest_review_v1",
        "reason": (
            "Completed long harvest has no determinism mismatch, but the base "
            "recommendation was not one of the expected terminal values."
        ),
        "base_recommendation_on_completed_rows": dict(base_recommendation),
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
        "# Phase-C Multi-Thread Long Harvest v1",
        "",
        "Purpose:",
        "- run a 25-hour-capped saved-surface replay harvest at roughly 20x the pilot size",
        "- compare reorder controls, width/depth/quota/replacement variants, and repeated-pass stability",
        "",
        "Status:",
        f"- status: `{_safe_str(run_state.get('status'))}`",
        f"- recommendation: `{_safe_str(recommendation.get('recommendation'))}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        f"- completed policy units: `{_safe_int(run_state.get('completed_policy_units'))}` / `{_safe_int(run_state.get('total_policy_units'))}`",
        f"- bundle complete: `{_safe_int(run_state.get('bundle_complete'))}`",
        f"- elapsed: `{_safe_str(run_state.get('elapsed_hhmmss'))}`",
        "",
        "Science threads:",
        "",
        "| pass | thread | rows | usable | mean delta | mean vs reorder | positive | neutral | negative | changed surfaces | winner changes |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in list(summary.get("pass_summary_rows", []) or []):
        lines.append(
            f"| {_safe_int(row.get('pass_index'))} | "
            f"`{_safe_str(row.get('science_thread'))}` | "
            f"{_safe_int(row.get('row_count'))} | "
            f"{_safe_int(row.get('usable_row_count'))} | "
            f"{_safe_float(row.get('mean_delta_on_gate')):.3f} | "
            f"{_safe_float(row.get('mean_vs_best_reorder_on_gate')):.3f} | "
            f"{_safe_int(row.get('positive_on_gate'))} | "
            f"{_safe_int(row.get('neutral_on_gate'))} | "
            f"{_safe_int(row.get('negative_on_gate'))} | "
            f"{_safe_int(row.get('selected_surface_changed_count'))} | "
            f"{_safe_int(row.get('winner_identity_changed_count'))} |"
        )

    lines.extend(
        [
            "",
            "Per-family summary:",
            "",
            "| family | best policy | width | usable gates | positive | neutral | negative | mean vs best reorder | changed surfaces | winner changes |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for row in list(summary.get("policy_family_summary_rows", []) or []):
        lines.append(
            f"| `{_safe_str(row.get('policy_family'))}` | "
            f"`{_safe_str(row.get('best_policy_name'))}` | "
            f"`{_safe_str(row.get('best_requested_width')) or '-'} ` | "
            f"{_safe_int(row.get('best_usable_decision_gate_cases'))} | "
            f"{_safe_int(row.get('best_positive_on_gate'))} | "
            f"{_safe_int(row.get('best_neutral_on_gate'))} | "
            f"{_safe_int(row.get('best_negative_on_gate'))} | "
            f"{_safe_float(row.get('best_mean_vs_best_reorder_on_gate')):.3f} | "
            f"{_safe_int(row.get('best_selected_surface_changed_cases'))} | "
            f"{_safe_int(row.get('best_winner_identity_changed_cases'))} |"
        )

    lines.extend(
        [
            "",
            "Best usable-gate policy by case:",
            "",
            "| case | best policy | family | best match | delta | flat read |",
            "| --- | --- | --- | ---: | ---: | --- |",
        ]
    )

    for row in list(summary.get("best_policy_by_case_rows", []) or []):
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}/search{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_str(row.get('best_policy_name'))}` | "
            f"`{_safe_str(row.get('best_policy_family'))}` | "
            f"{_safe_float(row.get('best_candidate_best_match_ratio')):.3f} | "
            f"{_safe_float(row.get('best_candidate_minus_control')):.3f} | "
            f"`{_safe_str(row.get('best_flat_delta_case_class'))}` |"
        )

    repeat_rows = list(summary.get("repeat_consistency_rows", []) or [])
    inconsistent = [
        row
        for row in repeat_rows
        if _safe_int(row.get("pass_count")) > 1
        and (
            _safe_int(row.get("score_consistent")) != 1
            or _safe_int(row.get("delta_consistent")) != 1
            or _safe_int(row.get("winner_consistent")) != 1
        )
    ]

    lines.extend(
        [
            "",
            "Repeat consistency:",
            f"- repeat rows: `{len(repeat_rows)}`",
            f"- inconsistent repeated rows: `{len(inconsistent)}`",
            "",
        ]
    )

    if inconsistent:
        lines.extend(
            [
                "Top repeat mismatches:",
                "",
                "| case | policy | passes | score range | delta range | winner hashes |",
                "| --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in inconsistent[:20]:
            lines.append(
                f"| `{_safe_int(row.get('fixture_seed'))}/search{_safe_int(row.get('search_seed'))}` | "
                f"`{_safe_str(row.get('policy_name'))}` | "
                f"{_safe_int(row.get('pass_count'))} | "
                f"{_safe_float(row.get('score_range')):.12f} | "
                f"{_safe_float(row.get('delta_range')):.12f} | "
                f"{_safe_int(row.get('distinct_winner_hash_count'))} |"
            )

    lines.extend(
        [
            "",
            "Interpretation guard:",
            "",
            "- This run does not reopen live runtime.",
            "- This run does not promote any global policy automatically.",
            "- Score movement should be tied to saved-surface or winner-route diagnostics before any rule is designed.",
            "- If the run is capped, partial rows are valid but the recommendation should remain conservative.",
            "",
        ]
    )

    (output_dir / "phasec_multi_thread_long_harvest_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def _build_run_state(
    *,
    output_dir: Path,
    status: str,
    started_at_utc: str,
    elapsed_seconds: float,
    case_count: int,
    policy_count: int,
    total_policy_units: int,
    completed_policy_units: int,
    rows: Sequence[Mapping[str, Any]],
    recommendation: Mapping[str, Any],
    stop_reason: str,
    config: Mapping[str, Any],
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
        "case_count": int(case_count),
        "policy_count": int(policy_count),
        "pass_count": int(len(PASS_PLAN)),
        "total_policy_units": int(total_policy_units),
        "completed_policy_units": int(completed_policy_units),
        "bundle_complete": int(bundle_complete),
        "partial_output_is_valid": int(PARTIAL_OUTPUT_IS_VALID),
        "row_count": int(len(rows)),
        "stop_reason": str(stop_reason),
        "recommendation": dict(recommendation),
        "config": dict(config),
    }


def _write_snapshot(
    *,
    output_dir: Path,
    rows: Sequence[Mapping[str, Any]],
    started_at_utc: str,
    started_at_monotonic: float,
    case_count: int,
    policy_count: int,
    total_policy_units: int,
    completed_policy_units: int,
    status: str,
    stop_reason: str,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    elapsed_seconds = monotonic() - started_at_monotonic

    annotated_rows = base_mod.annotate_against_best_reorder_control(rows)
    annotated_rows = sorted(
        [dict(row) for row in annotated_rows],
        key=lambda row: (
            _safe_int(row.get("pass_index")),
            _safe_int(row.get("fixture_seed")),
            _safe_int(row.get("search_seed")),
            _safe_str(row.get("policy_family")),
            _safe_str(row.get("requested_width")),
            _safe_str(row.get("policy_name")),
        ),
    )

    if annotated_rows:
        base_summary = base_mod.build_summary(annotated_rows)
        base_recommendation = base_mod.build_recommendation(summary=base_summary)
    else:
        base_summary = {
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

    pass_summary_rows = _build_pass_summary_rows(annotated_rows)
    science_thread_summary_rows = _build_science_thread_summary_rows(annotated_rows)
    repeat_consistency_rows = _build_repeat_consistency_rows(annotated_rows)

    bundle_complete = int(completed_policy_units == total_policy_units)
    recommendation = _build_long_recommendation(
        bundle_complete=bundle_complete,
        completed_policy_units=completed_policy_units,
        total_policy_units=total_policy_units,
        base_recommendation=base_recommendation,
        repeat_consistency_rows=repeat_consistency_rows,
    )

    summary = {
        **dict(base_summary),
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "base_recommendation": dict(base_recommendation),
        "recommendation": dict(recommendation),
        "config": dict(config),
        "pass_summary_rows": pass_summary_rows,
        "science_thread_summary_rows": science_thread_summary_rows,
        "repeat_consistency_rows": repeat_consistency_rows,
    }

    run_state = _build_run_state(
        output_dir=output_dir,
        status=status,
        started_at_utc=started_at_utc,
        elapsed_seconds=elapsed_seconds,
        case_count=case_count,
        policy_count=policy_count,
        total_policy_units=total_policy_units,
        completed_policy_units=completed_policy_units,
        rows=annotated_rows,
        recommendation=recommendation,
        stop_reason=stop_reason,
        config=config,
    )

    _write_jsonl(
        output_dir / "phasec_multi_thread_long_harvest_case_rows.jsonl",
        annotated_rows,
    )
    _write_csv(
        output_dir / "phasec_multi_thread_long_harvest_case_rows.csv",
        annotated_rows,
    )
    _write_csv(
        output_dir / "phasec_multi_thread_long_harvest_policy_summary_rows.csv",
        list(summary.get("policy_summary_rows", []) or []),
    )
    _write_csv(
        output_dir / "phasec_multi_thread_long_harvest_family_summary_rows.csv",
        list(summary.get("policy_family_summary_rows", []) or []),
    )
    _write_csv(
        output_dir / "phasec_multi_thread_long_harvest_pass_summary_rows.csv",
        pass_summary_rows,
    )
    _write_csv(
        output_dir / "phasec_multi_thread_long_harvest_science_thread_summary_rows.csv",
        science_thread_summary_rows,
    )
    _write_csv(
        output_dir / "phasec_multi_thread_long_harvest_repeat_consistency_rows.csv",
        repeat_consistency_rows,
    )
    _write_json(
        output_dir / "phasec_multi_thread_long_harvest_summary.json",
        summary,
    )
    _write_json(
        output_dir / "phasec_multi_thread_long_harvest_recommendation.json",
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
            "elapsed_hhmmss": _format_duration(elapsed_seconds),
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

    case_specs = _load_selected_case_specs()
    policy_specs = _load_selected_policy_specs()
    total_policy_units = _run_unit_count(case_specs, policy_specs)
    config = _build_config_payload(case_specs=case_specs, policy_specs=policy_specs)

    completed_policy_units = 0
    rows: list[dict[str, Any]] = []
    status = "running"
    stop_reason = ""

    _write_json(output_dir / "run_config.json", config)
    _emit_event(
        output_dir,
        {
            "event": "run_started",
            "run_label": RUN_LABEL,
            "status": status,
            "case_count": len(case_specs),
            "policy_count": len(policy_specs),
            "pass_count": len(PASS_PLAN),
            "total_policy_units": total_policy_units,
            "output_dir": _relative_path(output_dir),
        },
    )
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} "
        f"output_dir={_relative_path(output_dir)} "
        f"cases={len(case_specs)} "
        f"policies={len(policy_specs)} "
        f"passes={len(PASS_PLAN)} "
        f"units={total_policy_units} "
        f"cap={_format_duration(MAX_WALLCLOCK_SECONDS)}"
    )

    try:
        for pass_index, science_thread in PASS_PLAN:
            _emit_event(
                output_dir,
                {
                    "event": "pass_started",
                    "pass_index": int(pass_index),
                    "science_thread": str(science_thread),
                    "status": status,
                    "completed_policy_units": completed_policy_units,
                    "total_policy_units": total_policy_units,
                },
            )
            _print_progress(
                "pass_started "
                f"pass={pass_index}/{len(PASS_PLAN)} "
                f"thread={science_thread} "
                f"elapsed={_format_duration(monotonic() - started_at_monotonic)}"
            )

            pass_dir = cases_dir / f"pass_{pass_index:02d}__{science_thread}"
            pass_dir.mkdir(parents=True, exist_ok=True)

            for case_index, case_spec in enumerate(case_specs, start=1):
                bundle_relpath = _safe_str(case_spec.get("bundle_relpath"))
                source_artifact_relpath = _safe_str(case_spec.get("source_artifact_relpath"))
                fixture_seed = _safe_int(case_spec.get("fixture_seed"))
                search_seed = _safe_int(case_spec.get("search_seed"))
                bundle_path = REPO_ROOT / bundle_relpath

                case_dir = pass_dir / f"fixture_{fixture_seed}__search{search_seed}"
                case_dir.mkdir(parents=True, exist_ok=False)

                _emit_event(
                    output_dir,
                    {
                        "event": "case_started",
                        "pass_index": int(pass_index),
                        "science_thread": str(science_thread),
                        "case_index": int(case_index),
                        "case_count": int(len(case_specs)),
                        "fixture_seed": int(fixture_seed),
                        "search_seed": int(search_seed),
                        "status": status,
                    },
                )
                _print_progress(
                    "case_started "
                    f"pass={pass_index}/{len(PASS_PLAN)} "
                    f"thread={science_thread} "
                    f"case={case_index}/{len(case_specs)} "
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
                        "pass_index": int(pass_index),
                        "science_thread": str(science_thread),
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
                            "pass_index": int(pass_index),
                            "science_thread": str(science_thread),
                            "case_index": int(case_index),
                            "policy_index": int(policy_index),
                            "fixture_seed": int(fixture_seed),
                            "search_seed": int(search_seed),
                            "policy_name": str(policy_name),
                            "completed_policy_units": int(completed_policy_units),
                            "total_policy_units": int(total_policy_units),
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
                    row.update(
                        {
                            "pass_index": int(pass_index),
                            "science_thread": str(science_thread),
                            "policy_index": int(policy_index),
                            "unit_index": int(completed_policy_units + 1),
                            "policy_runtime_seconds": float(
                                monotonic() - policy_started_at
                            ),
                        }
                    )
                    rows.append(row)

                    policy_stub = f"{policy_index:02d}__{policy_name}"
                    _write_json(
                        case_dir
                        / f"{policy_stub}__candidate_saved_surface_summary.json",
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
                            "pass_index": int(pass_index),
                            "science_thread": str(science_thread),
                            "case_index": int(case_index),
                            "policy_index": int(policy_index),
                            "fixture_seed": int(fixture_seed),
                            "search_seed": int(search_seed),
                            "policy_name": str(policy_name),
                            "completed_policy_units": int(completed_policy_units),
                            "total_policy_units": int(total_policy_units),
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
                            "policy_runtime_seconds": float(
                                monotonic() - policy_started_at
                            ),
                            "status": status,
                        },
                    )
                    _print_progress(
                        "policy_finished "
                        f"unit={completed_policy_units}/{total_policy_units} "
                        f"pass={pass_index}/{len(PASS_PLAN)} "
                        f"thread={science_thread} "
                        f"case={case_index}/{len(case_specs)} "
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
                        case_count=len(case_specs),
                        policy_count=len(policy_specs),
                        total_policy_units=total_policy_units,
                        completed_policy_units=completed_policy_units,
                        status=status,
                        stop_reason=stop_reason,
                        config=config,
                    )
                    _check_cap(started_at_monotonic=started_at_monotonic)

                _emit_event(
                    output_dir,
                    {
                        "event": "case_finished",
                        "pass_index": int(pass_index),
                        "science_thread": str(science_thread),
                        "case_index": int(case_index),
                        "case_count": int(len(case_specs)),
                        "fixture_seed": int(fixture_seed),
                        "search_seed": int(search_seed),
                        "completed_policy_units": int(completed_policy_units),
                        "total_policy_units": int(total_policy_units),
                        "status": status,
                    },
                )

            _emit_event(
                output_dir,
                {
                    "event": "pass_finished",
                    "pass_index": int(pass_index),
                    "science_thread": str(science_thread),
                    "completed_policy_units": int(completed_policy_units),
                    "total_policy_units": int(total_policy_units),
                    "status": status,
                },
            )

        status = "completed"
        stop_reason = "completed_all_planned_policy_units"

    except HarvestStop as exc:
        status = "capped"
        stop_reason = str(exc)
        _emit_event(
            output_dir,
            {
                "event": "run_capped",
                "status": status,
                "stop_reason": stop_reason,
                "completed_policy_units": int(completed_policy_units),
                "total_policy_units": int(total_policy_units),
            },
        )

    except Exception as exc:
        status = "failed"
        stop_reason = f"{type(exc).__name__}: {exc}"
        _emit_event(
            output_dir,
            {
                "event": "run_failed",
                "status": status,
                "stop_reason": stop_reason,
                "completed_policy_units": int(completed_policy_units),
                "total_policy_units": int(total_policy_units),
            },
        )
        final_state = _write_snapshot(
            output_dir=output_dir,
            rows=rows,
            started_at_utc=started_at_utc,
            started_at_monotonic=started_at_monotonic,
            case_count=len(case_specs),
            policy_count=len(policy_specs),
            total_policy_units=total_policy_units,
            completed_policy_units=completed_policy_units,
            status=status,
            stop_reason=stop_reason,
            config=config,
        )
        raise RuntimeError(json.dumps(_json_safe(final_state), sort_keys=True)) from exc

    final_state = _write_snapshot(
        output_dir=output_dir,
        rows=rows,
        started_at_utc=started_at_utc,
        started_at_monotonic=started_at_monotonic,
        case_count=len(case_specs),
        policy_count=len(policy_specs),
        total_policy_units=total_policy_units,
        completed_policy_units=completed_policy_units,
        status=status,
        stop_reason=stop_reason,
        config=config,
    )

    _emit_event(
        output_dir,
        {
            "event": "run_finished",
            "status": status,
            "recommendation": _safe_str(
                final_state.get("recommendation", {}).get("recommendation")
            ),
            "completed_policy_units": int(completed_policy_units),
            "total_policy_units": int(total_policy_units),
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
    print(json.dumps(_json_safe(run_harvest()), sort_keys=True))


if __name__ == "__main__":
    main()