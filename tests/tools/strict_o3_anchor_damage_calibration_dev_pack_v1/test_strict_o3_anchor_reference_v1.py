from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.strict_o3_anchor_reference_v1 import (
    HitRow,
    filter_hits,
    dedupe_hits_by_span_keep_best,
    select_max_weight_nonoverlap,
    summarise_candidate,
    wilson_interval,
)


def test_rejects_rev_when_fwd_required() -> None:
    hits = [HitRow(candidate_id="A", trial_id="t", direction="rev", hd=0, phrase_length=10, start=0, end=10)]
    with pytest.raises(ValueError, match="direction='fwd'"):
        filter_hits(hits, max_hd=0, min_phrase_length=10, require_fwd=True)


def test_nonoverlap_prefers_best_weight_not_most_rows() -> None:
    hits = [
        HitRow("A", "t", "fwd", 0, 12, 0, 12, "rare", "s", 1),
        HitRow("A", "t", "fwd", 0, 10, 0, 10, "common", "s", 1000),
        HitRow("A", "t", "fwd", 0, 10, 20, 30, "other", "s", 10),
    ]
    regions = dedupe_hits_by_span_keep_best(hits, min_phrase_length=10)
    selected = select_max_weight_nonoverlap(regions)
    assert [r.phrase_row_id for r in selected] == ["rare", "other"]


def test_candidate_summary_long_hit_floor() -> None:
    hits = [
        HitRow("A", "t", "fwd", 0, 10, 0, 10, "p1", "s", 100),
        HitRow("A", "t", "fwd", 1, 15, 20, 35, "p2", "s", 50),
        HitRow("A", "t", "fwd", 2, 18, 40, 58, "p3", "s", 25),
    ]
    summary, selected = summarise_candidate(hits, candidate_id="A", trial_id="t", min_phrase_length=10, max_hd=0)
    assert summary.longest_hd0_phrase_len == 10
    assert summary.longest_hd1_phrase_len == 15
    assert summary.longest_hd2_phrase_len == 18
    assert summary.min_hd_at_len_ge_15 == 1
    assert summary.min_hd_at_len_ge_18 == 2
    assert len(selected) == 1


def test_wilson_interval_bounds_zero_breaks() -> None:
    low, high = wilson_interval(0, 87)
    assert low == 0.0
    assert 0.0 < high < 0.05
