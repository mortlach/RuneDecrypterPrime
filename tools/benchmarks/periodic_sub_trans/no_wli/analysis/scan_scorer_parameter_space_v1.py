from __future__ import annotations

"""
Report-only no-WLI scorer parameter-space scan.

Intended repo path:
    tools/benchmarks/periodic_sub_trans/no_wli/analysis/scan_scorer_parameter_space_v1.py

Purpose:
    S1e-style scorer-space scan before Stage 2 gate simulation.

What this script does:
    - reads the S1 current-rescored historical pair table;
    - loads the required numeric rune/base-29 partial texts;
    - scans span-Hamming settings and dictionary variants;
    - scans word-ngram activation/sensitivity settings downstream of each span setting;
    - records timing by full texts and deterministic 300/500/1000-token chunks;
    - reports pairwise rescue/break/control evidence on full S1 candidates only.

What this script does NOT do:
    - no runtime policy change;
    - no scorer design / fitted weights;
    - no truth fields as scorer inputs;
    - no English rendering;
    - no pairwise truth labels for chunks.
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


# =============================================================================
# IDE-friendly config block. Edit values here; do not add CLI plumbing.
# =============================================================================

RUN_LABEL = "scorer_parameter_space_scan_v1"

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
    "scorer_parameter_space_scan_v1"
)

WORD_NGRAM_SQLITE_REL = (
    "output/tools/benchmarks/scoring/word_ngrams_sqlite_assets/"
    "20260308T024914Z__build_word_ngram_sqlite_asset_phase2_v1/"
    "word_ngrams_tokenized64_phase2_v1.sqlite"
)

# S1d proved LTR for the S1 pair dataset only. Keep this explicit.
DIRECTION_FOR_S1 = "ltr"
BENCHMARK_MIN_TOKEN_LENGTH = 500

# Pair metrics use full candidate texts only. Chunks are timing/distribution only.
TIMING_CHUNK_LENGTHS = (300, 500, 1000)
TIMING_CHUNK_KINDS = ("prefix", "middle", "suffix")
# Keep disabled for the first canary; enable only after full-text timing is known.
RUN_WORD_NGRAM_ON_TIMING_CHUNKS = False

# Set to 0 to run all required hashes. Full S1e run approved after canary timing.
TOKEN_HASH_LIMIT_FOR_DEV_SMOKE = 0

# Timing. A single pass over many S1 texts is more useful than many repeats on one text.
WARMUP_SAMPLE_COUNT_PER_CONFIG = 2
TIMING_REPEATS_PER_SAMPLE = 1
PROGRESS_EVERY_SAMPLES = 25

DEFAULT_RAW_WORDLIST_DIR_REL = "assets/hamming_raw_1g"

# Span-Hamming grid. Keep declared and small enough to interpret.
SPAN_CONFIG_SPECS = (
    dict(
        config_id="raw_selected_len3_14_hd2_cap256__s1b_default",
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel=DEFAULT_RAW_WORDLIST_DIR_REL,
        note="S1b raw selected dictionary default.",
    ),
    dict(
        config_id="raw_selected_len3_14_hd0_exact",
        len_min=3,
        len_max=14,
        max_hd=0,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel=DEFAULT_RAW_WORDLIST_DIR_REL,
        note="Exact matches only.",
    ),
    dict(
        config_id="raw_selected_len3_14_hd1",
        len_min=3,
        len_max=14,
        max_hd=1,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel=DEFAULT_RAW_WORDLIST_DIR_REL,
        note="One mismatch tolerance.",
    ),
    dict(
        config_id="raw_selected_len4_14_hd1",
        len_min=4,
        len_max=14,
        max_hd=1,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel=DEFAULT_RAW_WORDLIST_DIR_REL,
        note="Suppress len-3 approximate spans.",
    ),
    dict(
        config_id="raw_selected_len5_8_hd2_fixture_like",
        len_min=5,
        len_max=8,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel=DEFAULT_RAW_WORDLIST_DIR_REL,
        note="Length range used by char4-overfit span rescue fixture; still raw/un-calibrated.",
    ),
    dict(
        config_id="raw_selected_len6_14_hd2_longer",
        len_min=6,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel=DEFAULT_RAW_WORDLIST_DIR_REL,
        note="Longer span emphasis.",
    ),
    dict(
        config_id="raw_selected_len3_14_hd2_cap512",
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=512,
        require_selected=True,
        wordlist_rel=DEFAULT_RAW_WORDLIST_DIR_REL,
        note="Candidate-cap pressure check.",
    ),
    dict(
        config_id="policy_strict_len3_14_hd2",
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel="assets/hamming_dictionary_policies/strict/hamming_raw_1g",
        note="Strict dictionary policy check.",
    ),
    dict(
        config_id="policy_normal_len3_14_hd2",
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel="assets/hamming_dictionary_policies/normal/hamming_raw_1g",
        note="Normal dictionary policy check.",
    ),
    dict(
        config_id="policy_broad_len3_14_hd2",
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel="assets/hamming_dictionary_policies/broad/hamming_raw_1g",
        note="Broad dictionary policy check.",
    ),
)

# Word-ngram grid. Word evidence depends on exact intervals from each span config.
WORD_CONFIG_SPECS = (
    dict(config_id="word_min6_alpha04_miss20", min_positions=6, alpha=0.4, miss_logp=-20.0),
    dict(config_id="word_min9_alpha04_miss20", min_positions=9, alpha=0.4, miss_logp=-20.0),
    dict(config_id="word_min12_alpha04_miss20__s1b_default", min_positions=12, alpha=0.4, miss_logp=-20.0),
    dict(config_id="word_min18_alpha04_miss20", min_positions=18, alpha=0.4, miss_logp=-20.0),
    dict(config_id="word_min24_alpha04_miss20", min_positions=24, alpha=0.4, miss_logp=-20.0),
)

RUN_WORD_ALPHA_MISS_SWEEP = False
WORD_ALPHA_MISS_SWEEP_SPECS = (
    dict(config_id="word_min12_alpha02_miss20", min_positions=12, alpha=0.2, miss_logp=-20.0),
    dict(config_id="word_min12_alpha07_miss20", min_positions=12, alpha=0.7, miss_logp=-20.0),
    dict(config_id="word_min12_alpha10_miss20", min_positions=12, alpha=1.0, miss_logp=-20.0),
    dict(config_id="word_min12_alpha04_miss10", min_positions=12, alpha=0.4, miss_logp=-10.0),
    dict(config_id="word_min12_alpha04_miss15", min_positions=12, alpha=0.4, miss_logp=-15.0),
)

# Char-LM scan is deliberately not wired here; it needs the current LMPrime/Torch builder
# audited in the full repo. This script carries current_score from S1 as the baseline.
CHAR_LM_SCAN_STATUS = "not_implemented_in_this_span_word_scan"


# =============================================================================
# Repo setup and imports.
# =============================================================================


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root from this script path")


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rune_decrypter_prime.core.types import ensure_direction  # noqa: E402
from rune_decrypter_prime.scoring.span_hamming.backend import SpanHammingBackend  # noqa: E402
from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig, SpanHammingStats  # noqa: E402
from rune_decrypter_prime.scoring.word_ngrams import RuneTokenWordNgramJudgeRuntime  # noqa: E402


S1_PAIR_ROWS = REPO_ROOT / S1_PAIR_ROWS_REL
UNIQUE_PARTIAL_ROWS = REPO_ROOT / UNIQUE_PARTIAL_ROWS_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL
WORD_NGRAM_SQLITE = REPO_ROOT / WORD_NGRAM_SQLITE_REL


# =============================================================================
# Data structures.
# =============================================================================


@dataclass(frozen=True)
class SpanSpec:
    config_id: str
    len_min: int
    len_max: int
    max_hd: int
    max_candidates_per_window: int
    require_selected: bool
    wordlist_rel: str
    note: str = ""
    start_stride: int = 1
    max_windows_total: int = 0
    max_intervals_considered_per_start: int = 4
    min_quality_threshold: float = 1e-9


@dataclass(frozen=True)
class WordSpec:
    config_id: str
    min_positions: int
    alpha: float
    miss_logp: float
    prefix_total_thresholds: tuple[int, ...] = (1, 10, 100)


@dataclass(frozen=True)
class TokenSample:
    token_hash: str
    sample_id: str
    sample_kind: str
    sample_start: int
    sample_length: int
    tokens: tuple[int, ...]
    is_full_candidate: bool


FEATURE_DEFINITIONS = (
    ("span_raw", "higher"),
    ("span_coverage", "higher"),
    ("span_quality", "higher"),
    ("span_interval_count", "higher"),
    ("span_mean_interval_length", "higher"),
    ("span_candidate_cap_pruned_rate", "lower"),
    ("word_trust_active_any", "higher"),
    ("word_xent_both_active", "lower"),
    ("word_backoff_xent_both_active", "lower"),
    ("word_miss_rate_both_active", "lower"),
)


# =============================================================================
# Small utilities.
# =============================================================================


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(_repo_rel(path))
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _parse_numeric_tokens(token_sequence_text: str) -> tuple[int, ...]:
    try:
        values = tuple(int(part) for part in str(token_sequence_text).split())
    except ValueError as exc:
        raise ValueError("token sequence must contain integers only") from exc
    if not values:
        raise ValueError("token sequence is empty")
    bad = [v for v in values if v < 0 or v > 28]
    if bad:
        raise ValueError("numeric rune/base-29 tokens must be in 0..28")
    return values


def _required_token_hashes(pair_rows: Sequence[Mapping[str, Any]]) -> set[str]:
    out: set[str] = set()
    for row in pair_rows:
        for key in ("winner_token_hash", "challenger_token_hash"):
            value = str(row.get(key, "") or "")
            if value:
                out.add(value)
    return out


def _load_required_token_rows(token_hashes: set[str]) -> dict[str, tuple[int, ...]]:
    found: dict[str, tuple[int, ...]] = {}
    rows = _read_csv(UNIQUE_PARTIAL_ROWS)
    for row in rows:
        token_hash = str(row.get("partial_text_hash", "") or row.get("token_hash", "") or "")
        if token_hash in token_hashes:
            found[token_hash] = _parse_numeric_tokens(str(row.get("token_sequence_text", "") or ""))
            if len(found) == len(token_hashes):
                break
    missing = sorted(token_hashes - set(found))
    if missing:
        preview = ", ".join(missing[:5])
        raise RuntimeError(f"Missing token sequences for {len(missing)} required token hashes: {preview}")
    return found


def _stable_sample_token_hashes(token_hashes: Iterable[str]) -> list[str]:
    values = sorted(str(v) for v in token_hashes)
    if TOKEN_HASH_LIMIT_FOR_DEV_SMOKE and TOKEN_HASH_LIMIT_FOR_DEV_SMOKE > 0:
        values = values[: int(TOKEN_HASH_LIMIT_FOR_DEV_SMOKE)]
    return values


def _make_chunk(tokens: Sequence[int], *, length: int, kind: str) -> tuple[int, int, tuple[int, ...]]:
    n = len(tokens)
    if n <= int(length):
        return 0, n, tuple(int(v) for v in tokens)
    if kind == "prefix":
        start = 0
    elif kind == "suffix":
        start = n - int(length)
    elif kind == "middle":
        start = (n - int(length)) // 2
    else:
        raise ValueError(f"unknown chunk kind: {kind}")
    end = start + int(length)
    return start, int(length), tuple(int(v) for v in tokens[start:end])


def build_token_samples(token_rows: Mapping[str, tuple[int, ...]]) -> list[TokenSample]:
    samples: list[TokenSample] = []
    for token_hash in _stable_sample_token_hashes(token_rows.keys()):
        tokens = tuple(int(v) for v in token_rows[token_hash])
        samples.append(
            TokenSample(
                token_hash=token_hash,
                sample_id=f"{token_hash}::full",
                sample_kind="full",
                sample_start=0,
                sample_length=len(tokens),
                tokens=tokens,
                is_full_candidate=True,
            )
        )
        for length in TIMING_CHUNK_LENGTHS:
            for kind in TIMING_CHUNK_KINDS:
                start, actual_len, chunk = _make_chunk(tokens, length=int(length), kind=str(kind))
                # Avoid duplicating the full candidate sample when chunk length equals text length.
                if actual_len == len(tokens) and len(tokens) == int(length):
                    continue
                samples.append(
                    TokenSample(
                        token_hash=token_hash,
                        sample_id=f"{token_hash}::{kind}_{actual_len}",
                        sample_kind=f"{kind}_{actual_len}",
                        sample_start=start,
                        sample_length=actual_len,
                        tokens=chunk,
                        is_full_candidate=False,
                    )
                )
    return samples


def _time_call(func: Any) -> tuple[Any, float]:
    start = time.perf_counter_ns()
    result = func()
    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
    return result, float(elapsed_ms)


def _summarise_times(values: Sequence[float]) -> dict[str, float]:
    vals = sorted(float(v) for v in values if math.isfinite(float(v)))
    if not vals:
        return dict(count=0, mean_ms=0.0, median_ms=0.0, p95_ms=0.0, max_ms=0.0)
    p95_idx = min(len(vals) - 1, int(math.ceil(0.95 * len(vals))) - 1)
    return dict(
        count=int(len(vals)),
        mean_ms=float(mean(vals)),
        median_ms=float(median(vals)),
        p95_ms=float(vals[p95_idx]),
        max_ms=float(vals[-1]),
    )


def _prefer_higher(winner: float | None, challenger: float | None) -> str:
    if winner is None or challenger is None:
        return "no_decision"
    if winner > challenger:
        return "truth_better"
    if winner < challenger:
        return "truth_worse"
    return "tie"


def _prefer_lower(winner: float | None, challenger: float | None) -> str:
    if winner is None or challenger is None:
        return "no_decision"
    if winner < challenger:
        return "truth_better"
    if winner > challenger:
        return "truth_worse"
    return "tie"


def _feature_preference(direction: str, winner: float | None, challenger: float | None) -> str:
    if direction == "higher":
        return _prefer_higher(winner, challenger)
    if direction == "lower":
        return _prefer_lower(winner, challenger)
    raise ValueError(f"unknown feature direction: {direction}")


def _as_json_tuple(values: Sequence[Any]) -> str:
    return json.dumps(list(values), separators=(",", ":"), ensure_ascii=True, allow_nan=False)


# =============================================================================
# Scoring functions.
# =============================================================================


def _span_specs() -> tuple[SpanSpec, ...]:
    return tuple(SpanSpec(**spec) for spec in SPAN_CONFIG_SPECS)


def _word_specs() -> tuple[WordSpec, ...]:
    specs = [WordSpec(**spec) for spec in WORD_CONFIG_SPECS]
    if RUN_WORD_ALPHA_MISS_SWEEP:
        specs.extend(WordSpec(**spec) for spec in WORD_ALPHA_MISS_SWEEP_SPECS)
    return tuple(specs)


def _span_config_from_spec(spec: SpanSpec) -> SpanHammingConfig:
    return SpanHammingConfig(
        len_min=int(spec.len_min),
        len_max=int(spec.len_max),
        max_hd=int(spec.max_hd),
        start_stride=int(spec.start_stride),
        max_windows_total=int(spec.max_windows_total),
        max_candidates_per_window=int(spec.max_candidates_per_window),
        max_intervals_considered_per_start=int(spec.max_intervals_considered_per_start),
        min_quality_threshold=float(spec.min_quality_threshold),
        debug_return_intervals=True,
    )


def _build_span_backend(spec: SpanSpec) -> tuple[SpanHammingBackend | None, str, float]:
    wordlist_dir = REPO_ROOT / spec.wordlist_rel
    if not wordlist_dir.exists():
        return None, "missing_wordlist_dir:" + _repo_rel(wordlist_dir), 0.0
    cfg = _span_config_from_spec(spec)

    def build() -> SpanHammingBackend:
        return SpanHammingBackend(
            config=cfg,
            wordlist_dir=wordlist_dir,
            require_selected=bool(spec.require_selected),
        )

    try:
        backend, build_ms = _time_call(build)
        return backend, "", float(build_ms)
    except Exception as exc:
        return None, type(exc).__name__ + ":" + str(exc), 0.0


def _span_len_fields(stats: SpanHammingStats) -> dict[str, Any]:
    out: dict[str, Any] = {
        "span_length_bins_json": _as_json_tuple(stats.length_bins),
        "span_raw_by_len_json": _as_json_tuple(stats.span_raw_by_len),
        "span_coverage_by_len_json": _as_json_tuple(stats.coverage_by_len),
        "span_quality_by_len_json": _as_json_tuple(stats.quality_by_len),
        "span_intervals_by_len_json": _as_json_tuple(stats.selected_intervals_by_len),
        "span_chars_by_len_json": _as_json_tuple(stats.chars_covered_by_len),
    }
    for idx, length in enumerate(stats.length_bins):
        out[f"span_raw_len_{int(length)}"] = float(stats.span_raw_by_len[idx])
        out[f"span_coverage_len_{int(length)}"] = float(stats.coverage_by_len[idx])
        out[f"span_quality_len_{int(length)}"] = float(stats.quality_by_len[idx])
        out[f"span_intervals_len_{int(length)}"] = int(stats.selected_intervals_by_len[idx])
        out[f"span_chars_len_{int(length)}"] = int(stats.chars_covered_by_len[idx])
    return out


def _empty_span_row(missing_reason: str) -> dict[str, Any]:
    return dict(
        span_available=0,
        span_missing_reason=missing_reason or "unavailable",
        span_score_ms=0.0,
        span_raw="",
        span_coverage="",
        span_quality="",
        span_interval_count="",
        span_chars_covered="",
        span_mean_interval_length="",
        span_best_interval_weight="",
        span_worst_interval_weight="",
        span_n_windows_total="",
        span_n_windows_scored="",
        span_n_candidates_considered="",
        span_n_candidates_pruned_cap="",
        span_candidate_cap_pruned_rate="",
        span_length_bins_json="[]",
        span_raw_by_len_json="[]",
        span_coverage_by_len_json="[]",
        span_quality_by_len_json="[]",
        span_intervals_by_len_json="[]",
        span_chars_by_len_json="[]",
    )


def _score_span(
    *,
    backend: SpanHammingBackend | None,
    sample: TokenSample,
    missing_reason: str,
) -> tuple[dict[str, Any], SpanHammingStats | None]:
    if backend is None:
        return _empty_span_row(missing_reason), None
    try:
        stats, elapsed_ms = _time_call(lambda: backend.score(sample.tokens))
        intervals = tuple(stats.selected_intervals)
        weights = [float(item.weight) for item in intervals]
        cap_den = max(1, int(stats.n_candidates_considered) + int(stats.n_candidates_pruned_cap))
        row = dict(
            span_available=1,
            span_missing_reason="",
            span_score_ms=float(elapsed_ms),
            span_raw=float(stats.span_raw),
            span_coverage=float(stats.coverage),
            span_quality=float(stats.quality),
            span_interval_count=int(stats.n_intervals_selected),
            span_chars_covered=int(stats.chars_covered),
            span_mean_interval_length=(
                float(stats.chars_covered / stats.n_intervals_selected)
                if int(stats.n_intervals_selected) > 0
                else 0.0
            ),
            span_best_interval_weight=max(weights) if weights else 0.0,
            span_worst_interval_weight=min(weights) if weights else 0.0,
            span_n_windows_total=int(stats.n_windows_total),
            span_n_windows_scored=int(stats.n_windows_scored),
            span_n_candidates_considered=int(stats.n_candidates_considered),
            span_n_candidates_pruned_cap=int(stats.n_candidates_pruned_cap),
            span_candidate_cap_pruned_rate=float(int(stats.n_candidates_pruned_cap) / cap_den),
        )
        row.update(_span_len_fields(stats))
        return row, stats
    except Exception as exc:
        return _empty_span_row(type(exc).__name__ + ":" + str(exc)), None


def _build_word_runtime(spec: WordSpec) -> tuple[RuneTokenWordNgramJudgeRuntime | None, str, float]:
    if not WORD_NGRAM_SQLITE.exists():
        return None, "missing_word_ngram_sqlite:" + _repo_rel(WORD_NGRAM_SQLITE), 0.0

    def build() -> RuneTokenWordNgramJudgeRuntime:
        return RuneTokenWordNgramJudgeRuntime.open_sqlite(
            WORD_NGRAM_SQLITE,
            alpha=float(spec.alpha),
            miss_logp=float(spec.miss_logp),
            min_positions=int(spec.min_positions),
            prefix_total_thresholds=tuple(int(v) for v in spec.prefix_total_thresholds),
        )

    try:
        runtime, build_ms = _time_call(build)
        return runtime, "", float(build_ms)
    except Exception as exc:
        return None, type(exc).__name__ + ":" + str(exc), 0.0


def _empty_word_row(missing_reason: str) -> dict[str, Any]:
    return dict(
        word_available=0,
        word_active=0,
        word_missing_reason=missing_reason or "unavailable",
        word_score_ms=0.0,
        word_exact_word_count="",
        word_segment_count="",
        word_xent="",
        word_backoff_xent="",
        word_n_positions="",
        word_miss_rate="",
        word_used5_rate="",
        word_used4_rate="",
        word_used3_rate="",
        word_prefix_total_ge_1_rate="",
        word_prefix_total_ge_10_rate="",
        word_prefix_total_ge_100_rate="",
        word_trust_score="",
        word_trust_tier="",
    )


def _score_word(
    *,
    runtime: RuneTokenWordNgramJudgeRuntime | None,
    sample: TokenSample,
    span_stats: SpanHammingStats | None,
    missing_reason: str,
) -> dict[str, Any]:
    if runtime is None:
        return _empty_word_row(missing_reason)
    if span_stats is None:
        return _empty_word_row("missing_span_intervals")
    try:
        report, elapsed_ms = _time_call(
            lambda: runtime.score_candidate(
                text_idx=sample.tokens,
                selected_intervals=span_stats.selected_intervals,
                direction=ensure_direction(DIRECTION_FOR_S1),
            )
        )
        return dict(
            word_available=int(bool(report.available)),
            word_active=int(bool(report.active)),
            word_missing_reason=str(report.inactive_reason or ""),
            word_score_ms=float(elapsed_ms),
            word_exact_word_count=int(report.exact_word_count),
            word_segment_count=int(report.segment_count),
            word_xent=("" if report.xent_3 is None else float(report.xent_3)),
            word_backoff_xent=("" if report.xent_backoff_5_4_3 is None else float(report.xent_backoff_5_4_3)),
            word_n_positions=int(report.n_positions),
            word_miss_rate=("" if report.miss_rate is None else float(report.miss_rate)),
            word_used5_rate=("" if report.used5_rate is None else float(report.used5_rate)),
            word_used4_rate=("" if report.used4_rate is None else float(report.used4_rate)),
            word_used3_rate=("" if report.used3_rate is None else float(report.used3_rate)),
            word_prefix_total_ge_1_rate=float(report.prefix_total_ge_1_rate),
            word_prefix_total_ge_10_rate=float(report.prefix_total_ge_10_rate),
            word_prefix_total_ge_100_rate=float(report.prefix_total_ge_100_rate),
            word_trust_score=float(report.trust_score),
            word_trust_tier=str(report.trust_tier),
        )
    except Exception as exc:
        return _empty_word_row(type(exc).__name__ + ":" + str(exc))


# =============================================================================
# Pair summaries.
# =============================================================================


def _full_span_index(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], Mapping[str, Any]]:
    out: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        if str(row.get("sample_kind", "")) == "full":
            out[(str(row["span_config_id"]), str(row["token_hash"]))] = row
    return out


def _full_word_index(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str, str], Mapping[str, Any]]:
    out: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for row in rows:
        if str(row.get("sample_kind", "")) == "full":
            out[(str(row["span_config_id"]), str(row["word_config_id"]), str(row["token_hash"]))] = row
    return out


def _word_active_pair_state(winner: Mapping[str, Any], challenger: Mapping[str, Any]) -> str:
    wa = _safe_int(winner.get("word_active"))
    ca = _safe_int(challenger.get("word_active"))
    if wa and ca:
        return "both_active"
    if wa and not ca:
        return "winner_only_active"
    if ca and not wa:
        return "challenger_only_active"
    return "neither_active"


def _feature_values_for_pair(
    feature_name: str,
    span_winner: Mapping[str, Any],
    span_challenger: Mapping[str, Any],
    word_winner: Mapping[str, Any] | None,
    word_challenger: Mapping[str, Any] | None,
) -> tuple[float | None, float | None, str]:
    if feature_name == "span_raw":
        return _safe_float(span_winner.get("span_raw")), _safe_float(span_challenger.get("span_raw")), ""
    if feature_name == "span_coverage":
        return _safe_float(span_winner.get("span_coverage")), _safe_float(span_challenger.get("span_coverage")), ""
    if feature_name == "span_quality":
        return _safe_float(span_winner.get("span_quality")), _safe_float(span_challenger.get("span_quality")), ""
    if feature_name == "span_interval_count":
        return _safe_float(span_winner.get("span_interval_count")), _safe_float(span_challenger.get("span_interval_count")), ""
    if feature_name == "span_mean_interval_length":
        return _safe_float(span_winner.get("span_mean_interval_length")), _safe_float(span_challenger.get("span_mean_interval_length")), ""
    if feature_name == "span_candidate_cap_pruned_rate":
        return _safe_float(span_winner.get("span_candidate_cap_pruned_rate")), _safe_float(span_challenger.get("span_candidate_cap_pruned_rate")), ""
    if word_winner is None or word_challenger is None:
        return None, None, "missing_word_rows"
    if feature_name == "word_trust_active_any":
        wa = _safe_int(word_winner.get("word_active"))
        ca = _safe_int(word_challenger.get("word_active"))
        if not wa and not ca:
            return None, None, "neither_word_ngram_active"
        return (
            _safe_float(word_winner.get("word_trust_score")) if wa else 0.0,
            _safe_float(word_challenger.get("word_trust_score")) if ca else 0.0,
            "",
        )
    if feature_name in {"word_xent_both_active", "word_backoff_xent_both_active", "word_miss_rate_both_active"}:
        if _word_active_pair_state(word_winner, word_challenger) != "both_active":
            return None, None, "not_both_word_ngram_active"
        if feature_name == "word_xent_both_active":
            return _safe_float(word_winner.get("word_xent")), _safe_float(word_challenger.get("word_xent")), ""
        if feature_name == "word_backoff_xent_both_active":
            return _safe_float(word_winner.get("word_backoff_xent")), _safe_float(word_challenger.get("word_backoff_xent")), ""
        return _safe_float(word_winner.get("word_miss_rate")), _safe_float(word_challenger.get("word_miss_rate")), ""
    raise KeyError(feature_name)


def build_pair_summaries(
    *,
    pair_rows: Sequence[Mapping[str, Any]],
    span_rows: Sequence[Mapping[str, Any]],
    word_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    span_index = _full_span_index(span_rows)
    word_index = _full_word_index(word_rows)
    summary_counts: dict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)
    unique_flags: dict[tuple[str, str, str, str], str] = {}
    active_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    flag_rows: list[dict[str, Any]] = []

    for row in pair_rows:
        winner_hash = str(row.get("winner_token_hash", "") or "")
        challenger_hash = str(row.get("challenger_token_hash", "") or "")
        text_pair_key = "||".join(sorted((winner_hash, challenger_hash)))
        current_correct = _safe_int(row.get("current_score_correct")) == 1
        pair_group = "current_correct_control" if current_correct else "current_misranked"

        for span_spec in _span_specs():
            span_winner = span_index.get((span_spec.config_id, winner_hash))
            span_challenger = span_index.get((span_spec.config_id, challenger_hash))
            if span_winner is None or span_challenger is None:
                continue
            for word_spec in _word_specs():
                word_winner = word_index.get((span_spec.config_id, word_spec.config_id, winner_hash))
                word_challenger = word_index.get((span_spec.config_id, word_spec.config_id, challenger_hash))
                if word_winner is not None and word_challenger is not None:
                    state = _word_active_pair_state(word_winner, word_challenger)
                else:
                    state = "missing_word_rows"
                active_counts[(span_spec.config_id, word_spec.config_id)][state] += 1
                active_counts[(span_spec.config_id, word_spec.config_id)][pair_group + "__" + state] += 1

                for feature_name, direction in FEATURE_DEFINITIONS:
                    key = (span_spec.config_id, word_spec.config_id, feature_name)
                    summary_counts[key]["pair_count"] += 1
                    summary_counts[key][pair_group + "_pair_count"] += 1
                    winner_value, challenger_value, missing_reason = _feature_values_for_pair(
                        feature_name, span_winner, span_challenger, word_winner, word_challenger
                    )
                    preference = _feature_preference(direction, winner_value, challenger_value)
                    summary_counts[key][preference] += 1
                    summary_counts[key][pair_group + "__" + preference] += 1
                    if preference == "truth_better" and not current_correct:
                        summary_counts[key]["rescues"] += 1
                    if preference == "truth_worse" and current_correct:
                        summary_counts[key]["breaks"] += 1
                    unique_flags.setdefault((span_spec.config_id, word_spec.config_id, feature_name, text_pair_key), preference)

                    if feature_name in {"span_raw", "span_quality", "word_trust_active_any", "word_xent_both_active"}:
                        flag_rows.append(
                            dict(
                                pair_id=row.get("pair_id", ""),
                                span_config_id=span_spec.config_id,
                                word_config_id=word_spec.config_id,
                                feature_name=feature_name,
                                feature_direction=direction,
                                current_score_correct=int(current_correct),
                                pair_group=pair_group,
                                text_pair_key=text_pair_key,
                                word_active_pair_state=state,
                                winner_value="" if winner_value is None else winner_value,
                                challenger_value="" if challenger_value is None else challenger_value,
                                preference=preference,
                                missing_reason=missing_reason,
                            )
                        )

    unique_counts: dict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)
    for (span_id, word_id, feature_name, _text_pair_key), preference in unique_flags.items():
        unique_counts[(span_id, word_id, feature_name)][preference] += 1

    summary_rows: list[dict[str, Any]] = []
    direction_by_name = {name: direction for name, direction in FEATURE_DEFINITIONS}
    for key in sorted(summary_counts):
        span_id, word_id, feature_name = key
        counts = summary_counts[key]
        unique = unique_counts.get(key, Counter())
        summary_rows.append(
            dict(
                span_config_id=span_id,
                word_config_id=word_id,
                feature_name=feature_name,
                feature_direction=direction_by_name[feature_name],
                pair_count=int(counts["pair_count"]),
                current_misranked_pair_count=int(counts["current_misranked_pair_count"]),
                current_correct_control_pair_count=int(counts["current_correct_control_pair_count"]),
                prefers_truth_better=int(counts["truth_better"]),
                prefers_truth_worse=int(counts["truth_worse"]),
                ties=int(counts["tie"]),
                no_decision=int(counts["no_decision"]),
                current_misranked_prefers_truth_better=int(counts["current_misranked__truth_better"]),
                current_misranked_prefers_truth_worse=int(counts["current_misranked__truth_worse"]),
                current_misranked_ties=int(counts["current_misranked__tie"]),
                current_misranked_no_decision=int(counts["current_misranked__no_decision"]),
                current_correct_prefers_truth_better=int(counts["current_correct_control__truth_better"]),
                current_correct_prefers_truth_worse=int(counts["current_correct_control__truth_worse"]),
                current_correct_ties=int(counts["current_correct_control__tie"]),
                current_correct_no_decision=int(counts["current_correct_control__no_decision"]),
                rescues=int(counts["rescues"]),
                breaks=int(counts["breaks"]),
                net=int(counts["rescues"] - counts["breaks"]),
                unique_text_pair_prefers_truth_better=int(unique["truth_better"]),
                unique_text_pair_prefers_truth_worse=int(unique["truth_worse"]),
                unique_text_pair_ties=int(unique["tie"]),
                unique_text_pair_no_decision=int(unique["no_decision"]),
            )
        )

    active_rows: list[dict[str, Any]] = []
    for (span_id, word_id), counts in sorted(active_counts.items()):
        active_rows.append(
            dict(
                span_config_id=span_id,
                word_config_id=word_id,
                both_active=int(counts["both_active"]),
                winner_only_active=int(counts["winner_only_active"]),
                challenger_only_active=int(counts["challenger_only_active"]),
                neither_active=int(counts["neither_active"]),
                missing_word_rows=int(counts["missing_word_rows"]),
                current_misranked_both_active=int(counts["current_misranked__both_active"]),
                current_misranked_winner_only_active=int(counts["current_misranked__winner_only_active"]),
                current_misranked_challenger_only_active=int(counts["current_misranked__challenger_only_active"]),
                current_misranked_neither_active=int(counts["current_misranked__neither_active"]),
                current_correct_both_active=int(counts["current_correct_control__both_active"]),
                current_correct_winner_only_active=int(counts["current_correct_control__winner_only_active"]),
                current_correct_challenger_only_active=int(counts["current_correct_control__challenger_only_active"]),
                current_correct_neither_active=int(counts["current_correct_control__neither_active"]),
            )
        )
    return summary_rows, flag_rows, active_rows


# =============================================================================
# Main scan.
# =============================================================================


def run_scan() -> None:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pair_rows = _read_csv(S1_PAIR_ROWS)
    all_token_hashes = _required_token_hashes(pair_rows)
    selected_token_hashes = set(_stable_sample_token_hashes(all_token_hashes))
    token_rows = _load_required_token_rows(selected_token_hashes)
    pair_rows_for_metrics = [
        row
        for row in pair_rows
        if str(row.get("winner_token_hash", "") or "") in selected_token_hashes
        and str(row.get("challenger_token_hash", "") or "") in selected_token_hashes
    ]
    samples = build_token_samples(token_rows)

    below_min = sum(1 for tok in token_rows.values() if len(tok) < BENCHMARK_MIN_TOKEN_LENGTH)
    if below_min:
        raise RuntimeError(f"S1e expected all required full candidates >= {BENCHMARK_MIN_TOKEN_LENGTH}; found {below_min}")

    span_rows: list[dict[str, Any]] = []
    word_rows: list[dict[str, Any]] = []
    config_rows: list[dict[str, Any]] = []

    span_specs = _span_specs()
    word_specs = _word_specs()
    print(
        "[scorer_parameter_space_scan_v1] "
        f"input_pairs={len(pair_rows)} metric_pairs={len(pair_rows_for_metrics)} "
        f"selected_token_hashes={len(token_rows)}/{len(all_token_hashes)} samples={len(samples)} "
        f"span_configs={len(span_specs)} word_configs={len(word_specs)} "
        f"word_chunks={int(bool(RUN_WORD_NGRAM_ON_TIMING_CHUNKS))}",
        flush=True,
    )

    for span_idx, span_spec in enumerate(span_specs, start=1):
        span_elapsed = time.perf_counter() - started
        print(
            "[scorer_parameter_space_scan_v1] "
            f"span_config {span_idx}/{len(span_specs)} {span_spec.config_id} "
            f"elapsed_s={span_elapsed:.1f}",
            flush=True,
        )
        span_backend, span_missing_reason, span_build_ms = _build_span_backend(span_spec)
        span_cfg = _span_config_from_spec(span_spec)
        config_rows.append(
            dict(
                config_family="span_hamming",
                config_id=span_spec.config_id,
                available=int(span_backend is not None),
                missing_reason=span_missing_reason,
                build_ms=span_build_ms,
                wordlist_rel=span_spec.wordlist_rel,
                require_selected=int(bool(span_spec.require_selected)),
                note=span_spec.note,
                **asdict(span_cfg),
            )
        )

        if span_backend is not None and WARMUP_SAMPLE_COUNT_PER_CONFIG > 0:
            for sample in samples[: int(WARMUP_SAMPLE_COUNT_PER_CONFIG)]:
                try:
                    _ = span_backend.score(sample.tokens)
                except Exception:
                    pass

        span_stats_by_sample: dict[str, SpanHammingStats | None] = {}
        for sample_idx, sample in enumerate(samples, start=1):
            last_features: dict[str, Any] | None = None
            last_stats: SpanHammingStats | None = None
            elapsed_values: list[float] = []
            repeats = max(1, int(TIMING_REPEATS_PER_SAMPLE))
            for _ in range(repeats):
                features, stats = _score_span(backend=span_backend, sample=sample, missing_reason=span_missing_reason)
                elapsed_values.append(float(features.get("span_score_ms", 0.0) or 0.0))
                last_features = features
                last_stats = stats
            assert last_features is not None
            if repeats > 1:
                last_features["span_score_ms"] = _summarise_times(elapsed_values)["mean_ms"]
            row = dict(
                token_hash=sample.token_hash,
                sample_id=sample.sample_id,
                sample_kind=sample.sample_kind,
                sample_start=int(sample.sample_start),
                sample_length=int(sample.sample_length),
                is_full_candidate=int(sample.is_full_candidate),
                span_config_id=span_spec.config_id,
            )
            row.update(last_features)
            span_rows.append(row)
            span_stats_by_sample[sample.sample_id] = last_stats
            if int(PROGRESS_EVERY_SAMPLES) > 0 and sample_idx % int(PROGRESS_EVERY_SAMPLES) == 0:
                print(
                    "[scorer_parameter_space_scan_v1] "
                    f"span_config {span_idx}/{len(span_specs)} samples={sample_idx}/{len(samples)} "
                    f"elapsed_s={time.perf_counter() - started:.1f}",
                    flush=True,
                )

        for word_idx, word_spec in enumerate(word_specs, start=1):
            print(
                "[scorer_parameter_space_scan_v1] "
                f"word_config {word_idx}/{len(word_specs)} for span={span_spec.config_id} "
                f"{word_spec.config_id} elapsed_s={time.perf_counter() - started:.1f}",
                flush=True,
            )
            if span_backend is None:
                word_runtime = None
                word_missing_reason = "missing_upstream_span:" + span_missing_reason
                word_build_ms = 0.0
            else:
                word_runtime, word_missing_reason, word_build_ms = _build_word_runtime(word_spec)
            config_rows.append(
                dict(
                    config_family="word_ngram",
                    config_id=f"{span_spec.config_id}__{word_spec.config_id}",
                    span_config_id=span_spec.config_id,
                    word_config_id=word_spec.config_id,
                    available=int(word_runtime is not None and span_backend is not None),
                    missing_reason=word_missing_reason,
                    build_ms=word_build_ms,
                    sqlite_rel=_repo_rel(WORD_NGRAM_SQLITE),
                    direction=DIRECTION_FOR_S1,
                    min_positions=int(word_spec.min_positions),
                    alpha=float(word_spec.alpha),
                    miss_logp=float(word_spec.miss_logp),
                    prefix_total_thresholds=" ".join(str(v) for v in word_spec.prefix_total_thresholds),
                )
            )

            if word_runtime is not None and WARMUP_SAMPLE_COUNT_PER_CONFIG > 0:
                for sample in samples[: int(WARMUP_SAMPLE_COUNT_PER_CONFIG)]:
                    stats = span_stats_by_sample.get(sample.sample_id)
                    try:
                        _ = word_runtime.score_candidate(
                            text_idx=sample.tokens,
                            selected_intervals=tuple() if stats is None else stats.selected_intervals,
                            direction=ensure_direction(DIRECTION_FOR_S1),
                        )
                    except Exception:
                        pass

            word_sample_count = 0
            for sample in samples:
                if not sample.is_full_candidate and not RUN_WORD_NGRAM_ON_TIMING_CHUNKS:
                    continue
                word_sample_count += 1
                stats = span_stats_by_sample.get(sample.sample_id)
                word_features = _score_word(
                    runtime=word_runtime,
                    sample=sample,
                    span_stats=stats,
                    missing_reason=word_missing_reason,
                )
                row = dict(
                    token_hash=sample.token_hash,
                    sample_id=sample.sample_id,
                    sample_kind=sample.sample_kind,
                    sample_start=int(sample.sample_start),
                    sample_length=int(sample.sample_length),
                    is_full_candidate=int(sample.is_full_candidate),
                    span_config_id=span_spec.config_id,
                    word_config_id=word_spec.config_id,
                    span_word_config_id=f"{span_spec.config_id}__{word_spec.config_id}",
                )
                row.update(word_features)
                word_rows.append(row)
                if int(PROGRESS_EVERY_SAMPLES) > 0 and word_sample_count % int(PROGRESS_EVERY_SAMPLES) == 0:
                    print(
                        "[scorer_parameter_space_scan_v1] "
                        f"word_config {word_idx}/{len(word_specs)} samples={word_sample_count} "
                        f"elapsed_s={time.perf_counter() - started:.1f}",
                        flush=True,
                    )

            if word_runtime is not None:
                try:
                    word_runtime.close()
                except Exception:
                    pass

    print(
        "[scorer_parameter_space_scan_v1] building pair summaries "
        f"elapsed_s={time.perf_counter() - started:.1f}",
        flush=True,
    )

    pair_summary_rows, pair_flag_rows, active_state_rows = build_pair_summaries(
        pair_rows=pair_rows_for_metrics,
        span_rows=span_rows,
        word_rows=word_rows,
    )

    timing_rows = _build_timing_summary_rows(span_rows=span_rows, word_rows=word_rows)

    span_fields = _fieldnames(span_rows)
    word_fields = _fieldnames(word_rows)
    config_fields = _fieldnames(config_rows)
    timing_fields = _fieldnames(timing_rows)
    pair_summary_fields = _fieldnames(pair_summary_rows)
    pair_flag_fields = _fieldnames(pair_flag_rows)
    active_fields = _fieldnames(active_state_rows)

    _write_csv(OUTPUT_DIR / "scorer_parameter_space_span_candidate_features.csv", span_rows, span_fields)
    _write_csv(OUTPUT_DIR / "scorer_parameter_space_word_candidate_features.csv", word_rows, word_fields)
    _write_csv(OUTPUT_DIR / "scorer_parameter_space_config_summary.csv", config_rows, config_fields)
    _write_csv(OUTPUT_DIR / "scorer_parameter_space_timing_summary.csv", timing_rows, timing_fields)
    _write_csv(OUTPUT_DIR / "scorer_parameter_space_pair_feature_summary.csv", pair_summary_rows, pair_summary_fields)
    _write_csv(OUTPUT_DIR / "scorer_parameter_space_pair_flags.csv", pair_flag_rows, pair_flag_fields)
    _write_csv(OUTPUT_DIR / "scorer_parameter_space_word_active_state_summary.csv", active_state_rows, active_fields)

    summary = dict(
        run_label=RUN_LABEL,
        generated_utc=_utc_now_text(),
        inputs=dict(
            s1_pair_rows=_repo_rel(S1_PAIR_ROWS),
            unique_partial_rows=_repo_rel(UNIQUE_PARTIAL_ROWS),
            word_ngram_sqlite=_repo_rel(WORD_NGRAM_SQLITE),
        ),
        output_dir=_repo_rel(OUTPUT_DIR),
        input_pair_count=len(pair_rows),
        pair_count=len(pair_rows_for_metrics),
        all_required_token_hash_count=len(all_token_hashes),
        selected_token_hash_count=len(selected_token_hashes),
        token_hash_limit_for_dev_smoke=int(TOKEN_HASH_LIMIT_FOR_DEV_SMOKE),
        loaded_token_hash_count=len(token_rows),
        full_candidate_count=len(token_rows),
        full_candidate_below_min_token_length_count=int(below_min),
        token_sample_count=len(samples),
        timing_chunk_lengths=list(TIMING_CHUNK_LENGTHS),
        timing_chunk_kinds=list(TIMING_CHUNK_KINDS),
        benchmark_min_token_length=BENCHMARK_MIN_TOKEN_LENGTH,
        direction_for_s1=DIRECTION_FOR_S1,
        span_config_count=len(_span_specs()),
        word_config_count=len(_word_specs()),
        span_candidate_feature_row_count=len(span_rows),
        word_candidate_feature_row_count=len(word_rows),
        pair_summary_row_count=len(pair_summary_rows),
        char_lm_scan_status=CHAR_LM_SCAN_STATUS,
        report_only=True,
        runtime_change=False,
        caveats=[
            "Full-candidate pair metrics only; chunks are timing/distribution samples.",
            "Word-ngram features depend on exact span-Hamming intervals from the same span config.",
            "Inactive word-ngram xent/backoff/miss-rate are no-decision; use *_both_active summaries.",
            "word_trust_active_any is positive-confidence evidence, not a general word-ngram reranker.",
            "This scan does not fit weights and does not define a checkpoint gate.",
            "Calibrated span-Hamming assets are not used in this starter; add them only after asset contracts are checked.",
        ],
    )
    _write_json(OUTPUT_DIR / "scorer_parameter_space_summary.json", summary)
    (OUTPUT_DIR / "scorer_parameter_space_readout.md").write_text(_build_readout(summary), encoding="utf-8")

    print(
        "[scorer_parameter_space_scan_v1] complete "
        f"elapsed_s={time.perf_counter() - started:.1f}",
        flush=True,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


def _fieldnames(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                ordered.append(str(key))
    return ordered or ["empty"]


def _build_timing_summary_rows(
    *,
    span_rows: Sequence[Mapping[str, Any]],
    word_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    acc: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in span_rows:
        acc[("span_hamming", str(row.get("span_config_id", "")), "", str(row.get("sample_kind", "")))].append(
            float(row.get("span_score_ms", 0.0) or 0.0)
        )
    for row in word_rows:
        acc[("word_ngram", str(row.get("span_config_id", "")), str(row.get("word_config_id", "")), str(row.get("sample_kind", "")))].append(
            float(row.get("word_score_ms", 0.0) or 0.0)
        )
    out: list[dict[str, Any]] = []
    for (component, span_id, word_id, sample_kind), values in sorted(acc.items()):
        out.append(
            dict(
                component=component,
                span_config_id=span_id,
                word_config_id=word_id,
                sample_kind=sample_kind,
                **_summarise_times(values),
            )
        )
    return out


def _build_readout(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Scorer Parameter-Space Scan v1",
        "",
        "## Purpose",
        "",
        "Report-only S1e scan of span-Hamming and word-ngram parameter settings on the S1 historical pair dataset.",
        "This script does not change runtime behaviour and does not define a checkpoint gate.",
        "",
        "## Interpretation rules",
        "",
        "- Numeric rune/base-29 token sequences only.",
        "- Truth labels are evaluation-only.",
        "- Full candidate texts are used for rescue/break/control pair metrics.",
        "- 300/500/1000-token chunks are timing and distribution samples only.",
        "- Inactive word-ngram xent/backoff/miss-rate are no-decision.",
        "",
        "## Headline counts",
        "",
        f"- input_pair_count: `{summary.get('input_pair_count')}`",
        f"- pair_count: `{summary.get('pair_count')}`",
        f"- all_required_token_hash_count: `{summary.get('all_required_token_hash_count')}`",
        f"- selected_token_hash_count: `{summary.get('selected_token_hash_count')}`",
        f"- token_hash_limit_for_dev_smoke: `{summary.get('token_hash_limit_for_dev_smoke')}`",
        f"- token_sample_count: `{summary.get('token_sample_count')}`",
        f"- span_config_count: `{summary.get('span_config_count')}`",
        f"- word_config_count: `{summary.get('word_config_count')}`",
        f"- full_candidate_below_min_token_length_count: `{summary.get('full_candidate_below_min_token_length_count')}`",
        "",
        "## Output files",
        "",
        "- `scorer_parameter_space_span_candidate_features.csv`",
        "- `scorer_parameter_space_word_candidate_features.csv`",
        "- `scorer_parameter_space_config_summary.csv`",
        "- `scorer_parameter_space_timing_summary.csv`",
        "- `scorer_parameter_space_pair_feature_summary.csv`",
        "- `scorer_parameter_space_pair_flags.csv`",
        "- `scorer_parameter_space_word_active_state_summary.csv`",
        "- `scorer_parameter_space_summary.json`",
        "",
        "## Caveats",
        "",
    ]
    for caveat in summary.get("caveats", []):
        lines.append(f"- {caveat}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    run_scan()
