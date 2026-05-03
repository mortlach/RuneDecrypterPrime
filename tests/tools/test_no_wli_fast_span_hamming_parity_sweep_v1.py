from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    sweep_fast_span_hamming_parity_v1 as mod,
)


def test_numeric_token_parser_rejects_non_base29_values() -> None:
    assert mod._parse_numeric_tokens("0 1 28") == (0, 1, 28)
    with pytest.raises(ValueError):
        mod._parse_numeric_tokens("29")
    with pytest.raises(ValueError):
        mod._parse_numeric_tokens("-1")


def test_span_config_preserves_debug_interval_contract() -> None:
    spec = mod.SpanSpec(
        config_id="x",
        len_min=3,
        len_max=9,
        max_hd=2,
        max_candidates_per_window=512,
        require_selected=False,
        wordlist_rel="assets/hamming_raw_1g",
    )
    cfg = mod._span_config(spec)
    assert cfg.len_min == 3
    assert cfg.len_max == 9
    assert cfg.max_hd == 2
    assert cfg.max_candidates_per_window == 512
    assert cfg.debug_return_intervals is True


def test_stats_compare_detects_parity_mismatch() -> None:
    cfg = mod.SpanHammingConfig(len_min=3, len_max=3, max_hd=0, debug_return_intervals=True)
    backend = mod.SpanHammingBackend(config=cfg, wordlists={3: [[1, 2, 3]]})
    exact = backend.score([1, 2, 3])
    miss = backend.score([1, 2, 4])

    assert mod._stats_compare(exact, exact) == []
    assert "span_raw" in mod._stats_compare(exact, miss)


def test_readout_reports_report_only_status() -> None:
    readout = mod._build_readout(
        {
            "token_hash_count": 10,
            "config_count": 2,
            "result_row_count": 20,
            "skipped_config_count": 0,
            "parity_failed_row_count": 0,
            "mean_speedup_ratio": 4.0,
            "median_speedup_ratio": 3.5,
        }
    )
    assert "Report-only only" in readout
    assert "Numeric rune/base-29" in readout
