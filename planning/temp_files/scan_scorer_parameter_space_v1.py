from __future__ import annotations

"""
Report-only scorer parameter-space scan for no-WLI S1 historical pairs.

Intended repo path:
    tools/benchmarks/periodic_sub_trans/no_wli/analysis/scan_scorer_parameter_space_v1.py

Purpose:
    Explore scorer input/settings sensitivity before Stage 2 gate simulation.
    This script does not change runtime behaviour and does not design a new scorer.

Main outputs:
    output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/scorer_parameter_space_scan_v1/

Important interpretation rule:
    Pairwise rescue/break metrics are valid only for full candidate texts, because
    truth_match/truth_gap labels are whole-candidate labels. 300/500-char chunks
    are used for timing and feature-distribution benchmarking only.
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
from typing import Any, Callable, Iterable, Mapping, Sequence


# =============================================================================
# IDE-friendly config block. Edit these values; do not add CLI arguments.
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

# Current S1/S1d context. S1d proved all S1 rows are LTR; keep this explicit.
WORD_NGRAM_DIRECTION = "ltr"
BENCHMARK_MIN_TOKEN_LENGTH = 500

# Whole-text pairwise evaluation uses full S1 candidates only.
RUN_FULL_TEXT_PAIRWISE_METRICS = True

# Timing/distribution benchmarking uses deterministic chunks from real S1 texts.
# These are NOT treated as independently truth-labelled examples.
TIMING_CHUNK_LENGTHS = (300, 500, 1000)
TIMING_CHUNK_KINDS = ("prefix", "middle", "suffix")

# Set to 0 for all required S1 token hashes. Use a small number for a fast smoke run.
TOKEN_HASH_LIMIT_FOR_DEV_SMOKE = 0

# Timing settings. A broad sample gives more useful timing than repeated calls on one text.
WARMUP_SAMPLE_COUNT_PER_CONFIG = 2
TIMING_REPEATS_PER_SAMPLE = 1

# Whether to run word-ngram timing on all timing chunks. This can be expensive.
RUN_WORD_NGRAM_ON_TIMING_CHUNKS = True

# Local asset roots. These assume data are present in the repo checkout.
DEFAULT_RAW_WORDLIST_DIR_REL = "assets/hamming_raw_1g"
POLICY_ROOT_REL = "assets"

# Span grid. Keep small enough to understand, broad enough to reveal sensitivity.
SPAN_CONFIG_SPECS = (
    dict(
        config_id="raw_selected_len3_14_hd2_cap256__s1b_default",
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel=DEFAULT_RAW_WORDLIST_DIR_REL,
        note="S1b default raw selected dictionary setting.",
    ),
    dict(
        config_id="raw_selected_len3_14_hd0_exact",
        len_min=3,
        len_max=14,
        max_hd=0,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel=DEFAULT_RAW_WORDLIST_DIR_REL,
        note="Exact span matches only; tests whether approximate matches create noise.",
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
        note="Suppress very short approximate spans.",
    ),
    dict(
        config_id="raw_selected_len5_8_hd2_fixture_like",
        len_min=5,
        len_max=8,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel=DEFAULT_RAW_WORDLIST_DIR_REL,
        note="Length range used by the char4-overfit rescue fixture, but still raw/un-calibrated.",
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
        note="Candidate-cap pressure check against S1b default.",
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

# Word grid. Run through each span config, because word-ngram depends on exact span intervals.
WORD_CONFIG_SPECS = (
    dict(config_id="word_min6_alpha04_miss20", min_positions=6, alpha=0.4, miss_logp=-20.0),
    dict(config_id="word_min9_alpha04_miss20", min_positions=9, alpha=0.4, miss_logp=-20.0),
    dict(config_id="word_min12_alpha04_miss20__s1b_default", min_positions=12, alpha=0.4, miss_logp=-20.0),
    dict(config_id="word_min18_alpha04_miss20", min_positions=18, alpha=0.4, miss_logp=-20.0),
    dict(config_id="word_min24_alpha04_miss20", min_positions=24, alpha=0.4, miss_logp=-20.0),
)

# Optional small xent/backoff sensitivity grid. Keep off for the first full scan unless needed.
RUN_WORD_ALPHA_MISS_SWEEP = False
WORD_ALPHA_MISS_SWEEP_SPECS = (
    dict(config_id="word_min12_alpha02_miss20", min_positions=12, alpha=0.2, miss_logp=-20.0),
    dict(config_id="word_min12_alpha07_miss20", min_positions=12, alpha=0.7, miss_logp=-20.0),
    dict(config_id="word_min12_alpha10_miss20", min_positions=12, alpha=1.0, miss_logp=-20.0),
    dict(config_id="word_min12_alpha04_miss10", min_positions=12, alpha=0.4, miss_logp=-10.0),
    dict(config_id="word_min12_alpha04_miss15", min_positions=12, alpha=0.4, miss_logp=-15.0),
)

# Char-LM parameter scans are deliberately not implemented in this starter because they
# require the full LMPrime/Torch scorer asset root and a carefully cross-checked builder.
# This script records the current frozen score from S1 and leaves a clear placeholder.
RUN_CHAR_LM_SCAN_PLACEHOLDER = True


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

from rune_decrypter_prime.core.types import Direction, ensure_direction  # noqa: E402
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
        token_hash = str(row.get("partial_text_hash", "") or "")
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
        tokens = token_rows[token_hash]
        samples.append(
            TokenSample(
                token_hash=token_hash,
                sample_id=f"{token_hash}::full",
                sample_kind="full",
                sample_start=0,
                sample_length=len(tokens),
                tokens=tuple(tokens),
                is_full_candidate=True,
            )
        )
        for length in TIMING_CHUNK_LENGTHS:
            for kind in TIMING_CHUNK_KINDS:
                start, actual_len, chunk = _make_chunk(tokens, length=int(length), kind=str(kind))
                # Avoid duplicating the full candidate as a timing chunk.
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


def _time_call(func: Callable[[], Any]) -> tuple[Any, float]:
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


# =============================================================================
# Scoring functions.
# =============================================================================


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


def _score_span(
    *,
    backend: SpanHammingBackend | None,
    sample: TokenSample,
    missing_reason: str,
) -> tuple[dict[str, Any], SpanHammingStats | None]:
    if backend is None:
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
        ), None
    try:
        # Optional warmup/repeats are handled at the config loop level. This call is measured once.
        stats, elapsed_ms = _time_call(lambda: backend.score(sample.tokens))
        intervals = tuple(stats.selected_intervals)
        weights = [float(item.weight) for item in intervals]
        cap_den = max(1, int(stats.n_candidates_considered) + int(stats.n_candidates_pruned_cap))
        return dict(
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
        ), stats
    except Exception as exc:
        return dict(
            span_available=0,
            span_missing_reason=type(exc).__name__ + ":" + str(exc),
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
        ), None


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


def _score_word(
    *,
    runtime: RuneTokenWordNgramJudgeRuntime | None,
    sample: TokenSample,
    span_stats: SpanHammingStats | None,
    missing_reason: str,
) -> dict[str, Any]:
    if runtime is None:
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
            word_prefix_total_ge_10_rate="",
            word_prefix_total_ge_100_rate="",
            word_trust_score="",
            word_trust_tier="",
        )
    if span_stats is None:
        return dict(
            word_available=0,
            word_active=0,
            word_missing_reason="missing_span_intervals",
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
            word_prefix_total_ge_10_rate="",
            word_prefix_total_ge_100_rate="",
            word_trust_score="",
            word_trust_tier="",
        )
    try:
        report, elapsed_ms = _time_call(
            lambda: runtime.score_candidate(
                text_idx=sample.tokens,
                selected_intervals=span_stats.selected_intervals,
                direction=ensure_direction(WORD_NGRAM_DIRECTION),
            )
        )
        inactive_reason = str(report.inactive_reason or "")
        return dict(
            word_available=int(bool(report.available)),
            word_active=int(bool(report.active)),
            word_missing_reason=inactive_reason,
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
            word_prefix_total_ge_10_rate=float(report.prefix_total_ge_10_rate),
            word_prefix_total_ge_100_rate=float(report.prefix_total_ge_100_rate),
            word_trust_score=float(report.trust_score),
            word_trust_tier=str(report.trust_tier),
        )
    except Exception as exc:
        return dict(
            word_available=0,
            word_active=0,
            word_missing_reason=type(exc).__name__ + ":" + str(exc),
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
            word_prefix_total_ge_10_rate="",
            word_prefix_total_ge_100_rate="",
            word_trust_score="",
            word_trust_tier="",
        )


# =============================================================================
# Pair summaries.
# =============================================================================


def _full_feature_index(candidate_rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str, str], Mapping[str, Any]]:
    out: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for row in candidate_rows:
        if str(row.get("sample_kind", "")) != "full":
            continue
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
    winner: Mapping[str, Any],
    challenger: Mapping[str, Any],
) -> tuple[float | None, float | None, str]:
    """Return winner value, challenger value, and no-decision/missing reason."""
    if feature_name == "span_raw":
        return _safe_float(winner.get("span_raw")), _safe_float(challenger.get("span_raw")), ""
    if feature_name == "span_coverage":
        return _safe_float(winner.get("span_coverage")), _safe_float(challenger.get("span_coverage")), ""
    if feature_name == "span_quality":
        return _safe_float(winner.get("span_quality")), _safe_float(challenger.get("span_quality")), ""
    if feature_name == "span_interval_count":
        return _safe_float(winner.get("span_interval_count")), _safe_float(challenger.get("span_interval_count")), ""
    if feature_name == "span_mean_interval_length":
        return _safe_float(winner.get("span_mean_interval_length")), _safe_float(challenger.get("span_mean_interval_length")), ""
    if feature_name == "span_candidate_cap_pruned_rate":
        return _safe_float(winner.get("span_candidate_cap_pruned_rate")), _safe_float(challenger.get("span_candidate_cap_pruned_rate")), ""
    if feature_name == "word_trust_active_any":
        # Positive-confidence-only variant: inactive means zero confidence, but if neither side
        # is active it is explicitly no-decision. This is not a general word-ngram reranker.
        wa = _safe_int(winner.get("word_active"))
        ca = _safe_int(challenger.get("word_active"))
        if not wa and not ca:
            return None, None, "neither_word_ngram_active"
        return (
            _safe_float(winner.get("word_trust_score")) if wa else 0.0,
            _safe_float(challenger.get("word_trust_score")) if ca else 0.0,
            "",
        )
    if feature_name in {"word_xent_both_active", "word_backoff_xent_both_active", "word_miss_rate_both_active"}:
        if _word_active_pair_state(winner, challenger) != "both_active":
            return None, None, "not_both_word_ngram_active"
        if feature_name == "word_xent_both_active":
            return _safe_float(winner.get("word_xent")), _safe_float(challenger.get("word_xent")), ""
        if feature_name == "word_backoff_xent_both_active":
            return _safe_float(winner.get("word_backoff_xent")), _safe_float(challenger.get("word_backoff_xent")), ""
        return _safe_float(winner.get("word_miss_rate")), _safe_float(challenger.get("word_miss_rate")), ""
    raise KeyError(feature_name)


def build_pair_summaries(
    *,
    pair_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    feature_index = _full_feature_index(candidate_rows)
    summaries: dict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)
    active_summaries: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    unique_flags: dict[tuple[str, str, str, str], str] = {}
    pair_flag_rows: list[dict[str, Any]] = []

    for row in pair_rows:
        winner_hash = str(row.get("winner_token_hash", "") or "")
        challenger_hash = str(row.get("challenger_token_hash", "") or "")
        text_pair_key = "||".join(sorted((winner_hash, challenger_hash)))
        current_correct = _safe_int(row.get("current_score_correct")) == 1
        pair_group = "current_correct_control" if current_correct else "current_misranked"
        for span_spec in _span_specs():
            for word_spec in _word_specs():
                winner = feature_index.get((span_spec.config_id, word_spec.config_id, winner_hash))
                challenger = feature_index.get((span_spec.config_id, word_spec.config_id, challenger_hash))
                if winner is None or challenger is None:
                    continue
                active_state = _word_active_pair_state(winner, challenger)
                active_summaries[(span_spec.config_id, word_spec.config_id)][active_state] += 1
                active_summaries[(span_spec.config_id, word_spec.config_id)][pair_group + "__" + active_state] += 1

                for feature_name, direction in FEATURE_DEFINITIONS:
                    key = (span_spec.config_id, word_spec.config_id, feature_name)
                    summaries[key]["pair_count"] += 1
                    summaries[key][pair_group + "_pair_count"] += 1
                    winner_value, challenger_value, missing_reason = _feature_values_for_pair(
                        feature_name, winner, challenger
                    )
                    preference = _feature_preference(direction, winner_value, challenger_value)
                    summaries[key][preference] += 1
                    summaries[key][pair_group + "__" + preference] += 1
                    if preference == "truth_better" and not current_correct:
                        summaries[key]["rescues"] += 1
                    if preference == "truth_worse" and current_correct:
                        summaries[key]["breaks"] += 1
                    if preference == "no_decision":
                        summaries[key]["no_decision"] += 1
                    unique_key = (span_spec.config_id, word_spec.config_id, feature_name, text_pair_key)
                    unique_flags.setdefault(unique_key, preference)

                    # Keep one row-level flag file for the main candidate gate-like features only.
                    if feature_name in {"span_raw", "word_trust_active_any", "word_xent_both_active"}:
                        pair_flag_rows.append(
                            dict(
                                pair_id=row.get("pair_id", ""),
                                span_config_id=span_spec.config_id,
                                word_config_id=word_spec.config_id,
                                feature_name=feature_name,
                                feature_direction=direction,
                                current_score_correct=int(current_correct),
                                pair_group=pair_group,
                                text_pair_key=text_pair_key,
                                word_active_pair_state=active_state,
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
    for key in sorted(summaries):
        span_id, word_id, feature_name = key
        counts = summaries[key]
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

    active_rows = []
    for (span_id, word_id), counts in sorted(active_summaries.items()):
        active_rows.append(
            dict(
                span_config_id=span_id,
                word_config_id=word_id,
                both_active=int(counts["both_active"]),
                winner_only_active=int(counts["winner_only_active"]),
                challenger_only_active=int(counts["challenger_only_active"]),
                neither_active=int(counts["neither_active"]),
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

    return summary_rows, pair_flag_rows + active_rows


# =============================================================================
# Main scan.
# =============================================================================


def _span_specs() -> tuple[SpanSpec, ...]:
    return tuple(SpanSpec(**spec) for spec in SPAN_CONFIG_SPECS)


def _word_specs() -> tuple[WordSpec, ...]:
    specs = [WordSpec(**spec) for spec in WORD_CONFIG_SPECS]
    if RUN_WORD_ALPHA_MISS_SWEEP:
        specs.extend(WordSpec(**spec) for spec in WORD_ALPHA_MISS_SWEEP_SPECS)
    return tuple(specs)


def run_scan() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pair_rows = _read_csv(S1_PAIR_ROWS)
    token_hashes = _required_token_hashes(pair_rows)
    token_rows = _load_required_token_rows(token_hashes)
    samples = build_token_samples(token_rows)

    candidate_feature_rows: list[dict[str, Any]] = []
    config_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []

    for span_spec in _span_specs():
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

        # Warm up the span backend to avoid first-call effects dominating timing.
        if span_backend is not None and WARMUP_SAMPLE_COUNT_PER_CONFIG > 0:
            for sample in samples[: int(WARMUP_SAMPLE_COUNT_PER_CONFIG)]:
                try:
                    _ = span_backend.score(sample.tokens)
                except Exception:
                    pass

        # First compute span for all samples once; keep full-candidate stats for word scans.
        span_by_sample: dict[str, tuple[dict[str, Any], SpanHammingStats | None]] = {}
        for sample in samples:
            last_features: dict[str, Any] | None = None
            last_stats: SpanHammingStats | None = None
            elapsed_values: list[float] = []
            repeats = max(1, int(TIMING_REPEATS_PER_SAMPLE))
            for _ in range(repeats):
                features, stats = _score_span(
                    backend=span_backend,
                    sample=sample,
                    missing_reason=span_missing_reason,
                )
                elapsed_values.append(float(features.get("span_score_ms", 0.0) or 0.0))
                last_features = features
                last_stats = stats
            assert last_features is not None
            if repeats > 1:
                time_summary = _summarise_times(elapsed_values)
                last_features["span_score_ms"] = time_summary["mean_ms"]
            span_by_sample[sample.sample_id] = (last_features, last_stats)

        for word_spec in _word_specs():
            word_runtime, word_missing_reason, word_build_ms = _build_word_runtime(word_spec)
            config_rows.append(
                dict(
                    config_family="word_ngram",
                    config_id=f"{span_spec.config_id}__{word_spec.config_id}",
                    span_config_id=span_spec.config_id,
                    word_config_id=word_spec.config_id,
                    available=int(word_runtime is not None),
                    missing_reason=word_missing_reason,
                    build_ms=word_build_ms,
                    sqlite_rel=_repo_rel(WORD_NGRAM_SQLITE),
                    direction=WORD_NGRAM_DIRECTION,
                    min_positions=int(word_spec.min_positions),
                    alpha=float(word_spec.alpha),
                    miss_logp=float(word_spec.miss_logp),
                    prefix_total_thresholds=" ".join(str(v) for v in word_spec.prefix_total_thresholds),
                )
            )

            if word_runtime is not None and WARMUP_SAMPLE_COUNT_PER_CONFIG > 0:
                for sample in samples[: int(WARMUP_SAMPLE_COUNT_PER_CONFIG)]:
                    span_features, span_stats = span_by_sample.get(sample.sample_id, ({}, None))
                    try:
                        _ = word_runtime.score_candidate(
                            text_idx=sample.tokens,
                            selected_intervals=tuple() if span_stats is None else span_stats.selected_intervals,
                            direction=ensure_direction(WORD_NGRAM_DIRECTION),
                        )
                    except Exception:
                        pass

            for sample in samples:
                if not sample.is_full_candidate and not RUN_WORD_NGRAM_ON_TIMING_CHUNKS:
                    continue
                span_features, span_stats = span_by_sample[sample.sample_id]
                word_features = _score_word(
                    runtime=word_runtime,
                    sample=sample,
                    span_stats=span_stats,
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
                row.update(span_features)
                row.update(word_features)
                candidate_feature_rows.append(row)

            if word_runtime is not None:
                try:
                    word_runtime.close()
                except Exception:
                    pass

    # Timing summaries by config/sample kind.
    timing_acc: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    word_timing_acc: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in candidate_feature_rows:
        timing_acc[(str(row["span_config_id"]), str(row["word_config_id"]), str(row["sample_kind"]))].append(
            float(row.get("span_score_ms", 0.0) or 0.0)
        )
        word_timing_acc[(str(row["span_config_id"]), str(row["word_config_id"]), str(row["sample_kind"]))].append(
            float(row.get("word_score_ms", 0.0) or 0.0)
        )
    for (span_id, word_id, sample_kind), vals in sorted(timing_acc.items()):
        summary = _summarise_times(vals)
        timing_rows.append(dict(component="span_hamming", span_config_id=span_id, word_config_id=word_id, sample_kind=sample_kind, **summary))
    for (span_id, word_id, sample_kind), vals in sorted(word_timing_acc.items()):
        summary = _summarise_times(vals)
        timing_rows.append(dict(component="word_ngram", span_config_id=span_id, word_config_id=word_id, sample_kind=sample_kind, **summary))

    if RUN_FULL_TEXT_PAIRWISE_METRICS:
        pair_summary_rows, pair_flag_and_active_rows = build_pair_summaries(
            pair_rows=pair_rows,
            candidate_rows=candidate_feature_rows,
        )
    else:
        pair_summary_rows = []
        pair_flag_and_active_rows = []

    candidate_fields = [
        "token_hash", "sample_id", "sample_kind", "sample_start", "sample_length", "is_full_candidate",
        "span_config_id", "word_config_id", "span_word_config_id",
        "span_available", "span_missing_reason", "span_score_ms", "span_raw", "span_coverage", "span_quality",
        "span_interval_count", "span_chars_covered", "span_mean_interval_length", "span_best_interval_weight",
        "span_worst_interval_weight", "span_n_windows_total", "span_n_windows_scored",
        "span_n_candidates_considered", "span_n_candidates_pruned_cap", "span_candidate_cap_pruned_rate",
        "word_available", "word_active", "word_missing_reason", "word_score_ms", "word_exact_word_count",
        "word_segment_count", "word_xent", "word_backoff_xent", "word_n_positions", "word_miss_rate",
        "word_used5_rate", "word_used4_rate", "word_used3_rate", "word_prefix_total_ge_10_rate",
        "word_prefix_total_ge_100_rate", "word_trust_score", "word_trust_tier",
    ]
    config_fields = sorted({k for row in config_rows for k in row.keys()})
    timing_fields = ["component", "span_config_id", "word_config_id", "sample_kind", "count", "mean_ms", "median_ms", "p95_ms", "max_ms"]
    pair_summary_fields = sorted({k for row in pair_summary_rows for k in row.keys()}) if pair_summary_rows else ["empty"]
    pair_flag_fields = sorted({k for row in pair_flag_and_active_rows for k in row.keys()}) if pair_flag_and_active_rows else ["empty"]

    _write_csv(OUTPUT_DIR / "scorer_parameter_space_candidate_features.csv", candidate_feature_rows, candidate_fields)
    _write_csv(OUTPUT_DIR / "scorer_parameter_space_config_summary.csv", config_rows, config_fields)
    _write_csv(OUTPUT_DIR / "scorer_parameter_space_timing_summary.csv", timing_rows, timing_fields)
    _write_csv(OUTPUT_DIR / "scorer_parameter_space_pair_feature_summary.csv", pair_summary_rows, pair_summary_fields)
    _write_csv(OUTPUT_DIR / "scorer_parameter_space_pair_flags_and_active_states.csv", pair_flag_and_active_rows, pair_flag_fields)

    summary = dict(
        run_label=RUN_LABEL,
        generated_utc=_utc_now_text(),
        inputs=dict(
            s1_pair_rows=_repo_rel(S1_PAIR_ROWS),
            unique_partial_rows=_repo_rel(UNIQUE_PARTIAL_ROWS),
            word_ngram_sqlite=_repo_rel(WORD_NGRAM_SQLITE),
        ),
        output_dir=_repo_rel(OUTPUT_DIR),
        pair_count=len(pair_rows),
        required_token_hash_count=len(token_hashes),
        loaded_token_hash_count=len(token_rows),
        token_sample_count=len(samples),
        full_candidate_sample_count=sum(1 for s in samples if s.is_full_candidate),
        timing_chunk_lengths=list(TIMING_CHUNK_LENGTHS),
        timing_chunk_kinds=list(TIMING_CHUNK_KINDS),
        benchmark_min_token_length=BENCHMARK_MIN_TOKEN_LENGTH,
        word_ngram_direction=WORD_NGRAM_DIRECTION,
        span_config_count=len(_span_specs()),
        word_config_count=len(_word_specs()),
        candidate_feature_row_count=len(candidate_feature_rows),
        pair_summary_row_count=len(pair_summary_rows),
        report_only=True,
        runtime_change=False,
        caveats=[
            "Pairwise rescue/break metrics use full candidate texts only.",
            "300/500-char chunks are timing/distribution samples, not independent truth-labelled examples.",
            "Word-ngram features depend on exact span-Hamming intervals for the same span config.",
            "Inactive word-ngram xent/backoff/miss-rate are no-decision; see *_both_active feature summaries.",
            "Char-LM parameter scan is not implemented in this starter script; current frozen score remains the baseline.",
        ],
    )
    _write_json(OUTPUT_DIR / "scorer_parameter_space_summary.json", summary)
    (OUTPUT_DIR / "scorer_parameter_space_readout.md").write_text(_build_readout(summary), encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


def _build_readout(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Scorer Parameter-Space Scan v1",
        "",
        "## Purpose",
        "",
        "Report-only scan of span-Hamming and word-ngram scorer settings on the S1 historical pair dataset.",
        "This does not change runtime behaviour and does not define a gate.",
        "",
        "## Key rules",
        "",
        "- Numeric rune/base-29 token sequences only.",
        "- Truth labels are evaluation-only.",
        "- Full-candidate pair metrics only; chunks are timing/distribution samples.",
        "- Inactive word-ngram xent/backoff/miss-rate are no-decision.",
        "",
        "## Headline counts",
        "",
        f"- pair_count: `{summary.get('pair_count')}`",
        f"- required_token_hash_count: `{summary.get('required_token_hash_count')}`",
        f"- token_sample_count: `{summary.get('token_sample_count')}`",
        f"- span_config_count: `{summary.get('span_config_count')}`",
        f"- word_config_count: `{summary.get('word_config_count')}`",
        f"- candidate_feature_row_count: `{summary.get('candidate_feature_row_count')}`",
        "",
        "## Output files",
        "",
        "- `scorer_parameter_space_candidate_features.csv`",
        "- `scorer_parameter_space_config_summary.csv`",
        "- `scorer_parameter_space_timing_summary.csv`",
        "- `scorer_parameter_space_pair_feature_summary.csv`",
        "- `scorer_parameter_space_pair_flags_and_active_states.csv`",
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
