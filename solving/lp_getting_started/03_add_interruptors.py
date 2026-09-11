"""Now add the bit of the Welcome Pilgrim solution we left out.

Some positions act as interruptors: the ciphertext rune passes through unchanged
and, importantly, the repeating key does not advance.

That matters rather quickly. Miss one interruptor and the key is out of step for
everything that follows.

We are still using known information from the solved page here. We know the
period is eight and that there are eleven interruptors. What we do *not* give
the search is the eight key values or the eleven positions themselves. It has to
find those from the candidate zero positions.
"""

from rdp import api

KEY_LENGTH = 8
INTERRUPTOR_COUNT = 11


def main() -> None:
    """Search the key and interruptor positions, then check the solved plaintext."""
    source_data = api.liber_primus.load_source("welcome_pilgrim")
    candidate_positions = tuple(
        index for index, value in enumerate(source_data.ct_idx) if value == 0
    )

    print("Ciphertext-zero positions:", len(candidate_positions))
    print("Interruptors to find      :", INTERRUPTOR_COUNT)

    request = api.RunSpec(
        problem_input=api.liber_primus.source("welcome_pilgrim"),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=KEY_LENGTH),
        solver=api.SolverSpec.beam_search(
            width=64,
            expansion=api.advanced.BeamExpansionMode.SWEEP,
            plateau_rounds=5,
            plateau_minimum_delta=0.0001,
            seed=2026,
            rounds=None,
        ),
        scoring=api.ScoringConfig(
            character_lane_enabled=True,
            wli_lane_enabled=True,
            character_order_weights={1: 0.3, 2: 0.7},
            wli_order_weights={1: 0.3, 2: 0.7},
            objective=api.advanced.ScoringObjective.percentile_log_probability(
                window_size=10
            ),
        ),
        text_direction=api.TextDirection.LTR,
        interruptors=api.InterruptorConfig.search(
            candidate_positions,
            minimum_count=INTERRUPTOR_COUNT,
            maximum_count=INTERRUPTOR_COUNT,
            strategy=api.advanced.InterruptorSearchStrategy.KEY_OPERATIONS,
            maximum_combinations=5000,
        ),
    )

    result = api.run(request)
    if result.key is None or result.plaintext_indices is None or result.plaintext_runes is None:
        raise RuntimeError("the search did not return a candidate")

    # For this search the concrete key contains the eight Vigenere values followed
    # by the selected interruptor positions.
    key_values = result.key[:KEY_LENGTH]
    positions = result.key[KEY_LENGTH:]

    print("Recovered key                 :", key_values)
    print("Selected interruptor positions:", positions)
    print("Score                         :", result.score)
    print("Plaintext                     :", result.plaintext_runes)

    reference = api.liber_primus.load_plaintext("welcome_pilgrim")
    exact_match = result.plaintext_indices == reference.indices

    print("Matches all 515 solved runes:", exact_match)
    if not exact_match:
        raise AssertionError("the interruptor model did not recover the solved text")


if __name__ == "__main__":
    main()
