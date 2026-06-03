from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_validation_v1"
COMPACT_ASSET_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1"
)
COMPACT_MANIFEST_REL = f"{COMPACT_ASSET_DIR_REL}/compact_asset_manifest.json"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_validation_v1"
)
EXPECTED_ASSET_ID = "phaseB_ngram_hamming_full_raw_compact_lookup_v1"
EXPECTED_SOURCE_ASSET_ID = "phaseB_ngram_hamming_full_raw_v1"
EXPECTED_ORDERS = [2, 3]
EXPECTED_CUTS = ["normal", "strict"]
EXPECTED_DIRECTIONS = ["fwd"]
REQUIRED_ROW_FIELDS = (
    "phrase_id",
    "direction",
    "dictionary_cut",
    "ngram_order",
    "word_token_tuple",
    "rune_token_tuple",
    "identity_sha256",
)


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


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(posixish(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Iterable[str]) -> None:
    ensure_under_repo(path)
    fields = list(fieldnames)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256_file(path: Path, expected_bytes: int | None = None) -> str:
    digest = hashlib.sha256()
    bytes_read = 0
    started = time.monotonic()
    expected_text = str(expected_bytes) if expected_bytes is not None else "unknown"
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024 * 4), b""):
            digest.update(chunk)
            bytes_read += len(chunk)
            if bytes_read % (1024 * 1024 * 512) < len(chunk):
                elapsed = time.monotonic() - started
                rate = bytes_read / elapsed if elapsed > 0 else 0.0
                remaining = ""
                if expected_bytes is not None and rate > 0:
                    eta_seconds = max(0, int((expected_bytes - bytes_read) / rate))
                    remaining = f" eta_seconds={eta_seconds}"
                print(
                    f"[{RUN_LABEL}] hash_file={repo_rel(path)} bytes={bytes_read}/{expected_text} "
                    f"elapsed_seconds={elapsed:.1f}{remaining}",
                    flush=True,
                )
    return digest.hexdigest()


def sort_key(row: Mapping[str, str]) -> tuple[Any, ...]:
    return (
        row["direction"],
        row["dictionary_cut"],
        int(row["ngram_order"]),
        int(row.get("phrase_token_length", 0) or 0),
        row.get("word_token_lengths", ""),
        row["rune_token_tuple"],
        row["word_token_tuple"],
        row["identity_sha256"],
    )


def validate_rows(path: Path, expected_rows: int | None = None) -> tuple[int, list[dict[str, Any]]]:
    failures: list[dict[str, Any]] = []
    previous_key: tuple[Any, ...] | None = None
    previous_phrase_id: str | None = None
    previous_identity: tuple[str, str, str, str, str] | None = None
    row_count = 0
    started = time.monotonic()
    expected_text = str(expected_rows) if expected_rows is not None else "unknown"
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=1):
            row_count += 1
            if row_count % 5_000_000 == 0:
                elapsed = time.monotonic() - started
                rate = row_count / elapsed if elapsed > 0 else 0.0
                remaining = ""
                if expected_rows is not None and rate > 0:
                    eta_seconds = max(0, int((expected_rows - row_count) / rate))
                    remaining = f" eta_seconds={eta_seconds}"
                print(
                    f"[{RUN_LABEL}] file={repo_rel(path)} rows={row_count}/{expected_text} "
                    f"elapsed_seconds={elapsed:.1f}{remaining}",
                    flush=True,
                )
            missing = [field for field in REQUIRED_ROW_FIELDS if not row.get(field)]
            if missing:
                failures.append({"path": repo_rel(path), "row_number": row_number, "reason": f"missing fields: {','.join(missing)}"})
                continue
            phrase_id = row["phrase_id"]
            identity = (
                row["direction"],
                row["dictionary_cut"],
                row["ngram_order"],
                row["word_token_tuple"],
                row["rune_token_tuple"],
            )
            if phrase_id == previous_phrase_id:
                failures.append({"path": repo_rel(path), "row_number": row_number, "reason": "duplicate phrase_id"})
            if identity == previous_identity:
                failures.append({"path": repo_rel(path), "row_number": row_number, "reason": "duplicate canonical identity"})
            current_key = sort_key(row)
            if previous_key is not None and current_key < previous_key:
                failures.append({"path": repo_rel(path), "row_number": row_number, "reason": "rows are not deterministically sorted"})
            previous_key = current_key
            previous_phrase_id = phrase_id
            previous_identity = identity
    return row_count, failures


def validate_compact_lookup_asset(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    manifest_path = REPO_ROOT / COMPACT_MANIFEST_REL
    failures: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        manifest: dict[str, Any] = {}
        failures.append({"path": COMPACT_MANIFEST_REL, "row_number": "", "reason": "compact_asset_manifest.json is missing"})
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest:
        expected = {
            "asset_id": EXPECTED_ASSET_ID,
            "source_asset_id": EXPECTED_SOURCE_ASSET_ID,
            "source_asset_mode": "full",
            "source_payload_validation_status": "pass",
        }
        for field, value in expected.items():
            if manifest.get(field) != value:
                failures.append({"path": COMPACT_MANIFEST_REL, "row_number": "", "reason": f"{field} is not {value}"})
        if manifest.get("orders") != EXPECTED_ORDERS:
            failures.append({"path": COMPACT_MANIFEST_REL, "row_number": "", "reason": "orders are not exactly [2, 3]"})
        if manifest.get("cuts") != EXPECTED_CUTS:
            failures.append({"path": COMPACT_MANIFEST_REL, "row_number": "", "reason": "cuts are not exactly normal/strict"})
        if manifest.get("directions") != EXPECTED_DIRECTIONS:
            failures.append({"path": COMPACT_MANIFEST_REL, "row_number": "", "reason": "directions are not exactly fwd"})
        for field in ("normal_strict_separate", "counts_are_diagnostic_only", "log_counts_are_diagnostic_only"):
            if manifest.get(field) is not True:
                failures.append({"path": COMPACT_MANIFEST_REL, "row_number": "", "reason": f"{field} is not true"})
        if manifest.get("sample_asset_used") is not False:
            failures.append({"path": COMPACT_MANIFEST_REL, "row_number": "", "reason": "sample asset was used"})
        if manifest.get("old_phrase_index_v1_used") is not False:
            failures.append({"path": COMPACT_MANIFEST_REL, "row_number": "", "reason": "old phrase_index_v1 was used"})

    file_count = 0
    row_count = 0
    for file_row in manifest.get("files", []) if manifest else []:
        rel_path = str(file_row.get("path", ""))
        path = REPO_ROOT / rel_path
        file_count += 1
        if "\\" in rel_path or Path(rel_path).is_absolute() or ":" in rel_path:
            failures.append({"path": rel_path, "row_number": "", "reason": "listed compact file path is not repo-relative POSIX"})
            continue
        if not path.is_file():
            failures.append({"path": rel_path, "row_number": "", "reason": "listed compact file is missing"})
            continue
        if path.stat().st_size != int(file_row.get("bytes", -1)):
            failures.append({"path": rel_path, "row_number": "", "reason": "listed compact file byte count mismatch"})
        expected_bytes = int(file_row.get("bytes", -1))
        if expected_bytes < 0:
            expected_bytes = None
        if sha256_file(path, expected_bytes=expected_bytes) != str(file_row.get("sha256", "")):
            failures.append({"path": rel_path, "row_number": "", "reason": "listed compact file hash mismatch"})
        expected_rows = int(file_row.get("row_count_after_dedup", -1))
        if expected_rows < 0:
            expected_rows = None
        print(
            f"[{RUN_LABEL}] validating_file={rel_path} expected_rows={expected_rows if expected_rows is not None else 'unknown'}",
            flush=True,
        )
        rows_in_file, row_failures = validate_rows(path, expected_rows=expected_rows)
        row_count += rows_in_file
        failures.extend(row_failures)
        print(
            f"[{RUN_LABEL}] completed_file={rel_path} rows={rows_in_file} failures_so_far={len(failures)}",
            flush=True,
        )

    status = "pass" if not failures else "blocked"
    validation = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "asset_id": manifest.get("asset_id", "") if manifest else "",
        "source_asset_id": manifest.get("source_asset_id", "") if manifest else "",
        "source_asset_mode": manifest.get("source_asset_mode", "") if manifest else "",
        "source_payload_validation_status": manifest.get("source_payload_validation_status", "") if manifest else "",
        "compact_files_checked": file_count,
        "compact_rows_checked": row_count,
        "failure_count": len(failures),
    }
    write_json(selected_output_dir / "validation_manifest.json", validation)
    write_csv(selected_output_dir / "validation_failure_rows.csv", failures, ("path", "row_number", "reason"))
    write_readout(selected_output_dir / "readout.md", validation)
    print(f"[{RUN_LABEL}] status={status}")
    print(f"[{RUN_LABEL}] compact_rows_checked={row_count}")
    return validation


def write_readout(path: Path, validation: Mapping[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# Phase B N-gram Hamming Full Raw Compact Phrase Lookup Asset Validation v1",
        "",
        f"Status: `{validation['status']}`",
        "",
        f"- asset id: `{validation['asset_id']}`",
        f"- source asset id: `{validation['source_asset_id']}`",
        f"- source asset mode: `{validation['source_asset_mode']}`",
        f"- source payload validation status: `{validation['source_payload_validation_status']}`",
        f"- compact files checked: `{validation['compact_files_checked']}`",
        f"- compact rows checked: `{validation['compact_rows_checked']}`",
        f"- failure count: `{validation['failure_count']}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    validate_compact_lookup_asset()


if __name__ == "__main__":
    main()
