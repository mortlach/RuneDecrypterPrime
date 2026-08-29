from __future__ import annotations
from rune_decrypter_prime.utils.tutorial_utils import (
    StopScoreResult,
    format_stop_summary,
    print_stop_summary,
    stop_summary_rows,
)


def test_stop_summary_rows_include_oracle_stop_and_status() -> None:
    result = StopScoreResult(oracle_score=0.5, stop_score=0.48, reason="oracle_ok")
    rows = stop_summary_rows("Columnar Hybrid", result)
    assert rows == [
        ("label", "Columnar Hybrid"),
        ("oracle_score", 0.5),
        ("stop_score", 0.48),
        ("status", "oracle_ok"),
    ]


def test_format_stop_summary_handles_oracle_and_fallback() -> None:
    ok = format_stop_summary("Columnar Hybrid", StopScoreResult(0.5, 0.48, "oracle_ok"))
    fallback = format_stop_summary(
        "Columnar Hybrid", StopScoreResult(None, 0.503, "oracle_failed: missing asset")
    )
    assert "Scoring / stop target" in ok
    assert "Columnar Hybrid" in ok
    assert "0.500000" in ok
    assert "0.480000" in ok
    assert "oracle_ok" in ok
    assert "unavailable" in fallback
    assert "oracle_failed: missing asset" in fallback


def test_print_stop_summary_uses_standard_block(capsys) -> None:
    print_stop_summary("Columnar Hybrid", StopScoreResult(0.5, 0.48, "oracle_ok"))
    out = capsys.readouterr().out
    assert "Scoring / stop target" in out
    assert "Columnar Hybrid" in out
    assert "oracle_ok" in out
