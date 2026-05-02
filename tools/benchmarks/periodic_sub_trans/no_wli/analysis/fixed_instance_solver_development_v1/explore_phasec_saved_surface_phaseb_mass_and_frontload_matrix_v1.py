import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Callable, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "explore_phasec_saved_surface_phaseb_mass_and_frontload_matrix_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_candidate3_saved_surface_exact_matrix_v1 as matrix_mod,
    verify_candidate3_phasec_saved_surface_1511_7004 as saved_surface_mod,
    verify_candidate3_phasec_saved_surface_exact_1511_7004 as exact_mod,
)


RUN_LABEL = "phasec_saved_surface_phaseb_mass_and_frontload_matrix_v1"
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
SOURCE_MATRIX_SUMMARY_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260418T042939Z__candidate3_saved_surface_exact_matrix_v1/"
    "candidate3_saved_surface_exact_matrix_summary.json"
)
SOURCE_ORDER_POLICY_NAME = "source_order"
ANCHOR_SWAP_POLICY_NAME = "phaseb_topk_anchor_swap_v1"
FRONTLOAD_ALL_POLICY_NAME = "phaseb_topk_frontload_all_v1"
CONTROL_POLICY_GROUP = "control"
REORDER_CONTROL_POLICY_GROUP = "reorder_control"
FRONTLOAD_DEPTH_POLICY_GROUP = "frontload_depth"
PHASEB_TOPK_QUOTA_POLICY_GROUP = "phaseb_topk_quota"
PHASEB_TOPK_ONLY_REPLACEMENT_POLICY_GROUP = "phaseb_topk_only_replacement"
PROMOTE_MEAN_VS_REORDER_EPS = 0.003
WIDTH_VALUES = tuple(range(1, 9))


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _safe_str(value: Any) -> str:
    return str(value or "")


def _format_duration(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0.0:
        return "na"
    total_seconds = int(round(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _print_progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] {message}", flush=True)


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
        raise ValueError(f"Refusing to write empty CSV: {path}")
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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_case_specs() -> list[dict[str, Any]]:
    summary = _load_json(REPO_ROOT / SOURCE_MATRIX_SUMMARY_REL_PATH)
    case_specs: list[dict[str, Any]] = []
    for bundle_relpath in list(summary.get("source_bundle_relpaths", []) or []):
        bundle_path = REPO_ROOT / str(bundle_relpath)
        comparison_summary = _load_json(bundle_path / "comparison_summary.json")
        case_specs.append(
            {
                "fixture_seed": _safe_int(comparison_summary.get("fixture_seed")),
                "search_seed": _safe_int(comparison_summary.get("search_seed")),
                "bundle_relpath": str(bundle_relpath),
                "source_artifact_relpath": _safe_str(
                    comparison_summary.get("source_artifact_relpath")
                ),
            }
        )
    return sorted(
        case_specs,
        key=lambda row: (_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed"))),
    )


def _load_saved_candidate_pool_rows(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    diagnostics = dict(artifact.get("stage3_diagnostics", {}) or {})
    return [
        dict(row)
        for row in list(diagnostics.get("phaseC_candidate_pool_rows", []) or [])
        if isinstance(row, Mapping)
    ]


def _clone_source_order_candidate_summary(
    control_summary: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **dict(control_summary),
        "replay_label": SOURCE_ORDER_POLICY_NAME,
    }


def _build_source_order_comparison_summary(
    *,
    control_summary: Mapping[str, Any],
    anchor_swap_comparison_summary: Mapping[str, Any],
    source_artifact_relpath: str,
) -> dict[str, Any]:
    retained_stage3_match = _safe_float(
        anchor_swap_comparison_summary.get("retained_stage3_reference_match_ratio")
    )
    control_best_match = _safe_float(control_summary.get("best_match_ratio"))
    control_winner_lane = _safe_str(control_summary.get("winner_lane"))
    control_winner_source = _safe_str(control_summary.get("winner_source"))
    control_winner_source_rank = _safe_int(control_summary.get("winner_source_rank"))
    control_winner_candidate_hash = _safe_str(control_summary.get("winner_candidate_hash"))
    control_start_hashes = [
        _safe_str(row.get("candidate_hash"))
        for row in list(control_summary.get("start_identities", []) or [])
    ]
    return {
        "run_label": RUN_LABEL,
        "source_artifact_relpath": str(source_artifact_relpath),
        "fixture_seed": _safe_int(anchor_swap_comparison_summary.get("fixture_seed")),
        "search_seed": _safe_int(anchor_swap_comparison_summary.get("search_seed")),
        "retained_stage3_reference_match_ratio": float(retained_stage3_match),
        "retained_stage3_reference_source": _safe_str(
            anchor_swap_comparison_summary.get("retained_stage3_reference_source")
        ),
        "retained_stage3_reference_stage3_source": _safe_str(
            anchor_swap_comparison_summary.get("retained_stage3_reference_stage3_source")
        ),
        "retained_stage3_reference_candidate_hash": _safe_str(
            anchor_swap_comparison_summary.get("retained_stage3_reference_candidate_hash")
        ),
        "control_pre_phasec_best_match": float(
            _safe_float(control_summary.get("pre_phasec_best_match"))
        ),
        "control_best_match_ratio": float(control_best_match),
        "candidate_best_match_ratio": float(control_best_match),
        "control_delta_vs_retained_stage3_reference": float(
            control_best_match - retained_stage3_match
        ),
        "candidate_delta_vs_retained_stage3_reference": float(
            control_best_match - retained_stage3_match
        ),
        "candidate_minus_control_best_match_ratio": 0.0,
        "control_winner_lane": str(control_winner_lane),
        "control_winner_source": str(control_winner_source),
        "control_winner_source_rank": int(control_winner_source_rank),
        "control_winner_candidate_hash": str(control_winner_candidate_hash),
        "candidate_winner_lane": str(control_winner_lane),
        "candidate_winner_source": str(control_winner_source),
        "candidate_winner_source_rank": int(control_winner_source_rank),
        "candidate_winner_candidate_hash": str(control_winner_candidate_hash),
        "control_start_hashes": control_start_hashes,
        "candidate_start_hashes": list(control_start_hashes),
        "candidate_reordered_surface": 0,
        "control_phasec_evals": _safe_int(control_summary.get("phasec_evals")),
        "candidate_phasec_evals": _safe_int(control_summary.get("phasec_evals")),
    }


def _build_policy_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = [
        {
            "policy_name": SOURCE_ORDER_POLICY_NAME,
            "policy_group": CONTROL_POLICY_GROUP,
            "policy_family": CONTROL_POLICY_GROUP,
            "requested_width": "",
            "mode": "source_order",
        },
        {
            "policy_name": ANCHOR_SWAP_POLICY_NAME,
            "policy_group": REORDER_CONTROL_POLICY_GROUP,
            "policy_family": REORDER_CONTROL_POLICY_GROUP,
            "requested_width": "",
            "mode": "existing_anchor_swap",
        },
        {
            "policy_name": FRONTLOAD_ALL_POLICY_NAME,
            "policy_group": REORDER_CONTROL_POLICY_GROUP,
            "policy_family": REORDER_CONTROL_POLICY_GROUP,
            "requested_width": "all",
            "mode": "replay",
            "builder": (
                lambda start_rows, candidate_pool_rows: saved_surface_mod.build_phaseb_topk_frontload_all_saved_surface_rows(
                    start_rows
                )
            ),
        },
    ]
    for width in WIDTH_VALUES:
        specs.append(
            {
                "policy_name": f"phaseb_topk_frontload_{width}_v1",
                "policy_group": FRONTLOAD_DEPTH_POLICY_GROUP,
                "policy_family": FRONTLOAD_DEPTH_POLICY_GROUP,
                "requested_width": str(width),
                "mode": "replay",
                "builder": (
                    lambda start_rows, candidate_pool_rows, frontload_width=width: saved_surface_mod.build_phaseb_topk_frontload_depth_saved_surface_rows(
                        start_rows,
                        frontload_width=int(frontload_width),
                    )
                ),
            }
        )
    for width in WIDTH_VALUES:
        specs.append(
            {
                "policy_name": f"phaseb_topk_quota_{width}_v1",
                "policy_group": PHASEB_TOPK_QUOTA_POLICY_GROUP,
                "policy_family": PHASEB_TOPK_QUOTA_POLICY_GROUP,
                "requested_width": str(width),
                "mode": "replay",
                "builder": (
                    lambda start_rows, candidate_pool_rows, quota_width=width: saved_surface_mod.build_phaseb_topk_quota_saved_surface_rows(
                        start_rows,
                        candidate_pool_rows,
                        quota_width=int(quota_width),
                    )
                ),
            }
        )
    for width in WIDTH_VALUES:
        specs.append(
            {
                "policy_name": f"phaseb_topk_replace_width_{width}_v1",
                "policy_group": PHASEB_TOPK_ONLY_REPLACEMENT_POLICY_GROUP,
                "policy_family": PHASEB_TOPK_ONLY_REPLACEMENT_POLICY_GROUP,
                "requested_width": str(width),
                "mode": "replay",
                "builder": (
                    lambda start_rows, candidate_pool_rows, replace_width=width: saved_surface_mod.build_phaseb_topk_only_replacement_saved_surface_rows(
                        start_rows,
                        candidate_pool_rows,
                        replace_width=int(replace_width),
                    )
                ),
            }
        )
    return specs


def _count_non_anchor_phaseb_topk_rows(summary: Mapping[str, Any]) -> int:
    return int(
        sum(
            1
            for row in list(summary.get("start_identities", []) or [])[1:]
            if _safe_str(row.get("source")) == "phaseB_topk"
        )
    )


def _effective_applied_width(
    *,
    policy_group: str,
    candidate_summary: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]] | None,
) -> int:
    if policy_group == FRONTLOAD_DEPTH_POLICY_GROUP:
        return int(
            sum(
                1
                for row in list(candidate_summary.get("start_identities", []) or [])[1:]
                if _safe_str(row.get("selection_bucket")).startswith(
                    "phaseb_topk_frontload_depth"
                )
            )
        )
    if policy_group == PHASEB_TOPK_QUOTA_POLICY_GROUP:
        return _count_non_anchor_phaseb_topk_rows(candidate_summary)
    if policy_group == PHASEB_TOPK_ONLY_REPLACEMENT_POLICY_GROUP:
        if not candidate_rows:
            return 0
        return int(
            sum(
                1
                for row in list(candidate_rows or [])
                if _safe_str(row.get("replacement_evicted_candidate_hash"))
            )
        )
    return 0


def _replacement_details(
    candidate_rows: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    if not candidate_rows:
        return []
    details: list[dict[str, Any]] = []
    for start_rank, row in enumerate(list(candidate_rows or []), start=1):
        evicted_hash = _safe_str(row.get("replacement_evicted_candidate_hash"))
        if not evicted_hash:
            continue
        details.append(
            {
                "inserted_start_rank": int(start_rank),
                "inserted_candidate_hash": _safe_str(row.get("candidate_hash")),
                "inserted_source": _safe_str(row.get("source")),
                "inserted_source_rank": _safe_int(row.get("source_rank")),
                "evicted_start_rank": _safe_int(row.get("replacement_evicted_start_rank")),
                "evicted_candidate_hash": str(evicted_hash),
                "evicted_source": _safe_str(row.get("replacement_evicted_source")),
                "evicted_source_rank": _safe_int(row.get("replacement_evicted_source_rank")),
            }
        )
    return details


def build_surface_diagnostics(
    *,
    control_summary: Mapping[str, Any],
    candidate_summary: Mapping[str, Any],
    comparison_summary: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]] | None,
    policy_group: str,
) -> dict[str, Any]:
    control_start_hashes = [
        _safe_str(row.get("candidate_hash"))
        for row in list(control_summary.get("start_identities", []) or [])
    ]
    candidate_start_hashes = [
        _safe_str(row.get("candidate_hash"))
        for row in list(candidate_summary.get("start_identities", []) or [])
    ]
    control_hash_set = {item for item in control_start_hashes if item}
    candidate_hash_set = {item for item in candidate_start_hashes if item}
    membership_changed = bool(control_hash_set != candidate_hash_set)
    order_changed = bool(control_start_hashes != candidate_start_hashes)
    selected_surface_changed = bool(
        _safe_int(comparison_summary.get("candidate_reordered_surface")) == 1
        or order_changed
    )
    if not selected_surface_changed:
        selected_surface_change_class = "no_change"
    elif membership_changed and order_changed:
        selected_surface_change_class = "membership_and_order_change"
    elif membership_changed:
        selected_surface_change_class = "membership_change"
    else:
        selected_surface_change_class = "order_only"

    control_winner_hash = _safe_str(comparison_summary.get("control_winner_candidate_hash"))
    candidate_winner_hash = _safe_str(
        comparison_summary.get("candidate_winner_candidate_hash")
    )
    control_winner_source = _safe_str(comparison_summary.get("control_winner_source"))
    candidate_winner_source = _safe_str(comparison_summary.get("candidate_winner_source"))
    control_winner_source_rank = _safe_int(
        comparison_summary.get("control_winner_source_rank")
    )
    candidate_winner_source_rank = _safe_int(
        comparison_summary.get("candidate_winner_source_rank")
    )
    control_winner_lane = _safe_str(comparison_summary.get("control_winner_lane"))
    candidate_winner_lane = _safe_str(comparison_summary.get("candidate_winner_lane"))
    winner_identity_changed = bool(control_winner_hash != candidate_winner_hash)
    winner_source_changed = bool(
        (control_winner_source, control_winner_source_rank)
        != (candidate_winner_source, candidate_winner_source_rank)
    )
    winner_lane_changed = bool(control_winner_lane != candidate_winner_lane)
    candidate_minus_control = _safe_float(
        comparison_summary.get("candidate_minus_control_best_match_ratio")
    )
    same_score = bool(abs(candidate_minus_control) <= 1.0e-12)
    if same_score:
        if not selected_surface_changed:
            flat_delta_case_class = "true_noop"
        elif not winner_identity_changed:
            flat_delta_case_class = "active_surface_change_same_winner_flat"
        else:
            flat_delta_case_class = "winner_change_flat"
    else:
        if winner_identity_changed:
            flat_delta_case_class = "winner_change_scored"
        elif selected_surface_changed:
            flat_delta_case_class = "surface_change_same_winner_scored"
        else:
            flat_delta_case_class = "scored_without_surface_change"

    inserted_hashes = sorted(candidate_hash_set - control_hash_set)
    evicted_hashes = sorted(control_hash_set - candidate_hash_set)
    replacement_details = _replacement_details(candidate_rows)
    return {
        "selected_surface_changed": int(1 if selected_surface_changed else 0),
        "selected_surface_membership_changed": int(1 if membership_changed else 0),
        "selected_surface_order_changed": int(1 if order_changed else 0),
        "selected_surface_change_class": str(selected_surface_change_class),
        "winner_identity_changed": int(1 if winner_identity_changed else 0),
        "winner_source_changed": int(1 if winner_source_changed else 0),
        "winner_lane_changed": int(1 if winner_lane_changed else 0),
        "flat_delta_case_class": str(flat_delta_case_class),
        "control_non_anchor_phaseb_topk_count": _count_non_anchor_phaseb_topk_rows(
            control_summary
        ),
        "candidate_non_anchor_phaseb_topk_count": _count_non_anchor_phaseb_topk_rows(
            candidate_summary
        ),
        "effective_applied_width": _effective_applied_width(
            policy_group=policy_group,
            candidate_summary=candidate_summary,
            candidate_rows=candidate_rows,
        ),
        "inserted_candidate_hashes": inserted_hashes,
        "evicted_candidate_hashes": evicted_hashes,
        "replacement_details": replacement_details,
    }


def build_policy_row(
    *,
    policy_name: str,
    policy_group: str,
    policy_family: str,
    requested_width: str,
    bundle_relpath: str,
    comparison_summary: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    control_delta = _safe_float(
        comparison_summary.get("control_delta_vs_retained_stage3_reference")
    )
    candidate_minus_control = _safe_float(
        comparison_summary.get("candidate_minus_control_best_match_ratio")
    )
    control_fidelity = matrix_mod.classify_control_fidelity(
        control_delta_vs_retained=control_delta
    )
    candidate_effect = matrix_mod.classify_candidate_effect(
        candidate_minus_control=candidate_minus_control
    )
    usable_decision_gate = int(control_fidelity in {"stable", "near_stable"})
    return {
        "policy_name": str(policy_name),
        "policy_group": str(policy_group),
        "policy_family": str(policy_family),
        "requested_width": str(requested_width),
        "effective_applied_width": _safe_int(diagnostics.get("effective_applied_width")),
        "fixture_seed": _safe_int(comparison_summary.get("fixture_seed")),
        "search_seed": _safe_int(comparison_summary.get("search_seed")),
        "bundle_relpath": str(bundle_relpath),
        "source_artifact_relpath": _safe_str(
            comparison_summary.get("source_artifact_relpath")
        ),
        "retained_stage3_reference_match_ratio": _safe_float(
            comparison_summary.get("retained_stage3_reference_match_ratio")
        ),
        "control_best_match_ratio": _safe_float(
            comparison_summary.get("control_best_match_ratio")
        ),
        "candidate_best_match_ratio": _safe_float(
            comparison_summary.get("candidate_best_match_ratio")
        ),
        "candidate_minus_control_best_match_ratio": candidate_minus_control,
        "candidate_reordered_surface": _safe_int(
            comparison_summary.get("candidate_reordered_surface")
        ),
        "control_fidelity_quality": str(control_fidelity),
        "usable_decision_gate": int(usable_decision_gate),
        "candidate_effect": str(candidate_effect),
        "decision_gate_read": (
            str(candidate_effect) if usable_decision_gate else "context_only"
        ),
        "control_winner_lane": _safe_str(comparison_summary.get("control_winner_lane")),
        "control_winner_source": _safe_str(
            comparison_summary.get("control_winner_source")
        ),
        "control_winner_source_rank": _safe_int(
            comparison_summary.get("control_winner_source_rank")
        ),
        "control_winner_candidate_hash": _safe_str(
            comparison_summary.get("control_winner_candidate_hash")
        ),
        "candidate_winner_lane": _safe_str(
            comparison_summary.get("candidate_winner_lane")
        ),
        "candidate_winner_source": _safe_str(
            comparison_summary.get("candidate_winner_source")
        ),
        "candidate_winner_source_rank": _safe_int(
            comparison_summary.get("candidate_winner_source_rank")
        ),
        "candidate_winner_candidate_hash": _safe_str(
            comparison_summary.get("candidate_winner_candidate_hash")
        ),
        "selected_surface_changed": _safe_int(
            diagnostics.get("selected_surface_changed")
        ),
        "selected_surface_membership_changed": _safe_int(
            diagnostics.get("selected_surface_membership_changed")
        ),
        "selected_surface_order_changed": _safe_int(
            diagnostics.get("selected_surface_order_changed")
        ),
        "selected_surface_change_class": _safe_str(
            diagnostics.get("selected_surface_change_class")
        ),
        "winner_identity_changed": _safe_int(
            diagnostics.get("winner_identity_changed")
        ),
        "winner_source_changed": _safe_int(diagnostics.get("winner_source_changed")),
        "winner_lane_changed": _safe_int(diagnostics.get("winner_lane_changed")),
        "flat_delta_case_class": _safe_str(diagnostics.get("flat_delta_case_class")),
        "control_non_anchor_phaseb_topk_count": _safe_int(
            diagnostics.get("control_non_anchor_phaseb_topk_count")
        ),
        "candidate_non_anchor_phaseb_topk_count": _safe_int(
            diagnostics.get("candidate_non_anchor_phaseb_topk_count")
        ),
        "inserted_candidate_hashes": list(
            diagnostics.get("inserted_candidate_hashes", []) or []
        ),
        "evicted_candidate_hashes": list(
            diagnostics.get("evicted_candidate_hashes", []) or []
        ),
        "replacement_details": list(diagnostics.get("replacement_details", []) or []),
    }


def annotate_against_best_reorder_control(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    best_reorder_by_case: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        if _safe_str(row.get("policy_group")) != REORDER_CONTROL_POLICY_GROUP:
            continue
        case_key = (_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed")))
        incumbent = best_reorder_by_case.get(case_key)
        payload = dict(row)
        if incumbent is None:
            best_reorder_by_case[case_key] = payload
            continue
        incumbent_score = _safe_float(incumbent.get("candidate_best_match_ratio"))
        payload_score = _safe_float(payload.get("candidate_best_match_ratio"))
        if payload_score > incumbent_score:
            best_reorder_by_case[case_key] = payload
            continue
        if (
            payload_score == incumbent_score
            and _safe_str(payload.get("policy_name")) == ANCHOR_SWAP_POLICY_NAME
        ):
            best_reorder_by_case[case_key] = payload

    out_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        case_key = (_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed")))
        best_reorder = best_reorder_by_case.get(case_key)
        if best_reorder is None:
            payload["best_reorder_policy_name"] = ""
            payload["best_reorder_candidate_best_match_ratio"] = float("nan")
            payload["vs_best_reorder_delta"] = float("nan")
            payload["vs_best_reorder_read"] = ""
        else:
            delta = _safe_float(row.get("candidate_best_match_ratio")) - _safe_float(
                best_reorder.get("candidate_best_match_ratio")
            )
            payload["best_reorder_policy_name"] = _safe_str(
                best_reorder.get("policy_name")
            )
            payload["best_reorder_candidate_best_match_ratio"] = _safe_float(
                best_reorder.get("candidate_best_match_ratio")
            )
            payload["vs_best_reorder_delta"] = float(delta)
            payload["vs_best_reorder_read"] = str(
                matrix_mod.classify_candidate_effect(candidate_minus_control=delta)
            )
        out_rows.append(payload)
    return out_rows


def _build_policy_summary_row(
    policy_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    usable_rows = [
        dict(row) for row in policy_rows if _safe_int(row.get("usable_decision_gate")) == 1
    ]
    deltas = [
        _safe_float(row.get("candidate_minus_control_best_match_ratio"))
        for row in usable_rows
    ]
    reorder_deltas = [
        _safe_float(row.get("vs_best_reorder_delta")) for row in usable_rows
    ]
    return {
        "policy_name": _safe_str(policy_rows[0].get("policy_name") if policy_rows else ""),
        "policy_group": _safe_str(policy_rows[0].get("policy_group") if policy_rows else ""),
        "policy_family": _safe_str(policy_rows[0].get("policy_family") if policy_rows else ""),
        "requested_width": _safe_str(
            policy_rows[0].get("requested_width") if policy_rows else ""
        ),
        "case_count": int(len(policy_rows)),
        "usable_decision_gate_cases": int(len(usable_rows)),
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
        "mean_delta_on_gate": (
            float(sum(deltas) / len(deltas)) if deltas else float("nan")
        ),
        "mean_vs_best_reorder_on_gate": (
            float(sum(reorder_deltas) / len(reorder_deltas))
            if reorder_deltas
            else float("nan")
        ),
        "better_than_best_reorder_on_gate": int(
            sum(
                1
                for row in usable_rows
                if _safe_str(row.get("vs_best_reorder_read")) == "positive"
            )
        ),
        "equal_to_best_reorder_on_gate": int(
            sum(
                1
                for row in usable_rows
                if _safe_str(row.get("vs_best_reorder_read")) == "neutral"
            )
        ),
        "worse_than_best_reorder_on_gate": int(
            sum(
                1
                for row in usable_rows
                if _safe_str(row.get("vs_best_reorder_read")) == "negative"
            )
        ),
        "selected_surface_changed_cases": int(
            sum(_safe_int(row.get("selected_surface_changed")) for row in policy_rows)
        ),
        "selected_surface_membership_changed_cases": int(
            sum(
                _safe_int(row.get("selected_surface_membership_changed"))
                for row in policy_rows
            )
        ),
        "selected_surface_order_changed_cases": int(
            sum(_safe_int(row.get("selected_surface_order_changed")) for row in policy_rows)
        ),
        "winner_identity_changed_cases": int(
            sum(_safe_int(row.get("winner_identity_changed")) for row in policy_rows)
        ),
        "winner_source_changed_cases": int(
            sum(_safe_int(row.get("winner_source_changed")) for row in policy_rows)
        ),
        "winner_lane_changed_cases": int(
            sum(_safe_int(row.get("winner_lane_changed")) for row in policy_rows)
        ),
        "true_noop_cases": int(
            sum(
                1
                for row in policy_rows
                if _safe_str(row.get("flat_delta_case_class")) == "true_noop"
            )
        ),
        "active_surface_change_same_winner_flat_cases": int(
            sum(
                1
                for row in policy_rows
                if _safe_str(row.get("flat_delta_case_class"))
                == "active_surface_change_same_winner_flat"
            )
        ),
        "winner_change_flat_cases": int(
            sum(
                1
                for row in policy_rows
                if _safe_str(row.get("flat_delta_case_class")) == "winner_change_flat"
            )
        ),
        "winner_change_scored_cases": int(
            sum(
                1
                for row in policy_rows
                if _safe_str(row.get("flat_delta_case_class")) == "winner_change_scored"
            )
        ),
        "surface_change_same_winner_scored_cases": int(
            sum(
                1
                for row in policy_rows
                if _safe_str(row.get("flat_delta_case_class"))
                == "surface_change_same_winner_scored"
            )
        ),
        "mean_candidate_non_anchor_phaseb_topk_count": float(
            sum(
                _safe_int(row.get("candidate_non_anchor_phaseb_topk_count"))
                for row in policy_rows
            )
            / len(policy_rows)
        ),
        "mean_effective_applied_width": float(
            sum(_safe_int(row.get("effective_applied_width")) for row in policy_rows)
            / len(policy_rows)
        ),
    }


def _policy_summary_sort_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        _safe_str(row.get("policy_family")),
        _safe_str(row.get("requested_width")),
        _safe_str(row.get("policy_name")),
    )


def _pick_best_policy_summary_row(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return dict(
        max(
            rows,
            key=lambda row: (
                _safe_float(row.get("mean_vs_best_reorder_on_gate")),
                _safe_int(row.get("better_than_best_reorder_on_gate"))
                - _safe_int(row.get("worse_than_best_reorder_on_gate")),
                _safe_int(row.get("positive_on_gate"))
                - _safe_int(row.get("negative_on_gate")),
                -_safe_int(row.get("winner_identity_changed_cases")),
            ),
        )
    )


def build_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    policy_summary_rows = [
        _build_policy_summary_row(policy_rows)
        for policy_rows in (
            [
                dict(item)
                for item in rows
                if _safe_str(item.get("policy_name")) == policy_name
            ]
            for policy_name in sorted({_safe_str(row.get("policy_name")) for row in rows})
        )
    ]
    policy_summary_rows = sorted(policy_summary_rows, key=_policy_summary_sort_key)

    family_summary_rows: list[dict[str, Any]] = []
    family_names = sorted({_safe_str(row.get("policy_family")) for row in policy_summary_rows})
    for family_name in family_names:
        family_rows = [
            dict(row)
            for row in policy_summary_rows
            if _safe_str(row.get("policy_family")) == family_name
        ]
        best_row = _pick_best_policy_summary_row(family_rows)
        family_summary_rows.append(
            {
                "policy_family": str(family_name),
                "policy_count": int(len(family_rows)),
                "best_policy_name": _safe_str(best_row.get("policy_name")),
                "best_requested_width": _safe_str(best_row.get("requested_width")),
                "best_mean_effective_applied_width": _safe_float(
                    best_row.get("mean_effective_applied_width")
                ),
                "best_usable_decision_gate_cases": _safe_int(
                    best_row.get("usable_decision_gate_cases")
                ),
                "best_positive_on_gate": _safe_int(best_row.get("positive_on_gate")),
                "best_neutral_on_gate": _safe_int(best_row.get("neutral_on_gate")),
                "best_negative_on_gate": _safe_int(best_row.get("negative_on_gate")),
                "best_mean_delta_on_gate": _safe_float(
                    best_row.get("mean_delta_on_gate")
                ),
                "best_mean_vs_best_reorder_on_gate": _safe_float(
                    best_row.get("mean_vs_best_reorder_on_gate")
                ),
                "best_better_than_best_reorder_on_gate": _safe_int(
                    best_row.get("better_than_best_reorder_on_gate")
                ),
                "best_equal_to_best_reorder_on_gate": _safe_int(
                    best_row.get("equal_to_best_reorder_on_gate")
                ),
                "best_worse_than_best_reorder_on_gate": _safe_int(
                    best_row.get("worse_than_best_reorder_on_gate")
                ),
                "best_selected_surface_changed_cases": _safe_int(
                    best_row.get("selected_surface_changed_cases")
                ),
                "best_winner_identity_changed_cases": _safe_int(
                    best_row.get("winner_identity_changed_cases")
                ),
                "best_active_surface_change_same_winner_flat_cases": _safe_int(
                    best_row.get("active_surface_change_same_winner_flat_cases")
                ),
                "best_winner_change_flat_cases": _safe_int(
                    best_row.get("winner_change_flat_cases")
                ),
            }
        )

    best_policy_by_case_rows: list[dict[str, Any]] = []
    case_keys = sorted(
        {(_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed"))) for row in rows}
    )
    for case_key in case_keys:
        case_rows = [
            dict(row)
            for row in rows
            if (
                _safe_int(row.get("fixture_seed")),
                _safe_int(row.get("search_seed")),
            )
            == case_key
            and _safe_int(row.get("usable_decision_gate")) == 1
        ]
        if not case_rows:
            continue
        best_row = max(
            case_rows,
            key=lambda row: (
                _safe_float(row.get("candidate_best_match_ratio")),
                int(_safe_str(row.get("policy_name")) == ANCHOR_SWAP_POLICY_NAME),
            ),
        )
        best_policy_by_case_rows.append(
            {
                "fixture_seed": int(case_key[0]),
                "search_seed": int(case_key[1]),
                "best_policy_name": _safe_str(best_row.get("policy_name")),
                "best_policy_family": _safe_str(best_row.get("policy_family")),
                "best_candidate_best_match_ratio": _safe_float(
                    best_row.get("candidate_best_match_ratio")
                ),
                "best_candidate_minus_control": _safe_float(
                    best_row.get("candidate_minus_control_best_match_ratio")
                ),
                "best_flat_delta_case_class": _safe_str(
                    best_row.get("flat_delta_case_class")
                ),
            }
        )

    return {
        "run_label": str(RUN_LABEL),
        "case_count": int(
            len({(_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed"))) for row in rows})
        ),
        "policy_summary_rows": family_summary_rows and policy_summary_rows or [],
        "policy_family_summary_rows": family_summary_rows,
        "best_policy_by_case_rows": best_policy_by_case_rows,
    }


def build_recommendation(
    *,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    family_rows = [
        dict(row)
        for row in list(summary.get("policy_family_summary_rows", []) or [])
        if _safe_str(row.get("policy_family"))
        not in {CONTROL_POLICY_GROUP, REORDER_CONTROL_POLICY_GROUP}
    ]
    if not family_rows:
        return {
            "recommendation": "close",
            "best_policy_family": "",
            "best_policy_name": "",
            "best_requested_width": "",
            "reason": "No candidate policy families were evaluated.",
        }

    best_family = dict(
        max(
            family_rows,
            key=lambda row: (
                _safe_float(row.get("best_mean_vs_best_reorder_on_gate")),
                _safe_int(row.get("best_better_than_best_reorder_on_gate"))
                - _safe_int(row.get("best_worse_than_best_reorder_on_gate")),
                _safe_int(row.get("best_positive_on_gate"))
                - _safe_int(row.get("best_negative_on_gate")),
            ),
        )
    )
    mean_vs_best_reorder = _safe_float(best_family.get("best_mean_vs_best_reorder_on_gate"))
    better = _safe_int(best_family.get("best_better_than_best_reorder_on_gate"))
    worse = _safe_int(best_family.get("best_worse_than_best_reorder_on_gate"))
    negative = _safe_int(best_family.get("best_negative_on_gate"))
    active_flat = _safe_int(
        best_family.get("best_active_surface_change_same_winner_flat_cases")
    )
    best_positive = _safe_int(best_family.get("best_positive_on_gate"))
    if mean_vs_best_reorder <= 0.0 and better <= worse:
        if active_flat > 0 and best_positive > 0:
            recommendation = "refine"
            reason = (
                "No policy family clearly beats the reorder controls yet, but one "
                "family shows active surface changes plus a small positive signal "
                "that may justify a narrower follow-up."
            )
        else:
            recommendation = "close"
            reason = (
                "No policy family clearly beats the reorder-only controls on usable "
                "decision gates."
            )
    elif (
        mean_vs_best_reorder >= float(PROMOTE_MEAN_VS_REORDER_EPS)
        and worse <= 1
        and negative <= 1
    ):
        recommendation = "promote"
        reason = (
            "One policy family clearly beats the controls, a best width emerges, "
            "and the harm profile stays bounded."
        )
    else:
        recommendation = "refine"
        reason = (
            "One policy family looks stronger than the others, but the width or "
            "harm profile is still mixed."
        )
    return {
        "recommendation": str(recommendation),
        "best_policy_family": _safe_str(best_family.get("policy_family")),
        "best_policy_name": _safe_str(best_family.get("best_policy_name")),
        "best_requested_width": _safe_str(best_family.get("best_requested_width")),
        "reason": str(reason),
    }


def write_markdown(
    output_dir: Path,
    *,
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    recommendation: Mapping[str, Any],
) -> None:
    lines = [
        "# Phase-C Saved-Surface Phase-B Mass And Frontload Matrix",
        "",
        "Question:",
        "- how much useful `phaseB_topk` mass should the retained Phase-C selected-start set contain, and in what shape should that mass appear?",
        "",
        "Controls:",
        f"- `{SOURCE_ORDER_POLICY_NAME}`",
        f"- `{ANCHOR_SWAP_POLICY_NAME}`",
        f"- `{FRONTLOAD_ALL_POLICY_NAME}`",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- best family: `{_safe_str(recommendation.get('best_policy_family'))}`",
        f"- best policy: `{_safe_str(recommendation.get('best_policy_name'))}`",
        f"- best requested width: `{_safe_str(recommendation.get('best_requested_width')) or '-'}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Per-family summary:",
        "",
        "| family | best policy | width | usable gates | positive | neutral | negative | mean vs best reorder | changed surfaces | winner changes | active-flat |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
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
            f"`{_safe_int(row.get('best_winner_identity_changed_cases'))}` | "
            f"`{_safe_int(row.get('best_active_surface_change_same_winner_flat_cases'))}` |"
        )
    lines.extend(
        [
            "",
            "Per-policy summary:",
            "",
            "| policy | family | width | usable gates | positive | neutral | negative | mean delta | mean vs best reorder | changed surfaces | winner changes | flat class highlight |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in list(summary.get("policy_summary_rows", []) or []):
        lines.append(
            f"| `{_safe_str(row.get('policy_name'))}` | "
            f"`{_safe_str(row.get('policy_family'))}` | "
            f"`{_safe_str(row.get('requested_width')) or '-'} ` | "
            f"`{_safe_int(row.get('usable_decision_gate_cases'))}` | "
            f"`{_safe_int(row.get('positive_on_gate'))}` | "
            f"`{_safe_int(row.get('neutral_on_gate'))}` | "
            f"`{_safe_int(row.get('negative_on_gate'))}` | "
            f"`{_safe_float(row.get('mean_delta_on_gate')):.3f}` | "
            f"`{_safe_float(row.get('mean_vs_best_reorder_on_gate')):.3f}` | "
            f"`{_safe_int(row.get('selected_surface_changed_cases'))}` | "
            f"`{_safe_int(row.get('winner_identity_changed_cases'))}` | "
            f"`flat:{_safe_int(row.get('active_surface_change_same_winner_flat_cases'))}` |"
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
    (output_dir / "phasec_saved_surface_phaseb_mass_and_frontload_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_exploration() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    cases_dir = output_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    case_specs = _load_case_specs()
    policy_specs = _build_policy_specs()
    total_cases = int(len(case_specs))
    total_policy_units = int(total_cases * len(policy_specs))
    completed_policy_units = 0
    started_at = monotonic()

    _print_progress(
        "run_started "
        f"label={RUN_LABEL} "
        f"output_dir={_relative_path(output_dir)} "
        f"cases={total_cases} "
        f"policies={len(policy_specs)} "
        f"units={total_policy_units}"
    )

    rows: list[dict[str, Any]] = []
    for case_index, case_spec in enumerate(case_specs, start=1):
        bundle_relpath = _safe_str(case_spec.get("bundle_relpath"))
        source_artifact_relpath = _safe_str(case_spec.get("source_artifact_relpath"))
        fixture_seed = _safe_int(case_spec.get("fixture_seed"))
        search_seed = _safe_int(case_spec.get("search_seed"))
        bundle_path = REPO_ROOT / bundle_relpath
        case_dir = cases_dir / f"fixture_{fixture_seed}__search{search_seed}"
        case_dir.mkdir(parents=True, exist_ok=False)

        _print_progress(
            "case_started "
            f"case={case_index}/{total_cases} "
            f"fixture={fixture_seed} "
            f"search={search_seed} "
            f"elapsed={_format_duration(monotonic() - started_at)}"
        )

        control_summary = _load_json(bundle_path / "control_saved_surface_summary.json")
        anchor_swap_candidate_summary = _load_json(
            bundle_path / "candidate_saved_surface_summary.json"
        )
        anchor_swap_comparison_summary = _load_json(bundle_path / "comparison_summary.json")
        case = resume_mod.load_artifact_case(artifact_path=REPO_ROOT / source_artifact_relpath)
        saved_rows = exact_mod._load_saved_start_rows(case.artifact)
        candidate_pool_rows = _load_saved_candidate_pool_rows(case.artifact)
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

        for policy_spec in policy_specs:
            policy_name = _safe_str(policy_spec.get("policy_name"))
            policy_group = _safe_str(policy_spec.get("policy_group"))
            policy_family = _safe_str(policy_spec.get("policy_family"))
            requested_width = _safe_str(policy_spec.get("requested_width"))
            policy_started_at = monotonic()

            if _safe_str(policy_spec.get("mode")) == "source_order":
                candidate_rows = list(saved_rows)
                candidate_summary = _clone_source_order_candidate_summary(control_summary)
                comparison_summary = _build_source_order_comparison_summary(
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
                    raise TypeError(f"Policy builder missing or not callable: {policy_name}")
                candidate_rows = builder(saved_rows, candidate_pool_rows)
                candidate_summary = exact_mod.run_saved_surface_phasec_replay(
                    case=case,
                    saved_rows=candidate_rows,
                    replay_label=str(policy_name),
                )
                comparison_summary = exact_mod.build_comparison_summary(
                    case=case,
                    control_summary=control_summary,
                    candidate_summary=candidate_summary,
                )

            diagnostics = build_surface_diagnostics(
                control_summary=control_summary,
                candidate_summary=candidate_summary,
                comparison_summary=comparison_summary,
                candidate_rows=candidate_rows,
                policy_group=policy_group,
            )
            row = build_policy_row(
                policy_name=policy_name,
                policy_group=policy_group,
                policy_family=policy_family,
                requested_width=requested_width,
                bundle_relpath=bundle_relpath,
                comparison_summary=comparison_summary,
                diagnostics=diagnostics,
            )
            rows.append(row)

            _write_json(
                case_dir / f"{policy_name}__candidate_saved_surface_summary.json",
                candidate_summary,
            )
            _write_json(
                case_dir / f"{policy_name}__comparison_summary.json",
                comparison_summary,
            )
            _write_json(
                case_dir / f"{policy_name}__surface_diagnostics.json",
                diagnostics,
            )

            completed_policy_units += 1
            elapsed = monotonic() - started_at
            eta_seconds = (
                (elapsed / completed_policy_units)
                * (total_policy_units - completed_policy_units)
                if completed_policy_units > 0
                else float("nan")
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

    rows = annotate_against_best_reorder_control(rows)
    rows = sorted(
        rows,
        key=lambda row: (
            _safe_int(row.get("fixture_seed")),
            _safe_int(row.get("search_seed")),
            _safe_str(row.get("policy_family")),
            _safe_str(row.get("requested_width")),
            _safe_str(row.get("policy_name")),
        ),
    )
    summary = build_summary(rows)
    recommendation = build_recommendation(summary=summary)
    summary = {
        **summary,
        "output_dir": _relative_path(output_dir),
        "source_matrix_summary_relpath": SOURCE_MATRIX_SUMMARY_REL_PATH.as_posix(),
        "recommendation": dict(recommendation),
    }

    _write_jsonl(
        output_dir / "phasec_saved_surface_phaseb_mass_and_frontload_case_rows.jsonl",
        rows,
    )
    _write_csv(
        output_dir / "phasec_saved_surface_phaseb_mass_and_frontload_case_rows.csv",
        rows,
    )
    _write_csv(
        output_dir / "phasec_saved_surface_phaseb_mass_and_frontload_summary_rows.csv",
        list(summary.get("policy_summary_rows", []) or []),
    )
    _write_csv(
        output_dir / "phasec_saved_surface_phaseb_mass_and_frontload_family_summary_rows.csv",
        list(summary.get("policy_family_summary_rows", []) or []),
    )
    _write_json(
        output_dir / "phasec_saved_surface_phaseb_mass_and_frontload_summary.json",
        summary,
    )
    _write_json(
        output_dir / "phasec_saved_surface_phaseb_mass_and_frontload_recommendation.json",
        recommendation,
    )
    write_markdown(output_dir, rows=rows, summary=summary, recommendation=recommendation)

    run_summary = {
        "output_dir": _relative_path(output_dir),
        "case_count": _safe_int(summary.get("case_count")),
        "policy_count": int(len(list(summary.get("policy_summary_rows", []) or []))),
        "recommendation": _safe_str(recommendation.get("recommendation")),
        "best_policy_family": _safe_str(recommendation.get("best_policy_family")),
        "best_policy_name": _safe_str(recommendation.get("best_policy_name")),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} "
        f"elapsed={_format_duration(monotonic() - started_at)} "
        f"recommendation={_safe_str(recommendation.get('recommendation'))} "
        f"best_policy_family={_safe_str(recommendation.get('best_policy_family'))} "
        f"best_policy={_safe_str(recommendation.get('best_policy_name'))} "
        f"output_dir={_relative_path(output_dir)}"
    )
    return run_summary


def main() -> None:
    print(json.dumps(run_exploration(), sort_keys=True))


if __name__ == "__main__":
    main()
