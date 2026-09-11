"""Give the Welcome Pilgrim model its missing interruptors.

An interruptor passes through unchanged and does not consume a key value.
Missing one shifts the key alignment for everything that follows. Here we
assume eleven such positions, drawn from ciphertext zeros, and let the search
choose which eleven belong to the construction.
"""

from rdp import api

# Both counts are prior information. No key values or chosen positions are given.
KEY_LENGTH = 8
INTERRUPTOR_COUNT = 11


def main() -> None:
    """Search the key and interruptors, then check the complete result."""
    source_data = api.liber_primus.load_source("welcome_pilgrim")
    candidate_positions = tuple(
        index for index, value in enumerate(source_data.ct_idx) if value == 0
    )

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
    if (
        result.key is None
        or result.plaintext_indices is None
        or result.plaintext_runes is None
    ):
        raise RuntimeError("the search did not return a candidate")

    # For this search, the concrete key holds key values followed by positions.
    key_values = result.key[:KEY_LENGTH]
    positions = result.key[KEY_LENGTH:]
    print("Recovered key:", key_values)
    print("Selected interruptor positions:", positions)
    print("Score:", result.score)
    print("Plaintext:", result.plaintext_runes)

    # The search is finished; now compare it with the separately stored answer.
    reference = api.liber_primus.load_plaintext("welcome_pilgrim")
    exact_match = result.plaintext_indices == reference.indices
    print("Matches the complete solved text:", exact_match)
    if not exact_match:
        raise AssertionError("the interruptor model did not recover the solved text")

if __name__ == "__main__":
    main()
