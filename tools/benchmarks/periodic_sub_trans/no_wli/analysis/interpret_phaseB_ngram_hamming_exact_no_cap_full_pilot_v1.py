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


RUN_LABEL = "phaseB_ngram_hamming_exact_no_cap_full_pilot_interpretation_v1"
SOURCE_OUTPUT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_exact_no_cap_full_pilot_v1"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_exact_no_cap_full_pilot_interpretation_v1"
)
CLAIM_MODE = "hard_pair_candidate_comparability"
FORBIDDEN_CLAIMS = (
    "scorer_improves_ranking",
    "scorer_rescues_damaged_text",
    "controlled_20_50_damage_ladder_validated",
    "representative_full_hard_pair_set",
)


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(rel_path: str) -> Any:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def read_csv(rel_path: str) -> list[dict[str, str]]:
    with (REPO_ROOT / rel_path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(rel_path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path = REPO_ROOT / rel_path
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_under_repo(path)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def group_sum(rows: list[dict[str, Any]], keys: tuple[str, ...], value_key: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(row[item] for item in keys)
        if key not in grouped:
            grouped[key] = {item: row[item] for item in keys}
            grouped[key]["hit_count"] = 0
            grouped[key]["row_count"] = 0
        grouped[key]["hit_count"] += int_value(row[value_key])
        grouped[key]["row_count"] += 1
    return sorted(grouped.values(), key=lambda row: tuple(str(row[item]) for item in keys))


def enrich_chunk_rows(
    chunk_rows: list[dict[str, str]],
    selection_by_candidate: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in chunk_rows:
        selected = selection_by_candidate.get(row["candidate_id"], {})
        enriched.append(
            {
                **row,
                "phrase_hit_count": int_value(row["phrase_hit_count"]),
                "weighted_hit_sum": float_value(row["weighted_hit_sum"]),
                "selected_stratum": selected.get("selected_stratum", ""),
                "known_better_or_worse_role": selected.get("known_better_or_worse_role", ""),
                "current_score": selected.get("current_score", ""),
                "truth_match_ratio": selected.get("truth_match_ratio", ""),
            }
        )
    return enriched


def enrich_hit_examples(
    hit_examples: list[dict[str, Any]],
    selection_by_candidate: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in hit_examples:
        hit = row["hit"]
        selected = selection_by_candidate.get(row["candidate_id"], {})
        enriched.append(
            {
                "candidate_id": row["candidate_id"],
                "candidate_chunk_id": row["candidate_chunk_id"],
                "selected_stratum": selected.get("selected_stratum", ""),
                "known_better_or_worse_role": selected.get("known_better_or_worse_role", ""),
                "profile_id": row["profile_id"],
                "ngram_order": int(row["ngram_order"]),
                "phrase_id": hit["phrase_id"],
                "hit_start": int(hit["hit_start"]),
                "hit_end": int(hit["hit_end"]),
                "total_phrase_hd": int(hit["total_phrase_hd"]),
                "max_word_hd": int(hit["max_word_hd"]),
                "normalised_phrase_hd": float(hit["normalised_phrase_hd"]),
                "phrase_log_count": float(hit["phrase_log_count"]),
                "word_hds": hit["word_hds"],
                "word_lengths": hit["word_lengths"],
            }
        )
    return enriched


def candidate_summary(
    selection_rows: list[dict[str, Any]],
    enriched_chunk_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in enriched_chunk_rows:
        rows_by_candidate[row["candidate_id"]].append(row)
    out: list[dict[str, Any]] = []
    for selected in selection_rows:
        candidate_id = selected["candidate_id"]
        rows = rows_by_candidate[candidate_id]
        hit_rows = [row for row in rows if int_value(row["phrase_hit_count"]) > 0]
        productive_profiles = sorted(
            {
                f"{row['profile_id']}|order{row['ngram_order']}"
                for row in hit_rows
            }
        )
        out.append(
            {
                "candidate_id": candidate_id,
                "selected_stratum": selected.get("selected_stratum", ""),
                "known_better_or_worse_role": selected.get("known_better_or_worse_role", ""),
                "current_score": selected.get("current_score", ""),
                "truth_match_ratio": selected.get("truth_match_ratio", ""),
                "pair_occurrence_count": selected.get("pair_occurrence_count", ""),
                "scan_rows": len(rows),
                "total_hit_count": sum(int_value(row["phrase_hit_count"]) for row in rows),
                "hit_row_count": len(hit_rows),
                "productive_profile_orders": ";".join(productive_profiles),
                "total_weighted_hit_sum": sum(float_value(row["weighted_hit_sum"]) for row in rows),
            }
        )
    return sorted(out, key=lambda row: (-int(row["total_hit_count"]), row["candidate_id"]))


def build_manifest() -> dict[str, Any]:
    source_manifest = read_json(f"{SOURCE_OUTPUT_REL}/pilot_manifest.json")
    chunk_rows = read_csv(f"{SOURCE_OUTPUT_REL}/chunk_feature_rows.csv")
    candidate_rows = read_csv(f"{SOURCE_OUTPUT_REL}/candidate_feature_rows.csv")
    timing_rows = read_csv(f"{SOURCE_OUTPUT_REL}/cell_timing_rows.csv")
    hit_examples = read_jsonl(f"{SOURCE_OUTPUT_REL}/debug_examples.jsonl")
    selection_rows = source_manifest["candidate_selection_manifest"]["selected_candidates"]
    selection_by_candidate = {row["candidate_id"]: row for row in selection_rows}

    enriched_chunk_rows = enrich_chunk_rows(chunk_rows, selection_by_candidate)
    enriched_hit_examples = enrich_hit_examples(hit_examples, selection_by_candidate)
    summary_by_candidate = candidate_summary(selection_rows, enriched_chunk_rows)
    summary_by_profile_order = group_sum(enriched_chunk_rows, ("profile_id", "ngram_order"), "phrase_hit_count")
    summary_by_stratum = group_sum(enriched_chunk_rows, ("selected_stratum",), "phrase_hit_count")
    summary_by_role = group_sum(enriched_chunk_rows, ("known_better_or_worse_role",), "phrase_hit_count")
    summary_by_candidate_profile_order = group_sum(
        enriched_chunk_rows,
        ("candidate_id", "selected_stratum", "known_better_or_worse_role", "profile_id", "ngram_order"),
        "phrase_hit_count",
    )
    summary_by_chunk = [
        row for row in sorted(
            enriched_chunk_rows,
            key=lambda item: (
                -int_value(item["phrase_hit_count"]),
                item["candidate_id"],
                int_value(item["chunk_index"]),
                item["profile_id"],
                int_value(item["ngram_order"]),
            ),
        )
        if int_value(row["phrase_hit_count"]) > 0
    ]

    total_hits = sum(int_value(row["phrase_hit_count"]) for row in enriched_chunk_rows)
    candidates_with_hits = sum(1 for row in summary_by_candidate if int_value(row["total_hit_count"]) > 0)
    productive_profile_orders = [
        f"{row['profile_id']}|order{row['ngram_order']}"
        for row in summary_by_profile_order
        if int_value(row["hit_count"]) > 0
    ]
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source_output_dir": SOURCE_OUTPUT_REL,
        "claim_mode": CLAIM_MODE,
        "source_status": source_manifest["status"],
        "source_backend_impl": source_manifest["backend_impl"],
        "source_python_fallback_allowed": source_manifest["python_fallback_allowed"],
        "hard_pair_candidate_stream_verified": source_manifest["candidate_source_preflight_manifest"][
            "hard_pair_candidate_stream_verified"
        ],
        "controlled_damage_stream_verified": source_manifest["candidate_source_preflight_manifest"][
            "controlled_damage_stream_verified"
        ],
        "broad_pilot": False,
        "full_hard_pair_report": False,
        "production_scorer_changes": False,
        "controlled_damage_ladder_claim": False,
        "forbidden_claims_made": [],
        "forbidden_claims": list(FORBIDDEN_CLAIMS),
        "row_counts": {
            "source_chunk_feature_rows": len(chunk_rows),
            "source_candidate_feature_rows": len(candidate_rows),
            "source_cell_timing_rows": len(timing_rows),
            "source_hit_example_rows": len(hit_examples),
            "selected_candidates": len(selection_rows),
        },
        "hit_summary": {
            "total_hits": total_hits,
            "candidates_with_hits": candidates_with_hits,
            "candidates_with_zero_hits": len(selection_rows) - candidates_with_hits,
            "productive_profile_orders": productive_profile_orders,
        },
        "observations": [
            "Hit signal is sparse in this bounded 10-candidate comparability sample.",
            "Only P1/P2 normal order-2 rows produced hits.",
            "P0 and all order-3 rows were zero-hit controls in this bounded sample.",
            "Hits appear on stable-fill and current-scorer-correct-good selected strata, not on known-worse or bad-control rows.",
        ],
        "next_recommendation": {
            "recommended_shape": "normal_order2_P1_P2_focused_bounded_expansion",
            "retain_controls": "keep P0 and order 3 as controls if reviewer wants continuity",
            "add_before_expansion": "bounded parity case for P2_conservative_len8_hd2 normal order 2 on a real non-zero-hit chunk",
            "still_defer": ["strict", "order_4", "P3", "P4", "broad_pilot", "full_hard_pair_report"],
        },
    }
    return {
        "manifest": manifest,
        "summary_by_candidate": summary_by_candidate,
        "summary_by_profile_order": summary_by_profile_order,
        "summary_by_stratum": summary_by_stratum,
        "summary_by_role": summary_by_role,
        "summary_by_candidate_profile_order": summary_by_candidate_profile_order,
        "summary_by_chunk": summary_by_chunk,
        "enriched_hit_examples": enriched_hit_examples,
    }


def write_outputs(payload: dict[str, Any]) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    manifest = payload["manifest"]
    write_json(output_dir / "interpretation_manifest.json", manifest)
    write_csv(output_dir / "hit_summary_by_candidate.csv", payload["summary_by_candidate"])
    write_csv(output_dir / "hit_summary_by_profile_order.csv", payload["summary_by_profile_order"])
    write_csv(output_dir / "hit_summary_by_stratum.csv", payload["summary_by_stratum"])
    write_csv(output_dir / "hit_summary_by_role.csv", payload["summary_by_role"])
    write_csv(output_dir / "hit_summary_by_candidate_profile_order.csv", payload["summary_by_candidate_profile_order"])
    write_csv(output_dir / "hit_summary_by_chunk.csv", payload["summary_by_chunk"])
    write_jsonl(output_dir / "hit_examples_enriched.jsonl", payload["enriched_hit_examples"])
    readout = [
        "# PhaseB N-Gram Hamming Exact No-Cap Full Pilot Interpretation v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- source output: `{manifest['source_output_dir']}`",
        f"- claim mode: `{manifest['claim_mode']}`",
        f"- broad pilot: `{manifest['broad_pilot']}`",
        f"- full hard-pair report: `{manifest['full_hard_pair_report']}`",
        f"- controlled damage ladder claim: `{manifest['controlled_damage_ladder_claim']}`",
        f"- total hits: `{manifest['hit_summary']['total_hits']}`",
        f"- candidates with hits: `{manifest['hit_summary']['candidates_with_hits']}`",
        f"- candidates with zero hits: `{manifest['hit_summary']['candidates_with_zero_hits']}`",
        f"- productive profile/orders: `{';'.join(manifest['hit_summary']['productive_profile_orders'])}`",
        "",
        "## Observations",
        "",
    ]
    readout.extend(f"- {item}" for item in manifest["observations"])
    readout.extend(
        [
            "",
            "## Recommendation",
            "",
            "- Next bounded expansion should focus on normal/order-2/P1/P2.",
            "- Keep P0 and order 3 only as controls unless reviewer asks otherwise.",
            "- Add a bounded P2 normal order-2 non-zero-hit parity case before expansion.",
            "- Do not add strict, order 4, P3/P4, broad pilot, full hard-pair report, or production scorer changes yet.",
        ]
    )
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def run_interpretation() -> dict[str, Any]:
    payload = build_manifest()
    write_outputs(payload)
    return payload["manifest"]


def main() -> None:
    manifest = run_interpretation()
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] total_hits={manifest['hit_summary']['total_hits']}")
    print(f"[{RUN_LABEL}] candidates_with_hits={manifest['hit_summary']['candidates_with_hits']}")


if __name__ == "__main__":
    main()
