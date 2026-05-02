from __future__ import annotations

import csv
import json
import math
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
        "extract_candidate3_saved_surface_exact_matrix_v1.py"
    )


REPO_ROOT = _find_repo_root()
RUN_LABEL = "candidate3_saved_surface_exact_matrix_v1"
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
CONTROL_FIDELITY_STABLE_EPS = 1.0e-9
CONTROL_FIDELITY_NEAR_STABLE_EPS = 0.005000001
CANDIDATE_EFFECT_EPS = 0.001
CASE_BUNDLE_REL_PATHS = (
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T041606Z__candidate3_phasec_saved_surface_exact_remaining_cases_v1/"
        "fixture_611__search7002"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T041606Z__candidate3_phasec_saved_surface_exact_remaining_cases_v1/"
        "fixture_611__search7003"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7002_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7003_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260417T054445Z__candidate3_phasec_saved_surface_exact_1511_search7004_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260417T153047Z__candidate3_phasec_saved_surface_exact_1511_search7005_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260417T055021Z__candidate3_phasec_saved_surface_exact_611_search7004_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260417T152806Z__candidate3_phasec_saved_surface_exact_611_search7001_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T014639Z__candidate3_phasec_saved_surface_exact_611_search7005_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T041606Z__candidate3_phasec_saved_surface_exact_remaining_cases_v1/"
        "fixture_1411__search7001"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T041606Z__candidate3_phasec_saved_surface_exact_remaining_cases_v1/"
        "fixture_1411__search7002"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T041606Z__candidate3_phasec_saved_surface_exact_remaining_cases_v1/"
        "fixture_1411__search7003"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T041606Z__candidate3_phasec_saved_surface_exact_remaining_cases_v1/"
        "fixture_1411__search7004"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T041606Z__candidate3_phasec_saved_surface_exact_remaining_cases_v1/"
        "fixture_1411__search7005"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T010939Z__candidate3_phasec_saved_surface_exact_1111_search7001_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260417T055755Z__candidate3_phasec_saved_surface_exact_1111_search7002_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T011123Z__candidate3_phasec_saved_surface_exact_1111_search7003_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T011226Z__candidate3_phasec_saved_surface_exact_1111_search7004_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T010749Z__candidate3_phasec_saved_surface_exact_1111_search7005_v1"
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


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, default=_json_default))
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
                if isinstance(value, list):
                    payload[key] = "; ".join(str(item) for item in value)
                elif isinstance(value, float) and not math.isfinite(value):
                    payload[key] = ""
                else:
                    payload[key] = value
            writer.writerow(payload)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_control_fidelity(*, control_delta_vs_retained: float) -> str:
    delta = abs(float(control_delta_vs_retained))
    if delta <= float(CONTROL_FIDELITY_STABLE_EPS):
        return "stable"
    if delta <= float(CONTROL_FIDELITY_NEAR_STABLE_EPS):
        return "near_stable"
    return "drifted"


def classify_candidate_effect(*, candidate_minus_control: float) -> str:
    delta = float(candidate_minus_control)
    if delta > float(CANDIDATE_EFFECT_EPS):
        return "positive"
    if delta < -float(CANDIDATE_EFFECT_EPS):
        return "negative"
    return "neutral"


def build_case_row(
    *,
    bundle_rel_path: Path,
    comparison_summary: Mapping[str, Any],
) -> dict[str, Any]:
    control_delta = _safe_float(
        comparison_summary.get("control_delta_vs_retained_stage3_reference")
    )
    candidate_delta = _safe_float(
        comparison_summary.get("candidate_delta_vs_retained_stage3_reference")
    )
    candidate_minus_control = _safe_float(
        comparison_summary.get("candidate_minus_control_best_match_ratio")
    )
    control_fidelity = classify_control_fidelity(
        control_delta_vs_retained=control_delta
    )
    candidate_effect = classify_candidate_effect(
        candidate_minus_control=candidate_minus_control
    )
    usable_decision_gate = int(control_fidelity in {"stable", "near_stable"})
    return {
        "fixture_seed": _safe_int(comparison_summary.get("fixture_seed")),
        "search_seed": _safe_int(comparison_summary.get("search_seed")),
        "bundle_relpath": bundle_rel_path.as_posix(),
        "comparison_summary_relpath": (bundle_rel_path / "comparison_summary.json").as_posix(),
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
        "control_delta_vs_retained_stage3_reference": control_delta,
        "candidate_delta_vs_retained_stage3_reference": candidate_delta,
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
        "control_winner_candidate_hash": _safe_str(
            comparison_summary.get("control_winner_candidate_hash")
        ),
        "candidate_winner_candidate_hash": _safe_str(
            comparison_summary.get("candidate_winner_candidate_hash")
        ),
    }


def build_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    decision_gate_rows = [
        dict(row) for row in rows if _safe_int(row.get("usable_decision_gate")) == 1
    ]
    drifted_rows = [
        dict(row) for row in rows if _safe_int(row.get("usable_decision_gate")) == 0
    ]
    fixture_summary: list[dict[str, Any]] = []
    for fixture_seed in sorted({_safe_int(row.get("fixture_seed")) for row in rows}):
        seed_rows = [
            dict(row)
            for row in rows
            if _safe_int(row.get("fixture_seed")) == int(fixture_seed)
        ]
        fixture_summary.append(
            {
                "fixture_seed": int(fixture_seed),
                "case_count": int(len(seed_rows)),
                "usable_decision_gate_cases": int(
                    sum(
                        1
                        for row in seed_rows
                        if _safe_int(row.get("usable_decision_gate")) == 1
                    )
                ),
                "positive_cases": int(
                    sum(
                        1
                        for row in seed_rows
                        if _safe_str(row.get("decision_gate_read")) == "positive"
                    )
                ),
                "neutral_cases": int(
                    sum(
                        1
                        for row in seed_rows
                        if _safe_str(row.get("decision_gate_read")) == "neutral"
                    )
                ),
                "negative_cases": int(
                    sum(
                        1
                        for row in seed_rows
                        if _safe_str(row.get("decision_gate_read")) == "negative"
                    )
                ),
                "context_only_cases": int(
                    sum(
                        1
                        for row in seed_rows
                        if _safe_str(row.get("decision_gate_read")) == "context_only"
                    )
                ),
            }
        )
    return {
        "run_label": str(RUN_LABEL),
        "case_count": int(len(rows)),
        "usable_decision_gate_cases": int(len(decision_gate_rows)),
        "drifted_context_cases": int(len(drifted_rows)),
        "positive_on_decision_gate": int(
            sum(
                1 for row in decision_gate_rows if _safe_str(row.get("candidate_effect")) == "positive"
            )
        ),
        "neutral_on_decision_gate": int(
            sum(
                1 for row in decision_gate_rows if _safe_str(row.get("candidate_effect")) == "neutral"
            )
        ),
        "negative_on_decision_gate": int(
            sum(
                1 for row in decision_gate_rows if _safe_str(row.get("candidate_effect")) == "negative"
            )
        ),
        "fixture_summary_rows": fixture_summary,
    }


def write_markdown(
    output_dir: Path,
    *,
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> None:
    lines = [
        "# Candidate 3 Saved-Surface Exact Decision Matrix",
        "",
        "Question:",
        "- across the currently completed candidate3 saved-surface exact cases, which lanes are usable decision gates and what do they say?",
        "",
        "Top-line counts:",
        f"- total cases: `{_safe_int(summary.get('case_count'))}`",
        f"- usable decision-gate cases: `{_safe_int(summary.get('usable_decision_gate_cases'))}`",
        f"- drifted context cases: `{_safe_int(summary.get('drifted_context_cases'))}`",
        f"- positive on usable gates: `{_safe_int(summary.get('positive_on_decision_gate'))}`",
        f"- neutral on usable gates: `{_safe_int(summary.get('neutral_on_decision_gate'))}`",
        f"- negative on usable gates: `{_safe_int(summary.get('negative_on_decision_gate'))}`",
        "",
        "Per-case matrix:",
        "",
        "| case | control fidelity | gate usable | control | candidate | delta | read |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}/search{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_str(row.get('control_fidelity_quality'))}` | "
            f"`{_safe_int(row.get('usable_decision_gate'))}` | "
            f"`{_safe_float(row.get('control_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('candidate_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('candidate_minus_control_best_match_ratio')):.3f}` | "
            f"`{_safe_str(row.get('decision_gate_read'))}` |"
        )
    lines.extend(
        [
            "",
            "Per-instance summary:",
            "",
            "| fixture seed | cases | usable gates | positive | neutral | negative | context only |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in list(summary.get("fixture_summary_rows", []) or []):
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}` | "
            f"`{_safe_int(row.get('case_count'))}` | "
            f"`{_safe_int(row.get('usable_decision_gate_cases'))}` | "
            f"`{_safe_int(row.get('positive_cases'))}` | "
            f"`{_safe_int(row.get('neutral_cases'))}` | "
            f"`{_safe_int(row.get('negative_cases'))}` | "
            f"`{_safe_int(row.get('context_only_cases'))}` |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- usable decision gates are stable or near-stable saved-surface exact lanes only",
            "- drifted cases stay in the matrix as context, but they do not count as clean utility reads",
            "- candidate3 currently reads as narrow and case-dependent rather than panel-general",
        ]
    )
    (output_dir / "candidate3_saved_surface_exact_matrix.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_extract() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    bundle_paths = [REPO_ROOT / rel_path for rel_path in CASE_BUNDLE_REL_PATHS]
    missing = [path for path in bundle_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing candidate3 exact bundle inputs: "
            + ", ".join(_relative_path(path) for path in missing)
        )

    rows = [
        build_case_row(
            bundle_rel_path=rel_path,
            comparison_summary=_load_json(REPO_ROOT / rel_path / "comparison_summary.json"),
        )
        for rel_path in CASE_BUNDLE_REL_PATHS
    ]
    rows = sorted(
        rows,
        key=lambda row: (_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed"))),
    )
    summary = build_summary(rows)
    summary = {
        **summary,
        "source_bundle_relpaths": [path.as_posix() for path in CASE_BUNDLE_REL_PATHS],
        "output_dir": _relative_path(output_dir),
    }

    _write_jsonl(output_dir / "candidate3_saved_surface_exact_matrix.jsonl", rows)
    _write_csv(output_dir / "candidate3_saved_surface_exact_matrix.csv", rows)
    _write_json(output_dir / "candidate3_saved_surface_exact_matrix_summary.json", summary)
    write_markdown(output_dir, rows=rows, summary=summary)

    run_summary = {
        "output_dir": _relative_path(output_dir),
        "case_count": _safe_int(summary.get("case_count")),
        "usable_decision_gate_cases": _safe_int(summary.get("usable_decision_gate_cases")),
        "positive_on_decision_gate": _safe_int(summary.get("positive_on_decision_gate")),
        "neutral_on_decision_gate": _safe_int(summary.get("neutral_on_decision_gate")),
        "negative_on_decision_gate": _safe_int(summary.get("negative_on_decision_gate")),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
