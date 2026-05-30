from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_balanced_readout_interpretation_v1"
SOURCE_OUTPUT_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_balanced_readout_v1"
OUTPUT_DIR_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_balanced_readout_interpretation_v1"
CLAIM_MODE = "hard_pair_candidate_comparability"


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


def stratum_decision_rows(candidate_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        grouped[row["selected_stratum"]].append(row)
    out: list[dict[str, Any]] = []
    for stratum, rows in sorted(grouped.items()):
        candidate_count = len(rows)
        candidates_with_hits = sum(1 for row in rows if int_value(row["hit_count"]) > 0)
        total_hits = sum(int_value(row["hit_count"]) for row in rows)
        total_weighted = sum(float_value(row["weighted_hit_sum"]) for row in rows)
        out.append(
            {
                "selected_stratum": stratum,
                "candidate_count": candidate_count,
                "candidates_with_hits": candidates_with_hits,
                "hit_candidate_rate": candidates_with_hits / candidate_count if candidate_count else 0.0,
                "total_hits": total_hits,
                "mean_hits_per_candidate": total_hits / candidate_count if candidate_count else 0.0,
                "total_weighted_hit_sum": total_weighted,
                "mean_weighted_hit_sum_per_candidate": total_weighted / candidate_count if candidate_count else 0.0,
                "mean_truth_match_ratio": sum(float_value(row["truth_match_ratio"]) for row in rows) / candidate_count
                if candidate_count
                else 0.0,
                "mean_current_score": sum(float_value(row["current_score"]) for row in rows) / candidate_count
                if candidate_count
                else 0.0,
            }
        )
    return sorted(out, key=lambda row: (-float(row["mean_hits_per_candidate"]), row["selected_stratum"]))


def role_decision_rows(candidate_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        grouped[row["known_better_or_worse_role"] or "no_recorded_pair_role"].append(row)
    out: list[dict[str, Any]] = []
    for role, rows in sorted(grouped.items()):
        candidate_count = len(rows)
        candidates_with_hits = sum(1 for row in rows if int_value(row["hit_count"]) > 0)
        total_hits = sum(int_value(row["hit_count"]) for row in rows)
        out.append(
            {
                "known_better_or_worse_role": role,
                "candidate_count": candidate_count,
                "candidates_with_hits": candidates_with_hits,
                "hit_candidate_rate": candidates_with_hits / candidate_count if candidate_count else 0.0,
                "total_hits": total_hits,
                "mean_hits_per_candidate": total_hits / candidate_count if candidate_count else 0.0,
                "mean_truth_match_ratio": sum(float_value(row["truth_match_ratio"]) for row in rows) / candidate_count
                if candidate_count
                else 0.0,
            }
        )
    return sorted(out, key=lambda row: (-float(row["mean_hits_per_candidate"]), row["known_better_or_worse_role"]))


def profile_redundancy_rows(candidate_profile_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_candidate: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in candidate_profile_rows:
        by_candidate[row["candidate_id"]][row["profile_id"]] = row
    out: list[dict[str, Any]] = []
    for candidate_id, profile_rows in sorted(by_candidate.items()):
        p1 = profile_rows.get("P1_word_analogue_len7_hd2", {})
        p2 = profile_rows.get("P2_conservative_len8_hd2", {})
        p0 = profile_rows.get("P0_exact_short", {})
        p1_hits = int_value(p1.get("hit_count", 0))
        p2_hits = int_value(p2.get("hit_count", 0))
        out.append(
            {
                "candidate_id": candidate_id,
                "selected_stratum": p1.get("selected_stratum") or p2.get("selected_stratum") or p0.get("selected_stratum", ""),
                "known_better_or_worse_role": p1.get("known_better_or_worse_role")
                or p2.get("known_better_or_worse_role")
                or p0.get("known_better_or_worse_role", ""),
                "p0_hits": int_value(p0.get("hit_count", 0)),
                "p1_hits": p1_hits,
                "p2_hits": p2_hits,
                "p1_minus_p2_hits": p1_hits - p2_hits,
                "p1_p2_same_hit_count": p1_hits == p2_hits,
            }
        )
    return out


def build_interpretation() -> dict[str, Any]:
    source_manifest = read_json(f"{SOURCE_OUTPUT_REL}/pilot_manifest.json")
    candidate_rows = read_csv(f"{SOURCE_OUTPUT_REL}/hit_summary_by_candidate.csv")
    candidate_profile_rows = read_csv(f"{SOURCE_OUTPUT_REL}/hit_summary_by_candidate_profile.csv")
    positive_chunks = read_csv(f"{SOURCE_OUTPUT_REL}/positive_chunk_rows.csv")
    stratum_rows = stratum_decision_rows(candidate_rows)
    role_rows = role_decision_rows(candidate_rows)
    redundancy_rows = profile_redundancy_rows(candidate_profile_rows)
    p1_p2_same = sum(1 for row in redundancy_rows if row["p1_p2_same_hit_count"])
    p0_positive = [row for row in positive_chunks if row.get("profile_id") == "P0_exact_short"]
    panel_rescue = next((row for row in stratum_rows if row["selected_stratum"] == "panel_rescue_known_better"), None)
    known_better = next((row for row in role_rows if row["known_better_or_worse_role"] == "known_better"), None)
    known_worse = next((row for row in role_rows if row["known_better_or_worse_role"] == "known_worse"), None)
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source_output_dir": SOURCE_OUTPUT_REL,
        "claim_mode": CLAIM_MODE,
        "source_status": source_manifest["status"],
        "source_backend_impl": source_manifest["backend_impl"],
        "source_python_fallback_allowed": source_manifest["python_fallback_allowed"],
        "broad_pilot": False,
        "full_hard_pair_report": False,
        "production_scorer_changes": False,
        "controlled_damage_ladder_claim": False,
        "summary": {
            "source_candidates": len(candidate_rows),
            "source_total_hits": source_manifest["total_hit_count"],
            "source_candidates_with_hits": source_manifest["candidates_with_hits"],
            "known_better_mean_hits": known_better["mean_hits_per_candidate"] if known_better else 0.0,
            "known_worse_mean_hits": known_worse["mean_hits_per_candidate"] if known_worse else 0.0,
            "panel_rescue_known_better_hits": panel_rescue["total_hits"] if panel_rescue else 0,
            "p1_p2_same_hit_count_candidates": p1_p2_same,
            "p1_p2_candidate_count": len(redundancy_rows),
            "p0_positive_chunk_count": len(p0_positive),
        },
        "decision_recommendation": {
            "next_step": "scorer_design_slice_without_production_change",
            "primary_signal": "normal_order2_P1_P2_weighted_hits",
            "use_p0": "keep as exact-control/audit feature, not primary signal",
            "p1_p2": "strongly redundant; choose one or keep both only for audit until scorer design review",
            "panel_rescue": "do not make rescue claims; investigate why selected rescue-known-better rows were zero-hit",
            "still_forbidden": [
                "production scorer changes",
                "controlled damage-ladder language",
                "strict/order4/P3/P4 expansion",
                "full hard-pair report",
            ],
        },
    }
    return {
        "manifest": manifest,
        "stratum_decision_rows": stratum_rows,
        "role_decision_rows": role_rows,
        "profile_redundancy_rows": redundancy_rows,
        "p0_positive_chunk_rows": p0_positive,
    }


def write_outputs(payload: dict[str, Any]) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    manifest = payload["manifest"]
    write_json(output_dir / "decision_manifest.json", manifest)
    write_csv(output_dir / "stratum_decision_rows.csv", payload["stratum_decision_rows"])
    write_csv(output_dir / "role_decision_rows.csv", payload["role_decision_rows"])
    write_csv(output_dir / "profile_redundancy_rows.csv", payload["profile_redundancy_rows"])
    write_csv(output_dir / "p0_positive_chunk_rows.csv", payload["p0_positive_chunk_rows"])
    readout = [
        "# PhaseB N-Gram Hamming Balanced Readout Interpretation v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- claim mode: `{manifest['claim_mode']}`",
        f"- broad pilot: `{manifest['broad_pilot']}`",
        f"- full hard-pair report: `{manifest['full_hard_pair_report']}`",
        f"- production scorer changes: `{manifest['production_scorer_changes']}`",
        f"- controlled damage ladder claim: `{manifest['controlled_damage_ladder_claim']}`",
        f"- source candidates: `{manifest['summary']['source_candidates']}`",
        f"- source total hits: `{manifest['summary']['source_total_hits']}`",
        f"- known-better mean hits: `{manifest['summary']['known_better_mean_hits']:.3f}`",
        f"- known-worse mean hits: `{manifest['summary']['known_worse_mean_hits']:.3f}`",
        f"- panel-rescue known-better hits: `{manifest['summary']['panel_rescue_known_better_hits']}`",
        f"- P1/P2 same-hit-count candidates: `{manifest['summary']['p1_p2_same_hit_count_candidates']}` / `{manifest['summary']['p1_p2_candidate_count']}`",
        f"- P0 positive chunk rows: `{manifest['summary']['p0_positive_chunk_count']}`",
        "",
        "## Recommendation",
        "",
        "- Move to a scorer-design slice, but do not change production scorer behavior yet.",
        "- Use normal/order-2/P1/P2 weighted hits as the primary candidate signal under review.",
        "- Keep P0 only as an exact-control/audit feature for now.",
        "- Treat P1/P2 as probably redundant until a design review decides whether to keep both.",
        "- Do not make rescue claims until the zero-hit panel-rescue stratum is understood.",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def run_interpretation() -> dict[str, Any]:
    payload = build_interpretation()
    write_outputs(payload)
    return payload["manifest"]


def main() -> None:
    manifest = run_interpretation()
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] source_total_hits={manifest['summary']['source_total_hits']}")


if __name__ == "__main__":
    main()
