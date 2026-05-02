from __future__ import annotations

import csv
import json
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
        "extract_stage3_entry_const_local_depth_handoff_activation_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


RUN_LABEL = "stage3_entry_const_local_depth_handoff_activation_v1"
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

CONST_LOCAL_DEPTH_RUN_CONFIG_OVERRIDE = {
    "stage3": {
        "period_scaling": {
            "init_keys_cap": 288,
        },
        "entry": {
            "allocation_policy": "constant_local_depth",
            "mutations_per_promoted": 1,
        },
    },
}


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


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


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(dict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([dict(row) for row in rows])


def _run_dir_from_handoff_root(handoff_root: Path) -> Path:
    marker = handoff_root.parts.index("resume_handoffs")
    return Path(*handoff_root.parts[:marker])


def _artifact_path_from_handoff(handoff_root: Path) -> Path:
    manifest = _read_json(handoff_root / "manifest.json")
    artifact_relpath = _safe_str(manifest.get("artifact_relpath"))
    if artifact_relpath:
        artifact_path = REPO_ROOT / artifact_relpath
        if artifact_path.exists():
            return artifact_path
    return _run_dir_from_handoff_root(handoff_root) / "best" / "best_instance.json"


def _key_tuples(prep: Mapping[str, Any]) -> list[tuple[int, ...]]:
    return [
        tuple(int(x) for x in key_vals)
        for key_vals in list(prep.get("init3", []) or [])
    ]


def _overlap_counts(
    legacy_prep: Mapping[str, Any],
    candidate_prep: Mapping[str, Any],
) -> dict[str, int]:
    legacy_keys = _key_tuples(legacy_prep)
    candidate_keys = _key_tuples(candidate_prep)
    legacy_set = set(legacy_keys)
    candidate_set = set(candidate_keys)
    overlap = legacy_set & candidate_set
    return {
        "legacy_unique_init3_keys": len(legacy_set),
        "candidate_unique_init3_keys": len(candidate_set),
        "shared_init3_keys": len(overlap),
        "candidate_new_init3_keys": len(candidate_set - legacy_set),
        "candidate_missing_legacy_init3_keys": len(legacy_set - candidate_set),
    }


def _phase_cfg_fingerprint(prep: Mapping[str, Any], field: str) -> str:
    return json.dumps(dict(prep.get(field, {}) or {}), sort_keys=True)


def build_activation_row(target: Mapping[str, Any]) -> dict[str, Any]:
    handoff_root = REPO_ROOT / _safe_str(target.get("handoff_root"))
    run_dir = _run_dir_from_handoff_root(handoff_root)
    artifact_path = _artifact_path_from_handoff(handoff_root)
    run_config = _read_json(run_dir / "run_config.json")
    artifact = _read_json(artifact_path)
    saved_stage2_resume = _read_json(handoff_root / "stage2_resume.json")
    saved_stage3_prep = _read_json(handoff_root / "stage3_prep.json")
    stage2_resume = resume_mod._coerce_stage2_resume_inputs(saved_stage2_resume)
    candidate_run_config = resume_mod._deep_merge_mapping(
        run_config,
        CONST_LOCAL_DEPTH_RUN_CONFIG_OVERRIDE,
    )
    candidate_stage3_prep = resume_mod._build_stage3_prep_from_stage2_resume(
        resume=stage2_resume,
        artifact=artifact,
        run_config=candidate_run_config,
    )
    overlap = _overlap_counts(saved_stage3_prep, candidate_stage3_prep)
    legacy_init3_n = _safe_int(saved_stage3_prep.get("init3_n"))
    candidate_init3_n = _safe_int(candidate_stage3_prep.get("init3_n"))
    legacy_target_before_cap = _safe_int(
        saved_stage3_prep.get("stage3_entry_target_before_cap")
    )
    candidate_target_before_cap = _safe_int(
        candidate_stage3_prep.get("stage3_entry_target_before_cap")
    )
    phasea_same = int(
        _phase_cfg_fingerprint(saved_stage3_prep, "stage3_phaseA_cfg")
        == _phase_cfg_fingerprint(candidate_stage3_prep, "stage3_phaseA_cfg")
    )
    phaseb_same = int(
        _phase_cfg_fingerprint(saved_stage3_prep, "stage3_phaseB_cfg")
        == _phase_cfg_fingerprint(candidate_stage3_prep, "stage3_phaseB_cfg")
    )
    structural_activation = int(
        candidate_init3_n != legacy_init3_n
        or candidate_target_before_cap != legacy_target_before_cap
        or int(overlap["candidate_new_init3_keys"]) > 0
    )
    mechanism_widened = int(candidate_init3_n > legacy_init3_n)
    return {
        "run_label": RUN_LABEL,
        "target_role": _safe_str(target.get("target_role")),
        "fixture_seed": _safe_int(target.get("fixture_seed")),
        "search_seed": _safe_int(target.get("search_seed")),
        "handoff_root": _repo_rel(handoff_root),
        "run_dir": _repo_rel(run_dir),
        "artifact_relpath": _repo_rel(artifact_path),
        "retained_best_match_ratio": _safe_float(artifact.get("best_match_ratio")),
        "retained_best_stage": _safe_str(artifact.get("best_stage")),
        "legacy_entry_policy": _safe_str(
            saved_stage3_prep.get("stage3_entry_allocation_policy")
        ),
        "candidate_entry_policy": _safe_str(
            candidate_stage3_prep.get("stage3_entry_allocation_policy")
        ),
        "legacy_init3_n": legacy_init3_n,
        "candidate_init3_n": candidate_init3_n,
        "init3_n_delta": candidate_init3_n - legacy_init3_n,
        "legacy_entry_base_budget": _safe_int(
            saved_stage3_prep.get("stage3_entry_base_budget")
        ),
        "candidate_entry_base_budget": _safe_int(
            candidate_stage3_prep.get("stage3_entry_base_budget")
        ),
        "legacy_entry_target_before_cap": legacy_target_before_cap,
        "candidate_entry_target_before_cap": candidate_target_before_cap,
        "entry_target_before_cap_delta": (
            candidate_target_before_cap - legacy_target_before_cap
        ),
        "legacy_entry_cap": _safe_int(saved_stage3_prep.get("stage3_entry_cap")),
        "candidate_entry_cap": _safe_int(candidate_stage3_prep.get("stage3_entry_cap")),
        "legacy_cap_applied": int(
            1 if bool(saved_stage3_prep.get("stage3_entry_cap_applied")) else 0
        ),
        "candidate_cap_applied": int(
            1 if bool(candidate_stage3_prep.get("stage3_entry_cap_applied")) else 0
        ),
        "legacy_promoted_keys_count": _safe_int(
            saved_stage3_prep.get("stage3_promoted_keys_count")
        ),
        "candidate_promoted_keys_count": _safe_int(
            candidate_stage3_prep.get("stage3_promoted_keys_count")
        ),
        "legacy_mutations_per_promoted": _safe_int(
            saved_stage3_prep.get("stage3_entry_mutations_per_promoted_cfg")
        ),
        "candidate_mutations_per_promoted": _safe_int(
            candidate_stage3_prep.get("stage3_entry_mutations_per_promoted_cfg")
        ),
        "legacy_mutation_calls_per_promoted": _safe_int(
            saved_stage3_prep.get("stage3_entry_mutation_calls_per_promoted")
        ),
        "candidate_mutation_calls_per_promoted": _safe_int(
            candidate_stage3_prep.get("stage3_entry_mutation_calls_per_promoted")
        ),
        **overlap,
        "phasea_cfg_same": phasea_same,
        "phaseb_cfg_same": phaseb_same,
        "stage3_phaseb_top_n_same": int(
            _safe_int(saved_stage3_prep.get("stage3_phaseB_top_n"))
            == _safe_int(candidate_stage3_prep.get("stage3_phaseB_top_n"))
        ),
        "structural_activation": structural_activation,
        "mechanism_widened": mechanism_widened,
        "runtime_launched": 0,
        "interpretation": (
            "candidate_changes_entry_surface"
            if structural_activation
            else "candidate_structurally_inert"
        ),
    }


def build_readout(rows: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> str:
    lines = [
        "# Stage3 Entry Constant-Local-Depth Handoff Activation v1",
        "",
        "Question:",
        "",
        "- before any runtime, does constant-local-depth materially change the",
        "  Stage-3 entry surface when rebuilt from saved handoff artefacts?",
        "",
        "Coverage:",
        "",
        f"- target rows: `{summary['target_count']}`",
        f"- structurally active rows: `{summary['structurally_active_count']}`",
        f"- mechanism-widened rows: `{summary['mechanism_widened_count']}`",
        f"- runtime launched: `{summary['runtime_launched']}`",
        "",
        "Rows:",
        "",
        "| case | retained | legacy policy | candidate policy | legacy init3 | candidate init3 | delta | new keys | missing legacy keys | active |",
        "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| `{fixture_seed}/search{search_seed}` | `{retained_best_match_ratio:.3f}` | "
            "`{legacy_entry_policy}` | `{candidate_entry_policy}` | "
            "`{legacy_init3_n}` | `{candidate_init3_n}` | `{init3_n_delta}` | "
            "`{candidate_new_init3_keys}` | `{candidate_missing_legacy_init3_keys}` | "
            "`{structural_activation}` |".format(**row)
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            f"- `{summary['interpretation']}`",
            "",
            "Recommended Next:",
            "",
            f"- `{summary['recommended_next']}`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_extract() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    rows = [build_activation_row(target) for target in TARGETS]
    active_count = sum(int(row["structural_activation"]) for row in rows)
    widened_count = sum(int(row["mechanism_widened"]) for row in rows)
    if active_count == 0:
        interpretation = "constant_local_depth_is_structurally_inert_on_handoffs"
        recommended_next = "close_constant_local_depth_handoff_runtime"
    elif widened_count == 0:
        interpretation = "constant_local_depth_changes_surface_without_widening"
        recommended_next = "inspect_changed_keys_before_any_runtime"
    else:
        interpretation = "constant_local_depth_structurally_active"
        recommended_next = "write_one_cell_late_stage_runtime_design_before_launch"
    summary = {
        "run_label": RUN_LABEL,
        "status": "completed",
        "output_dir": _repo_rel(output_dir),
        "target_count": len(rows),
        "structurally_active_count": active_count,
        "mechanism_widened_count": widened_count,
        "runtime_launched": 0,
        "run_config_override": CONST_LOCAL_DEPTH_RUN_CONFIG_OVERRIDE,
        "interpretation": interpretation,
        "recommended_next": recommended_next,
        "updated_utc": _utc_now_text(),
    }
    _write_csv(output_dir / "stage3_entry_const_local_depth_activation_rows.csv", rows)
    _write_json(
        output_dir / "stage3_entry_const_local_depth_activation_summary.json",
        summary,
    )
    (output_dir / "stage3_entry_const_local_depth_activation_readout.md").write_text(
        build_readout(rows, summary),
        encoding="utf-8",
    )
    _write_json(output_dir / "run_summary.json", summary)
    return summary


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
