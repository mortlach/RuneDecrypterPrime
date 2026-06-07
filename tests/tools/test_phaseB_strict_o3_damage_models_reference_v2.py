from __future__ import annotations

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.damage_models_reference_v2 import (
    ALPHABET_SIZE,
    DAMAGE_MODELS,
    make_target_actual_damage_result,
    stable_int_seed,
)


def _tokens(n: int = 500) -> tuple[int, ...]:
    return tuple(int(i % ALPHABET_SIZE) for i in range(n))


def _wli(n: int = 500, word_len: int = 5) -> tuple[tuple[int, int], ...]:
    return tuple((i % word_len, word_len) for i in range(n))


def test_all_target_actual_models_hit_requested_changed_fraction() -> None:
    tokens = _tokens()
    wli = _wli()
    probs = np.ones(ALPHABET_SIZE, dtype=np.float64) / float(ALPHABET_SIZE)
    for model in DAMAGE_MODELS:
        for level in (0.0, 0.30, 0.50):
            result = make_target_actual_damage_result(
                tokens,
                model_name=model,
                damage_level=level,
                seed=stable_int_seed("target", model, level),
                wli=wli,
                global_probs=probs,
                book_probs=probs,
                tolerance=0.01,
            )
            assert len(result.tokens) == len(tokens)
            assert min(result.tokens) >= 0 and max(result.tokens) < ALPHABET_SIZE
            result.assert_within_tolerance(tolerance=0.01)
            if level == 0.0:
                assert result.tokens == tokens
                assert result.changed_positions == ()


def test_word_local_target_actual_is_word_clustered_not_flat_position_sampling() -> None:
    tokens = _tokens()
    wli = _wli(word_len=5)
    result = make_target_actual_damage_result(
        tokens,
        model_name="word_local_substitution",
        damage_level=0.30,
        seed=stable_int_seed("word-local-shape"),
        wli=wli,
    )
    changed = set(result.changed_positions)
    touched_words = {pos // 5 for pos in changed}
    # 150 changed tokens over 5-token words should touch about 30 words, with at most one partial word.
    assert len(touched_words) <= 31
    assert result.metadata["shape"] == "word_local_exact_count"
    assert result.metadata["selected_word_count"] <= 31


def test_lane_period_target_actual_keeps_every_changed_position_on_selected_lanes() -> None:
    tokens = _tokens()
    result = make_target_actual_damage_result(
        tokens,
        model_name="lane_period_substitution",
        damage_level=0.50,
        seed=stable_int_seed("lane-shape"),
    )
    period = int(result.metadata["period"])
    lanes = set(int(x) for x in result.metadata["lanes"])
    assert period > 0
    assert lanes
    assert result.metadata["off_lane_fallback_used"] is False
    assert all((pos % period) in lanes for pos in result.changed_positions)


def test_burst_target_actual_has_few_contiguous_runs() -> None:
    tokens = _tokens()
    result = make_target_actual_damage_result(
        tokens,
        model_name="burst_substitution",
        damage_level=0.30,
        seed=stable_int_seed("burst-shape"),
    )
    run_count = int(result.metadata["run_count"])
    assert run_count > 0
    # Loose shape check: burst damage should not look like 150 isolated points.
    assert run_count <= 40


def test_frequency_matched_degenerate_distribution_still_changes_selected_positions() -> None:
    tokens = tuple(0 for _ in range(100))
    wli = _wli(n=100)
    probs = np.zeros(ALPHABET_SIZE, dtype=np.float64)
    probs[0] = 1.0
    result = make_target_actual_damage_result(
        tokens,
        model_name="frequency_matched_global",
        damage_level=0.30,
        seed=stable_int_seed("degenerate-frequency"),
        wli=wli,
        global_probs=probs,
        book_probs=probs,
    )
    assert len(result.changed_positions) == 30
    assert all(value != 0 for idx, value in enumerate(result.tokens) if idx in set(result.changed_positions))
