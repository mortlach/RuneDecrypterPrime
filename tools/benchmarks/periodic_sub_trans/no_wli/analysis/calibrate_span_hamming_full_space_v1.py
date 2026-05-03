from __future__ import annotations

"""
Report-only S1f span-Hamming calibration run.

No runtime solver behaviour changes. No CLI arguments. Edit constants below.
"""

import csv
import json
import math
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence


RUN_LABEL = "span_hamming_full_calibration_v1"

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
    "span_hamming_full_calibration_v1"
)

# Canary passed; 0 means all S1 token hashes.
TOKEN_HASH_LIMIT_FOR_DEV_SMOKE = 0
PROGRESS_EVERY_CANDIDATES = 50

# Timing/distribution only. Chunks are not truth-labelled pair examples.
TIMING_SAMPLE_TOKEN_LIMIT = 24
TIMING_CHUNK_LENGTHS = (300, 500, 1000)
TIMING_CHUNK_KINDS = ("prefix", "middle", "suffix")

# Start conservative. 2048 can be enabled after canary timing if useful.
CANDIDATE_CAPS = (256, 512, 1024)
INCLUDE_CAP_2048 = False

DICTIONARY_SPECS = (
    dict(dictionary_id="raw_selected", wordlist_rel="assets/hamming_raw_1g", require_selected=True),
    dict(dictionary_id="raw_all", wordlist_rel="assets/hamming_raw_1g", require_selected=False),
    dict(
        dictionary_id="strict_selected",
        wordlist_rel="assets/hamming_dictionary_policies/strict/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        dictionary_id="strict_all",
        wordlist_rel="assets/hamming_dictionary_policies/strict/hamming_raw_1g",
        require_selected=False,
    ),
    dict(
        dictionary_id="normal_selected",
        wordlist_rel="assets/hamming_dictionary_policies/normal/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        dictionary_id="normal_all",
        wordlist_rel="assets/hamming_dictionary_policies/normal/hamming_raw_1g",
        require_selected=False,
    ),
    dict(
        dictionary_id="broad_selected",
        wordlist_rel="assets/hamming_dictionary_policies/broad/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        dictionary_id="broad_all",
        wordlist_rel="assets/hamming_dictionary_policies/broad/hamming_raw_1g",
        require_selected=False,
    ),
    dict(
        dictionary_id="research_selected",
        wordlist_rel="assets/hamming_dictionary_policies/research/hamming_raw_1g",
        require_selected=True,
    ),
)

# These are backend scans. Intervals expose best-distance evidence under max_hd,
# not every possible dictionary-entry comparison.
SPAN_TEMPLATE_SPECS = (
    dict(template_id="len1_14_hd0_exact", len_min=1, len_max=14, max_hd=0),
    dict(template_id="len1_14_hd1", len_min=1, len_max=14, max_hd=1),
    dict(template_id="len1_14_hd2", len_min=1, len_max=14, max_hd=2),
    dict(template_id="len1_14_hd3", len_min=1, len_max=14, max_hd=3),
    dict(template_id="len3_14_hd2_s1b_shape", len_min=3, len_max=14, max_hd=2),
    dict(template_id="len5_14_hd2_longer", len_min=5, len_max=14, max_hd=2),
    dict(template_id="len8_14_hd2_long_signal", len_min=8, len_max=14, max_hd=2),
    dict(template_id="len10_14_hd2_very_long_signal", len_min=10, len_max=14, max_hd=2),
    dict(template_id="len1_4_hd2_short_noise", len_min=1, len_max=4, max_hd=2),
)

PYTHON_PARITY_SPOT_CHECK = True
PYTHON_PARITY_TOKEN_LIMIT = 4
PYTHON_PARITY_CONFIG_LIMIT = 3


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root")


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
class DictionarySpec:
    dictionary_id: str
    wordlist_rel: str
    require_selected: bool


@dataclass(frozen=True)
class SpanTemplateSpec:
    template_id: str
    len_min: int
    len_max: int
    max_hd: int


@dataclass(frozen=True)
class SpanConfigSpec:
    config_id: str
    dictionary_id: str
    wordlist_rel: str
    require_selected: bool
    template_id: str
    len_min: int
    len_max: int
    max_hd: int
    max_candidates_per_window: int


FEATURE_DIRECTIONS = {
    "span_raw_selected_current": "higher",
    "span_coverage_selected": "higher",
    "span_quality_selected_current": "higher",
    "span_interval_count_selected": "higher",
    "span_raw_interval_weight_current": "higher",
    "span_raw_interval_weight_len_norm": "higher",
    "span_raw_interval_weight_gamma_1_5": "higher",
    "span_raw_interval_weight_gamma_2_0": "higher",
    "span_raw_interval_weight_gamma_3_0": "higher",
    "span_raw_interval_weight_beta_1_25": "higher",
    "span_raw_interval_weight_beta_1_5": "higher",
    "exact_weight_len_ge_5": "higher",
    "exact_weight_len_ge_8": "higher",
    "low_error_weight_len_ge_5": "higher",
    "low_error_weight_len_ge_8": "higher",
    "low_error_weight_len_ge_10": "higher",
    "long_low_error_weight_len_ge_8": "higher",
    "long_low_error_weight_len_ge_10": "higher",
    "long_low_error_weight_len_ge_12": "higher",
    "short_weak_weight_len_le_4_error_gt_025": "lower",
    "short_weak_interval_count": "lower",
    "long_low_error_ratio": "higher",
    "short_weak_ratio": "lower",
    "exact_to_approx_ratio": "higher",
    "candidate_cap_pruned_rate": "lower",
}


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


def _safe_float(value: object) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


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
    missing = [token_hash for token_hash in required_hashes if token_hash not in loaded]
    if missing:
        raise RuntimeError(f"missing required S1 token rows: {len(missing)}")
    return {token_hash: loaded[token_hash] for token_hash in required_hashes}


def _config_specs() -> list[SpanConfigSpec]:
    caps = tuple(CANDIDATE_CAPS) + ((2048,) if INCLUDE_CAP_2048 else tuple())
    out: list[SpanConfigSpec] = []
    for dict_spec in [DictionarySpec(**row) for row in DICTIONARY_SPECS]:
        for template in [SpanTemplateSpec(**row) for row in SPAN_TEMPLATE_SPECS]:
            for cap in caps:
                config_id = f"{dict_spec.dictionary_id}__{template.template_id}__cap{cap}"
                out.append(
                    SpanConfigSpec(
                        config_id=config_id,
                        dictionary_id=dict_spec.dictionary_id,
                        wordlist_rel=dict_spec.wordlist_rel,
                        require_selected=dict_spec.require_selected,
                        template_id=template.template_id,
                        len_min=template.len_min,
                        len_max=template.len_max,
                        max_hd=template.max_hd,
                        max_candidates_per_window=int(cap),
                    )
                )
    return out


def _span_config(spec: SpanConfigSpec) -> SpanHammingConfig:
    return SpanHammingConfig(
        len_min=spec.len_min,
        len_max=spec.len_max,
        max_hd=spec.max_hd,
        max_candidates_per_window=spec.max_candidates_per_window,
        debug_return_intervals=True,
    )


def _build_fast_backend(spec: SpanConfigSpec) -> tuple[FastSpanHammingBackend | None, str, float]:
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


def _build_python_backend(spec: SpanConfigSpec) -> SpanHammingBackend:
    return SpanHammingBackend(
        config=_span_config(spec),
        wordlist_dir=REPO_ROOT / spec.wordlist_rel,
        require_selected=spec.require_selected,
    )


def _error_rate(distance: int, length: int) -> float:
    if length < 1:
        raise ValueError("span length must be >= 1")
    if distance < 0 or distance > length:
        raise ValueError("hamming distance must be in 0..span_length")
    return float(distance) / float(length)


def _error_bucket(distance: int, length: int) -> str:
    rate = _error_rate(distance, length)
    if distance == 0:
        return "exact"
    if rate <= 0.10:
        return "very_low_error"
    if rate <= 0.15:
        return "low_error"
    if rate <= 0.20:
        return "medium_low_error"
    if rate <= 0.25:
        return "medium_error"
    if rate <= 0.33:
        return "high_error"
    return "very_high_error"


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
    raise ValueError(f"unknown feature direction: {direction}")


def _interval_dicts(payload: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    return [dict(row) for row in payload.get(key, [])]


def _interval_weight_len_norm(interval: Mapping[str, Any]) -> float:
    length = int(interval["length"])
    distance = int(interval["distance"])
    return float(length) * (1.0 - _error_rate(distance, length))


def _interval_weight_gamma(interval: Mapping[str, Any], gamma: float) -> float:
    length = int(interval["length"])
    distance = int(interval["distance"])
    return float(length) * ((1.0 - _error_rate(distance, length)) ** gamma)


def _interval_weight_beta(interval: Mapping[str, Any], beta: float) -> float:
    length = int(interval["length"])
    distance = int(interval["distance"])
    return (float(length) ** beta) * (1.0 - _error_rate(distance, length))


def _candidate_features_from_payload(
    *,
    spec: SpanConfigSpec,
    token_hash: str,
    token_length: int,
    payload: Mapping[str, Any],
    elapsed_ms: float,
    build_ms: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw_intervals = _interval_dicts(payload, "raw_intervals")
    selected_intervals = _interval_dicts(payload, "selected_intervals")
    n_considered = int(payload.get("n_candidates_considered", 0) or 0)
    n_pruned = int(payload.get("n_candidates_pruned_cap", 0) or 0)
    cap_rate = float(n_pruned) / float(max(1, n_pruned + n_considered))

    features: dict[str, float] = {
        "span_raw_interval_weight_current": 0.0,
        "span_raw_interval_weight_len_norm": 0.0,
        "span_raw_interval_weight_gamma_1_5": 0.0,
        "span_raw_interval_weight_gamma_2_0": 0.0,
        "span_raw_interval_weight_gamma_3_0": 0.0,
        "span_raw_interval_weight_beta_1_25": 0.0,
        "span_raw_interval_weight_beta_1_5": 0.0,
        "exact_weight_len_ge_5": 0.0,
        "exact_weight_len_ge_8": 0.0,
        "low_error_weight_len_ge_5": 0.0,
        "low_error_weight_len_ge_8": 0.0,
        "low_error_weight_len_ge_10": 0.0,
        "long_low_error_weight_len_ge_8": 0.0,
        "long_low_error_weight_len_ge_10": 0.0,
        "long_low_error_weight_len_ge_12": 0.0,
        "short_weak_weight_len_le_4_error_gt_025": 0.0,
        "short_weak_interval_count": 0.0,
    }

    interval_bucket_acc: dict[tuple[str, int, int, str], dict[str, Any]] = {}

    for selected_flag, intervals in (("raw", raw_intervals), ("selected", selected_intervals)):
        for interval in intervals:
            length = int(interval["length"])
            distance = int(interval["distance"])
            bucket = _error_bucket(distance, length)
            error_rate = _error_rate(distance, length)
            exact_fraction = 1.0 - error_rate
            current_weight = float(interval["weight"])
            len_norm_weight = _interval_weight_len_norm(interval)

            key = (selected_flag, length, distance, bucket)
            acc = interval_bucket_acc.setdefault(
                key,
                {
                    "config_id": spec.config_id,
                    "dictionary_id": spec.dictionary_id,
                    "template_id": spec.template_id,
                    "token_hash": token_hash,
                    "row_kind": "interval_bucket",
                    "selected_flag": selected_flag,
                    "span_start": "",
                    "span_length": length,
                    "hamming_distance": distance,
                    "error_rate": f"{error_rate:.12g}",
                    "exact_fraction": f"{exact_fraction:.12g}",
                    "error_bucket": bucket,
                    "interval_count": 0,
                    "sum_weight_current": 0.0,
                    "sum_weight_len_norm": 0.0,
                },
            )
            acc["interval_count"] += 1
            acc["sum_weight_current"] += current_weight
            acc["sum_weight_len_norm"] += len_norm_weight

            if selected_flag != "raw":
                continue
            features["span_raw_interval_weight_current"] += current_weight
            features["span_raw_interval_weight_len_norm"] += len_norm_weight
            features["span_raw_interval_weight_gamma_1_5"] += _interval_weight_gamma(interval, 1.5)
            features["span_raw_interval_weight_gamma_2_0"] += _interval_weight_gamma(interval, 2.0)
            features["span_raw_interval_weight_gamma_3_0"] += _interval_weight_gamma(interval, 3.0)
            features["span_raw_interval_weight_beta_1_25"] += _interval_weight_beta(interval, 1.25)
            features["span_raw_interval_weight_beta_1_5"] += _interval_weight_beta(interval, 1.5)

            if distance == 0 and length >= 5:
                features["exact_weight_len_ge_5"] += len_norm_weight
            if distance == 0 and length >= 8:
                features["exact_weight_len_ge_8"] += len_norm_weight
            if error_rate <= 0.20 and length >= 5:
                features["low_error_weight_len_ge_5"] += len_norm_weight
            if error_rate <= 0.20 and length >= 8:
                features["low_error_weight_len_ge_8"] += len_norm_weight
                features["long_low_error_weight_len_ge_8"] += len_norm_weight
            if error_rate <= 0.20 and length >= 10:
                features["low_error_weight_len_ge_10"] += len_norm_weight
                features["long_low_error_weight_len_ge_10"] += len_norm_weight
            if error_rate <= 0.20 and length >= 12:
                features["long_low_error_weight_len_ge_12"] += len_norm_weight
            if length <= 4 and error_rate > 0.25:
                features["short_weak_weight_len_le_4_error_gt_025"] += len_norm_weight
                features["short_weak_interval_count"] += 1.0

    total_raw = max(1e-12, features["span_raw_interval_weight_len_norm"])
    approx = max(1e-12, total_raw - features["exact_weight_len_ge_5"])
    features["long_low_error_ratio"] = features["long_low_error_weight_len_ge_8"] / total_raw
    features["short_weak_ratio"] = features["short_weak_weight_len_le_4_error_gt_025"] / total_raw
    features["exact_to_approx_ratio"] = features["exact_weight_len_ge_5"] / approx

    row: dict[str, Any] = {
        "config_id": spec.config_id,
        "dictionary_id": spec.dictionary_id,
        "template_id": spec.template_id,
        "wordlist_rel": spec.wordlist_rel,
        "require_selected": int(spec.require_selected),
        "len_min": spec.len_min,
        "len_max": spec.len_max,
        "max_hd": spec.max_hd,
        "max_candidates_per_window": spec.max_candidates_per_window,
        "token_hash": token_hash,
        "token_length": token_length,
        "span_raw_selected_current": float(payload["span_raw"]),
        "span_coverage_selected": float(payload["coverage"]),
        "span_quality_selected_current": float(payload["quality"]),
        "span_interval_count_selected": int(payload["n_intervals_selected"]),
        "span_raw_interval_count": len(raw_intervals),
        "n_windows_total": int(payload["n_windows_total"]),
        "n_windows_scored": int(payload["n_windows_scored"]),
        "n_candidates_considered": n_considered,
        "n_candidates_pruned_cap": n_pruned,
        "candidate_cap_pruned_rate": cap_rate,
        "score_elapsed_ms": elapsed_ms,
        "backend_build_ms": build_ms,
    }
    row.update({key: f"{value:.12g}" for key, value in features.items()})

    interval_rows = []
    for acc in interval_bucket_acc.values():
        acc["sum_weight_current"] = f"{float(acc['sum_weight_current']):.12g}"
        acc["sum_weight_len_norm"] = f"{float(acc['sum_weight_len_norm']):.12g}"
        interval_rows.append(acc)
    return row, interval_rows


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


def _score_payload(backend: FastSpanHammingBackend, tokens: Sequence[int]) -> tuple[dict[str, Any], float]:
    start = time.perf_counter()
    payload = backend.score_payload(tokens)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return payload, elapsed_ms


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _candidate_fieldnames() -> list[str]:
    base = [
        "config_id",
        "dictionary_id",
        "template_id",
        "wordlist_rel",
        "require_selected",
        "len_min",
        "len_max",
        "max_hd",
        "max_candidates_per_window",
        "token_hash",
        "token_length",
        "span_raw_selected_current",
        "span_coverage_selected",
        "span_quality_selected_current",
        "span_interval_count_selected",
        "span_raw_interval_count",
        "n_windows_total",
        "n_windows_scored",
        "n_candidates_considered",
        "n_candidates_pruned_cap",
        "candidate_cap_pruned_rate",
        "score_elapsed_ms",
        "backend_build_ms",
    ]
    return base + [name for name in FEATURE_DIRECTIONS.keys() if name not in set(base)]


def _interval_fieldnames() -> list[str]:
    return [
        "config_id",
        "dictionary_id",
        "template_id",
        "token_hash",
        "row_kind",
        "selected_flag",
        "span_start",
        "span_length",
        "hamming_distance",
        "error_rate",
        "exact_fraction",
        "error_bucket",
        "interval_count",
        "sum_weight_current",
        "sum_weight_len_norm",
    ]


def _pair_feature_summary(pair_rows: Sequence[Mapping[str, str]], candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    candidate_by_key = {
        (str(row["config_id"]), str(row["token_hash"])): row
        for row in candidate_rows
    }
    config_ids_by_token: dict[str, set[str]] = defaultdict(set)
    for config_id, token_hash in candidate_by_key:
        config_ids_by_token[token_hash].add(config_id)

    acc: dict[tuple[str, str], dict[str, Any]] = {}
    for pair in pair_rows:
        winner_hash = str(pair.get("winner_token_hash", "")).strip()
        challenger_hash = str(pair.get("challenger_token_hash", "")).strip()
        if not winner_hash or not challenger_hash:
            continue
        current_correct = str(pair.get("current_score_correct", "")).strip() == "1"
        text_pair_key = f"{winner_hash}|{challenger_hash}"
        common_config_ids = sorted(config_ids_by_token.get(winner_hash, set()) & config_ids_by_token.get(challenger_hash, set()))

        for config_id in common_config_ids:
            winner = candidate_by_key.get((config_id, winner_hash))
            challenger = candidate_by_key.get((config_id, challenger_hash))
            if winner is None or challenger is None:
                continue
            for feature_name, direction in FEATURE_DIRECTIONS.items():
                pref = _feature_preference(direction, winner.get(feature_name), challenger.get(feature_name))
                key = (config_id, feature_name)
                row = acc.setdefault(
                    key,
                    {
                        "config_id": config_id,
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
                        "unique_text_pairs": set(),
                        "unique_misranked_rescue_pairs": set(),
                        "unique_control_break_pairs": set(),
                    },
                )
                row["pair_count"] += 1
                row["unique_text_pairs"].add(text_pair_key)
                if pref == "no_decision":
                    row["no_decision"] += 1
                    continue
                row["available_pair_count"] += 1
                row[pref] += 1
                if current_correct:
                    row["current_correct_control_pair_count"] += 1
                    if pref == "truth_worse":
                        row["breaks"] += 1
                        row["unique_control_break_pairs"].add(text_pair_key)
                else:
                    row["current_misranked_pair_count"] += 1
                    if pref == "truth_better":
                        row["rescues"] += 1
                        row["unique_misranked_rescue_pairs"].add(text_pair_key)

    out: list[dict[str, Any]] = []
    for row in acc.values():
        unique_text_pairs = row.pop("unique_text_pairs")
        unique_misranked_rescue_pairs = row.pop("unique_misranked_rescue_pairs")
        unique_control_break_pairs = row.pop("unique_control_break_pairs")
        row["net"] = int(row["rescues"]) - int(row["breaks"])
        row["unique_text_pair_count"] = len(unique_text_pairs)
        row["unique_misranked_rescue_pair_count"] = len(unique_misranked_rescue_pairs)
        row["unique_control_break_pair_count"] = len(unique_control_break_pairs)
        out.append(row)
    out.sort(key=lambda item: (str(item["config_id"]), str(item["feature_name"])))
    return out


def _summarize_timing(candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_config: dict[str, list[float]] = defaultdict(list)
    for row in candidate_rows:
        value = _safe_float(row.get("score_elapsed_ms"))
        if value is not None:
            by_config[str(row["config_id"])].append(value)
    out = []
    for config_id, values in sorted(by_config.items()):
        out.append(
            {
                "config_id": config_id,
                "sample_kind": "full_candidate",
                "row_count": len(values),
                "mean_ms": f"{mean(values):.6f}",
                "median_ms": f"{median(values):.6f}",
                "max_ms": f"{max(values):.6f}",
            }
        )
    return out


def _timing_chunk_rows(
    *,
    configs: Sequence[SpanConfigSpec],
    tokens_by_hash: Mapping[str, Sequence[int]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    token_items = list(tokens_by_hash.items())[:TIMING_SAMPLE_TOKEN_LIMIT]
    for spec in configs:
        backend, missing_reason, build_ms = _build_fast_backend(spec)
        if backend is None:
            continue
        for token_hash, tokens in token_items:
            for length in TIMING_CHUNK_LENGTHS:
                if len(tokens) < length:
                    continue
                starts = {
                    "prefix": 0,
                    "middle": max(0, (len(tokens) - length) // 2),
                    "suffix": max(0, len(tokens) - length),
                }
                for kind in TIMING_CHUNK_KINDS:
                    start = starts[kind]
                    chunk = tuple(tokens[start:start + length])
                    _payload, elapsed_ms = _score_payload(backend, chunk)
                    rows.append(
                        {
                            "config_id": spec.config_id,
                            "token_hash": token_hash,
                            "sample_kind": f"{kind}_{length}",
                            "token_length": length,
                            "elapsed_ms": f"{elapsed_ms:.6f}",
                            "backend_build_ms": f"{build_ms:.6f}",
                            "used_for_pair_metrics": 0,
                            "missing_reason": missing_reason,
                        }
                    )
    return rows


def _dictionary_summary(configs: Sequence[SpanConfigSpec]) -> list[dict[str, Any]]:
    rows = []
    for spec in configs:
        path = REPO_ROOT / spec.wordlist_rel
        rows.append(
            {
                "config_id": spec.config_id,
                "dictionary_id": spec.dictionary_id,
                "wordlist_rel": spec.wordlist_rel,
                "require_selected": int(spec.require_selected),
                "wordlist_exists": int(path.exists()),
                "missing_reason": "" if path.exists() else f"missing_wordlist_dir:{spec.wordlist_rel}",
            }
        )
    return rows


def _build_readout(summary: Mapping[str, Any], best_rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Span-Hamming Full Calibration v1",
        "",
        "## Purpose",
        "",
        "Report-only span-Hamming evidence calibration before Stage 2 gate simulation.",
        "",
        "## Input Dataset",
        "",
        f"- S1 pair rows: {summary['pair_row_count']}",
        f"- token hashes scored: {summary['token_hash_count']}",
        f"- span configs requested: {summary['config_count_requested']}",
        f"- span configs run: {summary['config_count_run']}",
        f"- span configs missing: {summary['config_count_missing']}",
        "",
        "## Result",
        "",
        f"- candidate feature rows: {summary['candidate_feature_row_count']}",
        f"- interval bucket rows: {summary['interval_bucket_row_count']}",
        f"- pair feature summary rows: {summary['pair_feature_summary_row_count']}",
        f"- parity spot-check failures: {summary['python_parity_failure_count']}",
        f"- elapsed minutes: {summary['elapsed_seconds'] / 60.0:.2f}",
        "",
        "## Best Rescue/Break Rows",
        "",
        "| config | feature | rescues | breaks | net | unique rescues | unique breaks |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in best_rows[:15]:
        lines.append(
            f"| {row['config_id']} | {row['feature_name']} | {row['rescues']} | {row['breaks']} | "
            f"{row['net']} | {row['unique_misranked_rescue_pair_count']} | "
            f"{row['unique_control_break_pair_count']} |"
        )
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- No runtime behaviour changed.",
            "- Truth labels are used only for pairwise evaluation.",
            "- Numeric rune/base-29 token sequences only.",
            "- Chunk timing rows are not counted as truth-labelled pair examples.",
            "- Interval rows are aggregate buckets, not every dictionary-entry comparison.",
            "- Fast backend remains anchored to Python parity checks.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_calibration() -> dict[str, Any]:
    if not fast_span_hamming_available():
        raise RuntimeError("optional _span_hamming_fast extension is not built")

    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pair_rows_all = _read_pair_rows()
    required_hashes = _required_token_hashes(pair_rows_all, TOKEN_HASH_LIMIT_FOR_DEV_SMOKE)
    tokens_by_hash = _read_token_rows(required_hashes)
    pair_rows = [
        row for row in pair_rows_all
        if row.get("winner_token_hash") in tokens_by_hash and row.get("challenger_token_hash") in tokens_by_hash
    ]
    configs = _config_specs()
    dictionary_rows = _dictionary_summary(configs)
    configs_to_run = [spec for spec in configs if (REPO_ROOT / spec.wordlist_rel).exists()]
    total_work = len(configs_to_run) * len(tokens_by_hash)

    print(
        f"[span_hamming_full_calibration] start token_hashes={len(tokens_by_hash)} "
        f"pairs={len(pair_rows)} configs={len(configs_to_run)} total_candidates={total_work}",
        flush=True,
    )

    candidate_rows: list[dict[str, Any]] = []
    interval_rows: list[dict[str, Any]] = []
    parity_rows: list[dict[str, Any]] = []
    completed = 0

    for config_idx, spec in enumerate(configs_to_run, start=1):
        backend, missing_reason, build_ms = _build_fast_backend(spec)
        if backend is None:
            continue
        python_backend = None
        if PYTHON_PARITY_SPOT_CHECK and config_idx <= PYTHON_PARITY_CONFIG_LIMIT:
            python_backend = _build_python_backend(spec)

        for token_idx, (token_hash, tokens) in enumerate(tokens_by_hash.items(), start=1):
            payload, elapsed_ms = _score_payload(backend, tokens)
            row, buckets = _candidate_features_from_payload(
                spec=spec,
                token_hash=token_hash,
                token_length=len(tokens),
                payload=payload,
                elapsed_ms=elapsed_ms,
                build_ms=build_ms,
            )
            candidate_rows.append(row)
            interval_rows.extend(buckets)

            if python_backend is not None and token_idx <= PYTHON_PARITY_TOKEN_LIMIT:
                py_stats = python_backend.score(tokens)
                fast_stats = backend.score(tokens)
                mismatches = _stats_compare(py_stats, fast_stats)
                parity_rows.append(
                    {
                        "config_id": spec.config_id,
                        "token_hash": token_hash,
                        "parity_ok": 1 if not mismatches else 0,
                        "mismatch_fields": ";".join(mismatches),
                    }
                )

            completed += 1
            if completed == 1 or completed % PROGRESS_EVERY_CANDIDATES == 0 or completed == total_work:
                elapsed = time.perf_counter() - started
                rate = completed / elapsed if elapsed > 0.0 else 0.0
                eta = (total_work - completed) / rate if rate > 0.0 else 0.0
                print(
                    f"[span_hamming_full_calibration] progress {completed}/{total_work} "
                    f"elapsed={elapsed/60.0:.1f}m eta={eta/60.0:.1f}m "
                    f"last_config={spec.config_id}",
                    flush=True,
                )

    pair_summary_rows = _pair_feature_summary(pair_rows, candidate_rows)
    timing_summary_rows = _summarize_timing(candidate_rows)
    timing_chunk_rows = _timing_chunk_rows(configs=configs_to_run[: min(8, len(configs_to_run))], tokens_by_hash=tokens_by_hash)
    best_rows = sorted(pair_summary_rows, key=lambda row: (int(row["net"]), int(row["rescues"])), reverse=True)

    _write_csv(OUTPUT_DIR / "span_hamming_full_calibration_candidate_features.csv", candidate_rows, _candidate_fieldnames())
    _write_csv(OUTPUT_DIR / "span_hamming_full_calibration_interval_rows.csv", interval_rows, _interval_fieldnames())
    _write_csv(
        OUTPUT_DIR / "span_hamming_full_calibration_pair_feature_summary.csv",
        pair_summary_rows,
        [
            "config_id",
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
            "unique_text_pair_count",
            "unique_misranked_rescue_pair_count",
            "unique_control_break_pair_count",
        ],
    )
    _write_csv(
        OUTPUT_DIR / "span_hamming_full_calibration_timing_summary.csv",
        timing_summary_rows,
        ["config_id", "sample_kind", "row_count", "mean_ms", "median_ms", "max_ms"],
    )
    _write_csv(
        OUTPUT_DIR / "span_hamming_full_calibration_timing_chunks.csv",
        timing_chunk_rows,
        ["config_id", "token_hash", "sample_kind", "token_length", "elapsed_ms", "backend_build_ms", "used_for_pair_metrics", "missing_reason"],
    )
    _write_csv(
        OUTPUT_DIR / "span_hamming_full_calibration_dictionary_summary.csv",
        dictionary_rows,
        ["config_id", "dictionary_id", "wordlist_rel", "require_selected", "wordlist_exists", "missing_reason"],
    )
    _write_csv(
        OUTPUT_DIR / "span_hamming_full_calibration_config_summary.csv",
        [asdict(spec) for spec in configs],
        ["config_id", "dictionary_id", "wordlist_rel", "require_selected", "template_id", "len_min", "len_max", "max_hd", "max_candidates_per_window"],
    )
    _write_csv(
        OUTPUT_DIR / "span_hamming_full_calibration_parity_spot_check.csv",
        parity_rows,
        ["config_id", "token_hash", "parity_ok", "mismatch_fields"],
    )

    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": _repo_rel(OUTPUT_DIR),
        "s1_pair_rows": _repo_rel(S1_PAIR_ROWS),
        "unique_partial_rows": _repo_rel(UNIQUE_PARTIAL_ROWS),
        "token_hash_limit_for_dev_smoke": TOKEN_HASH_LIMIT_FOR_DEV_SMOKE,
        "pair_row_count": len(pair_rows),
        "source_pair_row_count": len(pair_rows_all),
        "token_hash_count": len(tokens_by_hash),
        "config_count_requested": len(configs),
        "config_count_run": len(configs_to_run),
        "config_count_missing": len(configs) - len(configs_to_run),
        "candidate_feature_row_count": len(candidate_rows),
        "interval_bucket_row_count": len(interval_rows),
        "pair_feature_summary_row_count": len(pair_summary_rows),
        "timing_chunk_row_count": len(timing_chunk_rows),
        "python_parity_spot_check": PYTHON_PARITY_SPOT_CHECK,
        "python_parity_row_count": len(parity_rows),
        "python_parity_failure_count": sum(1 for row in parity_rows if int(row["parity_ok"]) != 1),
        "elapsed_seconds": time.perf_counter() - started,
        "missing_dictionary_counts": dict(Counter(row["missing_reason"] for row in dictionary_rows if row["missing_reason"])),
        "top_net_rows": best_rows[:20],
        "caveats": [
            "report-only; no runtime solver behaviour changed",
            "truth labels used only for pair evaluation",
            "numeric rune/base-29 token sequences only",
            "interval rows are aggregate buckets, not every dictionary-entry comparison",
            "chunk timing rows are not truth-labelled pair examples",
        ],
    }

    (OUTPUT_DIR / "span_hamming_full_calibration_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "span_hamming_full_calibration_readout.md").write_text(
        _build_readout(summary, best_rows),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    summary = run_calibration()
    print(
        "[span_hamming_full_calibration] done "
        f"tokens={summary['token_hash_count']} "
        f"configs={summary['config_count_run']} "
        f"candidate_rows={summary['candidate_feature_row_count']} "
        f"parity_failures={summary['python_parity_failure_count']} "
        f"elapsed={summary['elapsed_seconds']/60.0:.2f}m "
        f"output={summary['output_dir']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
