from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Callable, Iterable


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_nonproduction_scorer_combination_v1"
SOURCE_OUTPUT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_nonproduction_scorer_design_v1"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_nonproduction_scorer_combination_v1"
)
CLAIM_MODE = "hard_pair_candidate_comparability"

SCORE_MODES = {
    "current_score_only": lambda row: float_value(row["current_score"]),
    "p2_raw_weighted_hits_only": lambda row: float_value(row["primary_score_raw_weighted_hits"]),
    "current_score_plus_log1p_p2": lambda row: float_value(row["current_score"])
    + float_value(row["primary_score_log1p_weighted_hits"]),
}

CONTRASTS = [
    ("known_better_vs_known_worse", "known_better_or_worse_role", "known_better", "known_worse"),
    ("high_truth_stable_fill_vs_bad_control", "selected_stratum", "high_truth_stable_fill", "bad_control_candidate"),
    (
        "known_better_pair_candidate_vs_panel_rescue_known_better",
        "selected_stratum",
        "known_better_pair_candidate",
        "panel_rescue_known_better",
    ),
]


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(rel_path: str) -> Any:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def read_csv(rel_path: str) -> list[dict[str, str]]:
    with (REPO_ROOT / rel_path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def float_value(value: Any) -> float:
    if value in ("", None):
        return 0.0
    return float(value)


def int_value(value: Any) -> int:
    if value in ("", None):
        return 0
    return int(float(value))


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


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


def source_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(f"{SOURCE_OUTPUT_REL}/candidate_design_rows.csv"):
        converted = dict(row)
        for key in [
            "current_score",
            "truth_match_ratio",
            "primary_score_raw_weighted_hits",
            "primary_score_log1p_weighted_hits",
            "source_total_weighted_hit_sum",
        ]:
            converted[key] = float_value(converted.get(key))
        for key in [
            "chunk_count_available",
            "comparison_hit_count",
            "p0_exact_hit_count",
            "pair_occurrence_count",
            "primary_hit_count",
            "primary_positive_row_count",
            "source_total_hit_count",
        ]:
            converted[key] = int_value(converted.get(key))
        converted["p0_audit_flag"] = bool_value(converted.get("p0_audit_flag"))
        rows.append(converted)
    return rows


def ranked_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = [dict(row) for row in rows]
    for mode_name, score_fn in SCORE_MODES.items():
        for row in out:
            row[f"{mode_name}_score"] = score_fn(row)
        ranked = sorted(out, key=lambda row: (-float(row[f"{mode_name}_score"]), row["candidate_id"]))
        for rank, row in enumerate(ranked, start=1):
            row[f"{mode_name}_rank"] = rank
    return sorted(out, key=lambda row: int(row["current_score_plus_log1p_p2_rank"]))


def group_rows(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key) or "no_recorded_pair_role")].append(row)
    return grouped


def mode_group_summary(rows: list[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    grouped = group_rows(rows, group_key)
    out: list[dict[str, Any]] = []
    for mode_name in SCORE_MODES:
        score_key = f"{mode_name}_score"
        rank_key = f"{mode_name}_rank"
        for group_value, group in sorted(grouped.items()):
            scores = [float(row[score_key]) for row in group]
            ranks = [int(row[rank_key]) for row in group]
            out.append(
                {
                    "score_mode": mode_name,
                    "group_key": group_key,
                    "group_value": group_value,
                    "candidate_count": len(group),
                    "mean_score": sum(scores) / len(scores) if scores else 0.0,
                    "median_score": median(scores) if scores else 0.0,
                    "min_score": min(scores) if scores else 0.0,
                    "max_score": max(scores) if scores else 0.0,
                    "mean_rank": sum(ranks) / len(ranks) if ranks else 0.0,
                    "top10_count": sum(1 for rank in ranks if rank <= 10),
                    "top20_count": sum(1 for rank in ranks if rank <= 20),
                    "top40_count": sum(1 for rank in ranks if rank <= 40),
                    "mean_truth_match_ratio": sum(float(row["truth_match_ratio"]) for row in group) / len(group)
                    if group
                    else 0.0,
                    "p0_audit_flag_count": sum(1 for row in group if row["p0_audit_flag"]),
                    "primary_hit_candidate_count": sum(1 for row in group if int(row["primary_hit_count"]) > 0),
                }
            )
    return out


def contrast_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for mode_name in SCORE_MODES:
        score_key = f"{mode_name}_score"
        rank_key = f"{mode_name}_rank"
        for contrast_name, group_key, desired_high_value, desired_low_value in CONTRASTS:
            grouped = group_rows(rows, group_key)
            high_rows = grouped.get(desired_high_value, [])
            low_rows = grouped.get(desired_low_value, [])
            high_scores = [float(row[score_key]) for row in high_rows]
            low_scores = [float(row[score_key]) for row in low_rows]
            high_ranks = [int(row[rank_key]) for row in high_rows]
            low_ranks = [int(row[rank_key]) for row in low_rows]
            pairwise_total = len(high_rows) * len(low_rows)
            inversions = 0
            ties = 0
            for high in high_rows:
                high_score = float(high[score_key])
                for low in low_rows:
                    low_score = float(low[score_key])
                    if low_score > high_score:
                        inversions += 1
                    elif low_score == high_score:
                        ties += 1
            out.append(
                {
                    "score_mode": mode_name,
                    "contrast_name": contrast_name,
                    "group_key": group_key,
                    "desired_high_group": desired_high_value,
                    "desired_low_group": desired_low_value,
                    "desired_high_count": len(high_rows),
                    "desired_low_count": len(low_rows),
                    "desired_high_mean_score": sum(high_scores) / len(high_scores) if high_scores else 0.0,
                    "desired_low_mean_score": sum(low_scores) / len(low_scores) if low_scores else 0.0,
                    "mean_score_margin": (sum(high_scores) / len(high_scores) if high_scores else 0.0)
                    - (sum(low_scores) / len(low_scores) if low_scores else 0.0),
                    "desired_high_top20_count": sum(1 for rank in high_ranks if rank <= 20),
                    "desired_low_top20_count": sum(1 for rank in low_ranks if rank <= 20),
                    "pairwise_comparison_count": pairwise_total,
                    "undesired_pairwise_inversions": inversions,
                    "pairwise_ties": ties,
                    "undesired_inversion_rate": inversions / pairwise_total if pairwise_total else 0.0,
                }
            )
    return out


def pair_inversion_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pair: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        source_pair_id = str(row.get("source_pair_id") or "")
        role = str(row.get("known_better_or_worse_role") or "")
        if source_pair_id and role in {"known_better", "known_worse"}:
            by_pair[source_pair_id][role].append(row)

    out: list[dict[str, Any]] = []
    for source_pair_id, role_rows in sorted(by_pair.items()):
        better_rows = role_rows.get("known_better", [])
        worse_rows = role_rows.get("known_worse", [])
        if not better_rows or not worse_rows:
            continue
        for mode_name in SCORE_MODES:
            score_key = f"{mode_name}_score"
            rank_key = f"{mode_name}_rank"
            for better in better_rows:
                for worse in worse_rows:
                    better_score = float(better[score_key])
                    worse_score = float(worse[score_key])
                    if better_score > worse_score:
                        preferred = "known_better"
                    elif worse_score > better_score:
                        preferred = "known_worse"
                    else:
                        preferred = "tie"
                    out.append(
                        {
                            "score_mode": mode_name,
                            "source_pair_id": source_pair_id,
                            "known_better_candidate_id": better["candidate_id"],
                            "known_worse_candidate_id": worse["candidate_id"],
                            "known_better_score": better_score,
                            "known_worse_score": worse_score,
                            "known_better_rank": better[rank_key],
                            "known_worse_rank": worse[rank_key],
                            "score_margin_better_minus_worse": better_score - worse_score,
                            "preferred_role": preferred,
                            "ranking_inversion": preferred == "known_worse",
                        }
                    )
    return out


def panel_rescue_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if row["selected_stratum"] != "panel_rescue_known_better":
            continue
        out.append(
            {
                "candidate_id": row["candidate_id"],
                "current_score": row["current_score"],
                "truth_match_ratio": row["truth_match_ratio"],
                "primary_score_raw_weighted_hits": row["primary_score_raw_weighted_hits"],
                "primary_score_log1p_weighted_hits": row["primary_score_log1p_weighted_hits"],
                "current_score_only_rank": row["current_score_only_rank"],
                "p2_raw_weighted_hits_only_rank": row["p2_raw_weighted_hits_only_rank"],
                "current_score_plus_log1p_p2_rank": row["current_score_plus_log1p_p2_rank"],
                "primary_hit_count": row["primary_hit_count"],
                "p0_audit_flag": row["p0_audit_flag"],
            }
        )
    return sorted(out, key=lambda row: int(row["current_score_plus_log1p_p2_rank"]))


def build_simulation() -> dict[str, Any]:
    design_manifest = read_json(f"{SOURCE_OUTPUT_REL}/design_manifest.json")
    rows = ranked_rows(source_rows())
    group_summary_rows = mode_group_summary(rows, "known_better_or_worse_role") + mode_group_summary(rows, "selected_stratum")
    contrast = contrast_rows(rows)
    pair_rows = pair_inversion_rows(rows)
    panel_rescue = panel_rescue_rows(rows)
    pair_summary: dict[str, dict[str, int]] = {}
    for mode_name in SCORE_MODES:
        mode_rows = [row for row in pair_rows if row["score_mode"] == mode_name]
        pair_summary[mode_name] = {
            "pair_comparison_count": len(mode_rows),
            "known_better_preferred_count": sum(1 for row in mode_rows if row["preferred_role"] == "known_better"),
            "known_worse_preferred_count": sum(1 for row in mode_rows if row["preferred_role"] == "known_worse"),
            "tie_count": sum(1 for row in mode_rows if row["preferred_role"] == "tie"),
        }

    selected_contrasts = {
        row["score_mode"] + "::" + row["contrast_name"]: row
        for row in contrast
        if row["contrast_name"] in {"known_better_vs_known_worse", "high_truth_stable_fill_vs_bad_control"}
    }
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "review_ready",
        "source_output_dir": SOURCE_OUTPUT_REL,
        "claim_mode": CLAIM_MODE,
        "source_status": design_manifest["status"],
        "scorer_design_only": True,
        "production_scorer_changes": False,
        "controlled_damage_ladder_claim": False,
        "broad_pilot": False,
        "full_hard_pair_report": False,
        "score_modes": list(SCORE_MODES.keys()),
        "summary": {
            "candidate_count": len(rows),
            "panel_rescue_candidate_count": len(panel_rescue),
            "panel_rescue_candidates_with_p2_hits": sum(1 for row in panel_rescue if int(row["primary_hit_count"]) > 0),
            "pair_summary": pair_summary,
            "current_known_better_vs_known_worse_mean_margin": selected_contrasts[
                "current_score_only::known_better_vs_known_worse"
            ]["mean_score_margin"],
            "p2_known_better_vs_known_worse_mean_margin": selected_contrasts[
                "p2_raw_weighted_hits_only::known_better_vs_known_worse"
            ]["mean_score_margin"],
            "combo_known_better_vs_known_worse_mean_margin": selected_contrasts[
                "current_score_plus_log1p_p2::known_better_vs_known_worse"
            ]["mean_score_margin"],
            "current_high_truth_vs_bad_control_mean_margin": selected_contrasts[
                "current_score_only::high_truth_stable_fill_vs_bad_control"
            ]["mean_score_margin"],
            "p2_high_truth_vs_bad_control_mean_margin": selected_contrasts[
                "p2_raw_weighted_hits_only::high_truth_stable_fill_vs_bad_control"
            ]["mean_score_margin"],
            "combo_high_truth_vs_bad_control_mean_margin": selected_contrasts[
                "current_score_plus_log1p_p2::high_truth_stable_fill_vs_bad_control"
            ]["mean_score_margin"],
        },
        "review_recommendation": {
            "next_step": "review_nonproduction_combination_simulation_before_any_integration",
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
        "candidate_score_rows": rows,
        "mode_group_summary_rows": group_summary_rows,
        "contrast_rows": contrast,
        "pair_inversion_rows": pair_rows,
        "panel_rescue_rows": panel_rescue,
    }


def write_outputs(payload: dict[str, Any]) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    manifest = payload["manifest"]
    write_json(output_dir / "simulation_manifest.json", manifest)
    write_csv(output_dir / "candidate_score_rows.csv", payload["candidate_score_rows"])
    write_csv(output_dir / "mode_group_summary_rows.csv", payload["mode_group_summary_rows"])
    write_csv(output_dir / "contrast_rows.csv", payload["contrast_rows"])
    write_csv(output_dir / "pair_inversion_rows.csv", payload["pair_inversion_rows"])
    write_csv(output_dir / "panel_rescue_rows.csv", payload["panel_rescue_rows"])

    readout = [
        "# PhaseB N-Gram Hamming Non-Production Scorer Combination v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- claim mode: `{manifest['claim_mode']}`",
        f"- scorer design only: `{manifest['scorer_design_only']}`",
        f"- production scorer changes: `{manifest['production_scorer_changes']}`",
        f"- controlled damage ladder claim: `{manifest['controlled_damage_ladder_claim']}`",
        f"- score modes: `{', '.join(manifest['score_modes'])}`",
        f"- candidates: `{manifest['summary']['candidate_count']}`",
        "",
        "## Mean Separation",
        "",
        f"- current known-better minus known-worse: `{manifest['summary']['current_known_better_vs_known_worse_mean_margin']:.6f}`",
        f"- P2 known-better minus known-worse: `{manifest['summary']['p2_known_better_vs_known_worse_mean_margin']:.6f}`",
        f"- current+log1p(P2) known-better minus known-worse: `{manifest['summary']['combo_known_better_vs_known_worse_mean_margin']:.6f}`",
        f"- current high-truth minus bad-control: `{manifest['summary']['current_high_truth_vs_bad_control_mean_margin']:.6f}`",
        f"- P2 high-truth minus bad-control: `{manifest['summary']['p2_high_truth_vs_bad_control_mean_margin']:.6f}`",
        f"- current+log1p(P2) high-truth minus bad-control: `{manifest['summary']['combo_high_truth_vs_bad_control_mean_margin']:.6f}`",
        "",
        "## Panel Rescue",
        "",
        f"- panel-rescue candidates with P2 hits: `{manifest['summary']['panel_rescue_candidates_with_p2_hits']}` / `{manifest['summary']['panel_rescue_candidate_count']}`",
        "",
        "## Boundary",
        "",
        "This is a non-production combination simulation. It changes no scorer behavior and makes no controlled damage-ladder or rescue-performance claim.",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def run_simulation() -> dict[str, Any]:
    payload = build_simulation()
    write_outputs(payload)
    return payload["manifest"]


def main() -> None:
    manifest = run_simulation()
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] score_modes={','.join(manifest['score_modes'])}")


if __name__ == "__main__":
    main()
