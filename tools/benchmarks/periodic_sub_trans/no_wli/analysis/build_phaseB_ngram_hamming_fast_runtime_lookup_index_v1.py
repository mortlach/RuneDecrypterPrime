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

import numpy as np


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_fast_runtime_lookup_index_v1"
COMPACT_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1/compact_asset_manifest.json"
)
COMPACT_VALIDATION_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_validation_v1/validation_manifest.json"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_fast_runtime_lookup_index_v1"
)
ASSET_META_DIR_REL = "assets/ngram_hamming/phaseB_full_raw_fast_runtime_index_v1"
ASSET_ID = "phaseB_ngram_hamming_full_raw_fast_runtime_index_v1"
COMPACT_ASSET_ID = "phaseB_ngram_hamming_full_raw_compact_lookup_v1"
SOURCE_ASSET_ID = "phaseB_ngram_hamming_full_raw_v1"
RUNTIME_FORMAT = "grouped_npz_by_length_and_word_shape"
MAX_RUNTIME_ROWS_PER_FILE = 1_000_000
PRODUCTION_SCORER_CHANGE = False
COUNTS_ARE_DIAGNOSTIC_ONLY = True
LOG_COUNTS_ARE_DIAGNOSTIC_ONLY = True


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


def compact_ready_errors(compact_manifest: Mapping[str, Any], compact_validation: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if compact_manifest.get("asset_id") != COMPACT_ASSET_ID:
        errors.append("compact asset id mismatch")
    if compact_manifest.get("asset_status") != "built":
        errors.append("compact asset status is not built")
    if compact_manifest.get("source_asset_id") != SOURCE_ASSET_ID:
        errors.append("compact source asset id mismatch")
    if compact_manifest.get("source_asset_mode") != "full":
        errors.append("compact source asset mode is not full")
    if compact_validation.get("status") != "pass":
        errors.append("compact validation status is not pass")
    if compact_manifest.get("sample_asset_used") is not False:
        errors.append("compact asset used sample source")
    if compact_manifest.get("old_phrase_index_v1_used") is not False:
        errors.append("compact asset used old phrase_index_v1")
    if compact_manifest.get("counts_are_diagnostic_only") is not True:
        errors.append("compact counts are not diagnostic-only")
    if compact_manifest.get("log_counts_are_diagnostic_only") is not True:
        errors.append("compact log-counts are not diagnostic-only")
    return errors


def word_lens_slug(word_lens: tuple[int, ...]) -> str:
    return "-".join(str(item) for item in word_lens)


def runtime_group_rel_path(
    direction: str,
    order: int,
    cut: str,
    phrase_len: int,
    word_lens: tuple[int, ...],
    chunk_index: int,
) -> str:
    return (
        f"runtime_index/direction={direction}/order={order}/cut={cut}/"
        f"phrase_len={phrase_len}__word_lens={word_lens_slug(word_lens)}__chunk={chunk_index:06d}.npz"
    )


def parsed_group_key(row: Mapping[str, str]) -> tuple[str, int, str, int, tuple[int, ...]]:
    word_lens = tuple(int(item) for item in json.loads(row["word_token_lengths"]))
    return (
        str(row["direction"]),
        int(row["ngram_order"]),
        str(row["dictionary_cut"]),
        int(row["phrase_token_length"]),
        word_lens,
    )


def flush_group(
    *,
    output_dir: Path,
    key: tuple[str, int, str, int, tuple[int, ...]],
    chunk_index: int,
    rows: list[Mapping[str, str]],
) -> dict[str, Any]:
    direction, order, cut, phrase_len, word_lens = key
    rune_values = [json.loads(row["rune_token_tuple"]) for row in rows]
    max_token = max((int(token) for tokens in rune_values for token in tokens), default=0)
    dtype = np.uint8 if max_token <= 255 else np.uint16
    rune_tokens = np.asarray(rune_values, dtype=dtype)
    phrase_ids = np.asarray([str(row["phrase_id"]) for row in rows], dtype=np.str_)
    directions = np.asarray([direction] * len(rows), dtype=np.str_)
    cuts = np.asarray([cut] * len(rows), dtype=np.str_)
    orders = np.asarray([order] * len(rows), dtype=np.int16)
    phrase_lengths = np.asarray([phrase_len] * len(rows), dtype=np.int16)
    word_length_shape = np.asarray(word_lens, dtype=np.int16)
    source_row_count = np.asarray([int(row["source_row_count"]) for row in rows], dtype=np.int64)
    sum_count = np.asarray([float(row["sum_count"]) for row in rows], dtype=np.float64)
    max_count = np.asarray([float(row["max_count"]) for row in rows], dtype=np.float64)
    sum_log_count = np.asarray([float(row["sum_log_count"]) for row in rows], dtype=np.float64)
    max_log_count = np.asarray([float(row["max_log_count"]) for row in rows], dtype=np.float64)
    rel_path = runtime_group_rel_path(direction, order, cut, phrase_len, word_lens, chunk_index)
    path = output_dir / rel_path
    ensure_under_repo(path)
    np.savez_compressed(
        path,
        rune_tokens=rune_tokens,
        phrase_id=phrase_ids,
        direction=directions,
        dictionary_cut=cuts,
        ngram_order=orders,
        phrase_token_length=phrase_lengths,
        word_token_lengths=word_length_shape,
        sum_count=sum_count,
        max_count=max_count,
        sum_log_count=sum_log_count,
        max_log_count=max_log_count,
        source_row_count=source_row_count,
    )
    return {
        "path": repo_rel(path),
        "role": "fast_runtime_npz_group",
        "direction": direction,
        "ngram_order": order,
        "dictionary_cut": cut,
        "phrase_token_length": phrase_len,
        "word_token_lengths": json.dumps(list(word_lens), separators=(",", ":")),
        "chunk_index": chunk_index,
        "max_runtime_rows_per_file": MAX_RUNTIME_ROWS_PER_FILE,
        "phrase_count": len(rows),
        "token_dtype": str(np.dtype(dtype)),
        "runtime_format": RUNTIME_FORMAT,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def build_runtime_index_files(compact_manifest: Mapping[str, Any], output_dir: Path) -> list[dict[str, Any]]:
    file_rows: list[dict[str, Any]] = []
    compact_files = list(compact_manifest.get("files", []))
    total_expected_rows = sum(int(row.get("row_count_after_dedup", 0)) for row in compact_files)
    indexed_rows = 0
    started = time.monotonic()
    for compact_index, compact_file in enumerate(compact_files, start=1):
        current_key: tuple[str, int, str, int, tuple[int, ...]] | None = None
        current_rows: list[Mapping[str, str]] = []
        next_chunk_by_key: dict[tuple[str, int, str, int, tuple[int, ...]], int] = {}
        compact_rel = str(compact_file["path"])
        expected_rows = int(compact_file.get("row_count_after_dedup", 0))
        print(
            f"[{RUN_LABEL}] compact_file={compact_index}/{len(compact_files)} path={compact_rel} "
            f"expected_rows={expected_rows} indexed_rows={indexed_rows}/{total_expected_rows}",
            flush=True,
        )
        rows_in_file = 0
        with gzip.open(REPO_ROOT / compact_rel, "rt", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows_in_file += 1
                indexed_rows += 1
                if indexed_rows % 5_000_000 == 0:
                    elapsed = time.monotonic() - started
                    rate = indexed_rows / elapsed if elapsed > 0 else 0.0
                    eta_seconds = int((total_expected_rows - indexed_rows) / rate) if rate > 0 else -1
                    print(
                        f"[{RUN_LABEL}] indexed_rows={indexed_rows}/{total_expected_rows} "
                        f"elapsed_seconds={elapsed:.1f} eta_seconds={eta_seconds}",
                        flush=True,
                    )
                key = parsed_group_key(row)
                if current_key is not None and (key != current_key or len(current_rows) >= MAX_RUNTIME_ROWS_PER_FILE):
                    chunk_index = next_chunk_by_key.get(current_key, 0)
                    group_row = flush_group(
                        output_dir=output_dir,
                        key=current_key,
                        chunk_index=chunk_index,
                        rows=current_rows,
                    )
                    next_chunk_by_key[current_key] = chunk_index + 1
                    file_rows.append(group_row)
                    print(
                        f"[{RUN_LABEL}] wrote_group={group_row['path']} phrase_count={group_row['phrase_count']} "
                        f"chunk_index={chunk_index} group_count={len(file_rows)}",
                        flush=True,
                    )
                    current_rows = []
                current_key = key
                current_rows.append(row)
        if current_key is not None:
            chunk_index = next_chunk_by_key.get(current_key, 0)
            group_row = flush_group(
                output_dir=output_dir,
                key=current_key,
                chunk_index=chunk_index,
                rows=current_rows,
            )
            next_chunk_by_key[current_key] = chunk_index + 1
            file_rows.append(group_row)
            print(
                f"[{RUN_LABEL}] wrote_group={group_row['path']} phrase_count={group_row['phrase_count']} "
                f"chunk_index={chunk_index} group_count={len(file_rows)}",
                flush=True,
            )
        print(
            f"[{RUN_LABEL}] completed_compact_file={compact_index}/{len(compact_files)} rows={rows_in_file} "
            f"indexed_rows={indexed_rows}/{total_expected_rows}",
            flush=True,
        )
    return file_rows


def blocked_manifest(output_dir: Path, blocked_reasons: list[str]) -> dict[str, Any]:
    manifest = {
        "asset_id": ASSET_ID,
        "asset_kind": "ngram_hamming_fast_runtime_index",
        "asset_status": "blocked",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_compact_asset_id": COMPACT_ASSET_ID,
        "source_asset_id": SOURCE_ASSET_ID,
        "runtime_format": RUNTIME_FORMAT,
        "blocked_reasons": blocked_reasons,
        "production_scorer_change": PRODUCTION_SCORER_CHANGE,
        "counts_are_diagnostic_only": COUNTS_ARE_DIAGNOSTIC_ONLY,
        "log_counts_are_diagnostic_only": LOG_COUNTS_ARE_DIAGNOSTIC_ONLY,
        "sample_asset_used": False,
        "old_phrase_index_v1_used": False,
        "files": [],
    }
    write_outputs(output_dir, manifest, [])
    return manifest


def build_fast_runtime_lookup_index(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    compact_manifest = json.loads((REPO_ROOT / COMPACT_MANIFEST_REL).read_text(encoding="utf-8"))
    compact_validation = json.loads((REPO_ROOT / COMPACT_VALIDATION_MANIFEST_REL).read_text(encoding="utf-8"))
    blocked = compact_ready_errors(compact_manifest, compact_validation)
    if blocked:
        return blocked_manifest(selected_output_dir, blocked)
    files = build_runtime_index_files(compact_manifest, selected_output_dir)
    phrase_rows_indexed = sum(int(row["phrase_count"]) for row in files)
    manifest = {
        "asset_id": ASSET_ID,
        "asset_kind": "ngram_hamming_fast_runtime_index",
        "asset_status": "built",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_compact_asset_id": COMPACT_ASSET_ID,
        "source_asset_id": SOURCE_ASSET_ID,
        "source_compact_validation_status": compact_validation.get("status"),
        "runtime_format": RUNTIME_FORMAT,
        "orders": compact_manifest.get("orders", []),
        "cuts": compact_manifest.get("cuts", []),
        "directions": compact_manifest.get("directions", []),
        "production_scorer_change": PRODUCTION_SCORER_CHANGE,
        "counts_are_diagnostic_only": COUNTS_ARE_DIAGNOSTIC_ONLY,
        "log_counts_are_diagnostic_only": LOG_COUNTS_ARE_DIAGNOSTIC_ONLY,
        "sample_asset_used": False,
        "old_phrase_index_v1_used": False,
        "full_raw_shards_used_directly_as_runtime": False,
        "max_runtime_rows_per_file": MAX_RUNTIME_ROWS_PER_FILE,
        "group_count": len(files),
        "phrase_rows_indexed": phrase_rows_indexed,
        "source_compact_row_count": compact_manifest.get("row_count_after_dedup", phrase_rows_indexed),
        "files": files,
    }
    write_outputs(selected_output_dir, manifest, files)
    return manifest


def write_outputs(output_dir: Path, manifest: Mapping[str, Any], files: list[Mapping[str, Any]]) -> None:
    write_json(output_dir / "runtime_index_manifest.json", manifest)
    write_csv(output_dir / "runtime_index_file_rows.csv", files, (
        "path", "role", "direction", "ngram_order", "dictionary_cut", "phrase_token_length",
        "word_token_lengths", "chunk_index", "max_runtime_rows_per_file", "phrase_count",
        "token_dtype", "runtime_format", "bytes", "sha256",
    ))
    write_csv(output_dir / "runtime_index_group_summary_rows.csv", files, (
        "direction", "ngram_order", "dictionary_cut", "phrase_token_length",
        "word_token_lengths", "chunk_index", "max_runtime_rows_per_file", "phrase_count", "token_dtype",
    ))
    write_readout(output_dir / "readout.md", manifest)
    write_asset_metadata(REPO_ROOT / ASSET_META_DIR_REL, output_dir, manifest)


def write_asset_metadata(asset_dir: Path, output_dir: Path, manifest: Mapping[str, Any]) -> None:
    metadata = {
        **dict(manifest),
        "payload_storage_mode": "local_output_payload_due_large_size",
        "payload_manifest": repo_rel(output_dir / "runtime_index_manifest.json"),
        "payload_root": repo_rel(output_dir),
    }
    write_json(asset_dir / "asset_manifest.json", metadata)
    ensure_under_repo(asset_dir / "README.md")
    lines = [
        "# Phase B Full Raw Fast N-gram Hamming Runtime Index v1",
        "",
        "This git-facing metadata describes the grouped packed-array runtime index",
        "derived from the compact full raw lookup asset.",
        "",
        "The runtime payload is local/output-based because it may be too large for",
        "normal source-control tracking.",
        "",
        f"- payload root: `{metadata['payload_root']}`",
        f"- payload manifest: `{metadata['payload_manifest']}`",
        f"- source compact asset id: `{metadata.get('source_compact_asset_id', '')}`",
        f"- runtime format: `{metadata.get('runtime_format', '')}`",
        f"- counts/log-counts diagnostic only: `{metadata.get('counts_are_diagnostic_only', False)}`",
    ]
    (asset_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readout(path: Path, manifest: Mapping[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# Phase B N-gram Hamming Fast Runtime Lookup Index v1",
        "",
        f"Status: `{manifest.get('asset_status', '')}`",
        "",
        f"- asset id: `{manifest.get('asset_id', '')}`",
        f"- source compact asset id: `{manifest.get('source_compact_asset_id', '')}`",
        f"- source compact validation status: `{manifest.get('source_compact_validation_status', '')}`",
        f"- runtime format: `{manifest.get('runtime_format', '')}`",
        f"- max runtime rows per file: `{manifest.get('max_runtime_rows_per_file', 0)}`",
        f"- group count: `{manifest.get('group_count', 0)}`",
        f"- phrase rows indexed: `{manifest.get('phrase_rows_indexed', 0)}`",
        f"- production scorer change: `{manifest.get('production_scorer_change', False)}`",
        "",
        "Counts and log-counts are diagnostic arrays only.",
    ]
    if manifest.get("blocked_reasons"):
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in manifest["blocked_reasons"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    manifest = build_fast_runtime_lookup_index()
    print(f"[{RUN_LABEL}] status={manifest.get('asset_status')}")
    print(f"[{RUN_LABEL}] group_count={manifest.get('group_count', 0)}")
    print(f"[{RUN_LABEL}] phrase_rows_indexed={manifest.get('phrase_rows_indexed', 0)}")


if __name__ == "__main__":
    main()
