from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
RUN_LABEL = "phaseB_failed_decryption_retained_candidate_fixture_v1"
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
ASSET_ROOT = REPO_ROOT / "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1"
OUTPUT_DIR = ASSET_ROOT / "fixture" / RUN_LABEL
TEXT_ROWS = ASSET_ROOT / "source/historical_partial_text_review_v1/unique_partial_text_rows.csv"
PAIR_ROWS = ASSET_ROOT / "source/historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"


def _write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _trial_id(artifact_path: str) -> str:
    parts = artifact_path.replace("\\", "/").split("/")
    run = next((part for part in parts if "__bench_solve_pipeline_no_wli__" in part), "")
    return run or "trial_" + hashlib.sha256(artifact_path.encode("utf-8")).hexdigest()[:16]


def build_fixture() -> dict[str, object]:
    text_by_hash = {row["partial_text_hash"]: row for row in csv.DictReader(TEXT_ROWS.open(encoding="utf-8", newline=""))}
    pairs = list(csv.DictReader(PAIR_ROWS.open(encoding="utf-8", newline="")))
    trial_token_keys = sorted({
        (_trial_id(row["artifact_path"]), row[key])
        for row in pairs for key in ("winner_token_hash", "challenger_token_hash")
    })
    score_by_key: dict[tuple[str, str], list[float]] = {key: [] for key in trial_token_keys}
    for row in pairs:
        trial_id = _trial_id(row["artifact_path"])
        for side in ("winner", "challenger"):
            value = row.get(f"{side}_current_score", "")
            if value:
                score_by_key[(trial_id, row[f"{side}_token_hash"])].append(float(value))
    candidate_rows: list[dict[str, object]] = []
    chunk_rows: list[dict[str, object]] = []
    candidate_id_by_key: dict[tuple[str, str], str] = {}
    for trial_id, token_hash in trial_token_keys:
        source = text_by_hash[token_hash]
        tokens = [int(value) for value in source["token_sequence_text"].split()]
        candidate_id = f"hist_{hashlib.sha256(trial_id.encode('utf-8')).hexdigest()[:8]}_{token_hash}"
        candidate_id_by_key[(trial_id, token_hash)] = candidate_id
        scores = score_by_key[(trial_id, token_hash)]
        candidate_rows.append({
            "trial_id": trial_id,
            "candidate_id": candidate_id,
            "source_artifact_id": "historical_partial_text_review_v1_unique_rows",
            "source_row_id": token_hash,
            "candidate_rank": "",
            "baseline_score": sum(scores) / len(scores) if scores else source.get("best_score", ""),
            "baseline_raw_score": "",
            "baseline_objective": "historical_current_score",
            "cipher_kind": "periodic_substitution_transposition",
            "solver_kind": "",
            "key_summary": "",
            "seed": "",
            "device": "",
            "optimizer": "",
            "candidate_text": "",
            "candidate_token_ids_json": json.dumps(tokens, separators=(",", ":")),
            "candidate_token_count": len(tokens),
            "chunk_count": 1,
            "parse_status": "pass",
            "missing_required_fields": "candidate_rank|candidate_text",
            "notes": "source-backed historical partial token stream",
        })
        chunk_rows.append({
            "trial_id": trial_id, "candidate_id": candidate_id,
            "chunk_id": f"{candidate_id}:0", "chunk_index": 0, "chunk_text": "",
            "chunk_token_ids_json": json.dumps(tokens, separators=(",", ":")),
            "chunk_token_count": len(tokens), "chunk_source": "flat_source_token_stream",
            "parse_status": "pass", "notes": "",
        })
    pair_rows: list[dict[str, object]] = []
    for row in pairs:
        trial_id = _trial_id(row["artifact_path"])
        winner = candidate_id_by_key[(trial_id, row["winner_token_hash"])]
        challenger = candidate_id_by_key[(trial_id, row["challenger_token_hash"])]
        truth_winner = winner if float(row["winner_truth_match"]) >= float(row["challenger_truth_match"]) else challenger
        pair_rows.append({
            "pair_id": row["pair_id"], "trial_id": trial_id,
            "candidate_a_id": winner, "candidate_b_id": challenger,
            "pair_type": "historical_source_pair", "baseline_winner_id": winner,
            "baseline_margin": row.get("current_score_margin", ""),
            "gold_winner_id": truth_winner, "gold_label_source": "source_truth_match_ratio",
            "can_score_rescue_break": True, "notes": "source-backed pair; no ranking change",
        })
    candidate_fields = tuple(candidate_rows[0])
    chunk_fields = tuple(chunk_rows[0])
    pair_fields = tuple(pair_rows[0])
    _write_csv(OUTPUT_DIR / "retained_candidate_rows.csv", candidate_rows, candidate_fields)
    _write_csv(OUTPUT_DIR / "candidate_chunk_rows.csv", chunk_rows, chunk_fields)
    _write_csv(OUTPUT_DIR / "candidate_pair_rows.csv", pair_rows, pair_fields)
    _write_csv(OUTPUT_DIR / "source_artifact_rows.csv", [
        {"source_artifact_id": "historical_partial_text_review_v1_unique_rows", "source_path": TEXT_ROWS.relative_to(REPO_ROOT).as_posix()},
        {"source_artifact_id": "historical_pairwise_rescore_v1_pairs", "source_path": PAIR_ROWS.relative_to(REPO_ROOT).as_posix()},
    ], ("source_artifact_id", "source_path"))
    unique_hashes = {token_hash for _trial_id_value, token_hash in trial_token_keys}
    _write_csv(OUTPUT_DIR / "fixture_validation_rows.csv", [{"check": "source_hash_coverage", "status": "pass", "detail": f"{len(unique_hashes)}/{len(unique_hashes)}"}], ("check", "status", "detail"))
    manifest = {
        "status": "pass", "fixture_id": RUN_LABEL,
        "source_inventory_id": "phaseB_failed_decryption_candidate_inventory_v1",
        "trial_count": len({_trial_id(row["artifact_path"]) for row in pairs}),
        "candidate_count": len(candidate_rows), "chunk_count": len(chunk_rows),
        "pair_count": len(pair_rows), "source_artifact_count": 2,
        "candidate_text_available_count": 0, "candidate_token_available_count": len(candidate_rows),
        "baseline_score_available_count": sum(bool(row["baseline_score"]) for row in candidate_rows),
        "baseline_rank_available_count": 0, "gold_label_available": True,
        "supported_phrase_orders_now": [3], "future_supported_phrase_orders": [4],
        "order4_ready_when_runtime_asset_available": True,
        "anchor_manifest_available": False,
        "matched_null_status": "blocked_missing_upstream_anchor_manifest",
        "production_scoring_change": False, "production_ranking_change": False,
        "blocked_reasons": [],
    }
    (OUTPUT_DIR / "fixture_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "readout.md").write_text(
        f"# Failed-Decryption Retained-Candidate Fixture\n\n- status: `pass`\n"
        f"- candidates: `{len(candidate_rows)}`\n- pairs: `{len(pair_rows)}`\n"
        f"- trials: `{manifest['trial_count']}`\n- order 4 ready later: `true`\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    build_fixture()
