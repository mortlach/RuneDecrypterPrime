from __future__ import annotations

from typing import Any, Dict, Sequence

import numpy as np

from tools.benchmarks.periodic_sub_trans.common.batch_eval import score_plaintexts_chunked


def extract_word_ngram_report_fields(stats_obj: Any) -> Dict[str, Any]:
    stats = dict(stats_obj) if isinstance(stats_obj, dict) else {}
    return dict(
        word_ngram_judge_available=bool(stats.get("word_ngram_judge_available", False)),
        word_ngram_judge_active=bool(stats.get("word_ngram_judge_active", False)),
        word_ngram_judge_inactive_reason=str(
            stats.get("word_ngram_judge_inactive_reason", "") or ""
        ),
        word_ngram_judge_exact_word_count=int(
            stats.get("word_ngram_judge_exact_word_count", 0) or 0
        ),
        word_ngram_judge_segment_count=int(stats.get("word_ngram_judge_segment_count", 0) or 0),
        word_ngram_judge_n_positions=int(stats.get("word_ngram_judge_n_positions", 0) or 0),
        word_ngram_judge_xent_3=(
            float(stats["word_ngram_judge_xent_3"])
            if stats.get("word_ngram_judge_xent_3") is not None
            else None
        ),
        word_ngram_judge_backoff_xent=(
            float(stats["word_ngram_judge_backoff_xent"])
            if stats.get("word_ngram_judge_backoff_xent") is not None
            else None
        ),
        word_ngram_judge_report_xent=(
            float(stats["word_ngram_judge_report_xent"])
            if stats.get("word_ngram_judge_report_xent") is not None
            else None
        ),
        word_ngram_judge_report_backoff_xent=(
            float(stats["word_ngram_judge_report_backoff_xent"])
            if stats.get("word_ngram_judge_report_backoff_xent") is not None
            else None
        ),
        word_ngram_judge_miss_rate=(
            float(stats["word_ngram_judge_miss_rate"])
            if stats.get("word_ngram_judge_miss_rate") is not None
            else None
        ),
        word_ngram_judge_used5_rate=(
            float(stats["word_ngram_judge_used5_rate"])
            if stats.get("word_ngram_judge_used5_rate") is not None
            else None
        ),
        word_ngram_judge_used4_rate=(
            float(stats["word_ngram_judge_used4_rate"])
            if stats.get("word_ngram_judge_used4_rate") is not None
            else None
        ),
        word_ngram_judge_used3_rate=(
            float(stats["word_ngram_judge_used3_rate"])
            if stats.get("word_ngram_judge_used3_rate") is not None
            else None
        ),
        word_ngram_judge_prefix_total_mean=(
            float(stats["word_ngram_judge_prefix_total_mean"])
            if stats.get("word_ngram_judge_prefix_total_mean") is not None
            else None
        ),
        word_ngram_judge_prefix_total_min=(
            float(stats["word_ngram_judge_prefix_total_min"])
            if stats.get("word_ngram_judge_prefix_total_min") is not None
            else None
        ),
        word_ngram_judge_prefix_total_ge_1_rate=(
            float(stats["word_ngram_judge_prefix_total_ge_1_rate"])
            if stats.get("word_ngram_judge_prefix_total_ge_1_rate") is not None
            else None
        ),
        word_ngram_judge_prefix_total_ge_10_rate=(
            float(stats["word_ngram_judge_prefix_total_ge_10_rate"])
            if stats.get("word_ngram_judge_prefix_total_ge_10_rate") is not None
            else None
        ),
        word_ngram_judge_prefix_total_ge_100_rate=(
            float(stats["word_ngram_judge_prefix_total_ge_100_rate"])
            if stats.get("word_ngram_judge_prefix_total_ge_100_rate") is not None
            else None
        ),
        word_ngram_judge_trust_score=(
            float(stats["word_ngram_judge_trust_score"])
            if stats.get("word_ngram_judge_trust_score") is not None
            else None
        ),
        word_ngram_judge_trust_tier=str(stats.get("word_ngram_judge_trust_tier", "") or ""),
    )


def score_word_ngram_report_for_plaintext(
    *,
    scorer_runtime: Any,
    plaintext_idx: Sequence[int] | None,
    wli: Any,
    require_batch_scoring: bool,
) -> Dict[str, Any]:
    if scorer_runtime is None:
        return {}
    if plaintext_idx is None:
        return dict(
            word_ngram_judge_available=False,
            word_ngram_judge_active=False,
            word_ngram_judge_inactive_reason="no_plaintext",
        )
    pt = np.asarray(plaintext_idx, dtype=np.uint8).reshape(-1)
    if int(pt.size) == 0:
        return dict(
            word_ngram_judge_available=False,
            word_ngram_judge_active=False,
            word_ngram_judge_inactive_reason="empty_plaintext",
        )
    score_plaintexts_chunked(
        scorer=scorer_runtime,
        plaintexts=[pt],
        wli=wli,
        chunk_size=1,
        require_batch=bool(require_batch_scoring),
    )
    stats_obj: Dict[str, Any] = {}
    try:
        if hasattr(scorer_runtime, "last_stats") and callable(scorer_runtime.last_stats):
            last = scorer_runtime.last_stats()
            if isinstance(last, dict):
                stats_obj = dict(last)
    except Exception:
        stats_obj = {}
    return extract_word_ngram_report_fields(stats_obj)
