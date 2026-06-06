from __future__ import annotations

import csv
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
FIXTURE_DIR = REPO_ROOT / "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/fixture/phaseB_failed_decryption_retained_candidate_fixture_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_retained_candidate_fixture_validation_v1"


def validate_fixture() -> dict[str, object]:
    candidates = list(csv.DictReader((FIXTURE_DIR / "retained_candidate_rows.csv").open(encoding="utf-8", newline="")))
    chunks = list(csv.DictReader((FIXTURE_DIR / "candidate_chunk_rows.csv").open(encoding="utf-8", newline="")))
    pairs = list(csv.DictReader((FIXTURE_DIR / "candidate_pair_rows.csv").open(encoding="utf-8", newline="")))
    sources = {row["source_artifact_id"] for row in csv.DictReader((FIXTURE_DIR / "source_artifact_rows.csv").open(encoding="utf-8", newline=""))}
    failures: list[dict[str, str]] = []
    candidate_keys: set[tuple[str, str]] = set()
    for row in candidates:
        key = (row["trial_id"], row["candidate_id"])
        if not all(key):
            failures.append({"check": "candidate_identity", "row_id": row["candidate_id"], "detail": "missing trial_id or candidate_id"})
        if key in candidate_keys:
            failures.append({"check": "candidate_unique_within_trial", "row_id": row["candidate_id"], "detail": row["trial_id"]})
        candidate_keys.add(key)
        if row["source_artifact_id"] not in sources:
            failures.append({"check": "source_artifact_ref", "row_id": row["candidate_id"], "detail": row["source_artifact_id"]})
        tokens = json.loads(row["candidate_token_ids_json"]) if row["candidate_token_ids_json"] else []
        if not tokens and not row["candidate_text"]:
            failures.append({"check": "scoreable_payload", "row_id": row["candidate_id"], "detail": "no text or tokens"})
        if len(tokens) != int(row["candidate_token_count"]):
            failures.append({"check": "token_count", "row_id": row["candidate_id"], "detail": "payload count mismatch"})
    for row in chunks:
        if (row["trial_id"], row["candidate_id"]) not in candidate_keys:
            failures.append({"check": "chunk_candidate_ref", "row_id": row["chunk_id"], "detail": row["candidate_id"]})
    for row in pairs:
        for field in ("candidate_a_id", "candidate_b_id"):
            if (row["trial_id"], row[field]) not in candidate_keys:
                failures.append({"check": "pair_candidate_ref", "row_id": row["pair_id"], "detail": row[field]})
        if row["baseline_winner_id"] and row["baseline_winner_id"] not in (row["candidate_a_id"], row["candidate_b_id"]):
            failures.append({"check": "baseline_winner_ref", "row_id": row["pair_id"], "detail": row["baseline_winner_id"]})
        if row["gold_winner_id"] and not row["gold_label_source"]:
            failures.append({"check": "gold_label_source", "row_id": row["pair_id"], "detail": "missing"})
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_DIR / "validation_failure_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("check", "row_id", "detail"))
        writer.writeheader()
        writer.writerows(failures)
    manifest = {
        "status": "pass" if not failures else "blocked",
        "fixture_id": "phaseB_failed_decryption_retained_candidate_fixture_v1",
        "candidate_count": len(candidates), "chunk_count": len(chunks), "pair_count": len(pairs),
        "failure_count": len(failures), "production_scoring_change": False,
        "production_ranking_change": False, "absolute_local_paths_present": False,
    }
    (OUTPUT_DIR / "validation_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "readout.md").write_text(
        f"# Failed-Decryption Fixture Validation\n\n- status: `{manifest['status']}`\n"
        f"- candidates: `{len(candidates)}`\n- pairs: `{len(pairs)}`\n- failures: `{len(failures)}`\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    validate_fixture()
