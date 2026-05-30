from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_nonproduction_scorer_design_v1"
SOURCE_OUTPUT_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_balanced_readout_v1"
INTERPRETATION_OUTPUT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_balanced_readout_interpretation_v1"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_nonproduction_scorer_design_v1"
)
CLAIM_MODE = "hard_pair_candidate_comparability"
PRIMARY_PROFILE_ID = "P2_conservative_len8_hd2"
COMPARISON_PROFILE_ID = "P1_word_analogue_len7_hd2"
CONTROL_PROFILE_ID = "P0_exact_short"


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(rel_path: str) -> Any:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def read_csv(rel_path: str) -> list[dict[str, str]]:
    with (REPO_ROOT / rel_path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def int_value(value: Any) -> int:
    if value in ("", None):
        return 0
    return int(float(value))


def float_value(value: Any) -> float:
    if value in ("", None):
        return 0.0
    return float(value)


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: Iterable[str] | None = None) -> None:
    ensure_under_repo(path)
    names = list(fieldnames) if fieldnames is not None else sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def score_bucket(score: float) -> str:
    if score <= 0.0:
        return "zero"
    if score < 20.0:
        return "low_positive"
    if score < 60.0:
        return "medium_positive"
    return "high_positive"


def source_candidate_rows() -> dict[str, dict[str, Any]]:
    selection = read_json(f"{SOURCE_OUTPUT_REL}/candidate_selection_manifest.json")
    rows = {row["candidate_id"]: dict(row) for row in selection["selected_candidates"]}
    summary_rows = read_csv(f"{SOURCE_OUTPUT_REL}/hit_summary_by_candidate.csv")
    for row in summary_rows:
        rows.setdefault(row["candidate_id"], {}).update(
            {
                "source_total_hit_count": int_value(row["hit_count"]),
                "source_total_weighted_hit_sum": float_value(row["weighted_hit_sum"]),
                "source_positive_row_count": int_value(row["positive_row_count"]),
            }
        )
    return rows


def build_candidate_design_rows() -> list[dict[str, Any]]:
    candidates = source_candidate_rows()
    profile_rows = read_csv(f"{SOURCE_OUTPUT_REL}/hit_summary_by_candidate_profile.csv")
    by_candidate: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in profile_rows:
        by_candidate[row["candidate_id"]][row["profile_id"]] = row

    rows: list[dict[str, Any]] = []
    for candidate_id, selection_row in sorted(candidates.items()):
        p0 = by_candidate[candidate_id].get(CONTROL_PROFILE_ID, {})
        p1 = by_candidate[candidate_id].get(COMPARISON_PROFILE_ID, {})
        p2 = by_candidate[candidate_id].get(PRIMARY_PROFILE_ID, {})
        p1_score = float_value(p1.get("weighted_hit_sum"))
        p2_score = float_value(p2.get("weighted_hit_sum"))
        p0_hits = int_value(p0.get("hit_count"))
        primary_score = p2_score
        rows.append(
            {
                "candidate_id": candidate_id,
                "selected_stratum": selection_row.get("selected_stratum", ""),
                "source_pair_id": selection_row.get("source_pair_id", ""),
                "known_better_or_worse_role": selection_row.get("known_better_or_worse_role", ""),
                "current_score": float_value(selection_row.get("current_score")),
                "truth_match_ratio": float_value(selection_row.get("truth_match_ratio")),
                "pair_occurrence_count": int_value(selection_row.get("pair_occurrence_count")),
                "chunk_count_available": int_value(selection_row.get("chunk_count_available")),
                "primary_profile_id": PRIMARY_PROFILE_ID,
                "primary_score_raw_weighted_hits": primary_score,
                "primary_score_log1p_weighted_hits": math.log1p(primary_score),
                "primary_hit_count": int_value(p2.get("hit_count")),
                "primary_positive_row_count": int_value(p2.get("positive_row_count")),
                "comparison_profile_id": COMPARISON_PROFILE_ID,
                "comparison_score_raw_weighted_hits": p1_score,
                "comparison_hit_count": int_value(p1.get("hit_count")),
                "p1_p2_weighted_delta": p1_score - p2_score,
                "p1_p2_hit_delta": int_value(p1.get("hit_count")) - int_value(p2.get("hit_count")),
                "p1_p2_same_hit_count": int_value(p1.get("hit_count")) == int_value(p2.get("hit_count")),
                "control_profile_id": CONTROL_PROFILE_ID,
                "p0_exact_hit_count": p0_hits,
                "p0_audit_flag": p0_hits > 0,
                "score_bucket": score_bucket(primary_score),
                "source_total_hit_count": int_value(selection_row.get("source_total_hit_count")),
                "source_total_weighted_hit_sum": float_value(selection_row.get("source_total_weighted_hit_sum")),
            }
        )
    for rank, row in enumerate(
        sorted(rows, key=lambda item: (-float(item["primary_score_raw_weighted_hits"]), item["candidate_id"])),
        start=1,
    ):
        row["primary_score_rank"] = rank
    return sorted(rows, key=lambda row: int(row["primary_score_rank"]))


def aggregate_rows(rows: list[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[group_key]) or "no_recorded_pair_role"].append(row)
    out: list[dict[str, Any]] = []
    for group_value, group_rows in sorted(grouped.items()):
        scores = [float(row["primary_score_raw_weighted_hits"]) for row in group_rows]
        hits = [int(row["primary_hit_count"]) for row in group_rows]
        out.append(
            {
                group_key: group_value,
                "candidate_count": len(group_rows),
                "candidates_with_primary_hits": sum(1 for hit_count in hits if hit_count > 0),
                "candidate_hit_rate": sum(1 for hit_count in hits if hit_count > 0) / len(group_rows)
                if group_rows
                else 0.0,
                "total_primary_hits": sum(hits),
                "mean_primary_hits": sum(hits) / len(group_rows) if group_rows else 0.0,
                "total_primary_score": sum(scores),
                "mean_primary_score": sum(scores) / len(group_rows) if group_rows else 0.0,
                "median_primary_score": median(scores) if scores else 0.0,
                "mean_truth_match_ratio": sum(float(row["truth_match_ratio"]) for row in group_rows) / len(group_rows)
                if group_rows
                else 0.0,
                "p0_audit_flag_count": sum(1 for row in group_rows if row["p0_audit_flag"]),
            }
        )
    return sorted(out, key=lambda row: (-float(row["mean_primary_score"]), str(row[group_key])))


def pair_comparison_rows(candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in candidate_rows:
        source_pair_id = str(row.get("source_pair_id") or "")
        role = str(row.get("known_better_or_worse_role") or "")
        if source_pair_id and role in {"known_better", "known_worse"}:
            grouped[source_pair_id][role].append(row)
    out: list[dict[str, Any]] = []
    for source_pair_id, role_rows in sorted(grouped.items()):
        better_rows = role_rows.get("known_better", [])
        worse_rows = role_rows.get("known_worse", [])
        if not better_rows or not worse_rows:
            continue
        better = max(better_rows, key=lambda row: float(row["primary_score_raw_weighted_hits"]))
        worse = max(worse_rows, key=lambda row: float(row["primary_score_raw_weighted_hits"]))
        better_score = float(better["primary_score_raw_weighted_hits"])
        worse_score = float(worse["primary_score_raw_weighted_hits"])
        out.append(
            {
                "source_pair_id": source_pair_id,
                "known_better_candidate_id": better["candidate_id"],
                "known_worse_candidate_id": worse["candidate_id"],
                "known_better_primary_score": better_score,
                "known_worse_primary_score": worse_score,
                "score_margin_better_minus_worse": better_score - worse_score,
                "primary_score_prefers_known_better": better_score > worse_score,
                "known_better_truth_match_ratio": better["truth_match_ratio"],
                "known_worse_truth_match_ratio": worse["truth_match_ratio"],
            }
        )
    return out


def panel_rescue_rows(candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in candidate_rows if row["selected_stratum"] == "panel_rescue_known_better"]


def build_design() -> dict[str, Any]:
    source_manifest = read_json(f"{SOURCE_OUTPUT_REL}/pilot_manifest.json")
    interpretation_manifest = read_json(f"{INTERPRETATION_OUTPUT_REL}/decision_manifest.json")
    candidate_rows = build_candidate_design_rows()
    stratum_rows = aggregate_rows(candidate_rows, "selected_stratum")
    role_rows = aggregate_rows(candidate_rows, "known_better_or_worse_role")
    pair_rows = pair_comparison_rows(candidate_rows)
    rescue_rows = panel_rescue_rows(candidate_rows)

    p1_p2_same = sum(1 for row in candidate_rows if row["p1_p2_same_hit_count"])
    p0_audit_count = sum(1 for row in candidate_rows if row["p0_audit_flag"])
    paired_prefers_better = sum(1 for row in pair_rows if row["primary_score_prefers_known_better"])
    rescue_positive = sum(1 for row in rescue_rows if int(row["primary_hit_count"]) > 0)

    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "review_ready",
        "source_output_dir": SOURCE_OUTPUT_REL,
        "interpretation_output_dir": INTERPRETATION_OUTPUT_REL,
        "claim_mode": CLAIM_MODE,
        "source_status": source_manifest["status"],
        "source_backend_impl": source_manifest["backend_impl"],
        "source_python_fallback_allowed": source_manifest["python_fallback_allowed"],
        "broad_pilot": False,
        "full_hard_pair_report": False,
        "production_scorer_changes": False,
        "controlled_damage_ladder_claim": False,
        "scorer_design_only": True,
        "primary_design": {
            "candidate_signal": "normal_order2_P2_raw_weighted_hits",
            "primary_profile_id": PRIMARY_PROFILE_ID,
            "comparison_profile_id": COMPARISON_PROFILE_ID,
            "control_profile_id": CONTROL_PROFILE_ID,
            "raw_score_formula": "primary_score_raw_weighted_hits = P2 normal/order2 weighted_hit_sum",
            "optional_transform": "primary_score_log1p_weighted_hits = log1p(primary_score_raw_weighted_hits)",
            "p0_usage": "audit/control only",
        },
        "summary": {
            "candidate_count": len(candidate_rows),
            "source_total_hits": source_manifest["total_hit_count"],
            "source_candidates_with_hits": source_manifest["candidates_with_hits"],
            "p1_p2_same_hit_count_candidates": p1_p2_same,
            "p1_p2_candidate_count": len(candidate_rows),
            "p0_audit_flag_count": p0_audit_count,
            "pair_comparison_count": len(pair_rows),
            "pair_comparisons_preferring_known_better": paired_prefers_better,
            "panel_rescue_candidate_count": len(rescue_rows),
            "panel_rescue_candidates_with_primary_hits": rescue_positive,
            "interpretation_panel_rescue_hits": interpretation_manifest["summary"]["panel_rescue_known_better_hits"],
        },
        "review_recommendation": {
            "next_step": "review_nonproduction_scorer_design_before_any_integration",
            "recommended_primary": "Use P2 raw weighted hits as the conservative primary signal under review.",
            "recommended_transform": "Consider log1p only when combining with existing score scales.",
            "keep_as_audit": [
                "P0 exact-control hit count",
                "P1/P2 redundancy rows",
                "claim-mode/provenance manifest",
            ],
            "must_resolve_before_rescue_claim": "panel_rescue_known_better remains zero-hit under the primary signal.",
            "still_forbidden": [
                "production scorer changes",
                "controlled damage-ladder language",
                "strict/order4/P3/P4 expansion",
                "full hard-pair report",
                "rescue-performance claim",
            ],
        },
    }
    return {
        "manifest": manifest,
        "candidate_design_rows": candidate_rows,
        "stratum_design_rows": stratum_rows,
        "role_design_rows": role_rows,
        "pair_comparison_rows": pair_rows,
        "panel_rescue_inspection_rows": rescue_rows,
    }


def write_outputs(payload: dict[str, Any]) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    manifest = payload["manifest"]
    write_json(output_dir / "design_manifest.json", manifest)
    write_csv(output_dir / "candidate_design_rows.csv", payload["candidate_design_rows"])
    write_csv(output_dir / "stratum_design_rows.csv", payload["stratum_design_rows"])
    write_csv(output_dir / "role_design_rows.csv", payload["role_design_rows"])
    write_csv(output_dir / "pair_comparison_rows.csv", payload["pair_comparison_rows"])
    write_csv(output_dir / "panel_rescue_inspection_rows.csv", payload["panel_rescue_inspection_rows"])
    readout = [
        "# PhaseB N-Gram Hamming Non-Production Scorer Design v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- claim mode: `{manifest['claim_mode']}`",
        f"- scorer design only: `{manifest['scorer_design_only']}`",
        f"- production scorer changes: `{manifest['production_scorer_changes']}`",
        f"- controlled damage ladder claim: `{manifest['controlled_damage_ladder_claim']}`",
        f"- primary signal: `{manifest['primary_design']['candidate_signal']}`",
        f"- candidates: `{manifest['summary']['candidate_count']}`",
        f"- source total hits: `{manifest['summary']['source_total_hits']}`",
        f"- P1/P2 same-hit-count candidates: `{manifest['summary']['p1_p2_same_hit_count_candidates']}` / `{manifest['summary']['p1_p2_candidate_count']}`",
        f"- P0 audit flags: `{manifest['summary']['p0_audit_flag_count']}`",
        f"- paired comparisons available: `{manifest['summary']['pair_comparison_count']}`",
        f"- paired comparisons preferring known-better: `{manifest['summary']['pair_comparisons_preferring_known_better']}`",
        f"- panel-rescue candidates with primary hits: `{manifest['summary']['panel_rescue_candidates_with_primary_hits']}` / `{manifest['summary']['panel_rescue_candidate_count']}`",
        "",
        "## Proposed Non-Production Score",
        "",
        "Use P2 normal/order-2 raw weighted hits as the conservative candidate signal under review.",
        "Keep the log1p transform only as an optional bridge if this feature is later combined with existing score scales.",
        "Keep P0 exact hits as an audit/control flag, not as a positive ranking signal.",
        "",
        "## Review Boundary",
        "",
        "This slice does not change production scorer behavior. It is a design artifact over the balanced readout output only.",
        "It must not be used to claim controlled damage-ladder performance, full hard-pair representativeness, or rescue performance.",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def run_design() -> dict[str, Any]:
    payload = build_design()
    write_outputs(payload)
    return payload["manifest"]


def main() -> None:
    manifest = run_design()
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] primary_signal={manifest['primary_design']['candidate_signal']}")


if __name__ == "__main__":
    main()
