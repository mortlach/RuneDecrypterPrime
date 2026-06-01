from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_full_raw_provenance_review_pack_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_provenance_review_pack_v1"
)
SHARD_PROVENANCE_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1"
)
SHARD_ROOT_PARENT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_asset_shards_v1"
)
CONTEXT_FILES_REL = (
    "planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_phrase_coherence_v3_2_canon_review.md",
    "planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md",
    "planning/projects/no_wli/00_CURRENT_STATE.md",
    "planning/projects/no_wli/04_ACTIVE_RUNBOOK.md",
)
SOURCE_FILES_REL = (
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/summarise_phaseB_ngram_hamming_full_raw_asset_shards_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_provenance_review_pack_v1.py",
)
LIVE_LOG_FILES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shards_v1/full_raw_asset_shards_optimized_resume_20260530_164433.log",
    "planning/projects/no_wli/50_console_and_watch_logs/phaseB_ngram_hamming_full_raw_asset_shards_resume_2026-05-31.log",
)
NO_BROAD_SCAN_LAUNCHED = True
NO_PRODUCTION_SCORER_CHANGES = True


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def posixish(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): posixish(item) for key, item in value.items()}
    if isinstance(value, list):
        return [posixish(item) for item in value]
    if isinstance(value, str):
        return value.replace("\\", "/")
    return value


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(posixish(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_under_repo(path)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_shard_run_root(parent: Path | None = None) -> Path | None:
    root_parent = parent or (REPO_ROOT / SHARD_ROOT_PARENT_REL)
    candidates = [
        path
        for path in root_parent.iterdir()
        if path.is_dir() and (path / "shard_build_config.json").exists()
    ] if root_parent.exists() else []
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def copy_file_into_pack(source_rel: str, pack_root: Path, section: str) -> dict[str, Any]:
    source = REPO_ROOT / source_rel
    row = {
        "source_path": source_rel,
        "exists": source.exists(),
        "sha256": "",
        "pack_path": "",
    }
    if not source.exists():
        return row
    destination = pack_root / section / source_rel
    ensure_under_repo(destination)
    shutil.copy2(source, destination)
    row["sha256"] = sha256_file(source)
    row["pack_path"] = repo_rel(destination)
    return row


def copy_run_root_file(run_root: Path | None, file_name: str, pack_root: Path) -> dict[str, Any]:
    if run_root is None:
        return {"source_path": "", "exists": False, "sha256": "", "pack_path": "", "file_name": file_name}
    source = run_root / file_name
    row = {
        "source_path": repo_rel(source) if source.exists() else f"{repo_rel(run_root)}/{file_name}",
        "exists": source.exists(),
        "sha256": "",
        "pack_path": "",
        "file_name": file_name,
    }
    if not source.exists():
        return row
    destination = pack_root / "20_run_root" / file_name
    ensure_under_repo(destination)
    shutil.copy2(source, destination)
    row["sha256"] = sha256_file(source)
    row["pack_path"] = repo_rel(destination)
    return row


def normal_strict_row_counts(output_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str, str], dict[str, int]] = defaultdict(
        lambda: {"output_file_count": 0, "aggregate_rows": 0, "dictionary_kept_rows": 0, "count_sum": 0}
    )
    for row in output_rows:
        key = (
            str(row.get("ngram_order", "")),
            str(row.get("dictionary_cut", "")),
            str(row.get("direction", "")),
        )
        totals[key]["output_file_count"] += 1
        for field in ("aggregate_rows", "dictionary_kept_rows", "count_sum"):
            totals[key][field] += int(row.get(field, 0) or 0)
    return [
        {
            "ngram_order": order,
            "dictionary_cut": cut,
            "direction": direction,
            **counts,
        }
        for (order, cut, direction), counts in sorted(totals.items())
    ]


def csv_data_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _row in reader)


def checklist_rows(
    provenance: dict[str, Any],
    output_rows: list[dict[str, str]],
    copied_files: list[dict[str, Any]],
) -> list[dict[str, str]]:
    provenance_pass = provenance.get("status") == "pass"
    copied_by_source = {row["source_path"]: row for row in copied_files}
    provenance_dir = REPO_ROOT / SHARD_PROVENANCE_DIR_REL
    phrase_distribution_rows = csv_data_row_count(provenance_dir / "phrase_length_distribution_rows.csv")
    word_distribution_rows = csv_data_row_count(provenance_dir / "word_length_distribution_rows.csv")
    return [
        checklist_row("shard_count_total", bool(provenance.get("total_shards")), str(provenance.get("total_shards", ""))),
        checklist_row("shard_count_pass", provenance_pass, f"{provenance.get('completed_shards', 0)} / {provenance.get('total_shards', 0)}"),
        checklist_row("shard_count_failed", int(provenance.get("failed_shards", 0) or 0) == 0, str(provenance.get("failed_shards", ""))),
        checklist_row("missing_shard_list", provenance_pass, str(provenance.get("missing_shards", ""))),
        checklist_row("source_bytes_covered", provenance_pass, f"{provenance.get('source_bytes_completed', 0)} / {provenance.get('source_bytes_total', 0)}"),
        checklist_row(
            "order_cut_direction_counts",
            bool(provenance.get("output_count_by_order_cut_direction")),
            str(len(provenance.get("output_count_by_order_cut_direction", []))),
        ),
        checklist_row("normal_strict_row_counts", bool(output_rows), str(len(normal_strict_row_counts(output_rows)))),
        checklist_row("phrase_length_distributions", phrase_distribution_rows > 0, f"rows={phrase_distribution_rows}"),
        checklist_row("word_length_distributions", word_distribution_rows > 0, f"rows={word_distribution_rows}"),
        checklist_row(
            "duplicate_collapse_metadata",
            bool(provenance.get("aggregate_rows") or provenance.get("dictionary_kept_rows")),
            f"aggregate_rows={provenance.get('aggregate_rows', 0)} dictionary_kept_rows={provenance.get('dictionary_kept_rows', 0)}",
        ),
        checklist_row("count_log_count_availability", all(row.get("count_sum", "") != "" for row in output_rows), str(len(output_rows))),
        checklist_row("manifest_hashes", any(row.get("sha256") for row in copied_files), str(sum(1 for row in copied_files if row.get("sha256")))),
        checklist_row(
            "run_logs",
            any(copied_by_source.get(path, {}).get("exists") for path in LIVE_LOG_FILES_REL),
            str(sum(1 for path in LIVE_LOG_FILES_REL if copied_by_source.get(path, {}).get("exists"))),
        ),
        checklist_row("resume_interruption_history", True, "documented in run logs and planning notes"),
        checklist_row("known_limitations", True, "partial pack remains blocked until full raw provenance passes"),
    ]


def checklist_row(name: str, ready: bool, evidence: str) -> dict[str, str]:
    return {
        "check": name,
        "status": "present" if ready else "pending",
        "evidence": evidence,
    }


def build_review_pack(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    provenance_dir = REPO_ROOT / SHARD_PROVENANCE_DIR_REL
    provenance = read_json_if_exists(provenance_dir / "shard_provenance_manifest.json")
    output_rows = read_csv_rows(provenance_dir / "output_file_rows.csv")
    run_root = REPO_ROOT / provenance["run_root"] if provenance.get("run_root") else latest_shard_run_root()

    copied_files: list[dict[str, Any]] = []
    for file_name in ("shard_build_config.json", "shard_build_manifest.json"):
        copied_files.append(copy_run_root_file(run_root, file_name, selected_output_dir))
    for rel_path in (
        f"{SHARD_PROVENANCE_DIR_REL}/shard_provenance_manifest.json",
        f"{SHARD_PROVENANCE_DIR_REL}/shard_rows.csv",
        f"{SHARD_PROVENANCE_DIR_REL}/output_file_rows.csv",
        f"{SHARD_PROVENANCE_DIR_REL}/missing_shard_rows.csv",
        f"{SHARD_PROVENANCE_DIR_REL}/missing_required_output_combo_rows.csv",
        f"{SHARD_PROVENANCE_DIR_REL}/phrase_length_distribution_rows.csv",
        f"{SHARD_PROVENANCE_DIR_REL}/word_length_distribution_rows.csv",
        f"{SHARD_PROVENANCE_DIR_REL}/readout.md",
        *LIVE_LOG_FILES_REL,
    ):
        copied_files.append(copy_file_into_pack(rel_path, selected_output_dir, "10_evidence"))
    for rel_path in CONTEXT_FILES_REL:
        copied_files.append(copy_file_into_pack(rel_path, selected_output_dir, "30_context"))
    for rel_path in SOURCE_FILES_REL:
        copied_files.append(copy_file_into_pack(rel_path, selected_output_dir, "40_source"))

    checklist = checklist_rows(provenance, output_rows, copied_files)
    row_counts = normal_strict_row_counts(output_rows)
    provenance_pass = provenance.get("status") == "pass" and provenance.get("full_raw_ngram_rebuild_confirmed") is True
    missing_files = [row["source_path"] for row in copied_files if not row["exists"]]
    pending_checks = [row["check"] for row in checklist if row["status"] != "present"]
    review_ready = provenance_pass and not missing_files and not pending_checks
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "review_ready" if review_ready else "blocked",
        "blocked_reasons": blocked_reasons(provenance, missing_files, pending_checks),
        "provenance_status": provenance.get("status", ""),
        "full_raw_ngram_rebuild_confirmed": provenance.get("full_raw_ngram_rebuild_confirmed", False),
        "completed_shards": provenance.get("completed_shards", 0),
        "total_shards": provenance.get("total_shards", 0),
        "missing_shards": provenance.get("missing_shards", 0),
        "failed_shards": provenance.get("failed_shards", 0),
        "source_bytes_completed_fraction": provenance.get("source_bytes_completed_fraction", 0.0),
        "run_root": provenance.get("run_root", repo_rel(run_root) if run_root else ""),
        "copied_files": copied_files,
        "missing_files": missing_files,
        "checklist_rows": checklist,
        "pending_review_checks": pending_checks,
        "normal_strict_row_counts": row_counts,
        "phrase_length_distribution_rows": csv_data_row_count(
            provenance_dir / "phrase_length_distribution_rows.csv"
        ),
        "word_length_distribution_rows": csv_data_row_count(
            provenance_dir / "word_length_distribution_rows.csv"
        ),
        "no_broad_scan_launched": NO_BROAD_SCAN_LAUNCHED,
        "no_production_scorer_changes": NO_PRODUCTION_SCORER_CHANGES,
    }
    write_json(selected_output_dir / "review_pack_manifest.json", manifest)
    write_csv(selected_output_dir / "review_checklist.csv", checklist)
    write_csv(selected_output_dir / "normal_strict_row_counts.csv", row_counts)
    write_readout(selected_output_dir / "README.md", manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] completed_shards={manifest['completed_shards']}/{manifest['total_shards']}")
    return manifest


def blocked_reasons(
    provenance: dict[str, Any],
    missing_files: list[str],
    pending_checks: list[str],
) -> list[str]:
    reasons: list[str] = []
    if provenance.get("status") != "pass":
        reasons.append("full raw shard provenance status is not pass")
    if provenance.get("full_raw_ngram_rebuild_confirmed") is not True:
        reasons.append("full raw n-gram rebuild is not confirmed")
    if int(provenance.get("missing_shards", 0) or 0):
        reasons.append("one or more expected shards are missing")
    if int(provenance.get("failed_shards", 0) or 0):
        reasons.append("one or more shards are failed")
    if missing_files:
        reasons.append("one or more review-pack evidence files are missing")
    if pending_checks:
        reasons.append("one or more required provenance review checks are pending")
    return reasons


def write_readout(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB N-Gram Hamming Full Raw Provenance Review Pack v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- provenance status: `{manifest['provenance_status']}`",
        f"- full raw confirmed: `{manifest['full_raw_ngram_rebuild_confirmed']}`",
        f"- completed shards: `{manifest['completed_shards']} / {manifest['total_shards']}`",
        f"- missing shards: `{manifest['missing_shards']}`",
        f"- failed shards: `{manifest['failed_shards']}`",
        f"- source bytes completed fraction: `{manifest['source_bytes_completed_fraction']:.6f}`",
        f"- broad scan launched: `{not manifest['no_broad_scan_launched']}`",
        f"- production scorer changes: `{not manifest['no_production_scorer_changes']}`",
        "",
        "This pack assembles provenance evidence only. A blocked pack is useful for",
        "handoff and drift checking, but it must not be treated as full raw approval.",
    ]
    if manifest["blocked_reasons"]:
        lines.append("")
        lines.append("Blocked reasons:")
        lines.extend(f"- {reason}" for reason in manifest["blocked_reasons"])
    if manifest["pending_review_checks"]:
        lines.append("")
        lines.append("Pending review checks:")
        lines.extend(f"- {check}" for check in manifest["pending_review_checks"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    build_review_pack()


if __name__ == "__main__":
    main()
