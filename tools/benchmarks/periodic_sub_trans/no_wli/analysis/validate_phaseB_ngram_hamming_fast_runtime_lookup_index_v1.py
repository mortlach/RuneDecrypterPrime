from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_fast_runtime_lookup_index_validation_v1"
RUNTIME_INDEX_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_fast_runtime_lookup_index_v1"
)
RUNTIME_MANIFEST_REL = f"{RUNTIME_INDEX_DIR_REL}/runtime_index_manifest.json"
COMPACT_VALIDATION_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_validation_v1/validation_manifest.json"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_fast_runtime_lookup_index_validation_v1"
)
EXPECTED_ASSET_ID = "phaseB_ngram_hamming_full_raw_fast_runtime_index_v1"
EXPECTED_COMPACT_ASSET_ID = "phaseB_ngram_hamming_full_raw_compact_lookup_v1"
EXPECTED_RUNTIME_FORMAT = "grouped_npz_by_length_and_word_shape"
EXPECTED_MAX_RUNTIME_ROWS_PER_FILE = 1_000_000
EXPECTED_ORDERS = [2, 3]
EXPECTED_CUTS = ["normal", "strict"]
EXPECTED_DIRECTIONS = ["fwd"]
VALID_TOKEN_DTYPES = {"uint8", "uint16"}
REQUIRED_ARRAYS = {
    "rune_tokens",
    "phrase_id",
    "direction",
    "dictionary_cut",
    "ngram_order",
    "phrase_token_length",
    "word_token_lengths",
    "sum_count",
    "max_count",
    "sum_log_count",
    "max_log_count",
    "source_row_count",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024 * 4), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_failures(manifest: Mapping[str, Any], failures: list[dict[str, Any]]) -> None:
    expected = {
        "asset_id": EXPECTED_ASSET_ID,
        "source_compact_asset_id": EXPECTED_COMPACT_ASSET_ID,
        "source_compact_validation_status": "pass",
        "runtime_format": EXPECTED_RUNTIME_FORMAT,
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            failures.append({"path": RUNTIME_MANIFEST_REL, "row_number": "", "reason": f"{field} is not {value}"})
    if manifest.get("asset_status") != "built":
        failures.append({"path": RUNTIME_MANIFEST_REL, "row_number": "", "reason": "runtime index asset status is not built"})
    if int(manifest.get("max_runtime_rows_per_file", 0)) != EXPECTED_MAX_RUNTIME_ROWS_PER_FILE:
        failures.append({"path": RUNTIME_MANIFEST_REL, "row_number": "", "reason": "max_runtime_rows_per_file is not 1000000"})
    if manifest.get("orders") != EXPECTED_ORDERS:
        failures.append({"path": RUNTIME_MANIFEST_REL, "row_number": "", "reason": "orders are not exactly [2, 3]"})
    if manifest.get("cuts") != EXPECTED_CUTS:
        failures.append({"path": RUNTIME_MANIFEST_REL, "row_number": "", "reason": "cuts are not exactly normal/strict"})
    if manifest.get("directions") != EXPECTED_DIRECTIONS:
        failures.append({"path": RUNTIME_MANIFEST_REL, "row_number": "", "reason": "directions are not exactly fwd"})
    for field in ("counts_are_diagnostic_only", "log_counts_are_diagnostic_only"):
        if manifest.get(field) is not True:
            failures.append({"path": RUNTIME_MANIFEST_REL, "row_number": "", "reason": f"{field} is not true"})
    for field in ("production_scorer_change", "sample_asset_used", "old_phrase_index_v1_used", "full_raw_shards_used_directly_as_runtime"):
        if manifest.get(field) is not False:
            failures.append({"path": RUNTIME_MANIFEST_REL, "row_number": "", "reason": f"{field} is not false"})


def scalar_unique(values: np.ndarray) -> set[str]:
    return {str(item) for item in values.tolist()}


def validate_npz(path: Path, file_row: Mapping[str, Any], failures: list[dict[str, Any]]) -> int:
    with np.load(path, allow_pickle=False) as data:
        missing = sorted(REQUIRED_ARRAYS - set(data.files))
        if missing:
            failures.append({"path": repo_rel(path), "row_number": "", "reason": f"missing arrays: {','.join(missing)}"})
            return 0
        rune_tokens = data["rune_tokens"]
        phrase_ids = data["phrase_id"]
        row_count = int(rune_tokens.shape[0]) if rune_tokens.ndim == 2 else 0
        if rune_tokens.ndim != 2:
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "rune_tokens is not a 2D array"})
        if row_count != int(file_row.get("phrase_count", -1)):
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "array row count does not match listed phrase count"})
        if row_count > int(file_row.get("max_runtime_rows_per_file", 0)):
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "runtime chunk exceeds max_runtime_rows_per_file"})
        if int(file_row.get("max_runtime_rows_per_file", 0)) != EXPECTED_MAX_RUNTIME_ROWS_PER_FILE:
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "runtime chunk max_runtime_rows_per_file is not 1000000"})
        if rune_tokens.ndim == 2 and int(rune_tokens.shape[1]) != int(file_row.get("phrase_token_length", -1)):
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "rune token width does not match phrase_token_length"})
        if str(rune_tokens.dtype) != str(file_row.get("token_dtype", "")):
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "token dtype does not match manifest"})
        if str(rune_tokens.dtype) not in VALID_TOKEN_DTYPES:
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "token dtype is not valid"})
        if len(set(str(item) for item in phrase_ids.tolist())) != len(phrase_ids):
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "phrase_id values are not unique within group"})
        if scalar_unique(data["direction"]) != {str(file_row.get("direction", ""))}:
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "runtime group mixes direction"})
        if scalar_unique(data["dictionary_cut"]) != {str(file_row.get("dictionary_cut", ""))}:
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "runtime group mixes dictionary_cut"})
        if {int(item) for item in data["ngram_order"].tolist()} != {int(file_row.get("ngram_order", -1))}:
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "runtime group mixes ngram_order"})
        if {int(item) for item in data["phrase_token_length"].tolist()} != {int(file_row.get("phrase_token_length", -1))}:
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "runtime group mixes phrase length"})
        expected_word_lens = tuple(int(item) for item in json.loads(str(file_row.get("word_token_lengths", "[]"))))
        actual_word_lens = tuple(int(item) for item in data["word_token_lengths"].tolist())
        if actual_word_lens != expected_word_lens:
            failures.append({"path": repo_rel(path), "row_number": "", "reason": "word length shape does not match manifest"})
        return row_count


def validate_fast_runtime_lookup_index(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    failures: list[dict[str, Any]] = []
    manifest_path = REPO_ROOT / RUNTIME_MANIFEST_REL
    compact_validation_path = REPO_ROOT / COMPACT_VALIDATION_MANIFEST_REL
    if not manifest_path.is_file():
        manifest: dict[str, Any] = {}
        failures.append({"path": RUNTIME_MANIFEST_REL, "row_number": "", "reason": "runtime index manifest is missing"})
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_failures(manifest, failures)
    if not compact_validation_path.is_file():
        failures.append({"path": COMPACT_VALIDATION_MANIFEST_REL, "row_number": "", "reason": "compact validation manifest is missing"})
    else:
        compact_validation = json.loads(compact_validation_path.read_text(encoding="utf-8"))
        if compact_validation.get("status") != "pass":
            failures.append({"path": COMPACT_VALIDATION_MANIFEST_REL, "row_number": "", "reason": "compact validation status is not pass"})

    total_rows = 0
    runtime_files = list(manifest.get("files", [])) if manifest else []
    started = time.monotonic()
    for file_index, file_row in enumerate(runtime_files, start=1):
        rel_path = str(file_row.get("path", ""))
        path = REPO_ROOT / rel_path
        if file_index == 1 or file_index % 100 == 0 or file_index == len(runtime_files):
            elapsed = time.monotonic() - started
            print(
                f"[{RUN_LABEL}] validating_group={file_index}/{len(runtime_files)} "
                f"rows_so_far={total_rows} elapsed_seconds={elapsed:.1f}",
                flush=True,
            )
        if "\\" in rel_path or Path(rel_path).is_absolute() or ":" in rel_path:
            failures.append({"path": rel_path, "row_number": "", "reason": "runtime file path is not repo-relative POSIX"})
            continue
        if not path.is_file():
            failures.append({"path": rel_path, "row_number": "", "reason": "runtime npz file is missing"})
            continue
        if path.stat().st_size != int(file_row.get("bytes", -1)):
            failures.append({"path": rel_path, "row_number": "", "reason": "runtime npz byte count mismatch"})
        if sha256_file(path) != str(file_row.get("sha256", "")):
            failures.append({"path": rel_path, "row_number": "", "reason": "runtime npz hash mismatch"})
        total_rows += validate_npz(path, file_row, failures)
    if runtime_files:
        elapsed = time.monotonic() - started
        print(
            f"[{RUN_LABEL}] completed_groups={len(runtime_files)} phrase_rows_indexed={total_rows} "
            f"elapsed_seconds={elapsed:.1f} failures_so_far={len(failures)}",
            flush=True,
        )

    if manifest and total_rows != int(manifest.get("phrase_rows_indexed", -1)):
        failures.append({"path": RUNTIME_MANIFEST_REL, "row_number": "", "reason": "total runtime phrase rows do not match manifest"})
    if manifest and total_rows != int(manifest.get("source_compact_row_count", -1)):
        failures.append({"path": RUNTIME_MANIFEST_REL, "row_number": "", "reason": "total runtime phrase rows do not match compact row count"})

    status = "pass" if not failures else "blocked"
    validation = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "asset_id": manifest.get("asset_id", "") if manifest else "",
        "source_compact_asset_id": manifest.get("source_compact_asset_id", "") if manifest else "",
        "runtime_format": manifest.get("runtime_format", "") if manifest else "",
        "group_count": len(manifest.get("files", [])) if manifest else 0,
        "phrase_rows_indexed": total_rows,
        "failure_count": len(failures),
    }
    write_json(selected_output_dir / "validation_manifest.json", validation)
    write_csv(selected_output_dir / "validation_failure_rows.csv", failures, ("path", "row_number", "reason"))
    write_readout(selected_output_dir / "readout.md", validation)
    print(f"[{RUN_LABEL}] status={status}")
    print(f"[{RUN_LABEL}] phrase_rows_indexed={total_rows}")
    return validation


def write_readout(path: Path, validation: Mapping[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# Phase B N-gram Hamming Fast Runtime Lookup Index Validation v1",
        "",
        f"Status: `{validation['status']}`",
        "",
        f"- asset id: `{validation['asset_id']}`",
        f"- source compact asset id: `{validation['source_compact_asset_id']}`",
        f"- runtime format: `{validation['runtime_format']}`",
        f"- max runtime rows per file: `{EXPECTED_MAX_RUNTIME_ROWS_PER_FILE}`",
        f"- group count: `{validation['group_count']}`",
        f"- phrase rows indexed: `{validation['phrase_rows_indexed']}`",
        f"- failure count: `{validation['failure_count']}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    validate_fast_runtime_lookup_index()


if __name__ == "__main__":
    main()
