"""See how far an ordinary period-eight Vigenere model gets on Welcome Pilgrim.

Period eight is known from the solved page, but that does not mean the whole
solution is ordinary Vigenere. We will start by giving RDP the cipher family
and the period. None of the eight key values are supplied to the search, so
let's see what it can find.

A partial success is useful here. If the text looks right for a while and then
loses its way, that tells us rather more than simply turning the search budget
up.
"""

from rdp import api

# We know the period. The search still has to recover the eight key values.
KEY_LENGTH = 8


def main() -> None:
    """Search the incomplete model, then compare it with the known solved page."""
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

    # The solved plaintext is reference data. It had no part in the search above.
    reference = api.liber_primus.load_plaintext("welcome_pilgrim")
    exact_match = result.plaintext_indices == reference.indices

    print("Matches the complete solved text:", exact_match)
    if exact_match:
        raise AssertionError("the expected incomplete-model outcome changed")

    print("So period eight is doing something useful, but it is not the whole story.")
    print("Next: look at what happens when some positions do not advance the key.")


if __name__ == "__main__":
    main()
