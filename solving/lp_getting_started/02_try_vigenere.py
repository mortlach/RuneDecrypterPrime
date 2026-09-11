"""Try a period-eight Vigenere model on Welcome Pilgrim.

We supply the cipher family and key length, then ask RDP to find the eight
values. This leaves out part of the known construction. Watch for readable
stretches, but check the complete text before calling it a recovery.
"""

from rdp import api

# The period comes from the known solution; the eight key values are searched.
KEY_LENGTH = 8


def main() -> None:
    """Search the incomplete model, then compare with the solved text."""
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
    )

    result = api.run(request)
    if result.plaintext_indices is None or result.plaintext_runes is None:
        raise RuntimeError("the search did not return a candidate")

    print("Recovered key:", result.key)
    print("Score        :", result.score)
    print("Plaintext    :", result.plaintext_runes)

    # Only now look at the known answer. It was not part of the request.
    reference = api.liber_primus.load_plaintext("welcome_pilgrim")
    exact_match = result.plaintext_indices == reference.indices
    print("Matches the complete solved text:", exact_match)
    if exact_match:
        raise AssertionError("the expected incomplete-model outcome changed")
    print("The search ran, but this model did not recover the complete text.")
    print("Next: allow positions that leave the rune and key cursor unchanged.")

if __name__ == "__main__":
    main()
