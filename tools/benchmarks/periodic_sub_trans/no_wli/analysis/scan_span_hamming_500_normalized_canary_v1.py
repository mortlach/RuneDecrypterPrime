from __future__ import annotations

"""
Report-only 500-token span-Hamming normalized feature canary.

No CLI arguments. Edit constants below. This canary proves the pipeline before a
larger fixed-500 scan:

- score deterministic 500-token chunks, not full 1000-token candidates;
- use absolute max_hd only as a backend retrieval ceiling;
- compute length-scaled error-rate features;
- write candidate rows and run state incrementally.
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


RUN_LABEL = "span_hamming_500_normalized_canary_v1"

S1_PAIR_ROWS_REL = (
    "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/source/historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"
)
UNIQUE_PARTIAL_ROWS_REL = (
    "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/source/historical_partial_text_review_v1/unique_partial_text_rows.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_normalized_canary_v1"
)

CHUNK_LENGTH = 500
CHUNK_KINDS = ("prefix", "middle", "suffix")
TOKEN_HASH_LIMIT_FOR_CANARY = 80
PROGRESS_EVERY_SAMPLES = 50

PARITY_SPOT_CHECK = True
PARITY_CONFIG_LIMIT = 2
PARITY_SAMPLE_LIMIT = 2


SPAN_CONFIG_SPECS = (
    dict(
        config_id="raw_selected_len3_14_hd2_cap256_norm500",
        dictionary_id="raw_selected",
        wordlist_rel="assets/hamming_raw_1g",
        require_selected=True,
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
    ),
    dict(
        config_id="strict_selected_len3_14_hd2_cap256_norm500",
        dictionary_id="strict_selected",
        wordlist_rel="assets/hamming_dictionary_policies/strict/hamming_raw_1g",
        require_selected=True,
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
    ),
    dict(
        config_id="research_selected_len3_14_hd2_cap256_norm500",
        dictionary_id="research_selected",
        wordlist_rel="assets/hamming_dictionary_policies/research/hamming_raw_1g",
        require_selected=True,
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
    ),
)


FEATURE_DIRECTIONS = {
    "exact_len_ge_5_norm": "higher",
    "exact_len_ge_8_norm": "higher",
    "err10_len_ge_8_norm": "higher",
    "err15_len_ge_8_norm": "higher",
    "err20_len_ge_5_norm": "higher",
    "err20_len_ge_10_norm": "higher",
    "err20_len_ge_12_norm": "higher",
    "weighted_err20_gamma2_len_ge_5_norm": "higher",
    "weighted_err15_gamma3_len_ge_8_norm": "higher",
    "selected_interval_count_norm": "higher",
    "short_fuzzy_noise_len_le_4_norm": "lower",
    "short_fuzzy_interval_count_norm": "lower",
    "candidate_cap_pruned_rate": "lower",
}


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

from rune_decrypter_prime.scoring.span_hamming.backend import SpanHammingBackend  # noqa: E402
from rune_decrypter_prime.scoring.span_hamming.fast_backend import (  # noqa: E402
    FastSpanHammingBackend,
    fast_span_hamming_available,
)
from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig, SpanHammingStats  # noqa: E402


S1_PAIR_ROWS = REPO_ROOT / S1_PAIR_ROWS_REL
UNIQUE_PARTIAL_ROWS = REPO_ROOT / UNIQUE_PARTIAL_ROWS_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


@dataclass(frozen=True)
class SpanSpec:
    config_id: str
    dictionary_id: str
    wordlist_rel: str
    require_selected: bool
    len_min: int
    len_max: int
    max_hd: int
    max_candidates_per_window: int


@dataclass(frozen=True)
class ChunkSample:
    token_hash: str
    chunk_kind: str
    start: int
    end: int
    tokens: tuple[int, ...]

    @property
    def sample_id(self) -> str:
        return f"{self.token_hash}::{self.chunk_kind}_{self.start}_{self.end}"


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


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


def _chunk_starts(length: int) -> dict[str, int]:
    if length < CHUNK_LENGTH:
        return {}
    return {
        "prefix": 0,
        "middle": max(0, (length - CHUNK_LENGTH) // 2),
        "suffix": length - CHUNK_LENGTH,
    }


def build_chunk_samples(tokens_by_hash: Mapping[str, Sequence[int]]) -> list[ChunkSample]:
    out: list[ChunkSample] = []
    for token_hash, tokens_seq in tokens_by_hash.items():
        tokens = tuple(int(v) for v in tokens_seq)
        for chunk_kind in CHUNK_KINDS:
            start = _chunk_starts(len(tokens)).get(chunk_kind)
            if start is None:
                continue
            end = start + CHUNK_LENGTH
            out.append(
                ChunkSample(
                    token_hash=token_hash,
                    chunk_kind=chunk_kind,
                    start=start,
                    end=end,
                    tokens=tokens[start:end],
                )
            )
    return out


def _span_config(spec: SpanSpec) -> SpanHammingConfig:
    return SpanHammingConfig(
        len_min=spec.len_min,
        len_max=spec.len_max,
        max_hd=spec.max_hd,
        max_candidates_per_window=spec.max_candidates_per_window,
        debug_return_intervals=True,
    )


def _build_fast_backend(spec: SpanSpec) -> tuple[FastSpanHammingBackend | None, str, float]:
    wordlist_dir = REPO_ROOT / spec.wordlist_rel
    if not wordlist_dir.exists():
        return None, f"missing_wordlist_dir:{spec.wordlist_rel}", 0.0
    start = time.perf_counter()
    backend = FastSpanHammingBackend(
        config=_span_config(spec),
        wordlist_dir=wordlist_dir,
        require_selected=spec.require_selected,
        return_raw_intervals=True,
    )
    return backend, "", (time.perf_counter() - start) * 1000.0


def _build_python_backend(spec: SpanSpec) -> SpanHammingBackend:
    return SpanHammingBackend(
        config=_span_config(spec),
        wordlist_dir=REPO_ROOT / spec.wordlist_rel,
        require_selected=spec.require_selected,
    )


def _score_payload(backend: FastSpanHammingBackend, tokens: Sequence[int]) -> tuple[dict[str, Any], float]:
    start = time.perf_counter()
    payload = backend.score_payload(tokens)
    return payload, (time.perf_counter() - start) * 1000.0


def _error_rate(distance: int, length: int) -> float:
    if length < 1:
        raise ValueError("length must be >= 1")
    return float(distance) / float(length)


def _interval_weight(length: int, distance: int, gamma: float) -> float:
    return float(length) * ((1.0 - _error_rate(distance, length)) ** gamma)


def _empty_features() -> dict[str, float]:
    return {name: 0.0 for name in FEATURE_DIRECTIONS}


def _normalized_features(payload: Mapping[str, Any], token_length: int) -> dict[str, float]:
    features = _empty_features()
    selected_intervals = [dict(row) for row in payload.get("selected_intervals", [])]
    n_considered = int(payload.get("n_candidates_considered", 0) or 0)
    n_pruned = int(payload.get("n_candidates_pruned_cap", 0) or 0)
    features["candidate_cap_pruned_rate"] = float(n_pruned) / float(max(1, n_pruned + n_considered))

    denom = float(max(1, token_length))
    for interval in selected_intervals:
        length = int(interval["length"])
        distance = int(interval["distance"])
        rate = _error_rate(distance, length)

        if distance == 0 and length >= 5:
            features["exact_len_ge_5_norm"] += float(length) / denom
        if distance == 0 and length >= 8:
            features["exact_len_ge_8_norm"] += float(length) / denom
        if rate <= 0.10 and length >= 8:
            features["err10_len_ge_8_norm"] += _interval_weight(length, distance, 2.0) / denom
        if rate <= 0.15 and length >= 8:
            features["err15_len_ge_8_norm"] += _interval_weight(length, distance, 2.0) / denom
            features["weighted_err15_gamma3_len_ge_8_norm"] += _interval_weight(length, distance, 3.0) / denom
        if rate <= 0.20 and length >= 5:
            features["err20_len_ge_5_norm"] += _interval_weight(length, distance, 2.0) / denom
            features["weighted_err20_gamma2_len_ge_5_norm"] += _interval_weight(length, distance, 2.0) / denom
        if rate <= 0.20 and length >= 10:
            features["err20_len_ge_10_norm"] += _interval_weight(length, distance, 2.0) / denom
        if rate <= 0.20 and length >= 12:
            features["err20_len_ge_12_norm"] += _interval_weight(length, distance, 2.0) / denom
        if length <= 4 and distance > 0:
            features["short_fuzzy_noise_len_le_4_norm"] += float(length) * rate / denom
            features["short_fuzzy_interval_count_norm"] += 1.0 / denom

    features["selected_interval_count_norm"] = float(len(selected_intervals)) / denom
    return features


def _candidate_row(
    *,
    spec: SpanSpec,
    sample: ChunkSample,
    payload: Mapping[str, Any],
    elapsed_ms: float,
    build_ms: float,
) -> dict[str, Any]:
    n_considered = int(payload.get("n_candidates_considered", 0) or 0)
    n_pruned = int(payload.get("n_candidates_pruned_cap", 0) or 0)
    row: dict[str, Any] = {
        "run_label": RUN_LABEL,
        "config_id": spec.config_id,
        "dictionary_id": spec.dictionary_id,
        "wordlist_rel": spec.wordlist_rel,
        "require_selected": int(spec.require_selected),
        "len_min": spec.len_min,
        "len_max": spec.len_max,
        "max_hd": spec.max_hd,
        "max_candidates_per_window": spec.max_candidates_per_window,
        "token_hash": sample.token_hash,
        "sample_id": sample.sample_id,
        "chunk_kind": sample.chunk_kind,
        "chunk_start": sample.start,
        "chunk_end": sample.end,
        "token_length": len(sample.tokens),
        "span_raw_current": float(payload["span_raw"]),
        "span_coverage_current": float(payload["coverage"]),
        "span_quality_current": float(payload["quality"]),
        "selected_interval_count": int(payload["n_intervals_selected"]),
        "raw_interval_count": len(list(payload.get("raw_intervals", []))),
        "n_windows_total": int(payload["n_windows_total"]),
        "n_windows_scored": int(payload["n_windows_scored"]),
        "n_candidates_considered": n_considered,
        "n_candidates_pruned_cap": n_pruned,
        "score_elapsed_ms": f"{elapsed_ms:.6f}",
        "backend_build_ms": f"{build_ms:.6f}",
    }
    row.update({key: f"{value:.12g}" for key, value in _normalized_features(payload, len(sample.tokens)).items()})
    return row


def _candidate_fieldnames() -> list[str]:
    return [
        "run_label",
        "config_id",
        "dictionary_id",
        "wordlist_rel",
        "require_selected",
        "len_min",
        "len_max",
        "max_hd",
        "max_candidates_per_window",
        "token_hash",
        "sample_id",
        "chunk_kind",
        "chunk_start",
        "chunk_end",
        "token_length",
        "span_raw_current",
        "span_coverage_current",
        "span_quality_current",
        "selected_interval_count",
        "raw_interval_count",
        "n_windows_total",
        "n_windows_scored",
        "n_candidates_considered",
        "n_candidates_pruned_cap",
        "score_elapsed_ms",
        "backend_build_ms",
        *FEATURE_DIRECTIONS.keys(),
    ]


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _append_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    count = 0
    with path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def _safe_float(value: object) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def _feature_preference(direction: str, winner_value: object, challenger_value: object) -> str:
    winner = _safe_float(winner_value)
    challenger = _safe_float(challenger_value)
    if winner is None or challenger is None:
        return "no_decision"
    if abs(winner - challenger) <= 1e-12:
        return "tie"
    if direction == "higher":
        return "truth_better" if winner > challenger else "truth_worse"
    if direction == "lower":
        return "truth_better" if winner < challenger else "truth_worse"
    raise ValueError(f"unknown direction: {direction}")


def build_pair_summaries(
    *,
    pair_rows: Sequence[Mapping[str, str]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_key = {
        (str(row["config_id"]), str(row["token_hash"]), str(row["chunk_kind"])): row
        for row in candidate_rows
    }
    config_ids = sorted({str(row["config_id"]) for row in candidate_rows})
    out: list[dict[str, Any]] = []
    for config_id in config_ids:
        for chunk_kind in CHUNK_KINDS:
            for feature_name, direction in FEATURE_DIRECTIONS.items():
                row = {
                    "config_id": config_id,
                    "chunk_kind": chunk_kind,
                    "feature_name": feature_name,
                    "feature_direction": direction,
                    "pair_count": 0,
                    "available_pair_count": 0,
                    "no_decision": 0,
                    "truth_better": 0,
                    "truth_worse": 0,
                    "tie": 0,
                    "rescues": 0,
                    "breaks": 0,
                    "current_misranked_pair_count": 0,
                    "current_correct_control_pair_count": 0,
                    "unique_misranked_rescue_pair_count": 0,
                    "unique_control_break_pair_count": 0,
                }
                rescue_pairs: set[str] = set()
                break_pairs: set[str] = set()
                for pair in pair_rows:
                    winner_hash = str(pair.get("winner_token_hash", "")).strip()
                    challenger_hash = str(pair.get("challenger_token_hash", "")).strip()
                    winner = by_key.get((config_id, winner_hash, chunk_kind))
                    challenger = by_key.get((config_id, challenger_hash, chunk_kind))
                    if winner is None or challenger is None:
                        continue
                    current_correct = str(pair.get("current_score_correct", "")).strip() == "1"
                    pair_id = str(pair.get("pair_id", f"{winner_hash}|{challenger_hash}"))
                    pref = _feature_preference(direction, winner.get(feature_name), challenger.get(feature_name))
                    row["pair_count"] += 1
                    if pref == "no_decision":
                        row["no_decision"] += 1
                        continue
                    row["available_pair_count"] += 1
                    row[pref] += 1
                    if current_correct:
                        row["current_correct_control_pair_count"] += 1
                        if pref == "truth_worse":
                            row["breaks"] += 1
                            break_pairs.add(pair_id)
                    else:
                        row["current_misranked_pair_count"] += 1
                        if pref == "truth_better":
                            row["rescues"] += 1
                            rescue_pairs.add(pair_id)
                row["net"] = int(row["rescues"]) - int(row["breaks"])
                row["unique_misranked_rescue_pair_count"] = len(rescue_pairs)
                row["unique_control_break_pair_count"] = len(break_pairs)
                out.append(row)
    out.sort(key=lambda item: (str(item["config_id"]), str(item["chunk_kind"]), str(item["feature_name"])))
    return out


def _timing_summary(candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[float]] = {}
    for row in candidate_rows:
        value = _safe_float(row.get("score_elapsed_ms"))
        if value is None:
            continue
        key = (str(row["config_id"]), str(row["chunk_kind"]))
        grouped.setdefault(key, []).append(value)
    out = []
    for (config_id, chunk_kind), values in sorted(grouped.items()):
        out.append(
            {
                "config_id": config_id,
                "chunk_kind": chunk_kind,
                "row_count": len(values),
                "mean_ms": f"{mean(values):.6f}",
                "median_ms": f"{median(values):.6f}",
                "max_ms": f"{max(values):.6f}",
            }
        )
    return out


def _stats_compare(left: SpanHammingStats, right: SpanHammingStats) -> list[str]:
    fields = (
        "span_raw",
        "coverage",
        "quality",
        "n_chars",
        "chars_covered",
        "n_intervals_selected",
        "length_bins",
        "span_raw_by_len",
        "coverage_by_len",
        "quality_by_len",
        "selected_intervals_by_len",
        "chars_covered_by_len",
        "n_windows_total",
        "n_windows_scored",
        "n_candidates_considered",
        "n_candidates_pruned_cap",
        "selected_intervals",
    )
    mismatches: list[str] = []
    for field in fields:
        l_val = getattr(left, field)
        r_val = getattr(right, field)
        if isinstance(l_val, float):
            if abs(l_val - float(r_val)) > 1e-12:
                mismatches.append(field)
        elif isinstance(l_val, tuple) and l_val and isinstance(l_val[0], float):
            if len(l_val) != len(r_val) or any(abs(float(a) - float(b)) > 1e-12 for a, b in zip(l_val, r_val)):
                mismatches.append(field)
        elif l_val != r_val:
            mismatches.append(field)
    return mismatches


def _write_run_state(path: Path, state: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(state), indent=2, sort_keys=True), encoding="utf-8")


def _build_readout(summary: Mapping[str, Any], best_rows: Sequence[Mapping[str, Any]]) -> str:
    coverage_note = "Canary subset only." if int(summary["token_hash_limit_for_canary"]) else "Full configured token-hash set."
    lines = [
        "# Span-Hamming 500 Normalized Canary v1",
        "",
        "## Status",
        "",
        "- Report-only; no runtime behaviour changed.",
        f"- candidate rows: `{summary['candidate_row_count']}`",
        f"- pair summary rows: `{summary['pair_summary_row_count']}`",
        f"- parity failures: `{summary['parity_failure_count']}`",
        f"- elapsed seconds: `{float(summary['elapsed_seconds']):.2f}`",
        "",
        "## Best Rows",
        "",
        "| config | chunk | feature | rescues | breaks | net | unique rescues | unique breaks |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in best_rows[:15]:
        lines.append(
            f"| {row['config_id']} | {row['chunk_kind']} | {row['feature_name']} | "
            f"{row['rescues']} | {row['breaks']} | {row['net']} | "
            f"{row['unique_misranked_rescue_pair_count']} | {row['unique_control_break_pair_count']} |"
        )
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            f"- {coverage_note}",
            "- Fixed 500-token chunks only.",
            "- Absolute `max_hd` is only the backend retrieval ceiling.",
            "- Feature decisions are normalized by chunk length and filtered by error rate.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_canary() -> dict[str, Any]:
    if not fast_span_hamming_available():
        raise RuntimeError("optional _span_hamming_fast extension is not built")

    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidate_path = OUTPUT_DIR / "span_hamming_500_normalized_candidate_features.csv"
    pair_summary_path = OUTPUT_DIR / "span_hamming_500_normalized_pair_feature_summary.csv"
    timing_path = OUTPUT_DIR / "span_hamming_500_normalized_timing_summary.csv"
    config_path = OUTPUT_DIR / "span_hamming_500_normalized_config_summary.csv"
    parity_path = OUTPUT_DIR / "span_hamming_500_normalized_parity_spot_check.csv"
    state_path = OUTPUT_DIR / "span_hamming_500_normalized_run_state.json"

    for path in (candidate_path, pair_summary_path, timing_path, config_path, parity_path):
        if path.exists():
            path.unlink()

    pair_rows_all = _read_pair_rows()
    required_hashes = _required_token_hashes(pair_rows_all, TOKEN_HASH_LIMIT_FOR_CANARY)
    tokens_by_hash = _read_token_rows(required_hashes)
    samples = build_chunk_samples(tokens_by_hash)
    pair_rows = [
        row for row in pair_rows_all
        if row.get("winner_token_hash") in tokens_by_hash and row.get("challenger_token_hash") in tokens_by_hash
    ]
    specs = [SpanSpec(**row) for row in SPAN_CONFIG_SPECS]

    _write_csv(config_path, [asdict(spec) for spec in specs], list(asdict(specs[0]).keys()))
    total_work = len(specs) * len(samples)
    print(
        f"[span_hamming_500_normalized_canary] start token_hashes={len(tokens_by_hash)} "
        f"samples={len(samples)} pairs={len(pair_rows)} configs={len(specs)} total_scores={total_work}",
        flush=True,
    )

    candidate_rows: list[dict[str, Any]] = []
    parity_rows: list[dict[str, Any]] = []
    completed = 0
    config_elapsed: dict[str, float] = {}

    for config_index, spec in enumerate(specs, start=1):
        backend, missing_reason, build_ms = _build_fast_backend(spec)
        if backend is None:
            raise RuntimeError(missing_reason)
        python_backend = _build_python_backend(spec) if PARITY_SPOT_CHECK and config_index <= PARITY_CONFIG_LIMIT else None
        config_started = time.perf_counter()
        batch_rows: list[dict[str, Any]] = []

        for sample_index, sample in enumerate(samples, start=1):
            payload, elapsed_ms = _score_payload(backend, sample.tokens)
            row = _candidate_row(
                spec=spec,
                sample=sample,
                payload=payload,
                elapsed_ms=elapsed_ms,
                build_ms=build_ms,
            )
            batch_rows.append(row)
            candidate_rows.append(row)

            if python_backend is not None and sample_index <= PARITY_SAMPLE_LIMIT:
                py_stats = python_backend.score(sample.tokens)
                fast_stats = backend.score(sample.tokens)
                mismatches = _stats_compare(py_stats, fast_stats)
                parity_rows.append(
                    {
                        "config_id": spec.config_id,
                        "sample_id": sample.sample_id,
                        "parity_ok": 1 if not mismatches else 0,
                        "mismatch_fields": ";".join(mismatches),
                    }
                )

            completed += 1
            if completed == 1 or completed % PROGRESS_EVERY_SAMPLES == 0 or completed == total_work:
                elapsed = time.perf_counter() - started
                rate = completed / elapsed if elapsed > 0.0 else 0.0
                eta = (total_work - completed) / rate if rate > 0.0 else 0.0
                print(
                    f"[span_hamming_500_normalized_canary] progress {completed}/{total_work} "
                    f"elapsed={elapsed/60.0:.2f}m eta={eta/60.0:.2f}m last_config={spec.config_id}",
                    flush=True,
                )

        _append_csv(candidate_path, batch_rows, _candidate_fieldnames())
        config_elapsed[spec.config_id] = time.perf_counter() - config_started
        _write_run_state(
            state_path,
            {
                "run_label": RUN_LABEL,
                "status": "running",
                "completed_scores": completed,
                "total_scores": total_work,
                "last_completed_config": spec.config_id,
                "candidate_rows_written": len(candidate_rows),
                "updated_utc": datetime.now(timezone.utc).isoformat(),
            },
        )

    pair_summary_rows = build_pair_summaries(pair_rows=pair_rows, candidate_rows=candidate_rows)
    best_rows = sorted(pair_summary_rows, key=lambda row: (int(row["net"]), int(row["rescues"])), reverse=True)
    timing_rows = _timing_summary(candidate_rows)

    _write_csv(
        pair_summary_path,
        pair_summary_rows,
        [
            "config_id",
            "chunk_kind",
            "feature_name",
            "feature_direction",
            "pair_count",
            "available_pair_count",
            "no_decision",
            "truth_better",
            "truth_worse",
            "tie",
            "rescues",
            "breaks",
            "net",
            "current_misranked_pair_count",
            "current_correct_control_pair_count",
            "unique_misranked_rescue_pair_count",
            "unique_control_break_pair_count",
        ],
    )
    _write_csv(timing_path, timing_rows, ["config_id", "chunk_kind", "row_count", "mean_ms", "median_ms", "max_ms"])
    _write_csv(parity_path, parity_rows, ["config_id", "sample_id", "parity_ok", "mismatch_fields"])

    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": _repo_rel(OUTPUT_DIR),
        "chunk_length": CHUNK_LENGTH,
        "chunk_kinds": list(CHUNK_KINDS),
        "token_hash_limit_for_canary": TOKEN_HASH_LIMIT_FOR_CANARY,
        "token_hash_count": len(tokens_by_hash),
        "chunk_sample_count": len(samples),
        "pair_row_count": len(pair_rows),
        "source_pair_row_count": len(pair_rows_all),
        "config_count": len(specs),
        "candidate_row_count": len(candidate_rows),
        "pair_summary_row_count": len(pair_summary_rows),
        "parity_row_count": len(parity_rows),
        "parity_failure_count": sum(1 for row in parity_rows if int(row["parity_ok"]) != 1),
        "elapsed_seconds": time.perf_counter() - started,
        "config_elapsed_seconds": {key: round(value, 6) for key, value in config_elapsed.items()},
        "top_net_rows": best_rows[:20],
        "candidate_features_csv": _repo_rel(candidate_path),
        "pair_feature_summary_csv": _repo_rel(pair_summary_path),
        "timing_summary_csv": _repo_rel(timing_path),
        "parity_spot_check_csv": _repo_rel(parity_path),
        "caveats": [
            "report-only; no runtime solver behaviour changed",
            "canary subset only" if TOKEN_HASH_LIMIT_FOR_CANARY else "full configured token-hash set",
            "fixed 500-token chunk evaluation",
            "absolute max_hd is used only as backend retrieval ceiling",
        ],
    }
    (OUTPUT_DIR / "span_hamming_500_normalized_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "span_hamming_500_normalized_readout.md").write_text(
        _build_readout(summary, best_rows),
        encoding="utf-8",
    )
    _write_run_state(
        state_path,
        {
            "run_label": RUN_LABEL,
            "status": "complete",
            "completed_scores": completed,
            "total_scores": total_work,
            "candidate_rows_written": len(candidate_rows),
            "summary_json": "span_hamming_500_normalized_summary.json",
            "updated_utc": datetime.now(timezone.utc).isoformat(),
        },
    )
    return summary


def main() -> None:
    summary = run_canary()
    print(
        "[span_hamming_500_normalized_canary] done "
        f"scores={summary['candidate_row_count']} "
        f"pairs={summary['pair_row_count']} "
        f"parity_failures={summary['parity_failure_count']} "
        f"elapsed={summary['elapsed_seconds']:.2f}s "
        f"output={summary['output_dir']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
