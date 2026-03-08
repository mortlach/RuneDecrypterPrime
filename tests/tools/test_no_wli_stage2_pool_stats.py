from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.common.pool import basin_id_from_payload
from tools.benchmarks.periodic_sub_trans.no_wli.stage2_search import _pool_stats_from_entries


pytestmark = pytest.mark.tier_a


def test_pool_stats_from_entries_counts_deduped_candidates() -> None:
    ranked = [
        {"key": [1, 2, 3], "score": 1.0, "match": 0.1, "end_hash": "h1"},
        {"key": [1, 2, 3], "score": 0.9, "match": 0.1, "end_hash": "h1"},
        {"key": [9, 8, 7], "score": 0.8, "match": 0.2, "end_hash": "h2"},
    ]
    promoted = [
        {"key": [1, 2, 3], "score": 1.0, "match": 0.1, "end_hash": "h1"},
        {"key": [9, 8, 7], "score": 0.8, "match": 0.2, "end_hash": "h2"},
    ]

    stats = _pool_stats_from_entries(ranked_entries=ranked, promoted_entries=promoted)

    assert stats["ranked_total"] == 3
    assert stats["ranked_deduped"] == 2
    assert stats["promoted_total"] == 2
    assert stats["promoted_deduped"] == 2


def test_pool_stats_from_entries_uses_shared_basin_fallbacks() -> None:
    ranked = [
        {"key": [1, 2, 3], "score": 1.0, "match": 0.1, "start_hash": "s1"},
        {"key": [4, 5, 6], "score": 0.9, "match": 0.1, "start_hash": "s1"},
        {"key": [7, 8, 9], "score": 0.8, "match": 0.2},
    ]
    stats = _pool_stats_from_entries(ranked_entries=ranked, promoted_entries=ranked)
    assert stats["ranked_total"] == 3
    # pool_stats dedupe metric remains candidate-id based.
    assert stats["ranked_deduped"] == 3
    assert basin_id_from_payload({"start_hash": "s1"}, fallback="k") == "s1"
    assert basin_id_from_payload({}, fallback="k") == "k"
