from __future__ import annotations

from cipher_development.interruptor_position_search.benchmark import build_benchmark
from cipher_development.interruptor_position_search.config import (
    MAX_INTERRUPT_COUNT,
    MIN_INTERRUPT_COUNT,
    TRUE_INTERRUPT_COUNT,
)
from cipher_development.interruptor_position_search.experiment import (
    run_exact_control,
    terminal_metrics,
)


def test_benchmark_is_deterministic_and_has_false_positive_pool_positions():
    first = build_benchmark()
    second = build_benchmark()
    assert first == second
    assert len(first.true_positions) == TRUE_INTERRUPT_COUNT
    assert set(first.true_positions).issubset(first.pool)
    assert len(first.pool) > len(first.true_positions)
    assert all(first.ciphertext[i] == first.symbol_index for i in first.pool)
    assert all(first.plaintext[i] == first.ciphertext[i] for i in first.true_positions)


def test_count_range_contains_truth_without_revealing_exact_count():
    assert MIN_INTERRUPT_COUNT < TRUE_INTERRUPT_COUNT < MAX_INTERRUPT_COUNT


def test_positions_are_spread_and_absolute():
    benchmark = build_benchmark()
    assert tuple(sorted(benchmark.true_positions)) == benchmark.true_positions
    assert benchmark.true_positions[0] >= 0
    assert benchmark.true_positions[-1] < benchmark.text_length
    gaps = [
        b - a
        for a, b in zip(benchmark.true_positions, benchmark.true_positions[1:])
    ]
    assert min(gaps) > 0


def test_public_context_omits_truth():
    public = build_benchmark().public_context()
    forbidden = {"true_positions", "key", "plaintext", "true_count"}
    assert not forbidden & set(public)


def test_exact_mechanics_control_restores_configured_positions():
    benchmark = build_benchmark()
    result = run_exact_control(benchmark)
    metrics = terminal_metrics(benchmark, result)
    assert result.found_positions == benchmark.true_positions
    assert metrics["exact"] is True
