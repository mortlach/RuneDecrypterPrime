from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np

if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parents[4]
    _SRC = _ROOT / "src"
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    if _SRC.exists() and str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.scoring.span_hamming import (
    SpanCalibratedAssets,
    SpanHammingBackend,
    SpanHammingConfig,
    SpanHammingLmAssetsV2,
)
from rune_decrypter_prime.scoring.word_ngrams import (
    RuneTokenWordNgramMemoryModel,
    RuneTokenWordNgramScorer,
    summarize_prefix_total_confidence,
    summarize_word_ngram_report_trust,
    word_ngram_report_is_active,
)
from tools.benchmarks.scoring.span_hamming_nose.usage_benchmark_common import (
    SpanHammingBenchmarkRuntimeConfig,
    score_text_with_assets,
)
from tests.scoring.span_hamming.nowli_hard_cases import (
    auc_from_scores,
    chunk_ranges,
    exact_match_feasibility_metrics,
    extract_exact_match_tokens,
    interval_density,
    load_nowli_hard_cases_v1,
    long_interval_distance_stats,
    match_ratio,
    segment_exact_match_tokens,
    unique_ngram_ratio,
    vector_by_length,
    word_token_sets_by_len,
)


REPO_ROOT = Path(__file__).resolve().parents[4]

DATASET_JSON = Path("tests/scoring/span_hamming/data/nowli_hard_cases_v1.json")
SPAN_ASSETS_DIR = Path("output/tools/benchmarks/scoring/span_hamming_nose_assets_v1")
LM_ASSETS_JSON = Path(
    "output/tools/benchmarks/scoring/span_hamming_nose_assets_wordlen_v1/"
    "20260304T053856Z__span_hamming_nose_assets_wordlen_v1/"
    "span_hamming_nose_assets_wordlen_v1.json"
)
OUTPUT_ROOT = Path("output/tools/benchmarks/scoring/span_hamming_nose_nowli_hard_cases")
RUN_LABEL = "report_nowli_hard_cases_v1"
WORD_NGRAM_TOKENIZED_DIR = Path("assets_packed/tokenized_pg")
WORD_NGRAM_BOOK_LIMIT = 64
WORD_NGRAM_DIRECTION = "ltr"
WORD_NGRAM_ORDERS = (3, 4, 5)
WORD_NGRAM_ALPHA = 0.4
WORD_NGRAM_MISS_LOGP = -20.0
WORD_NGRAM_MIN_POSITIONS = 12
WORD_NGRAM_PREFIX_TOTAL_THRESHOLDS = (1, 10, 100)

DIRECTION = "ltr"
CLAMP_MIN = 1e-6
CLAMP_MAX = 1.0 - 1e-6
SPAN_CONFIG = SpanHammingConfig()
FOCUS_BINS = tuple(range(8, 15))
N_CHUNKS = 4

REPORT_PROFILES = {
    "span_only_relaxed": SpanHammingBenchmarkRuntimeConfig(
        objective_family="pct",
        coverage_min=0.0,
        quality_min=0.0,
        span_pct_min=None,
        char_pct_min=None,
        combine_mode="min",
        weight_span=1.0,
        weight_char=0.0,
        use_char_channel=False,
        gate_fail_policy="score_floor",
        gate_score_floor=None,
        lm_weight=0.0,
        lm_profile_source="span_raw_by_len",
        lm_tail_start_index=5,
    ),
    "span_lm_relaxed": SpanHammingBenchmarkRuntimeConfig(
        objective_family="pct",
        coverage_min=0.0,
        quality_min=0.0,
        span_pct_min=None,
        char_pct_min=None,
        combine_mode="min",
        weight_span=1.0,
        weight_char=0.0,
        use_char_channel=False,
        gate_fail_policy="score_floor",
        gate_score_floor=None,
        lm_weight=0.75,
        lm_weight_margin=1.0,
        lm_weight_mean_bin_index=1.0,
        lm_weight_mean_bin_length=1.0,
        lm_weight_tail_mass=1.0,
        lm_profile_source="span_raw_by_len",
        lm_tail_start_index=5,
    ),
    "span_lm_strict_gate": SpanHammingBenchmarkRuntimeConfig(
        objective_family="pct",
        coverage_min=0.0,
        quality_min=0.0,
        span_pct_min=0.98,
        char_pct_min=None,
        combine_mode="min",
        weight_span=1.0,
        weight_char=0.0,
        use_char_channel=False,
        gate_fail_policy="score_floor",
        gate_score_floor=None,
        lm_weight=0.75,
        lm_weight_margin=1.0,
        lm_weight_mean_bin_index=1.0,
        lm_weight_mean_bin_length=1.0,
        lm_weight_tail_mass=1.0,
        lm_profile_source="span_raw_by_len",
        lm_tail_start_index=5,
    ),
}


def _resolve_repo_path(path_like: Path | str) -> Path:
    path = Path(path_like).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    else:
        path = path.resolve()
    return path


def _utc_now_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _summarize(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return {
            "n": 0.0,
            "mean": 0.0,
            "min": 0.0,
            "p25": 0.0,
            "median": 0.0,
            "p75": 0.0,
            "max": 0.0,
        }
    return {
        "n": float(arr.size),
        "mean": float(np.mean(arr)),
        "min": float(np.min(arr)),
        "p25": float(np.quantile(arr, 0.25)),
        "median": float(np.quantile(arr, 0.5)),
        "p75": float(np.quantile(arr, 0.75)),
        "max": float(np.max(arr)),
    }


def _json_compact(obj: object) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


def _focus_bin_columns(
    *,
    prefix: str,
    values_by_len: dict[int, float],
) -> dict[str, float]:
    out: dict[str, float] = {}
    for length in FOCUS_BINS:
        out[f"{prefix}_len_{int(length)}"] = float(values_by_len.get(int(length), 0.0))
    return out


def _chunk_span_pct_stats(
    text_idx: tuple[int, ...],
    *,
    backend: SpanHammingBackend,
    span_assets: SpanCalibratedAssets,
) -> dict[str, object]:
    chunk_scores: list[float] = []
    for start, end in chunk_ranges(len(text_idx), N_CHUNKS):
        chunk = text_idx[int(start) : int(end)]
        if not chunk:
            chunk_scores.append(0.0)
            continue
        stats = backend.score(chunk)
        bucket = span_assets.select_bucket(DIRECTION, len(chunk))
        scored = span_assets.score_span_raw_in_bucket(
            direction=DIRECTION,
            length_bucket=int(bucket),
            span_raw=float(stats.span_raw),
            clamp_min=CLAMP_MIN,
            clamp_max=CLAMP_MAX,
        )
        chunk_scores.append(float(scored.span_pct))
    arr = np.asarray(chunk_scores, dtype=np.float64)
    return {
        "chunk_span_pct_json": _json_compact([float(v) for v in chunk_scores]),
        "chunk_min_span_pct": float(np.min(arr) if arr.size else 0.0),
        "chunk_std_span_pct": float(np.std(arr, ddof=0) if arr.size else 0.0),
    }


def _select_word_ngram_books(root: Path, *, limit: int | None) -> list[Path]:
    paths = sorted(root.glob("*_fwd.npz"))
    ranked = sorted(
        paths,
        key=lambda p: (hashlib.sha1(p.name.encode("utf-8")).hexdigest(), p.name),
    )
    if limit is None or int(limit) <= 0:
        return ranked
    return ranked[: int(limit)]


def main() -> None:
    dataset_fp = _resolve_repo_path(DATASET_JSON)
    span_assets_dir = _resolve_repo_path(SPAN_ASSETS_DIR)
    lm_assets_json = _resolve_repo_path(LM_ASSETS_JSON)
    word_ngram_tokenized_dir = _resolve_repo_path(WORD_NGRAM_TOKENIZED_DIR)
    output_root = _resolve_repo_path(OUTPUT_ROOT)
    run_dir = output_root / f"{_utc_now_label()}__{RUN_LABEL}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print("[report_nowli_hard_cases_v1] loading frozen hard-case dataset...")
    dataset = load_nowli_hard_cases_v1(dataset_fp)
    print(f"[report_nowli_hard_cases_v1] loaded {len(dataset.cases)} cases from {dataset.version}")

    print("[report_nowli_hard_cases_v1] loading local span-hamming assets...")
    backend = SpanHammingBackend(config=SpanHammingConfig(debug_return_intervals=True))
    span_assets = SpanCalibratedAssets.load(span_assets_dir)
    lm_assets = SpanHammingLmAssetsV2.load(lm_assets_json)
    word_sets = word_token_sets_by_len(getattr(backend, "_words_by_len", {}))
    print("[report_nowli_hard_cases_v1] building tiny in-memory rune-token 3/4/5-gram model...")
    model_paths = _select_word_ngram_books(
        word_ngram_tokenized_dir,
        limit=WORD_NGRAM_BOOK_LIMIT,
    )
    word3_model = RuneTokenWordNgramMemoryModel.from_tokenized_npz_paths(
        model_paths,
        pt_key="pt_nose_data",
        wli_key="wli_nose_data",
        orders=WORD_NGRAM_ORDERS,
    )
    word3_scorer = RuneTokenWordNgramScorer(
        word3_model,
        alpha=WORD_NGRAM_ALPHA,
        miss_logp=WORD_NGRAM_MISS_LOGP,
    )
    print(
        "[report_nowli_hard_cases_v1] "
        f"word_ngram_books={len(model_paths)} direction={WORD_NGRAM_DIRECTION}",
    )

    case_rows: list[dict] = []
    metrics: dict[str, dict[str, float]] = {}
    target = dataset.shared_target_plaintext_idx
    case_diag_by_id: dict[str, dict[str, object]] = {}

    print("[report_nowli_hard_cases_v1] computing backend diagnostics...")
    for case in dataset.cases:
        stats = backend.score(case.candidate_plaintext_idx)
        span_raw_by_len = vector_by_length(stats.length_bins, stats.span_raw_by_len)
        chars_covered_by_len = vector_by_length(stats.length_bins, stats.chars_covered_by_len)
        quality_by_len = vector_by_length(stats.length_bins, stats.quality_by_len)
        selected_intervals_by_len = vector_by_length(stats.length_bins, stats.selected_intervals_by_len)
        long_stats = long_interval_distance_stats(stats.selected_intervals, min_len=min(FOCUS_BINS), max_len=max(FOCUS_BINS))
        exact_tokens = extract_exact_match_tokens(case.candidate_plaintext_idx, stats.selected_intervals)
        exact_segments = segment_exact_match_tokens(exact_tokens)
        exact_stats = exact_match_feasibility_metrics(
            case.candidate_plaintext_idx,
            stats.selected_intervals,
            word_sets_by_len=word_sets,
        )
        token_segments = tuple(tuple(tok.token for tok in seg) for seg in exact_segments)
        word3_diag = word3_scorer.score_segments_with_diagnostics(token_segments)
        word3 = word3_diag.score
        word3_conf = summarize_prefix_total_confidence(
            word3_diag.prefix_totals_3,
            thresholds=WORD_NGRAM_PREFIX_TOTAL_THRESHOLDS,
        )
        word3_report_active = word_ngram_report_is_active(
            n_positions=int(word3.n_positions),
            min_positions=WORD_NGRAM_MIN_POSITIONS,
        )
        word3_trust = summarize_word_ngram_report_trust(
            n_positions=int(word3.n_positions),
            min_positions=WORD_NGRAM_MIN_POSITIONS,
            prefix_total_ge_10_rate=float(word3_conf["prefix_total_ge_10_rate"]),
            prefix_total_ge_100_rate=float(word3_conf["prefix_total_ge_100_rate"]),
        )
        diag: dict[str, object] = {
            "span_raw": float(stats.span_raw),
            "coverage": float(stats.coverage),
            "quality": float(stats.quality),
            "chars_covered": int(stats.chars_covered),
            "n_intervals_selected": int(stats.n_intervals_selected),
            "interval_density": interval_density(
                chars_covered=int(stats.chars_covered),
                n_intervals_selected=int(stats.n_intervals_selected),
            ),
            "unique_bigram_ratio": unique_ngram_ratio(case.candidate_plaintext_idx, 2),
            "unique_trigram_ratio": unique_ngram_ratio(case.candidate_plaintext_idx, 3),
            "span_raw_by_len_json": _json_compact(span_raw_by_len),
            "chars_covered_by_len_json": _json_compact(chars_covered_by_len),
            "quality_by_len_json": _json_compact(quality_by_len),
            "selected_intervals_by_len_json": _json_compact(selected_intervals_by_len),
            "n_long_intervals": float(long_stats["n_long_intervals"]),
            "mean_dist_long": float(long_stats["mean_dist_long"]),
            "frac_dist2_long": float(long_stats["frac_dist2_long"]),
            "exact_word_count": int(exact_stats["exact_word_count"]),
            "exact_word_char_coverage": float(exact_stats["exact_word_char_coverage"]),
            "segment_count": int(exact_stats["segment_count"]),
            "segment_word_counts_json": _json_compact(exact_stats["segment_word_counts"]),
            "adjacent_rate": float(exact_stats["adjacent_rate"]),
            "total_trigram_positions": int(exact_stats["total_trigram_positions"]),
            "total_4gram_positions": int(exact_stats["total_4gram_positions"]),
            "total_5gram_positions": int(exact_stats["total_5gram_positions"]),
            "extendable_left_rate": float(exact_stats["extendable_left_rate"]),
            "extendable_right_rate": float(exact_stats["extendable_right_rate"]),
            "extendable_either_rate": float(exact_stats["extendable_either_rate"]),
            "maximal_rate": float(exact_stats["maximal_rate"]),
            "word3_xent": (None if int(word3.n_positions) <= 0 else float(word3.xent_3)),
            "word3_backoff_xent": (
                None if int(word3.n_positions) <= 0 else float(word3.xent_backoff_5_4_3)
            ),
            "word3_positions": int(word3.n_positions),
            "word3_miss_rate": (None if int(word3.n_positions) <= 0 else float(word3.miss_rate)),
            "word3_used5_rate": (None if int(word3.n_positions) <= 0 else float(word3.used5_rate)),
            "word3_used4_rate": (None if int(word3.n_positions) <= 0 else float(word3.used4_rate)),
            "word3_used3_rate": (None if int(word3.n_positions) <= 0 else float(word3.used3_rate)),
            "word3_prefix_total_mean": float(word3_conf["prefix_total_mean"]),
            "word3_prefix_total_min": float(word3_conf["prefix_total_min"]),
            "word3_prefix_total_ge_1_rate": float(word3_conf["prefix_total_ge_1_rate"]),
            "word3_prefix_total_ge_10_rate": float(word3_conf["prefix_total_ge_10_rate"]),
            "word3_prefix_total_ge_100_rate": float(word3_conf["prefix_total_ge_100_rate"]),
            "word3_report_min_positions": int(WORD_NGRAM_MIN_POSITIONS),
            "word3_report_active": bool(word3_report_active),
            "word3_report_xent": (
                None
                if (int(word3.n_positions) <= 0 or not word3_report_active)
                else float(word3.xent_3)
            ),
            "word3_report_backoff_xent": (
                None
                if (int(word3.n_positions) <= 0 or not word3_report_active)
                else float(word3.xent_backoff_5_4_3)
            ),
            "word3_report_trust_score": float(word3_trust.trust_score),
            "word3_report_trust_tier": str(word3_trust.trust_tier),
        }
        diag.update(
            _chunk_span_pct_stats(
                case.candidate_plaintext_idx,
                backend=backend,
                span_assets=span_assets,
            )
        )
        diag.update(_focus_bin_columns(prefix="span_raw", values_by_len=span_raw_by_len))
        diag.update(_focus_bin_columns(prefix="chars_covered", values_by_len=chars_covered_by_len))
        diag.update(_focus_bin_columns(prefix="quality", values_by_len=quality_by_len))
        diag.update(_focus_bin_columns(prefix="selected_intervals", values_by_len=selected_intervals_by_len))
        case_diag_by_id[case.case_id] = diag

    for profile_name, runtime_cfg in REPORT_PROFILES.items():
        print(f"[report_nowli_hard_cases_v1] scoring profile={profile_name}")
        final_by_category: dict[str, list[float]] = defaultdict(list)
        span_by_category: dict[str, list[float]] = defaultdict(list)
        gate_by_category: dict[str, list[float]] = defaultdict(list)
        word3_by_category: dict[str, list[float]] = defaultdict(list)
        word3_report_by_category: dict[str, list[float]] = defaultdict(list)
        word3_active_by_category: dict[str, list[float]] = defaultdict(list)
        word3_trust_by_category: dict[str, list[float]] = defaultdict(list)

        use_lm = float(runtime_cfg.lm_weight) != 0.0
        for case in dataset.cases:
            scored = score_text_with_assets(
                case.candidate_plaintext_idx,
                backend=backend,
                span_assets=span_assets,
                lm_assets=(lm_assets if use_lm else None),
                direction=DIRECTION,
                clamp_min=CLAMP_MIN,
                clamp_max=CLAMP_MAX,
                runtime_config=runtime_cfg,
            )
            row = {
                "profile": profile_name,
                "case_id": case.case_id,
                "category": case.category,
                "status": case.status,
                "best_stage": case.best_stage,
                "period": case.period,
                "columns": case.columns,
                "best_match_ratio_saved": case.best_match_ratio,
                "best_match_ratio_calc": match_ratio(case.candidate_plaintext_idx, target),
                "span_pct": float(scored.span_pct),
                "lm_profile_pct": (None if scored.lm_profile_pct is None else float(scored.lm_profile_pct)),
                "runtime_total_pct": float(scored.runtime_total_pct),
                "final_pct": float(scored.final_pct),
                "gate_failed": bool(scored.gate_failed),
                "gate_reasons": "|".join(scored.gate_reasons),
                "lm_applied_to_score": bool(scored.lm_applied_to_score),
            }
            row.update(case_diag_by_id[case.case_id])
            case_rows.append(row)
            final_by_category[case.category].append(float(scored.final_pct))
            span_by_category[case.category].append(float(scored.span_pct))
            gate_by_category[case.category].append(float(bool(scored.gate_failed)))
            word3_xent = case_diag_by_id[case.case_id].get("word3_xent")
            if word3_xent is not None:
                word3_by_category[case.category].append(float(word3_xent))
            word3_report_active = bool(case_diag_by_id[case.case_id].get("word3_report_active", False))
            word3_active_by_category[case.category].append(float(word3_report_active))
            word3_trust_by_category[case.category].append(
                float(case_diag_by_id[case.case_id].get("word3_report_trust_score", 0.0))
            )
            word3_report_xent = case_diag_by_id[case.case_id].get("word3_report_xent")
            if word3_report_xent is not None:
                word3_report_by_category[case.category].append(float(word3_report_xent))

        stalled_final = list(final_by_category.get("stalled_dead_basin", []))
        other_final = [
            score
            for category, scores in final_by_category.items()
            if category != "stalled_dead_basin"
            for score in scores
        ]
        stalled_span = list(span_by_category.get("stalled_dead_basin", []))
        other_span = [
            score
            for category, scores in span_by_category.items()
            if category != "stalled_dead_basin"
            for score in scores
        ]
        near_word3 = list(word3_by_category.get("near_miss", []))
        false_word3 = list(word3_by_category.get("false_high_basin", []))
        solved_word3 = list(word3_by_category.get("solved_control", []))
        near_word3_report = list(word3_report_by_category.get("near_miss", []))
        false_word3_report = list(word3_report_by_category.get("false_high_basin", []))
        solved_word3_report = list(word3_report_by_category.get("solved_control", []))
        near_word3_backoff = [
            float(case_diag_by_id[case.case_id]["word3_report_backoff_xent"])
            for case in dataset.cases
            if case.category == "near_miss"
            and case_diag_by_id[case.case_id].get("word3_report_backoff_xent") not in (None, "")
        ]
        false_word3_backoff = [
            float(case_diag_by_id[case.case_id]["word3_report_backoff_xent"])
            for case in dataset.cases
            if case.category == "false_high_basin"
            and case_diag_by_id[case.case_id].get("word3_report_backoff_xent") not in (None, "")
        ]
        solved_word3_backoff = [
            float(case_diag_by_id[case.case_id]["word3_report_backoff_xent"])
            for case in dataset.cases
            if case.category == "solved_control"
            and case_diag_by_id[case.case_id].get("word3_report_backoff_xent") not in (None, "")
        ]
        metrics[profile_name] = {
            "stalled_vs_other_auc_span_pct": auc_from_scores(other_span, stalled_span),
            "stalled_vs_other_auc_final_pct": auc_from_scores(other_final, stalled_final),
            "stalled_dead_basin_gate_failed_rate": float(
                np.mean(np.asarray(gate_by_category.get("stalled_dead_basin", [0.0]), dtype=np.float64))
            ),
            "solved_control_gate_failed_rate": float(
                np.mean(np.asarray(gate_by_category.get("solved_control", [0.0]), dtype=np.float64))
            ),
            "false_high_vs_near_miss_final_win_rate": auc_from_scores(
                list(final_by_category.get("false_high_basin", [])),
                list(final_by_category.get("near_miss", [])),
            ),
            "false_high_vs_solved_final_win_rate": auc_from_scores(
                list(final_by_category.get("false_high_basin", [])),
                list(final_by_category.get("solved_control", [])),
            ),
            "near_miss_vs_false_high_word3_xent_auc": (
                auc_from_scores([-x for x in near_word3], [-x for x in false_word3])
                if near_word3 and false_word3
                else float("nan")
            ),
            "solved_vs_false_high_word3_xent_auc": (
                auc_from_scores([-x for x in solved_word3], [-x for x in false_word3])
                if solved_word3 and false_word3
                else float("nan")
            ),
            "near_miss_vs_false_high_word3_report_xent_auc": (
                auc_from_scores([-x for x in near_word3_report], [-x for x in false_word3_report])
                if near_word3_report and false_word3_report
                else float("nan")
            ),
            "solved_vs_false_high_word3_report_xent_auc": (
                auc_from_scores([-x for x in solved_word3_report], [-x for x in false_word3_report])
                if solved_word3_report and false_word3_report
                else float("nan")
            ),
            "near_miss_vs_false_high_word3_report_backoff_auc": (
                auc_from_scores([-x for x in near_word3_backoff], [-x for x in false_word3_backoff])
                if near_word3_backoff and false_word3_backoff
                else float("nan")
            ),
            "solved_vs_false_high_word3_report_backoff_auc": (
                auc_from_scores([-x for x in solved_word3_backoff], [-x for x in false_word3_backoff])
                if solved_word3_backoff and false_word3_backoff
                else float("nan")
            ),
            "near_miss_word3_report_active_rate": float(
                np.mean(np.asarray(word3_active_by_category.get("near_miss", [0.0]), dtype=np.float64))
            ),
            "false_high_word3_report_active_rate": float(
                np.mean(np.asarray(word3_active_by_category.get("false_high_basin", [0.0]), dtype=np.float64))
            ),
            "solved_word3_report_active_rate": float(
                np.mean(np.asarray(word3_active_by_category.get("solved_control", [0.0]), dtype=np.float64))
            ),
            "false_high_word3_report_trust_mean": float(
                np.mean(np.asarray(word3_trust_by_category.get("false_high_basin", [0.0]), dtype=np.float64))
            ),
            "near_miss_word3_report_trust_mean": float(
                np.mean(np.asarray(word3_trust_by_category.get("near_miss", [0.0]), dtype=np.float64))
            ),
            "solved_word3_report_trust_mean": float(
                np.mean(np.asarray(word3_trust_by_category.get("solved_control", [0.0]), dtype=np.float64))
            ),
        }

    category_rows: list[dict] = []
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in case_rows:
        grouped[(str(row["profile"]), str(row["category"]))].append(row)
    for (profile_name, category), rows in sorted(grouped.items()):
        match_stats = _summarize([float(r["best_match_ratio_calc"]) for r in rows])
        span_stats = _summarize([float(r["span_pct"]) for r in rows])
        final_stats = _summarize([float(r["final_pct"]) for r in rows])
        gate_stats = _summarize([float(bool(r["gate_failed"])) for r in rows])
        bigram_stats = _summarize([float(r["unique_bigram_ratio"]) for r in rows])
        trigram_stats = _summarize([float(r["unique_trigram_ratio"]) for r in rows])
        exact_word_count_stats = _summarize([float(r["exact_word_count"]) for r in rows])
        exact_cov_stats = _summarize([float(r["exact_word_char_coverage"]) for r in rows])
        trigram_pos_stats = _summarize([float(r["total_trigram_positions"]) for r in rows])
        maximal_stats = _summarize([float(r["maximal_rate"]) for r in rows])
        word3_vals = [float(r["word3_xent"]) for r in rows if r.get("word3_xent") not in (None, "")]
        word3_report_vals = [
            float(r["word3_report_xent"])
            for r in rows
            if r.get("word3_report_xent") not in (None, "")
        ]
        word3_stats = _summarize(word3_vals)
        word3_report_stats = _summarize(word3_report_vals)
        word3_pos_stats = _summarize([float(r["word3_positions"]) for r in rows])
        word3_active_stats = _summarize([float(bool(r["word3_report_active"])) for r in rows])
        word3_trust_stats = _summarize([float(r["word3_report_trust_score"]) for r in rows])
        word3_backoff_vals = [
            float(r["word3_backoff_xent"])
            for r in rows
            if r.get("word3_backoff_xent") not in (None, "")
        ]
        word3_backoff_stats = _summarize(word3_backoff_vals)
        prefix_mean_stats = _summarize([float(r["word3_prefix_total_mean"]) for r in rows])
        prefix_min_stats = _summarize([float(r["word3_prefix_total_min"]) for r in rows])
        prefix_ge_10_stats = _summarize([float(r["word3_prefix_total_ge_10_rate"]) for r in rows])
        prefix_ge_100_stats = _summarize([float(r["word3_prefix_total_ge_100_rate"]) for r in rows])
        category_rows.append(
            {
                "profile": profile_name,
                "category": category,
                "n": int(match_stats["n"]),
                "match_ratio_mean": match_stats["mean"],
                "match_ratio_median": match_stats["median"],
                "span_pct_mean": span_stats["mean"],
                "span_pct_p25": span_stats["p25"],
                "span_pct_median": span_stats["median"],
                "span_pct_p75": span_stats["p75"],
                "final_pct_mean": final_stats["mean"],
                "final_pct_p25": final_stats["p25"],
                "final_pct_median": final_stats["median"],
                "final_pct_p75": final_stats["p75"],
                "exact_word_count_mean": exact_word_count_stats["mean"],
                "exact_word_count_median": exact_word_count_stats["median"],
                "exact_word_char_coverage_mean": exact_cov_stats["mean"],
                "exact_word_char_coverage_median": exact_cov_stats["median"],
                "total_trigram_positions_mean": trigram_pos_stats["mean"],
                "total_trigram_positions_median": trigram_pos_stats["median"],
                "maximal_rate_mean": maximal_stats["mean"],
                "maximal_rate_median": maximal_stats["median"],
                "word3_xent_mean": word3_stats["mean"],
                "word3_xent_median": word3_stats["median"],
                "word3_backoff_xent_mean": word3_backoff_stats["mean"],
                "word3_backoff_xent_median": word3_backoff_stats["median"],
                "word3_positions_mean": word3_pos_stats["mean"],
                "word3_positions_median": word3_pos_stats["median"],
                "word3_report_active_rate": word3_active_stats["mean"],
                "word3_report_xent_mean": word3_report_stats["mean"],
                "word3_report_xent_median": word3_report_stats["median"],
                "word3_report_trust_mean": word3_trust_stats["mean"],
                "word3_report_trust_median": word3_trust_stats["median"],
                "word3_prefix_total_mean_mean": prefix_mean_stats["mean"],
                "word3_prefix_total_mean_median": prefix_mean_stats["median"],
                "word3_prefix_total_min_mean": prefix_min_stats["mean"],
                "word3_prefix_total_min_median": prefix_min_stats["median"],
                "word3_prefix_total_ge_10_rate_mean": prefix_ge_10_stats["mean"],
                "word3_prefix_total_ge_100_rate_mean": prefix_ge_100_stats["mean"],
                "unique_bigram_ratio_mean": bigram_stats["mean"],
                "unique_bigram_ratio_p25": bigram_stats["p25"],
                "unique_bigram_ratio_median": bigram_stats["median"],
                "unique_bigram_ratio_p75": bigram_stats["p75"],
                "unique_trigram_ratio_mean": trigram_stats["mean"],
                "unique_trigram_ratio_p25": trigram_stats["p25"],
                "unique_trigram_ratio_median": trigram_stats["median"],
                "unique_trigram_ratio_p75": trigram_stats["p75"],
                "gate_failed_rate": gate_stats["mean"],
            }
        )

    case_csv = run_dir / "cases.csv"
    category_csv = run_dir / "category_summary.csv"
    metrics_json = run_dir / "metrics.json"
    run_config_json = run_dir / "run_config.json"

    _write_csv(
        case_csv,
        case_rows,
        [
            "profile",
            "case_id",
            "category",
            "status",
            "best_stage",
            "period",
            "columns",
            "best_match_ratio_saved",
            "best_match_ratio_calc",
            "span_raw",
            "coverage",
            "quality",
            "chars_covered",
            "n_intervals_selected",
            "interval_density",
            "n_long_intervals",
            "mean_dist_long",
            "frac_dist2_long",
            "exact_word_count",
            "exact_word_char_coverage",
            "segment_count",
            "segment_word_counts_json",
            "adjacent_rate",
            "total_trigram_positions",
            "total_4gram_positions",
            "total_5gram_positions",
            "extendable_left_rate",
            "extendable_right_rate",
            "extendable_either_rate",
            "maximal_rate",
            "word3_xent",
            "word3_backoff_xent",
            "word3_positions",
            "word3_miss_rate",
            "word3_used5_rate",
            "word3_used4_rate",
            "word3_used3_rate",
            "word3_prefix_total_mean",
            "word3_prefix_total_min",
            "word3_prefix_total_ge_1_rate",
            "word3_prefix_total_ge_10_rate",
            "word3_prefix_total_ge_100_rate",
            "word3_report_min_positions",
            "word3_report_active",
            "word3_report_xent",
            "word3_report_backoff_xent",
            "word3_report_trust_score",
            "word3_report_trust_tier",
            "unique_bigram_ratio",
            "unique_trigram_ratio",
            "chunk_span_pct_json",
            "chunk_min_span_pct",
            "chunk_std_span_pct",
            "span_raw_by_len_json",
            "chars_covered_by_len_json",
            "quality_by_len_json",
            "selected_intervals_by_len_json",
            "span_raw_len_8",
            "span_raw_len_9",
            "span_raw_len_10",
            "span_raw_len_11",
            "span_raw_len_12",
            "span_raw_len_13",
            "span_raw_len_14",
            "chars_covered_len_8",
            "chars_covered_len_9",
            "chars_covered_len_10",
            "chars_covered_len_11",
            "chars_covered_len_12",
            "chars_covered_len_13",
            "chars_covered_len_14",
            "quality_len_8",
            "quality_len_9",
            "quality_len_10",
            "quality_len_11",
            "quality_len_12",
            "quality_len_13",
            "quality_len_14",
            "selected_intervals_len_8",
            "selected_intervals_len_9",
            "selected_intervals_len_10",
            "selected_intervals_len_11",
            "selected_intervals_len_12",
            "selected_intervals_len_13",
            "selected_intervals_len_14",
            "span_pct",
            "lm_profile_pct",
            "runtime_total_pct",
            "final_pct",
            "gate_failed",
            "gate_reasons",
            "lm_applied_to_score",
        ],
    )
    _write_csv(
        category_csv,
        category_rows,
        [
            "profile",
            "category",
            "n",
            "match_ratio_mean",
            "match_ratio_median",
            "span_pct_mean",
            "span_pct_p25",
            "span_pct_median",
            "span_pct_p75",
            "final_pct_mean",
            "final_pct_p25",
            "final_pct_median",
            "final_pct_p75",
            "exact_word_count_mean",
            "exact_word_count_median",
            "exact_word_char_coverage_mean",
            "exact_word_char_coverage_median",
            "total_trigram_positions_mean",
            "total_trigram_positions_median",
            "maximal_rate_mean",
            "maximal_rate_median",
            "word3_xent_mean",
            "word3_xent_median",
            "word3_backoff_xent_mean",
            "word3_backoff_xent_median",
            "word3_positions_mean",
            "word3_positions_median",
            "word3_report_active_rate",
            "word3_report_xent_mean",
            "word3_report_xent_median",
            "word3_report_trust_mean",
            "word3_report_trust_median",
            "word3_prefix_total_mean_mean",
            "word3_prefix_total_mean_median",
            "word3_prefix_total_min_mean",
            "word3_prefix_total_min_median",
            "word3_prefix_total_ge_10_rate_mean",
            "word3_prefix_total_ge_100_rate_mean",
            "unique_bigram_ratio_mean",
            "unique_bigram_ratio_p25",
            "unique_bigram_ratio_median",
            "unique_bigram_ratio_p75",
            "unique_trigram_ratio_mean",
            "unique_trigram_ratio_p25",
            "unique_trigram_ratio_median",
            "unique_trigram_ratio_p75",
            "gate_failed_rate",
        ],
    )
    metrics_json.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    run_config_json.write_text(
        json.dumps(
            {
                "dataset_json": str(dataset_fp),
                "span_assets_dir": str(span_assets_dir),
                "lm_assets_json": str(lm_assets_json),
                    "word_ngram_phase1": {
                        "tokenized_dir": str(word_ngram_tokenized_dir),
                        "book_limit": int(WORD_NGRAM_BOOK_LIMIT),
                        "books_used": [str(p.name) for p in model_paths],
                        "orders": [int(v) for v in WORD_NGRAM_ORDERS],
                        "alpha": float(WORD_NGRAM_ALPHA),
                        "miss_logp": float(WORD_NGRAM_MISS_LOGP),
                        "min_positions": int(WORD_NGRAM_MIN_POSITIONS),
                        "prefix_total_thresholds": [int(v) for v in WORD_NGRAM_PREFIX_TOTAL_THRESHOLDS],
                    },
                "profiles": {
                    key: {
                        "objective_family": cfg.objective_family,
                        "span_pct_min": cfg.span_pct_min,
                        "lm_weight": cfg.lm_weight,
                        "gate_fail_policy": cfg.gate_fail_policy,
                    }
                    for key, cfg in REPORT_PROFILES.items()
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"  wrote cases: {case_csv}")
    print(f"  wrote category summary: {category_csv}")
    print(f"  wrote metrics: {metrics_json}")
    print(f"  wrote config: {run_config_json}")
    for profile_name, vals in metrics.items():
        print(
            "[report_nowli_hard_cases_v1] "
            f"profile={profile_name} "
            f"auc_span={vals['stalled_vs_other_auc_span_pct']:.3f} "
            f"auc_final={vals['stalled_vs_other_auc_final_pct']:.3f} "
            f"stalled_gate_fail={vals['stalled_dead_basin_gate_failed_rate']:.3f} "
            f"solved_gate_fail={vals['solved_control_gate_failed_rate']:.3f}"
        )


if __name__ == "__main__":
    main()
