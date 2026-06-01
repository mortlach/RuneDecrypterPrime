from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_full_raw_language_asset_pack_v1"
ASSET_HOME_REL = "assets/ngram_hamming/phaseB_full_raw_v1"
SHARD_PROVENANCE_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1"
)
PROVENANCE_FILES = (
    "shard_provenance_manifest.json",
    "shard_rows.csv",
    "output_file_rows.csv",
    "missing_shard_rows.csv",
    "missing_required_output_combo_rows.csv",
    "phrase_length_distribution_rows.csv",
    "word_length_distribution_rows.csv",
)
REQUIRED_ORDERS = (2, 3)
REQUIRED_CUTS = ("normal", "strict")
REQUIRED_DIRECTIONS = ("fwd",)
NO_PRODUCTION_SCORER_CHANGE = True
LANE2_LAUNCH_AUTHORITY = "not_granted_by_this_asset"


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def reset_asset_home(asset_home: Path) -> None:
    resolved = asset_home.resolve()
    expected_parent = (REPO_ROOT / "assets" / "ngram_hamming").resolve()
    resolved.relative_to(expected_parent)
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def posixish(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): posixish(item) for key, item in value.items()}
    if isinstance(value, list):
        return [posixish(item) for item in value]
    if isinstance(value, str):
        return value.replace("\\", "/")
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(posixish(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def required_combo_set(rows: list[dict[str, str]]) -> set[tuple[int, str, str]]:
    return {
        (
            int(row.get("ngram_order", 0) or 0),
            str(row.get("dictionary_cut", "")),
            str(row.get("direction", "")),
        )
        for row in rows
    }


def build_blocked_reasons(
    provenance: dict[str, Any],
    output_rows: list[dict[str, str]],
    provenance_dir: Path,
) -> list[str]:
    reasons: list[str] = []
    if provenance.get("status") != "pass":
        reasons.append("shard provenance status is not pass")
    if provenance.get("full_raw_ngram_rebuild_confirmed") is not True:
        reasons.append("full raw rebuild is not confirmed")
    if provenance.get("sample_line_limit_per_order") is not None:
        reasons.append("sample_line_limit_per_order is not null")
    for field in ("missing_shards", "failed_shards", "missing_output_files", "missing_required_output_combos"):
        if int(provenance.get(field, 0) or 0) != 0:
            reasons.append(f"{field} is not zero")
    present = required_combo_set(output_rows)
    required = {
        (order, cut, direction)
        for order in REQUIRED_ORDERS
        for cut in REQUIRED_CUTS
        for direction in REQUIRED_DIRECTIONS
    }
    if not required <= present:
        reasons.append("one or more required order/cut/direction combos are missing")
    if not any(row.get("dictionary_cut") == "normal" for row in output_rows):
        reasons.append("normal cut is missing")
    if not any(row.get("dictionary_cut") == "strict" for row in output_rows):
        reasons.append("strict cut is missing")
    if csv_data_row_count(provenance_dir / "phrase_length_distribution_rows.csv") <= 0:
        reasons.append("phrase length distribution is missing or empty")
    if csv_data_row_count(provenance_dir / "word_length_distribution_rows.csv") <= 0:
        reasons.append("word length distribution is missing or empty")
    return reasons


def copy_provenance_files(provenance_dir: Path, asset_home: Path) -> tuple[list[dict[str, Any]], list[str]]:
    copied: list[dict[str, Any]] = []
    missing: list[str] = []
    for name in PROVENANCE_FILES:
        source = provenance_dir / name
        destination = asset_home / "provenance" / name
        if not source.exists():
            missing.append(f"{SHARD_PROVENANCE_DIR_REL}/{name}")
            continue
        ensure_under_repo(destination)
        shutil.copy2(source, destination)
        copied.append(
            {
                "role": "provenance",
                "path": repo_rel(destination),
                "source_path": repo_rel(source),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
            }
        )
    return copied, missing


def shard_file_rows(output_rows: list[dict[str, str]], *, progress: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(output_rows)
    for index, row in enumerate(output_rows, start=1):
        rel_path = str(row.get("output_file", "")).replace("\\", "/")
        path = REPO_ROOT / rel_path
        file_row: dict[str, Any] = {
            "role": "shard_payload",
            "path": rel_path,
            "source_path": rel_path,
            "tracked_in_asset_home": False,
            "bytes": int(row.get("bytes", 0) or 0),
            "sha256": "",
            "ngram_order": int(row.get("ngram_order", 0) or 0),
            "dictionary_cut": str(row.get("dictionary_cut", "")),
            "direction": str(row.get("direction", "")),
            "aggregate_rows": int(row.get("aggregate_rows", 0) or 0),
            "dictionary_kept_rows": int(row.get("dictionary_kept_rows", 0) or 0),
            "count_sum": int(row.get("count_sum", 0) or 0),
        }
        if path.exists():
            file_row["bytes"] = path.stat().st_size
            file_row["sha256"] = sha256_file(path)
        rows.append(file_row)
        if progress and (index == 1 or index == total or index % 100 == 0):
            print(f"[{RUN_LABEL}] hashed_payload_files={index}/{total}", flush=True)
    return rows


def write_readme(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB Full Raw N-Gram Hamming Language Asset v1",
        "",
        "This directory is the permanent repo asset contract for the full raw",
        "order-2/order-3 FWD normal/strict n-gram Hamming language asset tranche.",
        "",
        "The shard payload is too large for ordinary source-control tracking, so",
        "the payload files are registered by repo-relative path and SHA256 in",
        "`asset_manifest.json` instead of copied into this directory.",
        "",
        f"- asset status: `{manifest['asset_status']}`",
        f"- source run root: `{manifest['source_run_root']}`",
        f"- completed shards: `{manifest['completed_shards']} / {manifest['total_shards']}`",
        f"- payload files listed: `{len(manifest['files'])}`",
        f"- phrase distribution rows: `{manifest['phrase_length_distribution_rows']}`",
        f"- word distribution rows: `{manifest['word_length_distribution_rows']}`",
        f"- Lane 2 launch authority: `{manifest['lane2_launch_authority']}`",
        f"- production scorer change: `{not manifest['no_production_scorer_change']}`",
        "",
        "Order 4 and order 5 are outside this Lane 1 asset tranche, not rejected.",
        "Counts and log-counts remain diagnostic only.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_language_asset_pack(
    asset_home: Path | None = None,
    *,
    hash_payload_files: bool = True,
) -> dict[str, Any]:
    selected_asset_home = asset_home or (REPO_ROOT / ASSET_HOME_REL)
    provenance_dir = REPO_ROOT / SHARD_PROVENANCE_DIR_REL
    provenance = read_json(provenance_dir / "shard_provenance_manifest.json")
    output_rows = read_csv_rows(provenance_dir / "output_file_rows.csv")
    blocked = build_blocked_reasons(provenance, output_rows, provenance_dir)
    reset_asset_home(selected_asset_home)
    provenance_files, missing_provenance_files = copy_provenance_files(provenance_dir, selected_asset_home)
    if missing_provenance_files:
        blocked.append("one or more required provenance files are missing")
    files = shard_file_rows(output_rows, progress=hash_payload_files) if hash_payload_files else []
    missing_payload_files = [row.get("output_file", "") for row in output_rows if not (REPO_ROOT / str(row.get("output_file", ""))).exists()]
    if missing_payload_files:
        blocked.append("one or more shard payload files are missing")
    if hash_payload_files and any(not row.get("sha256") for row in files):
        blocked.append("one or more shard payload hashes are missing")
    manifest = {
        "asset_id": "phaseB_ngram_hamming_full_raw_v1",
        "asset_version": "v1",
        "asset_status": "review_ready_candidate" if not blocked else "blocked",
        "asset_kind": "ngram_hamming_full_raw_language_asset",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_run_root": provenance.get("run_root", ""),
        "payload_storage_mode": "manifest_index_external_payload_due_large_size",
        "asset_home": repo_rel(selected_asset_home),
        "asset_mode": "full",
        "sample_line_limit_per_order": provenance.get("sample_line_limit_per_order"),
        "required_orders": list(REQUIRED_ORDERS),
        "required_cuts": list(REQUIRED_CUTS),
        "required_directions": list(REQUIRED_DIRECTIONS),
        "completed_shards": provenance.get("completed_shards", 0),
        "total_shards": provenance.get("total_shards", 0),
        "missing_shards": provenance.get("missing_shards", 0),
        "failed_shards": provenance.get("failed_shards", 0),
        "missing_output_files": provenance.get("missing_output_files", 0),
        "missing_required_output_combos": provenance.get("missing_required_output_combos", 0),
        "output_count_by_order_cut_direction": provenance.get("output_count_by_order_cut_direction", []),
        "aggregate_rows": provenance.get("aggregate_rows", 0),
        "dictionary_kept_rows": provenance.get("dictionary_kept_rows", 0),
        "count_sum": sum(int(row.get("count_sum", 0) or 0) for row in output_rows),
        "phrase_length_distribution_rows": csv_data_row_count(provenance_dir / "phrase_length_distribution_rows.csv"),
        "word_length_distribution_rows": csv_data_row_count(provenance_dir / "word_length_distribution_rows.csv"),
        "files": files,
        "provenance_files": provenance_files,
        "missing_files": missing_provenance_files + missing_payload_files,
        "hash_algorithm": "sha256",
        "no_production_scorer_change": NO_PRODUCTION_SCORER_CHANGE,
        "lane2_launch_authority": LANE2_LAUNCH_AUTHORITY,
        "blocked_reasons": sorted(set(blocked)),
        "known_limitations": [
            "orders 4 and 5 are not included in this Lane 1 asset tranche",
            "direction scope is fwd only unless explicitly extended later",
            "counts and log-counts remain diagnostic only",
            "payload files are registered by manifest because the generated shard outputs are too large for ordinary source-control tracking",
        ],
    }
    write_json(selected_asset_home / "asset_manifest.json", manifest)
    write_readme(selected_asset_home / "README.md", manifest)
    (selected_asset_home / "shards").mkdir(parents=True, exist_ok=True)
    (selected_asset_home / "shards" / "PAYLOAD_NOT_TRACKED.md").write_text(
        "Shard payload files are registered in ../asset_manifest.json by repo-relative path and SHA256.\n",
        encoding="utf-8",
    )
    print(f"[{RUN_LABEL}] status={manifest['asset_status']}")
    print(f"[{RUN_LABEL}] listed_files={len(files)}")
    return manifest


def main() -> None:
    build_language_asset_pack()


if __name__ == "__main__":
    main()
