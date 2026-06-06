from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
RUN_LABEL = "phaseB_failed_decryption_candidate_inventory_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / RUN_LABEL
LEGACY_ROOT = Path("F:/legacy/ready_for_archive/2026-06-01_repo_cleanup")
CONFIG = {
    "search_roots": (
        REPO_ROOT / "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1",
        REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1",
        REPO_ROOT / "planning/projects/no_wli",
        LEGACY_ROOT / "output/tools/benchmarks/solve_proof/legacy_import",
    ),
    "allowed_file_suffixes": (".json", ".jsonl", ".csv", ".md", ".txt", ".gz"),
    "candidate_keywords": (
        "candidate", "plaintext", "token_sequence", "rank", "score", "retained",
        "solver", "trial", "report", "sidecar", "chunk", "wli", "partial_text",
    ),
    "max_probe_bytes": 1_000_000,
}


def _source_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return "legacy_archive/" + path.resolve().relative_to(LEGACY_ROOT.resolve()).as_posix()


def _write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_inventory() -> dict[str, object]:
    roots = tuple(CONFIG["search_roots"])
    existing = [root for root in roots if root.exists()]
    rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for root in existing:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in CONFIG["allowed_file_suffixes"]:
                continue
            try:
                stat = path.stat()
                probe = path.read_bytes()[: int(CONFIG["max_probe_bytes"])]
                probe_text = probe.decode("utf-8", errors="ignore").lower()
                matched = sorted(word for word in CONFIG["candidate_keywords"] if word in probe_text or word in path.name.lower())
                candidate_like = bool(matched)
                rows.append({
                    "artifact_id": hashlib.sha256(_source_path(path).encode("utf-8")).hexdigest()[:24],
                    "source_path": _source_path(path),
                    "path_exists": True,
                    "file_suffix": path.suffix.lower(),
                    "file_size_bytes": stat.st_size,
                    "modified_time_utc_if_available": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "matched_keywords": "|".join(matched),
                    "parser_status": "probe_pass",
                    "candidate_like": candidate_like,
                    "notes": "read_only_inventory",
                })
            except Exception as exc:
                failures.append({"source_path": _source_path(path), "error": str(exc)})
    rows.sort(key=lambda row: str(row["source_path"]))
    candidate_rows = [row for row in rows if row["candidate_like"]]
    fields = (
        "artifact_id", "source_path", "path_exists", "file_suffix", "file_size_bytes",
        "modified_time_utc_if_available", "sha256", "matched_keywords", "parser_status",
        "candidate_like", "notes",
    )
    _write_csv(OUTPUT_DIR / "discovered_artifact_rows.csv", rows, fields)
    _write_csv(OUTPUT_DIR / "candidate_like_artifact_rows.csv", candidate_rows, fields)
    _write_csv(OUTPUT_DIR / "parse_failure_rows.csv", failures, ("source_path", "error"))
    root_rows = [{
        "configured_root": _source_path(root) if root.exists() else str(root).replace("\\", "/"),
        "exists": root.exists(),
        "artifact_count": sum(1 for row in rows if str(row["source_path"]).startswith(_source_path(root))) if root.exists() else 0,
    } for root in roots]
    _write_csv(OUTPUT_DIR / "source_root_summary_rows.csv", root_rows, ("configured_root", "exists", "artifact_count"))
    manifest = {
        "status": "pass" if candidate_rows else "blocked",
        "configured_search_roots": [row["configured_root"] for row in root_rows],
        "existing_search_roots": [row["configured_root"] for row in root_rows if row["exists"]],
        "missing_search_roots": [row["configured_root"] for row in root_rows if not row["exists"]],
        "artifact_count": len(rows),
        "candidate_like_artifact_count": len(candidate_rows),
        "parse_failure_count": len(failures),
        "selected_artifact_count": 2,
        "selected_artifacts": [
            "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/source/historical_partial_text_review_v1/unique_partial_text_rows.csv",
            "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/source/historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv",
        ],
        "blocked_reasons": [] if candidate_rows else ["no candidate-like artifacts found"],
        "production_scoring_change": False,
        "production_ranking_change": False,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "inventory_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "readout.md").write_text(
        f"# Failed-Decryption Candidate Inventory\n\n- status: `{manifest['status']}`\n"
        f"- artifacts: `{len(rows)}`\n- candidate-like artifacts: `{len(candidate_rows)}`\n"
        "- selected compact source artifacts: `2`\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    build_inventory()
