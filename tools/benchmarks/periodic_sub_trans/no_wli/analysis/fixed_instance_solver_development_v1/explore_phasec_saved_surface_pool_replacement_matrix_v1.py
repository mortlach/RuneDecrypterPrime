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
        "explore_phasec_saved_surface_pool_replacement_matrix_v1.py"
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


RUN_LABEL = "phasec_saved_surface_pool_replacement_matrix_v1"
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
SOURCE_MATRIX_CSV_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260418T042939Z__candidate3_saved_surface_exact_matrix_v1/"
    "candidate3_saved_surface_exact_matrix.csv"
)
SOURCE_ORDER_POLICY_NAME = "source_order"
ANCHOR_SWAP_POLICY_NAME = "phaseb_topk_anchor_swap_v1"
FRONTLOAD_ALL_POLICY_NAME = "phaseb_topk_frontload_all_v1"
PROMOTE_MEAN_VS_REORDER_EPS = 0.003
REORDER_POLICY_NAMES = (
    ANCHOR_SWAP_POLICY_NAME,
    FRONTLOAD_ALL_POLICY_NAME,
)
REPLAY_POLICY_SPECS: tuple[
    tuple[str, str, str, Callable[[Sequence[Mapping[str, Any]], Sequence[Mapping[str, Any]]], list[dict[str, Any]]]],
    ...,
] = (
    (
        FRONTLOAD_ALL_POLICY_NAME,
        "reorder_control",
        "",
        lambda start_rows, candidate_pool_rows: saved_surface_mod.build_phaseb_topk_frontload_all_saved_surface_rows(
            start_rows
        ),
    ),
    (
        "pool_replace_width_1_v1",
        "replacement",
        "1",
        saved_surface_mod.build_phasec_pool_replace_width_one_saved_surface_rows,
    ),
    (
        "pool_replace_width_2_v1",
        "replacement",
        "2",
        saved_surface_mod.build_phasec_pool_replace_width_two_saved_surface_rows,
    ),
    (
        "pool_replace_width_3_v1",
        "replacement",
        "3",
        saved_surface_mod.build_phasec_pool_replace_width_three_saved_surface_rows,
    ),
    (
        "pool_replace_width_cap_all_v1",
        "replacement",
        "cap_all",
        saved_surface_mod.build_phasec_pool_replace_width_cap_all_saved_surface_rows,
    ),
)


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


def _print_progress(
    message: str,
) -> None:
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
                else:
                    payload[key] = value
            writer.writerow(payload)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_baseline_anchor_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with (REPO_ROOT / SOURCE_MATRIX_CSV_REL_PATH).open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "policy_name": str(ANCHOR_SWAP_POLICY_NAME),
                    "policy_group": "reorder_control",
                    "replacement_width": "",
                    "fixture_seed": _safe_int(row.get("fixture_seed")),
                    "search_seed": _safe_int(row.get("search_seed")),
                    "bundle_relpath": _safe_str(row.get("bundle_relpath")),
                    "source_artifact_relpath": _safe_str(row.get("source_artifact_relpath")),
                    "retained_stage3_reference_match_ratio": _safe_float(
                        row.get("retained_stage3_reference_match_ratio")
                    ),
                    "control_best_match_ratio": _safe_float(
                        row.get("control_best_match_ratio")
                    ),
                    "candidate_best_match_ratio": _safe_float(
                        row.get("candidate_best_match_ratio")
                    ),
                    "candidate_minus_control_best_match_ratio": _safe_float(
                        row.get("candidate_minus_control_best_match_ratio")
                    ),
                    "candidate_reordered_surface": _safe_int(
                        row.get("candidate_reordered_surface")
                    ),
                    "control_fidelity_quality": _safe_str(
                        row.get("control_fidelity_quality")
                    ),
                    "usable_decision_gate": _safe_int(row.get("usable_decision_gate")),
                    "candidate_effect": _safe_str(row.get("candidate_effect")),
                    "decision_gate_read": _safe_str(row.get("decision_gate_read")),
                    "control_winner_source": _safe_str(
                        row.get("control_winner_source")
                    ),
                    "candidate_winner_source": _safe_str(
                        row.get("candidate_winner_source")
                    ),
                    "candidate_winner_candidate_hash": _safe_str(
                        row.get("candidate_winner_candidate_hash")
                    ),
                }
            )
    return rows


def build_source_order_rows(
    anchor_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out_rows: list[dict[str, Any]] = []
    for anchor_row in anchor_rows:
        usable_decision_gate = _safe_int(anchor_row.get("usable_decision_gate"))
        out_rows.append(
            {
                "policy_name": str(SOURCE_ORDER_POLICY_NAME),
                "policy_group": "control",
                "replacement_width": "",
                "fixture_seed": _safe_int(anchor_row.get("fixture_seed")),
                "search_seed": _safe_int(anchor_row.get("search_seed")),
                "bundle_relpath": _safe_str(anchor_row.get("bundle_relpath")),
                "source_artifact_relpath": _safe_str(
                    anchor_row.get("source_artifact_relpath")
                ),
                "retained_stage3_reference_match_ratio": _safe_float(
                    anchor_row.get("retained_stage3_reference_match_ratio")
                ),
                "control_best_match_ratio": _safe_float(
                    anchor_row.get("control_best_match_ratio")
                ),
                "candidate_best_match_ratio": _safe_float(
                    anchor_row.get("control_best_match_ratio")
                ),
                "candidate_minus_control_best_match_ratio": 0.0,
                "candidate_reordered_surface": 0,
                "control_fidelity_quality": _safe_str(
                    anchor_row.get("control_fidelity_quality")
                ),
                "usable_decision_gate": int(usable_decision_gate),
                "candidate_effect": "neutral",
                "decision_gate_read": (
                    "neutral" if int(usable_decision_gate) == 1 else "context_only"
                ),
                "control_winner_source": _safe_str(
                    anchor_row.get("control_winner_source")
                ),
                "candidate_winner_source": _safe_str(
                    anchor_row.get("control_winner_source")
                ),
                "candidate_winner_candidate_hash": _safe_str(
                    anchor_row.get("control_winner_candidate_hash")
                ),
            }
        )
    return out_rows


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


def build_policy_row(
    *,
    policy_name: str,
    policy_group: str,
    replacement_width: str,
    bundle_relpath: str,
    comparison_summary: Mapping[str, Any],
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
        "replacement_width": str(replacement_width),
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
        "control_winner_source": _safe_str(
            comparison_summary.get("control_winner_source")
        ),
        "candidate_winner_source": _safe_str(
            comparison_summary.get("candidate_winner_source")
        ),
        "candidate_winner_candidate_hash": _safe_str(
            comparison_summary.get("candidate_winner_candidate_hash")
        ),
    }


def annotate_against_best_reorder_control(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    best_reorder_by_case: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        if _safe_str(row.get("policy_group")) != "reorder_control":
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


def build_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    policy_summary_rows: list[dict[str, Any]] = []
    policy_names = sorted({_safe_str(row.get("policy_name")) for row in rows})
    for policy_name in policy_names:
        policy_rows = [
            dict(row) for row in rows if _safe_str(row.get("policy_name")) == policy_name
        ]
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
        policy_summary_rows.append(
            {
                "policy_name": str(policy_name),
                "policy_group": _safe_str(policy_rows[0].get("policy_group") if policy_rows else ""),
                "replacement_width": _safe_str(
                    policy_rows[0].get("replacement_width") if policy_rows else ""
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
                "best_policy_group": _safe_str(best_row.get("policy_group")),
                "best_candidate_best_match_ratio": _safe_float(
                    best_row.get("candidate_best_match_ratio")
                ),
                "best_candidate_minus_control": _safe_float(
                    best_row.get("candidate_minus_control_best_match_ratio")
                ),
            }
        )

    summary_rows = sorted(
        policy_summary_rows,
        key=lambda row: (
            _safe_str(row.get("policy_group")),
            _safe_str(row.get("replacement_width")),
            _safe_str(row.get("policy_name")),
        ),
    )
    return {
        "run_label": str(RUN_LABEL),
        "case_count": int(
            len({(_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed"))) for row in rows})
        ),
        "policy_summary_rows": summary_rows,
        "best_policy_by_case_rows": best_policy_by_case_rows,
    }


def build_recommendation(
    *,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    replacement_rows = [
        dict(row)
        for row in list(summary.get("policy_summary_rows", []) or [])
        if _safe_str(row.get("policy_group")) == "replacement"
    ]
    if not replacement_rows:
        return {
            "recommendation": "close",
            "best_replacement_policy_name": "",
            "best_replacement_width": "",
            "reason": "No replacement policy rows were evaluated.",
        }

    best_row = max(
        replacement_rows,
        key=lambda row: (
            _safe_float(row.get("mean_vs_best_reorder_on_gate")),
            _safe_int(row.get("better_than_best_reorder_on_gate"))
            - _safe_int(row.get("worse_than_best_reorder_on_gate")),
            _safe_int(row.get("positive_on_gate"))
            - _safe_int(row.get("negative_on_gate")),
        ),
    )
    mean_vs_best_reorder = _safe_float(best_row.get("mean_vs_best_reorder_on_gate"))
    better = _safe_int(best_row.get("better_than_best_reorder_on_gate"))
    worse = _safe_int(best_row.get("worse_than_best_reorder_on_gate"))
    negative = _safe_int(best_row.get("negative_on_gate"))

    if mean_vs_best_reorder <= 0.0 and better <= worse:
        recommendation = "close"
        reason = (
            "Replacement widths do not beat the reorder-only controls on usable "
            "decision gates."
        )
    elif (
        mean_vs_best_reorder >= float(PROMOTE_MEAN_VS_REORDER_EPS)
        and worse == 0
        and negative <= 1
    ):
        recommendation = "promote"
        reason = (
            "One replacement width is clearly better than the reorder-only "
            "controls on usable gates and the harm profile stays bounded."
        )
    else:
        recommendation = "refine"
        reason = (
            "Replacement shows some signal against the reorder-only controls, "
            "but the gain-versus-harm trade is still mixed."
        )
    return {
        "recommendation": str(recommendation),
        "best_replacement_policy_name": _safe_str(best_row.get("policy_name")),
        "best_replacement_width": _safe_str(best_row.get("replacement_width")),
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
        "# Phase-C Saved-Surface Pool Replacement Matrix",
        "",
        "Question:",
        "- on the exact saved-surface lane, does true late-pool replacement beat the reorder-only controls strongly enough to justify a second study?",
        "",
        "Policies compared:",
        f"- `{SOURCE_ORDER_POLICY_NAME}`",
        f"- `{ANCHOR_SWAP_POLICY_NAME}`",
        f"- `{FRONTLOAD_ALL_POLICY_NAME}`",
        "- `pool_replace_width_1_v1`",
        "- `pool_replace_width_2_v1`",
        "- `pool_replace_width_3_v1`",
        "- `pool_replace_width_cap_all_v1`",
        "",
        "Replacement rule used in this batch:",
        "- keep the retained anchor fixed",
        "- replace the weakest non-anchor selected starts",
        "- use strongest eligible non-selected challengers from the retained late pool",
        "- prefer `phaseB_topk` challengers ahead of `phaseA_selected` challengers",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- best replacement policy: `{_safe_str(recommendation.get('best_replacement_policy_name'))}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Per-policy summary:",
        "",
        "| policy | group | width | usable gates | positive | neutral | negative | mean delta | mean vs best reorder | better vs best reorder | equal | worse |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in list(summary.get("policy_summary_rows", []) or []):
        lines.append(
            f"| `{_safe_str(row.get('policy_name'))}` | "
            f"`{_safe_str(row.get('policy_group'))}` | "
            f"`{_safe_str(row.get('replacement_width')) or '-'} ` | "
            f"`{_safe_int(row.get('usable_decision_gate_cases'))}` | "
            f"`{_safe_int(row.get('positive_on_gate'))}` | "
            f"`{_safe_int(row.get('neutral_on_gate'))}` | "
            f"`{_safe_int(row.get('negative_on_gate'))}` | "
            f"`{_safe_float(row.get('mean_delta_on_gate')):.3f}` | "
            f"`{_safe_float(row.get('mean_vs_best_reorder_on_gate')):.3f}` | "
            f"`{_safe_int(row.get('better_than_best_reorder_on_gate'))}` | "
            f"`{_safe_int(row.get('equal_to_best_reorder_on_gate'))}` | "
            f"`{_safe_int(row.get('worse_than_best_reorder_on_gate'))}` |"
        )
    lines.extend(
        [
            "",
            "Usable-gate case matrix:",
            "",
            "| case | policy | group | control | candidate | delta | best reorder | vs best reorder | read |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    usable_rows = [
        dict(row) for row in rows if _safe_int(row.get("usable_decision_gate")) == 1
    ]
    for row in sorted(
        usable_rows,
        key=lambda item: (
            _safe_int(item.get("fixture_seed")),
            _safe_int(item.get("search_seed")),
            _safe_str(item.get("policy_name")),
        ),
    ):
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}/search{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_str(row.get('policy_name'))}` | "
            f"`{_safe_str(row.get('policy_group'))}` | "
            f"`{_safe_float(row.get('control_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('candidate_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('candidate_minus_control_best_match_ratio')):.3f}` | "
            f"`{_safe_str(row.get('best_reorder_policy_name'))}` | "
            f"`{_safe_float(row.get('vs_best_reorder_delta')):.3f}` | "
            f"`{_safe_str(row.get('vs_best_reorder_read'))}` |"
        )
    (output_dir / "phasec_saved_surface_pool_replacement_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_exploration() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    cases_dir = output_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    anchor_rows = _load_baseline_anchor_rows()
    source_order_rows = build_source_order_rows(anchor_rows)
    case_specs = _load_case_specs()
    total_cases = int(len(case_specs))
    total_policy_replays = int(total_cases * len(REPLAY_POLICY_SPECS))
    completed_policy_replays = 0
    started_at = monotonic()

    _print_progress(
        "run_started "
        f"label={RUN_LABEL} "
        f"output_dir={_relative_path(output_dir)} "
        f"cases={total_cases} "
        f"replay_policies={len(REPLAY_POLICY_SPECS)} "
        f"replay_units={total_policy_replays}"
    )

    replay_rows: list[dict[str, Any]] = []
    for case_index, case_spec in enumerate(case_specs, start=1):
        bundle_relpath = _safe_str(case_spec.get("bundle_relpath"))
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
        source_artifact_relpath = _safe_str(case_spec.get("source_artifact_relpath"))
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

        for policy_name, policy_group, replacement_width, builder in REPLAY_POLICY_SPECS:
            policy_started_at = monotonic()
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
            row = build_policy_row(
                policy_name=str(policy_name),
                policy_group=str(policy_group),
                replacement_width=str(replacement_width),
                bundle_relpath=str(bundle_relpath),
                comparison_summary=comparison_summary,
            )
            replay_rows.append(row)
            _write_json(
                case_dir / f"{policy_name}__candidate_saved_surface_summary.json",
                candidate_summary,
            )
            _write_json(
                case_dir / f"{policy_name}__comparison_summary.json",
                comparison_summary,
            )
            completed_policy_replays += 1
            elapsed = monotonic() - started_at
            eta_seconds = (
                (elapsed / completed_policy_replays)
                * (total_policy_replays - completed_policy_replays)
                if completed_policy_replays > 0
                else float("nan")
            )
            _print_progress(
                "policy_finished "
                f"unit={completed_policy_replays}/{total_policy_replays} "
                f"case={case_index}/{total_cases} "
                f"fixture={fixture_seed} "
                f"search={search_seed} "
                f"policy={policy_name} "
                f"delta={_safe_float(comparison_summary.get('candidate_minus_control_best_match_ratio')):.3f} "
                f"elapsed={_format_duration(elapsed)} "
                f"eta={_format_duration(eta_seconds)} "
                f"policy_runtime={_format_duration(monotonic() - policy_started_at)}"
            )

    rows = annotate_against_best_reorder_control(
        [*source_order_rows, *anchor_rows, *replay_rows]
    )
    rows = sorted(
        rows,
        key=lambda row: (
            _safe_int(row.get("fixture_seed")),
            _safe_int(row.get("search_seed")),
            _safe_str(row.get("policy_group")),
            _safe_str(row.get("replacement_width")),
            _safe_str(row.get("policy_name")),
        ),
    )
    summary = build_summary(rows)
    recommendation = build_recommendation(summary=summary)
    summary = {
        **summary,
        "output_dir": _relative_path(output_dir),
        "source_matrix_summary_relpath": SOURCE_MATRIX_SUMMARY_REL_PATH.as_posix(),
        "source_matrix_csv_relpath": SOURCE_MATRIX_CSV_REL_PATH.as_posix(),
        "recommendation": dict(recommendation),
    }

    _write_jsonl(output_dir / "phasec_saved_surface_pool_replacement_case_rows.jsonl", rows)
    _write_csv(output_dir / "phasec_saved_surface_pool_replacement_case_rows.csv", rows)
    _write_csv(
        output_dir / "phasec_saved_surface_pool_replacement_summary_rows.csv",
        list(summary.get("policy_summary_rows", []) or []),
    )
    _write_json(output_dir / "phasec_saved_surface_pool_replacement_summary.json", summary)
    _write_json(
        output_dir / "phasec_saved_surface_pool_replacement_recommendation.json",
        recommendation,
    )
    write_markdown(output_dir, rows=rows, summary=summary, recommendation=recommendation)

    run_summary = {
        "output_dir": _relative_path(output_dir),
        "case_count": _safe_int(summary.get("case_count")),
        "policy_count": int(len(list(summary.get("policy_summary_rows", []) or []))),
        "recommendation": _safe_str(recommendation.get("recommendation")),
        "best_replacement_policy_name": _safe_str(
            recommendation.get("best_replacement_policy_name")
        ),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} "
        f"elapsed={_format_duration(monotonic() - started_at)} "
        f"recommendation={_safe_str(recommendation.get('recommendation'))} "
        f"best_replacement_policy={_safe_str(recommendation.get('best_replacement_policy_name'))} "
        f"output_dir={_relative_path(output_dir)}"
    )
    return run_summary


def main() -> None:
    print(json.dumps(run_exploration(), sort_keys=True))


if __name__ == "__main__":
    main()
