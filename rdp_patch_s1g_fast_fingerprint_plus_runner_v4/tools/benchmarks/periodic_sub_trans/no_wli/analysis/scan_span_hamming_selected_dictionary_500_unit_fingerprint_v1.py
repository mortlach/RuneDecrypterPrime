from __future__ import annotations

"""
Report-only S1g selected-dictionary 500-unit raw span-Hamming fingerprint scan.

No CLI arguments. Edit constants below, then run from an IDE or as a normal
Python script.

This script is intentionally separate from the existing span-Hamming scorer
calibration scripts. It uses the fast backend's analysis-only
``fingerprint_raw_hamming_counts`` mode, which records raw length-by-HD
histograms rather than selected intervals or best-window intervals.

Hard policy for this run:

- selected dictionaries only;
- never use ``require_selected=False``;
- never use all-row dictionary cuts;
- 500-token chunks are primary;
- ``full_1000`` is comparison only;
- HD bins are ``0..length-1``;
- no runtime solver behaviour is changed;
- no Stage 2 gate is promoted.
"""

import csv
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence


RUN_LABEL = "span_hamming_selected_dictionary_500_unit_scan_v1"
RUN_MODE = "inventory_only"
# Allowed values:
#   "inventory_only"
#   "parity_smoke"
#   "canary"
#   "full"

S1_PAIR_ROWS_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"
)
UNIQUE_PARTIAL_ROWS_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_partial_text_review_v1/unique_partial_text_rows.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_selected_dictionary_500_unit_scan_v1"
)

SPAN_LENGTHS = tuple(range(1, 15))
PRIMARY_SAMPLE_LENGTH = 500
PARITY_TOKEN_HASH_LIMIT = 20
CANARY_TOKEN_HASH_LIMIT = 20
FULL_TOKEN_HASH_LIMIT = 0  # 0 means all token hashes in the S1 pair table.
PROGRESS_EVERY_SAMPLES = 50
FLOAT_TOLERANCE = 1e-12

# Full mode writes chunk histograms only by default. Offset rows are usually
# best kept for canary sizing because they can be much larger.
FULL_INCLUDE_OFFSET_ROWS = False
CANARY_INCLUDE_OFFSET_ROWS = True
MATCH_DUMP_TOKEN_HASH_LIMIT = 2
MATCH_DUMP_ENABLED_FOR_CANARY = False
MATCH_DUMP_ENABLED_FOR_FULL = False

# Fingerprint mode only: 0 means uncapped. If this is changed to a positive
# number, the summary and cap-pressure files will record that it is capped.
FINGERPRINT_MAX_CANDIDATES_PER_WINDOW = 0

FINGERPRINT_SCOPE = "raw_hamming_counts"
FINGERPRINT_MODE = "analysis_only"
FINGERPRINT_DETAIL_CHUNK = "chunk_histogram"
FINGERPRINT_DETAIL_OFFSET = "offset_histogram"
FINGERPRINT_DETAIL_MATCH_DUMP = "match_dump"
HD_MAX_POLICY = "length_minus_one"
HD_BINS_TEXT = "0..max(0, span_length - 1)"
REPORT_ONLY = True
RUNTIME_CHANGE = False
STAGE2_GATE_PROMOTION = False

REQUIRED_OUTPUT_FILES = (
    "selected_dictionary_inventory.csv",
    "fast_backend_parity_summary.csv",
    "fast_backend_parity_failures.csv",
    "fast_backend_parity_readout.md",
    "span_hamming_hd_fingerprint_candidate_rows.csv",
    "span_hamming_hd_fingerprint_offset_rows.csv",
    "span_hamming_hd_fingerprint_match_dump_debug.csv",
    "span_hamming_500_unit_candidate_features.csv",
    "span_hamming_500_unit_pair_feature_summary.csv",
    "span_hamming_500_unit_pair_flags.csv",
    "cap_pressure_by_dictionary_length.csv",
    "span_hamming_selected_dictionary_timing_summary.csv",
    "span_hamming_selected_dictionary_timing_by_length.csv",
    "span_hamming_selected_dictionary_config_summary.csv",
    "span_hamming_selected_dictionary_summary.json",
    "span_hamming_selected_dictionary_readout.md",
)

FEATURE_DEFINITIONS = (
    ("hd_le_0", "higher"),
    ("hd_le_1", "higher"),
    ("hd_le_2", "higher"),
    ("err_le_010", "higher"),
    ("err_le_015", "higher"),
    ("err_le_020", "higher"),
    ("err_le_025", "higher"),
    ("err_le_033", "higher"),
    ("len_ge_5_err_le_020", "higher"),
    ("len_ge_8_err_le_015", "higher"),
    ("len_ge_10_err_le_020", "higher"),
    ("exact_len_ge_5", "higher"),
    ("exact_len_ge_8", "higher"),
    ("short_weak_len_le_4_err_gt_025", "lower"),
)
FEATURE_DIRECTIONS = dict(FEATURE_DEFINITIONS)
AGGREGATIONS_500 = ("mean", "median", "min", "max", "lower_quartile", "range")


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root from script path")


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))



def _load_raw1grams_wordlists(*args: Any, **kwargs: Any) -> Any:
    # Lazy import keeps pure unit tests importable in reduced review bundles
    # that do not include rune_decrypter_prime.data assets.
    from rune_decrypter_prime.scoring.hamming.loader import load_raw1grams_wordlists

    return load_raw1grams_wordlists(*args, **kwargs)


def _fast_span_hamming_available() -> bool:
    from rune_decrypter_prime.scoring.span_hamming.fast_backend import fast_span_hamming_available

    return fast_span_hamming_available()


def _fast_span_hamming_backend_class() -> Any:
    from rune_decrypter_prime.scoring.span_hamming.fast_backend import FastSpanHammingBackend

    return FastSpanHammingBackend


def _span_hamming_config_class() -> Any:
    from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig

    return SpanHammingConfig


S1_PAIR_ROWS = REPO_ROOT / S1_PAIR_ROWS_REL
UNIQUE_PARTIAL_ROWS = REPO_ROOT / UNIQUE_PARTIAL_ROWS_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


@dataclass(frozen=True)
class DictionarySpec:
    dictionary_cut: str
    dictionary_path: str
    require_selected: bool
    diagnostic_only: bool = False


@dataclass(frozen=True)
class ChunkSample:
    token_hash: str
    sample_kind: str
    sample_start: int
    sample_length: int
    tokens: tuple[int, ...]

    @property
    def sample_end(self) -> int:
        return self.sample_start + self.sample_length

    @property
    def sample_id(self) -> str:
        return f"{self.token_hash}::{self.sample_kind}_{self.sample_start}_{self.sample_end}"


DICTIONARY_SPECS = (
    DictionarySpec("raw_selected", "assets/hamming_raw_1g", True, False),
    DictionarySpec("strict_selected", "assets/hamming_dictionary_policies/strict/hamming_raw_1g", True, False),
    DictionarySpec("normal_selected", "assets/hamming_dictionary_policies/normal/hamming_raw_1g", True, False),
    DictionarySpec("broad_selected", "assets/hamming_dictionary_policies/broad/hamming_raw_1g", True, False),
    DictionarySpec("research_selected", "assets/hamming_dictionary_policies/research/hamming_raw_1g", True, True),
)

PRIMARY_DICTIONARY_CUTS = tuple(spec.dictionary_cut for spec in DICTIONARY_SPECS if not spec.diagnostic_only)
DIAGNOSTIC_DICTIONARY_CUTS = tuple(spec.dictionary_cut for spec in DICTIONARY_SPECS if spec.diagnostic_only)


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_selected_only_specs(specs: Sequence[DictionarySpec] = DICTIONARY_SPECS) -> None:
    for spec in specs:
        cut = spec.dictionary_cut.lower()
        if not spec.require_selected:
            raise ValueError(f"require_selected=False is forbidden for S1g: {spec.dictionary_cut}")
        if cut.endswith("_all") or "_all" in cut:
            raise ValueError(f"all-row dictionary cuts are forbidden for S1g: {spec.dictionary_cut}")


def _parse_numeric_tokens(text: str) -> tuple[int, ...]:
    values = tuple(int(part) for part in str(text).split() if part.strip())
    for value in values:
        if value < 0 or value > 28:
            raise ValueError(f"numeric rune token out of range 0..28: {value}")
    return values


def _read_pair_rows() -> list[dict[str, str]]:
    with S1_PAIR_ROWS.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _required_token_hashes(pair_rows: Sequence[Mapping[str, str]], limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for row in pair_rows:
        for key in ("winner_token_hash", "challenger_token_hash"):
            token_hash = str(row.get(key, "")).strip()
            if token_hash and token_hash not in seen:
                seen.add(token_hash)
                out.append(token_hash)
                if limit and len(out) >= limit:
                    return out
    return out


def _read_token_rows(required_hashes: Sequence[str]) -> dict[str, tuple[int, ...]]:
    required = set(required_hashes)
    loaded: dict[str, tuple[int, ...]] = {}
    with UNIQUE_PARTIAL_ROWS.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            token_hash = str(row.get("partial_text_hash", "")).strip()
            if token_hash not in required:
                continue
            loaded[token_hash] = _parse_numeric_tokens(str(row.get("token_sequence_text", "")))
            if len(loaded) >= len(required):
                break
    return {token_hash: loaded[token_hash] for token_hash in required_hashes if token_hash in loaded}


def _chunk_specs_for_length(token_length: int) -> list[tuple[str, int, int]]:
    out: list[tuple[str, int, int]] = []
    if token_length >= PRIMARY_SAMPLE_LENGTH:
        out.extend(
            [
                ("prefix_500", 0, PRIMARY_SAMPLE_LENGTH),
                ("middle_500", max(0, (token_length - PRIMARY_SAMPLE_LENGTH) // 2), PRIMARY_SAMPLE_LENGTH),
                ("suffix_500", token_length - PRIMARY_SAMPLE_LENGTH, PRIMARY_SAMPLE_LENGTH),
            ]
        )
    if token_length > 0:
        out.append(("full_1000", 0, token_length))
    return out


def build_chunk_samples(tokens_by_hash: Mapping[str, Sequence[int]]) -> list[ChunkSample]:
    out: list[ChunkSample] = []
    for token_hash, token_values in tokens_by_hash.items():
        tokens = tuple(int(value) for value in token_values)
        for sample_kind, start, length in _chunk_specs_for_length(len(tokens)):
            sample_tokens = tokens[start:start + length]
            if len(sample_tokens) != length:
                continue
            out.append(
                ChunkSample(
                    token_hash=token_hash,
                    sample_kind=sample_kind,
                    sample_start=start,
                    sample_length=length,
                    tokens=tuple(sample_tokens),
                )
            )
    return out


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_placeholder(path: Path, *, reason: str, run_mode: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "not_produced",
        "reason": reason,
        "run_mode": run_mode,
        "created_utc": _now_iso(),
        "run_label": RUN_LABEL,
    }
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    elif path.suffix.lower() == ".md":
        path.write_text(
            "\n".join(
                [
                    f"# Placeholder: {path.name}",
                    "",
                    f"- status: `{payload['status']}`",
                    f"- reason: `{reason}`",
                    f"- run_mode: `{run_mode}`",
                    f"- created_utc: `{payload['created_utc']}`",
                    f"- run_label: `{RUN_LABEL}`",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    else:
        _write_csv(path, [payload], ["status", "reason", "run_mode", "created_utc", "run_label"])


def _ensure_required_placeholders(produced: set[str], *, reason: str, run_mode: str) -> None:
    for filename in REQUIRED_OUTPUT_FILES:
        if filename in produced:
            continue
        _write_placeholder(OUTPUT_DIR / filename, reason=reason, run_mode=run_mode)


def _dictionary_inventory_rows() -> list[dict[str, Any]]:
    _validate_selected_only_specs()
    rows: list[dict[str, Any]] = []
    for spec in DICTIONARY_SPECS:
        path = REPO_ROOT / spec.dictionary_path
        file_exists = path.exists()
        load_ok = False
        missing_reason = ""
        wordlists: dict[int, list[list[int]]] = {}
        if not file_exists:
            missing_reason = "dictionary_path_missing"
        else:
            try:
                loaded, _ = _load_raw1grams_wordlists(path, build_rtl=False, require_selected=spec.require_selected)
                wordlists = loaded
                load_ok = True
            except Exception as exc:  # explicit accounting, not silent fallback
                missing_reason = f"load_failed:{type(exc).__name__}:{exc}"
        for length in SPAN_LENGTHS:
            rows.append(
                {
                    "dictionary_cut": spec.dictionary_cut,
                    "dictionary_path": spec.dictionary_path,
                    "require_selected": int(spec.require_selected),
                    "diagnostic_only": int(spec.diagnostic_only),
                    "length": length,
                    "selected_row_count": len(wordlists.get(length, [])) if load_ok else 0,
                    "file_exists": int(file_exists),
                    "load_ok": int(load_ok),
                    "missing_reason": missing_reason,
                }
            )
    return rows


def _inventory_fieldnames() -> list[str]:
    return [
        "dictionary_cut",
        "dictionary_path",
        "require_selected",
        "diagnostic_only",
        "length",
        "selected_row_count",
        "file_exists",
        "load_ok",
        "missing_reason",
    ]


def _inventory_status(rows: Sequence[Mapping[str, Any]]) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    failed: list[str] = []
    by_cut: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_cut.setdefault(str(row["dictionary_cut"]), []).append(row)
    for cut in PRIMARY_DICTIONARY_CUTS:
        cut_rows = by_cut.get(cut, [])
        if not cut_rows:
            missing.append(cut)
            continue
        if not any(int(row.get("file_exists", 0)) for row in cut_rows):
            missing.append(cut)
        elif not any(int(row.get("load_ok", 0)) for row in cut_rows):
            failed.append(cut)
    return sorted(set(missing)), sorted(set(failed))


def _span_config() -> Any:
    # max_hd is retained only because update_words_index requires a SpanHammingConfig.
    # The fingerprint method itself uses HD bins 0..length-1.
    SpanHammingConfig = _span_hamming_config_class()
    return SpanHammingConfig(
        len_min=min(SPAN_LENGTHS),
        len_max=max(SPAN_LENGTHS),
        max_hd=2,
        max_candidates_per_window=1024,
        debug_return_intervals=False,
    )


def _build_fast_backend(spec: DictionarySpec) -> tuple[Any | None, str, float]:
    if not _fast_span_hamming_available():
        return None, "fast_backend_unavailable", 0.0
    wordlist_dir = REPO_ROOT / spec.dictionary_path
    if not wordlist_dir.exists():
        return None, f"missing_dictionary_path:{spec.dictionary_path}", 0.0
    start = time.perf_counter()
    try:
        FastSpanHammingBackend = _fast_span_hamming_backend_class()
        backend = FastSpanHammingBackend(
            config=_span_config(),
            wordlist_dir=wordlist_dir,
            require_selected=spec.require_selected,
            return_raw_intervals=False,
        )
    except Exception as exc:
        return None, f"backend_build_failed:{type(exc).__name__}:{exc}", 0.0
    return backend, "", (time.perf_counter() - start) * 1000.0


def _reference_fingerprint_bin_map(
    tokens: Sequence[int],
    wordlists: Mapping[int, Sequence[Sequence[int]]],
) -> dict[tuple[int, int], int]:
    out: dict[tuple[int, int], int] = {}
    for length in SPAN_LENGTHS:
        for hd in range(length):
            out[(length, hd)] = 0
        words = [tuple(int(value) for value in word) for word in wordlists.get(length, ()) if len(word) == length]
        if not words or len(tokens) < length:
            continue
        for start in range(0, len(tokens) - length + 1):
            window = tokens[start:start + length]
            for word in words:
                distance = sum(1 for left, right in zip(window, word) if int(left) != int(right))
                if distance < length:
                    out[(length, distance)] += 1
    return out


def _payload_chunk_bin_map(payload: Mapping[str, Any]) -> dict[tuple[int, int], int]:
    return {
        (int(row["length"]), int(row["hd"])): int(row["raw_match_count"])
        for row in payload.get("chunk_bins", [])
    }


def _payload_length_metric(payload: Mapping[str, Any], metric_name: str, length: int) -> int:
    length_bins = [int(value) for value in payload.get("length_bins", [])]
    values = list(payload.get(metric_name, []))
    if length not in length_bins:
        return 0
    index = length_bins.index(length)
    if index >= len(values):
        return 0
    return int(values[index])


def _safe_float(value: object) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return float(ordered[idx])


def _error_rate(hd: int, length: int) -> float:
    if length < 1:
        raise ValueError("length must be >= 1")
    return float(hd) / float(length)


def _exact_fraction(hd: int, length: int) -> float:
    return 1.0 - _error_rate(hd, length)


def _candidate_fingerprint_rows(
    *,
    spec: DictionarySpec,
    sample: ChunkSample,
    payload: Mapping[str, Any],
    score_ms: float,
    backend_name: str,
    build_ms: float,
) -> list[dict[str, Any]]:
    cap = int(payload.get("cap", FINGERPRINT_MAX_CANDIDATES_PER_WINDOW) or 0)
    is_uncapped = bool(payload.get("is_uncapped", cap == 0))
    rows: list[dict[str, Any]] = []
    for bin_row in payload.get("chunk_bins", []):
        length = int(bin_row["length"])
        hd = int(bin_row["hd"])
        if hd >= length:
            raise ValueError(f"fingerprint emitted forbidden hd == length row: length={length} hd={hd}")
        count = int(bin_row["raw_match_count"])
        exact = _exact_fraction(hd, length)
        n_windows_scored = _payload_length_metric(payload, "n_windows_scored_by_len", length)
        n_considered = _payload_length_metric(payload, "n_candidates_considered_by_len", length)
        n_pruned = _payload_length_metric(payload, "n_candidates_pruned_cap_by_len", length)
        rows.append(
            {
                "dictionary_cut": spec.dictionary_cut,
                "token_hash": sample.token_hash,
                "sample_kind": sample.sample_kind,
                "sample_start": sample.sample_start,
                "sample_length": sample.sample_length,
                "span_length": length,
                "hd": hd,
                "error_rate": f"{_error_rate(hd, length):.12g}",
                "exact_fraction": f"{exact:.12g}",
                "raw_match_count": count,
                "raw_match_weight_len_norm": f"{(count * length) / float(max(1, sample.sample_length)):.12g}",
                "raw_match_weight_gamma2": f"{(count * length * exact * exact) / float(max(1, sample.sample_length)):.12g}",
                "selected_match_count": "",
                "selected_match_weight_current": "",
                "selected_match_weight_len_norm": "",
                "n_windows_scored": n_windows_scored,
                "n_candidates_considered": n_considered,
                "n_candidates_pruned_cap": n_pruned,
                "candidate_cap_pruned_rate": f"{n_pruned / float(max(1, n_pruned + n_considered)):.12g}",
                "score_ms": f"{score_ms:.6f}",
                "build_ms": f"{build_ms:.6f}",
                "backend_name": backend_name,
                "fingerprint_scope": FINGERPRINT_SCOPE,
                "fingerprint_detail_level": FINGERPRINT_DETAIL_CHUNK,
                "hd_max_policy": HD_MAX_POLICY,
                "cap": cap,
                "is_uncapped": int(is_uncapped),
            }
        )
    return rows


def _candidate_fingerprint_fieldnames() -> list[str]:
    return [
        "dictionary_cut",
        "token_hash",
        "sample_kind",
        "sample_start",
        "sample_length",
        "span_length",
        "hd",
        "error_rate",
        "exact_fraction",
        "raw_match_count",
        "raw_match_weight_len_norm",
        "raw_match_weight_gamma2",
        "selected_match_count",
        "selected_match_weight_current",
        "selected_match_weight_len_norm",
        "n_windows_scored",
        "n_candidates_considered",
        "n_candidates_pruned_cap",
        "candidate_cap_pruned_rate",
        "score_ms",
        "build_ms",
        "backend_name",
        "fingerprint_scope",
        "fingerprint_detail_level",
        "hd_max_policy",
        "cap",
        "is_uncapped",
    ]


def _offset_fingerprint_rows(
    *,
    spec: DictionarySpec,
    sample: ChunkSample,
    payload: Mapping[str, Any],
    score_ms: float,
    backend_name: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bin_row in payload.get("offset_bins", []):
        length = int(bin_row["length"])
        hd = int(bin_row["hd"])
        if hd >= length:
            raise ValueError(f"offset fingerprint emitted forbidden hd == length row: length={length} hd={hd}")
        rows.append(
            {
                "dictionary_cut": spec.dictionary_cut,
                "token_hash": sample.token_hash,
                "sample_kind": sample.sample_kind,
                "sample_start": sample.sample_start,
                "sample_length": sample.sample_length,
                "offset": int(bin_row["offset"]),
                "span_length": length,
                "hd": hd,
                "error_rate": f"{_error_rate(hd, length):.12g}",
                "raw_match_count": int(bin_row["raw_match_count"]),
                "score_ms": f"{score_ms:.6f}",
                "backend_name": backend_name,
                "fingerprint_scope": FINGERPRINT_SCOPE,
                "fingerprint_detail_level": FINGERPRINT_DETAIL_OFFSET,
                "hd_max_policy": HD_MAX_POLICY,
            }
        )
    return rows


def _offset_fingerprint_fieldnames() -> list[str]:
    return [
        "dictionary_cut",
        "token_hash",
        "sample_kind",
        "sample_start",
        "sample_length",
        "offset",
        "span_length",
        "hd",
        "error_rate",
        "raw_match_count",
        "score_ms",
        "backend_name",
        "fingerprint_scope",
        "fingerprint_detail_level",
        "hd_max_policy",
    ]


def _match_dump_rows(
    *,
    spec: DictionarySpec,
    sample: ChunkSample,
    payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for match in payload.get("match_dump_rows", []):
        length = int(match["length"])
        hd = int(match["hd"])
        if hd >= length:
            raise ValueError(f"match dump emitted forbidden hd == length row: length={length} hd={hd}")
        rows.append(
            {
                "dictionary_cut": spec.dictionary_cut,
                "token_hash": sample.token_hash,
                "sample_kind": sample.sample_kind,
                "sample_start": sample.sample_start,
                "sample_length": sample.sample_length,
                "offset": int(match["offset"]),
                "span_length": length,
                "dictionary_entry_id": int(match["word_id"]),
                "hd": hd,
                "error_rate": f"{_error_rate(hd, length):.12g}",
                "fingerprint_scope": FINGERPRINT_SCOPE,
                "fingerprint_detail_level": FINGERPRINT_DETAIL_MATCH_DUMP,
                "hd_max_policy": HD_MAX_POLICY,
            }
        )
    return rows


def _match_dump_fieldnames() -> list[str]:
    return [
        "dictionary_cut",
        "token_hash",
        "sample_kind",
        "sample_start",
        "sample_length",
        "offset",
        "span_length",
        "dictionary_entry_id",
        "hd",
        "error_rate",
        "fingerprint_scope",
        "fingerprint_detail_level",
        "hd_max_policy",
    ]


def _feature_values_from_bins(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    values = {name: 0.0 for name, _direction in FEATURE_DEFINITIONS}
    sample_length = int(rows[0]["sample_length"]) if rows else 1
    denom = float(max(1, sample_length))
    for row in rows:
        length = int(row["span_length"])
        hd = int(row["hd"])
        count = float(row["raw_match_count"])
        if count <= 0.0:
            continue
        rate = _error_rate(hd, length)
        weight_len_norm = count * float(length) / denom
        weight_gamma2 = weight_len_norm * (_exact_fraction(hd, length) ** 2)
        if hd <= 0:
            values["hd_le_0"] += weight_len_norm
        if hd <= 1:
            values["hd_le_1"] += weight_gamma2
        if hd <= 2:
            values["hd_le_2"] += weight_gamma2
        if rate <= 0.10:
            values["err_le_010"] += weight_gamma2
        if rate <= 0.15:
            values["err_le_015"] += weight_gamma2
        if rate <= 0.20:
            values["err_le_020"] += weight_gamma2
        if rate <= 0.25:
            values["err_le_025"] += weight_gamma2
        if rate <= 0.33:
            values["err_le_033"] += weight_gamma2
        if length >= 5 and rate <= 0.20:
            values["len_ge_5_err_le_020"] += weight_gamma2
        if length >= 8 and rate <= 0.15:
            values["len_ge_8_err_le_015"] += weight_gamma2
        if length >= 10 and rate <= 0.20:
            values["len_ge_10_err_le_020"] += weight_gamma2
        if hd == 0 and length >= 5:
            values["exact_len_ge_5"] += weight_len_norm
        if hd == 0 and length >= 8:
            values["exact_len_ge_8"] += weight_len_norm
        if length <= 4 and rate > 0.25:
            values["short_weak_len_le_4_err_gt_025"] += weight_len_norm * rate
    return values


def _candidate_feature_rows(candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for row in candidate_rows:
        key = (str(row["dictionary_cut"]), str(row["token_hash"]), str(row["sample_kind"]))
        grouped.setdefault(key, []).append(row)

    out: list[dict[str, Any]] = []
    for (dictionary_cut, token_hash, sample_kind), rows in sorted(grouped.items()):
        values = _feature_values_from_bins(rows)
        first = rows[0]
        base_row: dict[str, Any] = {
            "dictionary_cut": dictionary_cut,
            "token_hash": token_hash,
            "sample_basis": sample_kind,
            "aggregation": "sample",
            "sample_kind": sample_kind,
            "sample_start": first["sample_start"],
            "sample_length": first["sample_length"],
            "fingerprint_scope": FINGERPRINT_SCOPE,
            "hd_max_policy": HD_MAX_POLICY,
        }
        base_row.update({name: f"{value:.12g}" for name, value in values.items()})
        out.append(base_row)

    by_dictionary_token: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in out:
        if row["sample_basis"] in {"prefix_500", "middle_500", "suffix_500"}:
            by_dictionary_token.setdefault((str(row["dictionary_cut"]), str(row["token_hash"])), []).append(row)

    for (dictionary_cut, token_hash), sample_rows in sorted(by_dictionary_token.items()):
        if {str(row["sample_basis"]) for row in sample_rows} != {"prefix_500", "middle_500", "suffix_500"}:
            continue
        for aggregation in AGGREGATIONS_500:
            agg_row: dict[str, Any] = {
                "dictionary_cut": dictionary_cut,
                "token_hash": token_hash,
                "sample_basis": f"500_{aggregation}",
                "aggregation": aggregation,
                "sample_kind": "prefix_500+middle_500+suffix_500",
                "sample_start": "",
                "sample_length": PRIMARY_SAMPLE_LENGTH,
                "fingerprint_scope": FINGERPRINT_SCOPE,
                "hd_max_policy": HD_MAX_POLICY,
            }
            for feature_name, _direction in FEATURE_DEFINITIONS:
                values = [float(row[feature_name]) for row in sample_rows]
                if aggregation == "mean":
                    value = mean(values)
                elif aggregation == "median":
                    value = median(values)
                elif aggregation == "min":
                    value = min(values)
                elif aggregation == "max":
                    value = max(values)
                elif aggregation == "lower_quartile":
                    value = _percentile(values, 0.25)
                elif aggregation == "range":
                    value = max(values) - min(values)
                else:
                    raise ValueError(f"unknown aggregation: {aggregation}")
                agg_row[feature_name] = f"{value:.12g}"
            out.append(agg_row)
    return out


def _candidate_feature_fieldnames() -> list[str]:
    return [
        "dictionary_cut",
        "token_hash",
        "sample_basis",
        "aggregation",
        "sample_kind",
        "sample_start",
        "sample_length",
        "fingerprint_scope",
        "hd_max_policy",
        *[name for name, _direction in FEATURE_DEFINITIONS],
    ]


def _feature_preference(direction: str, winner_value: object, challenger_value: object) -> str:
    winner = _safe_float(winner_value)
    challenger = _safe_float(challenger_value)
    if winner is None or challenger is None:
        return "no_decision"
    if abs(winner - challenger) <= FLOAT_TOLERANCE:
        return "tie"
    if direction == "higher":
        return "truth_better" if winner > challenger else "truth_worse"
    if direction == "lower":
        return "truth_better" if winner < challenger else "truth_worse"
    raise ValueError(f"unknown direction: {direction}")


def _pair_summaries(
    *,
    pair_rows: Sequence[Mapping[str, str]],
    feature_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_key = {
        (str(row["dictionary_cut"]), str(row["token_hash"]), str(row["sample_basis"])): row
        for row in feature_rows
    }
    dictionary_cuts = sorted({str(row["dictionary_cut"]) for row in feature_rows})
    sample_bases = sorted({str(row["sample_basis"]) for row in feature_rows})
    summary_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    for dictionary_cut in dictionary_cuts:
        for sample_basis in sample_bases:
            for feature_name, direction in FEATURE_DEFINITIONS:
                summary = {
                    "feature_name": feature_name,
                    "dictionary_cut": dictionary_cut,
                    "sample_basis": sample_basis,
                    "aggregation": sample_basis.replace("500_", "") if sample_basis.startswith("500_") else "sample",
                    "feature_direction": direction,
                    "pair_count": 0,
                    "current_misranked_count": 0,
                    "current_control_count": 0,
                    "rescues": 0,
                    "breaks": 0,
                    "net": 0,
                    "unique_misranked_rescues": 0,
                    "unique_control_breaks": 0,
                    "ties": 0,
                    "no_decisions": 0,
                    "dominant_rescue_fixture_search_fraction": "",
                    "dominant_break_fixture_search_fraction": "",
                    "candidate_cap_pruned_rate_mean": "",
                    "mean_score_ms": "",
                    "p95_score_ms": "",
                }
                rescue_ids: set[str] = set()
                break_ids: set[str] = set()
                for pair in pair_rows:
                    winner_hash = str(pair.get("winner_token_hash", "")).strip()
                    challenger_hash = str(pair.get("challenger_token_hash", "")).strip()
                    winner = by_key.get((dictionary_cut, winner_hash, sample_basis))
                    challenger = by_key.get((dictionary_cut, challenger_hash, sample_basis))
                    pair_id = str(pair.get("pair_id", f"{winner_hash}|{challenger_hash}"))
                    current_correct = str(pair.get("current_score_correct", "")).strip() == "1"
                    if winner is None or challenger is None:
                        summary["no_decisions"] += 1
                        continue
                    pref = _feature_preference(direction, winner.get(feature_name), challenger.get(feature_name))
                    summary["pair_count"] += 1
                    if current_correct:
                        summary["current_control_count"] += 1
                    else:
                        summary["current_misranked_count"] += 1
                    if pref == "no_decision":
                        summary["no_decisions"] += 1
                    elif pref == "tie":
                        summary["ties"] += 1
                    elif (not current_correct) and pref == "truth_better":
                        summary["rescues"] += 1
                        rescue_ids.add(pair_id)
                        flag_rows.append(
                            {
                                "pair_id": pair_id,
                                "dictionary_cut": dictionary_cut,
                                "sample_basis": sample_basis,
                                "feature_name": feature_name,
                                "flag": "rescue",
                                "winner_token_hash": winner_hash,
                                "challenger_token_hash": challenger_hash,
                            }
                        )
                    elif current_correct and pref == "truth_worse":
                        summary["breaks"] += 1
                        break_ids.add(pair_id)
                        flag_rows.append(
                            {
                                "pair_id": pair_id,
                                "dictionary_cut": dictionary_cut,
                                "sample_basis": sample_basis,
                                "feature_name": feature_name,
                                "flag": "break",
                                "winner_token_hash": winner_hash,
                                "challenger_token_hash": challenger_hash,
                            }
                        )
                summary["net"] = int(summary["rescues"]) - int(summary["breaks"])
                summary["unique_misranked_rescues"] = len(rescue_ids)
                summary["unique_control_breaks"] = len(break_ids)
                summary_rows.append(summary)
    summary_rows.sort(key=lambda row: (int(row["net"]), int(row["rescues"]), -int(row["breaks"])), reverse=True)
    return summary_rows, flag_rows


def _pair_summary_fieldnames() -> list[str]:
    return [
        "feature_name",
        "dictionary_cut",
        "sample_basis",
        "aggregation",
        "feature_direction",
        "pair_count",
        "current_misranked_count",
        "current_control_count",
        "rescues",
        "breaks",
        "net",
        "unique_misranked_rescues",
        "unique_control_breaks",
        "ties",
        "no_decisions",
        "dominant_rescue_fixture_search_fraction",
        "dominant_break_fixture_search_fraction",
        "candidate_cap_pruned_rate_mean",
        "mean_score_ms",
        "p95_score_ms",
    ]


def _pair_flag_fieldnames() -> list[str]:
    return [
        "pair_id",
        "dictionary_cut",
        "sample_basis",
        "feature_name",
        "flag",
        "winner_token_hash",
        "challenger_token_hash",
    ]


def _timing_rows(candidate_rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sample_seen: set[tuple[Any, ...]] = set()
    length_seen: set[tuple[Any, ...]] = set()
    by_summary: dict[tuple[str, str, str, int, int, int], list[float]] = {}
    by_length: dict[tuple[str, str, str, int, int, int, int], list[float]] = {}

    for row in candidate_rows:
        score_ms = _safe_float(row.get("score_ms"))
        if score_ms is None:
            continue
        sample_key = (
            row.get("dictionary_cut"),
            row.get("token_hash"),
            row.get("sample_kind"),
            row.get("sample_start"),
            row.get("sample_length"),
            row.get("cap"),
            row.get("is_uncapped"),
        )
        if sample_key not in sample_seen:
            sample_seen.add(sample_key)
            summary_key = (
                str(row["backend_name"]),
                str(row["dictionary_cut"]),
                str(row["sample_kind"]),
                int(row["sample_length"]),
                int(row["cap"]),
                int(row["is_uncapped"]),
            )
            by_summary.setdefault(summary_key, []).append(score_ms)

        length_key_seen = (*sample_key, row.get("span_length"))
        if length_key_seen not in length_seen:
            length_seen.add(length_key_seen)
            length_key = (
                str(row["backend_name"]),
                str(row["dictionary_cut"]),
                str(row["sample_kind"]),
                int(row["sample_length"]),
                int(row["cap"]),
                int(row["is_uncapped"]),
                int(row["span_length"]),
            )
            by_length.setdefault(length_key, []).append(score_ms)

    summary_rows: list[dict[str, Any]] = []
    for (backend_name, dictionary_cut, sample_kind, sample_length, cap, is_uncapped_int), values in sorted(by_summary.items()):
        summary_rows.append(
            {
                "backend_name": backend_name,
                "dictionary_cut": dictionary_cut,
                "sample_kind": sample_kind,
                "sample_length": sample_length,
                "span_length_range": f"{min(SPAN_LENGTHS)}..{max(SPAN_LENGTHS)}",
                "cap": cap,
                "is_uncapped": is_uncapped_int,
                "candidate_count": len(values),
                "mean_score_ms": f"{mean(values):.6f}",
                "median_score_ms": f"{median(values):.6f}",
                "p95_score_ms": f"{_percentile(values, 0.95):.6f}",
                "max_score_ms": f"{max(values):.6f}",
                "build_ms": "",
            }
        )

    length_rows: list[dict[str, Any]] = []
    for (backend_name, dictionary_cut, sample_kind, sample_length, cap, is_uncapped_int, span_length), values in sorted(by_length.items()):
        length_rows.append(
            {
                "backend_name": backend_name,
                "dictionary_cut": dictionary_cut,
                "sample_kind": sample_kind,
                "sample_length": sample_length,
                "span_length": span_length,
                "cap": cap,
                "is_uncapped": is_uncapped_int,
                "candidate_count": len(values),
                "mean_score_ms": f"{mean(values):.6f}",
                "median_score_ms": f"{median(values):.6f}",
                "p95_score_ms": f"{_percentile(values, 0.95):.6f}",
                "max_score_ms": f"{max(values):.6f}",
                "build_ms": "",
            }
        )
    return summary_rows, length_rows

def _timing_summary_fieldnames() -> list[str]:
    return [
        "backend_name",
        "dictionary_cut",
        "sample_kind",
        "sample_length",
        "span_length_range",
        "cap",
        "is_uncapped",
        "candidate_count",
        "mean_score_ms",
        "median_score_ms",
        "p95_score_ms",
        "max_score_ms",
        "build_ms",
    ]


def _timing_by_length_fieldnames() -> list[str]:
    return [
        "backend_name",
        "dictionary_cut",
        "sample_kind",
        "sample_length",
        "span_length",
        "cap",
        "is_uncapped",
        "candidate_count",
        "mean_score_ms",
        "median_score_ms",
        "p95_score_ms",
        "max_score_ms",
        "build_ms",
    ]


def _cap_pressure_rows(candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    sample_length_rows: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for row in candidate_rows:
        unique_key = (
            row.get("dictionary_cut"),
            row.get("token_hash"),
            row.get("sample_kind"),
            row.get("sample_start"),
            row.get("sample_length"),
            row.get("span_length"),
            row.get("cap"),
            row.get("is_uncapped"),
        )
        sample_length_rows.setdefault(unique_key, row)

    grouped: dict[tuple[str, str, int, int, int, int], list[Mapping[str, Any]]] = {}
    for row in sample_length_rows.values():
        key = (
            str(row["dictionary_cut"]),
            str(row["sample_kind"]),
            int(row["sample_length"]),
            int(row["span_length"]),
            int(row["cap"]),
            int(row["is_uncapped"]),
        )
        grouped.setdefault(key, []).append(row)
    out: list[dict[str, Any]] = []
    for (dictionary_cut, sample_kind, sample_length, span_length, cap, is_uncapped), rows in sorted(grouped.items()):
        n_windows = [int(row["n_windows_scored"]) for row in rows]
        n_considered = [int(row["n_candidates_considered"]) for row in rows]
        n_pruned = [int(row["n_candidates_pruned_cap"]) for row in rows]
        score_ms = [float(row["score_ms"]) for row in rows]
        total_considered = sum(n_considered)
        total_pruned = sum(n_pruned)
        out.append(
            {
                "dictionary_cut": dictionary_cut,
                "sample_kind": sample_kind,
                "sample_length": sample_length,
                "span_length": span_length,
                "cap": cap,
                "is_uncapped": is_uncapped,
                "n_windows_scored": sum(n_windows),
                "n_candidates_considered": total_considered,
                "n_candidates_pruned_cap": total_pruned,
                "candidate_cap_pruned_rate": f"{total_pruned / float(max(1, total_considered + total_pruned)):.12g}",
                "mean_score_ms": f"{mean(score_ms):.6f}",
                "p95_score_ms": f"{_percentile(score_ms, 0.95):.6f}",
            }
        )
    return out

def _cap_pressure_fieldnames() -> list[str]:
    return [
        "dictionary_cut",
        "sample_kind",
        "sample_length",
        "span_length",
        "cap",
        "is_uncapped",
        "n_windows_scored",
        "n_candidates_considered",
        "n_candidates_pruned_cap",
        "candidate_cap_pruned_rate",
        "mean_score_ms",
        "p95_score_ms",
    ]


def _config_summary_rows(
    *,
    run_mode: str,
    inventory_rows: Sequence[Mapping[str, Any]],
    completed: Sequence[str],
    missing: Sequence[str],
    failed: Sequence[str],
    skipped: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    load_by_cut: dict[str, bool] = {}
    for row in inventory_rows:
        cut = str(row["dictionary_cut"])
        load_by_cut[cut] = load_by_cut.get(cut, False) or bool(int(row.get("load_ok", 0)))
    out = []
    completed_set = set(completed)
    missing_set = set(missing)
    failed_by_cut: dict[str, str] = {}
    for item in failed:
        item_text = str(item)
        cut, sep, detail = item_text.partition(":")
        failed_by_cut[cut] = detail if sep else "dictionary load/backend failed"
    skipped_reasons = {str(row["dictionary_cut"]): str(row.get("reason", "")) for row in skipped}
    for spec in DICTIONARY_SPECS:
        status = "completed" if spec.dictionary_cut in completed_set else "requested"
        reason = ""
        if spec.dictionary_cut in missing_set:
            status = "missing"
            reason = "dictionary missing"
        elif spec.dictionary_cut in failed_by_cut:
            status = "failed"
            reason = failed_by_cut[spec.dictionary_cut]
        elif spec.dictionary_cut in skipped_reasons:
            status = "skipped_explicitly"
            reason = skipped_reasons[spec.dictionary_cut]
        out.append(
            {
                "run_label": RUN_LABEL,
                "run_mode": run_mode,
                "dictionary_cut": spec.dictionary_cut,
                "dictionary_path": spec.dictionary_path,
                "require_selected": int(spec.require_selected),
                "diagnostic_only": int(spec.diagnostic_only),
                "fingerprint_scope": FINGERPRINT_SCOPE,
                "hd_max_policy": HD_MAX_POLICY,
                "hd_bins": HD_BINS_TEXT,
                "status": status,
                "load_ok": int(load_by_cut.get(spec.dictionary_cut, False)),
                "reason": reason,
            }
        )
    return out


def _summary_json(
    *,
    run_mode: str,
    status: str,
    inventory_rows: Sequence[Mapping[str, Any]],
    completed_configs: Sequence[str],
    missing_configs: Sequence[str],
    skipped_configs: Sequence[Mapping[str, Any]],
    failed_configs: Sequence[str],
    candidate_row_count: int = 0,
    offset_row_count: int = 0,
    match_dump_row_count: int = 0,
    feature_row_count: int = 0,
    pair_summary_row_count: int = 0,
    parity_row_count: int = 0,
    parity_failure_count: int = 0,
    elapsed_seconds: float = 0.0,
) -> dict[str, Any]:
    requested = list(PRIMARY_DICTIONARY_CUTS)
    if DIAGNOSTIC_DICTIONARY_CUTS:
        requested.extend(DIAGNOSTIC_DICTIONARY_CUTS)
    return {
        "run_label": RUN_LABEL,
        "created_utc": _now_iso(),
        "run_mode": run_mode,
        "status": status,
        "output_dir": _repo_rel(OUTPUT_DIR),
        "report_only": REPORT_ONLY,
        "runtime_change": RUNTIME_CHANGE,
        "stage2_gate_promotion": STAGE2_GATE_PROMOTION,
        "selected_dictionaries_only": True,
        "fingerprint_mode": FINGERPRINT_MODE,
        "fingerprint_scope": FINGERPRINT_SCOPE,
        "hd_max_policy": HD_MAX_POLICY,
        "hd_bins": HD_BINS_TEXT,
        "span_lengths": list(SPAN_LENGTHS),
        "primary_sample_kinds": ["prefix_500", "middle_500", "suffix_500"],
        "comparison_sample_kinds": ["full_1000"],
        "requested_configs": requested,
        "requested_config_count": len(requested),
        "completed_config_count": len(set(completed_configs)),
        "completed_configs": sorted(set(completed_configs)),
        "missing_config_count": len(set(missing_configs)),
        "missing_configs": sorted(set(missing_configs)),
        "skipped_config_count": len(skipped_configs),
        "skipped_configs": list(skipped_configs),
        "failed_config_count": len(set(failed_configs)),
        "failed_configs": sorted(set(failed_configs)),
        "reason": "",
        "candidate_row_count": candidate_row_count,
        "offset_row_count": offset_row_count,
        "match_dump_row_count": match_dump_row_count,
        "feature_row_count": feature_row_count,
        "pair_summary_row_count": pair_summary_row_count,
        "parity_row_count": parity_row_count,
        "parity_failure_count": parity_failure_count,
        "elapsed_seconds": elapsed_seconds,
        "deviations_from_plan": [
            {
                "field": "hd_bins",
                "original": "0..span_length",
                "used": HD_BINS_TEXT,
                "reason": "hd == span_length means every token differs and is not useful scoring evidence.",
            }
        ],
    }


def _build_readout(summary: Mapping[str, Any]) -> str:
    lines = [
        "# S1g Selected-Dictionary 500-Unit Span-Hamming Fingerprint Scan v1",
        "",
        "## Purpose",
        "",
        "Collect report-only raw span-Hamming fingerprint evidence by dictionary cut, 500-token chunk, span length, and HD bin.",
        "",
        "## Inputs",
        "",
        f"- pair rows: `{S1_PAIR_ROWS_REL}`",
        f"- token rows: `{UNIQUE_PARTIAL_ROWS_REL}`",
        "",
        "## Selected dictionaries requested",
        "",
        *[f"- `{spec.dictionary_cut}` -> `{spec.dictionary_path}`" for spec in DICTIONARY_SPECS],
        "",
        "## Selected dictionaries completed / missing / failed",
        "",
        f"- completed: `{summary.get('completed_configs', [])}`",
        f"- missing: `{summary.get('missing_configs', [])}`",
        f"- failed: `{summary.get('failed_configs', [])}`",
        f"- skipped: `{summary.get('skipped_configs', [])}`",
        "",
        "## Backend used",
        "",
        "- preferred backend: `FastSpanHammingBackend.fingerprint_raw_hamming_counts`",
        "- Python reference is used only for parity checks on deterministic smoke samples.",
        "",
        "## Fast-backend parity result",
        "",
        f"- parity rows: `{summary.get('parity_row_count', 0)}`",
        f"- parity failures: `{summary.get('parity_failure_count', 0)}`",
        "",
        "## HD max policy",
        "",
        f"- `{HD_MAX_POLICY}`",
        f"- HD bins: `{HD_BINS_TEXT}`",
        "- no row with `hd == span_length` is valid.",
        "",
        "## Fingerprint scope",
        "",
        f"- `{FINGERPRINT_SCOPE}`",
        "- current scorer `raw_intervals` are not used as raw match histograms.",
        "",
        "## Fingerprint detail levels produced",
        "",
        f"- candidate/chunk rows: `{summary.get('candidate_row_count', 0)}`",
        f"- offset rows: `{summary.get('offset_row_count', 0)}`",
        f"- debug match dump rows: `{summary.get('match_dump_row_count', 0)}`",
        "",
        "## 500-token benchmark result",
        "",
        "See `span_hamming_500_unit_candidate_features.csv` and pair summaries.",
        "",
        "## Full-1000 comparison",
        "",
        "`full_1000` is kept as a separate sample basis and is not silently mixed with 500 aggregates.",
        "",
        "## HD fingerprint findings",
        "",
        "Pending run output.",
        "",
        "## Offset/island findings",
        "",
        "Offset rows are produced in canary mode and optional in full mode.",
        "",
        "## Dictionary cut comparison",
        "",
        "Pending run output.",
        "",
        "## Cap pressure result",
        "",
        "See `cap_pressure_by_dictionary_length.csv`.",
        "",
        "## Timing result",
        "",
        "See timing summary files.",
        "",
        "## Best rescue/break features",
        "",
        "Pending pair summary output.",
        "",
        "## Features rejected as noisy",
        "",
        "Pending review of pair summary output.",
        "",
        "## What remains incomplete",
        "",
        "Anything represented by placeholder files remains incomplete for this run mode.",
        "",
        "## Deviations from original S1g plan",
        "",
        "- HD bins changed from `0..span_length` to `0..max(0, span_length - 1)`.",
        "",
        "## Recommendation",
        "",
        "No runtime gate is promoted by this run. Next stage is fresh held-out validation or shadow-selector validation only.",
        "",
    ]
    return "\n".join(lines)


def run_inventory_only() -> dict[str, Any]:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    inventory = _dictionary_inventory_rows()
    missing, failed = _inventory_status(inventory)
    produced = {"selected_dictionary_inventory.csv"}
    _write_csv(OUTPUT_DIR / "selected_dictionary_inventory.csv", inventory, _inventory_fieldnames())

    config_rows = _config_summary_rows(
        run_mode="inventory_only",
        inventory_rows=inventory,
        completed=[],
        missing=missing,
        failed=failed,
        skipped=[{"dictionary_cut": spec.dictionary_cut, "reason": "inventory_only mode"} for spec in DICTIONARY_SPECS if spec.dictionary_cut not in missing and spec.dictionary_cut not in failed],
    )
    _write_csv(
        OUTPUT_DIR / "span_hamming_selected_dictionary_config_summary.csv",
        config_rows,
        list(config_rows[0].keys()) if config_rows else ["run_label"],
    )
    produced.add("span_hamming_selected_dictionary_config_summary.csv")

    summary = _summary_json(
        run_mode="inventory_only",
        status="inventory_complete",
        inventory_rows=inventory,
        completed_configs=[],
        missing_configs=missing,
        skipped_configs=[{"dictionary_cut": spec.dictionary_cut, "reason": "inventory_only mode"} for spec in DICTIONARY_SPECS if spec.dictionary_cut not in missing and spec.dictionary_cut not in failed],
        failed_configs=failed,
        elapsed_seconds=time.perf_counter() - started,
    )
    (OUTPUT_DIR / "span_hamming_selected_dictionary_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "span_hamming_selected_dictionary_readout.md").write_text(_build_readout(summary), encoding="utf-8")
    produced.update({"span_hamming_selected_dictionary_summary.json", "span_hamming_selected_dictionary_readout.md"})
    _ensure_required_placeholders(produced, reason="inventory_only mode", run_mode="inventory_only")
    return summary


def _load_wordlists_for_reference(spec: DictionarySpec) -> dict[int, list[list[int]]]:
    wordlists, _ = _load_raw1grams_wordlists(REPO_ROOT / spec.dictionary_path, build_rtl=False, require_selected=spec.require_selected)
    return wordlists


def _run_scoring_mode(run_mode: str) -> dict[str, Any]:
    if run_mode not in {"parity_smoke", "canary", "full"}:
        raise ValueError(f"unsupported scoring run_mode: {run_mode}")
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _validate_selected_only_specs()

    inventory = _dictionary_inventory_rows()
    missing, failed_inventory = _inventory_status(inventory)
    produced = {"selected_dictionary_inventory.csv"}
    _write_csv(OUTPUT_DIR / "selected_dictionary_inventory.csv", inventory, _inventory_fieldnames())

    if missing or failed_inventory:
        summary = _summary_json(
            run_mode=run_mode,
            status="incomplete_missing_or_failed_dictionary",
            inventory_rows=inventory,
            completed_configs=[],
            missing_configs=missing,
            skipped_configs=[],
            failed_configs=failed_inventory,
            elapsed_seconds=time.perf_counter() - started,
        )
        (OUTPUT_DIR / "span_hamming_selected_dictionary_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (OUTPUT_DIR / "span_hamming_selected_dictionary_readout.md").write_text(_build_readout(summary), encoding="utf-8")
        produced.update({"span_hamming_selected_dictionary_summary.json", "span_hamming_selected_dictionary_readout.md"})
        _ensure_required_placeholders(produced, reason="primary selected dictionary missing or failed", run_mode=run_mode)
        return summary

    if not _fast_span_hamming_available():
        summary = _summary_json(
            run_mode=run_mode,
            status="incomplete_fast_backend_unavailable",
            inventory_rows=inventory,
            completed_configs=[],
            missing_configs=[],
            skipped_configs=[],
            failed_configs=["fast_backend_unavailable"],
            elapsed_seconds=time.perf_counter() - started,
        )
        (OUTPUT_DIR / "span_hamming_selected_dictionary_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (OUTPUT_DIR / "span_hamming_selected_dictionary_readout.md").write_text(_build_readout(summary), encoding="utf-8")
        produced.update({"span_hamming_selected_dictionary_summary.json", "span_hamming_selected_dictionary_readout.md"})
        _ensure_required_placeholders(produced, reason="fast backend unavailable", run_mode=run_mode)
        return summary

    pair_rows_all = _read_pair_rows()
    limit = PARITY_TOKEN_HASH_LIMIT if run_mode == "parity_smoke" else CANARY_TOKEN_HASH_LIMIT if run_mode == "canary" else FULL_TOKEN_HASH_LIMIT
    required_hashes = _required_token_hashes(pair_rows_all, limit)
    tokens_by_hash = _read_token_rows(required_hashes)
    missing_token_hashes = [token_hash for token_hash in required_hashes if token_hash not in tokens_by_hash]
    samples = build_chunk_samples(tokens_by_hash)
    pair_rows = [
        row for row in pair_rows_all
        if row.get("winner_token_hash") in tokens_by_hash and row.get("challenger_token_hash") in tokens_by_hash
    ]

    if not samples:
        summary = _summary_json(
            run_mode=run_mode,
            status="incomplete_no_scoring_samples",
            inventory_rows=inventory,
            completed_configs=[],
            missing_configs=missing,
            skipped_configs=[],
            failed_configs=failed_inventory + ["token_samples_missing"],
            elapsed_seconds=time.perf_counter() - started,
        )
        summary["missing_token_hash_count"] = len(missing_token_hashes)
        summary["missing_token_hashes"] = missing_token_hashes[:100]
        (OUTPUT_DIR / "span_hamming_selected_dictionary_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (OUTPUT_DIR / "span_hamming_selected_dictionary_readout.md").write_text(_build_readout(summary), encoding="utf-8")
        produced.update({"span_hamming_selected_dictionary_summary.json", "span_hamming_selected_dictionary_readout.md"})
        _ensure_required_placeholders(produced, reason="no scoring samples were available", run_mode=run_mode)
        return summary

    include_offset_rows = CANARY_INCLUDE_OFFSET_ROWS if run_mode in {"parity_smoke", "canary"} else FULL_INCLUDE_OFFSET_ROWS
    include_match_dump = (
        MATCH_DUMP_ENABLED_FOR_CANARY if run_mode in {"parity_smoke", "canary"} else MATCH_DUMP_ENABLED_FOR_FULL
    )

    candidate_rows: list[dict[str, Any]] = []
    offset_rows: list[dict[str, Any]] = []
    match_dump_rows: list[dict[str, Any]] = []
    parity_rows: list[dict[str, Any]] = []
    parity_failure_rows: list[dict[str, Any]] = []
    completed_configs: list[str] = []
    failed_configs: list[str] = []
    skipped_configs: list[dict[str, Any]] = []

    specs_to_attempt = [spec for spec in DICTIONARY_SPECS if not (spec.diagnostic_only and run_mode == "full")]
    total_samples = len(specs_to_attempt) * len(samples)
    completed_samples = 0

    for spec in DICTIONARY_SPECS:
        if spec.diagnostic_only and run_mode == "full":
            skipped_configs.append({"dictionary_cut": spec.dictionary_cut, "reason": "diagnostic cut skipped in full mode"})
            continue
        backend, fail_reason, build_ms = _build_fast_backend(spec)
        if backend is None:
            failed_configs.append(f"{spec.dictionary_cut}:{fail_reason}")
            continue
        reference_wordlists = _load_wordlists_for_reference(spec) if run_mode == "parity_smoke" else None
        completed_configs.append(spec.dictionary_cut)
        for sample_index, sample in enumerate(samples, start=1):
            dump_this_sample = include_match_dump and sample_index <= MATCH_DUMP_TOKEN_HASH_LIMIT
            start_score = time.perf_counter()
            payload = backend.fingerprint_raw_hamming_counts(
                sample.tokens,
                include_offset_rows=include_offset_rows,
                include_match_dump=dump_this_sample,
                max_candidates_per_window=FINGERPRINT_MAX_CANDIDATES_PER_WINDOW,
            )
            score_ms = (time.perf_counter() - start_score) * 1000.0
            candidate_rows.extend(
                _candidate_fingerprint_rows(
                    spec=spec,
                    sample=sample,
                    payload=payload,
                    score_ms=score_ms,
                    backend_name="fast_span_backend",
                    build_ms=build_ms,
                )
            )
            if include_offset_rows:
                offset_rows.extend(
                    _offset_fingerprint_rows(
                        spec=spec,
                        sample=sample,
                        payload=payload,
                        score_ms=score_ms,
                        backend_name="fast_span_backend",
                    )
                )
            if dump_this_sample:
                match_dump_rows.extend(_match_dump_rows(spec=spec, sample=sample, payload=payload))

            if reference_wordlists is not None:
                expected = _reference_fingerprint_bin_map(sample.tokens, reference_wordlists)
                observed = _payload_chunk_bin_map(payload)
                mismatch_keys = sorted(key for key in set(expected) | set(observed) if expected.get(key, 0) != observed.get(key, 0))
                parity_ok = not mismatch_keys
                parity_row = {
                    "dictionary_cut": spec.dictionary_cut,
                    "token_hash": sample.token_hash,
                    "sample_kind": sample.sample_kind,
                    "sample_start": sample.sample_start,
                    "sample_length": sample.sample_length,
                    "parity_ok": int(parity_ok),
                    "mismatch_count": len(mismatch_keys),
                    "mismatch_keys": json.dumps(mismatch_keys[:20]),
                    "float_tolerance": FLOAT_TOLERANCE,
                    "backend_name": "fast_span_backend",
                    "reference_backend_name": "python_reference_bruteforce",
                }
                parity_rows.append(parity_row)
                if not parity_ok:
                    parity_failure_rows.append(parity_row)
            completed_samples += 1
            if completed_samples == 1 or completed_samples % PROGRESS_EVERY_SAMPLES == 0 or completed_samples == total_samples:
                print(
                    f"[s1g_span_hamming_fingerprint] progress samples={completed_samples}/{total_samples} "
                    f"run_mode={run_mode} dictionary_cut={spec.dictionary_cut}",
                    flush=True,
                )

    _write_csv(OUTPUT_DIR / "span_hamming_hd_fingerprint_candidate_rows.csv", candidate_rows, _candidate_fingerprint_fieldnames())
    _write_csv(OUTPUT_DIR / "span_hamming_hd_fingerprint_offset_rows.csv", offset_rows, _offset_fingerprint_fieldnames())
    _write_csv(OUTPUT_DIR / "span_hamming_hd_fingerprint_match_dump_debug.csv", match_dump_rows, _match_dump_fieldnames())
    produced.update(
        {
            "span_hamming_hd_fingerprint_candidate_rows.csv",
            "span_hamming_hd_fingerprint_offset_rows.csv",
            "span_hamming_hd_fingerprint_match_dump_debug.csv",
        }
    )

    feature_rows = _candidate_feature_rows(candidate_rows)
    _write_csv(OUTPUT_DIR / "span_hamming_500_unit_candidate_features.csv", feature_rows, _candidate_feature_fieldnames())
    produced.add("span_hamming_500_unit_candidate_features.csv")

    pair_summary_rows, pair_flag_rows = _pair_summaries(pair_rows=pair_rows, feature_rows=feature_rows)
    _write_csv(OUTPUT_DIR / "span_hamming_500_unit_pair_feature_summary.csv", pair_summary_rows, _pair_summary_fieldnames())
    _write_csv(OUTPUT_DIR / "span_hamming_500_unit_pair_flags.csv", pair_flag_rows, _pair_flag_fieldnames())
    produced.update({"span_hamming_500_unit_pair_feature_summary.csv", "span_hamming_500_unit_pair_flags.csv"})

    cap_rows = _cap_pressure_rows(candidate_rows)
    _write_csv(OUTPUT_DIR / "cap_pressure_by_dictionary_length.csv", cap_rows, _cap_pressure_fieldnames())
    produced.add("cap_pressure_by_dictionary_length.csv")

    timing_summary_rows, timing_length_rows = _timing_rows(candidate_rows)
    _write_csv(OUTPUT_DIR / "span_hamming_selected_dictionary_timing_summary.csv", timing_summary_rows, _timing_summary_fieldnames())
    _write_csv(OUTPUT_DIR / "span_hamming_selected_dictionary_timing_by_length.csv", timing_length_rows, _timing_by_length_fieldnames())
    produced.update({"span_hamming_selected_dictionary_timing_summary.csv", "span_hamming_selected_dictionary_timing_by_length.csv"})

    _write_csv(
        OUTPUT_DIR / "fast_backend_parity_summary.csv",
        parity_rows,
        [
            "dictionary_cut",
            "token_hash",
            "sample_kind",
            "sample_start",
            "sample_length",
            "parity_ok",
            "mismatch_count",
            "mismatch_keys",
            "float_tolerance",
            "backend_name",
            "reference_backend_name",
        ],
    )
    _write_csv(
        OUTPUT_DIR / "fast_backend_parity_failures.csv",
        parity_failure_rows,
        [
            "dictionary_cut",
            "token_hash",
            "sample_kind",
            "sample_start",
            "sample_length",
            "parity_ok",
            "mismatch_count",
            "mismatch_keys",
            "float_tolerance",
            "backend_name",
            "reference_backend_name",
        ],
    )
    (OUTPUT_DIR / "fast_backend_parity_readout.md").write_text(
        "\n".join(
            [
                "# Fast Backend Parity Readout",
                "",
                f"- run_mode: `{run_mode}`",
                f"- parity rows: `{len(parity_rows)}`",
                f"- parity failures: `{len(parity_failure_rows)}`",
                f"- float tolerance: `{FLOAT_TOLERANCE}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    produced.update({"fast_backend_parity_summary.csv", "fast_backend_parity_failures.csv", "fast_backend_parity_readout.md"})

    config_rows = _config_summary_rows(
        run_mode=run_mode,
        inventory_rows=inventory,
        completed=completed_configs,
        missing=missing,
        failed=failed_inventory + failed_configs,
        skipped=skipped_configs,
    )
    _write_csv(OUTPUT_DIR / "span_hamming_selected_dictionary_config_summary.csv", config_rows, list(config_rows[0].keys()))
    produced.add("span_hamming_selected_dictionary_config_summary.csv")

    summary = _summary_json(
        run_mode=run_mode,
        status="complete" if not parity_failure_rows and not failed_configs else "complete_with_failures",
        inventory_rows=inventory,
        completed_configs=completed_configs,
        missing_configs=missing,
        skipped_configs=skipped_configs,
        failed_configs=failed_inventory + failed_configs,
        candidate_row_count=len(candidate_rows),
        offset_row_count=len(offset_rows),
        match_dump_row_count=len(match_dump_rows),
        feature_row_count=len(feature_rows),
        pair_summary_row_count=len(pair_summary_rows),
        parity_row_count=len(parity_rows),
        parity_failure_count=len(parity_failure_rows),
        elapsed_seconds=time.perf_counter() - started,
    )
    summary["missing_token_hash_count"] = len(missing_token_hashes)
    summary["missing_token_hashes"] = missing_token_hashes[:100]
    (OUTPUT_DIR / "span_hamming_selected_dictionary_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "span_hamming_selected_dictionary_readout.md").write_text(_build_readout(summary), encoding="utf-8")
    produced.update({"span_hamming_selected_dictionary_summary.json", "span_hamming_selected_dictionary_readout.md"})
    _ensure_required_placeholders(produced, reason="not produced by scoring mode", run_mode=run_mode)
    return summary


def main() -> None:
    if RUN_MODE == "inventory_only":
        summary = run_inventory_only()
    elif RUN_MODE in {"parity_smoke", "canary", "full"}:
        summary = _run_scoring_mode(RUN_MODE)
    else:
        raise ValueError(f"unknown RUN_MODE: {RUN_MODE}")
    print(
        f"[s1g_span_hamming_fingerprint] done mode={summary['run_mode']} "
        f"status={summary['status']} output={summary['output_dir']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
