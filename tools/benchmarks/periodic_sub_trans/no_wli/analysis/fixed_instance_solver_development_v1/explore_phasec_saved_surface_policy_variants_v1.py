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
        "explore_phasec_saved_surface_policy_variants_v1.py"
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


RUN_LABEL = "phasec_saved_surface_policy_variants_v1"
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
ANCHOR_SWAP_POLICY_NAME = "phaseb_topk_anchor_swap_v1"
POLICY_BUILDERS: tuple[tuple[str, Callable[[Sequence[Mapping[str, Any]]], list[dict[str, Any]]]], ...] = (
    (
        "phaseb_topk_frontload_two_v1",
        saved_surface_mod.build_phaseb_topk_frontload_two_saved_surface_rows,
    ),
    (
        "phaseb_topk_frontload_all_v1",
        saved_surface_mod.build_phaseb_topk_frontload_all_saved_surface_rows,
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


def _load_baseline_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with (REPO_ROOT / SOURCE_MATRIX_CSV_REL_PATH).open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "policy_name": str(ANCHOR_SWAP_POLICY_NAME),
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
                    "control_winner_source": _safe_str(row.get("control_winner_source")),
                    "candidate_winner_source": _safe_str(
                        row.get("candidate_winner_source")
                    ),
                    "candidate_winner_candidate_hash": _safe_str(
                        row.get("candidate_winner_candidate_hash")
                    ),
                }
            )
    return rows


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


def build_policy_row(
    *,
    policy_name: str,
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


def annotate_against_anchor_swap(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    anchor_by_case: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        if _safe_str(row.get("policy_name")) != str(ANCHOR_SWAP_POLICY_NAME):
            continue
        anchor_by_case[
            (_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed")))
        ] = dict(row)

    out_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        case_key = (_safe_int(row.get("fixture_seed")), _safe_int(row.get("search_seed")))
        anchor_row = anchor_by_case.get(case_key)
        if anchor_row is None:
            payload["vs_anchor_swap_delta"] = float("nan")
            payload["vs_anchor_swap_read"] = ""
        else:
            delta = _safe_float(row.get("candidate_best_match_ratio")) - _safe_float(
                anchor_row.get("candidate_best_match_ratio")
            )
            payload["vs_anchor_swap_delta"] = float(delta)
            payload["vs_anchor_swap_read"] = str(
                matrix_mod.classify_candidate_effect(candidate_minus_control=delta)
            )
        out_rows.append(payload)
    return out_rows


def build_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    policy_summary_rows: list[dict[str, Any]] = []
    for policy_name in sorted({_safe_str(row.get("policy_name")) for row in rows}):
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
        vs_anchor_positive = int(
            sum(
                1
                for row in usable_rows
                if _safe_str(row.get("vs_anchor_swap_read")) == "positive"
            )
        )
        vs_anchor_neutral = int(
            sum(
                1
                for row in usable_rows
                if _safe_str(row.get("vs_anchor_swap_read")) == "neutral"
            )
        )
        vs_anchor_negative = int(
            sum(
                1
                for row in usable_rows
                if _safe_str(row.get("vs_anchor_swap_read")) == "negative"
            )
        )
        policy_summary_rows.append(
            {
                "policy_name": str(policy_name),
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
                "better_than_anchor_swap_on_gate": int(vs_anchor_positive),
                "equal_to_anchor_swap_on_gate": int(vs_anchor_neutral),
                "worse_than_anchor_swap_on_gate": int(vs_anchor_negative),
            }
        )
    best_policy_by_case: list[dict[str, Any]] = []
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
                -_safe_int(row.get("policy_name") == ANCHOR_SWAP_POLICY_NAME),
            ),
        )
        best_policy_by_case.append(
            {
                "fixture_seed": int(case_key[0]),
                "search_seed": int(case_key[1]),
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
        "policy_summary_rows": policy_summary_rows,
        "best_policy_by_case_rows": best_policy_by_case,
    }


def write_markdown(output_dir: Path, *, rows: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> None:
    lines = [
        "# Phase-C Saved-Surface Policy Variant Matrix",
        "",
        "Question:",
        "- across the full supported candidate3 exact saved-surface panel, do stronger `phaseB_topk` front-load variants outperform the current anchor-swap probe?",
        "",
        "Policies compared:",
        f"- `{ANCHOR_SWAP_POLICY_NAME}` from the current exact matrix",
    ]
    for policy_name, _builder in POLICY_BUILDERS:
        lines.append(f"- `{policy_name}` newly replayed on the same saved-surface control lanes")
    lines.extend(
        [
            "",
            "Per-policy summary:",
            "",
            "| policy | usable gates | positive | neutral | negative | mean delta | better vs anchor-swap | equal | worse |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in list(summary.get("policy_summary_rows", []) or []):
        lines.append(
            f"| `{_safe_str(row.get('policy_name'))}` | "
            f"`{_safe_int(row.get('usable_decision_gate_cases'))}` | "
            f"`{_safe_int(row.get('positive_on_gate'))}` | "
            f"`{_safe_int(row.get('neutral_on_gate'))}` | "
            f"`{_safe_int(row.get('negative_on_gate'))}` | "
            f"`{_safe_float(row.get('mean_delta_on_gate')):.3f}` | "
            f"`{_safe_int(row.get('better_than_anchor_swap_on_gate'))}` | "
            f"`{_safe_int(row.get('equal_to_anchor_swap_on_gate'))}` | "
            f"`{_safe_int(row.get('worse_than_anchor_swap_on_gate'))}` |"
        )
    lines.extend(
        [
            "",
            "Usable-gate case matrix:",
            "",
            "| case | policy | control | candidate | delta | vs anchor-swap | read |",
            "| --- | --- | --- | --- | --- | --- | --- |",
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
            f"`{_safe_float(row.get('control_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('candidate_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('candidate_minus_control_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('vs_anchor_swap_delta')):.3f}` | "
            f"`{_safe_str(row.get('decision_gate_read'))}` |"
        )
    lines.extend(
        [
            "",
            "Best policy by usable-gate case:",
            "",
            "| case | best policy | best candidate match | candidate minus control |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in list(summary.get("best_policy_by_case_rows", []) or []):
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}/search{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_str(row.get('best_policy_name'))}` | "
            f"`{_safe_float(row.get('best_candidate_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('best_candidate_minus_control')):.3f}` |"
        )
    (output_dir / "phasec_saved_surface_policy_variant_matrix.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_exploration() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    cases_dir = output_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    baseline_rows = _load_baseline_rows()
    case_specs = _load_case_specs()

    new_rows: list[dict[str, Any]] = []
    for case_spec in case_specs:
        bundle_relpath = _safe_str(case_spec.get("bundle_relpath"))
        fixture_seed = _safe_int(case_spec.get("fixture_seed"))
        search_seed = _safe_int(case_spec.get("search_seed"))
        bundle_path = REPO_ROOT / bundle_relpath
        case_dir = cases_dir / f"fixture_{fixture_seed}__search{search_seed}"
        case_dir.mkdir(parents=True, exist_ok=False)

        control_summary = _load_json(bundle_path / "control_saved_surface_summary.json")
        source_artifact_relpath = _safe_str(case_spec.get("source_artifact_relpath"))
        case = resume_mod.load_artifact_case(artifact_path=REPO_ROOT / source_artifact_relpath)
        saved_rows = exact_mod._load_saved_start_rows(case.artifact)
        _write_json(
            case_dir / "case_manifest.json",
            {
                "fixture_seed": int(fixture_seed),
                "search_seed": int(search_seed),
                "bundle_relpath": str(bundle_relpath),
                "source_artifact_relpath": str(source_artifact_relpath),
                "saved_start_count": int(len(saved_rows)),
            },
        )

        for policy_name, builder in POLICY_BUILDERS:
            candidate_rows = builder(saved_rows)
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
                bundle_relpath=str(bundle_relpath),
                comparison_summary=comparison_summary,
            )
            new_rows.append(row)
            _write_json(
                case_dir / f"{policy_name}__candidate_saved_surface_summary.json",
                candidate_summary,
            )
            _write_json(
                case_dir / f"{policy_name}__comparison_summary.json",
                comparison_summary,
            )

    rows = annotate_against_anchor_swap([*baseline_rows, *new_rows])
    rows = sorted(
        rows,
        key=lambda row: (
            _safe_int(row.get("fixture_seed")),
            _safe_int(row.get("search_seed")),
            _safe_str(row.get("policy_name")),
        ),
    )
    summary = build_summary(rows)
    summary = {
        **summary,
        "output_dir": _relative_path(output_dir),
        "source_matrix_summary_relpath": SOURCE_MATRIX_SUMMARY_REL_PATH.as_posix(),
        "source_matrix_csv_relpath": SOURCE_MATRIX_CSV_REL_PATH.as_posix(),
    }

    _write_jsonl(output_dir / "phasec_saved_surface_policy_variant_rows.jsonl", rows)
    _write_csv(output_dir / "phasec_saved_surface_policy_variant_rows.csv", rows)
    _write_json(output_dir / "phasec_saved_surface_policy_variant_summary.json", summary)
    write_markdown(output_dir, rows=rows, summary=summary)

    run_summary = {
        "output_dir": _relative_path(output_dir),
        "case_count": _safe_int(summary.get("case_count")),
        "policy_count": int(len(list(summary.get("policy_summary_rows", []) or []))),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    print(json.dumps(run_exploration(), sort_keys=True))


if __name__ == "__main__":
    main()
