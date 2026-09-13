import pytest
from rdp.core.types import SeMode
from rdp.scoring.windowing import aligned_window_count, span_core_tokens, span_map, span_max, span_with_tags

def test_span_core_tokens_matches_W_plus_n_minus_1():
    assert span_core_tokens(n=4, W=10) == 13
    assert span_core_tokens(n=1, W=10) == 10

def test_span_with_tags_nose_vs_wise():
    W = 10
    n = 4
    assert span_with_tags(n=n, W=W, se_mode=SeMode.NOSE) == 13
    assert span_with_tags(n=n, W=W, se_mode=SeMode.WISE) == 15

def test_span_map_and_max():
    spans = span_map(n_set=(1, 4), W=10, se_mode='nose')
    assert spans == {1: 10, 4: 13}
    assert span_max(n_set=(1, 4), W=10, se_mode='nose') == 13

def test_aligned_window_count_uses_L_max_and_stride():
    assert aligned_window_count(length=13, n_set=(4,), W=10, se_mode='nose', stride=1) == 1
    assert aligned_window_count(length=14, n_set=(4,), W=10, se_mode='nose', stride=1) == 2
    assert aligned_window_count(length=13, n_set=(4,), W=10, se_mode='nose', stride=2) == 1
    assert aligned_window_count(length=14, n_set=(4,), W=10, se_mode='nose', stride=2) == 1
    assert aligned_window_count(length=15, n_set=(4,), W=10, se_mode='wise', stride=1) == 1
    assert aligned_window_count(length=16, n_set=(4,), W=10, se_mode='wise', stride=1) == 2

def test_aligned_window_count_empty_when_too_short():
    assert aligned_window_count(length=12, n_set=(4,), W=10, se_mode='nose', stride=1) == 0
    assert aligned_window_count(length=14, n_set=(4,), W=10, se_mode='wise', stride=1) == 0

def test_span_errors_on_bad_input():
    with pytest.raises(ValueError):
        span_core_tokens(n=0, W=10)
    with pytest.raises(ValueError):
        span_with_tags(n=1, W=0, se_mode='nose')
    with pytest.raises(ValueError):
        span_with_tags(n=1, W=10, se_mode='bad')
