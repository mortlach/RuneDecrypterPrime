from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "explore_phasec_saved_surface_policy_seed_sweep_v1.py"
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


RUN_LABEL = "phasec_saved_surface_policy_seed_sweep_v1"
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
CASE_BUNDLE_REL_PATHS = (
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T041606Z__candidate3_phasec_saved_surface_exact_remaining_cases_v1/"
        "fixture_611__search7003"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T011226Z__candidate3_phasec_saved_surface_exact_1111_search7004_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7003_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260417T153047Z__candidate3_phasec_saved_surface_exact_1511_search7005_v1"
    ),
    Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "fixed_instance_solver_development_v1/"
        "20260417T054445Z__candidate3_phasec_saved_surface_exact_1511_search7004_v1"
    ),
)
SEED_OFFSETS = (-2, -1, 0, 1, 2)
POLICY_BUILDERS: tuple[tuple[str, Callable[[Sequence[Mapping[str, Any]]], list[dict[str, Any]]]], ...] = (
    ("source_order_control_v1", exact_mod._prepare_saved_start_rows),
    ("phaseb_topk_anchor_swap_v1", saved_surface_mod.build_candidate3_saved_surface_rows),
    (
        "phaseb_topk_frontload_two_v1",
        saved_surface_mod.build_phaseb_topk_frontload_two_saved_surface_rows,
    ),
    (
        "phaseb_topk_frontload_all_v1",
        saved_surface_mod.build_phaseb_topk_frontload_all_saved_surface_rows,
    ),
)
BASELINE_POLICY_NAME = "source_order_control_v1"


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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_policy_row(
    *,
    policy_name: str,
    seed_offset: int,
    phasec_seed: int,
    bundle_relpath: str,
    case: Mapping[str, Any],
    summary: Mapping[str, Any],
    baseline_best_match_ratio: float,
) -> dict[str, Any]:
    candidate_best_match = _safe_float(summary.get("best_match_ratio"))
    delta_vs_control = float(candidate_best_match - float(baseline_best_match_ratio))
    candidate_effect = matrix_mod.classify_candidate_effect(
        candidate_minus_control=delta_vs_control
    )
    return {
        "policy_name": str(policy_name),
        "seed_offset": int(seed_offset),
        "phasec_seed": int(phasec_seed),
        "fixture_seed": _safe_int(case.get("fixture_seed")),
        "search_seed": _safe_int(case.get("search_seed")),
        "bundle_relpath": str(bundle_relpath),
        "source_artifact_relpath": _safe_str(case.get("source_artifact_relpath")),
        "baseline_best_match_ratio": float(baseline_best_match_ratio),
        "candidate_best_match_ratio": float(candidate_best_match),
        "candidate_minus_control_best_match_ratio": float(delta_vs_control),
        "candidate_effect": str(candidate_effect),
        "winner_source": _safe_str(summary.get("winner_source")),
        "winner_source_rank": _safe_int(summary.get("winner_source_rank")),
        "winner_candidate_hash": _safe_str(summary.get("winner_candidate_hash")),
    }


def build_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    policy_summary_rows: list[dict[str, Any]] = []
    for policy_name in sorted({_safe_str(row.get("policy_name")) for row in rows}):
        policy_rows = [
            dict(row) for row in rows if _safe_str(row.get("policy_name")) == policy_name
        ]
        deltas = [
            _safe_float(row.get("candidate_minus_control_best_match_ratio"))
            for row in policy_rows
        ]
        policy_summary_rows.append(
            {
                "policy_name": str(policy_name),
                "row_count": int(len(policy_rows)),
                "positive_rows": int(
                    sum(
                        1
                        for row in policy_rows
                        if _safe_str(row.get("candidate_effect")) == "positive"
                    )
                ),
                "neutral_rows": int(
                    sum(
                        1
                        for row in policy_rows
                        if _safe_str(row.get("candidate_effect")) == "neutral"
                    )
                ),
                "negative_rows": int(
                    sum(
                        1
                        for row in policy_rows
                        if _safe_str(row.get("candidate_effect")) == "negative"
                    )
                ),
                "mean_delta_vs_control": (
                    float(sum(deltas) / len(deltas)) if deltas else float("nan")
                ),
            }
        )
    best_policy_rows: list[dict[str, Any]] = []
    case_seed_keys = sorted(
        {
            (
                _safe_int(row.get("fixture_seed")),
                _safe_int(row.get("search_seed")),
                _safe_int(row.get("seed_offset")),
            )
            for row in rows
        }
    )
    for key in case_seed_keys:
        bucket = [
            dict(row)
            for row in rows
            if (
                _safe_int(row.get("fixture_seed")),
                _safe_int(row.get("search_seed")),
                _safe_int(row.get("seed_offset")),
            )
            == key
        ]
        if not bucket:
            continue
        best_row = max(
            bucket,
            key=lambda row: (
                _safe_float(row.get("candidate_best_match_ratio")),
                -_safe_int(_safe_str(row.get("policy_name")) == BASELINE_POLICY_NAME),
            ),
        )
        best_policy_rows.append(
            {
                "fixture_seed": int(key[0]),
                "search_seed": int(key[1]),
                "seed_offset": int(key[2]),
                "best_policy_name": _safe_str(best_row.get("policy_name")),
                "best_candidate_best_match_ratio": _safe_float(
                    best_row.get("candidate_best_match_ratio")
                ),
                "best_candidate_minus_control": _safe_float(
                    best_row.get("candidate_minus_control_best_match_ratio")
                ),
            }
        )
    return {
        "run_label": str(RUN_LABEL),
        "case_count": int(
            len({(_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed"))) for row in rows})
        ),
        "seed_offset_count": int(len({ _safe_int(row.get("seed_offset")) for row in rows })),
        "policy_summary_rows": policy_summary_rows,
        "best_policy_rows": best_policy_rows,
    }


def write_markdown(output_dir: Path, *, rows: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> None:
    lines = [
        "# Phase-C Saved-Surface Policy Seed Sweep",
        "",
        "Question:",
        "- on the most informative usable candidate3 lanes, do the policy preferences survive small Phase-C seed shifts, or are they mostly one-seed ordering effects?",
        "",
        "Cases:",
    ]
    for bundle_relpath in CASE_BUNDLE_REL_PATHS:
        lines.append(f"- `{bundle_relpath.as_posix()}`")
    lines.extend(
        [
            "",
            "Per-policy summary:",
            "",
            "| policy | rows | positive | neutral | negative | mean delta vs control |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in list(summary.get("policy_summary_rows", []) or []):
        lines.append(
            f"| `{_safe_str(row.get('policy_name'))}` | "
            f"`{_safe_int(row.get('row_count'))}` | "
            f"`{_safe_int(row.get('positive_rows'))}` | "
            f"`{_safe_int(row.get('neutral_rows'))}` | "
            f"`{_safe_int(row.get('negative_rows'))}` | "
            f"`{_safe_float(row.get('mean_delta_vs_control')):.3f}` |"
        )
    lines.extend(
        [
            "",
            "Per-case/seed winners:",
            "",
            "| case | seed offset | best policy | best candidate match | delta vs control |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in list(summary.get("best_policy_rows", []) or []):
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}/search{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_int(row.get('seed_offset'))}` | "
            f"`{_safe_str(row.get('best_policy_name'))}` | "
            f"`{_safe_float(row.get('best_candidate_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('best_candidate_minus_control')):.3f}` |"
        )
    (output_dir / "phasec_saved_surface_policy_seed_sweep.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_sweep() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    cases_dir = output_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for bundle_relpath in CASE_BUNDLE_REL_PATHS:
        bundle_path = REPO_ROOT / bundle_relpath
        comparison_summary = _load_json(bundle_path / "comparison_summary.json")
        fixture_seed = _safe_int(comparison_summary.get("fixture_seed"))
        search_seed = _safe_int(comparison_summary.get("search_seed"))
        source_artifact_relpath = _safe_str(comparison_summary.get("source_artifact_relpath"))
        case = resume_mod.load_artifact_case(artifact_path=REPO_ROOT / source_artifact_relpath)
        saved_rows = exact_mod._load_saved_start_rows(case.artifact)
        retained_phasec_seed = exact_mod._resolve_phasec_seed(case.run_config)

        case_dir = cases_dir / f"fixture_{fixture_seed}__search{search_seed}"
        case_dir.mkdir(parents=True, exist_ok=False)
        _write_json(
            case_dir / "case_manifest.json",
            {
                "fixture_seed": int(fixture_seed),
                "search_seed": int(search_seed),
                "bundle_relpath": bundle_relpath.as_posix(),
                "source_artifact_relpath": str(source_artifact_relpath),
                "saved_start_count": int(len(saved_rows)),
                "retained_phasec_seed": int(retained_phasec_seed),
            },
        )

        for seed_offset in SEED_OFFSETS:
            phasec_seed = int(retained_phasec_seed + int(seed_offset))
            seed_dir = case_dir / f"seed_offset_{seed_offset:+d}".replace("+", "plus").replace("-", "minus")
            seed_dir.mkdir(parents=True, exist_ok=False)

            policy_summaries: dict[str, dict[str, Any]] = {}
            for policy_name, builder in POLICY_BUILDERS:
                policy_rows = builder(saved_rows)
                policy_summary = exact_mod.run_saved_surface_phasec_replay(
                    case=case,
                    saved_rows=policy_rows,
                    replay_label=f"{policy_name}__seed_{seed_offset:+d}",
                    phasec_seed_override=int(phasec_seed),
                )
                policy_summaries[str(policy_name)] = dict(policy_summary)
                _write_json(
                    seed_dir / f"{policy_name}__summary.json",
                    policy_summary,
                )

            baseline_best = _safe_float(
                policy_summaries[BASELINE_POLICY_NAME].get("best_match_ratio")
            )
            for policy_name in [name for name, _builder in POLICY_BUILDERS]:
                rows.append(
                    build_policy_row(
                        policy_name=str(policy_name),
                        seed_offset=int(seed_offset),
                        phasec_seed=int(phasec_seed),
                        bundle_relpath=bundle_relpath.as_posix(),
                        case={
                            "fixture_seed": fixture_seed,
                            "search_seed": search_seed,
                            "source_artifact_relpath": source_artifact_relpath,
                        },
                        summary=policy_summaries[str(policy_name)],
                        baseline_best_match_ratio=float(baseline_best),
                    )
                )

    rows = sorted(
        rows,
        key=lambda row: (
            _safe_int(row.get("fixture_seed")),
            _safe_int(row.get("search_seed")),
            _safe_int(row.get("seed_offset")),
            _safe_str(row.get("policy_name")),
        ),
    )
    summary = build_summary(rows)
    summary = {
        **summary,
        "output_dir": _relative_path(output_dir),
        "seed_offsets": [int(v) for v in SEED_OFFSETS],
        "case_bundle_relpaths": [path.as_posix() for path in CASE_BUNDLE_REL_PATHS],
    }

    _write_jsonl(output_dir / "phasec_saved_surface_policy_seed_rows.jsonl", rows)
    _write_csv(output_dir / "phasec_saved_surface_policy_seed_rows.csv", rows)
    _write_json(output_dir / "phasec_saved_surface_policy_seed_summary.json", summary)
    write_markdown(output_dir, rows=rows, summary=summary)

    run_summary = {
        "output_dir": _relative_path(output_dir),
        "case_count": _safe_int(summary.get("case_count")),
        "seed_offset_count": _safe_int(summary.get("seed_offset_count")),
        "row_count": int(len(rows)),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    print(json.dumps(run_sweep(), sort_keys=True))


if __name__ == "__main__":
    main()
