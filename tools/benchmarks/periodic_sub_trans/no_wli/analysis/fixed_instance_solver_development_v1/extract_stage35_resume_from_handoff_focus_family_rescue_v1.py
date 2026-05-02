from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_stage35_resume_from_handoff_focus_family_rescue_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


RUN_LABEL = "stage35_resume_from_handoff_focus_family_rescue_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)

TARGETS: tuple[dict[str, Any], ...] = (
    {
        "target_role": "primary_selector_rescue_headroom",
        "fixture_seed": 1111,
        "search_seed": 7005,
        "handoff_root": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260412T053512632846Z__bench_solve_pipeline_no_wli__9557c0f/"
            "resume_handoffs/"
            "fixture_001__p9_c3_l1000__text0__seed1111__search7005"
        ),
    },
    {
        "target_role": "secondary_fragmentation_target",
        "fixture_seed": 1111,
        "search_seed": 7004,
        "handoff_root": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260412T031328680128Z__bench_solve_pipeline_no_wli__9557c0f/"
            "resume_handoffs/"
            "fixture_001__p9_c3_l1000__text0__seed1111__search7004"
        ),
    },
    {
        "target_role": "control_proof_of_runner",
        "fixture_seed": 1111,
        "search_seed": 7002,
        "handoff_root": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260428T035424021944Z__bench_solve_pipeline_no_wli__ee62083/"
            "resume_handoffs/"
            "fixture_001__p9_c3_l1000__text0__seed1111__search7002"
        ),
    },
)

REQUIRED_HANDOFF_FILES = (
    "manifest.json",
    "stage2_resume.json",
    "stage3_prep.json",
    "stage35_seed_archive.json",
)


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if result != result:
        return float(default)
    return result


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return str(default)
    return str(value)


def _format_counts(values: list[str]) -> str:
    counts = Counter(value for value in values if value)
    return ";".join(f"{key}:{counts[key]}" for key in sorted(counts))


def _run_dir_from_handoff_root(handoff_root: Path) -> Path:
    marker = handoff_root.parts.index("resume_handoffs")
    return Path(*handoff_root.parts[:marker])


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return _read_json(path)
    except Exception:
        return {}


def build_inventory_row(target: dict[str, Any]) -> dict[str, Any]:
    handoff_root = REPO_ROOT / str(target["handoff_root"])
    files_present = {
        name: int((handoff_root / name).exists()) for name in REQUIRED_HANDOFF_FILES
    }
    missing = [name for name, present in files_present.items() if not present]

    manifest = _load_optional_json(handoff_root / "manifest.json")
    stage3_prep = _load_optional_json(handoff_root / "stage3_prep.json")
    stage35_archive = _load_optional_json(handoff_root / "stage35_seed_archive.json")

    run_dir = _run_dir_from_handoff_root(handoff_root)
    artifact_path = REPO_ROOT / _safe_str(manifest.get("artifact_relpath"))
    if not artifact_path.exists():
        artifact_path = run_dir / "best" / "best_instance.json"
    artifact = _load_optional_json(artifact_path)
    run_manifest = _load_optional_json(run_dir / "run_manifest.json")
    run_config = _load_optional_json(run_dir / "run_config.json")

    seed_rows = list(stage35_archive.get("seed_rows") or [])
    candidate_hashes = [
        _safe_str(row.get("candidate_hash"))
        for row in seed_rows
        if isinstance(row, dict)
    ]
    seed_sources = [
        _safe_str(row.get("seed_source"))
        for row in seed_rows
        if isinstance(row, dict)
    ]
    lanes = [
        _safe_str(row.get("lane"))
        for row in seed_rows
        if isinstance(row, dict)
    ]

    stage3_entry = run_config.get("stage3", {}).get("entry", {})
    period_scaling = run_config.get("stage3", {}).get("period_scaling", {})

    all_files_present = int(all(files_present.values()))
    archive_seed_rows = len(seed_rows)
    late_stage_only_feasible = int(all_files_present and archive_seed_rows > 0)

    return {
        "target_role": _safe_str(target.get("target_role")),
        "fixture_seed": _safe_int(target.get("fixture_seed")),
        "search_seed": _safe_int(target.get("search_seed")),
        "handoff_root": _relative_path(handoff_root),
        "run_dir": _relative_path(run_dir),
        "all_required_files_present": all_files_present,
        "missing_required_files": ";".join(missing),
        "stage2_to_stage3_saved": _safe_int(
            manifest.get("stage2_to_stage3", {}).get("saved")
        ),
        "stage3_to_stage35_saved": _safe_int(
            manifest.get("stage3_to_stage35", {}).get("saved")
        ),
        "manifest_seed_count": _safe_int(
            manifest.get("stage3_to_stage35", {}).get("seed_count")
        ),
        "archive_seed_rows": archive_seed_rows,
        "archive_unique_candidate_hashes": len(set(candidate_hashes)),
        "archive_seed_source_counts": _format_counts(seed_sources),
        "archive_lane_counts": _format_counts(lanes),
        "stage3_init3_count": _safe_int(stage3_prep.get("init3_n")),
        "stage3_promoted_keys_count": _safe_int(
            stage3_prep.get("stage3_promoted_keys_count")
        ),
        "stage3_entry_allocation_policy": _safe_str(
            stage3_prep.get("stage3_entry_allocation_policy")
            or stage3_entry.get("allocation_policy")
        ),
        "stage3_entry_cap": _safe_int(
            stage3_prep.get("stage3_entry_cap")
            or period_scaling.get("init_keys_cap")
        ),
        "stage3_entry_mutations_per_promoted": _safe_int(
            stage3_prep.get("stage3_entry_mutations_per_promoted_cfg")
            or stage3_entry.get("mutations_per_promoted")
        ),
        "retained_best_match_ratio": _safe_float(artifact.get("best_match_ratio")),
        "retained_best_stage": _safe_str(artifact.get("best_stage")),
        "retained_status": _safe_str(artifact.get("status")),
        "retained_total_seconds": _safe_float(
            artifact.get("total_seconds") or run_manifest.get("elapsed_seconds")
        ),
        "run_id": _safe_str(run_manifest.get("run_id") or run_dir.name),
        "git_dirty": _safe_int(run_manifest.get("git", {}).get("dirty")),
        "late_stage_only_feasible": late_stage_only_feasible,
        "next_step": (
            "eligible_for_static_archive_design"
            if late_stage_only_feasible
            else "blocked_missing_inputs"
        ),
    }


def build_archive_seed_rows(target: dict[str, Any]) -> list[dict[str, Any]]:
    handoff_root = REPO_ROOT / str(target["handoff_root"])
    stage35_archive = _load_optional_json(handoff_root / "stage35_seed_archive.json")
    rows = []
    for row in list(stage35_archive.get("seed_rows") or []):
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "target_role": _safe_str(target.get("target_role")),
                "fixture_seed": _safe_int(target.get("fixture_seed")),
                "search_seed": _safe_int(target.get("search_seed")),
                "candidate_hash": _safe_str(row.get("candidate_hash")),
                "seed_source": _safe_str(row.get("seed_source")),
                "lane": _safe_str(row.get("lane")),
                "source_rank": _safe_int(row.get("source_rank"), -1),
                "stage3_rank": _safe_int(row.get("stage3_rank"), -1),
                "seed_priority_group": _safe_int(row.get("seed_priority_group"), -1),
                "seed_priority_rank": _safe_int(row.get("seed_priority_rank"), -1),
                "checkpoint_final_match": _safe_float(
                    row.get("checkpoint_final_match"), 0.0
                ),
                "checkpoint_final_score": _safe_float(
                    row.get("checkpoint_final_score"), 0.0
                ),
                "checkpoint_rescue_applied": _safe_int(
                    row.get("checkpoint_rescue_applied")
                ),
            }
        )
    return rows


def _target_artifact_path(target: dict[str, Any]) -> Path:
    handoff_root = REPO_ROOT / str(target["handoff_root"])
    manifest = _load_optional_json(handoff_root / "manifest.json")
    artifact_relpath = _safe_str(manifest.get("artifact_relpath"))
    if artifact_relpath:
        artifact_path = REPO_ROOT / artifact_relpath
        if artifact_path.exists():
            return artifact_path
    return _run_dir_from_handoff_root(handoff_root) / "best" / "best_instance.json"


def _phasec_rows_by_hash(case: Any) -> dict[str, dict[str, Any]]:
    rows = resume_mod.load_phasec_frontier_rows(
        artifact_path=case.artifact_path,
        artifact=case.artifact,
    )
    by_hash: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_d = dict(row)
        for field in ("candidate_hash", "end_hash", "start_hash"):
            candidate_hash = _safe_str(row_d.get(field))
            if candidate_hash and candidate_hash not in by_hash:
                by_hash[candidate_hash] = row_d
    return by_hash


def _artifact_final_best_selected_row(
    *,
    artifact: dict[str, Any],
    candidate_hash: str,
) -> dict[str, Any]:
    return {
        "selector": "legacy",
        "candidate_hash": candidate_hash,
        "source": "final_best",
        "lane": _safe_str(
            dict(artifact.get("stage3_diagnostics", {}) or {}).get(
                "phaseC_final_winner_lane"
            )
        ),
        "final_key_idx": list(artifact.get("final_best_key_idx", []) or []),
        "final_plaintext_idx": list(
            artifact.get("final_best_plaintext_idx", []) or []
        ),
        "final_score": _safe_float(artifact.get("best_score")),
        "final_match": _safe_float(artifact.get("best_match_ratio")),
    }


def build_selected_candidate_material_rows(
    target: dict[str, Any],
    archive_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    artifact_path = _target_artifact_path(target)
    case = resume_mod.load_artifact_case(artifact_path=artifact_path)
    artifact = dict(case.artifact)
    frontier_by_hash = _phasec_rows_by_hash(case)
    rows = []
    for archive_row in archive_rows:
        candidate_hash = _safe_str(archive_row.get("candidate_hash"))
        seed_source = _safe_str(archive_row.get("seed_source"))
        if seed_source == "final_best":
            selected_row = _artifact_final_best_selected_row(
                artifact=artifact,
                candidate_hash=candidate_hash,
            )
            material_source = "artifact_final_best"
        else:
            selected_row = dict(frontier_by_hash.get(candidate_hash, {}))
            selected_row.setdefault("selector", "score_plus_novelty")
            material_source = "phasec_frontier_or_checkpoint"

        final_key = list(selected_row.get("final_key_idx", []) or [])
        final_plaintext = list(selected_row.get("final_plaintext_idx", []) or [])
        final_match = _safe_float(
            selected_row.get("final_match")
            or selected_row.get("match_final")
            or archive_row.get("checkpoint_final_match")
        )
        final_score = _safe_float(
            selected_row.get("final_score")
            or selected_row.get("score_final")
            or archive_row.get("checkpoint_final_score")
        )
        material_complete = int(bool(final_key) and bool(final_plaintext))
        rows.append(
            {
                "target_role": _safe_str(target.get("target_role")),
                "fixture_seed": _safe_int(target.get("fixture_seed")),
                "search_seed": _safe_int(target.get("search_seed")),
                "candidate_hash": candidate_hash,
                "archive_seed_source": seed_source,
                "archive_lane": _safe_str(archive_row.get("lane")),
                "archive_checkpoint_match": _safe_float(
                    archive_row.get("checkpoint_final_match")
                ),
                "material_source": material_source,
                "frontier_row_found": int(bool(selected_row)),
                "selected_source": _safe_str(selected_row.get("source") or seed_source),
                "selected_lane": _safe_str(selected_row.get("lane")),
                "selected_final_match": final_match,
                "selected_final_score": final_score,
                "selected_selector": _safe_str(
                    selected_row.get("selector") or "score_plus_novelty"
                ),
                "final_key_len": len(final_key),
                "final_plaintext_len": len(final_plaintext),
                "selected_row_material_complete": material_complete,
                "late_stage_entry": "run_stage35_from_selected_trial_row",
                "partial_outputs_supported": 1,
            }
        )
    return rows


def build_runner_design_rows(
    inventory_rows: list[dict[str, Any]],
    material_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    material_by_search: dict[int, list[dict[str, Any]]] = {}
    for row in material_rows:
        material_by_search.setdefault(int(row["search_seed"]), []).append(row)

    rows = []
    for inventory in inventory_rows:
        search_seed = int(inventory["search_seed"])
        retained_best = float(inventory["retained_best_match_ratio"])
        members = material_by_search.get(search_seed, [])
        complete_members = [
            row for row in members if int(row["selected_row_material_complete"])
        ]
        final_best_rows = [
            row
            for row in complete_members
            if str(row["archive_seed_source"]) == "final_best"
        ]
        challenger_rows = [
            row
            for row in complete_members
            if str(row["archive_seed_source"]) != "final_best"
        ]
        best_selected = max(
            challenger_rows,
            key=lambda row: float(row["selected_final_match"]),
            default={},
        )
        best_selected_match = _safe_float(best_selected.get("selected_final_match"))
        selected_minus_retained = best_selected_match - retained_best
        control_row = final_best_rows[0] if final_best_rows else {}
        rows.append(
            {
                "target_role": inventory["target_role"],
                "fixture_seed": inventory["fixture_seed"],
                "search_seed": search_seed,
                "retained_best_match_ratio": retained_best,
                "complete_selected_rows": len(complete_members),
                "control_candidate_hash": _safe_str(control_row.get("candidate_hash")),
                "control_selected_match": _safe_float(
                    control_row.get("selected_final_match")
                ),
                "best_selected_candidate_hash": _safe_str(
                    best_selected.get("candidate_hash")
                ),
                "best_selected_source": _safe_str(best_selected.get("selected_source")),
                "best_selected_lane": _safe_str(best_selected.get("selected_lane")),
                "best_selected_match": best_selected_match,
                "best_selected_minus_retained": selected_minus_retained,
                "entry_function": "artifact_resume.run_stage35_from_selected_trial_row",
                "requires_upstream_recompute": 0,
                "partial_outputs_supported": 1,
                "runtime_status": "not_launched",
                "recommended_next_unit": (
                    "selected_best_frontier_micro_canary"
                    if selected_minus_retained > 0.0
                    else "control_replay_or_hold"
                ),
            }
        )
    return rows


def build_design_rows(
    inventory_rows: list[dict[str, Any]],
    archive_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows_by_search: dict[int, list[dict[str, Any]]] = {}
    for row in archive_rows:
        rows_by_search.setdefault(int(row["search_seed"]), []).append(row)

    design_rows = []
    for inventory in inventory_rows:
        search_seed = int(inventory["search_seed"])
        members = rows_by_search.get(search_seed, [])
        checkpoint_members = [
            row for row in members if float(row["checkpoint_final_match"]) > 0.0
        ]
        best_checkpoint = max(
            checkpoint_members,
            key=lambda row: float(row["checkpoint_final_match"]),
            default={},
        )
        best_checkpoint_match = _safe_float(
            best_checkpoint.get("checkpoint_final_match")
        )
        retained_best = float(inventory["retained_best_match_ratio"])
        headroom = best_checkpoint_match - retained_best
        if search_seed == 7005 and headroom > 0.0:
            recommended_variant = "focus_or_dominant_challenger_rescue_first"
        elif search_seed == 7004:
            recommended_variant = "fragmentation_static_audit_before_runtime"
        else:
            recommended_variant = "control_archive_replay_only"
        design_rows.append(
            {
                "target_role": inventory["target_role"],
                "fixture_seed": inventory["fixture_seed"],
                "search_seed": search_seed,
                "retained_best_match_ratio": retained_best,
                "archive_seed_rows": inventory["archive_seed_rows"],
                "checkpoint_seed_rows": len(checkpoint_members),
                "best_checkpoint_candidate_hash": _safe_str(
                    best_checkpoint.get("candidate_hash")
                ),
                "best_checkpoint_seed_source": _safe_str(
                    best_checkpoint.get("seed_source")
                ),
                "best_checkpoint_lane": _safe_str(best_checkpoint.get("lane")),
                "best_checkpoint_match": best_checkpoint_match,
                "best_checkpoint_minus_retained": headroom,
                "recommended_static_variant": recommended_variant,
            }
        )
    return design_rows


def build_readout(
    rows: list[dict[str, Any]],
    design_rows: list[dict[str, Any]],
    runner_design_rows: list[dict[str, Any]],
) -> str:
    feasible_count = sum(int(row["late_stage_only_feasible"]) for row in rows)
    lines = [
        "# Stage35 Resume From Handoff Focus-Family Rescue v1 Inventory",
        "",
        "Purpose:",
        "- inventory retained handoff/archive artefacts before any late-stage-only runtime",
        "- avoid recomputing full pipelines",
        "- keep the next executable unit gated by timing evidence",
        "",
        "Status:",
        f"- target rows: `{len(rows)}`",
        f"- late-stage feasible rows: `{feasible_count}`",
        "",
        "Targets:",
        "",
        "| role | case | files | archive rows | unique hashes | retained match | entry policy | cap | git dirty | next step |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| `{target_role}` | `{fixture_seed}/search{search_seed}` | "
            "`{all_required_files_present}` | `{archive_seed_rows}` | "
            "`{archive_unique_candidate_hashes}` | `{retained_best_match_ratio:.3f}` | "
            "`{stage3_entry_allocation_policy}` | `{stage3_entry_cap}` | "
            "`{git_dirty}` | `{next_step}` |".format(**row)
        )
    lines.extend(
        [
            "",
            "Static design read:",
            "",
            "| case | retained | best checkpoint | delta | recommended variant |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in design_rows:
        lines.append(
            "| `{fixture_seed}/search{search_seed}` | `{retained_best_match_ratio:.3f}` | "
            "`{best_checkpoint_match:.3f}` | `{best_checkpoint_minus_retained:+.3f}` | "
            "`{recommended_static_variant}` |".format(**row)
        )
    lines.extend(
        [
            "",
            "Selected-row runner design:",
            "",
            "| case | retained | best selected row | delta | entry | next unit |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in runner_design_rows:
        lines.append(
            "| `{fixture_seed}/search{search_seed}` | `{retained_best_match_ratio:.3f}` | "
            "`{best_selected_match:.3f}` | `{best_selected_minus_retained:+.3f}` | "
            "`{entry_function}` | `{recommended_next_unit}` |".format(**row)
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- all feasible rows can support static archive design work",
            "- selected-row material is available through the existing Stage 3.5 artifact resume API",
            "- `1111/search7004` still matters as a fragmentation target, but this archive inventory does not show simple checkpoint headroom",
            "- `1111/search7002` remains the control / proof-of-runner target",
            "- this inventory does not launch or approve runtime",
            "- if the next proposed run is expected to take about an hour or more, ask before launching",
            "",
            "Recommended next action:",
            "- inspect the archive rows and design one narrow late-stage-only control/selector comparison",
            "- keep `1111/search7005` first unless static inspection finds its archive unsuitable",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def run_extract() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    rows = [build_inventory_row(target) for target in TARGETS]
    archive_rows = [
        archive_row
        for target in TARGETS
        for archive_row in build_archive_seed_rows(target)
    ]
    design_rows = build_design_rows(rows, archive_rows)
    archive_rows_by_search: dict[int, list[dict[str, Any]]] = {}
    for row in archive_rows:
        archive_rows_by_search.setdefault(int(row["search_seed"]), []).append(row)
    material_rows = [
        material_row
        for target in TARGETS
        for material_row in build_selected_candidate_material_rows(
            target,
            archive_rows_by_search.get(_safe_int(target.get("search_seed")), []),
        )
    ]
    runner_design_rows = build_runner_design_rows(rows, material_rows)
    feasible_count = sum(int(row["late_stage_only_feasible"]) for row in rows)
    all_required_files_present = int(
        all(int(row["all_required_files_present"]) for row in rows)
    )

    _write_csv(output_dir / "stage35_resume_handoff_inventory_rows.csv", rows)
    _write_csv(output_dir / "stage35_resume_archive_seed_rows.csv", archive_rows)
    _write_csv(output_dir / "stage35_resume_static_design_rows.csv", design_rows)
    _write_csv(
        output_dir / "stage35_resume_selected_candidate_material_rows.csv",
        material_rows,
    )
    _write_csv(output_dir / "stage35_resume_runner_design_rows.csv", runner_design_rows)
    _write_json(
        output_dir / "stage35_resume_handoff_inventory_summary.json",
        {
            "run_label": RUN_LABEL,
            "output_dir": _relative_path(output_dir),
            "target_count": len(rows),
            "feasible_count": feasible_count,
            "all_required_files_present": all_required_files_present,
            "runtime_launched": 0,
            "recommendation": (
                "advance_to_static_archive_design"
                if feasible_count == len(rows)
                else "hold_missing_handoff_inputs"
            ),
        },
    )
    (output_dir / "stage35_resume_handoff_inventory_readout.md").write_text(
        build_readout(rows, design_rows, runner_design_rows),
        encoding="utf-8",
    )

    summary = {
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "target_count": len(rows),
        "feasible_count": feasible_count,
        "all_required_files_present": all_required_files_present,
        "runtime_launched": 0,
    }
    _write_json(output_dir / "run_summary.json", summary)
    return summary


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
