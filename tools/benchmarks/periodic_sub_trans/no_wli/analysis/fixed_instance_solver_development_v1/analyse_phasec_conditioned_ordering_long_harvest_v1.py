from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
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
        "analyse_phasec_conditioned_ordering_long_harvest_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


RUN_LABEL = "phasec_conditioned_ordering_long_harvest_analysis_v1"
SOURCE_RUN_SUFFIX = "__phasec_conditioned_ordering_long_harvest_v1"

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

# Leave blank to analyse the latest matching long-harvest bundle.
# To pin a specific run, set this to a repo-relative path, for example:
# "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T174808Z__phasec_conditioned_ordering_long_harvest_v1"
SOURCE_BUNDLE_DIR_REL = ""

EXPECTED_CASES: tuple[tuple[int, int], ...] = (
    (1111, 7004),
    (611, 7003),
    (1511, 7005),
    (1511, 7003),
)

EXPECTED_POLICY_NAMES: tuple[str, ...] = (
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

REQUIRED_ROW_COLUMNS: tuple[str, ...] = (
    "policy_name",
    "policy_group",
    "policy_family",
    "requested_width",
    "effective_applied_width",
    "fixture_seed",
    "search_seed",
    "control_best_match_ratio",
    "candidate_best_match_ratio",
    "candidate_minus_control_best_match_ratio",
    "control_fidelity_quality",
    "usable_decision_gate",
    "candidate_effect",
    "decision_gate_read",
    "selected_surface_changed",
    "selected_surface_membership_changed",
    "selected_surface_order_changed",
    "selected_surface_change_class",
    "winner_identity_changed",
    "winner_source_changed",
    "winner_lane_changed",
    "flat_delta_case_class",
)

EXPECTED_SOURCE_FILES: tuple[str, ...] = (
    "matrix_run_state.json",
    "matrix_run_events.jsonl",
    "run_config.json",
    "phasec_conditioned_ordering_long_harvest_case_rows.csv",
    "phasec_conditioned_ordering_long_harvest_case_rows.jsonl",
    "phasec_conditioned_ordering_long_harvest_summary.json",
    "phasec_conditioned_ordering_long_harvest_recommendation.json",
    "phasec_conditioned_ordering_long_harvest_readout.md",
)

EPS = 1.0e-12


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


def _safe_str(value: Any) -> str:
    return str(value or "")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value == "":
            return int(default)
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        if value == "":
            return float(default)
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    return result


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


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        rows.append(dict(json.loads(stripped)))
    return rows


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload: dict[str, Any] = {}
            for key in fieldnames:
                value = row.get(key, "")
                if isinstance(value, float) and not math.isfinite(value):
                    payload[key] = ""
                elif isinstance(value, (dict, list)):
                    payload[key] = json.dumps(_json_safe(value), sort_keys=True)
                else:
                    payload[key] = value
            writer.writerow(payload)


def _emit_event(output_dir: Path, event: Mapping[str, Any]) -> None:
    path = output_dir / "matrix_run_events.jsonl"
    payload = {"timestamp_utc": _utc_now_iso(), **dict(event)}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_json_safe(payload), sort_keys=True))
        handle.write("\n")


def _find_latest_source_bundle() -> Path:
    candidates = [
        item
        for item in OUTPUT_BASE_DIR.iterdir()
        if item.is_dir()
        and item.name.endswith(SOURCE_RUN_SUFFIX)
        and not item.name.endswith("__" + RUN_LABEL)
    ]
    if not candidates:
        raise FileNotFoundError(
            "No long-harvest source bundle found under "
            f"{_relative_path(OUTPUT_BASE_DIR)}"
        )
    return max(candidates, key=lambda item: item.name)


def _resolve_source_bundle() -> Path:
    if SOURCE_BUNDLE_DIR_REL.strip():
        source = REPO_ROOT / SOURCE_BUNDLE_DIR_REL.strip()
    else:
        source = _find_latest_source_bundle()
    if not source.exists():
        raise FileNotFoundError(f"Source bundle does not exist: {_relative_path(source)}")
    return source


def _case_id(fixture_seed: int, search_seed: int) -> str:
    return f"{fixture_seed}/search{search_seed}"


def _row_case_id(row: Mapping[str, Any]) -> str:
    return _case_id(_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed")))


def _read_source_rows(source_dir: Path) -> list[dict[str, Any]]:
    csv_rows = _read_csv(
        source_dir / "phasec_conditioned_ordering_long_harvest_case_rows.csv"
    )
    if csv_rows:
        return csv_rows
    return _read_jsonl(
        source_dir / "phasec_conditioned_ordering_long_harvest_case_rows.jsonl"
    )


def _normalise_row(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    fixture_seed = _safe_int(payload.get("fixture_seed"))
    search_seed = _safe_int(payload.get("search_seed"))
    policy_name = _safe_str(payload.get("policy_name"))
    policy_group = _safe_str(payload.get("policy_group"))
    policy_family = _safe_str(payload.get("policy_family"))
    requested_width = _safe_str(payload.get("requested_width"))

    control_best = _safe_float(payload.get("control_best_match_ratio"))
    candidate_best = _safe_float(payload.get("candidate_best_match_ratio"))
    delta = _safe_float(payload.get("candidate_minus_control_best_match_ratio"))
    vs_best_reorder = _safe_float(payload.get("vs_best_reorder_delta"))
    usable = _safe_int(payload.get("usable_decision_gate"))
    selected_changed = _safe_int(payload.get("selected_surface_changed"))
    winner_changed = _safe_int(payload.get("winner_identity_changed"))
    winner_source_changed = _safe_int(payload.get("winner_source_changed"))
    winner_lane_changed = _safe_int(payload.get("winner_lane_changed"))
    effective_width = _safe_int(payload.get("effective_applied_width"))

    if math.isfinite(delta):
        if delta > EPS:
            signed_delta_class = "positive"
        elif delta < -EPS:
            signed_delta_class = "negative"
        else:
            signed_delta_class = "neutral"
    else:
        signed_delta_class = "unknown"

    route_signal = int(
        selected_changed == 1
        or winner_changed == 1
        or winner_source_changed == 1
        or winner_lane_changed == 1
        or effective_width > 0
    )

    payload.update(
        {
            "case_id": _case_id(fixture_seed, search_seed),
            "fixture_seed": fixture_seed,
            "search_seed": search_seed,
            "policy_name": policy_name,
            "policy_group": policy_group,
            "policy_family": policy_family,
            "requested_width": requested_width,
            "effective_applied_width": effective_width,
            "control_best_match_ratio": control_best,
            "candidate_best_match_ratio": candidate_best,
            "candidate_minus_control_best_match_ratio": delta,
            "vs_best_reorder_delta": vs_best_reorder,
            "usable_decision_gate": usable,
            "selected_surface_changed": selected_changed,
            "winner_identity_changed": winner_changed,
            "winner_source_changed": winner_source_changed,
            "winner_lane_changed": winner_lane_changed,
            "signed_delta_class": signed_delta_class,
            "route_signal_present": route_signal,
        }
    )
    return payload


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


def _best_row(
    rows: Sequence[Mapping[str, Any]],
    *,
    prefer_usable: bool,
    exclude_policy_groups: set[str] | None = None,
) -> dict[str, Any]:
    exclude_policy_groups = set(exclude_policy_groups or set())
    candidates = [
        dict(row)
        for row in rows
        if _safe_str(row.get("policy_group")) not in exclude_policy_groups
    ]
    if prefer_usable:
        usable = [row for row in candidates if _safe_int(row.get("usable_decision_gate")) == 1]
        if usable:
            candidates = usable
    if not candidates:
        return {}
    return dict(
        max(
            candidates,
            key=lambda row: (
                _safe_float(row.get("candidate_best_match_ratio"), -1.0e9),
                _safe_float(row.get("candidate_minus_control_best_match_ratio"), -1.0e9),
                _safe_int(row.get("selected_surface_changed")),
                _safe_int(row.get("winner_identity_changed")),
                _safe_str(row.get("policy_name")),
            ),
        )
    )


def _group_rows(
    rows: Sequence[Mapping[str, Any]],
    key_fields: Sequence[str],
) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(field) for field in key_fields)
        grouped[key].append(dict(row))
    return dict(grouped)


def _build_integrity(
    *,
    source_dir: Path,
    rows: Sequence[Mapping[str, Any]],
    state: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    present_files = {
        relpath: int((source_dir / relpath).exists())
        for relpath in EXPECTED_SOURCE_FILES
    }
    missing_files = [relpath for relpath, present in present_files.items() if present == 0]

    observed_columns: set[str] = set()
    for row in rows:
        observed_columns.update(row.keys())
    missing_columns = [
        column for column in REQUIRED_ROW_COLUMNS if column not in observed_columns
    ]

    completed_policy_units = _safe_int(state.get("completed_policy_units"))
    total_policy_units = _safe_int(state.get("total_policy_units"))
    source_bundle_complete = _safe_int(state.get("bundle_complete"))
    source_status = _safe_str(state.get("status"))
    row_count = len(rows)
    final_events = [
        dict(event)
        for event in events
        if _safe_str(event.get("event")) == "run_finished"
    ]
    final_event = final_events[-1] if final_events else {}

    expected_case_ids = {
        _case_id(fixture, search)
        for fixture, search in EXPECTED_CASES
    }
    observed_case_ids = {_row_case_id(row) for row in rows}
    missing_case_ids = sorted(expected_case_ids - observed_case_ids)

    expected_policy_names = set(EXPECTED_POLICY_NAMES)
    observed_policy_names = {_safe_str(row.get("policy_name")) for row in rows}
    missing_policy_names = sorted(expected_policy_names - observed_policy_names)

    if source_bundle_complete == 1:
        row_count_matches_state = int(row_count == completed_policy_units)
    else:
        row_count_matches_state = int(row_count <= completed_policy_units or row_count == completed_policy_units)

    critical_missing = bool(
        "phasec_conditioned_ordering_long_harvest_case_rows.csv" in missing_files
        and "phasec_conditioned_ordering_long_harvest_case_rows.jsonl" in missing_files
    )

    return {
        "source_bundle_dir": _relative_path(source_dir),
        "source_status": source_status,
        "source_bundle_complete": int(source_bundle_complete),
        "source_completed_policy_units": int(completed_policy_units),
        "source_total_policy_units": int(total_policy_units),
        "source_row_count": int(row_count),
        "source_final_event_present": int(bool(final_event)),
        "source_final_event_status": _safe_str(final_event.get("status")),
        "source_final_event_recommendation": _safe_str(final_event.get("recommendation")),
        "source_files_present": present_files,
        "missing_source_files": missing_files,
        "missing_required_columns": missing_columns,
        "row_count_matches_state": int(row_count_matches_state),
        "observed_case_ids": sorted(observed_case_ids),
        "missing_expected_case_ids": missing_case_ids,
        "observed_policy_names": sorted(observed_policy_names),
        "missing_expected_policy_names": missing_policy_names,
        "critical_missing_input": int(critical_missing),
        "analysis_input_usable": int(
            not critical_missing
            and not missing_columns
            and row_count > 0
        ),
    }


def _build_case_best_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for (case_id,), case_rows in sorted(_group_rows(rows, ["case_id"]).items()):
        all_best = _best_row(case_rows, prefer_usable=True)
        candidate_best = _best_row(
            case_rows,
            prefer_usable=True,
            exclude_policy_groups={"control", "reorder_control"},
        )
        reorder_best = _best_row(
            [
                row
                for row in case_rows
                if _safe_str(row.get("policy_group")) == "reorder_control"
            ],
            prefer_usable=True,
        )
        control_best = _best_row(
            [
                row
                for row in case_rows
                if _safe_str(row.get("policy_group")) == "control"
            ],
            prefer_usable=False,
        )

        if candidate_best and reorder_best:
            candidate_vs_reorder = _safe_float(
                candidate_best.get("candidate_best_match_ratio")
            ) - _safe_float(reorder_best.get("candidate_best_match_ratio"))
        else:
            candidate_vs_reorder = float("nan")

        if candidate_best:
            candidate_read = _safe_str(candidate_best.get("decision_gate_read"))
            if not candidate_read:
                candidate_read = _safe_str(candidate_best.get("signed_delta_class"))
        else:
            candidate_read = ""

        route_signal_count = sum(_safe_int(row.get("route_signal_present")) for row in case_rows)
        winner_change_count = sum(_safe_int(row.get("winner_identity_changed")) for row in case_rows)
        surface_change_count = sum(_safe_int(row.get("selected_surface_changed")) for row in case_rows)

        out.append(
            {
                "case_id": case_id,
                "fixture_seed": _safe_int(all_best.get("fixture_seed")),
                "search_seed": _safe_int(all_best.get("search_seed")),
                "row_count": int(len(case_rows)),
                "usable_row_count": int(
                    sum(_safe_int(row.get("usable_decision_gate")) for row in case_rows)
                ),
                "best_overall_policy_name": _safe_str(all_best.get("policy_name")),
                "best_overall_policy_family": _safe_str(all_best.get("policy_family")),
                "best_overall_match_ratio": _safe_float(
                    all_best.get("candidate_best_match_ratio")
                ),
                "best_candidate_policy_name": _safe_str(candidate_best.get("policy_name")),
                "best_candidate_policy_family": _safe_str(
                    candidate_best.get("policy_family")
                ),
                "best_candidate_requested_width": _safe_str(
                    candidate_best.get("requested_width")
                ),
                "best_candidate_match_ratio": _safe_float(
                    candidate_best.get("candidate_best_match_ratio")
                ),
                "best_candidate_minus_control": _safe_float(
                    candidate_best.get("candidate_minus_control_best_match_ratio")
                ),
                "best_candidate_vs_reorder": float(candidate_vs_reorder),
                "best_candidate_read": candidate_read,
                "best_reorder_policy_name": _safe_str(reorder_best.get("policy_name")),
                "best_reorder_match_ratio": _safe_float(
                    reorder_best.get("candidate_best_match_ratio")
                ),
                "control_policy_name": _safe_str(control_best.get("policy_name")),
                "control_match_ratio": _safe_float(
                    control_best.get("candidate_best_match_ratio")
                ),
                "surface_change_count": int(surface_change_count),
                "winner_identity_change_count": int(winner_change_count),
                "route_signal_count": int(route_signal_count),
                "case_interpretation": _case_interpretation(
                    candidate_best=candidate_best,
                    candidate_vs_reorder=candidate_vs_reorder,
                    surface_change_count=surface_change_count,
                    winner_change_count=winner_change_count,
                ),
            }
        )
    return out


def _case_interpretation(
    *,
    candidate_best: Mapping[str, Any],
    candidate_vs_reorder: float,
    surface_change_count: int,
    winner_change_count: int,
) -> str:
    if not candidate_best:
        return "no_candidate_policy_rows"
    delta = _safe_float(candidate_best.get("best_candidate_minus_control"))
    if not math.isfinite(delta):
        delta = _safe_float(candidate_best.get("candidate_minus_control_best_match_ratio"))

    if math.isfinite(candidate_vs_reorder) and candidate_vs_reorder > EPS:
        if winner_change_count > 0:
            return "candidate_policy_beats_reorder_with_winner_change"
        if surface_change_count > 0:
            return "candidate_policy_beats_reorder_with_surface_change"
        return "candidate_policy_beats_reorder_without_route_signal"

    if math.isfinite(candidate_vs_reorder) and abs(candidate_vs_reorder) <= EPS:
        if surface_change_count > 0 or winner_change_count > 0:
            return "candidate_policy_ties_reorder_with_route_signal"
        return "candidate_policy_ties_reorder_no_route_signal"

    if math.isfinite(candidate_vs_reorder) and candidate_vs_reorder < -EPS:
        return "candidate_policy_worse_than_reorder"

    if surface_change_count > 0 or winner_change_count > 0:
        return "route_signal_present_but_reorder_comparison_missing"
    return "no_clear_conditioned_signal"


def _build_signal_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    group_field: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for (group_value,), group_rows in sorted(_group_rows(rows, [group_field]).items()):
        usable_rows = [
            dict(row)
            for row in group_rows
            if _safe_int(row.get("usable_decision_gate")) == 1
        ]
        positive_rows = [
            row for row in usable_rows
            if _safe_str(row.get("signed_delta_class")) == "positive"
        ]
        neutral_rows = [
            row for row in usable_rows
            if _safe_str(row.get("signed_delta_class")) == "neutral"
        ]
        negative_rows = [
            row for row in usable_rows
            if _safe_str(row.get("signed_delta_class")) == "negative"
        ]
        vs_reorder_values = [
            _safe_float(row.get("vs_best_reorder_delta"))
            for row in usable_rows
        ]
        positive_vs_reorder_rows = [
            row for row in usable_rows
            if _safe_float(row.get("vs_best_reorder_delta")) > EPS
        ]
        negative_vs_reorder_rows = [
            row for row in usable_rows
            if _safe_float(row.get("vs_best_reorder_delta")) < -EPS
        ]
        best = _best_row(usable_rows or group_rows, prefer_usable=False)

        out.append(
            {
                group_field: group_value,
                "row_count": int(len(group_rows)),
                "usable_row_count": int(len(usable_rows)),
                "case_count": int(len({_row_case_id(row) for row in group_rows})),
                "positive_count": int(len(positive_rows)),
                "neutral_count": int(len(neutral_rows)),
                "negative_count": int(len(negative_rows)),
                "positive_vs_reorder_count": int(len(positive_vs_reorder_rows)),
                "negative_vs_reorder_count": int(len(negative_vs_reorder_rows)),
                "mean_delta": _mean(
                    [
                        _safe_float(row.get("candidate_minus_control_best_match_ratio"))
                        for row in usable_rows
                    ]
                ),
                "max_delta": _max(
                    [
                        _safe_float(row.get("candidate_minus_control_best_match_ratio"))
                        for row in usable_rows
                    ]
                ),
                "min_delta": _min(
                    [
                        _safe_float(row.get("candidate_minus_control_best_match_ratio"))
                        for row in usable_rows
                    ]
                ),
                "mean_vs_best_reorder": _mean(vs_reorder_values),
                "max_vs_best_reorder": _max(vs_reorder_values),
                "selected_surface_changed_count": int(
                    sum(_safe_int(row.get("selected_surface_changed")) for row in group_rows)
                ),
                "winner_identity_changed_count": int(
                    sum(_safe_int(row.get("winner_identity_changed")) for row in group_rows)
                ),
                "winner_source_changed_count": int(
                    sum(_safe_int(row.get("winner_source_changed")) for row in group_rows)
                ),
                "route_signal_count": int(
                    sum(_safe_int(row.get("route_signal_present")) for row in group_rows)
                ),
                "mean_effective_applied_width": _mean(
                    [
                        _safe_float(row.get("effective_applied_width"))
                        for row in group_rows
                    ]
                ),
                "best_case_id": _row_case_id(best),
                "best_policy_name": _safe_str(best.get("policy_name")),
                "best_policy_family": _safe_str(best.get("policy_family")),
                "best_requested_width": _safe_str(best.get("requested_width")),
                "best_candidate_match_ratio": _safe_float(
                    best.get("candidate_best_match_ratio")
                ),
                "best_delta": _safe_float(
                    best.get("candidate_minus_control_best_match_ratio")
                ),
                "signal_read": _signal_read(
                    usable_count=len(usable_rows),
                    positive=len(positive_rows),
                    neutral=len(neutral_rows),
                    negative=len(negative_rows),
                    positive_vs_reorder=len(positive_vs_reorder_rows),
                    negative_vs_reorder=len(negative_vs_reorder_rows),
                    mean_vs_reorder=_mean(vs_reorder_values),
                    route_signal=sum(
                        _safe_int(row.get("route_signal_present")) for row in group_rows
                    ),
                ),
            }
        )
    return out


def _signal_read(
    *,
    usable_count: int,
    positive: int,
    neutral: int,
    negative: int,
    positive_vs_reorder: int,
    negative_vs_reorder: int,
    mean_vs_reorder: float,
    route_signal: int,
) -> str:
    if usable_count == 0:
        return "no_usable_decision_rows"
    if positive_vs_reorder > negative_vs_reorder and mean_vs_reorder > EPS:
        if route_signal > 0:
            return "conditioned_candidate_signal"
        return "score_signal_without_route_explanation"
    if positive > negative and route_signal > 0:
        return "route_signal_with_positive_delta"
    if positive == 0 and negative == 0:
        if route_signal > 0:
            return "route_signal_flat_score"
        return "flat_no_route_signal"
    if negative > positive:
        return "net_negative"
    return "mixed_or_weak"


def _build_condition_signal_rows(
    rows: Sequence[Mapping[str, Any]],
    case_best_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    by_case = {str(row.get("case_id")): dict(row) for row in case_best_rows}

    for (case_id, policy_family), group_rows in sorted(
        _group_rows(rows, ["case_id", "policy_family"]).items()
    ):
        if policy_family in {"control", "reorder_control"}:
            continue
        best = _best_row(group_rows, prefer_usable=True)
        case_best = by_case.get(str(case_id), {})
        vs_case_best = _safe_float(best.get("candidate_best_match_ratio")) - _safe_float(
            case_best.get("best_candidate_match_ratio")
        )
        out.append(
            {
                "case_id": case_id,
                "fixture_seed": _safe_int(best.get("fixture_seed")),
                "search_seed": _safe_int(best.get("search_seed")),
                "policy_family": policy_family,
                "best_policy_name": _safe_str(best.get("policy_name")),
                "best_requested_width": _safe_str(best.get("requested_width")),
                "best_candidate_match_ratio": _safe_float(
                    best.get("candidate_best_match_ratio")
                ),
                "best_candidate_minus_control": _safe_float(
                    best.get("candidate_minus_control_best_match_ratio")
                ),
                "best_vs_best_reorder": _safe_float(best.get("vs_best_reorder_delta")),
                "vs_case_best_candidate_policy": float(vs_case_best),
                "selected_surface_changed": _safe_int(
                    best.get("selected_surface_changed")
                ),
                "winner_identity_changed": _safe_int(
                    best.get("winner_identity_changed")
                ),
                "winner_source_changed": _safe_int(best.get("winner_source_changed")),
                "effective_applied_width": _safe_int(
                    best.get("effective_applied_width")
                ),
                "condition_read": _condition_read(best),
            }
        )
    return out


def _condition_read(row: Mapping[str, Any]) -> str:
    vs_reorder = _safe_float(row.get("vs_best_reorder_delta"))
    delta = _safe_float(row.get("candidate_minus_control_best_match_ratio"))
    surface = _safe_int(row.get("selected_surface_changed"))
    winner = _safe_int(row.get("winner_identity_changed"))
    source = _safe_int(row.get("winner_source_changed"))
    width = _safe_int(row.get("effective_applied_width"))

    if math.isfinite(vs_reorder) and vs_reorder > EPS:
        if winner:
            return "beats_reorder_with_winner_change"
        if source:
            return "beats_reorder_with_source_change"
        if surface:
            return "beats_reorder_with_surface_change"
        return "beats_reorder_without_visible_route_change"

    if math.isfinite(delta) and delta > EPS:
        if winner or source or surface or width > 0:
            return "positive_vs_control_with_route_signal"
        return "positive_vs_control_no_visible_route_signal"

    if math.isfinite(delta) and abs(delta) <= EPS:
        if winner or source or surface or width > 0:
            return "flat_score_with_route_signal"
        return "flat_score_no_visible_route_signal"

    if math.isfinite(delta) and delta < -EPS:
        return "negative_score"

    return "unclassified"


def _build_recommendation(
    *,
    integrity: Mapping[str, Any],
    case_best_rows: Sequence[Mapping[str, Any]],
    family_signal_rows: Sequence[Mapping[str, Any]],
    condition_signal_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if _safe_int(integrity.get("analysis_input_usable")) != 1:
        return {
            "recommendation": "hold",
            "next_branch_label": "",
            "reason": (
                "Input bundle is not usable for analysis because required source "
                "files or required row columns are missing."
            ),
        }

    source_complete = _safe_int(integrity.get("source_bundle_complete"))
    completed_units = _safe_int(integrity.get("source_completed_policy_units"))
    total_units = _safe_int(integrity.get("source_total_policy_units"))

    candidate_signals = [
        dict(row)
        for row in family_signal_rows
        if _safe_str(row.get("policy_family")) not in {"control", "reorder_control"}
        and _safe_str(row.get("signal_read"))
        in {
            "conditioned_candidate_signal",
            "route_signal_with_positive_delta",
        }
    ]

    condition_hits = [
        dict(row)
        for row in condition_signal_rows
        if _safe_str(row.get("condition_read"))
        in {
            "beats_reorder_with_winner_change",
            "beats_reorder_with_source_change",
            "beats_reorder_with_surface_change",
            "positive_vs_control_with_route_signal",
        }
    ]

    complete_enough_cases = len(case_best_rows) >= 3
    if source_complete == 1 and complete_enough_cases and candidate_signals and condition_hits:
        best_family = max(
            candidate_signals,
            key=lambda row: (
                _safe_float(row.get("mean_vs_best_reorder"), -1.0e9),
                _safe_int(row.get("positive_vs_reorder_count"))
                - _safe_int(row.get("negative_vs_reorder_count")),
                _safe_int(row.get("positive_count")) - _safe_int(row.get("negative_count")),
            ),
        )
        return {
            "recommendation": "refine",
            "next_branch_label": "phasec_conditioned_ordering_rule_design_v1",
            "reason": (
                "Completed harvest contains route/surface-linked candidate policy "
                "signals. Review should design a conditioned Phase-C ordering rule, "
                "not promote a global policy."
            ),
            "best_signal_policy_family": _safe_str(best_family.get("policy_family")),
            "best_signal_policy_name": _safe_str(best_family.get("best_policy_name")),
        }

    if source_complete != 1:
        return {
            "recommendation": "hold",
            "next_branch_label": "",
            "reason": (
                "Source harvest is partial. Completed rows are saved and analysable, "
                f"but only {completed_units}/{total_units} policy units are complete."
            ),
        }

    if complete_enough_cases and (candidate_signals or condition_hits):
        return {
            "recommendation": "review",
            "next_branch_label": "manual_phasec_conditioned_ordering_review",
            "reason": (
                "Completed harvest has some route/surface signal, but it is not "
                "strong enough for an automatic refine recommendation."
            ),
        }

    return {
        "recommendation": "close_or_hold",
        "next_branch_label": "",
        "reason": (
            "Completed harvest does not show a clear route/surface-conditioned "
            "policy signal."
        ),
    }


def _build_readout(
    *,
    output_dir: Path,
    source_dir: Path,
    integrity: Mapping[str, Any],
    case_best_rows: Sequence[Mapping[str, Any]],
    policy_signal_rows: Sequence[Mapping[str, Any]],
    family_signal_rows: Sequence[Mapping[str, Any]],
    condition_signal_rows: Sequence[Mapping[str, Any]],
    recommendation: Mapping[str, Any],
) -> str:
    lines: list[str] = [
        "# Phase-C Conditioned Ordering Long Harvest Analysis v1",
        "",
        "Source:",
        f"- source bundle: `{_relative_path(source_dir)}`",
        f"- analysis bundle: `{_relative_path(output_dir)}`",
        "",
        "Integrity:",
        f"- source status: `{_safe_str(integrity.get('source_status'))}`",
        f"- source bundle complete: `{_safe_int(integrity.get('source_bundle_complete'))}`",
        f"- completed policy units: `{_safe_int(integrity.get('source_completed_policy_units'))}` / `{_safe_int(integrity.get('source_total_policy_units'))}`",
        f"- source row count: `{_safe_int(integrity.get('source_row_count'))}`",
        f"- analysis input usable: `{_safe_int(integrity.get('analysis_input_usable'))}`",
        f"- missing source files: `{', '.join(integrity.get('missing_source_files', []) or []) or 'none'}`",
        f"- missing required columns: `{', '.join(integrity.get('missing_required_columns', []) or []) or 'none'}`",
        "",
        "Recommendation:",
        f"- recommendation: `{_safe_str(recommendation.get('recommendation'))}`",
        f"- next branch: `{_safe_str(recommendation.get('next_branch_label'))}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Case best rows:",
        "",
        "| case | best candidate policy | family | width | candidate | delta | vs reorder | route read |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for row in case_best_rows:
        lines.append(
            f"| `{_safe_str(row.get('case_id'))}` | "
            f"`{_safe_str(row.get('best_candidate_policy_name'))}` | "
            f"`{_safe_str(row.get('best_candidate_policy_family'))}` | "
            f"`{_safe_str(row.get('best_candidate_requested_width')) or '-'} ` | "
            f"`{_safe_float(row.get('best_candidate_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('best_candidate_minus_control')):.3f}` | "
            f"`{_safe_float(row.get('best_candidate_vs_reorder')):.3f}` | "
            f"`{_safe_str(row.get('case_interpretation'))}` |"
        )

    lines.extend(
        [
            "",
            "Family signal rows:",
            "",
            "| family | rows | usable | positive | neutral | negative | mean delta | mean vs reorder | route signals | read |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )

    for row in sorted(
        family_signal_rows,
        key=lambda item: (
            -_safe_float(item.get("mean_vs_best_reorder"), -1.0e9),
            _safe_str(item.get("policy_family")),
        ),
    ):
        lines.append(
            f"| `{_safe_str(row.get('policy_family'))}` | "
            f"{_safe_int(row.get('row_count'))} | "
            f"{_safe_int(row.get('usable_row_count'))} | "
            f"{_safe_int(row.get('positive_count'))} | "
            f"{_safe_int(row.get('neutral_count'))} | "
            f"{_safe_int(row.get('negative_count'))} | "
            f"{_safe_float(row.get('mean_delta')):.3f} | "
            f"{_safe_float(row.get('mean_vs_best_reorder')):.3f} | "
            f"{_safe_int(row.get('route_signal_count'))} | "
            f"`{_safe_str(row.get('signal_read'))}` |"
        )

    top_conditions = sorted(
        condition_signal_rows,
        key=lambda item: (
            -_safe_float(item.get("best_vs_best_reorder"), -1.0e9),
            -_safe_float(item.get("best_candidate_minus_control"), -1.0e9),
            _safe_str(item.get("case_id")),
            _safe_str(item.get("policy_family")),
        ),
    )[:20]

    lines.extend(
        [
            "",
            "Top condition signals:",
            "",
            "| case | family | policy | width | delta | vs reorder | changed | winner changed | read |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )

    for row in top_conditions:
        lines.append(
            f"| `{_safe_str(row.get('case_id'))}` | "
            f"`{_safe_str(row.get('policy_family'))}` | "
            f"`{_safe_str(row.get('best_policy_name'))}` | "
            f"`{_safe_str(row.get('best_requested_width')) or '-'} ` | "
            f"{_safe_float(row.get('best_candidate_minus_control')):.3f} | "
            f"{_safe_float(row.get('best_vs_best_reorder')):.3f} | "
            f"{_safe_int(row.get('selected_surface_changed'))} | "
            f"{_safe_int(row.get('winner_identity_changed'))} | "
            f"`{_safe_str(row.get('condition_read'))}` |"
        )

    lines.extend(
        [
            "",
            "Interpretation guard:",
            "",
            "- A positive score alone is not enough to promote a policy.",
            "- The useful signal is a score movement tied to a route/surface change.",
            "- This analysis should suggest a conditioned follow-up, not a global policy.",
            "- If the source harvest is still partial, use this as a progress readout only.",
            "",
        ]
    )

    return "\n".join(lines)


def analyse() -> dict[str, Any]:
    source_dir = _resolve_source_bundle()
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    _emit_event(
        output_dir,
        {
            "event": "analysis_started",
            "run_label": RUN_LABEL,
            "source_bundle_dir": _relative_path(source_dir),
        },
    )

    state = _read_json_if_present(source_dir / "matrix_run_state.json")
    events = _read_jsonl(source_dir / "matrix_run_events.jsonl")
    source_summary = _read_json_if_present(
        source_dir / "phasec_conditioned_ordering_long_harvest_summary.json"
    )
    source_recommendation = _read_json_if_present(
        source_dir / "phasec_conditioned_ordering_long_harvest_recommendation.json"
    )

    raw_rows = _read_source_rows(source_dir)
    rows = [_normalise_row(row) for row in raw_rows]
    rows = sorted(
        rows,
        key=lambda row: (
            _safe_int(row.get("fixture_seed")),
            _safe_int(row.get("search_seed")),
            _safe_str(row.get("policy_family")),
            _safe_str(row.get("policy_name")),
            _safe_str(row.get("requested_width")),
        ),
    )

    integrity = _build_integrity(
        source_dir=source_dir,
        rows=rows,
        state=state,
        events=events,
    )
    case_best_rows = _build_case_best_rows(rows)
    policy_signal_rows = _build_signal_rows(rows, group_field="policy_name")
    family_signal_rows = _build_signal_rows(rows, group_field="policy_family")
    condition_signal_rows = _build_condition_signal_rows(rows, case_best_rows)
    recommendation = _build_recommendation(
        integrity=integrity,
        case_best_rows=case_best_rows,
        family_signal_rows=family_signal_rows,
        condition_signal_rows=condition_signal_rows,
    )

    summary = {
        "run_label": RUN_LABEL,
        "created_at_utc": _utc_now_iso(),
        "source_bundle_dir": _relative_path(source_dir),
        "output_dir": _relative_path(output_dir),
        "integrity": integrity,
        "source_recommendation": source_recommendation,
        "source_summary_status": {
            "source_summary_present": int(bool(source_summary)),
            "source_summary_keys": sorted(source_summary.keys()) if source_summary else [],
        },
        "case_best_rows": case_best_rows,
        "policy_signal_rows": policy_signal_rows,
        "family_signal_rows": family_signal_rows,
        "condition_signal_rows": condition_signal_rows,
        "recommendation": recommendation,
    }

    run_state = {
        "run_label": RUN_LABEL,
        "status": "completed",
        "created_at_utc": _utc_now_iso(),
        "source_bundle_dir": _relative_path(source_dir),
        "output_dir": _relative_path(output_dir),
        "row_count": int(len(rows)),
        "case_best_row_count": int(len(case_best_rows)),
        "policy_signal_row_count": int(len(policy_signal_rows)),
        "family_signal_row_count": int(len(family_signal_rows)),
        "condition_signal_row_count": int(len(condition_signal_rows)),
        "recommendation": recommendation,
        "integrity": integrity,
    }

    _write_json(
        output_dir / "run_config.json",
        {
            "run_label": RUN_LABEL,
            "source_bundle_dir_rel": SOURCE_BUNDLE_DIR_REL,
            "resolved_source_bundle_dir": _relative_path(source_dir),
            "expected_cases": [
                {"fixture_seed": fixture, "search_seed": search}
                for fixture, search in EXPECTED_CASES
            ],
            "expected_policy_names": list(EXPECTED_POLICY_NAMES),
            "required_row_columns": list(REQUIRED_ROW_COLUMNS),
            "expected_source_files": list(EXPECTED_SOURCE_FILES),
        },
    )
    _write_json(
        output_dir / "phasec_conditioned_ordering_long_harvest_analysis_integrity.json",
        integrity,
    )
    _write_csv(
        output_dir / "phasec_conditioned_ordering_long_harvest_analysis_case_rows.csv",
        rows,
    )
    _write_csv(
        output_dir / "phasec_conditioned_ordering_long_harvest_analysis_case_best_rows.csv",
        case_best_rows,
    )
    _write_csv(
        output_dir / "phasec_conditioned_ordering_long_harvest_analysis_policy_signal_rows.csv",
        policy_signal_rows,
    )
    _write_csv(
        output_dir / "phasec_conditioned_ordering_long_harvest_analysis_family_signal_rows.csv",
        family_signal_rows,
    )
    _write_csv(
        output_dir / "phasec_conditioned_ordering_long_harvest_analysis_condition_signal_rows.csv",
        condition_signal_rows,
    )
    _write_json(
        output_dir / "phasec_conditioned_ordering_long_harvest_analysis_summary.json",
        summary,
    )
    _write_json(
        output_dir / "phasec_conditioned_ordering_long_harvest_analysis_recommendation.json",
        recommendation,
    )
    readout = _build_readout(
        output_dir=output_dir,
        source_dir=source_dir,
        integrity=integrity,
        case_best_rows=case_best_rows,
        policy_signal_rows=policy_signal_rows,
        family_signal_rows=family_signal_rows,
        condition_signal_rows=condition_signal_rows,
        recommendation=recommendation,
    )
    (
        output_dir / "phasec_conditioned_ordering_long_harvest_analysis_readout.md"
    ).write_text(readout, encoding="utf-8")
    _write_json(output_dir / "matrix_run_state.json", run_state)
    _emit_event(
        output_dir,
        {
            "event": "analysis_finished",
            "status": "completed",
            "recommendation": _safe_str(recommendation.get("recommendation")),
            "row_count": int(len(rows)),
            "source_bundle_dir": _relative_path(source_dir),
            "output_dir": _relative_path(output_dir),
        },
    )

    print(
        json.dumps(
            {
                "status": "completed",
                "recommendation": _safe_str(recommendation.get("recommendation")),
                "source_bundle_dir": _relative_path(source_dir),
                "output_dir": _relative_path(output_dir),
                "row_count": int(len(rows)),
                "analysis_input_usable": _safe_int(
                    integrity.get("analysis_input_usable")
                ),
            },
            sort_keys=True,
        )
    )
    return run_state


def main() -> None:
    analyse()


if __name__ == "__main__":
    main()