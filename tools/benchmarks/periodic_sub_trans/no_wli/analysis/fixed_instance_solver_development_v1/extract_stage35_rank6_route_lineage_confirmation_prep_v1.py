from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_stage35_rank6_route_lineage_confirmation_prep_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


RUN_LABEL = "stage35_rank6_route_lineage_confirmation_prep_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
FRONTIER_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/"
    "stage35_guard_selector_frontier_runtime_rows.csv"
)

SELECTED_START_MIN = 0.437
SHALLOW_MINUS_SELECTED_MIN = 0.400
ROUTE_LINEAGE_SOURCE = "phaseA_selected"
ROUTE_LINEAGE_SOURCE_RANK = 1
ROUTE_LINEAGE_NOVELTY_MIN = 173.5


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_json_relpath(relpath: str) -> dict[str, Any]:
    path = REPO_ROOT / relpath.replace("\\", "/")
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _key_of(row: Mapping[str, Any]) -> list[int]:
    raw = row.get("key_idx")
    if raw is None:
        raw = row.get("key")
    if not isinstance(raw, list):
        return []
    return [_safe_int(item) for item in raw]


def _hamming(left: list[int], right: list[int]) -> int | str:
    if not left or not right or len(left) != len(right):
        return ""
    return sum(1 for a, b in zip(left, right) if a != b)


def _has_value(mapping: Mapping[str, Any], key: str) -> bool:
    value = mapping.get(key)
    return value is not None and value != ""


def old_softened_rule_keep(raw: Mapping[str, Any]) -> int:
    if _safe_int(raw.get("candidate_rank")) != 6:
        return 0
    selected_start = _safe_float(raw.get("selected_start_match_ratio"))
    shallow_minus_selected = _safe_float(raw.get("resume_minus_selected"))
    if "shallow_minus_selected" in raw:
        shallow_minus_selected = _safe_float(raw.get("shallow_minus_selected"))
    return int(
        selected_start >= SELECTED_START_MIN
        or shallow_minus_selected >= SHALLOW_MINUS_SELECTED_MIN
    )


def route_lineage_rule_keep(
    *,
    candidate_source: str,
    candidate_source_rank: int,
    candidate_novelty_distance_to_anchor: float,
) -> int:
    return int(
        candidate_source == ROUTE_LINEAGE_SOURCE
        and candidate_source_rank == ROUTE_LINEAGE_SOURCE_RANK
        and candidate_novelty_distance_to_anchor >= ROUTE_LINEAGE_NOVELTY_MIN
    )


def confirmation_group(
    *,
    row_valid: int,
    old_softened_keep: int,
    route_lineage_keep: int,
) -> str:
    if not row_valid:
        return "E_invalid_missing_lineage"
    if not old_softened_keep and route_lineage_keep:
        return "A_old_reject_route_keep_predicted_recovered_positive"
    if old_softened_keep and not route_lineage_keep:
        return "B_old_keep_route_reject_safety_check"
    if old_softened_keep and route_lineage_keep:
        return "C_both_keep_positive_control"
    return "D_both_reject_negative_control"


def classify_rank6_row(
    raw: Mapping[str, Any],
    artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    invalid_reasons: list[str] = []
    candidate_hash = str(raw.get("candidate_hash", "") or "")
    artifact_relpath = str(raw.get("artifact_relpath", "") or "")
    if not candidate_hash:
        invalid_reasons.append("missing_candidate_hash")
    if not artifact_relpath:
        invalid_reasons.append("missing_artifact_relpath")
    if artifact is None:
        if "missing_artifact_relpath" not in invalid_reasons:
            invalid_reasons.append("missing_artifact_relpath")
        artifact = {}

    diagnostics = dict(artifact.get("stage3_diagnostics", {}) or {})
    phasec_pool_raw = diagnostics.get("phaseC_candidate_pool_rows")
    if not isinstance(phasec_pool_raw, list) or not phasec_pool_raw:
        invalid_reasons.append("missing_phaseC_candidate_pool_rows")
        phasec_pool: list[Mapping[str, Any]] = []
    else:
        phasec_pool = [
            row for row in phasec_pool_raw if isinstance(row, Mapping)
        ]

    candidate_row = next(
        (
            row
            for row in phasec_pool
            if str(row.get("candidate_hash", "") or "") == candidate_hash
        ),
        None,
    )
    if candidate_hash and candidate_row is None:
        invalid_reasons.append("candidate_hash_not_found_in_pool")
        candidate_row = {}

    anchor_hash = str(diagnostics.get("phaseC_anchor_candidate_hash", "") or "")
    if not anchor_hash:
        invalid_reasons.append("missing_phaseC_anchor_candidate_hash")
    anchor_row = next(
        (
            row
            for row in phasec_pool
            if str(row.get("candidate_hash", "") or "") == anchor_hash
        ),
        None,
    )
    if anchor_hash and anchor_row is None:
        invalid_reasons.append("anchor_hash_not_found_in_pool")
        anchor_row = {}

    candidate_source = str(candidate_row.get("source", "") or "")
    if not candidate_source:
        invalid_reasons.append("missing_candidate_source")

    candidate_source_rank_text = candidate_row.get("source_rank")
    if not _has_value(candidate_row, "source_rank"):
        invalid_reasons.append("missing_candidate_source_rank")
        candidate_source_rank: int | str = ""
    else:
        candidate_source_rank = _safe_int(candidate_source_rank_text)

    novelty_text = candidate_row.get("novelty_distance_to_anchor")
    if not _has_value(candidate_row, "novelty_distance_to_anchor"):
        invalid_reasons.append("missing_candidate_novelty_distance_to_anchor")
        novelty_distance: float | str = ""
    else:
        novelty_distance = _safe_float(novelty_text)

    distance_to_anchor = _hamming(_key_of(candidate_row), _key_of(anchor_row))
    old_keep = old_softened_rule_keep(raw)
    row_valid = int(not invalid_reasons)
    route_keep = (
        route_lineage_rule_keep(
            candidate_source=candidate_source,
            candidate_source_rank=int(candidate_source_rank),
            candidate_novelty_distance_to_anchor=float(novelty_distance),
        )
        if row_valid
        else 0
    )
    group = confirmation_group(
        row_valid=row_valid,
        old_softened_keep=old_keep,
        route_lineage_keep=route_keep,
    )
    selected_start = _safe_float(raw.get("selected_start_match_ratio"))
    shallow_minus_selected = _safe_float(raw.get("resume_minus_selected"))
    if "shallow_minus_selected" in raw:
        shallow_minus_selected = _safe_float(raw.get("shallow_minus_selected"))
    return {
        "fixture_seed": _safe_int(raw.get("fixture_seed")),
        "search_seed": _safe_int(raw.get("search_seed")),
        "candidate_rank": _safe_int(raw.get("candidate_rank")),
        "candidate_hash": candidate_hash,
        "candidate_source": candidate_source,
        "candidate_source_rank": candidate_source_rank,
        "candidate_novelty_distance_to_anchor": novelty_distance,
        "candidate_distance_to_phasec_anchor": distance_to_anchor,
        "selected_start_match_ratio": selected_start,
        "shallow_resume_minus_selected": shallow_minus_selected,
        "old_softened_keep": old_keep,
        "route_lineage_keep": route_keep,
        "confirmation_group": group,
        "row_valid": row_valid,
        "invalid_reason": "|".join(dict.fromkeys(invalid_reasons)),
        "artifact_relpath": artifact_relpath,
    }


def build_confirmation_rows(raw_rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        if _safe_int(raw.get("candidate_rank")) != 6:
            continue
        artifact_relpath = str(raw.get("artifact_relpath", "") or "")
        artifact: Mapping[str, Any] | None
        if artifact_relpath:
            artifact = _load_json_relpath(artifact_relpath)
        else:
            artifact = None
        rows.append(classify_rank6_row(raw, artifact))
    rows.sort(
        key=lambda row: (
            str(row["confirmation_group"]),
            int(row["fixture_seed"]),
            int(row["search_seed"]),
            str(row["candidate_hash"]),
        )
    )
    return rows


def summarize_rows(rows: list[Mapping[str, Any]], output_dir: Path) -> dict[str, Any]:
    invalid_reasons = Counter()
    for row in rows:
        if int(row.get("row_valid", 0)):
            continue
        for reason in str(row.get("invalid_reason", "")).split("|"):
            if reason:
                invalid_reasons[reason] += 1
    group_counts = Counter(str(row.get("confirmation_group", "")) for row in rows)
    return {
        "run_label": RUN_LABEL,
        "status": "completed",
        "output_dir": _repo_rel(output_dir),
        "frontier_rows_path": _repo_rel(REPO_ROOT / FRONTIER_ROWS_REL),
        "valid_row_count": sum(1 for row in rows if int(row.get("row_valid", 0))),
        "invalid_row_count": sum(1 for row in rows if not int(row.get("row_valid", 0))),
        "invalid_reason_counts": dict(sorted(invalid_reasons.items())),
        "old_softened_keep_count": sum(
            1 for row in rows if int(row.get("old_softened_keep", 0))
        ),
        "old_softened_reject_count": sum(
            1 for row in rows if not int(row.get("old_softened_keep", 0))
        ),
        "route_lineage_keep_count": sum(
            1 for row in rows if int(row.get("route_lineage_keep", 0))
        ),
        "route_lineage_reject_count": sum(
            1
            for row in rows
            if int(row.get("row_valid", 0))
            and not int(row.get("route_lineage_keep", 0))
        ),
        "rule_disagreement_count": sum(
            1
            for row in rows
            if int(row.get("row_valid", 0))
            and int(row.get("old_softened_keep", 0))
            != int(row.get("route_lineage_keep", 0))
        ),
        "group_A_count": group_counts[
            "A_old_reject_route_keep_predicted_recovered_positive"
        ],
        "group_B_count": group_counts["B_old_keep_route_reject_safety_check"],
        "group_C_count": group_counts["C_both_keep_positive_control"],
        "group_D_count": group_counts["D_both_reject_negative_control"],
        "group_E_count": group_counts["E_invalid_missing_lineage"],
        "rule": {
            "old_softened": (
                "candidate_rank == 6 and "
                "(selected_start_match_ratio >= 0.437 or "
                "shallow_resume_minus_selected >= 0.400)"
            ),
            "route_lineage_action_safe": (
                'candidate_source == "phaseA_selected" and '
                "candidate_source_rank == 1 and "
                "candidate_novelty_distance_to_anchor >= 173.5"
            ),
        },
        "interpretation": "offline_confirmation_prep_no_runtime",
        "recommended_next": "review_group_A_B_before_any_runtime_design",
        "updated_utc": _utc_now_text(),
    }


def build_readout(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Stage35 Rank6 Route-Lineage Confirmation Prep v1",
        "",
        "Question:",
        "",
        "- across all available retained rank-6 frontier rows, where does the",
        "  strict action-safe route-lineage rule disagree with the old softened",
        "  rule?",
        "",
        "Rules:",
        "",
        "- old softened rule:",
        "  - rank `6`",
        "  - `selected_start_match_ratio >= 0.437` or",
        "    `shallow_resume_minus_selected >= 0.400`",
        "- route-lineage rule:",
        "  - `candidate_source == phaseA_selected`",
        "  - `candidate_source_rank == 1`",
        "  - `candidate_novelty_distance_to_anchor >= 173.5`",
        "",
        "Coverage:",
        "",
        f"- valid rows: `{summary['valid_row_count']}`",
        f"- invalid rows: `{summary['invalid_row_count']}`",
        "",
        "Group Counts:",
        "",
        f"- A old reject / route keep: `{summary['group_A_count']}`",
        f"- B old keep / route reject: `{summary['group_B_count']}`",
        f"- C both keep: `{summary['group_C_count']}`",
        f"- D both reject: `{summary['group_D_count']}`",
        f"- E invalid: `{summary['group_E_count']}`",
        "",
        "Interpretation:",
        "",
        "- missing lineage is classified invalid, not reject",
        "- the route-lineage rule uses only action-safe saved Phase-C lineage",
        "- no runtime is implied by this extractor",
        "",
        "Recommended Next:",
        "",
        "- inspect groups A and B; if they provide honest held-out/disagreement",
        "  rows, write a tiny fixed-rule confirmation design before runtime",
    ]
    return "\n".join(lines).rstrip() + "\n"


def run_extract() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    rows = build_confirmation_rows(_read_csv(REPO_ROOT / FRONTIER_ROWS_REL))
    summary = summarize_rows(rows, output_dir)
    _write_csv(
        output_dir / "stage35_rank6_route_lineage_confirmation_prep_rows.csv",
        rows,
    )
    _write_json(
        output_dir / "stage35_rank6_route_lineage_confirmation_prep_summary.json",
        summary,
    )
    (output_dir / "stage35_rank6_route_lineage_confirmation_prep_readout.md").write_text(
        build_readout(summary),
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_extract()


if __name__ == "__main__":
    main()
