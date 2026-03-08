from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.sub_then_col.runner import _pool_stats_from_entries


pytestmark = pytest.mark.tier_a


def test_sub_then_col_pool_stats_reports_basin_dedupe() -> None:
    ranked = [
        {"key": [1, 2, 3], "score": 1.0, "match": 0.1, "start_hash": "s1"},
        {"key": [4, 5, 6], "score": 0.9, "match": 0.2, "start_hash": "s1"},
        {"key": [7, 8, 9], "score": 0.8, "match": 0.3, "start_hash": "s2"},
    ]
    promoted = [ranked[0], ranked[1]]
    stats = _pool_stats_from_entries(ranked_entries=ranked, promoted_entries=promoted)
    assert stats["ranked_total"] == 3
    assert stats["ranked_deduped"] == 3
    assert stats["ranked_basin_deduped"] == 2
    assert stats["promoted_total"] == 2
    assert stats["promoted_basin_deduped"] == 1
