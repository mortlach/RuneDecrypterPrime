from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.damage_models_reference_v1 import (
    GLOBAL_SEED,
    empirical_probs,
    make_target_actual_damage_variant,
    make_variant,
    stable_int_seed,
)


def test_damage_and_null_models_are_deterministic_and_length_preserving() -> None:
    tokens = tuple(range(29)) * 20
    tokens = tokens[:500]
    wli = tuple((i % 5, 5) for i in range(len(tokens)))
    probs = empirical_probs(tokens)
    for model in (
        "independent_substitution",
        "frequency_matched_global",
        "frequency_matched_book",
        "word_local_substitution",
        "burst_substitution",
        "lane_period_substitution",
        "uniform_random",
        "global_frequency_random",
        "within_chunk_shuffle",
        "block_shuffle_10",
        "block_shuffle_25",
        "block_shuffle_50",
    ):
        seed = stable_int_seed(GLOBAL_SEED, model, "test")
        a = make_variant(tokens, model_name=model, damage_level=0.40, seed=seed, wli=wli, global_probs=probs, book_probs=probs)
        b = make_variant(tokens, model_name=model, damage_level=0.40, seed=seed, wli=wli, global_probs=probs, book_probs=probs)
        assert a == b
        assert len(a) == len(tokens)
        assert min(a) >= 0
        assert max(a) < 29


def test_target_actual_damage_models_hit_requested_global_damage_rate() -> None:
    tokens = tuple(range(29)) * 20
    tokens = tokens[:500]
    wli = tuple((i % 5, 5) for i in range(len(tokens)))
    probs = empirical_probs(tokens)
    for level in (0.30, 0.50):
        for model in (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ):
            seed = stable_int_seed(GLOBAL_SEED, model, f"{level:.2f}", "target-actual-test")
            variant = make_target_actual_damage_variant(
                tokens,
                model_name=model,
                damage_level=level,
                seed=seed,
                wli=wli,
                global_probs=probs,
                book_probs=probs,
            )
            changed = sum(1 for left, right in zip(tokens, variant) if left != right) / float(len(tokens))
            assert abs(changed - level) <= 0.01, (model, level, changed)
