from __future__ import annotations

import csv
import gzip
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


RUN_LABEL = "phaseB_ngram_hamming_asset_validation_v1"
ASSET_ROOT_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_index_v1/20260514T044954Z__phaseB_filtered_ngram_index_v1"
OUTPUT_DIR_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_asset_validation_v1"
ASSET_MODE = "sample"
SAMPLE_LINE_LIMIT_PER_ORDER = 25000
FULL_ASSET_AVAILABLE = False
DIRECTIONS = ("fwd", "rev")
DICTIONARY_CUTS = ("normal", "strict")
ORDERS = (2, 3, 4, 5)
CORE_ORDERS = (2, 3, 4)
REQUIRED_FIELDS = (
    "n",
    "dictionary_cut",
    "encoding_direction",
    "rune_token_ids",
    "word_token_ids",
    "rune_lengths",
    "count",
    "log_count",
    "phrase_count",
    "top_latin_ngram",
)


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def parse_json(value: str, default: Any) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return default


def parse_flat_tokens(value: str) -> tuple[int, ...]:
    raw = parse_json(value, [])
    if not isinstance(raw, list):
        raise ValueError("rune_token_ids is not a JSON list")
    out: list[int] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError("rune_token_ids token is not an integer")
        token = item
        if token < 0 or token > 28:
            raise ValueError("token outside 0..28")
        out.append(token)
    if not out:
        raise ValueError("empty rune_token_ids")
    return tuple(out)


def parse_word_token_ids(value: str) -> tuple[tuple[int, ...], ...]:
    raw = parse_json(value, [])
    if not isinstance(raw, list):
        raise ValueError("word_token_ids is not a JSON list")
    words: list[tuple[int, ...]] = []
    for word in raw:
        if not isinstance(word, list):
            raise ValueError("word_token_ids contains a non-list word")
        parsed: list[int] = []
        for item in word:
            if isinstance(item, bool) or not isinstance(item, int):
                raise ValueError("word_token_ids token is not an integer")
            token = item
            if token < 0 or token > 28:
                raise ValueError("word token outside 0..28")
            parsed.append(token)
        if not parsed:
            raise ValueError("word_token_ids contains an empty word")
        words.append(tuple(parsed))
    if not words:
        raise ValueError("empty word_token_ids")
    return tuple(words)


def parse_int_list(value: str) -> tuple[int, ...]:
    raw = parse_json(value, [])
    if not isinstance(raw, list):
        raise ValueError("not a JSON list")
    out: list[int] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError("rune_lengths value is not an integer")
        if item <= 0:
            raise ValueError("rune_lengths value must be positive")
        out.append(item)
    if not out:
        raise ValueError("empty rune_lengths")
    return tuple(out)


def flatten(words: Iterable[Iterable[int]]) -> tuple[int, ...]:
    return tuple(token for word in words for token in word)


def quantile(values: list[int], fraction: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    pos = (len(ordered) - 1) * fraction
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return float(ordered[low])
    weight = pos - low
    return float(ordered[low] * (1.0 - weight) + ordered[high] * weight)


def validate_asset_row(row: Mapping[str, str], *, expected_cut: str, expected_direction: str, expected_order: int) -> tuple[tuple[tuple[int, ...], ...], tuple[int, ...]]:
    if row.get("dictionary_cut") != expected_cut:
        raise ValueError("dictionary_cut mismatch")
    if row.get("encoding_direction") != expected_direction:
        raise ValueError("encoding_direction mismatch")
    if int(row.get("n", "-1")) != expected_order:
        raise ValueError("n mismatch")
    rune_token_ids = parse_flat_tokens(row.get("rune_token_ids", ""))
    word_token_ids = parse_word_token_ids(row.get("word_token_ids", ""))
    rune_lengths = parse_int_list(row.get("rune_lengths", ""))
    if flatten(word_token_ids) != rune_token_ids:
        raise ValueError("flatten(word_token_ids) != rune_token_ids")
    if tuple(len(word) for word in word_token_ids) != rune_lengths:
        raise ValueError("word_token_ids lengths != rune_lengths")
    if len(word_token_ids) != expected_order:
        raise ValueError("word_token_ids group count != n")
    return word_token_ids, rune_token_ids


def asset_path(dictionary_cut: str, direction: str, order: int) -> Path:
    return REPO_ROOT / ASSET_ROOT_REL / f"{dictionary_cut}_{direction}" / f"ngram{order}.csv.gz"


def validate_asset_file(
    dictionary_cut: str,
    direction: str,
    order: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    path = asset_path(dictionary_cut, direction, order)
    summary: dict[str, Any] = {
        "path": repo_rel(path),
        "exists": path.exists(),
        "dictionary_cut": dictionary_cut,
        "direction": direction,
        "ngram_order": order,
        "raw_rows": 0,
        "valid_rows": 0,
        "invalid_rows": 0,
        "missing_required_fields": [],
        "unique_canonical_word_sequence_count": 0,
        "unique_joined_token_sequence_count": 0,
        "duplicate_canonical_word_sequence_rows": 0,
        "same_joined_different_boundary_count": 0,
        "canonical_validation_pass": False,
    }
    examples: list[dict[str, Any]] = []
    pattern_counts: Counter[tuple[int, ...]] = Counter()
    token_lengths: list[int] = []
    if not path.exists():
        return summary, examples, [], [], []

    canonical_counts: Counter[tuple[tuple[int, ...], ...]] = Counter()
    joined_to_boundaries: dict[tuple[int, ...], set[tuple[tuple[int, ...], ...]]] = defaultdict(set)
    invalid_reasons: Counter[str] = Counter()
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = [field for field in REQUIRED_FIELDS if field not in fieldnames]
        summary["missing_required_fields"] = missing
        for row in reader:
            summary["raw_rows"] += 1
            if missing:
                summary["invalid_rows"] += 1
                invalid_reasons["missing_required_fields"] += 1
                continue
            try:
                word_token_ids, rune_token_ids = validate_asset_row(
                    row,
                    expected_cut=dictionary_cut,
                    expected_direction=direction,
                    expected_order=order,
                )
            except Exception as exc:
                summary["invalid_rows"] += 1
                invalid_reasons[str(exc)] += 1
                continue
            summary["valid_rows"] += 1
            canonical_counts[word_token_ids] += 1
            joined_to_boundaries[rune_token_ids].add(word_token_ids)
            word_lengths = tuple(len(word) for word in word_token_ids)
            pattern_counts[word_lengths] += 1
            token_lengths.append(len(rune_token_ids))
            if len(examples) < 20:
                examples.append(
                    {
                        "dictionary_cut": dictionary_cut,
                        "direction": direction,
                        "ngram_order": order,
                        "canonical_word_token_ids": json.dumps(word_token_ids),
                        "rune_token_ids": json.dumps(rune_token_ids),
                        "rune_lengths": row.get("rune_lengths", ""),
                        "top_latin_ngram": row.get("top_latin_ngram", ""),
                        "count": row.get("count", ""),
                    }
                )

    summary["unique_canonical_word_sequence_count"] = len(canonical_counts)
    summary["unique_joined_token_sequence_count"] = len(joined_to_boundaries)
    summary["duplicate_canonical_word_sequence_rows"] = sum(count - 1 for count in canonical_counts.values() if count > 1)
    summary["same_joined_different_boundary_count"] = sum(1 for values in joined_to_boundaries.values() if len(values) > 1)
    summary["invalid_reason_counts"] = dict(invalid_reasons)
    summary["token_min"] = 0
    summary["token_max"] = 28
    summary["separator_token_forbidden"] = True
    summary["invalid_token_count"] = sum(count for reason, count in invalid_reasons.items() if "token" in reason)
    summary["canonical_validation_pass"] = (
        summary["exists"]
        and summary["raw_rows"] > 0
        and summary["valid_rows"] > 0
        and summary["invalid_rows"] == 0
        and not summary["missing_required_fields"]
    )
    pattern_rows = [
        {
            "dictionary_cut": dictionary_cut,
            "direction": direction,
            "ngram_order": order,
            "word_lengths": json.dumps(pattern),
            "row_count": count,
        }
        for pattern, count in pattern_counts.most_common()
    ]
    quantile_rows = [
        {
            "dictionary_cut": dictionary_cut,
            "direction": direction,
            "ngram_order": order,
            "min_phrase_token_length": min(token_lengths) if token_lengths else 0,
            "max_phrase_token_length": max(token_lengths) if token_lengths else 0,
            "q05_phrase_token_length": quantile(token_lengths, 0.05),
            "q50_phrase_token_length": quantile(token_lengths, 0.50),
            "q95_phrase_token_length": quantile(token_lengths, 0.95),
            "mean_phrase_token_length": (sum(token_lengths) / len(token_lengths) if token_lengths else 0.0),
        }
    ]
    duplicate_rows = [
        {
            "dictionary_cut": dictionary_cut,
            "direction": direction,
            "ngram_order": order,
            "canonical_word_token_ids": json.dumps(identity),
            "duplicate_row_count": count - 1,
        }
        for identity, count in canonical_counts.items()
        if count > 1
    ]
    duplicate_rows.sort(key=lambda row: (-int(row["duplicate_row_count"]), row["canonical_word_token_ids"]))
    return summary, examples, pattern_rows, quantile_rows, duplicate_rows


def validate_assets() -> dict[str, Any]:
    summaries: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []
    word_length_patterns: list[dict[str, Any]] = []
    token_length_quantiles: list[dict[str, Any]] = []
    duplicate_report: list[dict[str, Any]] = []
    for dictionary_cut in DICTIONARY_CUTS:
        for direction in DIRECTIONS:
            for order in ORDERS:
                summary, rows, pattern_rows, quantile_rows, duplicate_rows = validate_asset_file(dictionary_cut, direction, order)
                summaries.append(summary)
                examples.extend(rows)
                word_length_patterns.extend(pattern_rows)
                token_length_quantiles.extend(quantile_rows)
                duplicate_report.extend(duplicate_rows)

    core_pass = all(
        row["canonical_validation_pass"]
        for row in summaries
        if row["direction"] == "fwd" and row["ngram_order"] in CORE_ORDERS
    )
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if core_pass else "blocked",
        "asset_root": ASSET_ROOT_REL,
        "asset_mode": ASSET_MODE,
        "sample_line_limit_per_order": SAMPLE_LINE_LIMIT_PER_ORDER,
        "full_asset_available": FULL_ASSET_AVAILABLE,
        "directions": list(DIRECTIONS),
        "dictionary_cuts": list(DICTIONARY_CUTS),
        "orders": list(ORDERS),
        "core_orders": list(CORE_ORDERS),
        "uses_rune_token_ids_for_flattened_validation": True,
        "uses_word_token_ids_for_phrase_identity": True,
        "uses_rune_key_hex_for_scanning": False,
        "parser_contract": {
            "word_token_ids_format": "JSON list[list[int]]",
            "uses_eval": False,
            "allows_float_tokens": False,
            "allows_string_tokens": False,
            "allows_empty_words": False,
            "allows_empty_phrase": False,
            "rune_lengths_format": "JSON list[int]",
            "allows_float_lengths": False,
            "allows_string_lengths": False,
            "allows_nonpositive_lengths": False,
            "flatten_word_token_ids_must_equal_rune_token_ids": True,
            "word_group_count_must_equal_n": True,
            "word_lengths_must_equal_rune_lengths": True,
        },
        "token_bounds": {
            "token_min": 0,
            "token_max": 28,
            "separator_token_forbidden": True,
            "invalid_token_count": sum(int(row.get("invalid_token_count", 0)) for row in summaries),
        },
        "phrase_identity_key": [
            "direction",
            "dictionary_cut",
            "ngram_order",
            "canonical_word_token_ids",
        ],
        "core_fwd_asset_validation_pass": core_pass,
        "summaries": summaries,
        "examples": examples,
        "word_length_patterns": word_length_patterns,
        "token_length_quantiles": token_length_quantiles,
        "duplicate_report": duplicate_report,
    }
    return manifest


def write_csv(path: Path, rows: list[Mapping[str, Any]], fieldnames: list[str]) -> None:
    ensure_under_repo(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(manifest: dict[str, Any]) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    ensure_under_repo(output_dir / "ngram_hamming_asset_manifest.json")
    (output_dir / "ngram_hamming_asset_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary_fields = [
        "path",
        "exists",
        "dictionary_cut",
        "direction",
        "ngram_order",
        "raw_rows",
        "valid_rows",
        "invalid_rows",
        "missing_required_fields",
        "unique_canonical_word_sequence_count",
        "unique_joined_token_sequence_count",
        "duplicate_canonical_word_sequence_rows",
        "same_joined_different_boundary_count",
        "token_min",
        "token_max",
        "separator_token_forbidden",
        "invalid_token_count",
        "canonical_validation_pass",
    ]
    write_csv(output_dir / "ngram_hamming_asset_validation_summary.csv", manifest["summaries"], summary_fields)
    example_fields = [
        "dictionary_cut",
        "direction",
        "ngram_order",
        "canonical_word_token_ids",
        "rune_token_ids",
        "rune_lengths",
        "top_latin_ngram",
        "count",
    ]
    write_csv(output_dir / "ngram_hamming_asset_examples.csv", manifest["examples"], example_fields)
    pattern_fields = [
        "dictionary_cut",
        "direction",
        "ngram_order",
        "word_lengths",
        "row_count",
    ]
    write_csv(output_dir / "ngram_hamming_asset_word_length_patterns.csv", manifest["word_length_patterns"], pattern_fields)
    quantile_fields = [
        "dictionary_cut",
        "direction",
        "ngram_order",
        "min_phrase_token_length",
        "max_phrase_token_length",
        "q05_phrase_token_length",
        "q50_phrase_token_length",
        "q95_phrase_token_length",
        "mean_phrase_token_length",
    ]
    write_csv(output_dir / "ngram_hamming_asset_token_length_quantiles.csv", manifest["token_length_quantiles"], quantile_fields)
    duplicate_fields = [
        "dictionary_cut",
        "direction",
        "ngram_order",
        "canonical_word_token_ids",
        "duplicate_row_count",
    ]
    write_csv(output_dir / "ngram_hamming_asset_duplicate_report.csv", manifest["duplicate_report"], duplicate_fields)
    readout = [
        "# PhaseB N-Gram Hamming Asset Validation v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        "## Contract",
        "",
        "- candidate chunks are flat rune-token sequences",
        "- phrase identity uses canonical nested `word_token_ids`",
        "- flattened `rune_token_ids` is validation/diagnostic metadata",
        "- `rune_key_hex` is not used for scanning",
        "",
        "## Asset Mode",
        "",
        f"- asset mode: `{manifest['asset_mode']}`",
        f"- sample line limit per order: `{manifest['sample_line_limit_per_order']}`",
        f"- full asset available: `{manifest['full_asset_available']}`",
        "",
        "## Gate",
        "",
        f"- core FWD asset validation pass: `{manifest['core_fwd_asset_validation_pass']}`",
        "",
        "## Files",
        "",
        "- `ngram_hamming_asset_manifest.json`",
        "- `ngram_hamming_asset_validation_summary.csv`",
        "- `ngram_hamming_asset_word_length_patterns.csv`",
        "- `ngram_hamming_asset_token_length_quantiles.csv`",
        "- `ngram_hamming_asset_duplicate_report.csv`",
        "- `ngram_hamming_asset_examples.csv`",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def main() -> None:
    manifest = validate_assets()
    write_outputs(manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] wrote {OUTPUT_DIR_REL}/ngram_hamming_asset_manifest.json")


if __name__ == "__main__":
    main()
