from __future__ import annotations

import numpy as np

from cipher_development.two_period_overlay.config import (
    CRIB_RUNES,
    P13_P31_BENCHMARKS,
    P13_P31_TARGET_BENCHMARK,
)
from cipher_development.two_period_overlay.keyspace import (
    crib_space,
    deterministic_key,
    expand,
)


def _consistent_ciphertext(benchmark):
    key = deterministic_key(benchmark)
    ciphertext = np.zeros(benchmark.text_length, dtype=np.uint8)
    spans = ((benchmark.crib_start, tuple(CRIB_RUNES)), *(
        (item.start, item.runes) for item in benchmark.additional_cribs
    ))
    for start, runes in spans:
        for offset, plain in enumerate(runes):
            pos = start + offset
            ciphertext[pos] = (
                int(plain)
                + int(key[pos % benchmark.period_a])
                + int(key[benchmark.period_a + pos % benchmark.period_b])
            ) % benchmark.alphabet_size
    return ciphertext, key


def test_p13_p31_dimension_ladder_is_derived() -> None:
    expected = (30, 22, 22, 14)
    actual: list[int] = []
    for benchmark in P13_P31_BENCHMARKS:
        ciphertext, _ = _consistent_ciphertext(benchmark)
        particular, basis, free = crib_space(
            ciphertext,
            np.asarray(CRIB_RUNES, dtype=np.uint8),
            benchmark,
        )
        assert particular.shape == (benchmark.key_length,)
        assert basis.shape == (benchmark.key_length, len(free))
        actual.append(len(free))
    assert tuple(actual) == expected


def test_p13_p31_true_key_is_represented_by_target_affine_space() -> None:
    benchmark = P13_P31_TARGET_BENCHMARK
    ciphertext, key = _consistent_ciphertext(benchmark)
    particular, basis, free = crib_space(
        ciphertext,
        np.asarray(CRIB_RUNES, dtype=np.uint8),
        benchmark,
    )
    variables = np.asarray([key[index] for index in free], dtype=np.uint8)
    assert np.array_equal(expand(variables, particular, basis, benchmark), key)
    assert len(free) == 14
    assert all(index >= benchmark.period_a for index in free)
    assert int(key[benchmark.gauge_key_index]) == benchmark.gauge_value


def test_p13_p31_benchmark_ids_and_crib_order_are_frozen() -> None:
    assert tuple(item.benchmark_id for item in P13_P31_BENCHMARKS) == (
        "alice_308_p13_p31_crib188x13_d30",
        "alice_308_p13_p31_crib188x13_plus081x8_d22",
        "alice_308_p13_p31_crib188x13_plus206x8_d22",
        "alice_308_p13_p31_crib188x13_plus081x8_plus206x8_d14",
    )
    target = P13_P31_TARGET_BENCHMARK
    assert tuple(item.start for item in target.additional_cribs) == (81, 206)
    assert tuple(item.word for item in target.additional_cribs) == ("dormouse", "dormouse")
    assert target.period_a == 13
    assert target.period_b == 31
    assert target.expected_free_dimension == 14
