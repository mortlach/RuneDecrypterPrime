from __future__ import annotations

import csv
import gzip
import json
import math
import shutil
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


RUN_LABEL = "phaseB_filtered_ngram_hard_pair_report_v1"
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
OUTPUT_DIR = ANALYSIS_ROOT / RUN_LABEL
ASSET_ROOT = ANALYSIS_ROOT / "phaseB_filtered_ngram_index_v1/20260514T044954Z__phaseB_filtered_ngram_index_v1"
HARD_PAIR_DIR = ANALYSIS_ROOT / "phaseB_span_hamming_hard_pair_road_test_v1"
MANUAL_DIR = ANALYSIS_ROOT / "phaseB_span_hamming_candidate_manual_inspection_v1"
MULTISCORE_DIR = ANALYSIS_ROOT / "phaseB_span_hamming_multiscore_hard_pair_report_v1"
PROXY_DIR = ANALYSIS_ROOT / "phaseB_order_phrase_ngram_coherence_hard_pair_report_v1"

ASSET_MODE = "sample"
SAMPLE_LINE_LIMIT_PER_ORDER = 25000
CORE_ORDERS = (2, 3, 4)
DIAGNOSTIC_ORDERS = (5,)
ALL_ORDERS = CORE_ORDERS + DIAGNOSTIC_ORDERS
DICTIONARY_CUTS = ("normal", "strict")
ASSET_DIRECTIONS = ("fwd", "rev")
SCORING_DIRECTION = "fwd"
CHUNK_SIZE = 500
TOP_K_LOG_HITS = 5
TOP_HITS_PER_CHUNK_ORDER = 5
TOP_PAIR_ROWS = 80
CURRENT_MARGIN_GATE = 0.01
CONSERVATIVE_MARGIN = 0.25
MARGIN_THRESHOLDS = (0.0, 0.01, 0.025, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.75, 1.00, 1.50, 2.00)


@dataclass
class PhraseMeta:
    sequence: tuple[int, ...]
    dictionary_cut: str
    direction: str
    ngram_order: int
    encoded_token_length: int
    phrase_count: int = 0
    sum_count: float = 0.0
    max_count: float = 0.0
    max_log_count: float = 0.0
    top_latin_ngram: str = ""
    top_latin_count: float = 0.0
    rune_joined: str = ""
    latin_examples: list[str] = field(default_factory=list)
    all_rune_joined_examples: set[str] = field(default_factory=set)


@dataclass
class Hit:
    start: int
    end: int
    meta: PhraseMeta


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def ensure_under_repo(path: Path) -> None:
    resolved = path.resolve()
    if not resolved.is_relative_to(REPO_ROOT):
        raise ValueError(f"path escapes repo root: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        out = float(value)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def mean(values: Iterable[float]) -> float:
    seq = list(values)
    return statistics.fmean(seq) if seq else 0.0


def median(values: Iterable[float]) -> float:
    seq = sorted(values)
    return statistics.median(seq) if seq else 0.0


def percentile(values: Iterable[float], q: float) -> float:
    seq = sorted(values)
    if not seq:
        return 0.0
    if len(seq) == 1:
        return seq[0]
    pos = (len(seq) - 1) * q / 100.0
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return seq[lo]
    return seq[lo] + (seq[hi] - seq[lo]) * (pos - lo)


def pearson(xs: Iterable[float], ys: Iterable[float]) -> float:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 2:
        return 0.0
    xvals = [p[0] for p in pairs]
    yvals = [p[1] for p in pairs]
    xm = statistics.fmean(xvals)
    ym = statistics.fmean(yvals)
    xden = math.sqrt(sum((x - xm) ** 2 for x in xvals))
    yden = math.sqrt(sum((y - ym) ** 2 for y in yvals))
    if xden <= 1e-12 or yden <= 1e-12:
        return 0.0
    return sum((x - xm) * (y - ym) for x, y in pairs) / (xden * yden)


def wilson_ci(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    z = 1.959963984540054
    p = successes / total
    denom = 1.0 + z * z / total
    centre = p + z * z / (2.0 * total)
    spread = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
    return (centre - spread) / denom, (centre + spread) / denom


def parse_json_list(value: str, default: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: list[str]) -> None:
    ensure_under_repo(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_csv_gz(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: list[str]) -> None:
    ensure_under_repo(path)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_csv_gz_rows(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ngram_asset_path(dictionary_cut: str, direction: str, order: int) -> Path:
    return ASSET_ROOT / f"{dictionary_cut}_{direction}" / f"ngram{order}.csv.gz"


def parse_token_sequence(row: Mapping[str, str]) -> tuple[int, ...]:
    raw = parse_json_list(row.get("rune_token_ids", ""), [])
    if not isinstance(raw, list):
        return ()
    out: list[int] = []
    for value in raw:
        token = as_int(value, -1)
        if token < 0 or token > 28:
            return ()
        out.append(token)
    return tuple(out)


def update_phrase_meta(meta: PhraseMeta, row: Mapping[str, str], sequence: tuple[int, ...]) -> None:
    count = as_float(row.get("count"))
    log_count = as_float(row.get("log_count"))
    phrase_count = as_int(row.get("phrase_count"), 1)
    top_latin_count = as_float(row.get("top_latin_count"))
    meta.phrase_count += max(1, phrase_count)
    meta.sum_count += count
    if count > meta.max_count:
        meta.max_count = count
        meta.top_latin_ngram = row.get("top_latin_ngram", "")
        meta.top_latin_count = top_latin_count
        meta.rune_joined = row.get("rune_joined", "")
    meta.max_log_count = max(meta.max_log_count, log_count)
    if row.get("rune_joined"):
        meta.all_rune_joined_examples.add(row["rune_joined"])
    examples = parse_json_list(row.get("latin_examples", ""), [])
    if isinstance(examples, list):
        for example in examples:
            text = str(example)
            if text and text not in meta.latin_examples and len(meta.latin_examples) < 5:
                meta.latin_examples.append(text)
    if not meta.rune_joined:
        meta.rune_joined = row.get("rune_joined", "")
    if not meta.top_latin_ngram:
        meta.top_latin_ngram = row.get("top_latin_ngram", "")
    if meta.encoded_token_length == 0:
        meta.encoded_token_length = len(sequence)


def load_asset_table(dictionary_cut: str, direction: str, order: int) -> tuple[dict[tuple[int, ...], PhraseMeta], dict[str, Any]]:
    path = ngram_asset_path(dictionary_cut, direction, order)
    collapsed: dict[tuple[int, ...], PhraseMeta] = {}
    raw_rows = 0
    invalid_token_rows = 0
    empty_sequence_rows = 0
    missing_required_fields: set[str] = set()
    phrase_keys: set[str] = set()
    token_lengths: list[int] = []
    counts: list[float] = []
    log_counts: list[float] = []
    if not path.exists():
        return {}, {"path": rel(path), "exists": False}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        for required in ("rune_token_ids", "count", "log_count", "phrase_count", "top_latin_ngram"):
            if required not in fieldnames:
                missing_required_fields.add(required)
        for row in reader:
            raw_rows += 1
            sequence = parse_token_sequence(row)
            if not sequence:
                if row.get("rune_token_ids") in ("", "[]"):
                    empty_sequence_rows += 1
                else:
                    invalid_token_rows += 1
                continue
            phrase_keys.add(row.get("top_latin_ngram", ""))
            token_lengths.append(len(sequence))
            counts.append(as_float(row.get("count")))
            log_counts.append(as_float(row.get("log_count")))
            meta = collapsed.get(sequence)
            if meta is None:
                meta = PhraseMeta(
                    sequence=sequence,
                    dictionary_cut=dictionary_cut,
                    direction=direction,
                    ngram_order=order,
                    encoded_token_length=len(sequence),
                )
                collapsed[sequence] = meta
            update_phrase_meta(meta, row, sequence)
    duplicate_rows = raw_rows - len(collapsed) - invalid_token_rows - empty_sequence_rows
    summary = {
        "path": rel(path),
        "exists": True,
        "bytes": path.stat().st_size,
        "dictionary_cut": dictionary_cut,
        "direction": direction,
        "ngram_order": order,
        "raw_rows": raw_rows,
        "unique_phrase_count": len(phrase_keys),
        "unique_encoded_token_sequence_count": len(collapsed),
        "duplicate_encoded_token_rows": max(0, duplicate_rows),
        "invalid_token_rows": invalid_token_rows,
        "empty_sequence_rows": empty_sequence_rows,
        "missing_required_fields": sorted(missing_required_fields),
        "token_length_min": min(token_lengths) if token_lengths else 0,
        "token_length_median": median(token_lengths),
        "token_length_max": max(token_lengths) if token_lengths else 0,
        "count_q05": percentile(counts, 5),
        "count_median": median(counts),
        "count_q95": percentile(counts, 95),
        "log_count_q05": percentile(log_counts, 5),
        "log_count_median": median(log_counts),
        "log_count_q95": percentile(log_counts, 95),
    }
    return collapsed, summary


def validate_and_load_assets() -> tuple[dict[tuple[str, str, int], dict[tuple[int, ...], PhraseMeta]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    assets: dict[tuple[str, str, int], dict[tuple[int, ...], PhraseMeta]] = {}
    summaries: list[dict[str, Any]] = []
    duplicate_rows: list[dict[str, Any]] = []
    top_examples: list[dict[str, Any]] = []
    for dictionary_cut in DICTIONARY_CUTS:
        for direction in ASSET_DIRECTIONS:
            for order in ALL_ORDERS:
                collapsed, summary = load_asset_table(dictionary_cut, direction, order)
                assets[(dictionary_cut, direction, order)] = collapsed
                summaries.append(summary)
                dupes = sorted(
                    [meta for meta in collapsed.values() if meta.phrase_count > 1],
                    key=lambda meta: (meta.phrase_count, meta.sum_count),
                    reverse=True,
                )[:50]
                for meta in dupes:
                    duplicate_rows.append(
                        {
                            "dictionary_cut": dictionary_cut,
                            "direction": direction,
                            "ngram_order": order,
                            "encoded_token_length": meta.encoded_token_length,
                            "phrase_count": meta.phrase_count,
                            "sum_count": meta.sum_count,
                            "max_count": meta.max_count,
                            "max_log_count": meta.max_log_count,
                            "top_latin_ngram": meta.top_latin_ngram,
                            "latin_examples": json.dumps(meta.latin_examples, ensure_ascii=False),
                        }
                    )
                for meta in sorted(collapsed.values(), key=lambda item: item.max_count, reverse=True)[:20]:
                    top_examples.append(
                        {
                            "dictionary_cut": dictionary_cut,
                            "direction": direction,
                            "ngram_order": order,
                            "encoded_token_length": meta.encoded_token_length,
                            "sum_count": meta.sum_count,
                            "max_count": meta.max_count,
                            "max_log_count": meta.max_log_count,
                            "phrase_count": meta.phrase_count,
                            "top_latin_ngram": meta.top_latin_ngram,
                            "rune_joined": meta.rune_joined,
                            "latin_examples": json.dumps(meta.latin_examples, ensure_ascii=False),
                        }
                    )
    return assets, summaries, duplicate_rows, top_examples


def build_scan_index(
    assets: Mapping[tuple[str, str, int], Mapping[tuple[int, ...], PhraseMeta]]
) -> dict[tuple[str, int], dict[int, dict[int, dict[tuple[int, ...], PhraseMeta]]]]:
    index: dict[tuple[str, int], dict[int, dict[int, dict[tuple[int, ...], PhraseMeta]]]] = {}
    for dictionary_cut in DICTIONARY_CUTS:
        for order in ALL_ORDERS:
            by_first: dict[int, dict[int, dict[tuple[int, ...], PhraseMeta]]] = defaultdict(lambda: defaultdict(dict))
            for sequence, meta in assets.get((dictionary_cut, SCORING_DIRECTION, order), {}).items():
                if not sequence:
                    continue
                by_first[sequence[0]][len(sequence)][sequence] = meta
            index[(dictionary_cut, order)] = by_first
    return index


def scan_chunk(tokens: list[int], index: Mapping[tuple[str, int], Mapping[int, Mapping[int, Mapping[tuple[int, ...], PhraseMeta]]]]) -> dict[tuple[str, int], list[Hit]]:
    out: dict[tuple[str, int], list[Hit]] = {(cut, order): [] for cut in DICTIONARY_CUTS for order in ALL_ORDERS}
    token_count = len(tokens)
    for dictionary_cut in DICTIONARY_CUTS:
        for order in ALL_ORDERS:
            by_first = index[(dictionary_cut, order)]
            hits = out[(dictionary_cut, order)]
            for start, token in enumerate(tokens):
                by_length = by_first.get(token)
                if not by_length:
                    continue
                for length, by_sequence in by_length.items():
                    end = start + length
                    if end > token_count:
                        continue
                    sequence = tuple(tokens[start:end])
                    meta = by_sequence.get(sequence)
                    if meta is not None:
                        hits.append(Hit(start=start, end=end, meta=meta))
    return out


def nonoverlap_hits(hits: list[Hit]) -> list[Hit]:
    selected: list[Hit] = []
    occupied: set[int] = set()
    for hit in sorted(hits, key=lambda item: (item.meta.max_log_count, item.meta.encoded_token_length), reverse=True):
        span = set(range(hit.start, hit.end))
        if occupied & span:
            continue
        selected.append(hit)
        occupied.update(span)
    selected.sort(key=lambda item: item.start)
    return selected


def chunk_feature_row(candidate_id: str, chunk_id: int, tokens: list[int], dictionary_cut: str, order: int, hits: list[Hit]) -> dict[str, Any]:
    token_count = len(tokens)
    unique_sequences = {hit.meta.sequence for hit in hits}
    log_weights = sorted((hit.meta.max_log_count for hit in hits), reverse=True)
    hit_lengths = [hit.meta.encoded_token_length for hit in hits]
    selected = nonoverlap_hits(hits)
    nonoverlap_coverage = sum(hit.meta.encoded_token_length for hit in selected)
    scale = token_count / CHUNK_SIZE if token_count else 1.0
    return {
        "candidate_id": candidate_id,
        "chunk_id": chunk_id,
        "direction": SCORING_DIRECTION,
        "dictionary_cut": dictionary_cut,
        "ngram_order": order,
        "token_count": token_count,
        "hit_count": len(hits),
        "unique_hit_count": len(unique_sequences),
        "binary_presence": 1.0 if hits else 0.0,
        "unweighted_hit_density": len(hits) / scale,
        "log_count_weighted_hit_sum": sum(log_weights),
        "log_count_weighted_hit_density": sum(log_weights) / scale,
        "top_k_log_count_sum": sum(log_weights[:TOP_K_LOG_HITS]),
        "max_log_count": max(log_weights) if log_weights else 0.0,
        "mean_hit_token_length": mean(hit_lengths),
        "max_hit_token_length": max(hit_lengths) if hit_lengths else 0,
        "nonoverlap_hit_count": len(selected),
        "nonoverlap_log_count_weighted_sum": sum(hit.meta.max_log_count for hit in selected),
        "nonoverlap_token_coverage": nonoverlap_coverage,
        "nonoverlap_token_coverage_fraction": nonoverlap_coverage / token_count if token_count else 0.0,
    }


def top_hit_records(candidate_id: str, chunk_id: int, dictionary_cut: str, order: int, hits: list[Hit]) -> list[dict[str, Any]]:
    best: dict[tuple[int, ...], Hit] = {}
    for hit in hits:
        current = best.get(hit.meta.sequence)
        if current is None or hit.meta.max_log_count > current.meta.max_log_count:
            best[hit.meta.sequence] = hit
    selected = sorted(best.values(), key=lambda item: (item.meta.max_log_count, item.meta.encoded_token_length), reverse=True)[:TOP_HITS_PER_CHUNK_ORDER]
    out: list[dict[str, Any]] = []
    for hit in selected:
        meta = hit.meta
        out.append(
            {
                "candidate_id": candidate_id,
                "chunk_id": chunk_id,
                "direction": SCORING_DIRECTION,
                "dictionary_cut": dictionary_cut,
                "ngram_order": order,
                "hit_start": hit.start,
                "hit_end": hit.end,
                "encoded_token_length": meta.encoded_token_length,
                "rune_joined": meta.rune_joined,
                "top_latin_ngram": meta.top_latin_ngram,
                "latin_examples": meta.latin_examples,
                "count": meta.max_count,
                "log_count": meta.max_log_count,
                "phrase_count": meta.phrase_count,
            }
        )
    return out


def load_candidate_tokens() -> dict[str, dict[str, Any]]:
    path = MANUAL_DIR / "candidate_full_texts.jsonl.gz"
    out: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            tokens = [as_int(value, -1) for value in str(row.get("token_sequence_text", "")).split()]
            tokens = [token for token in tokens if 0 <= token <= 28]
            chunks = [tokens[idx : idx + CHUNK_SIZE] for idx in range(0, len(tokens), CHUNK_SIZE)]
            out[row["candidate_id"]] = {
                "candidate_id": row["candidate_id"],
                "current_score": as_float(row.get("current_score")),
                "label": row.get("label", ""),
                "panelA_score": as_float(row.get("panelA_score")),
                "truth_match_ratio": as_float(row.get("truth_match_ratio")),
                "token_count": len(tokens),
                "token_hash": row.get("token_hash", ""),
                "chunks": chunks,
            }
    return out


def scan_candidates(
    candidates: Mapping[str, Mapping[str, Any]],
    index: Mapping[tuple[str, int], Mapping[int, Mapping[int, Mapping[tuple[int, ...], PhraseMeta]]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    chunk_rows: list[dict[str, Any]] = []
    top_records: list[dict[str, Any]] = []
    total_chunks = sum(len(row["chunks"]) for row in candidates.values())
    completed = 0
    start_time = time.perf_counter()
    for candidate_id, row in sorted(candidates.items()):
        for chunk_id, tokens in enumerate(row["chunks"]):
            hits_by_key = scan_chunk(tokens, index)
            for dictionary_cut in DICTIONARY_CUTS:
                for order in ALL_ORDERS:
                    hits = hits_by_key[(dictionary_cut, order)]
                    chunk_rows.append(chunk_feature_row(candidate_id, chunk_id, tokens, dictionary_cut, order, hits))
                    top_records.extend(top_hit_records(candidate_id, chunk_id, dictionary_cut, order, hits))
            completed += 1
            if completed == 1 or completed % 100 == 0 or completed == total_chunks:
                elapsed = time.perf_counter() - start_time
                rate = completed / elapsed if elapsed > 0 else 0.0
                eta = (total_chunks - completed) / rate if rate > 0 else 0.0
                print(
                    f"[{RUN_LABEL}] scanned_chunks={completed}/{total_chunks} "
                    f"elapsed_s={elapsed:.1f} eta_s={eta:.1f}"
                )
    return chunk_rows, top_records


def zscore_by_key(rows: list[dict[str, Any]], key_field: str, value_field: str, out_field: str) -> None:
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row[key_field]].append(row)
    for group_rows in groups.values():
        values = [as_float(row.get(value_field)) for row in group_rows]
        mu = mean(values)
        sigma = statistics.stdev(values) if len(values) >= 2 else 0.0
        for row in group_rows:
            row[out_field] = 0.0 if sigma <= 1e-12 else (as_float(row.get(value_field)) - mu) / sigma


def add_chunk_scores(chunk_rows: list[dict[str, Any]]) -> None:
    keyed_field_rows: list[dict[str, Any]] = []
    for row in chunk_rows:
        key = f"{row['dictionary_cut']}_{row['ngram_order']}"
        keyed_field_rows.append({**row, "_z_key": key})
    zscore_by_key(keyed_field_rows, "_z_key", "log_count_weighted_hit_density", "log_density_z")
    zscore_by_key(keyed_field_rows, "_z_key", "nonoverlap_token_coverage_fraction", "coverage_z")
    for original, zrow in zip(chunk_rows, keyed_field_rows):
        original["log_density_z"] = zrow["log_density_z"]
        original["coverage_z"] = zrow["coverage_z"]
        original["capped_log_density_z"] = max(-3.0, min(3.0, as_float(zrow["log_density_z"])))
        original["positive_log_density_z"] = max(0.0, as_float(zrow["log_density_z"]))


def load_len7_hd2_exact_support() -> dict[str, float]:
    path = HARD_PAIR_DIR / "candidate_feature_rows.csv.gz"
    sums: dict[str, float] = defaultdict(float)
    counts: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("dictionary_cut") != "phaseA14_normal_selected":
                continue
            if row.get("span_length") != "7" or row.get("hd") != "2":
                continue
            if row.get("feature_name") != "exact_count_norm":
                continue
            if row.get("comparison_null_class") != "local_null":
                continue
            key = (row["candidate_id"], row["candidate_chunk_id"])
            if key in seen:
                continue
            seen.add(key)
            sums[row["candidate_id"]] += as_float(row.get("signed_effect_vs_local_null"))
            counts[row["candidate_id"]] += 1
    return {candidate_id: total / max(1, counts[candidate_id]) for candidate_id, total in sums.items()}


def load_multiscore_candidates() -> dict[str, dict[str, str]]:
    return {row["candidate_id"]: row for row in read_csv_rows(MULTISCORE_DIR / "candidate_multiscore_summary.csv")}


def zscore_mapping(values: Mapping[str, float]) -> dict[str, float]:
    seq = list(values.values())
    mu = mean(seq)
    sigma = statistics.stdev(seq) if len(seq) >= 2 else 0.0
    return {key: 0.0 if sigma <= 1e-12 else (value - mu) / sigma for key, value in values.items()}


def aggregate_candidate_scores(
    candidates: Mapping[str, Mapping[str, Any]],
    chunk_rows: list[dict[str, Any]],
    len7_support: Mapping[str, float],
    multiscore: Mapping[str, Mapping[str, str]],
) -> list[dict[str, Any]]:
    by_candidate_chunk: dict[tuple[str, int], dict[tuple[str, int], dict[str, Any]]] = defaultdict(dict)
    for row in chunk_rows:
        by_candidate_chunk[(row["candidate_id"], as_int(row["chunk_id"]))][(row["dictionary_cut"], as_int(row["ngram_order"]))] = row

    candidate_rows: list[dict[str, Any]] = []
    raw_score_maps: dict[str, dict[str, float]] = defaultdict(dict)
    for candidate_id, candidate in sorted(candidates.items()):
        chunk_ids = sorted(chunk_id for cid, chunk_id in by_candidate_chunk if cid == candidate_id)
        per_order_scores: dict[str, list[float]] = defaultdict(list)
        per_order_coverage: dict[str, list[float]] = defaultdict(list)
        for chunk_id in chunk_ids:
            chunk_map = by_candidate_chunk[(candidate_id, chunk_id)]
            for dictionary_cut in DICTIONARY_CUTS:
                for order in ALL_ORDERS:
                    feature = chunk_map.get((dictionary_cut, order), {})
                    per_order_scores[f"{dictionary_cut}_{order}"].append(as_float(feature.get("capped_log_density_z")))
                    per_order_coverage[f"{dictionary_cut}_{order}"].append(as_float(feature.get("coverage_z")))

        normal_2 = mean(per_order_scores["normal_2"])
        normal_3 = mean(per_order_scores["normal_3"])
        normal_4 = mean(per_order_scores["normal_4"])
        normal_5 = mean(per_order_scores["normal_5"])
        strict_2 = mean(per_order_scores["strict_2"])
        strict_3 = mean(per_order_scores["strict_3"])
        strict_4 = mean(per_order_scores["strict_4"])
        strict_5 = mean(per_order_scores["strict_5"])
        n4 = mean([normal_2, normal_3, normal_4])
        n5 = mean([strict_2, strict_3, strict_4])
        n7 = mean([max(0.0, normal_3), 1.25 * max(0.0, normal_4), 1.50 * max(0.0, normal_5)])
        n8 = mean(per_order_coverage["normal_2"] + per_order_coverage["normal_3"] + per_order_coverage["normal_4"])
        n9 = mean([normal_5, 0.35 * strict_5])
        row = {
            "candidate_id": candidate_id,
            "label": candidate.get("label", ""),
            "token_count": candidate.get("token_count", 0),
            "chunk_count": len(chunk_ids),
            "current_score": candidate.get("current_score", 0.0),
            "truth_match_ratio": candidate.get("truth_match_ratio", 0.0),
            "panelA": as_float(multiscore.get(candidate_id, {}).get("panelA")),
            "S5_local_null_positive_selected": as_float(multiscore.get(candidate_id, {}).get("S5_local_null_positive_selected")),
            "len7_hd2_exact_support": len7_support.get(candidate_id, 0.0),
            "N1_normal_2gram_mean": normal_2,
            "N2_normal_3gram_mean": normal_3,
            "N3_normal_4gram_mean": normal_4,
            "N4_normal_2_4_combined_core": n4,
            "N5_strict_2_4_combined_core": n5,
            "N6_normal_plus_strict_support": n4 + 0.35 * n5,
            "N7_longest_highest_order_phrase_support": n7,
            "N8_nonoverlap_coverage_score": n8,
            "N9_5gram_diagnostic": n9,
        }
        candidate_rows.append(row)
        for score_name in (
            "current_score",
            "panelA",
            "S5_local_null_positive_selected",
            "len7_hd2_exact_support",
            "N1_normal_2gram_mean",
            "N2_normal_3gram_mean",
            "N3_normal_4gram_mean",
            "N4_normal_2_4_combined_core",
            "N5_strict_2_4_combined_core",
            "N6_normal_plus_strict_support",
            "N7_longest_highest_order_phrase_support",
            "N8_nonoverlap_coverage_score",
            "N9_5gram_diagnostic",
        ):
            raw_score_maps[score_name][candidate_id] = as_float(row[score_name])

    z_len7 = zscore_mapping(raw_score_maps["len7_hd2_exact_support"])
    z_s5 = zscore_mapping(raw_score_maps["S5_local_null_positive_selected"])
    z_panela = zscore_mapping(raw_score_maps["panelA"])
    for row in candidate_rows:
        cid = row["candidate_id"]
        n4 = as_float(row["N4_normal_2_4_combined_core"])
        n6 = as_float(row["N6_normal_plus_strict_support"])
        row["N10_span_len7_support_plus_ngram_core"] = z_len7.get(cid, 0.0) + 0.5 * n4
        row["N11_S5_span_support_plus_ngram_core"] = z_s5.get(cid, 0.0) + 0.5 * n4
        row["N12_current_margin_support_policy_score"] = n4
        row["N13_conservative_support_policy_score"] = n6 + 0.25 * z_panela.get(cid, 0.0)
    return candidate_rows


def candidate_score_maps(candidate_rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    fields = [
        "current_score",
        "panelA",
        "S5_local_null_positive_selected",
        "len7_hd2_exact_support",
        "N1_normal_2gram_mean",
        "N2_normal_3gram_mean",
        "N3_normal_4gram_mean",
        "N4_normal_2_4_combined_core",
        "N5_strict_2_4_combined_core",
        "N6_normal_plus_strict_support",
        "N7_longest_highest_order_phrase_support",
        "N8_nonoverlap_coverage_score",
        "N9_5gram_diagnostic",
        "N10_span_len7_support_plus_ngram_core",
        "N11_S5_span_support_plus_ngram_core",
        "N12_current_margin_support_policy_score",
        "N13_conservative_support_policy_score",
    ]
    return {field: {row["candidate_id"]: as_float(row.get(field)) for row in candidate_rows} for field in fields}


def load_proxy_pair_gaps() -> dict[str, dict[str, dict[str, str]]]:
    path = PROXY_DIR / "pairwise_score_gaps.csv.gz"
    out: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                out[row["score_family"]][row["pair_id"]] = row
    feature_path = PROXY_DIR / "pairwise_coherence_feature_rows.csv.gz"
    if not feature_path.exists():
        return out
    with gzip.open(feature_path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            pair_id = row["pair_id"]
            out["coherence_proxy_v1"][pair_id] = {"score_gap": row.get("coherence_composite_gap", "0")}
            out["proxy_C1_char_ngram_coherence"][pair_id] = {"score_gap": row.get("C1_char_ngram_coherence_gap", "0")}
            out["proxy_C6_S5_plus_coherence"][pair_id] = {"score_gap": row.get("C6_S5_plus_coherence_gap", "0")}
    return out


def load_multiscore_pair_gaps() -> dict[str, dict[str, dict[str, str]]]:
    path = MULTISCORE_DIR / "pairwise_score_gaps.csv.gz"
    out: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out[row["score_family"]][row["pair_id"]] = row
    return out


def build_pair_rows(
    pairwise_rows: list[dict[str, str]],
    score_maps: Mapping[str, Mapping[str, float]],
    span_gaps: Mapping[str, Mapping[str, Mapping[str, str]]],
    proxy_gaps: Mapping[str, Mapping[str, Mapping[str, str]]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in pairwise_rows:
        pair_id = row["pair_id"]
        truth_better = row.get("known_better_candidate") or row["candidate_a_id"]
        other = row["candidate_b_id"] if truth_better == row["candidate_a_id"] else row["candidate_a_id"]
        current_correct = str(row.get("current_scorer_correct", "")).lower() == "true"
        base: dict[str, Any] = {
            "pair_id": pair_id,
            "truth_better_candidate_id": truth_better,
            "truth_worse_candidate_id": other,
            "candidate_a_id": row["candidate_a_id"],
            "candidate_b_id": row["candidate_b_id"],
            "current_score_gap": as_float(row.get("current_score_margin")),
            "current_scorer_correct": current_correct,
            "candidate_label": "",
            "source_family": "",
        }
        for score_name, scores in score_maps.items():
            base[f"{score_name}_gap"] = scores.get(truth_better, 0.0) - scores.get(other, 0.0)
        for source, source_rows in span_gaps.items():
            base[f"{source}_gap"] = as_float(source_rows.get(pair_id, {}).get("score_gap"))
        for source, source_rows in proxy_gaps.items():
            source_row = source_rows.get(pair_id, {})
            base[f"{source}_gap"] = as_float(source_row.get("score_gap"))
            if "score_applies" in source_row:
                base[f"{source}_precomputed_applies"] = str(source_row.get("score_applies", "")).lower() == "true"
        base["panelA_gap"] = base.get("S0_panelA_baseline_gap", 0.0)
        base["S5_gap"] = base.get("S5_local_null_positive_selected_gap", 0.0)
        base["coherence_proxy_v1_gap"] = base.get("coherence_proxy_v1_gap", 0.0)
        base["C7_proxy_combined_gap"] = base.get("C7_len7_hd2_exact_support_plus_coherence_gap", 0.0)
        out.append(base)
    return out


def evaluate_pairs(
    pair_rows: list[dict[str, Any]],
    score_name: str,
    *,
    threshold: float = 0.0,
    current_margin_gate: float | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    gap_field = f"{score_name}_gap"
    gaps: list[float] = []
    preference_count = rescues = breaks = applied = 0
    current_correct = current_wrong = correct_pref = wrong_pref = 0
    details: list[dict[str, Any]] = []
    for row in pair_rows:
        gap = as_float(row.get(gap_field))
        gaps.append(gap)
        is_current_correct = bool(row["current_scorer_correct"])
        current_correct += 1 if is_current_correct else 0
        current_wrong += 0 if is_current_correct else 1
        precomputed_applies_key = f"{score_name}_precomputed_applies"
        if precomputed_applies_key in row:
            applies = bool(row[precomputed_applies_key])
        else:
            applies = abs(gap) > threshold
        if current_margin_gate is not None and abs(as_float(row.get("current_score_gap"))) >= current_margin_gate:
            applies = False
        prefers_truth = gap > 0.0
        if applies:
            applied += 1
            preference_count += 1 if prefers_truth else 0
            correct_pref += 1 if prefers_truth and is_current_correct else 0
            wrong_pref += 1 if prefers_truth and not is_current_correct else 0
            rescues += 1 if prefers_truth and not is_current_correct else 0
            breaks += 1 if (not prefers_truth) and is_current_correct else 0
        details.append(
            {
                "score_family": score_name,
                "pair_id": row["pair_id"],
                "truth_better_candidate_id": row["truth_better_candidate_id"],
                "truth_worse_candidate_id": row["truth_worse_candidate_id"],
                "score_gap": gap,
                "score_applies": "true" if applies else "false",
                "score_prefers_truth_better": "true" if applies and prefers_truth else "false",
                "current_scorer_correct": "true" if is_current_correct else "false",
                "current_score_gap": row["current_score_gap"],
                "panelA_gap": row.get("panelA_gap", 0.0),
                "S5_gap": row.get("S5_gap", 0.0),
                "len7_hd2_exact_support_gap": row.get("len7_hd2_exact_support_gap", 0.0),
                "coherence_proxy_v1_gap": row.get("coherence_proxy_v1_gap", 0.0),
                "C7_proxy_combined_gap": row.get("C7_proxy_combined_gap", 0.0),
                "rescues_current_misrank": "true" if applies and prefers_truth and not is_current_correct else "false",
                "breaks_current_correct": "true" if applies and (not prefers_truth) and is_current_correct else "false",
            }
        )
    total = len(pair_rows)
    ci_low, ci_high = wilson_ci(preference_count, total)
    return (
        {
            "score_family": score_name,
            "n_pairs": total,
            "truth_better_preference_count": preference_count,
            "truth_better_preference_rate": preference_count / total if total else 0.0,
            "truth_preference_95ci_low": ci_low,
            "truth_preference_95ci_high": ci_high,
            "rescues": rescues,
            "breaks": breaks,
            "net_rescues": rescues - breaks,
            "mean_gap": mean(gaps),
            "median_gap": median(gaps),
            "gap_q05": percentile(gaps, 5),
            "gap_q25": percentile(gaps, 25),
            "gap_q75": percentile(gaps, 75),
            "gap_q95": percentile(gaps, 95),
            "applied_count": applied,
            "current_scorer_correct_count": current_correct,
            "current_scorer_misrank_count": current_wrong,
            "truth_preference_when_current_correct": correct_pref / current_correct if current_correct else 0.0,
            "truth_preference_when_current_wrong": wrong_pref / current_wrong if current_wrong else 0.0,
        },
        details,
    )


def margin_sweep(pair_rows: list[dict[str, Any]], score_name: str, current_margin_gate: float | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    misranks = sum(1 for row in pair_rows if not row["current_scorer_correct"])
    for threshold in MARGIN_THRESHOLDS:
        summary, _ = evaluate_pairs(pair_rows, score_name, threshold=threshold, current_margin_gate=current_margin_gate)
        applied = as_int(summary["applied_count"])
        rescues = as_int(summary["rescues"])
        out.append(
            {
                "score_family": score_name,
                "threshold": threshold,
                "applied_count": applied,
                "rescues": rescues,
                "breaks": summary["breaks"],
                "net": summary["net_rescues"],
                "precision_of_applied_overrides": rescues / applied if applied else 0.0,
                "misrank_recall": rescues / misranks if misranks else 0.0,
            }
        )
    return out


def build_correlation_summary(pair_rows: list[dict[str, Any]], score_families: list[str]) -> list[dict[str, Any]]:
    references = {
        "current_score_margin": [as_float(row.get("current_score_gap")) for row in pair_rows],
        "panelA_margin": [as_float(row.get("panelA_gap")) for row in pair_rows],
        "S5_margin": [as_float(row.get("S5_gap")) for row in pair_rows],
        "len7_hd2_exact_support_margin": [as_float(row.get("len7_hd2_exact_support_gap")) for row in pair_rows],
        "coherence_proxy_v1_margin": [as_float(row.get("coherence_proxy_v1_gap")) for row in pair_rows],
        "C7_proxy_combined_margin": [as_float(row.get("C7_proxy_combined_gap")) for row in pair_rows],
    }
    out: list[dict[str, Any]] = []
    for score_name in score_families:
        gaps = [as_float(row.get(f"{score_name}_gap")) for row in pair_rows]
        row = {"score_family": score_name}
        for reference_name, reference_values in references.items():
            row[f"correlation_with_{reference_name}"] = pearson(gaps, reference_values)
        out.append(row)
    return out


def feature_rows_long(chunk_rows: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    feature_names = [
        "hit_count",
        "unique_hit_count",
        "binary_presence",
        "unweighted_hit_density",
        "log_count_weighted_hit_sum",
        "log_count_weighted_hit_density",
        "top_k_log_count_sum",
        "max_log_count",
        "mean_hit_token_length",
        "max_hit_token_length",
        "nonoverlap_hit_count",
        "nonoverlap_log_count_weighted_sum",
        "nonoverlap_token_coverage",
        "nonoverlap_token_coverage_fraction",
        "log_density_z",
        "coverage_z",
    ]
    weighting_by_feature = {
        "hit_count": "unweighted",
        "unique_hit_count": "unweighted",
        "binary_presence": "binary_presence",
        "unweighted_hit_density": "unweighted",
        "log_count_weighted_hit_sum": "log_count_weighted",
        "log_count_weighted_hit_density": "log_count_weighted",
        "top_k_log_count_sum": "log_count_weighted",
        "max_log_count": "log_count_weighted",
        "mean_hit_token_length": "unweighted",
        "max_hit_token_length": "unweighted",
        "nonoverlap_hit_count": "unweighted",
        "nonoverlap_log_count_weighted_sum": "log_count_weighted",
        "nonoverlap_token_coverage": "unweighted",
        "nonoverlap_token_coverage_fraction": "unweighted",
        "log_density_z": "log_count_weighted",
        "coverage_z": "unweighted",
    }
    for row in chunk_rows:
        for feature_name in feature_names:
            yield {
                "candidate_id": row["candidate_id"],
                "chunk_id": row["chunk_id"],
                "direction": row["direction"],
                "dictionary_cut": row["dictionary_cut"],
                "ngram_order": row["ngram_order"],
                "weighting_mode": weighting_by_feature[feature_name],
                "feature_name": feature_name,
                "feature_value": row.get(feature_name, 0.0),
                "hit_count": row.get("hit_count", 0),
                "unique_hit_count": row.get("unique_hit_count", 0),
                "token_count": row.get("token_count", 0),
            }


def summarize_group(rows: list[dict[str, Any]], group_fields: list[str], value_fields: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in group_fields)].append(row)
    out: list[dict[str, Any]] = []
    for key, group_rows in sorted(groups.items()):
        summary = {field: value for field, value in zip(group_fields, key)}
        summary["row_count"] = len(group_rows)
        for field_name in value_fields:
            values = [as_float(row.get(field_name)) for row in group_rows]
            summary[f"{field_name}_mean"] = mean(values)
            summary[f"{field_name}_median"] = median(values)
            summary[f"{field_name}_q95"] = percentile(values, 95)
        out.append(summary)
    return out


def top_rows(details: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    rows = [row for row in details if row.get(field) == "true"]
    rows.sort(key=lambda row: abs(as_float(row.get("score_gap"))), reverse=True)
    return rows[:TOP_PAIR_ROWS]


def false_negative_rows(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in details
        if row.get("current_scorer_correct") == "false" and row.get("rescues_current_misrank") != "true"
    ]
    rows.sort(key=lambda row: as_float(row.get("score_gap")))
    return rows[:TOP_PAIR_ROWS]


def write_top_hits(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    ensure_under_repo(path)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_readout(score_summary: list[dict[str, Any]], correlation_rows: list[dict[str, Any]], elapsed_s: float) -> None:
    by_name = {row["score_family"]: row for row in score_summary}
    ranked = sorted(score_summary, key=lambda row: (as_float(row["net_rescues"]), as_float(row["truth_better_preference_rate"])), reverse=True)
    best = ranked[0] if ranked else {}
    proxy = by_name.get("coherence_proxy_v1", {})
    n4 = by_name.get("N4_normal_2_4_combined_core", {})
    n6 = by_name.get("N6_normal_plus_strict_support", {})
    n10 = by_name.get("N10_span_len7_support_plus_ngram_core", {})
    n11 = by_name.get("N11_S5_span_support_plus_ngram_core", {})
    n13 = by_name.get("N13_conservative_support_policy", {})
    corr_by_name = {row["score_family"]: row for row in correlation_rows}
    n6_corr = corr_by_name.get("N6_normal_plus_strict_support", {})
    lines = [
        "# PhaseB Filtered N-Gram Hard-Pair Report v1",
        "",
        f"Created UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Elapsed seconds: {elapsed_s:.1f}",
        "",
        "## Scope",
        "",
        "- This report uses filtered sample n-gram assets. Results are pilot evidence, not final full-corpus n-gram calibration.",
        f"- Asset mode: `{ASSET_MODE}`.",
        f"- Sample line limit per order: `{SAMPLE_LINE_LIMIT_PER_ORDER}`.",
        "- FWD-only scoring; REV assets were validated but not used for the hard-pair score.",
        "- Core score uses 2-, 3-, and 4-grams. 5-grams are diagnostic only.",
        "- Candidate scoring uses two 500-token chunks per candidate and primary candidate scores are chunk means.",
        "- No production scorer weights, defaults, ranking policy, or span-Hamming calibration outputs were changed.",
        "",
        "## Main Answers",
        "",
        f"- Best family by net then truth preference: `{best.get('score_family', '')}` with truth preference {as_float(best.get('truth_better_preference_rate')):.3f}, rescues {best.get('rescues', '')}, breaks {best.get('breaks', '')}, net {best.get('net_rescues', '')}.",
        f"- Proxy coherence baseline: truth preference {as_float(proxy.get('truth_better_preference_rate')):.3f}, rescues {proxy.get('rescues', '')}, breaks {proxy.get('breaks', '')}, net {proxy.get('net_rescues', '')}.",
        f"- N4 normal 2-4 core: truth preference {as_float(n4.get('truth_better_preference_rate')):.3f}, rescues {n4.get('rescues', '')}, breaks {n4.get('breaks', '')}, net {n4.get('net_rescues', '')}.",
        f"- N6 normal plus strict support: truth preference {as_float(n6.get('truth_better_preference_rate')):.3f}, rescues {n6.get('rescues', '')}, breaks {n6.get('breaks', '')}, net {n6.get('net_rescues', '')}.",
        f"- N10 len7 span support plus n-gram core: truth preference {as_float(n10.get('truth_better_preference_rate')):.3f}, rescues {n10.get('rescues', '')}, breaks {n10.get('breaks', '')}, net {n10.get('net_rescues', '')}.",
        f"- N11 S5 span support plus n-gram core: truth preference {as_float(n11.get('truth_better_preference_rate')):.3f}, rescues {n11.get('rescues', '')}, breaks {n11.get('breaks', '')}, net {n11.get('net_rescues', '')}.",
        f"- N13 conservative policy: truth preference {as_float(n13.get('truth_better_preference_rate')):.3f}, rescues {n13.get('rescues', '')}, breaks {n13.get('breaks', '')}, net {n13.get('net_rescues', '')}, applied {n13.get('applied_count', '')}.",
        "",
        "## Correlation",
        "",
        f"- N6 correlation with current score margin: {as_float(n6_corr.get('correlation_with_current_score_margin')):.3f}.",
        f"- N6 correlation with Panel A margin: {as_float(n6_corr.get('correlation_with_panelA_margin')):.3f}.",
        f"- N6 correlation with S5 margin: {as_float(n6_corr.get('correlation_with_S5_margin')):.3f}.",
        f"- N6 correlation with proxy coherence margin: {as_float(n6_corr.get('correlation_with_coherence_proxy_v1_margin')):.3f}.",
        "",
        "## Interpretation Notes",
        "",
        "- Positive score gap means the score prefers the truth-better candidate.",
        "- Strict and normal n-gram surfaces are kept separate in feature outputs and score definitions.",
        "- Duplicate encoded phrase rows are collapsed for scanning so the same encoded token sequence is not double-counted by Latin phrase multiplicity.",
        "- If sample n-grams underperform the proxy, the likely next review question is whether sample coverage is too sparse or exact no-WLI phrase matching is too brittle.",
        "",
        "## Files",
        "",
        "- config.json",
        "- input_manifest.json",
        "- ngram_asset_manifest.json",
        "- ngram_asset_validation_summary.json",
        "- score_definition_manifest.json",
        "- candidate_ngram_feature_rows.csv.gz",
        "- candidate_ngram_chunk_summary.csv",
        "- candidate_ngram_candidate_summary.csv",
        "- candidate_ngram_top_hits.jsonl.gz",
        "- score_family_pairwise_summary.csv",
        "- score_family_margin_sweep.csv",
        "- pairwise_score_gaps.csv.gz",
        "- ngram_order_summary.csv",
        "- dictionary_cut_summary.csv",
        "- weighting_mode_summary.csv",
        "- correlation_summary.csv",
        "- proxy_vs_filtered_ngram_comparison.csv",
        "- top_ngram_rescues.csv",
        "- top_ngram_breaks.csv",
        "- top_ngram_false_positives.csv",
        "- top_ngram_false_negatives.csv",
    ]
    ensure_under_repo(OUTPUT_DIR / "readout.md")
    (OUTPUT_DIR / "readout.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_asset_validation_readout(validation_rows: list[dict[str, Any]], validation_summary: Mapping[str, Any]) -> None:
    total_rows = sum(as_int(row.get("raw_rows")) for row in validation_rows)
    total_unique = sum(as_int(row.get("unique_encoded_token_sequence_count")) for row in validation_rows)
    invalid_rows = sum(as_int(row.get("invalid_token_rows")) for row in validation_rows)
    empty_rows = sum(as_int(row.get("empty_sequence_rows")) for row in validation_rows)
    missing_fields = sorted({field for row in validation_rows for field in row.get("missing_required_fields", [])})
    lines = [
        "# PhaseB Filtered N-Gram Asset Validation v1",
        "",
        f"Created UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Scope",
        "",
        f"- Asset root: `{rel(ASSET_ROOT)}`.",
        f"- Asset mode: `{ASSET_MODE}`.",
        f"- Sample line limit per order: `{SAMPLE_LINE_LIMIT_PER_ORDER}`.",
        "- Validated strict/normal and FWD/REV tables for 2-, 3-, 4-, and 5-grams.",
        "- The hard-pair scorer uses FWD only, but REV presence was checked.",
        "",
        "## Summary",
        "",
        f"- Raw rows scanned: `{total_rows}`.",
        f"- Unique encoded token sequences after duplicate collapse: `{total_unique}`.",
        f"- Invalid token rows: `{invalid_rows}`.",
        f"- Empty token-sequence rows: `{empty_rows}`.",
        f"- Missing required fields: `{', '.join(missing_fields) if missing_fields else 'none'}`.",
        f"- Normal and strict content distinct by order: `{validation_summary.get('normal_and_strict_content_distinct_by_order')}`.",
        "",
        "## Contract Notes",
        "",
        "- Scanner input field: `rune_token_ids`.",
        "- `rune_key_hex` is not used for no-WLI candidate scanning because it contains word separators.",
        "- Duplicate encoded token sequences are collapsed for scoring while preserving phrase metadata.",
    ]
    ensure_under_repo(OUTPUT_DIR / "readout_asset_validation.md")
    (OUTPUT_DIR / "readout_asset_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    start = time.perf_counter()
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    required_paths = {
        "asset_root": ASSET_ROOT,
        "candidate_full_texts": MANUAL_DIR / "candidate_full_texts.jsonl.gz",
        "hard_pair_pairwise": HARD_PAIR_DIR / "pairwise_road_test_summary.csv",
        "hard_pair_candidate_features": HARD_PAIR_DIR / "candidate_feature_rows.csv.gz",
        "multiscore_candidate_summary": MULTISCORE_DIR / "candidate_multiscore_summary.csv",
        "multiscore_pairwise_gaps": MULTISCORE_DIR / "pairwise_score_gaps.csv.gz",
        "proxy_pairwise_gaps": PROXY_DIR / "pairwise_score_gaps.csv.gz",
    }
    missing = [f"{name}: {rel(path)}" for name, path in required_paths.items() if not path.exists()]
    if missing:
        write_json(OUTPUT_DIR / "input_manifest.json", {"missing": missing})
        raise FileNotFoundError(f"missing required inputs: {missing}")

    for path in [OUTPUT_DIR / "config.json", OUTPUT_DIR / "input_manifest.json", OUTPUT_DIR / "readout.md"]:
        ensure_under_repo(path)

    write_json(
        OUTPUT_DIR / "config.json",
        {
            "run_label": RUN_LABEL,
            "report_only": True,
            "asset_mode": ASSET_MODE,
            "sample_line_limit_per_order": SAMPLE_LINE_LIMIT_PER_ORDER,
            "full_asset_available": False,
            "asset_root": rel(ASSET_ROOT),
            "output_dir": rel(OUTPUT_DIR),
            "scoring_direction": SCORING_DIRECTION,
            "core_orders": CORE_ORDERS,
            "diagnostic_orders": DIAGNOSTIC_ORDERS,
            "dictionary_cuts": DICTIONARY_CUTS,
            "chunk_size": CHUNK_SIZE,
            "candidate_primary_aggregation": "mean of two chunk scores",
            "scorer_policy": "report-only; no production weights/defaults/ranking changes",
        },
    )
    write_json(
        OUTPUT_DIR / "input_manifest.json",
        {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "inputs": {
                name: {
                    "path": rel(path),
                    "exists": path.exists(),
                    "bytes": path.stat().st_size if path.is_file() else 0,
                }
                for name, path in required_paths.items()
            },
            "missing": missing,
        },
    )

    print(f"[{RUN_LABEL}] loading_and_validating_assets")
    assets, validation_rows, duplicate_rows, top_examples = validate_and_load_assets()
    write_csv(
        OUTPUT_DIR / "ngram_asset_counts_by_order.csv",
        validation_rows,
        [
            "dictionary_cut",
            "direction",
            "ngram_order",
            "raw_rows",
            "unique_phrase_count",
            "unique_encoded_token_sequence_count",
            "duplicate_encoded_token_rows",
            "invalid_token_rows",
            "empty_sequence_rows",
            "token_length_min",
            "token_length_median",
            "token_length_max",
            "count_q05",
            "count_median",
            "count_q95",
            "log_count_q05",
            "log_count_median",
            "log_count_q95",
            "path",
        ],
    )
    write_csv(
        OUTPUT_DIR / "ngram_asset_token_length_quantiles.csv",
        validation_rows,
        ["dictionary_cut", "direction", "ngram_order", "token_length_min", "token_length_median", "token_length_max"],
    )
    write_csv(
        OUTPUT_DIR / "ngram_asset_duplicate_report.csv",
        duplicate_rows,
        [
            "dictionary_cut",
            "direction",
            "ngram_order",
            "encoded_token_length",
            "phrase_count",
            "sum_count",
            "max_count",
            "max_log_count",
            "top_latin_ngram",
            "latin_examples",
        ],
    )
    write_csv(
        OUTPUT_DIR / "ngram_asset_top_examples.csv",
        top_examples,
        [
            "dictionary_cut",
            "direction",
            "ngram_order",
            "encoded_token_length",
            "sum_count",
            "max_count",
            "max_log_count",
            "phrase_count",
            "top_latin_ngram",
            "rune_joined",
            "latin_examples",
        ],
    )
    normal_signatures = {
        order: set(assets[("normal", SCORING_DIRECTION, order)].keys()) for order in ALL_ORDERS
    }
    strict_signatures = {
        order: set(assets[("strict", SCORING_DIRECTION, order)].keys()) for order in ALL_ORDERS
    }
    validation_summary = {
        "asset_mode": ASSET_MODE,
        "sample_line_limit_per_order": SAMPLE_LINE_LIMIT_PER_ORDER,
        "full_asset_available": False,
        "orders_present": sorted({as_int(row.get("ngram_order")) for row in validation_rows if row.get("exists", True)}),
        "cuts_present": DICTIONARY_CUTS,
        "directions_present": ASSET_DIRECTIONS,
        "scoring_direction": SCORING_DIRECTION,
        "uses_rune_token_ids": True,
        "uses_rune_key_hex": False,
        "all_required_paths_exist": not missing,
        "normal_and_strict_content_distinct_by_order": {
            str(order): normal_signatures[order] != strict_signatures[order] for order in ALL_ORDERS
        },
        "validation_rows": validation_rows,
    }
    write_json(OUTPUT_DIR / "ngram_asset_validation_summary.json", validation_summary)
    write_asset_validation_readout(validation_rows, validation_summary)
    write_json(
        OUTPUT_DIR / "ngram_asset_manifest.json",
        {
            "asset_root": rel(ASSET_ROOT),
            "asset_mode": ASSET_MODE,
            "sample_line_limit_per_order": SAMPLE_LINE_LIMIT_PER_ORDER,
            "full_asset_available": False,
            "source_readout": rel(ASSET_ROOT / "readout.md"),
            "tables": validation_rows,
        },
    )

    index = build_scan_index(assets)
    candidates = load_candidate_tokens()
    chunk_rows, top_records = scan_candidates(candidates, index)
    add_chunk_scores(chunk_rows)

    chunk_fields = [
        "candidate_id",
        "chunk_id",
        "direction",
        "dictionary_cut",
        "ngram_order",
        "token_count",
        "hit_count",
        "unique_hit_count",
        "binary_presence",
        "unweighted_hit_density",
        "log_count_weighted_hit_sum",
        "log_count_weighted_hit_density",
        "top_k_log_count_sum",
        "max_log_count",
        "mean_hit_token_length",
        "max_hit_token_length",
        "nonoverlap_hit_count",
        "nonoverlap_log_count_weighted_sum",
        "nonoverlap_token_coverage",
        "nonoverlap_token_coverage_fraction",
        "log_density_z",
        "coverage_z",
        "capped_log_density_z",
        "positive_log_density_z",
    ]
    write_csv(OUTPUT_DIR / "candidate_ngram_chunk_summary.csv", chunk_rows, chunk_fields)
    write_csv_gz(
        OUTPUT_DIR / "candidate_ngram_feature_rows.csv.gz",
        feature_rows_long(chunk_rows),
        [
            "candidate_id",
            "chunk_id",
            "direction",
            "dictionary_cut",
            "ngram_order",
            "weighting_mode",
            "feature_name",
            "feature_value",
            "hit_count",
            "unique_hit_count",
            "token_count",
        ],
    )
    write_top_hits(OUTPUT_DIR / "candidate_ngram_top_hits.jsonl.gz", top_records)

    len7_support = load_len7_hd2_exact_support()
    multiscore_candidates = load_multiscore_candidates()
    candidate_rows = aggregate_candidate_scores(candidates, chunk_rows, len7_support, multiscore_candidates)
    candidate_fields = [
        "candidate_id",
        "label",
        "token_count",
        "chunk_count",
        "current_score",
        "truth_match_ratio",
        "panelA",
        "S5_local_null_positive_selected",
        "len7_hd2_exact_support",
        "N1_normal_2gram_mean",
        "N2_normal_3gram_mean",
        "N3_normal_4gram_mean",
        "N4_normal_2_4_combined_core",
        "N5_strict_2_4_combined_core",
        "N6_normal_plus_strict_support",
        "N7_longest_highest_order_phrase_support",
        "N8_nonoverlap_coverage_score",
        "N9_5gram_diagnostic",
        "N10_span_len7_support_plus_ngram_core",
        "N11_S5_span_support_plus_ngram_core",
        "N12_current_margin_support_policy_score",
        "N13_conservative_support_policy_score",
    ]
    write_csv(OUTPUT_DIR / "candidate_ngram_candidate_summary.csv", candidate_rows, candidate_fields)

    maps = candidate_score_maps(candidate_rows)
    span_gaps = load_multiscore_pair_gaps()
    proxy_gaps = load_proxy_pair_gaps()
    pair_rows = build_pair_rows(read_csv_rows(HARD_PAIR_DIR / "pairwise_road_test_summary.csv"), maps, span_gaps, proxy_gaps)

    score_definitions = {
        "N0_current_scorer_baseline": "current score from existing hard-pair summary",
        "N1_normal_2gram_coherence": "normal FWD 2-gram mean capped log-density z score",
        "N2_normal_3gram_coherence": "normal FWD 3-gram mean capped log-density z score",
        "N3_normal_4gram_coherence": "normal FWD 4-gram mean capped log-density z score",
        "N4_normal_2_4_combined_core": "mean of capped N1, N2, and N3",
        "N5_strict_2_4_combined_core": "strict-only equivalent of N4",
        "N6_normal_plus_strict_support": "N4 plus 0.35 * N5",
        "N7_longest_highest_order_phrase_support": "positive 3/4/5-gram support with higher-order weights",
        "N8_nonoverlap_coverage_score": "mean z-scored non-overlapping token coverage for normal 2/3/4-grams",
        "N9_5gram_diagnostic": "normal 5-gram diagnostic plus small strict support; not part of N4",
        "N10_span_len7_support_plus_ngram_core": "z(normal length 7 HD2 exact support) plus 0.5 * N4",
        "N11_S5_span_support_plus_ngram_core": "z(S5 local null positive selected) plus 0.5 * N4",
        "N12_current_margin_support_policy": "N4 only applies when current score margin is under 0.01",
        "N13_conservative_support_policy": "N6 plus panel-A support, applies above 0.25 margin",
        "coherence_proxy_v1": "prior simple proxy coherence_composite from phaseB_order_phrase_ngram_coherence_hard_pair_report_v1",
        "C7_len7_hd2_exact_support_plus_coherence": "prior proxy combined support score",
        "C8_span_plus_coherence_conservative": "prior proxy conservative support policy",
    }
    write_json(OUTPUT_DIR / "score_definition_manifest.json", score_definitions)

    score_plan = [
        ("N0_current_scorer_baseline", "current_score", 0.0, None),
        ("PanelA_baseline", "panelA", 0.0, None),
        ("S5_local_null_positive_selected", "S5_local_null_positive_selected", 0.0, None),
        ("normal_len7_hd2_exact_support", "len7_hd2_exact_support", 0.0, None),
        ("N1_normal_2gram_coherence", "N1_normal_2gram_mean", 0.0, None),
        ("N2_normal_3gram_coherence", "N2_normal_3gram_mean", 0.0, None),
        ("N3_normal_4gram_coherence", "N3_normal_4gram_mean", 0.0, None),
        ("N4_normal_2_4_combined_core", "N4_normal_2_4_combined_core", 0.0, None),
        ("N5_strict_2_4_combined_core", "N5_strict_2_4_combined_core", 0.0, None),
        ("N6_normal_plus_strict_support", "N6_normal_plus_strict_support", 0.0, None),
        ("N7_longest_highest_order_phrase_support", "N7_longest_highest_order_phrase_support", 0.0, None),
        ("N8_nonoverlap_coverage_score", "N8_nonoverlap_coverage_score", 0.0, None),
        ("N9_5gram_diagnostic", "N9_5gram_diagnostic", 0.0, None),
        ("N10_span_len7_support_plus_ngram_core", "N10_span_len7_support_plus_ngram_core", 0.0, None),
        ("N11_S5_span_support_plus_ngram_core", "N11_S5_span_support_plus_ngram_core", 0.0, None),
        ("N12_current_margin_support_policy", "N12_current_margin_support_policy_score", 0.0, CURRENT_MARGIN_GATE),
        ("N13_conservative_support_policy", "N13_conservative_support_policy_score", CONSERVATIVE_MARGIN, None),
        ("coherence_proxy_v1", "coherence_proxy_v1", 0.0, None),
        ("C7_len7_hd2_exact_support_plus_coherence", "C7_len7_hd2_exact_support_plus_coherence", 0.0, None),
        ("C8_span_plus_coherence_conservative", "C8_span_plus_coherence_conservative", 0.0, None),
    ]

    score_summary: list[dict[str, Any]] = []
    pair_gap_rows: list[dict[str, Any]] = []
    all_score_names: list[str] = []
    for display_name, source_name, threshold, current_margin_gate in score_plan:
        if source_name != display_name and f"{source_name}_gap" in pair_rows[0]:
            for row in pair_rows:
                row[f"{display_name}_gap"] = row.get(f"{source_name}_gap", 0.0)
        summary, details = evaluate_pairs(pair_rows, display_name, threshold=threshold, current_margin_gate=current_margin_gate)
        score_summary.append(summary)
        pair_gap_rows.extend(details)
        all_score_names.append(display_name)

    summary_fields = [
        "score_family",
        "n_pairs",
        "truth_better_preference_count",
        "truth_better_preference_rate",
        "truth_preference_95ci_low",
        "truth_preference_95ci_high",
        "rescues",
        "breaks",
        "net_rescues",
        "mean_gap",
        "median_gap",
        "gap_q05",
        "gap_q25",
        "gap_q75",
        "gap_q95",
        "applied_count",
        "current_scorer_correct_count",
        "current_scorer_misrank_count",
        "truth_preference_when_current_correct",
        "truth_preference_when_current_wrong",
    ]
    write_csv(OUTPUT_DIR / "score_family_pairwise_summary.csv", score_summary, summary_fields)

    gap_fields = [
        "score_family",
        "pair_id",
        "truth_better_candidate_id",
        "truth_worse_candidate_id",
        "score_gap",
        "score_applies",
        "score_prefers_truth_better",
        "current_scorer_correct",
        "current_score_gap",
        "panelA_gap",
        "S5_gap",
        "len7_hd2_exact_support_gap",
        "coherence_proxy_v1_gap",
        "C7_proxy_combined_gap",
        "rescues_current_misrank",
        "breaks_current_correct",
    ]
    write_csv_gz(OUTPUT_DIR / "pairwise_score_gaps.csv.gz", pair_gap_rows, gap_fields)

    sweep_rows: list[dict[str, Any]] = []
    for display_name, _source_name, _threshold, current_margin_gate in score_plan:
        sweep_rows.extend(margin_sweep(pair_rows, display_name, current_margin_gate=current_margin_gate))
    write_csv(
        OUTPUT_DIR / "score_family_margin_sweep.csv",
        sweep_rows,
        [
            "score_family",
            "threshold",
            "applied_count",
            "rescues",
            "breaks",
            "net",
            "precision_of_applied_overrides",
            "misrank_recall",
        ],
    )

    correlation_rows = build_correlation_summary(pair_rows, all_score_names)
    correlation_fields = ["score_family"] + [field for field in correlation_rows[0] if field != "score_family"]
    write_csv(OUTPUT_DIR / "correlation_summary.csv", correlation_rows, correlation_fields)

    write_csv(
        OUTPUT_DIR / "ngram_order_summary.csv",
        summarize_group(chunk_rows, ["ngram_order"], ["hit_count", "log_count_weighted_hit_density", "nonoverlap_token_coverage_fraction"]),
        ["ngram_order", "row_count", "hit_count_mean", "hit_count_median", "hit_count_q95", "log_count_weighted_hit_density_mean", "log_count_weighted_hit_density_median", "log_count_weighted_hit_density_q95", "nonoverlap_token_coverage_fraction_mean", "nonoverlap_token_coverage_fraction_median", "nonoverlap_token_coverage_fraction_q95"],
    )
    write_csv(
        OUTPUT_DIR / "dictionary_cut_summary.csv",
        summarize_group(chunk_rows, ["dictionary_cut"], ["hit_count", "log_count_weighted_hit_density", "nonoverlap_token_coverage_fraction"]),
        ["dictionary_cut", "row_count", "hit_count_mean", "hit_count_median", "hit_count_q95", "log_count_weighted_hit_density_mean", "log_count_weighted_hit_density_median", "log_count_weighted_hit_density_q95", "nonoverlap_token_coverage_fraction_mean", "nonoverlap_token_coverage_fraction_median", "nonoverlap_token_coverage_fraction_q95"],
    )
    write_csv(
        OUTPUT_DIR / "weighting_mode_summary.csv",
        summarize_group(list(feature_rows_long(chunk_rows)), ["weighting_mode", "feature_name"], ["feature_value"]),
        [
            "weighting_mode",
            "feature_name",
            "row_count",
            "feature_value_mean",
            "feature_value_median",
            "feature_value_q95",
        ],
    )

    comparison_names = {
        "coherence_proxy_v1",
        "C7_len7_hd2_exact_support_plus_coherence",
        "C8_span_plus_coherence_conservative",
        "N4_normal_2_4_combined_core",
        "N6_normal_plus_strict_support",
        "N10_span_len7_support_plus_ngram_core",
        "N11_S5_span_support_plus_ngram_core",
        "N13_conservative_support_policy",
    }
    proxy_comparison_rows = [row for row in score_summary if row["score_family"] in comparison_names]
    write_csv(OUTPUT_DIR / "proxy_vs_filtered_ngram_comparison.csv", proxy_comparison_rows, summary_fields)
    write_csv(OUTPUT_DIR / "top_ngram_rescues.csv", top_rows(pair_gap_rows, "rescues_current_misrank"), gap_fields)
    write_csv(OUTPUT_DIR / "top_ngram_breaks.csv", top_rows(pair_gap_rows, "breaks_current_correct"), gap_fields)
    write_csv(OUTPUT_DIR / "top_ngram_false_positives.csv", top_rows(pair_gap_rows, "breaks_current_correct"), gap_fields)
    write_csv(OUTPUT_DIR / "top_ngram_false_negatives.csv", false_negative_rows(pair_gap_rows), gap_fields)

    elapsed_s = time.perf_counter() - start
    write_readout(score_summary, correlation_rows, elapsed_s)
    print(f"[{RUN_LABEL}] complete candidates={len(candidate_rows)} pairs={len(pair_rows)} elapsed_s={elapsed_s:.1f}")
    print(f"[{RUN_LABEL}] output_dir={rel(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
