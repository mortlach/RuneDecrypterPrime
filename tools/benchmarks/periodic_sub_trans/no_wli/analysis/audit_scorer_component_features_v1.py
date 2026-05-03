from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


RUN_LABEL = "scorer_component_feature_audit_v1"
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
    "scorer_component_feature_audit_v1"
)

SPAN_HAMMING_ENABLED = True
WORD_NGRAM_ENABLED = True
WORD_NGRAM_SQLITE_REL = (
    "output/tools/benchmarks/scoring/word_ngrams_sqlite_assets/"
    "20260308T024914Z__build_word_ngram_sqlite_asset_phase2_v1/"
    "word_ngrams_tokenized64_phase2_v1.sqlite"
)
WORD_NGRAM_ALPHA = 0.4
WORD_NGRAM_MISS_LOGP = -20.0
WORD_NGRAM_MIN_POSITIONS = 12
WORD_NGRAM_PREFIX_THRESHOLDS = (1, 10, 100)
DIAGNOSTIC_PERIODS = (3, 4, 5, 6, 7, 8, 9)
NGRAM_SIZES = (3, 4, 5, 6)


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

from rune_decrypter_prime.core.types import Direction  # noqa: E402
from rune_decrypter_prime.scoring.span_hamming.backend import SpanHammingBackend  # noqa: E402
from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig  # noqa: E402
from rune_decrypter_prime.scoring.word_ngrams import RuneTokenWordNgramJudgeRuntime  # noqa: E402


S1_PAIR_ROWS = REPO_ROOT / S1_PAIR_ROWS_REL
UNIQUE_PARTIAL_ROWS = REPO_ROOT / UNIQUE_PARTIAL_ROWS_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL
WORD_NGRAM_SQLITE = REPO_ROOT / WORD_NGRAM_SQLITE_REL


CANDIDATE_FEATURE_FIELDS = (
    "token_hash",
    "token_length",
    "numeric_valid",
    "numeric_missing_reason",
    "current_score_mean",
    "current_score_min",
    "current_score_max",
    "current_score_value_count",
    "token_unique_fraction",
    "token_entropy_norm",
    "low_diversity_penalty",
    "repeated_3gram_rate",
    "repeated_4gram_rate",
    "repeated_5gram_rate",
    "repeated_6gram_rate",
    "unique_3gram_fraction",
    "unique_4gram_fraction",
    "unique_5gram_fraction",
    "unique_6gram_fraction",
    "max_ngram_repeat_count_3",
    "max_ngram_repeat_count_4",
    "max_ngram_repeat_count_5",
    "max_ngram_repeat_count_6",
    "period_lane_repeat_rate_mean_p3",
    "period_lane_repeat_rate_spread_p3",
    "period_lane_diversity_spread_p3",
    "period_lane_repeat_rate_mean_p4",
    "period_lane_repeat_rate_spread_p4",
    "period_lane_diversity_spread_p4",
    "period_lane_repeat_rate_mean_p5",
    "period_lane_repeat_rate_spread_p5",
    "period_lane_diversity_spread_p5",
    "period_lane_repeat_rate_mean_p6",
    "period_lane_repeat_rate_spread_p6",
    "period_lane_diversity_spread_p6",
    "period_lane_repeat_rate_mean_p7",
    "period_lane_repeat_rate_spread_p7",
    "period_lane_diversity_spread_p7",
    "period_lane_repeat_rate_mean_p8",
    "period_lane_repeat_rate_spread_p8",
    "period_lane_diversity_spread_p8",
    "period_lane_repeat_rate_mean_p9",
    "period_lane_repeat_rate_spread_p9",
    "period_lane_diversity_spread_p9",
    "span_hamming_available",
    "span_hamming_missing_reason",
    "span_raw_score",
    "span_coverage",
    "span_quality",
    "selected_interval_count",
    "selected_interval_total_length",
    "mean_selected_interval_length",
    "best_interval_score",
    "worst_selected_interval_score",
    "word_ngram_available",
    "word_ngram_active",
    "word_ngram_missing_reason",
    "word_ngram_trust_tier",
    "word_ngram_trust_score",
    "word_ngram_xent",
    "word_ngram_backoff_xent",
    "word_ngram_token_count",
    "word_ngram_n_positions",
    "word_ngram_miss_rate",
    "word_ngram_backoff_used_rate",
)

PAIR_FEATURE_FIELDS = (
    "pair_id",
    "artifact_path",
    "fixture_id",
    "fixture_seed",
    "search_seed",
    "token_length",
    "winner_candidate_hash",
    "challenger_candidate_hash",
    "winner_token_hash",
    "challenger_token_hash",
    "winner_truth_match",
    "challenger_truth_match",
    "truth_gap",
    "winner_current_score",
    "challenger_current_score",
    "current_score_margin",
    "current_score_correct",
    "pair_group",
    "feature_family",
    "feature_name",
    "feature_direction",
    "winner_feature_value",
    "challenger_feature_value",
    "feature_margin",
    "feature_prefers_truth_better",
    "feature_prefers_truth_worse",
    "feature_tie",
    "feature_missing",
    "feature_missing_reason",
    "text_pair_key",
    "candidate_hash_pair_key",
)

FEATURE_SUMMARY_FIELDS = (
    "feature_family",
    "feature_name",
    "feature_direction",
    "available_pair_count",
    "missing_pair_count",
    "all_pairs_prefers_truth_better",
    "all_pairs_prefers_truth_worse",
    "all_pairs_tie",
    "current_misranked_prefers_truth_better",
    "current_misranked_prefers_truth_worse",
    "current_misranked_tie",
    "current_correct_controls_prefers_truth_better",
    "current_correct_controls_prefers_truth_worse",
    "current_correct_controls_tie",
    "unique_text_pair_count",
    "unique_text_pair_prefers_truth_better",
    "unique_text_pair_prefers_truth_worse",
    "unique_text_pair_tie",
    "rescues",
    "breaks",
    "net",
    "dominant_pair_fraction",
)

MISSINGNESS_FIELDS = (
    "feature_family",
    "feature_name",
    "missing_reason",
    "row_count",
    "unique_text_pair_count",
    "unique_candidate_hash_pair_count",
)

FEATURE_DEFINITIONS: tuple[dict[str, str], ...] = (
    {"family": "char_current", "name": "current_score", "direction": "higher"},
    {"family": "motif_repetition", "name": "repeated_3gram_rate", "direction": "lower"},
    {"family": "motif_repetition", "name": "repeated_4gram_rate", "direction": "lower"},
    {"family": "motif_repetition", "name": "repeated_5gram_rate", "direction": "lower"},
    {"family": "motif_repetition", "name": "repeated_6gram_rate", "direction": "lower"},
    {"family": "motif_repetition", "name": "unique_3gram_fraction", "direction": "higher"},
    {"family": "motif_repetition", "name": "unique_4gram_fraction", "direction": "higher"},
    {"family": "motif_repetition", "name": "unique_5gram_fraction", "direction": "higher"},
    {"family": "motif_repetition", "name": "unique_6gram_fraction", "direction": "higher"},
    {"family": "motif_repetition", "name": "max_ngram_repeat_count_3", "direction": "lower"},
    {"family": "motif_repetition", "name": "max_ngram_repeat_count_4", "direction": "lower"},
    {"family": "motif_repetition", "name": "max_ngram_repeat_count_5", "direction": "lower"},
    {"family": "motif_repetition", "name": "max_ngram_repeat_count_6", "direction": "lower"},
    {"family": "diversity", "name": "token_unique_fraction", "direction": "higher"},
    {"family": "diversity", "name": "token_entropy_norm", "direction": "higher"},
    {"family": "diversity", "name": "low_diversity_penalty", "direction": "lower"},
    {"family": "span_hamming", "name": "span_raw_score", "direction": "higher"},
    {"family": "span_hamming", "name": "span_coverage", "direction": "higher"},
    {"family": "span_hamming", "name": "span_quality", "direction": "higher"},
    {"family": "span_hamming", "name": "selected_interval_count", "direction": "higher"},
    {"family": "span_hamming", "name": "selected_interval_total_length", "direction": "higher"},
    {"family": "span_hamming", "name": "mean_selected_interval_length", "direction": "higher"},
    {"family": "span_hamming", "name": "best_interval_score", "direction": "higher"},
    {"family": "span_hamming", "name": "worst_selected_interval_score", "direction": "higher"},
    {"family": "word_ngram", "name": "word_ngram_trust_score", "direction": "higher"},
    {"family": "word_ngram", "name": "word_ngram_xent", "direction": "lower"},
    {"family": "word_ngram", "name": "word_ngram_backoff_xent", "direction": "lower"},
    {"family": "word_ngram", "name": "word_ngram_token_count", "direction": "higher"},
    {"family": "word_ngram", "name": "word_ngram_n_positions", "direction": "higher"},
    {"family": "word_ngram", "name": "word_ngram_miss_rate", "direction": "lower"},
    {"family": "word_ngram", "name": "word_ngram_backoff_used_rate", "direction": "higher"},
)

for _period in DIAGNOSTIC_PERIODS:
    FEATURE_DEFINITIONS += (
        {
            "family": "period_lane",
            "name": f"period_lane_repeat_rate_mean_p{_period}",
            "direction": "lower",
        },
        {
            "family": "period_lane",
            "name": f"period_lane_repeat_rate_spread_p{_period}",
            "direction": "lower",
        },
        {
            "family": "period_lane",
            "name": f"period_lane_diversity_spread_p{_period}",
            "direction": "lower",
        },
    )


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def _finite_or_blank(value: Any) -> float | str:
    out = _safe_float(value)
    return float(out) if math.isfinite(out) else ""


def _pair_key(left: str, right: str) -> str:
    return "||".join(sorted((str(left), str(right))))


def parse_numeric_tokens(token_sequence_text: str) -> list[int]:
    try:
        values = [int(part) for part in str(token_sequence_text).split()]
    except ValueError as exc:
        raise ValueError("token sequence must contain integers only") from exc
    if not values:
        raise ValueError("token sequence is empty")
    bad = [value for value in values if value < 0 or value > 28]
    if bad:
        raise ValueError("numeric rune/base-29 tokens must be in 0..28")
    return values


def _ngram_counts(tokens: Sequence[int], ngram_size: int) -> Counter[tuple[int, ...]]:
    n = int(ngram_size)
    if len(tokens) < n:
        return Counter()
    return Counter(tuple(int(v) for v in tokens[idx : idx + n]) for idx in range(len(tokens) - n + 1))


def ngram_metrics(tokens: Sequence[int], ngram_size: int) -> dict[str, float | int]:
    counts = _ngram_counts(tokens, ngram_size)
    total = sum(counts.values())
    if total <= 0:
        return {
            "repeated_rate": 0.0,
            "unique_fraction": 0.0,
            "max_repeat_count": 0,
        }
    repeated_positions = sum(count for count in counts.values() if count > 1)
    return {
        "repeated_rate": float(repeated_positions / total),
        "unique_fraction": float(len(counts) / total),
        "max_repeat_count": int(max(counts.values())),
    }


def token_diversity_metrics(tokens: Sequence[int]) -> dict[str, float]:
    vals = [int(v) for v in tokens]
    counts = Counter(vals)
    length = len(vals)
    probs = [float(count) / float(length) for count in counts.values()] if length else []
    entropy = -sum(p * math.log(p) for p in probs if p > 0.0)
    entropy_norm = entropy / math.log(29.0) if length else 0.0
    return {
        "token_unique_fraction": float(len(counts) / length) if length else 0.0,
        "token_entropy_norm": float(entropy_norm),
        "low_diversity_penalty": float(1.0 - entropy_norm),
    }


def period_lane_metrics(tokens: Sequence[int], period: int) -> dict[str, float]:
    lanes = [[int(tokens[idx]) for idx in range(offset, len(tokens), int(period))] for offset in range(int(period))]
    repeat_rates: list[float] = []
    diversity_rates: list[float] = []
    for lane in lanes:
        repeat_rates.append(float(ngram_metrics(lane, 3)["repeated_rate"]))
        diversity_rates.append(float(token_diversity_metrics(lane)["token_unique_fraction"]) if lane else 0.0)
    return {
        f"period_lane_repeat_rate_mean_p{period}": float(sum(repeat_rates) / len(repeat_rates)),
        f"period_lane_repeat_rate_spread_p{period}": float(max(repeat_rates) - min(repeat_rates)),
        f"period_lane_diversity_spread_p{period}": float(max(diversity_rates) - min(diversity_rates)),
    }


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_s1_pair_rows() -> list[dict[str, Any]]:
    return _load_csv(S1_PAIR_ROWS)


def _required_token_hashes(pair_rows: Sequence[Mapping[str, Any]]) -> set[str]:
    out: set[str] = set()
    for row in pair_rows:
        for key in ("winner_token_hash", "challenger_token_hash"):
            value = str(row.get(key, "") or "")
            if value:
                out.add(value)
    return out


def load_required_token_rows(token_hashes: set[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    with UNIQUE_PARTIAL_ROWS.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            token_hash = str(row.get("partial_text_hash", "") or "")
            if token_hash in token_hashes:
                found[token_hash] = dict(row)
                if len(found) == len(token_hashes):
                    break
    return found


def _score_values_by_token(pair_rows: Sequence[Mapping[str, Any]]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = defaultdict(list)
    for row in pair_rows:
        for side in ("winner", "challenger"):
            token_hash = str(row.get(f"{side}_token_hash", "") or "")
            score = _safe_float(row.get(f"{side}_current_score"))
            if token_hash and math.isfinite(score):
                out[token_hash].append(float(score))
    return out


def _build_span_backend() -> tuple[SpanHammingBackend | None, str]:
    if not SPAN_HAMMING_ENABLED:
        return None, "disabled"
    try:
        cfg = SpanHammingConfig(debug_return_intervals=True)
        return SpanHammingBackend(config=cfg), ""
    except Exception as exc:
        return None, type(exc).__name__ + ": " + str(exc)


def _build_word_runtime() -> tuple[RuneTokenWordNgramJudgeRuntime | None, str]:
    if not WORD_NGRAM_ENABLED:
        return None, "disabled"
    if not WORD_NGRAM_SQLITE.exists():
        return None, "missing sqlite asset: " + _repo_rel(WORD_NGRAM_SQLITE)
    try:
        return (
            RuneTokenWordNgramJudgeRuntime.open_sqlite(
                WORD_NGRAM_SQLITE,
                alpha=WORD_NGRAM_ALPHA,
                miss_logp=WORD_NGRAM_MISS_LOGP,
                min_positions=WORD_NGRAM_MIN_POSITIONS,
                prefix_total_thresholds=WORD_NGRAM_PREFIX_THRESHOLDS,
            ),
            "",
        )
    except Exception as exc:
        return None, type(exc).__name__ + ": " + str(exc)


def _span_features(tokens: Sequence[int], backend: SpanHammingBackend | None, missing_reason: str) -> dict[str, Any]:
    if backend is None:
        return {
            "span_hamming_available": 0,
            "span_hamming_missing_reason": missing_reason or "unavailable",
            "span_raw_score": "",
            "span_coverage": "",
            "span_quality": "",
            "selected_interval_count": "",
            "selected_interval_total_length": "",
            "mean_selected_interval_length": "",
            "best_interval_score": "",
            "worst_selected_interval_score": "",
            "_selected_intervals": (),
        }
    try:
        stats = backend.score(tokens)
        intervals = tuple(stats.selected_intervals)
        weights = [float(item.weight) for item in intervals]
        total_len = int(sum(int(item.length) for item in intervals))
        return {
            "span_hamming_available": 1,
            "span_hamming_missing_reason": "",
            "span_raw_score": float(stats.span_raw),
            "span_coverage": float(stats.coverage),
            "span_quality": float(stats.quality),
            "selected_interval_count": int(stats.n_intervals_selected),
            "selected_interval_total_length": total_len,
            "mean_selected_interval_length": float(total_len / len(intervals)) if intervals else 0.0,
            "best_interval_score": max(weights) if weights else 0.0,
            "worst_selected_interval_score": min(weights) if weights else 0.0,
            "_selected_intervals": intervals,
        }
    except Exception as exc:
        return {
            "span_hamming_available": 0,
            "span_hamming_missing_reason": type(exc).__name__ + ": " + str(exc),
            "span_raw_score": "",
            "span_coverage": "",
            "span_quality": "",
            "selected_interval_count": "",
            "selected_interval_total_length": "",
            "mean_selected_interval_length": "",
            "best_interval_score": "",
            "worst_selected_interval_score": "",
            "_selected_intervals": (),
        }


def _word_features(
    tokens: Sequence[int],
    intervals: Sequence[Any],
    runtime: RuneTokenWordNgramJudgeRuntime | None,
    missing_reason: str,
) -> dict[str, Any]:
    if runtime is None:
        return {
            "word_ngram_available": 0,
            "word_ngram_active": 0,
            "word_ngram_missing_reason": missing_reason or "unavailable",
            "word_ngram_trust_tier": "",
            "word_ngram_trust_score": "",
            "word_ngram_xent": "",
            "word_ngram_backoff_xent": "",
            "word_ngram_token_count": "",
            "word_ngram_n_positions": "",
            "word_ngram_miss_rate": "",
            "word_ngram_backoff_used_rate": "",
        }
    try:
        report = runtime.score_candidate(text_idx=tokens, selected_intervals=intervals, direction=Direction.LTR)
        backoff_used_rate = ""
        used_rates = [
            _safe_float(report.used5_rate),
            _safe_float(report.used4_rate),
            _safe_float(report.used3_rate),
        ]
        if all(math.isfinite(value) for value in used_rates):
            backoff_used_rate = float(sum(used_rates))
        return {
            "word_ngram_available": int(bool(report.available)),
            "word_ngram_active": int(bool(report.active)),
            "word_ngram_missing_reason": str(report.inactive_reason or ""),
            "word_ngram_trust_tier": str(report.trust_tier),
            "word_ngram_trust_score": float(report.trust_score),
            "word_ngram_xent": _finite_or_blank(report.xent_3),
            "word_ngram_backoff_xent": _finite_or_blank(report.xent_backoff_5_4_3),
            "word_ngram_token_count": int(report.exact_word_count),
            "word_ngram_n_positions": int(report.n_positions),
            "word_ngram_miss_rate": _finite_or_blank(report.miss_rate),
            "word_ngram_backoff_used_rate": backoff_used_rate,
        }
    except Exception as exc:
        return {
            "word_ngram_available": 0,
            "word_ngram_active": 0,
            "word_ngram_missing_reason": type(exc).__name__ + ": " + str(exc),
            "word_ngram_trust_tier": "",
            "word_ngram_trust_score": "",
            "word_ngram_xent": "",
            "word_ngram_backoff_xent": "",
            "word_ngram_token_count": "",
            "word_ngram_n_positions": "",
            "word_ngram_miss_rate": "",
            "word_ngram_backoff_used_rate": "",
        }


def build_candidate_feature_rows(
    *,
    token_rows: Mapping[str, Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    span_backend: SpanHammingBackend | None = None,
    span_missing_reason: str = "",
    word_runtime: RuneTokenWordNgramJudgeRuntime | None = None,
    word_missing_reason: str = "",
) -> list[dict[str, Any]]:
    score_values = _score_values_by_token(pair_rows)
    out: list[dict[str, Any]] = []
    required_hashes = sorted(_required_token_hashes(pair_rows))
    started = time.perf_counter()
    total = len(required_hashes)
    for index, token_hash in enumerate(required_hashes, start=1):
        if index == 1 or index % 100 == 0 or index == total:
            elapsed = time.perf_counter() - started
            rate = index / elapsed if elapsed > 0.0 else 0.0
            eta = (total - index) / rate if rate > 0.0 else 0.0
            print(
                f"[{RUN_LABEL}] candidate_features {index}/{total} "
                f"elapsed={elapsed:.1f}s eta={eta:.1f}s"
            )
        row = dict(token_rows.get(token_hash, {}))
        base: dict[str, Any] = {
            "token_hash": token_hash,
            "token_length": "",
            "numeric_valid": 0,
            "numeric_missing_reason": "",
        }
        scores = score_values.get(token_hash, [])
        if scores:
            base.update(
                current_score_mean=float(sum(scores) / len(scores)),
                current_score_min=float(min(scores)),
                current_score_max=float(max(scores)),
                current_score_value_count=len({round(float(value), 15) for value in scores}),
            )
        else:
            base.update(
                current_score_mean="",
                current_score_min="",
                current_score_max="",
                current_score_value_count=0,
            )
        try:
            tokens = parse_numeric_tokens(str(row.get("token_sequence_text", "")))
            base["token_length"] = int(len(tokens))
            base["numeric_valid"] = 1
            base.update(token_diversity_metrics(tokens))
            for ngram_size in NGRAM_SIZES:
                metrics = ngram_metrics(tokens, ngram_size)
                base[f"repeated_{ngram_size}gram_rate"] = float(metrics["repeated_rate"])
                base[f"unique_{ngram_size}gram_fraction"] = float(metrics["unique_fraction"])
                base[f"max_ngram_repeat_count_{ngram_size}"] = int(metrics["max_repeat_count"])
            for period in DIAGNOSTIC_PERIODS:
                base.update(period_lane_metrics(tokens, period))
            span = _span_features(tokens, span_backend, span_missing_reason)
            intervals = tuple(span.pop("_selected_intervals", ()))
            base.update(span)
            base.update(_word_features(tokens, intervals, word_runtime, word_missing_reason))
        except Exception as exc:
            base["numeric_missing_reason"] = type(exc).__name__ + ": " + str(exc)
            base.update(_empty_feature_values())
        out.append({field: base.get(field, "") for field in CANDIDATE_FEATURE_FIELDS})
    return out


def _empty_feature_values() -> dict[str, Any]:
    preserved_base_fields = {
        "token_hash",
        "token_length",
        "numeric_valid",
        "numeric_missing_reason",
        "current_score_mean",
        "current_score_min",
        "current_score_max",
        "current_score_value_count",
    }
    out = {field: "" for field in CANDIDATE_FEATURE_FIELDS if field not in preserved_base_fields}
    out.update(
        span_hamming_available=0,
        span_hamming_missing_reason="numeric tokens unavailable",
        word_ngram_available=0,
        word_ngram_active=0,
        word_ngram_missing_reason="numeric tokens unavailable",
    )
    return out


def _feature_value(
    *,
    feature_name: str,
    side: str,
    pair_row: Mapping[str, Any],
    candidate_rows_by_hash: Mapping[str, Mapping[str, Any]],
) -> Any:
    if feature_name == "current_score":
        return pair_row.get(f"{side}_current_score", "")
    token_hash = str(pair_row.get(f"{side}_token_hash", "") or "")
    return dict(candidate_rows_by_hash.get(token_hash, {})).get(feature_name, "")


def _preference(*, winner_value: Any, challenger_value: Any, direction: str) -> tuple[int, int, int, int, str, float | str]:
    winner = _safe_float(winner_value)
    challenger = _safe_float(challenger_value)
    if not math.isfinite(winner) or not math.isfinite(challenger):
        return 0, 0, 0, 1, "missing winner or challenger feature value", ""
    if winner == challenger:
        return 0, 0, 1, 0, "", 0.0
    if direction == "higher":
        prefers_better = winner > challenger
        margin = winner - challenger
    elif direction == "lower":
        prefers_better = winner < challenger
        margin = challenger - winner
    else:
        return 0, 0, 0, 1, "unknown feature direction", ""
    return int(prefers_better), int(not prefers_better), 0, 0, "", float(margin)


def build_pair_feature_rows(
    *,
    pair_rows: Sequence[Mapping[str, Any]],
    candidate_feature_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidate_rows_by_hash = {str(row.get("token_hash", "")): dict(row) for row in candidate_feature_rows}
    out: list[dict[str, Any]] = []
    for pair in pair_rows:
        pair_group = (
            "current_score_correct"
            if int(pair.get("current_score_correct", 0) or 0) == 1
            else "current_score_misranked"
        )
        for feature in FEATURE_DEFINITIONS:
            name = feature["name"]
            direction = feature["direction"]
            winner_value = _feature_value(
                feature_name=name,
                side="winner",
                pair_row=pair,
                candidate_rows_by_hash=candidate_rows_by_hash,
            )
            challenger_value = _feature_value(
                feature_name=name,
                side="challenger",
                pair_row=pair,
                candidate_rows_by_hash=candidate_rows_by_hash,
            )
            prefers_better, prefers_worse, tie, missing, reason, margin = _preference(
                winner_value=winner_value,
                challenger_value=challenger_value,
                direction=direction,
            )
            row = {
                "pair_id": pair.get("pair_id", ""),
                "artifact_path": pair.get("artifact_path", ""),
                "fixture_id": pair.get("fixture_id", ""),
                "fixture_seed": pair.get("fixture_seed", ""),
                "search_seed": pair.get("search_seed", ""),
                "token_length": pair.get("token_length", ""),
                "winner_candidate_hash": pair.get("winner_candidate_hash", ""),
                "challenger_candidate_hash": pair.get("challenger_candidate_hash", ""),
                "winner_token_hash": pair.get("winner_token_hash", ""),
                "challenger_token_hash": pair.get("challenger_token_hash", ""),
                "winner_truth_match": pair.get("winner_truth_match", ""),
                "challenger_truth_match": pair.get("challenger_truth_match", ""),
                "truth_gap": pair.get("truth_gap", ""),
                "winner_current_score": pair.get("winner_current_score", ""),
                "challenger_current_score": pair.get("challenger_current_score", ""),
                "current_score_margin": pair.get("current_score_margin", ""),
                "current_score_correct": pair.get("current_score_correct", ""),
                "pair_group": pair_group,
                "feature_family": feature["family"],
                "feature_name": name,
                "feature_direction": direction,
                "winner_feature_value": _finite_or_blank(winner_value),
                "challenger_feature_value": _finite_or_blank(challenger_value),
                "feature_margin": margin,
                "feature_prefers_truth_better": prefers_better,
                "feature_prefers_truth_worse": prefers_worse,
                "feature_tie": tie,
                "feature_missing": missing,
                "feature_missing_reason": reason,
                "text_pair_key": _pair_key(pair.get("winner_token_hash", ""), pair.get("challenger_token_hash", "")),
                "candidate_hash_pair_key": _pair_key(
                    pair.get("winner_candidate_hash", ""),
                    pair.get("challenger_candidate_hash", ""),
                ),
            }
            out.append({field: row.get(field, "") for field in PAIR_FEATURE_FIELDS})
    return out


def _dominant_fraction(values: Sequence[str]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    return float(max(counts.values()) / total) if total else 0.0


def _unique_rows_by_text_pair(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    unique: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        unique.setdefault(str(row.get("text_pair_key", "")), row)
    return list(unique.values())


def build_feature_summary_rows(pair_feature_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in pair_feature_rows:
        grouped[
            (
                str(row.get("feature_family", "")),
                str(row.get("feature_name", "")),
                str(row.get("feature_direction", "")),
            )
        ].append(row)

    out: list[dict[str, Any]] = []
    for (family, name, direction), rows in sorted(grouped.items()):
        available = [row for row in rows if int(row.get("feature_missing", 0) or 0) == 0]
        missing = [row for row in rows if int(row.get("feature_missing", 0) or 0) == 1]
        misranked = [row for row in available if str(row.get("pair_group", "")) == "current_score_misranked"]
        controls = [row for row in available if str(row.get("pair_group", "")) == "current_score_correct"]
        unique_available = _unique_rows_by_text_pair(available)
        out.append(
            {
                "feature_family": family,
                "feature_name": name,
                "feature_direction": direction,
                "available_pair_count": len(available),
                "missing_pair_count": len(missing),
                "all_pairs_prefers_truth_better": sum(int(row.get("feature_prefers_truth_better", 0) or 0) for row in available),
                "all_pairs_prefers_truth_worse": sum(int(row.get("feature_prefers_truth_worse", 0) or 0) for row in available),
                "all_pairs_tie": sum(int(row.get("feature_tie", 0) or 0) for row in available),
                "current_misranked_prefers_truth_better": sum(int(row.get("feature_prefers_truth_better", 0) or 0) for row in misranked),
                "current_misranked_prefers_truth_worse": sum(int(row.get("feature_prefers_truth_worse", 0) or 0) for row in misranked),
                "current_misranked_tie": sum(int(row.get("feature_tie", 0) or 0) for row in misranked),
                "current_correct_controls_prefers_truth_better": sum(int(row.get("feature_prefers_truth_better", 0) or 0) for row in controls),
                "current_correct_controls_prefers_truth_worse": sum(int(row.get("feature_prefers_truth_worse", 0) or 0) for row in controls),
                "current_correct_controls_tie": sum(int(row.get("feature_tie", 0) or 0) for row in controls),
                "unique_text_pair_count": len(unique_available),
                "unique_text_pair_prefers_truth_better": sum(int(row.get("feature_prefers_truth_better", 0) or 0) for row in unique_available),
                "unique_text_pair_prefers_truth_worse": sum(int(row.get("feature_prefers_truth_worse", 0) or 0) for row in unique_available),
                "unique_text_pair_tie": sum(int(row.get("feature_tie", 0) or 0) for row in unique_available),
                "rescues": sum(int(row.get("feature_prefers_truth_better", 0) or 0) for row in misranked),
                "breaks": sum(int(row.get("feature_prefers_truth_worse", 0) or 0) for row in controls),
                "net": (
                    sum(int(row.get("feature_prefers_truth_better", 0) or 0) for row in misranked)
                    - sum(int(row.get("feature_prefers_truth_worse", 0) or 0) for row in controls)
                ),
                "dominant_pair_fraction": _dominant_fraction([str(row.get("text_pair_key", "")) for row in available]),
            }
        )
    return out


def build_missingness_rows(pair_feature_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in pair_feature_rows:
        if int(row.get("feature_missing", 0) or 0) != 1:
            continue
        grouped[
            (
                str(row.get("feature_family", "")),
                str(row.get("feature_name", "")),
                str(row.get("feature_missing_reason", "") or "missing"),
            )
        ].append(row)
    out = []
    for (family, name, reason), rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        out.append(
            {
                "feature_family": family,
                "feature_name": name,
                "missing_reason": reason,
                "row_count": len(rows),
                "unique_text_pair_count": len({str(row.get("text_pair_key", "")) for row in rows}),
                "unique_candidate_hash_pair_count": len({str(row.get("candidate_hash_pair_key", "")) for row in rows}),
            }
        )
    return out


def build_summary(
    *,
    pair_rows: Sequence[Mapping[str, Any]],
    candidate_feature_rows: Sequence[Mapping[str, Any]],
    pair_feature_rows: Sequence[Mapping[str, Any]],
    feature_summary_rows: Sequence[Mapping[str, Any]],
    elapsed_seconds: float,
) -> dict[str, Any]:
    current_misranked = [row for row in pair_rows if int(row.get("current_score_correct", 0) or 0) == 0]
    current_correct = [row for row in pair_rows if int(row.get("current_score_correct", 0) or 0) == 1]
    text_pair_keys = [_pair_key(row.get("winner_token_hash", ""), row.get("challenger_token_hash", "")) for row in pair_rows]
    candidate_pair_keys = [
        _pair_key(row.get("winner_candidate_hash", ""), row.get("challenger_candidate_hash", ""))
        for row in pair_rows
    ]
    span_rows = [row for row in candidate_feature_rows if int(row.get("span_hamming_available", 0) or 0) == 1]
    word_rows = [row for row in candidate_feature_rows if int(row.get("word_ngram_available", 0) or 0) == 1]
    word_active_rows = [row for row in candidate_feature_rows if int(row.get("word_ngram_active", 0) or 0) == 1]
    top_features = sorted(
        feature_summary_rows,
        key=lambda row: (
            int(row.get("net", 0) or 0),
            int(row.get("rescues", 0) or 0),
            -int(row.get("breaks", 0) or 0),
        ),
        reverse=True,
    )[:10]
    return {
        "run_label": RUN_LABEL,
        "updated_utc": _utc_now_text(),
        "elapsed_seconds": float(elapsed_seconds),
        "input_pair_rows": S1_PAIR_ROWS_REL,
        "input_unique_partial_rows": UNIQUE_PARTIAL_ROWS_REL,
        "output_dir": OUTPUT_DIR_REL,
        "runtime_behavior_changed": False,
        "representation_rule": "Numeric rune/base-29 token sequences only; allowed values are 0..28.",
        "truth_is_evaluation_only": True,
        "candidate_feature_row_count": len(candidate_feature_rows),
        "pair_count": len(pair_rows),
        "pair_feature_row_count": len(pair_feature_rows),
        "feature_count": len(feature_summary_rows),
        "current_score_misranked_pair_count": len(current_misranked),
        "current_score_correct_control_pair_count": len(current_correct),
        "unique_numeric_text_pair_count": len(set(text_pair_keys)),
        "unique_candidate_hash_pair_count": len(set(candidate_pair_keys)),
        "artifact_count": len({str(row.get("artifact_path", "")) for row in pair_rows}),
        "fixture_search_cell_count": len(
            {
                (str(row.get("fixture_seed", "")), str(row.get("search_seed", "")))
                for row in pair_rows
            }
        ),
        "dominant_text_pair_fraction": _dominant_fraction(text_pair_keys),
        "dominant_candidate_hash_pair_fraction": _dominant_fraction(candidate_pair_keys),
        "span_hamming_candidate_available_count": len(span_rows),
        "span_hamming_candidate_missing_count": len(candidate_feature_rows) - len(span_rows),
        "word_ngram_candidate_available_count": len(word_rows),
        "word_ngram_candidate_active_count": len(word_active_rows),
        "word_ngram_candidate_missing_count": len(candidate_feature_rows) - len(word_rows),
        "top_net_features": [dict(row) for row in top_features],
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=True, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_readout(summary: Mapping[str, Any], feature_summary_rows: Sequence[Mapping[str, Any]]) -> str:
    by_family: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in feature_summary_rows:
        by_family[str(row.get("feature_family", ""))].append(row)

    def family_lines(family: str) -> list[str]:
        rows = sorted(
            by_family.get(family, []),
            key=lambda row: (int(row.get("net", 0) or 0), int(row.get("rescues", 0) or 0)),
            reverse=True,
        )[:5]
        if not rows:
            return ["- no rows"]
        return [
            (
                f"- `{row['feature_name']}` direction `{row['feature_direction']}`: "
                f"rescues `{row['rescues']}`, breaks `{row['breaks']}`, net `{row['net']}`, "
                f"available `{row['available_pair_count']}`"
            )
            for row in rows
        ]

    lines = [
        "# Scorer Component Feature Audit v1",
        "",
        "## Purpose",
        "",
        "Audit existing report-safe scorer components on S1 current-rescored historical pairs.",
        "This is report-only and does not change runtime selection or acceptance.",
        "",
        "## Inputs",
        "",
        f"- pair rows: `{summary['input_pair_rows']}`",
        f"- unique partial text rows: `{summary['input_unique_partial_rows']}`",
        "",
        "## Dataset counts",
        "",
        f"- candidate feature rows: `{summary['candidate_feature_row_count']}`",
        f"- pair rows: `{summary['pair_count']}`",
        f"- pair feature rows: `{summary['pair_feature_row_count']}`",
        f"- current-score misranked pairs: `{summary['current_score_misranked_pair_count']}`",
        f"- current-score correct controls: `{summary['current_score_correct_control_pair_count']}`",
        f"- unique numeric text pairs: `{summary['unique_numeric_text_pair_count']}`",
        f"- unique candidate-hash pairs: `{summary['unique_candidate_hash_pair_count']}`",
        f"- artifacts represented: `{summary['artifact_count']}`",
        f"- fixture/search cells represented: `{summary['fixture_search_cell_count']}`",
        f"- dominant text-pair fraction: `{summary['dominant_text_pair_fraction']:.4f}`",
        f"- dominant candidate-hash-pair fraction: `{summary['dominant_candidate_hash_pair_fraction']:.4f}`",
        "",
        "## Feature availability",
        "",
        f"- span-Hamming available candidates: `{summary['span_hamming_candidate_available_count']}`",
        f"- span-Hamming missing candidates: `{summary['span_hamming_candidate_missing_count']}`",
        f"- word-ngram available candidates: `{summary['word_ngram_candidate_available_count']}`",
        f"- word-ngram active candidates: `{summary['word_ngram_candidate_active_count']}`",
        f"- word-ngram missing candidates: `{summary['word_ngram_candidate_missing_count']}`",
        "",
        "## Motif/repetition result",
        "",
        *family_lines("motif_repetition"),
        "",
        "## Period-lane result",
        "",
        *family_lines("period_lane"),
        "",
        "## Span-Hamming result",
        "",
        *family_lines("span_hamming"),
        "",
        "## Word-ngram result",
        "",
        *family_lines("word_ngram"),
        "",
        "## Caveats",
        "",
        "- `winner` means truth-better candidate, not scorer-selected candidate.",
        "- Truth fields are evaluation labels only.",
        "- Feature preference is pairwise and report-only.",
        "- Features with high break counts should not become gates without S2 simulation and held-out checks.",
        "",
        "## Recommendation for next stage",
        "",
        "Review feature families by unique text pair and controls before any S2 gate simulation.",
    ]
    return "\n".join(lines) + "\n"


def write_outputs() -> dict[str, Any]:
    started = time.perf_counter()
    print(f"[{RUN_LABEL}] loading S1 pair rows from {S1_PAIR_ROWS_REL}")
    pair_rows = load_s1_pair_rows()
    token_hashes = _required_token_hashes(pair_rows)
    print(f"[{RUN_LABEL}] loading {len(token_hashes)} required numeric token rows")
    token_rows = load_required_token_rows(token_hashes)
    missing_hashes = sorted(token_hashes - set(token_rows))
    if missing_hashes:
        print(f"[{RUN_LABEL}] warning: missing token rows for {len(missing_hashes)} hashes")

    span_backend, span_missing_reason = _build_span_backend()
    word_runtime, word_missing_reason = _build_word_runtime()
    try:
        print(f"[{RUN_LABEL}] building candidate features")
        candidate_rows = build_candidate_feature_rows(
            token_rows=token_rows,
            pair_rows=pair_rows,
            span_backend=span_backend,
            span_missing_reason=span_missing_reason,
            word_runtime=word_runtime,
            word_missing_reason=word_missing_reason,
        )
    finally:
        if word_runtime is not None:
            word_runtime.close()

    print(f"[{RUN_LABEL}] building pair feature rows")
    pair_feature_rows = build_pair_feature_rows(pair_rows=pair_rows, candidate_feature_rows=candidate_rows)
    feature_summary_rows = build_feature_summary_rows(pair_feature_rows)
    missingness_rows = build_missingness_rows(pair_feature_rows)
    summary = build_summary(
        pair_rows=pair_rows,
        candidate_feature_rows=candidate_rows,
        pair_feature_rows=pair_feature_rows,
        feature_summary_rows=feature_summary_rows,
        elapsed_seconds=time.perf_counter() - started,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(
        OUTPUT_DIR / "scorer_component_feature_audit_candidate_features.csv",
        candidate_rows,
        CANDIDATE_FEATURE_FIELDS,
    )
    _write_jsonl(OUTPUT_DIR / "scorer_component_feature_audit_candidate_features.jsonl", candidate_rows)
    _write_csv(
        OUTPUT_DIR / "scorer_component_feature_audit_pair_features.csv",
        pair_feature_rows,
        PAIR_FEATURE_FIELDS,
    )
    _write_jsonl(OUTPUT_DIR / "scorer_component_feature_audit_pair_features.jsonl", pair_feature_rows)
    _write_csv(
        OUTPUT_DIR / "scorer_component_feature_audit_feature_summary.csv",
        feature_summary_rows,
        FEATURE_SUMMARY_FIELDS,
    )
    _write_csv(
        OUTPUT_DIR / "scorer_component_feature_audit_missingness.csv",
        missingness_rows,
        MISSINGNESS_FIELDS,
    )
    _write_json(OUTPUT_DIR / "scorer_component_feature_audit_summary.json", summary)
    (OUTPUT_DIR / "scorer_component_feature_audit_readout.md").write_text(
        build_readout(summary, feature_summary_rows),
        encoding="utf-8",
    )

    print(
        f"[{RUN_LABEL}] done candidates={summary['candidate_feature_row_count']} "
        f"pairs={summary['pair_count']} features={summary['feature_count']} "
        f"output_dir={summary['output_dir']}"
    )
    return summary


def main() -> None:
    write_outputs()


if __name__ == "__main__":
    main()
