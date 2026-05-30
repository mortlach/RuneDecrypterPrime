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


RUN_LABEL = "phaseB_ngram_hamming_sample_index_all_candidate_matrix_interpretation_v1"
SOURCE_OUTPUT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_sample_index_all_candidate_matrix_interpretation_v1"
)
HARD_PAIR_DIR_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1"
BALANCED_OUTPUT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_balanced_readout_v1"
)
CLAIM_MODE = "hard_pair_candidate_comparability"

SCORE_MODES = (
    "current_score_only",
    "p2_raw_weighted_hits_only",
    "current_score_plus_log1p_p2",
    "gated_current_plus_log1p_p2",
)


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(rel_path: str) -> Any:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def read_csv(rel_path: str) -> list[dict[str, str]]:
    with (REPO_ROOT / rel_path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def float_value(value: Any) -> float:
    if value in ("", None):
        return 0.0
    return float(value)


def int_value(value: Any) -> int:
    if value in ("", None):
        return 0
    return int(float(value))


def candidate_scores() -> dict[str, dict[str, Any]]:
    selection = read_json(f"{SOURCE_OUTPUT_REL}/candidate_selection_manifest.json")
    rows = {
        row["candidate_id"]: {
            "candidate_id": row["candidate_id"],
            "current_score": float_value(row.get("current_score")),
            "truth_match_ratio": float_value(row.get("truth_match_ratio")),
            "known_better_or_worse_role": row.get("known_better_or_worse_role", ""),
            "selected_stratum": row.get("selected_stratum", ""),
            "pair_occurrence_count": int_value(row.get("pair_occurrence_count")),
            "p0_hit_count": 0,
            "p0_weighted_hit_sum": 0.0,
            "p1_hit_count": 0,
            "p1_weighted_hit_sum": 0.0,
            "p2_hit_count": 0,
            "p2_weighted_hit_sum": 0.0,
        }
        for row in selection["selected_candidates"]
    }
    profile_rows = read_csv(f"{SOURCE_OUTPUT_REL}/hit_summary_by_candidate_profile.csv")
    for row in profile_rows:
        candidate = rows[row["candidate_id"]]
        profile_id = row["profile_id"]
        if profile_id == "P0_exact_short":
            prefix = "p0"
        elif profile_id == "P1_word_analogue_len7_hd2":
            prefix = "p1"
        elif profile_id == "P2_conservative_len8_hd2":
            prefix = "p2"
        else:
            continue
        candidate[f"{prefix}_hit_count"] = int_value(row.get("hit_count"))
        candidate[f"{prefix}_weighted_hit_sum"] = float_value(row.get("weighted_hit_sum"))

    balanced_selection = read_json(f"{BALANCED_OUTPUT_REL}/candidate_selection_manifest.json")
    balanced_strata = {
        row["candidate_id"]: row.get("selected_stratum", "")
        for row in balanced_selection["selected_candidates"]
    }
    for candidate in rows.values():
        p2 = float(candidate["p2_weighted_hit_sum"])
        candidate["current_score_only"] = candidate["current_score"]
        candidate["p2_raw_weighted_hits_only"] = p2
        candidate["current_score_plus_log1p_p2"] = candidate["current_score"] + math.log1p(p2)
        candidate["gated_current_plus_log1p_p2"] = (
            candidate["current_score"] + math.log1p(p2) if p2 > 0.0 else 0.0
        )
        candidate["balanced_panel_stratum"] = balanced_strata.get(candidate["candidate_id"], "")
        candidate["truth_bucket"] = truth_bucket(candidate["truth_match_ratio"])
    ranked = list(rows.values())
    for mode in SCORE_MODES:
        for rank, row in enumerate(
            sorted(ranked, key=lambda item: (-float(item[mode]), item["candidate_id"])),
            start=1,
        ):
            row[f"{mode}_rank"] = rank
    return rows


def truth_bucket(value: float) -> str:
    if value >= 0.75:
        return "high_truth"
    if value <= 0.15:
        return "bad_control"
    return "mid_truth"


def build_pairwise_rows(candidates: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    pair_rows = read_csv(f"{HARD_PAIR_DIR_REL}/hard_pair_manifest.csv")
    out: list[dict[str, Any]] = []
    for pair in pair_rows:
        known_better_id = pair.get("known_better_candidate", "")
        candidate_a = pair.get("candidate_a_id", "")
        candidate_b = pair.get("candidate_b_id", "")
        known_worse_id = candidate_b if known_better_id == candidate_a else candidate_a
        better = candidates.get(known_better_id)
        worse = candidates.get(known_worse_id)
        if not better or not worse:
            continue
        row: dict[str, Any] = {
            "pair_id": pair.get("pair_id", ""),
            "known_better_candidate_id": known_better_id,
            "known_worse_candidate_id": known_worse_id,
            "known_better_truth_match_ratio": better["truth_match_ratio"],
            "known_worse_truth_match_ratio": worse["truth_match_ratio"],
            "current_scorer_preferred": pair.get("current_scorer_preferred", ""),
        }
        for mode in SCORE_MODES:
            better_score = float(better[mode])
            worse_score = float(worse[mode])
            if better_score > worse_score:
                preferred = "known_better"
            elif worse_score > better_score:
                preferred = "known_worse"
            else:
                preferred = "tie"
            row[f"{mode}_known_better_score"] = better_score
            row[f"{mode}_known_worse_score"] = worse_score
            row[f"{mode}_margin_better_minus_worse"] = better_score - worse_score
            row[f"{mode}_preferred_role"] = preferred
        out.append(row)
    return out


def pairwise_mode_summary(pair_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for mode in SCORE_MODES:
        preferred_values = [row[f"{mode}_preferred_role"] for row in pair_rows]
        margins = [float(row[f"{mode}_margin_better_minus_worse"]) for row in pair_rows]
        out.append(
            {
                "score_mode": mode,
                "pair_count": len(pair_rows),
                "known_better_preferred_count": sum(1 for value in preferred_values if value == "known_better"),
                "known_worse_preferred_count": sum(1 for value in preferred_values if value == "known_worse"),
                "tie_count": sum(1 for value in preferred_values if value == "tie"),
                "known_better_preferred_rate": sum(1 for value in preferred_values if value == "known_better")
                / len(pair_rows)
                if pair_rows
                else 0.0,
                "known_worse_inversion_rate": sum(1 for value in preferred_values if value == "known_worse")
                / len(pair_rows)
                if pair_rows
                else 0.0,
                "mean_margin_better_minus_worse": sum(margins) / len(margins) if margins else 0.0,
                "median_margin_better_minus_worse": median(margins) if margins else 0.0,
            }
        )
    return out


def group_summary(candidates: dict[str, dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates.values():
        grouped[str(row.get(group_key) or "none")].append(row)
    out: list[dict[str, Any]] = []
    for mode in SCORE_MODES:
        for group_value, rows in sorted(grouped.items()):
            scores = [float(row[mode]) for row in rows]
            ranks = [int(row[f"{mode}_rank"]) for row in rows]
            out.append(
                {
                    "score_mode": mode,
                    "group_key": group_key,
                    "group_value": group_value,
                    "candidate_count": len(rows),
                    "mean_score": sum(scores) / len(scores) if scores else 0.0,
                    "median_score": median(scores) if scores else 0.0,
                    "mean_rank": sum(ranks) / len(ranks) if ranks else 0.0,
                    "top20_count": sum(1 for rank in ranks if rank <= 20),
                    "top100_count": sum(1 for rank in ranks if rank <= 100),
                    "p2_hit_candidate_count": sum(1 for row in rows if int(row["p2_hit_count"]) > 0),
                    "mean_truth_match_ratio": sum(float(row["truth_match_ratio"]) for row in rows) / len(rows)
                    if rows
                    else 0.0,
                }
            )
    return out


def contrast_rows(candidates: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    contrasts = [
        ("role_known_better_vs_known_worse", "known_better_or_worse_role", "known_better", "known_worse"),
        ("truth_high_vs_bad_control", "truth_bucket", "high_truth", "bad_control"),
        ("balanced_high_truth_vs_bad_control", "balanced_panel_stratum", "high_truth_stable_fill", "bad_control_candidate"),
        ("balanced_rescue_vs_known_worse", "balanced_panel_stratum", "panel_rescue_known_better", "known_worse_pair_candidate"),
    ]
    out: list[dict[str, Any]] = []
    grouped_by_key: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for _, group_key, _, _ in contrasts:
        grouped_by_key[group_key] = defaultdict(list)
    for row in candidates.values():
        for group_key, grouped in grouped_by_key.items():
            grouped[str(row.get(group_key) or "none")].append(row)
    for mode in SCORE_MODES:
        for contrast_name, group_key, high_name, low_name in contrasts:
            high_rows = grouped_by_key[group_key].get(high_name, [])
            low_rows = grouped_by_key[group_key].get(low_name, [])
            total = len(high_rows) * len(low_rows)
            inversions = 0
            ties = 0
            for high in high_rows:
                for low in low_rows:
                    high_score = float(high[mode])
                    low_score = float(low[mode])
                    if low_score > high_score:
                        inversions += 1
                    elif low_score == high_score:
                        ties += 1
            high_scores = [float(row[mode]) for row in high_rows]
            low_scores = [float(row[mode]) for row in low_rows]
            out.append(
                {
                    "score_mode": mode,
                    "contrast_name": contrast_name,
                    "group_key": group_key,
                    "desired_high_group": high_name,
                    "desired_low_group": low_name,
                    "desired_high_count": len(high_rows),
                    "desired_low_count": len(low_rows),
                    "desired_high_mean_score": sum(high_scores) / len(high_scores) if high_scores else 0.0,
                    "desired_low_mean_score": sum(low_scores) / len(low_scores) if low_scores else 0.0,
                    "mean_score_margin": (sum(high_scores) / len(high_scores) if high_scores else 0.0)
                    - (sum(low_scores) / len(low_scores) if low_scores else 0.0),
                    "pairwise_comparison_count": total,
                    "undesired_pairwise_inversions": inversions,
                    "pairwise_ties": ties,
                    "undesired_inversion_rate": inversions / total if total else 0.0,
                }
            )
    return out


def panel_rescue_rows(candidates: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in sorted(
            candidates.values(),
            key=lambda item: (int(item["gated_current_plus_log1p_p2_rank"]), item["candidate_id"]),
        )
        if row.get("balanced_panel_stratum") == "panel_rescue_known_better"
    ]


def build_interpretation() -> dict[str, Any]:
    source_manifest = read_json(f"{SOURCE_OUTPUT_REL}/pilot_manifest.json")
    candidates = candidate_scores()
    pair_rows = build_pairwise_rows(candidates)
    pair_summary = pairwise_mode_summary(pair_rows)
    groups = (
        group_summary(candidates, "known_better_or_worse_role")
        + group_summary(candidates, "truth_bucket")
        + group_summary(candidates, "balanced_panel_stratum")
    )
    contrasts = contrast_rows(candidates)
    rescue = panel_rescue_rows(candidates)
    pair_summary_by_mode = {row["score_mode"]: row for row in pair_summary}
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "review_ready",
        "source_output_dir": SOURCE_OUTPUT_REL,
        "source_status": source_manifest["status"],
        "claim_mode": CLAIM_MODE,
        "dataset_status": source_manifest["config"].get("dataset_status"),
        "sample_index_based": True,
        "full_raw_ngram_rebuild_confirmed": False,
        "backend_impl": source_manifest["backend_impl"],
        "python_fallback_allowed": source_manifest["python_fallback_allowed"],
        "production_scorer_changes": False,
        "controlled_damage_ladder_claim": False,
        "full_hard_pair_report": False,
        "score_modes": list(SCORE_MODES),
        "summary": {
            "candidate_count": len(candidates),
            "pair_count": len(pair_rows),
            "source_total_hits": source_manifest["total_hit_count"],
            "source_candidates_with_hits": source_manifest["candidates_with_hits"],
            "panel_rescue_candidate_count": len(rescue),
            "panel_rescue_p2_hit_candidate_count": sum(1 for row in rescue if int(row["p2_hit_count"]) > 0),
            "current_pair_known_better_rate": pair_summary_by_mode["current_score_only"]["known_better_preferred_rate"],
            "p2_pair_known_better_rate": pair_summary_by_mode["p2_raw_weighted_hits_only"]["known_better_preferred_rate"],
            "combo_pair_known_better_rate": pair_summary_by_mode["current_score_plus_log1p_p2"]["known_better_preferred_rate"],
            "gated_combo_pair_known_better_rate": pair_summary_by_mode["gated_current_plus_log1p_p2"]["known_better_preferred_rate"],
            "current_pair_inversion_rate": pair_summary_by_mode["current_score_only"]["known_worse_inversion_rate"],
            "p2_pair_inversion_rate": pair_summary_by_mode["p2_raw_weighted_hits_only"]["known_worse_inversion_rate"],
            "combo_pair_inversion_rate": pair_summary_by_mode["current_score_plus_log1p_p2"]["known_worse_inversion_rate"],
            "gated_combo_pair_inversion_rate": pair_summary_by_mode["gated_current_plus_log1p_p2"]["known_worse_inversion_rate"],
        },
        "review_recommendation": {
            "next_step": "review_sample_index_matrix_interpretation_before_full_raw_rebuild_or_scorer_integration",
            "still_forbidden": [
                "production scorer changes",
                "controlled damage-ladder language",
                "full raw ngram claim",
                "full hard-pair report claim",
                "rescue-performance claim",
            ],
        },
    }
    return {
        "manifest": manifest,
        "candidate_score_rows": sorted(candidates.values(), key=lambda row: int(row["p2_raw_weighted_hits_only_rank"])),
        "pairwise_score_rows": pair_rows,
        "pairwise_mode_summary_rows": pair_summary,
        "group_summary_rows": groups,
        "contrast_rows": contrasts,
        "panel_rescue_rows": rescue,
    }


def write_outputs(payload: dict[str, Any]) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    manifest = payload["manifest"]
    write_json(output_dir / "interpretation_manifest.json", manifest)
    write_csv(output_dir / "candidate_score_rows.csv", payload["candidate_score_rows"])
    write_csv(output_dir / "pairwise_score_rows.csv", payload["pairwise_score_rows"])
    write_csv(output_dir / "pairwise_mode_summary_rows.csv", payload["pairwise_mode_summary_rows"])
    write_csv(output_dir / "group_summary_rows.csv", payload["group_summary_rows"])
    write_csv(output_dir / "contrast_rows.csv", payload["contrast_rows"])
    write_csv(output_dir / "panel_rescue_rows.csv", payload["panel_rescue_rows"])
    readout = [
        "# PhaseB N-Gram Hamming Sample-Index All-Candidate Matrix Interpretation v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- dataset status: `{manifest['dataset_status']}`",
        f"- sample-index based: `{manifest['sample_index_based']}`",
        f"- full raw ngram rebuild confirmed: `{manifest['full_raw_ngram_rebuild_confirmed']}`",
        f"- candidates: `{manifest['summary']['candidate_count']}`",
        f"- hard-pair rows evaluated: `{manifest['summary']['pair_count']}`",
        f"- source total hits: `{manifest['summary']['source_total_hits']}`",
        f"- source candidates with hits: `{manifest['summary']['source_candidates_with_hits']}`",
        "",
        "## Pairwise Preference Rates",
        "",
        f"- current known-better rate: `{manifest['summary']['current_pair_known_better_rate']:.6f}`",
        f"- P2 raw known-better rate: `{manifest['summary']['p2_pair_known_better_rate']:.6f}`",
        f"- current+log1p(P2) known-better rate: `{manifest['summary']['combo_pair_known_better_rate']:.6f}`",
        f"- gated current+log1p(P2) known-better rate: `{manifest['summary']['gated_combo_pair_known_better_rate']:.6f}`",
        "",
        "## Panel Rescue",
        "",
        f"- panel-rescue P2-hit candidates: `{manifest['summary']['panel_rescue_p2_hit_candidate_count']}` / `{manifest['summary']['panel_rescue_candidate_count']}`",
        "",
        "This is a sample-index interpretation. It must not be described as a full raw n-gram or controlled damage-ladder result.",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def run_interpretation() -> dict[str, Any]:
    payload = build_interpretation()
    write_outputs(payload)
    return payload["manifest"]


def main() -> None:
    manifest = run_interpretation()
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] pair_count={manifest['summary']['pair_count']}")


if __name__ == "__main__":
    main()
