from __future__ import annotations

import csv
import gzip
import heapq
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    import duckdb
except ImportError:  # pragma: no cover - optional full-build accelerator
    duckdb = None


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.scoring.ngram_hamming.reference import phrase_entry_from_asset_row  # noqa: E402


RUN_LABEL = "phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1"
SOURCE_ASSET_MANIFEST_REL = "assets/ngram_hamming/phaseB_full_raw_v1/asset_manifest.json"
SOURCE_VALIDATION_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_local_payload_copy_validation_v1/validation_manifest.json"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1"
)
ASSET_META_DIR_REL = "assets/ngram_hamming/phaseB_full_raw_compact_lookup_v1"
ASSET_ID = "phaseB_ngram_hamming_full_raw_compact_lookup_v1"
SOURCE_ASSET_ID = "phaseB_ngram_hamming_full_raw_v1"
ORDERS = (2, 3)
CUTS = ("normal", "strict")
DIRECTIONS = ("fwd",)
PRODUCTION_SCORER_CHANGE = False
COUNTS_ARE_DIAGNOSTIC_ONLY = True
LOG_COUNTS_ARE_DIAGNOSTIC_ONLY = True
EXTERNAL_SORT_CHUNK_ROWS = 500000
USE_DUCKDB_COMPACT_BUILDER = True
DUCKDB_PARTITION_SOURCE_FILES = 5
CANONICAL_FIELDS = (
    "direction",
    "dictionary_cut",
    "ngram_order",
    "word_token_tuple",
    "rune_token_tuple",
)
COMPACT_FIELDNAMES = (
    "phrase_id",
    "direction",
    "dictionary_cut",
    "ngram_order",
    "word_token_tuple",
    "rune_token_tuple",
    "phrase_token_length",
    "word_token_lengths",
    "word_count",
    "source_row_count",
    "duplicate_row_count",
    "sum_count",
    "max_count",
    "sum_log_count",
    "max_log_count",
    "source_file_count",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024 * 4), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity_payload(
    *,
    direction: str,
    dictionary_cut: str,
    ngram_order: int,
    word_token_tuple: tuple[tuple[int, ...], ...],
    rune_token_tuple: tuple[int, ...],
) -> str:
    return json.dumps(
        {
            "direction": direction,
            "dictionary_cut": dictionary_cut,
            "ngram_order": ngram_order,
            "word_token_tuple": word_token_tuple,
            "rune_token_tuple": rune_token_tuple,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def identity_sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def phrase_id_for(identity_hash: str) -> str:
    return f"phrase_{identity_hash}"


def selected_payload_rows(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in manifest.get("files", [])
        if str(row.get("role", "")) == "shard_payload"
        and int(row.get("ngram_order", -1)) in ORDERS
        and str(row.get("dictionary_cut", "")) in CUTS
        and str(row.get("direction", "")) in DIRECTIONS
    ]


def compact_row_from_entry(entry: Any, source_path: str) -> dict[str, Any]:
    word_token_tuple = tuple(tuple(int(token) for token in word) for word in entry.word_token_ids)
    rune_token_tuple = tuple(int(token) for token in entry.rune_token_ids)
    payload = identity_payload(
        direction=entry.direction,
        dictionary_cut=entry.dictionary_cut,
        ngram_order=int(entry.ngram_order),
        word_token_tuple=word_token_tuple,
        rune_token_tuple=rune_token_tuple,
    )
    ident = identity_sha256(payload)
    phrase_id = phrase_id_for(ident)
    word_lengths = tuple(len(word) for word in word_token_tuple)
    return {
        "phrase_id": phrase_id,
        "direction": entry.direction,
        "dictionary_cut": entry.dictionary_cut,
        "ngram_order": int(entry.ngram_order),
        "word_token_tuple": json.dumps(word_token_tuple, separators=(",", ":")),
        "rune_token_tuple": json.dumps(rune_token_tuple, separators=(",", ":")),
        "phrase_token_length": int(entry.phrase_token_length),
        "word_token_lengths": json.dumps(word_lengths, separators=(",", ":")),
        "word_count": len(word_token_tuple),
        "source_row_count": 1,
        "duplicate_row_count": 0,
        "sum_count": float(entry.count),
        "max_count": float(entry.count),
        "sum_log_count": float(entry.log_count),
        "max_log_count": float(entry.log_count),
        "source_file_count": 1,
        "identity_sha256": ident,
        "source_path": source_path,
    }


def compact_row_from_raw(row: Mapping[str, Any], source_path: str) -> dict[str, Any]:
    word_raw = json.loads(str(row.get("word_token_ids", "")))
    rune_raw = json.loads(str(row.get("rune_token_ids", "")))
    rune_lengths_raw = json.loads(str(row.get("rune_lengths", "")))
    word_token_tuple = tuple(tuple(int(token) for token in word) for word in word_raw)
    rune_token_tuple = tuple(int(token) for token in rune_raw)
    word_lengths = tuple(len(word) for word in word_token_tuple)
    if not word_token_tuple or any(not word for word in word_token_tuple):
        raise ValueError("word_token_ids contains an empty word")
    if tuple(token for word in word_token_tuple for token in word) != rune_token_tuple:
        raise ValueError("flatten(word_token_ids) != rune_token_ids")
    if word_lengths != tuple(int(item) for item in rune_lengths_raw):
        raise ValueError("word_token_ids lengths != rune_lengths")
    ngram_order = int(row.get("n", len(word_token_tuple)))
    if len(word_token_tuple) != ngram_order:
        raise ValueError("word_token_ids group count != n")
    direction = str(row.get("encoding_direction", ""))
    dictionary_cut = str(row.get("dictionary_cut", ""))
    payload = identity_payload(
        direction=direction,
        dictionary_cut=dictionary_cut,
        ngram_order=ngram_order,
        word_token_tuple=word_token_tuple,
        rune_token_tuple=rune_token_tuple,
    )
    ident = identity_sha256(payload)
    count = float(row.get("count", 0.0) or 0.0)
    log_count = float(row.get("log_count", 0.0) or 0.0)
    return {
        "phrase_id": phrase_id_for(ident),
        "direction": direction,
        "dictionary_cut": dictionary_cut,
        "ngram_order": ngram_order,
        "word_token_tuple": json.dumps(word_token_tuple, separators=(",", ":")),
        "rune_token_tuple": json.dumps(rune_token_tuple, separators=(",", ":")),
        "phrase_token_length": len(rune_token_tuple),
        "word_token_lengths": json.dumps(word_lengths, separators=(",", ":")),
        "word_count": len(word_token_tuple),
        "source_row_count": 1,
        "duplicate_row_count": 0,
        "sum_count": count,
        "max_count": count,
        "sum_log_count": log_count,
        "max_log_count": log_count,
        "source_file_count": 1,
        "identity_sha256": ident,
        "source_path": source_path,
    }


def compact_rel_path(direction: str, order: int, cut: str) -> str:
    return (
        f"compact_rows/direction={direction}/order={order}/cut={cut}/"
        "phrase_lookup_rows.csv.gz"
    )


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def duckdb_path(path: Path) -> str:
    return path.resolve().as_posix()


def build_duckdb_partition(
    *,
    source_paths: list[str],
    partition_path: Path,
    db_path: Path,
) -> tuple[int, int, int]:
    source_list = "[" + ",".join(sql_literal(path) for path in source_paths) + "]"
    db_path.unlink(missing_ok=True)
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("PRAGMA threads=4")
        conn.execute(
            f"""
            CREATE TEMP TABLE compact AS
            WITH raw AS (
                SELECT *
                FROM read_csv({source_list}, header=true, filename=true, union_by_name=true)
            ),
            normalised AS (
                SELECT
                    encoding_direction::VARCHAR AS direction,
                    dictionary_cut::VARCHAR AS dictionary_cut,
                    n::INTEGER AS ngram_order,
                    replace(word_token_ids::VARCHAR, ' ', '') AS word_token_tuple,
                    replace(rune_token_ids::VARCHAR, ' ', '') AS rune_token_tuple,
                    replace(rune_lengths::VARCHAR, ' ', '') AS word_token_lengths,
                    json_array_length(rune_token_ids::JSON)::INTEGER AS phrase_token_length,
                    json_array_length(word_token_ids::JSON)::INTEGER AS word_count,
                    COALESCE(TRY_CAST("count" AS DOUBLE), 0.0) AS row_count_value,
                    COALESCE(TRY_CAST(log_count AS DOUBLE), 0.0) AS row_log_count_value,
                    filename::VARCHAR AS source_file
                FROM raw
            ),
            keyed AS (
                SELECT
                    *,
                    sha256(
                        direction || '|' || dictionary_cut || '|' || ngram_order::VARCHAR || '|'
                        || word_token_tuple || '|' || rune_token_tuple
                    ) AS identity_sha256
                FROM normalised
            )
            SELECT
                'phrase_' || identity_sha256 AS phrase_id,
                direction,
                dictionary_cut,
                ngram_order,
                word_token_tuple,
                rune_token_tuple,
                phrase_token_length,
                word_token_lengths,
                word_count,
                COUNT(*)::BIGINT AS source_row_count,
                (COUNT(*) - 1)::BIGINT AS duplicate_row_count,
                SUM(row_count_value)::DOUBLE AS sum_count,
                MAX(row_count_value)::DOUBLE AS max_count,
                SUM(row_log_count_value)::DOUBLE AS sum_log_count,
                MAX(row_log_count_value)::DOUBLE AS max_log_count,
                COUNT(DISTINCT source_file)::BIGINT AS source_file_count,
                identity_sha256
            FROM keyed
            GROUP BY
                identity_sha256, direction, dictionary_cut, ngram_order, word_token_tuple,
                rune_token_tuple, phrase_token_length, word_token_lengths, word_count
            """
        )
        conn.execute(
            f"""
            COPY (
                SELECT
                    phrase_id, direction, dictionary_cut, ngram_order, word_token_tuple,
                    rune_token_tuple, phrase_token_length, word_token_lengths, word_count,
                    source_row_count, duplicate_row_count, sum_count, max_count,
                    sum_log_count, max_log_count, source_file_count, identity_sha256
                FROM compact
                ORDER BY direction, dictionary_cut, ngram_order, phrase_token_length,
                         word_token_lengths, rune_token_tuple, word_token_tuple, identity_sha256
            )
            TO {sql_literal(duckdb_path(partition_path))}
            (HEADER, DELIMITER ',', COMPRESSION GZIP)
            """
        )
        stats = conn.execute(
            """
            SELECT
                COALESCE(SUM(source_row_count), 0)::BIGINT,
                COUNT(*)::BIGINT,
                COALESCE(SUM(duplicate_row_count), 0)::BIGINT
            FROM compact
            """
        ).fetchone()
    finally:
        conn.close()
    db_path.unlink(missing_ok=True)
    return int(stats[0]), int(stats[1]), int(stats[2])


def merge_compact_partition_files(
    partition_paths: list[Path],
    compact_path: Path,
    *,
    direction: str,
    order: int,
    cut: str,
) -> tuple[int, int, int]:
    ensure_under_repo(compact_path)
    handles: list[Any] = []
    readers: list[csv.DictReader] = []
    heap: list[tuple[tuple[Any, ...], int, dict[str, str]]] = []
    started = time.monotonic()
    last_progress = started
    try:
        for idx, partition_path in enumerate(partition_paths):
            handle = gzip.open(partition_path, "rt", encoding="utf-8", newline="")
            reader = csv.DictReader(handle)
            handles.append(handle)
            readers.append(reader)
            try:
                row = next(reader)
            except StopIteration:
                continue
            heapq.heappush(heap, (compact_sort_key(row), idx, row))
        row_count_before = 0
        row_count_after = 0
        duplicate_identity_count = 0
        with gzip.open(compact_path, "wt", encoding="utf-8", newline="") as out_handle:
            writer = csv.DictWriter(out_handle, fieldnames=list(COMPACT_FIELDNAMES))
            writer.writeheader()
            current: dict[str, Any] | None = None
            while heap:
                _key, idx, row = heapq.heappop(heap)
                row_count_before += int(row["source_row_count"])
                now = time.monotonic()
                if row_count_before % 5_000_000 == 0 or now - last_progress >= 300:
                    print(
                        f"[{RUN_LABEL}] group={direction}/{order}/{cut} engine=duckdb_partitioned "
                        f"merge_rows_before={row_count_before} merge_rows_after={row_count_after} "
                        f"elapsed_seconds={now - started:.1f}",
                        flush=True,
                    )
                    last_progress = now
                if current is None:
                    current = dict(row)
                elif str(row["identity_sha256"]) == str(current["identity_sha256"]):
                    current["source_row_count"] = int(current["source_row_count"]) + int(row["source_row_count"])
                    current["duplicate_row_count"] = int(current["duplicate_row_count"]) + int(row["duplicate_row_count"]) + 1
                    current["sum_count"] = float(current["sum_count"]) + float(row["sum_count"])
                    current["max_count"] = max(float(current["max_count"]), float(row["max_count"]))
                    current["sum_log_count"] = float(current["sum_log_count"]) + float(row["sum_log_count"])
                    current["max_log_count"] = max(float(current["max_log_count"]), float(row["max_log_count"]))
                    current["source_file_count"] = int(current["source_file_count"]) + int(row["source_file_count"])
                else:
                    writer.writerow({field: current.get(field, "") for field in COMPACT_FIELDNAMES})
                    duplicate_identity_count += int(current["duplicate_row_count"])
                    row_count_after += 1
                    current = dict(row)
                try:
                    next_row = next(readers[idx])
                except StopIteration:
                    continue
                heapq.heappush(heap, (compact_sort_key(next_row), idx, next_row))
            if current is not None:
                writer.writerow({field: current.get(field, "") for field in COMPACT_FIELDNAMES})
                duplicate_identity_count += int(current["duplicate_row_count"])
                row_count_after += 1
        return row_count_before, row_count_after, duplicate_identity_count
    finally:
        for handle in handles:
            handle.close()


def build_group_with_duckdb(
    rows: list[dict[str, Any]],
    *,
    output_dir: Path,
    direction: str,
    order: int,
    cut: str,
) -> dict[str, Any] | None:
    if duckdb is None or not USE_DUCKDB_COMPACT_BUILDER:
        return None
    group_key = f"direction={direction}__order={order}__cut={cut}"
    complete_path = output_dir / "work" / f"{group_key}.complete.json"
    if complete_path.is_file():
        return json.loads(complete_path.read_text(encoding="utf-8"))
    compact_rel = compact_rel_path(direction, order, cut)
    compact_path = output_dir / compact_rel
    ensure_under_repo(compact_path)
    group_work_dir = output_dir / "work" / group_key
    ensure_under_repo(group_work_dir / "placeholder")
    source_paths = [duckdb_path(REPO_ROOT / str(row["path"])) for row in rows]
    if not source_paths:
        write_empty_compact_file(compact_path)
        result = group_result(
            compact_path=compact_path,
            direction=direction,
            order=order,
            cut=cut,
            row_count_before=0,
            row_count_after=0,
            duplicate_identity_count=0,
            invalid_rows=0,
            builder_engine="duckdb_partitioned",
            elapsed_seconds=0.0,
        )
        write_json(complete_path, result)
        return result
    started = time.monotonic()
    partition_paths: list[Path] = []
    for start in range(0, len(source_paths), DUCKDB_PARTITION_SOURCE_FILES):
        batch = source_paths[start:start + DUCKDB_PARTITION_SOURCE_FILES]
        partition_index = len(partition_paths)
        partition_path = group_work_dir / f"partition_{partition_index:06d}.csv.gz"
        partition_complete = group_work_dir / f"partition_{partition_index:06d}.complete.json"
        db_path = group_work_dir / f"partition_{partition_index:06d}.duckdb"
        if partition_complete.is_file() and partition_path.is_file():
            partition_paths.append(partition_path)
            continue
        partition_path.unlink(missing_ok=True)
        db_path.unlink(missing_ok=True)
        build_duckdb_partition(source_paths=batch, partition_path=partition_path, db_path=db_path)
        write_json(
            partition_complete,
            {
                "partition_index": partition_index,
                "path": repo_rel(partition_path),
                "source_file_count": len(batch),
                "bytes": partition_path.stat().st_size,
                "sha256": sha256_file(partition_path),
            },
        )
        partition_paths.append(partition_path)
        elapsed = time.monotonic() - started
        print(
            f"[{RUN_LABEL}] group={direction}/{order}/{cut} engine=duckdb_partitioned "
            f"partitions={len(partition_paths)}/{(len(source_paths) + DUCKDB_PARTITION_SOURCE_FILES - 1) // DUCKDB_PARTITION_SOURCE_FILES} "
            f"source_files={min(start + DUCKDB_PARTITION_SOURCE_FILES, len(source_paths))}/{len(source_paths)} "
            f"elapsed_seconds={elapsed:.1f}",
            flush=True,
        )
    row_count_before, row_count_after, duplicate_identity_count = merge_compact_partition_files(
        partition_paths,
        compact_path,
        direction=direction,
        order=order,
        cut=cut,
    )
    for partition_path in partition_paths:
        partition_path.unlink(missing_ok=True)
        (partition_path.parent / partition_path.name.replace(".csv.gz", ".complete.json")).unlink(missing_ok=True)
    elapsed = time.monotonic() - started
    result = group_result(
        compact_path=compact_path,
        direction=direction,
        order=order,
        cut=cut,
        row_count_before=row_count_before,
        row_count_after=row_count_after,
        duplicate_identity_count=duplicate_identity_count,
        invalid_rows=0,
        builder_engine="duckdb_partitioned",
        elapsed_seconds=round(elapsed, 3),
    )
    write_json(complete_path, result)
    print(
        f"[{RUN_LABEL}] group={direction}/{order}/{cut} engine=duckdb_partitioned "
        f"rows_before={result['row_count_before_dedup']} rows_after={result['row_count_after_dedup']} "
        f"elapsed_seconds={elapsed:.1f}",
        flush=True,
    )
    return result


def write_empty_compact_file(compact_path: Path) -> None:
    ensure_under_repo(compact_path)
    with gzip.open(compact_path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COMPACT_FIELDNAMES))
        writer.writeheader()


def group_result(
    *,
    compact_path: Path,
    direction: str,
    order: int,
    cut: str,
    row_count_before: int,
    row_count_after: int,
    duplicate_identity_count: int,
    invalid_rows: int,
    builder_engine: str,
    elapsed_seconds: float,
) -> dict[str, Any]:
    file_hash = sha256_file(compact_path)
    file_bytes = compact_path.stat().st_size
    return {
        "path": repo_rel(compact_path),
        "role": "compact_phrase_lookup_rows",
        "direction": direction,
        "ngram_order": order,
        "dictionary_cut": cut,
        "row_count_before_dedup": row_count_before,
        "row_count_after_dedup": row_count_after,
        "duplicate_identity_count": duplicate_identity_count,
        "invalid_rows": invalid_rows,
        "bytes": file_bytes,
        "sha256": file_hash,
        "builder_engine": builder_engine,
        "elapsed_seconds": elapsed_seconds,
    }


def compact_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row["direction"]),
        str(row["dictionary_cut"]),
        int(row["ngram_order"]),
        int(row["phrase_token_length"]),
        str(row["word_token_lengths"]),
        str(row["rune_token_tuple"]),
        str(row["word_token_tuple"]),
        str(row["identity_sha256"]),
    )


def write_chunk(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_under_repo(path)
    rows.sort(key=compact_sort_key)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*COMPACT_FIELDNAMES, "source_path"])
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in [*COMPACT_FIELDNAMES, "source_path"]})


def open_chunk_reader(path: Path) -> Any:
    handle = gzip.open(path, "rt", encoding="utf-8", newline="")
    reader = csv.DictReader(handle)
    return handle, reader


def merge_sorted_chunks(chunk_paths: list[Path], compact_path: Path) -> tuple[int, int]:
    ensure_under_repo(compact_path)
    handles: list[Any] = []
    heap: list[tuple[tuple[Any, ...], int, dict[str, str]]] = []
    try:
        for idx, chunk_path in enumerate(chunk_paths):
            handle, reader = open_chunk_reader(chunk_path)
            handles.append(handle)
            try:
                row = next(reader)
            except StopIteration:
                continue
            heapq.heappush(heap, (compact_sort_key(row), idx, row))
            handles.append(reader)
        readers = [item for item in handles if isinstance(item, csv.DictReader)]
        file_handles = [item for item in handles if not isinstance(item, csv.DictReader)]
        row_count_after = 0
        duplicate_identity_count = 0
        with gzip.open(compact_path, "wt", encoding="utf-8", newline="") as out_handle:
            writer = csv.DictWriter(out_handle, fieldnames=list(COMPACT_FIELDNAMES))
            writer.writeheader()
            current: dict[str, Any] | None = None
            current_sources: set[str] = set()
            while heap:
                _key, idx, row = heapq.heappop(heap)
                ident = str(row["identity_sha256"])
                if current is None:
                    current = dict(row)
                    current_sources = {str(row.get("source_path", ""))}
                elif ident == str(current["identity_sha256"]):
                    current["source_row_count"] = int(current["source_row_count"]) + int(row["source_row_count"])
                    current["sum_count"] = float(current["sum_count"]) + float(row["sum_count"])
                    current["max_count"] = max(float(current["max_count"]), float(row["max_count"]))
                    current["sum_log_count"] = float(current["sum_log_count"]) + float(row["sum_log_count"])
                    current["max_log_count"] = max(float(current["max_log_count"]), float(row["max_log_count"]))
                    current_sources.add(str(row.get("source_path", "")))
                else:
                    source_row_count = int(current["source_row_count"])
                    current["duplicate_row_count"] = max(0, source_row_count - 1)
                    current["source_file_count"] = len(current_sources)
                    duplicate_identity_count += int(current["duplicate_row_count"])
                    writer.writerow({field: current.get(field, "") for field in COMPACT_FIELDNAMES})
                    row_count_after += 1
                    current = dict(row)
                    current_sources = {str(row.get("source_path", ""))}
                try:
                    next_row = next(readers[idx])
                except StopIteration:
                    continue
                heapq.heappush(heap, (compact_sort_key(next_row), idx, next_row))
            if current is not None:
                source_row_count = int(current["source_row_count"])
                current["duplicate_row_count"] = max(0, source_row_count - 1)
                current["source_file_count"] = len(current_sources)
                duplicate_identity_count += int(current["duplicate_row_count"])
                writer.writerow({field: current.get(field, "") for field in COMPACT_FIELDNAMES})
                row_count_after += 1
        for handle in file_handles:
            handle.close()
        return row_count_after, duplicate_identity_count
    finally:
        for item in handles:
            if hasattr(item, "close"):
                try:
                    item.close()
                except Exception:
                    pass


def build_group(
    rows: list[dict[str, Any]],
    *,
    output_dir: Path,
    direction: str,
    order: int,
    cut: str,
) -> dict[str, Any]:
    accelerated = build_group_with_duckdb(rows, output_dir=output_dir, direction=direction, order=order, cut=cut)
    if accelerated is not None:
        return accelerated
    group_key = f"direction={direction}__order={order}__cut={cut}"
    complete_path = output_dir / "work" / f"{group_key}.complete.json"
    if complete_path.is_file():
        return json.loads(complete_path.read_text(encoding="utf-8"))
    work_dir = output_dir / "work" / group_key
    ensure_under_repo(work_dir / "placeholder")
    for stale in work_dir.glob("chunk_*.csv.gz"):
        stale.unlink()
    started = time.monotonic()
    row_count_before = 0
    invalid_rows = 0
    chunk_paths: list[Path] = []
    chunk_rows: list[dict[str, Any]] = []
    for file_index, file_row in enumerate(rows, start=1):
        rel_path = str(file_row["path"])
        with gzip.open(REPO_ROOT / rel_path, "rt", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for raw in reader:
                row_count_before += 1
                try:
                    chunk_rows.append(compact_row_from_raw(raw, rel_path))
                except Exception:
                    invalid_rows += 1
                    continue
                if len(chunk_rows) >= EXTERNAL_SORT_CHUNK_ROWS:
                    chunk_path = work_dir / f"chunk_{len(chunk_paths):06d}.csv.gz"
                    write_chunk(chunk_path, chunk_rows)
                    chunk_paths.append(chunk_path)
                    chunk_rows = []
                if row_count_before % 1000000 == 0:
                    elapsed = time.monotonic() - started
                    rows_per_second = row_count_before / elapsed if elapsed > 0 else 0.0
                    eta_seconds = int((sum(int(item.get("aggregate_rows", 0)) for item in rows) - row_count_before) / rows_per_second) if rows_per_second else 0
                    print(
                        f"[{RUN_LABEL}] group={direction}/{order}/{cut} rows={row_count_before} "
                        f"files={file_index}/{len(rows)} elapsed_seconds={elapsed:.1f} eta_seconds={eta_seconds}",
                        flush=True,
                    )
    if chunk_rows:
        chunk_path = work_dir / f"chunk_{len(chunk_paths):06d}.csv.gz"
        write_chunk(chunk_path, chunk_rows)
        chunk_paths.append(chunk_path)
    compact_rel = compact_rel_path(direction, order, cut)
    compact_path = output_dir / compact_rel
    row_count_after, duplicate_identity_count = merge_sorted_chunks(chunk_paths, compact_path)
    for chunk_path in chunk_paths:
        chunk_path.unlink(missing_ok=True)
    file_hash = sha256_file(compact_path)
    file_bytes = compact_path.stat().st_size
    result = {
        "path": repo_rel(compact_path),
        "role": "compact_phrase_lookup_rows",
        "direction": direction,
        "ngram_order": order,
        "dictionary_cut": cut,
        "row_count_before_dedup": row_count_before,
        "row_count_after_dedup": row_count_after,
        "duplicate_identity_count": duplicate_identity_count,
        "invalid_rows": invalid_rows,
        "bytes": file_bytes,
        "sha256": file_hash,
    }
    write_json(complete_path, result)
    return result


def build_compact_lookup_asset(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    source_manifest = json.loads((REPO_ROOT / SOURCE_ASSET_MANIFEST_REL).read_text(encoding="utf-8"))
    validation = json.loads((REPO_ROOT / SOURCE_VALIDATION_MANIFEST_REL).read_text(encoding="utf-8"))
    blocked_reasons: list[str] = []
    if source_manifest.get("asset_id") != SOURCE_ASSET_ID:
        blocked_reasons.append("source asset id is not phaseB_ngram_hamming_full_raw_v1")
    if source_manifest.get("asset_mode") != "full":
        blocked_reasons.append("source asset mode is not full")
    if validation.get("status") != "pass":
        blocked_reasons.append("source payload validation status is not pass")
    if blocked_reasons:
        manifest = blocked_manifest(selected_output_dir, blocked_reasons)
        return manifest

    rows = selected_payload_rows(source_manifest)
    files: list[dict[str, Any]] = []
    for order in ORDERS:
        for cut in CUTS:
            for direction in DIRECTIONS:
                group_rows = [
                    row for row in rows
                    if int(row.get("ngram_order", -1)) == order
                    and str(row.get("dictionary_cut", "")) == cut
                    and str(row.get("direction", "")) == direction
                ]
                files.append(build_group(group_rows, output_dir=selected_output_dir, direction=direction, order=order, cut=cut))

    row_count_before = sum(int(row["row_count_before_dedup"]) for row in files)
    row_count_after = sum(int(row["row_count_after_dedup"]) for row in files)
    duplicate_identity_count = sum(int(row["duplicate_identity_count"]) for row in files)
    manifest = {
        "asset_id": ASSET_ID,
        "asset_kind": "ngram_hamming_compact_phrase_lookup",
        "asset_status": "built",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_asset_id": SOURCE_ASSET_ID,
        "source_asset_mode": "full",
        "source_payload_validation_status": validation.get("status"),
        "runtime_authority": "diagnostic_and_report_only_candidate_input",
        "production_scorer_change": PRODUCTION_SCORER_CHANGE,
        "orders": list(ORDERS),
        "cuts": list(CUTS),
        "directions": list(DIRECTIONS),
        "omitted_orders": [4, 5],
        "normal_strict_separate": True,
        "canonical_identity_fields": list(CANONICAL_FIELDS),
        "counts_are_diagnostic_only": COUNTS_ARE_DIAGNOSTIC_ONLY,
        "log_counts_are_diagnostic_only": LOG_COUNTS_ARE_DIAGNOSTIC_ONLY,
        "old_phrase_index_v1_used": False,
        "sample_asset_used": False,
        "row_count_before_dedup": row_count_before,
        "row_count_after_dedup": row_count_after,
        "duplicate_identity_count": duplicate_identity_count,
        "files": files,
    }
    write_outputs(selected_output_dir, manifest, files)
    return manifest


def blocked_manifest(output_dir: Path, blocked_reasons: list[str]) -> dict[str, Any]:
    manifest = {
        "asset_id": ASSET_ID,
        "asset_kind": "ngram_hamming_compact_phrase_lookup",
        "asset_status": "blocked",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_asset_id": SOURCE_ASSET_ID,
        "blocked_reasons": blocked_reasons,
        "production_scorer_change": PRODUCTION_SCORER_CHANGE,
        "old_phrase_index_v1_used": False,
        "sample_asset_used": False,
        "files": [],
    }
    write_outputs(output_dir, manifest, [])
    return manifest


def write_outputs(output_dir: Path, manifest: Mapping[str, Any], files: list[Mapping[str, Any]]) -> None:
    write_json(output_dir / "compact_asset_manifest.json", manifest)
    write_csv(output_dir / "compact_asset_file_rows.csv", files, (
        "path", "role", "direction", "ngram_order", "dictionary_cut",
        "row_count_before_dedup", "row_count_after_dedup", "duplicate_identity_count",
        "invalid_rows", "bytes", "sha256",
    ))
    write_csv(output_dir / "compact_asset_summary_rows.csv", [manifest], (
        "asset_id", "asset_kind", "asset_status", "source_asset_id", "source_asset_mode",
        "source_payload_validation_status", "row_count_before_dedup", "row_count_after_dedup",
        "duplicate_identity_count", "production_scorer_change",
    ))
    write_csv(output_dir / "deduplication_summary_rows.csv", files, (
        "direction", "ngram_order", "dictionary_cut", "row_count_before_dedup",
        "row_count_after_dedup", "duplicate_identity_count", "invalid_rows",
    ))
    write_readout(output_dir / "readout.md", manifest)
    write_asset_metadata(REPO_ROOT / ASSET_META_DIR_REL, output_dir, manifest)


def write_asset_metadata(asset_dir: Path, output_dir: Path, manifest: Mapping[str, Any]) -> None:
    metadata = {
        **dict(manifest),
        "payload_storage_mode": "local_output_payload_due_large_size",
        "payload_manifest": repo_rel(output_dir / "compact_asset_manifest.json"),
        "payload_root": repo_rel(output_dir),
    }
    write_json(asset_dir / "asset_manifest.json", metadata)
    ensure_under_repo(asset_dir / "README.md")
    lines = [
        "# Phase B Full Raw Compact N-gram Hamming Lookup v1",
        "",
        "This git-facing metadata describes the compact lookup asset derived from",
        "`assets/ngram_hamming/phaseB_full_raw_v1`.",
        "",
        "The compact payload is local/output-based because it may be too large for",
        "normal source-control tracking.",
        "",
        f"- payload root: `{metadata['payload_root']}`",
        f"- payload manifest: `{metadata['payload_manifest']}`",
        f"- source asset id: `{metadata.get('source_asset_id', '')}`",
        f"- source mode: `{metadata.get('source_asset_mode', '')}`",
        f"- counts/log-counts diagnostic only: `{metadata.get('counts_are_diagnostic_only', False)}`",
    ]
    (asset_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readout(path: Path, manifest: Mapping[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# Phase B N-gram Hamming Full Raw Compact Phrase Lookup Asset v1",
        "",
        f"Status: `{manifest.get('asset_status', '')}`",
        "",
        f"- asset id: `{manifest.get('asset_id', '')}`",
        f"- source asset id: `{manifest.get('source_asset_id', '')}`",
        f"- source asset mode: `{manifest.get('source_asset_mode', '')}`",
        f"- source payload validation status: `{manifest.get('source_payload_validation_status', '')}`",
        f"- row count before dedup: `{manifest.get('row_count_before_dedup', 0)}`",
        f"- row count after dedup: `{manifest.get('row_count_after_dedup', 0)}`",
        f"- duplicate identity count: `{manifest.get('duplicate_identity_count', 0)}`",
        f"- production scorer change: `{manifest.get('production_scorer_change', False)}`",
        "",
        "Counts and log-counts are retained as diagnostic metadata only.",
    ]
    if manifest.get("blocked_reasons"):
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in manifest["blocked_reasons"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    manifest = build_compact_lookup_asset()
    print(f"[{RUN_LABEL}] status={manifest.get('asset_status')}")
    print(f"[{RUN_LABEL}] row_count_after_dedup={manifest.get('row_count_after_dedup', 0)}")


if __name__ == "__main__":
    main()
