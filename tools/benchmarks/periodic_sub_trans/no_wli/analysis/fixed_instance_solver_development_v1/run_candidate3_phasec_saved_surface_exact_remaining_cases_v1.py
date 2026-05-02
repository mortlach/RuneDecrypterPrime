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
        "run_candidate3_phasec_saved_surface_exact_remaining_cases_v1.py"
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


RUN_LABEL = "candidate3_phasec_saved_surface_exact_remaining_cases_v1"
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
CASE_SPECS = (
    {
        "fixture_seed": 611,
        "search_seed": 7002,
        "artifact_relpath": Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260409T121929535534Z__bench_solve_pipeline_no_wli__e52cb46/"
            "final_instances/fixture_001__p9_c3_l1000__text0__seed611__search7002.json"
        ),
    },
    {
        "fixture_seed": 611,
        "search_seed": 7003,
        "artifact_relpath": Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260409T190839986494Z__bench_solve_pipeline_no_wli__e52cb46/"
            "final_instances/fixture_001__p9_c3_l1000__text0__seed611__search7003.json"
        ),
    },
    {
        "fixture_seed": 1411,
        "search_seed": 7001,
        "artifact_relpath": Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260412T223757030076Z__bench_solve_pipeline_no_wli__9557c0f/"
            "final_instances/fixture_001__p9_c3_l1000__text0__seed1411__search7001.json"
        ),
    },
    {
        "fixture_seed": 1411,
        "search_seed": 7002,
        "artifact_relpath": Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260413T022821149962Z__bench_solve_pipeline_no_wli__9557c0f/"
            "final_instances/fixture_001__p9_c3_l1000__text0__seed1411__search7002.json"
        ),
    },
    {
        "fixture_seed": 1411,
        "search_seed": 7003,
        "artifact_relpath": Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260413T065825378729Z__bench_solve_pipeline_no_wli__9557c0f/"
            "final_instances/fixture_001__p9_c3_l1000__text0__seed1411__search7003.json"
        ),
    },
    {
        "fixture_seed": 1411,
        "search_seed": 7004,
        "artifact_relpath": Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260413T103306896547Z__bench_solve_pipeline_no_wli__9557c0f/"
            "final_instances/fixture_001__p9_c3_l1000__text0__seed1411__search7004.json"
        ),
    },
    {
        "fixture_seed": 1411,
        "search_seed": 7005,
        "artifact_relpath": Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260413T141931797018Z__bench_solve_pipeline_no_wli__9557c0f/"
            "final_instances/fixture_001__p9_c3_l1000__text0__seed1411__search7005.json"
        ),
    },
)


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


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
                if isinstance(value, float) and value != value:
                    payload[key] = ""
                else:
                    payload[key] = value
            writer.writerow(payload)


def _build_case_row(
    *,
    case_dir: Path,
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
    control_fidelity = matrix_mod.classify_control_fidelity(
        control_delta_vs_retained=control_delta
    )
    candidate_effect = matrix_mod.classify_candidate_effect(
        candidate_minus_control=candidate_minus_control
    )
    usable_decision_gate = int(control_fidelity in {"stable", "near_stable"})
    return {
        "fixture_seed": _safe_int(comparison_summary.get("fixture_seed")),
        "search_seed": _safe_int(comparison_summary.get("search_seed")),
        "case_dir_relpath": _relative_path(case_dir),
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
        "control_fidelity_quality": str(control_fidelity),
        "usable_decision_gate": int(usable_decision_gate),
        "candidate_effect": str(candidate_effect),
        "decision_gate_read": (
            str(candidate_effect) if usable_decision_gate else "context_only"
        ),
    }


def _build_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    usable_rows = [dict(row) for row in rows if _safe_int(row.get("usable_decision_gate")) == 1]
    drifted_rows = [dict(row) for row in rows if _safe_int(row.get("usable_decision_gate")) == 0]
    fixture_rows: list[dict[str, Any]] = []
    for fixture_seed in sorted({_safe_int(row.get("fixture_seed")) for row in rows}):
        seed_rows = [dict(row) for row in rows if _safe_int(row.get("fixture_seed")) == fixture_seed]
        fixture_rows.append(
            {
                "fixture_seed": int(fixture_seed),
                "case_count": int(len(seed_rows)),
                "usable_decision_gate_cases": int(
                    sum(1 for row in seed_rows if _safe_int(row.get("usable_decision_gate")) == 1)
                ),
                "positive_cases": int(
                    sum(1 for row in seed_rows if _safe_str(row.get("decision_gate_read")) == "positive")
                ),
                "neutral_cases": int(
                    sum(1 for row in seed_rows if _safe_str(row.get("decision_gate_read")) == "neutral")
                ),
                "negative_cases": int(
                    sum(1 for row in seed_rows if _safe_str(row.get("decision_gate_read")) == "negative")
                ),
                "context_only_cases": int(
                    sum(1 for row in seed_rows if _safe_str(row.get("decision_gate_read")) == "context_only")
                ),
            }
        )
    return {
        "run_label": str(RUN_LABEL),
        "case_count": int(len(rows)),
        "usable_decision_gate_cases": int(len(usable_rows)),
        "drifted_context_cases": int(len(drifted_rows)),
        "positive_on_decision_gate": int(
            sum(1 for row in usable_rows if _safe_str(row.get("candidate_effect")) == "positive")
        ),
        "neutral_on_decision_gate": int(
            sum(1 for row in usable_rows if _safe_str(row.get("candidate_effect")) == "neutral")
        ),
        "negative_on_decision_gate": int(
            sum(1 for row in usable_rows if _safe_str(row.get("candidate_effect")) == "negative")
        ),
        "fixture_summary_rows": fixture_rows,
    }


def _write_markdown(
    output_dir: Path,
    *,
    rows: Sequence[Mapping[str, Any]],
    failures: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> None:
    lines = [
        "# Candidate 3 Remaining Exact Saved-Surface Batch",
        "",
        "Question:",
        "- across the remaining supported retained cases, does candidate3 show any broader signal beyond the existing `1111`-leaning read?",
        "",
        "Top-line counts:",
        f"- attempted cases: `{_safe_int(summary.get('case_count')) + len(failures)}`",
        f"- completed cases: `{_safe_int(summary.get('case_count'))}`",
        f"- failures: `{len(failures)}`",
        f"- usable decision-gate cases: `{_safe_int(summary.get('usable_decision_gate_cases'))}`",
        f"- drifted context cases: `{_safe_int(summary.get('drifted_context_cases'))}`",
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
    if failures:
        lines.extend(["", "Failures:"])
        for row in failures:
            lines.append(
                f"- `{_safe_int(row.get('fixture_seed'))}/search{_safe_int(row.get('search_seed'))}`: "
                f"{_safe_str(row.get('error'))}"
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
    (output_dir / "remaining_cases_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def _run_case(spec: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    fixture_seed = _safe_int(spec.get("fixture_seed"))
    search_seed = _safe_int(spec.get("search_seed"))
    artifact_relpath = Path(_safe_str(spec.get("artifact_relpath")))
    artifact_path = REPO_ROOT / artifact_relpath
    case_dir = output_dir / f"fixture_{fixture_seed}__search{search_seed}"
    case_dir.mkdir(parents=True, exist_ok=False)

    case = resume_mod.load_artifact_case(artifact_path=artifact_path)
    saved_rows = exact_mod._load_saved_start_rows(case.artifact)
    control_rows = exact_mod._prepare_saved_start_rows(saved_rows)
    candidate_rows = saved_surface_mod.build_candidate3_saved_surface_rows(saved_rows)

    _write_json(
        case_dir / "attempt_manifest.json",
        {
            "fixture_seed": int(fixture_seed),
            "search_seed": int(search_seed),
            "source_artifact_relpath": _relative_path(case.artifact_path),
            "source_run_dir_relpath": _relative_path(case.run_dir),
            "start_surface_count": int(len(saved_rows)),
            "scope_note": (
                "saved-surface exact replay uses retained phaseC_start_summaries "
                "directly and supports rescue-disabled cases only"
            ),
        },
    )

    control_summary = exact_mod.run_saved_surface_phasec_replay(
        case=case,
        saved_rows=control_rows,
        replay_label="saved_surface_control",
    )
    candidate_summary = exact_mod.run_saved_surface_phasec_replay(
        case=case,
        saved_rows=candidate_rows,
        replay_label="saved_surface_candidate3",
    )
    comparison_summary = exact_mod.build_comparison_summary(
        case=case,
        control_summary=control_summary,
        candidate_summary=candidate_summary,
    )
    comparison_summary = dict(comparison_summary, run_label=str(RUN_LABEL))

    _write_json(case_dir / "control_saved_surface_summary.json", control_summary)
    _write_json(case_dir / "candidate_saved_surface_summary.json", candidate_summary)
    _write_json(case_dir / "comparison_summary.json", comparison_summary)
    _write_json(
        case_dir / "control_saved_surface_start_rows.json",
        list(control_summary.get("start_summaries", []) or []),
    )
    _write_json(
        case_dir / "candidate_saved_surface_start_rows.json",
        list(candidate_summary.get("start_summaries", []) or []),
    )
    exact_mod.write_markdown(
        case_dir,
        comparison_summary=comparison_summary,
        control_summary=control_summary,
        candidate_summary=candidate_summary,
    )

    row = _build_case_row(case_dir=case_dir, comparison_summary=comparison_summary)
    _write_json(case_dir / "run_summary.json", row)
    return row


def run_batch() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for spec in CASE_SPECS:
        try:
            rows.append(_run_case(spec, output_dir))
        except Exception as exc:  # pragma: no cover - operational path
            failures.append(
                {
                    "fixture_seed": _safe_int(spec.get("fixture_seed")),
                    "search_seed": _safe_int(spec.get("search_seed")),
                    "artifact_relpath": _safe_str(spec.get("artifact_relpath")),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    rows = sorted(rows, key=lambda row: (_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed"))))
    failures = sorted(
        failures,
        key=lambda row: (_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed"))),
    )
    summary = _build_summary(rows)
    summary = {
        **summary,
        "output_dir": _relative_path(output_dir),
        "failure_count": int(len(failures)),
    }

    _write_jsonl(output_dir / "remaining_cases_rows.jsonl", rows)
    if rows:
        _write_csv(output_dir / "remaining_cases_rows.csv", rows)
    _write_json(output_dir / "remaining_cases_summary.json", summary)
    _write_json(output_dir / "remaining_cases_failures.json", failures)
    _write_markdown(output_dir, rows=rows, failures=failures, summary=summary)
    _write_json(
        output_dir / "run_summary.json",
        {
            "output_dir": _relative_path(output_dir),
            "case_count": _safe_int(summary.get("case_count")),
            "usable_decision_gate_cases": _safe_int(summary.get("usable_decision_gate_cases")),
            "drifted_context_cases": _safe_int(summary.get("drifted_context_cases")),
            "failure_count": int(len(failures)),
        },
    )
    return {
        "output_dir": _relative_path(output_dir),
        "case_count": _safe_int(summary.get("case_count")),
        "usable_decision_gate_cases": _safe_int(summary.get("usable_decision_gate_cases")),
        "drifted_context_cases": _safe_int(summary.get("drifted_context_cases")),
        "failure_count": int(len(failures)),
    }


def main() -> None:
    print(json.dumps(run_batch(), sort_keys=True))


if __name__ == "__main__":
    main()
