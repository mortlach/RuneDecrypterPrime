from __future__ import annotations

import hashlib
import json
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


RUN_LABEL = "phaseB_ngram_hamming_full_raw_language_asset_validation_v1"
ASSET_HOME_REL = "assets/ngram_hamming/phaseB_full_raw_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_language_asset_validation_v1"
)
EXPECTED_ORDERS = [2, 3]
EXPECTED_CUTS = ["normal", "strict"]
EXPECTED_DIRECTIONS = ["fwd"]
EXPECTED_TOTAL_SHARDS = 1118
REQUIRED_PROVENANCE_NAMES = {
    "shard_provenance_manifest.json",
    "shard_rows.csv",
    "output_file_rows.csv",
    "missing_shard_rows.csv",
    "missing_required_output_combo_rows.csv",
    "phrase_length_distribution_rows.csv",
    "word_length_distribution_rows.csv",
}


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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(posixish(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def has_absolute_or_backslash(path_value: str) -> bool:
    return "\\" in path_value or Path(path_value).is_absolute() or ":" in path_value


def validate_file_rows(rows: list[dict[str, Any]]) -> tuple[list[str], int, int]:
    reasons: list[str] = []
    hash_failures = 0
    missing_files = 0
    total = len(rows)
    for index, row in enumerate(rows, start=1):
        rel_path = str(row.get("path", ""))
        if has_absolute_or_backslash(rel_path):
            reasons.append(f"path is not repo-relative POSIX: {rel_path}")
            continue
        path = REPO_ROOT / rel_path
        if not path.exists():
            missing_files += 1
            reasons.append(f"listed file is missing: {rel_path}")
            continue
        expected_hash = str(row.get("sha256", ""))
        if expected_hash and sha256_file(path) != expected_hash:
            hash_failures += 1
            reasons.append(f"listed file hash mismatch: {rel_path}")
        if index == 1 or index == total or index % 100 == 0:
            print(f"[{RUN_LABEL}] validated_listed_files={index}/{total}", flush=True)
    return reasons, hash_failures, missing_files


def validate_language_asset(
    asset_home: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    selected_asset_home = asset_home or (REPO_ROOT / ASSET_HOME_REL)
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    manifest_path = selected_asset_home / "asset_manifest.json"
    readme_path = selected_asset_home / "README.md"
    blocked_reasons: list[str] = []
    if not manifest_path.exists():
        blocked_reasons.append("asset_manifest.json is missing")
        manifest: dict[str, Any] = {}
    else:
        manifest = read_json(manifest_path)
    if not readme_path.exists():
        blocked_reasons.append("README.md is missing")
    if manifest:
        if manifest.get("asset_mode") != "full":
            blocked_reasons.append("asset_mode is not full")
        if manifest.get("sample_line_limit_per_order") is not None:
            blocked_reasons.append("sample_line_limit_per_order is not null")
        if manifest.get("required_orders") != EXPECTED_ORDERS:
            blocked_reasons.append("required_orders are not exactly [2, 3]")
        if manifest.get("required_cuts") != EXPECTED_CUTS:
            blocked_reasons.append("required_cuts are not exactly normal/strict")
        if manifest.get("required_directions") != EXPECTED_DIRECTIONS:
            blocked_reasons.append("required_directions are not exactly fwd")
        if int(manifest.get("completed_shards", 0) or 0) != EXPECTED_TOTAL_SHARDS:
            blocked_reasons.append("completed_shards does not match expected total")
        if int(manifest.get("total_shards", 0) or 0) != EXPECTED_TOTAL_SHARDS:
            blocked_reasons.append("total_shards does not match expected total")
        for field in ("missing_shards", "failed_shards", "missing_output_files", "missing_required_output_combos"):
            if int(manifest.get(field, 0) or 0) != 0:
                blocked_reasons.append(f"{field} is not zero")
        if int(manifest.get("phrase_length_distribution_rows", 0) or 0) <= 0:
            blocked_reasons.append("phrase_length_distribution_rows is empty")
        if int(manifest.get("word_length_distribution_rows", 0) or 0) <= 0:
            blocked_reasons.append("word_length_distribution_rows is empty")
        provenance_names = {Path(str(row.get("path", ""))).name for row in manifest.get("provenance_files", [])}
        missing_provenance = sorted(REQUIRED_PROVENANCE_NAMES - provenance_names)
        if missing_provenance:
            blocked_reasons.append("one or more required provenance CSVs are missing")
        if manifest.get("no_production_scorer_change") is not True:
            blocked_reasons.append("no_production_scorer_change is not true")
        if manifest.get("lane2_launch_authority") != "not_granted_by_this_asset":
            blocked_reasons.append("lane2 launch authority is not blocked")
        file_reasons, hash_failures, missing_files = validate_file_rows(
            list(manifest.get("files", [])) + list(manifest.get("provenance_files", []))
        )
        blocked_reasons.extend(file_reasons)
    else:
        hash_failures = 0
        missing_files = 0
    validation = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not blocked_reasons else "blocked",
        "asset_home": repo_rel(selected_asset_home) if selected_asset_home.exists() else ASSET_HOME_REL,
        "asset_manifest": repo_rel(manifest_path) if manifest_path.exists() else f"{ASSET_HOME_REL}/asset_manifest.json",
        "blocked_reasons": blocked_reasons,
        "listed_files": len(manifest.get("files", [])) if manifest else 0,
        "provenance_files": len(manifest.get("provenance_files", [])) if manifest else 0,
        "hash_failures": hash_failures,
        "missing_files": missing_files,
        "no_production_scorer_change": manifest.get("no_production_scorer_change", False) if manifest else False,
        "lane2_launch_authority": manifest.get("lane2_launch_authority", "") if manifest else "",
    }
    write_json(selected_output_dir / "validation_manifest.json", validation)
    print(f"[{RUN_LABEL}] status={validation['status']}")
    print(f"[{RUN_LABEL}] listed_files={validation['listed_files']}")
    return validation


def main() -> None:
    validate_language_asset()


if __name__ == "__main__":
    main()
