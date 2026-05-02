from __future__ import annotations

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
        "explore_phasec_richer_pool_phaseb_replacement_reopen_v1.py"
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
    explore_phasec_saved_surface_phaseb_mass_and_frontload_matrix_v1 as phaseb_mass_mod,
    verify_candidate3_phasec_saved_surface_1511_7004 as saved_surface_mod,
    verify_candidate3_phasec_saved_surface_exact_1511_7004 as exact_mod,
)


RUN_LABEL = "phasec_richer_pool_phaseb_replacement_reopen_v1"
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
SOURCE_ARTIFACT_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260420T163353521403Z__bench_solve_pipeline_no_wli__ee62083/"
    "final_instances/fixture_001__p9_c3_l1000__text0__seed1111__search7002.json"
)
CONTROL_POLICY_NAME = "source_order"
REORDER_FLOOR_POLICY_NAME = "phaseb_topk_frontload_all_v1"
PROMOTE_DELTA_EPS = 0.003
POLICY_SPECS: tuple[
    tuple[str, str, str, Callable[[Sequence[Mapping[str, Any]], Sequence[Mapping[str, Any]]], list[dict[str, Any]]] | None],
    ...,
] = (
    (CONTROL_POLICY_NAME, "control", "", None),
    (
        REORDER_FLOOR_POLICY_NAME,
        "reorder_floor",
        "all",
        lambda start_rows, candidate_pool_rows: saved_surface_mod.build_phaseb_topk_frontload_all_saved_surface_rows(  # noqa: ARG005
            start_rows
        ),
    ),
    (
        "phaseb_topk_replace_width_1_v1",
        "replacement",
        "1",
        lambda start_rows, candidate_pool_rows: saved_surface_mod.build_phaseb_topk_only_replacement_saved_surface_rows(
            start_rows,
            candidate_pool_rows,
            replace_width=1,
        ),
    ),
    (
        "phaseb_topk_replace_width_2_v1",
        "replacement",
        "2",
        lambda start_rows, candidate_pool_rows: saved_surface_mod.build_phaseb_topk_only_replacement_saved_surface_rows(
            start_rows,
            candidate_pool_rows,
            replace_width=2,
        ),
    ),
    (
        "phaseb_topk_replace_width_3_v1",
        "replacement",
        "3",
        lambda start_rows, candidate_pool_rows: saved_surface_mod.build_phaseb_topk_only_replacement_saved_surface_rows(
            start_rows,
            candidate_pool_rows,
            replace_width=3,
        ),
    ),
)

QUESTION = (
    "on the richer retained pool from 1111/search7002, can narrow phaseB_topk-only "
    "replacement beat the richer-pool control and reorder floor on the exact "
    "saved-surface lane?"
)
SUSPICION = (
    "the supply retake created real spare phaseB_topk challengers, so replacement "
    "should now be structurally active and may unlock a better exact-lane winner."
)
ALTERNATIVE = (
    "the richer pool only archived extra variety, and replacement will stay flat or "
    "harmful even when it can now insert true spare challengers."
)
EXPECT_IF_SUSPICION = (
    "at least one replacement width changes the winner or exact score and beats both "
    "source_order and frontload_all."
)
EXPECT_IF_ALTERNATIVE = (
    "replacement widths change the surface but stay flat or worse than frontload_all, "
    "with mostly same-winner or cosmetic changes."
)
DECISION_RULE = (
    "promote only if one width clearly beats the reorder floor with a meaningful "
    "winner-level change; otherwise refine only for a narrow ambiguous positive and "
    "close if the richer-pool replacement line stays flat or harmful."
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


def _print_progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] {message}", flush=True)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


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


def _load_saved_candidate_pool_rows(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    diagnostics = dict(artifact.get("stage3_diagnostics", {}) or {})
    return [
        dict(row)
        for row in list(diagnostics.get("phaseC_candidate_pool_rows", []) or [])
        if isinstance(row, Mapping)
    ]


def _clone_control_summary(control_summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **dict(control_summary),
        "replay_label": CONTROL_POLICY_NAME,
    }


def _build_control_comparison_summary(
    *,
    case: exact_mod.phasec_replay_mod.ArtifactCase,
    control_summary: Mapping[str, Any],
) -> dict[str, Any]:
    retained_stage3_reference = exact_mod.retained_mod.extract_retained_stage3_reference(
        case.artifact
    )
    retained_stage3_match = _safe_float(retained_stage3_reference.get("match_ratio"))
    control_best_match = _safe_float(control_summary.get("best_match_ratio"))
    control_winner_lane = _safe_str(control_summary.get("winner_lane"))
    control_winner_source = _safe_str(control_summary.get("winner_source"))
    control_winner_source_rank = _safe_int(control_summary.get("winner_source_rank"))
    control_winner_candidate_hash = _safe_str(
        control_summary.get("winner_candidate_hash")
    )
    control_start_hashes = [
        _safe_str(row.get("candidate_hash"))
        for row in list(control_summary.get("start_identities", []) or [])
    ]
    return {
        "run_label": RUN_LABEL,
        "source_artifact_relpath": _relative_path(case.artifact_path),
        "fixture_seed": _safe_int(case.artifact.get("instance_source_key_seed")),
        "search_seed": _safe_int(case.artifact.get("search_seed")),
        "retained_stage3_reference_match_ratio": float(retained_stage3_match),
        "retained_stage3_reference_source": _safe_str(
            retained_stage3_reference.get("source")
        ),
        "retained_stage3_reference_stage3_source": _safe_str(
            retained_stage3_reference.get("stage3_source")
        ),
        "retained_stage3_reference_candidate_hash": _safe_str(
            retained_stage3_reference.get("candidate_hash")
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


def _annotate_vs_reorder_floor(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    reorder_floor_row = next(
        row
        for row in rows
        if _safe_str(row.get("policy_name")) == REORDER_FLOOR_POLICY_NAME
    )
    reorder_floor_score = _safe_float(reorder_floor_row.get("candidate_best_match_ratio"))
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        delta = _safe_float(row.get("candidate_best_match_ratio")) - reorder_floor_score
        payload["reorder_floor_policy_name"] = REORDER_FLOOR_POLICY_NAME
        payload["reorder_floor_candidate_best_match_ratio"] = float(reorder_floor_score)
        payload["vs_reorder_floor_delta"] = float(delta)
        payload["vs_reorder_floor_read"] = matrix_mod.classify_candidate_effect(
            candidate_minus_control=delta
        )
        out_rows.append(payload)
    return out_rows


def _build_row(
    *,
    policy_name: str,
    policy_group: str,
    requested_width: str,
    case: exact_mod.phasec_replay_mod.ArtifactCase,
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
        "requested_width": str(requested_width),
        "effective_applied_width": _safe_int(diagnostics.get("effective_applied_width")),
        "fixture_seed": _safe_int(case.artifact.get("instance_source_key_seed")),
        "search_seed": _safe_int(case.artifact.get("search_seed")),
        "bundle_relpath": _relative_path(case.artifact_path),
        "source_artifact_relpath": _relative_path(case.artifact_path),
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
        "decision_gate_read": str(candidate_effect) if usable_decision_gate else "context_only",
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
        "selected_surface_changed": _safe_int(diagnostics.get("selected_surface_changed")),
        "selected_surface_membership_changed": _safe_int(
            diagnostics.get("selected_surface_membership_changed")
        ),
        "selected_surface_order_changed": _safe_int(
            diagnostics.get("selected_surface_order_changed")
        ),
        "selected_surface_change_class": _safe_str(
            diagnostics.get("selected_surface_change_class")
        ),
        "winner_identity_changed": _safe_int(diagnostics.get("winner_identity_changed")),
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


def build_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summary_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        summary_rows.append(
            {
                "policy_name": _safe_str(payload.get("policy_name")),
                "policy_group": _safe_str(payload.get("policy_group")),
                "requested_width": _safe_str(payload.get("requested_width")),
                "effective_applied_width": _safe_int(
                    payload.get("effective_applied_width")
                ),
                "candidate_best_match_ratio": _safe_float(
                    payload.get("candidate_best_match_ratio")
                ),
                "candidate_minus_control_best_match_ratio": _safe_float(
                    payload.get("candidate_minus_control_best_match_ratio")
                ),
                "vs_reorder_floor_delta": _safe_float(
                    payload.get("vs_reorder_floor_delta")
                ),
                "vs_reorder_floor_read": _safe_str(
                    payload.get("vs_reorder_floor_read")
                ),
                "selected_surface_change_class": _safe_str(
                    payload.get("selected_surface_change_class")
                ),
                "winner_identity_changed": _safe_int(
                    payload.get("winner_identity_changed")
                ),
                "flat_delta_case_class": _safe_str(
                    payload.get("flat_delta_case_class")
                ),
            }
        )
    best_row = max(
        [row for row in rows if _safe_str(row.get("policy_group")) == "replacement"],
        key=lambda row: (
            _safe_float(row.get("vs_reorder_floor_delta")),
            _safe_float(row.get("candidate_minus_control_best_match_ratio")),
            _safe_int(row.get("winner_identity_changed")),
        ),
    )
    return {
        "run_label": RUN_LABEL,
        "case_count": 1,
        "policy_summary_rows": summary_rows,
        "best_replacement_policy_name": _safe_str(best_row.get("policy_name")),
        "best_replacement_width": _safe_str(best_row.get("requested_width")),
        "best_replacement_vs_reorder_floor_delta": _safe_float(
            best_row.get("vs_reorder_floor_delta")
        ),
        "best_replacement_delta_vs_control": _safe_float(
            best_row.get("candidate_minus_control_best_match_ratio")
        ),
        "best_replacement_winner_identity_changed": _safe_int(
            best_row.get("winner_identity_changed")
        ),
        "best_replacement_flat_delta_case_class": _safe_str(
            best_row.get("flat_delta_case_class")
        ),
    }


def build_recommendation(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    replacement_rows = [
        dict(row) for row in rows if _safe_str(row.get("policy_group")) == "replacement"
    ]
    best_row = max(
        replacement_rows,
        key=lambda row: (
            _safe_float(row.get("vs_reorder_floor_delta")),
            _safe_float(row.get("candidate_minus_control_best_match_ratio")),
            _safe_int(row.get("winner_identity_changed")),
        ),
    )
    vs_floor = _safe_float(best_row.get("vs_reorder_floor_delta"))
    vs_control = _safe_float(best_row.get("candidate_minus_control_best_match_ratio"))
    winner_identity_changed = _safe_int(best_row.get("winner_identity_changed"))
    if vs_floor <= 0.0:
        recommendation = "close"
        reason = (
            "No replacement width beats the richer-pool reorder floor on the exact "
            "saved-surface lane."
        )
    elif (
        vs_floor >= float(PROMOTE_DELTA_EPS)
        and vs_control > 0.0
        and winner_identity_changed == 1
    ):
        recommendation = "promote"
        reason = (
            "One replacement width clearly beats both control and reorder floor and "
            "the improvement is tied to a winner-level change."
        )
    else:
        recommendation = "refine"
        reason = (
            "Replacement shows some richer-pool signal, but the gain is still too "
            "small or too ambiguous for runtime confirmation."
        )
    return {
        "recommendation": recommendation,
        "best_replacement_policy_name": _safe_str(best_row.get("policy_name")),
        "best_replacement_width": _safe_str(best_row.get("requested_width")),
        "reason": reason,
    }


def write_markdown(
    output_dir: Path,
    *,
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    recommendation: Mapping[str, Any],
) -> None:
    lines = [
        "# Phase-C Richer-Pool Replacement Reopen v1",
        "",
        "Question:",
        f"- {QUESTION}",
        "",
        "Pre-run block:",
        f"- suspicion: {SUSPICION}",
        f"- main alternative: {ALTERNATIVE}",
        f"- if suspicion is true, expect: {EXPECT_IF_SUSPICION}",
        f"- if alternative is true, expect: {EXPECT_IF_ALTERNATIVE}",
        f"- tomorrow's decision rule: {DECISION_RULE}",
        "",
        "Richer-pool retained source:",
        f"- `{SOURCE_ARTIFACT_REL_PATH.as_posix()}`",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- best replacement policy: `{_safe_str(recommendation.get('best_replacement_policy_name'))}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Per-policy exact-lane read:",
        "",
        "| policy | group | width | effective width | candidate | delta vs control | delta vs reorder floor | read vs floor | surface change | winner changed | flat-delta class |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{_safe_str(row.get('policy_name'))}` | "
            f"`{_safe_str(row.get('policy_group'))}` | "
            f"`{_safe_str(row.get('requested_width')) or '-'} ` | "
            f"`{_safe_int(row.get('effective_applied_width'))}` | "
            f"`{_safe_float(row.get('candidate_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('candidate_minus_control_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('vs_reorder_floor_delta')):.3f}` | "
            f"`{_safe_str(row.get('vs_reorder_floor_read'))}` | "
            f"`{_safe_str(row.get('selected_surface_change_class'))}` | "
            f"`{_safe_int(row.get('winner_identity_changed'))}` | "
            f"`{_safe_str(row.get('flat_delta_case_class'))}` |"
        )
    lines.extend(
        [
            "",
            "Replacement identity details:",
            "",
        ]
    )
    for row in rows:
        if _safe_str(row.get("policy_group")) != "replacement":
            continue
        lines.append(f"## `{_safe_str(row.get('policy_name'))}`")
        details = list(row.get("replacement_details", []) or [])
        if not details:
            lines.append("- no replacement insertions were applied")
            lines.append("")
            continue
        for detail in details:
            lines.append(
                "- inserted "
                f"`{_safe_str(detail.get('inserted_candidate_hash'))}` "
                f"from `{_safe_str(detail.get('inserted_source'))}`/"
                f"`{_safe_int(detail.get('inserted_source_rank'))}` at start "
                f"`{_safe_int(detail.get('inserted_start_rank'))}`, evicting "
                f"`{_safe_str(detail.get('evicted_candidate_hash'))}` "
                f"from `{_safe_str(detail.get('evicted_source'))}`/"
                f"`{_safe_int(detail.get('evicted_source_rank'))}`"
            )
        lines.append("")
    lines.extend(
        [
            "Summary:",
            f"- best replacement width: `{_safe_str(summary.get('best_replacement_width'))}`",
            f"- best replacement delta vs reorder floor: `{_safe_float(summary.get('best_replacement_vs_reorder_floor_delta')):.3f}`",
            f"- best replacement delta vs control: `{_safe_float(summary.get('best_replacement_delta_vs_control')):.3f}`",
            f"- best replacement winner changed: `{_safe_int(summary.get('best_replacement_winner_identity_changed'))}`",
        ]
    )
    (output_dir / "phasec_richer_pool_phaseb_replacement_reopen_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_exploration() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    case_dir = output_dir / "case_1111__search7002"
    case_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = REPO_ROOT / SOURCE_ARTIFACT_REL_PATH
    case = resume_mod.load_artifact_case(artifact_path=artifact_path)
    saved_rows = exact_mod._load_saved_start_rows(case.artifact)
    candidate_pool_rows = _load_saved_candidate_pool_rows(case.artifact)
    if not saved_rows:
        raise ValueError("No saved Phase-C start rows were found in richer-pool source artifact")
    if not candidate_pool_rows:
        raise ValueError("No saved Phase-C candidate-pool rows were found in richer-pool source artifact")

    total_units = 1 + sum(1 for _name, _group, _width, builder in POLICY_SPECS if builder is not None)
    completed_units = 0
    started_at = monotonic()
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} "
        f"output_dir={_relative_path(output_dir)} "
        f"units={total_units} "
        f"question=\"{QUESTION}\" "
        f"suspicion=\"{SUSPICION}\" "
        f"alternative=\"{ALTERNATIVE}\""
    )
    _print_progress(
        "decision_contract "
        f"if_suspicion=\"{EXPECT_IF_SUSPICION}\" "
        f"if_alternative=\"{EXPECT_IF_ALTERNATIVE}\" "
        f"decision_rule=\"{DECISION_RULE}\""
    )

    control_started_at = monotonic()
    control_summary = exact_mod.run_saved_surface_phasec_replay(
        case=case,
        saved_rows=saved_rows,
        replay_label="saved_surface_control",
    )
    completed_units += 1
    elapsed = monotonic() - started_at
    eta_seconds = (elapsed / completed_units) * (total_units - completed_units)
    _print_progress(
        "control_finished "
        f"unit={completed_units}/{total_units} "
        f"candidate={_safe_float(control_summary.get('best_match_ratio')):.3f} "
        f"elapsed={_format_duration(elapsed)} "
        f"eta={_format_duration(eta_seconds)} "
        f"unit_runtime={_format_duration(monotonic() - control_started_at)}"
    )

    control_case_summary = _clone_control_summary(control_summary)
    control_comparison_summary = _build_control_comparison_summary(
        case=case,
        control_summary=control_summary,
    )
    control_diagnostics = phaseb_mass_mod.build_surface_diagnostics(
        control_summary=control_summary,
        candidate_summary=control_case_summary,
        comparison_summary=control_comparison_summary,
        candidate_rows=saved_rows,
        policy_group="control",
    )
    rows = [
        _build_row(
            policy_name=CONTROL_POLICY_NAME,
            policy_group="control",
            requested_width="",
            case=case,
            comparison_summary=control_comparison_summary,
            diagnostics=control_diagnostics,
        )
    ]
    _write_json(case_dir / f"{CONTROL_POLICY_NAME}__candidate_saved_surface_summary.json", control_case_summary)
    _write_json(case_dir / f"{CONTROL_POLICY_NAME}__comparison_summary.json", control_comparison_summary)

    for policy_name, policy_group, requested_width, builder in POLICY_SPECS:
        if builder is None:
            continue
        unit_started_at = monotonic()
        candidate_rows = builder(saved_rows, candidate_pool_rows)
        candidate_summary = exact_mod.run_saved_surface_phasec_replay(
            case=case,
            saved_rows=candidate_rows,
            replay_label=policy_name,
        )
        comparison_summary = exact_mod.build_comparison_summary(
            case=case,
            control_summary=control_summary,
            candidate_summary=candidate_summary,
        )
        diagnostics_policy_group = (
            phaseb_mass_mod.PHASEB_TOPK_ONLY_REPLACEMENT_POLICY_GROUP
            if policy_group == "replacement"
            else policy_group
        )
        diagnostics = phaseb_mass_mod.build_surface_diagnostics(
            control_summary=control_summary,
            candidate_summary=candidate_summary,
            comparison_summary=comparison_summary,
            candidate_rows=candidate_rows,
            policy_group=diagnostics_policy_group,
        )
        rows.append(
            _build_row(
                policy_name=policy_name,
                policy_group=policy_group,
                requested_width=requested_width,
                case=case,
                comparison_summary=comparison_summary,
                diagnostics=diagnostics,
            )
        )
        _write_json(case_dir / f"{policy_name}__candidate_saved_surface_summary.json", candidate_summary)
        _write_json(case_dir / f"{policy_name}__comparison_summary.json", comparison_summary)
        completed_units += 1
        elapsed = monotonic() - started_at
        eta_seconds = (elapsed / completed_units) * (total_units - completed_units)
        _print_progress(
            "policy_finished "
            f"unit={completed_units}/{total_units} "
            f"policy={policy_name} "
            f"delta={_safe_float(comparison_summary.get('candidate_minus_control_best_match_ratio')):.3f} "
            f"winner_changed={_safe_int(diagnostics.get('winner_identity_changed'))} "
            f"elapsed={_format_duration(elapsed)} "
            f"eta={_format_duration(eta_seconds)} "
            f"unit_runtime={_format_duration(monotonic() - unit_started_at)}"
        )

    rows = _annotate_vs_reorder_floor(rows)
    rows = sorted(
        rows,
        key=lambda row: (
            _safe_str(row.get("policy_group")),
            _safe_str(row.get("requested_width")),
            _safe_str(row.get("policy_name")),
        ),
    )
    summary = build_summary(rows)
    recommendation = build_recommendation(rows)
    summary = {
        **summary,
        "output_dir": _relative_path(output_dir),
        "source_artifact_relpath": SOURCE_ARTIFACT_REL_PATH.as_posix(),
        "recommendation": dict(recommendation),
    }

    _write_jsonl(output_dir / "phasec_richer_pool_phaseb_replacement_reopen_rows.jsonl", rows)
    _write_csv(output_dir / "phasec_richer_pool_phaseb_replacement_reopen_rows.csv", rows)
    _write_json(output_dir / "phasec_richer_pool_phaseb_replacement_reopen_summary.json", summary)
    _write_json(output_dir / "phasec_richer_pool_phaseb_replacement_reopen_recommendation.json", recommendation)
    write_markdown(output_dir, rows=rows, summary=summary, recommendation=recommendation)
    run_summary = {
        "output_dir": _relative_path(output_dir),
        "fixture_seed": _safe_int(case.artifact.get("instance_source_key_seed")),
        "search_seed": _safe_int(case.artifact.get("search_seed")),
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
