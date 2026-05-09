from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np


# =============================================================================
# Hardcoded run configuration
# =============================================================================


TOKENIZED_ROOT_REL = "../language_model_prime/lmprime_out/tokenized"
OUTPUT_DIR_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/chunk_inventory_v1"
CHUNK_MAX_TOKENS = 500
DIRECTIONS = ("fwd", "rev")
EXCLUDE_BOOKS = (
    "1-0.txt",
    "10004.txt",
)
DICTIONARY_SPECS = (
    {
        "dictionary_cut": "phaseA14_strict_selected",
        "dictionary_path": "assets/hamming_dictionary_policies_phaseA_v0_14/strict/hamming_raw_1g",
    },
    {
        "dictionary_cut": "phaseA14_normal_selected",
        "dictionary_path": "assets/hamming_dictionary_policies_phaseA_v0_14/normal/hamming_raw_1g",
    },
)
WORD_LENGTH_BUCKETS = tuple(str(length) for length in range(1, 15)) + ("15plus",)
CONVERGENCE_THRESHOLDS = (100, 500, 1000, 2000, 5000, 10000, 20000, 50000)
QUANTILE_POINTS = (0.0, 0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 1.0)


# =============================================================================
# Repo/path helpers
# =============================================================================


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


REPO_ROOT = repo_root()


def resolve_from_repo_root(path_text: str) -> Path:
    return (REPO_ROOT / path_text).resolve()


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        try:
            return path.resolve().relative_to(REPO_ROOT.parent).as_posix()
        except ValueError:
            return path.name


def require_parent_under_repo(path: Path) -> None:
    parent = path.parent.resolve()
    root = REPO_ROOT.resolve()
    if parent != root and root not in parent.parents:
        raise ValueError(f"output parent is outside repo root: {repo_rel(parent)}")
    parent.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Tokenized file discovery/loading
# =============================================================================


def book_name_from_tokenized(path: Path, direction: str) -> str:
    suffix = f"_{direction}.npz"
    if not path.name.endswith(suffix):
        raise ValueError(f"unexpected tokenized filename for direction={direction}: {path.name}")
    return path.name[: -len(suffix)]


def discover_tokenized_files(tokenized_root: Path) -> list[tuple[str, str, Path]]:
    rows: list[tuple[str, str, Path]] = []
    for direction in DIRECTIONS:
        for path in sorted(tokenized_root.glob(f"*_{direction}.npz")):
            rows.append((book_name_from_tokenized(path, direction), direction, path))
    return rows


def complete_books_from_rows(rows: Sequence[tuple[str, str, Path]]) -> list[str]:
    by_book: dict[str, set[str]] = {}
    for book, direction, _path in rows:
        by_book.setdefault(book, set()).add(direction)
    required = set(DIRECTIONS)
    return sorted(book for book, seen in by_book.items() if required.issubset(seen))


def load_nose_arrays(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        if "pt_nose_data" not in data:
            raise KeyError(f"{repo_rel(path)} missing pt_nose_data")
        if "wli_nose_data" not in data:
            raise KeyError(f"{repo_rel(path)} missing wli_nose_data")
        tokens = np.asarray(data["pt_nose_data"], dtype=np.uint8)
        raw_wli = np.asarray(data["wli_nose_data"], dtype=np.int64)
    if raw_wli.ndim == 1:
        if raw_wli.size % 2 != 0:
            raise ValueError(f"{repo_rel(path)} wli_nose_data length is not even")
        wli = raw_wli.reshape((-1, 2))
    elif raw_wli.ndim == 2 and raw_wli.shape[1] == 2:
        wli = raw_wli
    else:
        raise ValueError(f"{repo_rel(path)} wli_nose_data has unexpected shape {raw_wli.shape}")
    if tokens.size != wli.shape[0]:
        raise ValueError(f"{repo_rel(path)} token/WLI length mismatch: tokens={tokens.size} wli={wli.shape[0]}")
    return tokens, wli


# =============================================================================
# Sequential whole-word chunking
# =============================================================================


def word_start_indices(wli: Sequence[Sequence[int]]) -> list[int]:
    return [idx for idx, pair in enumerate(wli) if int(pair[0]) == 0 and int(pair[1]) > 0]


def sequential_whole_word_chunks_for_wli(
    wli: Sequence[Sequence[int]],
    *,
    max_tokens: int = CHUNK_MAX_TOKENS,
) -> list[tuple[int, int]]:
    wli_array = np.asarray(wli, dtype=np.int64)
    if wli_array.ndim != 2 or wli_array.shape[1] != 2:
        raise ValueError(f"unexpected WLI shape {wli_array.shape}")
    positions = wli_array[:, 0]
    lengths = wli_array[:, 1]
    starts = np.flatnonzero((positions == 0) & (lengths > 0)).astype(np.int64).tolist()
    if not starts:
        return []
    start_set = set(starts)
    n = int(wli_array.shape[0])
    chunks: list[tuple[int, int]] = []
    start_idx = 0
    while start_idx < len(starts):
        start = starts[start_idx]
        best_end = start
        cursor_idx = start_idx
        while cursor_idx < len(starts):
            cursor = starts[cursor_idx]
            if cursor != best_end:
                break
            length = int(lengths[cursor])
            if length <= 0:
                break
            end = cursor + length
            if end > n or (end - start) > max_tokens:
                break
            best_end = end
            cursor_idx += 1
        if best_end > start:
            chunks.append((start, best_end))
            while start_idx < len(starts) and starts[start_idx] < best_end:
                start_idx += 1
        else:
            start_idx += 1
    return chunks


# =============================================================================
# Output
# =============================================================================


INVENTORY_FIELDS = [
    "book",
    "direction",
    "token_count",
    "chunk_count_500",
    "mean_chunk_tokens",
    "min_chunk_tokens",
    "max_chunk_tokens",
    "fwd_file_bytes",
    "rev_file_bytes",
]


TOP_BOOK_FIELDS = [
    "book",
    "chunk_count_500_total",
    "fwd_chunk_count_500",
    "rev_chunk_count_500",
    "fwd_token_count",
    "rev_token_count",
    "fwd_file_bytes",
    "rev_file_bytes",
]

CHUNK_LENGTH_QUANTILE_FIELDS = [
    "scope",
    "chunk_count",
    *[f"q{int(q * 100):03d}_chunk_tokens" for q in QUANTILE_POINTS],
]

WORD_LENGTH_HISTOGRAM_FIELDS = [
    "scope",
    "chunk_count",
    "word_count",
    *[f"len{bucket}" for bucket in WORD_LENGTH_BUCKETS],
]

WORD_LENGTH_CONVERGENCE_FIELDS = [
    "scope",
    "threshold_chunks",
    "observed_chunks",
    "word_count",
    *[f"len{bucket}" for bucket in WORD_LENGTH_BUCKETS],
]

CHUNK_VARIABILITY_FIELDS = [
    "book",
    "direction",
    "chunk_index",
    "chunk_start",
    "chunk_end",
    "chunk_tokens",
    "word_count",
    "mean_word_tokens",
    "min_word_tokens",
    "max_word_tokens",
    "stddev_word_tokens",
    "word_token_range",
    "unique_word_lengths",
]

DICTIONARY_ENTRY_COUNT_FIELDS = [
    "dictionary_cut",
    "dictionary_path",
    "span_length",
    "entry_count",
    "file_bytes",
]


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> None:
    require_parent_under_repo(path)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def bucket_chunk_count(count: int) -> str:
    if count == 1:
        return "1"
    if 2 <= count <= 10:
        return "2-10"
    if 10 < count < 100:
        return "10-100"
    if count >= 100:
        return "100+"
    return "0"


def empty_word_length_histogram() -> dict[str, int]:
    return {bucket: 0 for bucket in WORD_LENGTH_BUCKETS}


def word_length_bucket(length: int) -> str:
    return str(length) if 1 <= length <= 14 else "15plus"


def add_word_lengths(histogram: dict[str, int], word_lengths: Sequence[int]) -> None:
    for length in word_lengths:
        histogram[word_length_bucket(int(length))] += 1


def word_lengths_for_chunk(wli: np.ndarray, start: int, end: int) -> list[int]:
    positions = wli[:, 0]
    lengths = wli[:, 1]
    word_starts = np.flatnonzero((positions[start:end] == 0) & (lengths[start:end] > 0)) + int(start)
    return [int(lengths[idx]) for idx in word_starts]


def word_histogram_row(scope: str, chunk_count: int, histogram: dict[str, int]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "scope": scope,
        "chunk_count": chunk_count,
        "word_count": sum(histogram.values()),
    }
    for bucket in WORD_LENGTH_BUCKETS:
        row[f"len{bucket}"] = histogram.get(bucket, 0)
    return row


def convergence_row(scope: str, threshold: int, observed_chunks: int, histogram: dict[str, int]) -> dict[str, Any]:
    row = word_histogram_row(scope, observed_chunks, histogram)
    row["threshold_chunks"] = threshold
    row["observed_chunks"] = observed_chunks
    row.pop("chunk_count", None)
    return row


def chunk_variability_row(
    *,
    book: str,
    direction: str,
    chunk_index: int,
    chunk_start: int,
    chunk_end: int,
    word_lengths: Sequence[int],
) -> dict[str, Any]:
    lengths = np.asarray(list(word_lengths), dtype=np.float64)
    if lengths.size:
        mean = float(np.mean(lengths))
        min_value = int(np.min(lengths))
        max_value = int(np.max(lengths))
        stddev = float(np.std(lengths))
        unique_count = int(np.unique(lengths).size)
    else:
        mean = 0.0
        min_value = 0
        max_value = 0
        stddev = 0.0
        unique_count = 0
    return {
        "book": book,
        "direction": direction,
        "chunk_index": chunk_index,
        "chunk_start": chunk_start,
        "chunk_end": chunk_end,
        "chunk_tokens": chunk_end - chunk_start,
        "word_count": int(lengths.size),
        "mean_word_tokens": f"{mean:.6f}",
        "min_word_tokens": min_value,
        "max_word_tokens": max_value,
        "stddev_word_tokens": f"{stddev:.6f}",
        "word_token_range": max_value - min_value if lengths.size else 0,
        "unique_word_lengths": unique_count,
    }


def quantile_rows(chunk_lengths_by_scope: dict[str, list[int]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scope in sorted(chunk_lengths_by_scope):
        values = np.asarray(chunk_lengths_by_scope[scope], dtype=np.float64)
        row: dict[str, Any] = {"scope": scope, "chunk_count": int(values.size)}
        if values.size:
            quantiles = np.quantile(values, QUANTILE_POINTS)
        else:
            quantiles = np.zeros(len(QUANTILE_POINTS), dtype=np.float64)
        for q, value in zip(QUANTILE_POINTS, quantiles):
            row[f"q{int(q * 100):03d}_chunk_tokens"] = f"{float(value):.6f}"
        rows.append(row)
    return rows


def dictionary_entry_count_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in DICTIONARY_SPECS:
        dictionary_path = resolve_from_repo_root(str(spec["dictionary_path"]))
        for length in range(1, 15):
            path = dictionary_path / f"raw1grams_{length:02d}.csv"
            if not path.exists():
                raise FileNotFoundError(f"dictionary length file not found: {repo_rel(path)}")
            entry_count = 0
            with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
                for line in fh:
                    if line.strip():
                        entry_count += 1
            rows.append(
                {
                    "dictionary_cut": spec["dictionary_cut"],
                    "dictionary_path": repo_rel(dictionary_path),
                    "span_length": length,
                    "entry_count": entry_count,
                    "file_bytes": path.stat().st_size,
                }
            )
    return rows


def inventory_row(
    *,
    book: str,
    direction: str,
    tokens: np.ndarray,
    chunks: Sequence[tuple[int, int]],
    fwd_file_bytes: int,
    rev_file_bytes: int,
) -> dict[str, Any]:
    lengths = [end - start for start, end in chunks]
    return {
        "book": book,
        "direction": direction,
        "token_count": int(tokens.size),
        "chunk_count_500": len(chunks),
        "mean_chunk_tokens": f"{(sum(lengths) / float(len(lengths)) if lengths else 0.0):.6f}",
        "min_chunk_tokens": min(lengths) if lengths else 0,
        "max_chunk_tokens": max(lengths) if lengths else 0,
        "fwd_file_bytes": fwd_file_bytes,
        "rev_file_bytes": rev_file_bytes,
    }


def main() -> None:
    started = time.perf_counter()
    tokenized_root = resolve_from_repo_root(TOKENIZED_ROOT_REL)
    output_dir = resolve_from_repo_root(OUTPUT_DIR_REL)
    if not tokenized_root.exists():
        raise FileNotFoundError(f"tokenized root not found: {repo_rel(tokenized_root)}")
    output_dir.mkdir(parents=True, exist_ok=True)

    discovered = discover_tokenized_files(tokenized_root)
    rows_by_key = {(book, direction): path for book, direction, path in discovered}
    complete_books = [book for book in complete_books_from_rows(discovered) if book not in set(EXCLUDE_BOOKS)]

    inventory_rows: list[dict[str, Any]] = []
    chunk_variability_rows: list[dict[str, Any]] = []
    word_histograms = {
        "all": empty_word_length_histogram(),
        "fwd": empty_word_length_histogram(),
        "rev": empty_word_length_histogram(),
    }
    chunk_lengths_by_scope: dict[str, list[int]] = {"all": [], "fwd": [], "rev": []}
    convergence_histograms = {
        "all": empty_word_length_histogram(),
        "fwd": empty_word_length_histogram(),
        "rev": empty_word_length_histogram(),
    }
    convergence_counts = {"all": 0, "fwd": 0, "rev": 0}
    convergence_rows: list[dict[str, Any]] = []
    by_book: dict[str, dict[str, Any]] = {}
    for book_idx, book in enumerate(complete_books, start=1):
        fwd_path = rows_by_key[(book, "fwd")]
        rev_path = rows_by_key[(book, "rev")]
        fwd_file_bytes = fwd_path.stat().st_size
        rev_file_bytes = rev_path.stat().st_size
        book_payload: dict[str, Any] = {
            "book": book,
            "fwd_file_bytes": fwd_file_bytes,
            "rev_file_bytes": rev_file_bytes,
        }
        for direction in DIRECTIONS:
            path = rows_by_key[(book, direction)]
            tokens, wli = load_nose_arrays(path)
            chunks = sequential_whole_word_chunks_for_wli(wli, max_tokens=CHUNK_MAX_TOKENS)
            row = inventory_row(
                book=book,
                direction=direction,
                tokens=tokens,
                chunks=chunks,
                fwd_file_bytes=fwd_file_bytes,
                rev_file_bytes=rev_file_bytes,
            )
            inventory_rows.append(row)
            book_payload[f"{direction}_chunk_count_500"] = len(chunks)
            book_payload[f"{direction}_token_count"] = int(tokens.size)
            for chunk_index, (chunk_start, chunk_end) in enumerate(chunks):
                word_lengths = word_lengths_for_chunk(wli, chunk_start, chunk_end)
                chunk_length = chunk_end - chunk_start
                chunk_lengths_by_scope["all"].append(chunk_length)
                chunk_lengths_by_scope[direction].append(chunk_length)
                add_word_lengths(word_histograms["all"], word_lengths)
                add_word_lengths(word_histograms[direction], word_lengths)
                chunk_variability_rows.append(
                    chunk_variability_row(
                        book=book,
                        direction=direction,
                        chunk_index=chunk_index,
                        chunk_start=chunk_start,
                        chunk_end=chunk_end,
                        word_lengths=word_lengths,
                    )
                )
                for scope in ("all", direction):
                    convergence_counts[scope] += 1
                    add_word_lengths(convergence_histograms[scope], word_lengths)
                    count = convergence_counts[scope]
                    if count in CONVERGENCE_THRESHOLDS:
                        convergence_rows.append(
                            convergence_row(
                                scope=scope,
                                threshold=count,
                                observed_chunks=count,
                                histogram=dict(convergence_histograms[scope]),
                            )
                        )
        by_book[book] = book_payload
        if book_idx == 1 or book_idx % 50 == 0 or book_idx == len(complete_books):
            elapsed = time.perf_counter() - started
            print(f"[chunk_inventory] books={book_idx}/{len(complete_books)} elapsed={elapsed:.1f}s", flush=True)

    top_books = sorted(
        (
            {
                "book": payload["book"],
                "chunk_count_500_total": int(payload.get("fwd_chunk_count_500", 0))
                + int(payload.get("rev_chunk_count_500", 0)),
                "fwd_chunk_count_500": int(payload.get("fwd_chunk_count_500", 0)),
                "rev_chunk_count_500": int(payload.get("rev_chunk_count_500", 0)),
                "fwd_token_count": int(payload.get("fwd_token_count", 0)),
                "rev_token_count": int(payload.get("rev_token_count", 0)),
                "fwd_file_bytes": int(payload["fwd_file_bytes"]),
                "rev_file_bytes": int(payload["rev_file_bytes"]),
            }
            for payload in by_book.values()
        ),
        key=lambda row: (-int(row["chunk_count_500_total"]), str(row["book"])),
    )

    fwd_total = sum(int(row["chunk_count_500"]) for row in inventory_rows if row["direction"] == "fwd")
    rev_total = sum(int(row["chunk_count_500"]) for row in inventory_rows if row["direction"] == "rev")
    buckets = {"0": 0, "1": 0, "2-10": 0, "10-100": 0, "100+": 0}
    for row in top_books:
        buckets[bucket_chunk_count(int(row["chunk_count_500_total"]))] += 1

    inventory_path = output_dir / "chunk_inventory_by_book_direction.csv"
    top_books_path = output_dir / "top_books_by_chunk_count.csv"
    chunk_length_quantiles_path = output_dir / "chunk_length_quantiles.csv"
    word_length_histogram_path = output_dir / "word_length_histogram.csv"
    word_length_convergence_path = output_dir / "word_length_histogram_convergence.csv"
    chunk_variability_path = output_dir / "chunk_word_length_variability.csv"
    dictionary_counts_path = output_dir / "dictionary_entry_counts_by_rune_length.csv"
    summary_path = output_dir / "chunk_inventory_summary.json"
    readout_path = output_dir / "readout.md"
    chunk_length_quantile_rows = quantile_rows(chunk_lengths_by_scope)
    word_length_histogram_rows = [
        word_histogram_row(scope, len(chunk_lengths_by_scope[scope]), word_histograms[scope])
        for scope in ("all", "fwd", "rev")
    ]
    dictionary_count_rows = dictionary_entry_count_rows()
    write_csv(inventory_path, inventory_rows, INVENTORY_FIELDS)
    write_csv(top_books_path, top_books[:20], TOP_BOOK_FIELDS)
    write_csv(chunk_length_quantiles_path, chunk_length_quantile_rows, CHUNK_LENGTH_QUANTILE_FIELDS)
    write_csv(word_length_histogram_path, word_length_histogram_rows, WORD_LENGTH_HISTOGRAM_FIELDS)
    write_csv(word_length_convergence_path, convergence_rows, WORD_LENGTH_CONVERGENCE_FIELDS)
    write_csv(chunk_variability_path, chunk_variability_rows, CHUNK_VARIABILITY_FIELDS)
    write_csv(dictionary_counts_path, dictionary_count_rows, DICTIONARY_ENTRY_COUNT_FIELDS)

    elapsed = time.perf_counter() - started
    summary = {
        "chunk_max_tokens": CHUNK_MAX_TOKENS,
        "tokenized_root": repo_rel(tokenized_root),
        "output_dir": repo_rel(output_dir),
        "exclude_books": list(EXCLUDE_BOOKS),
        "complete_books_after_exclusions": len(complete_books),
        "book_direction_rows": len(inventory_rows),
        "total_unique_fwd_chunks": fwd_total,
        "total_unique_rev_chunks": rev_total,
        "total_unique_fwd_rev_chunks": fwd_total + rev_total,
        "book_chunk_count_buckets": buckets,
        "convergence_thresholds": list(CONVERGENCE_THRESHOLDS),
        "word_length_buckets": list(WORD_LENGTH_BUCKETS),
        "dictionary_entry_count_rows": len(dictionary_count_rows),
        "elapsed_seconds": round(elapsed, 3),
        "files": {
            "inventory": repo_rel(inventory_path),
            "top_books": repo_rel(top_books_path),
            "chunk_length_quantiles": repo_rel(chunk_length_quantiles_path),
            "word_length_histogram": repo_rel(word_length_histogram_path),
            "word_length_histogram_convergence": repo_rel(word_length_convergence_path),
            "chunk_word_length_variability": repo_rel(chunk_variability_path),
            "dictionary_entry_counts_by_rune_length": repo_rel(dictionary_counts_path),
            "summary": repo_rel(summary_path),
            "readout": repo_rel(readout_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    top_lines = [
        f"- `{row['book']}`: total `{row['chunk_count_500_total']}`, "
        f"fwd `{row['fwd_chunk_count_500']}`, rev `{row['rev_chunk_count_500']}`"
        for row in top_books[:20]
    ]
    bucket_lines = [f"- `{name}` chunks: `{count}` books" for name, count in buckets.items()]
    quantile_line = next(row for row in chunk_length_quantile_rows if row["scope"] == "all")
    word_hist_all = next(row for row in word_length_histogram_rows if row["scope"] == "all")
    readout = "\n".join(
        [
            "# PhaseB Runeberg NOSE 500-Rune Chunk Inventory",
            "",
            f"- CHUNK_MAX_TOKENS: `{CHUNK_MAX_TOKENS}`",
            f"- complete books after exclusions: `{len(complete_books)}`",
            f"- total unique FWD chunks: `{fwd_total}`",
            f"- total unique REV chunks: `{rev_total}`",
            f"- total unique FWD+REV chunks: `{fwd_total + rev_total}`",
            f"- all-chunk median tokens: `{quantile_line['q050_chunk_tokens']}`",
            f"- all-chunk p95 tokens: `{quantile_line['q095_chunk_tokens']}`",
            f"- aggregate word count in chunks: `{word_hist_all['word_count']}`",
            f"- elapsed seconds: `{elapsed:.3f}`",
            "",
            "## Book Count Buckets",
            "",
            *bucket_lines,
            "",
            "## Top 20 Books By Chunk Count",
            "",
            *top_lines,
            "",
            "## Files",
            "",
            f"- `{repo_rel(inventory_path)}`",
            f"- `{repo_rel(top_books_path)}`",
            f"- `{repo_rel(chunk_length_quantiles_path)}`",
            f"- `{repo_rel(word_length_histogram_path)}`",
            f"- `{repo_rel(word_length_convergence_path)}`",
            f"- `{repo_rel(chunk_variability_path)}`",
            f"- `{repo_rel(dictionary_counts_path)}`",
            f"- `{repo_rel(summary_path)}`",
        ]
    )
    readout_path.write_text(readout + "\n", encoding="utf-8")

    print(json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
