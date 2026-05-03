from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    benchmark_fast_span_hamming_probe_v1 as mod,
)


def test_numeric_token_parser_rejects_non_base29_values() -> None:
    assert mod._parse_numeric_tokens("0 1 28") == (0, 1, 28)
    with pytest.raises(ValueError):
        mod._parse_numeric_tokens("29")
    with pytest.raises(ValueError):
        mod._parse_numeric_tokens("-1")


def test_probe_config_builds_debug_interval_config() -> None:
    spec = mod.ProbeConfig(
        config_id="test",
        len_min=3,
        len_max=5,
        max_hd=1,
        max_candidates_per_window=128,
        require_selected=True,
        wordlist_rel="assets/hamming_raw_1g",
    )
    cfg = mod._span_config(spec)
    assert cfg.len_min == 3
    assert cfg.len_max == 5
    assert cfg.max_hd == 1
    assert cfg.max_candidates_per_window == 128
    assert cfg.debug_return_intervals is True


def test_stats_compare_reports_matching_and_mismatching_fields() -> None:
    cfg = mod.SpanHammingConfig(len_min=3, len_max=3, max_hd=0, debug_return_intervals=True)
    backend = mod.SpanHammingBackend(config=cfg, wordlists={3: [[1, 2, 3]]})
    same = backend.score([1, 2, 3])
    other = backend.score([1, 2, 4])

    assert mod._stats_compare(same, same) == []
    assert "span_raw" in mod._stats_compare(same, other)


def test_readout_states_report_only_status() -> None:
    readout = mod._build_readout(
        {
            "token_hash_count": 2,
            "config_count": 1,
            "parity_failed_row_count": 0,
            "mean_speedup_ratio": 10.0,
            "median_speedup_ratio": 9.0,
        }
    )
    assert "does not change runtime solver behaviour" in readout
    assert "numeric rune/base-29" in readout.lower()
