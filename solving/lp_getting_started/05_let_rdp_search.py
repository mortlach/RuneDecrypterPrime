"""Let RDP search the same family, then remove the reverse-shift assumption.

First describe the rule as a cipher and search its single key value. Compare
the answer with a complete manual sweep. Then try a general substitution:
any permutation of the 29-symbol alphabet is allowed. That is a much larger
problem, so the short run is an experiment rather than a promised recovery.
"""

from rdp import api

ORDER_WEIGHTS = {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25}


def reverse_shift(plaintext: int, shift: int) -> int:
    """Define the encryption rule; this particular map is its own inverse."""
    return (28 - plaintext + shift) % 29


def main() -> None:
    """Compare enumeration, a narrow solver search and a broader experiment."""
    source = api.liber_primus.source("koan_a_man")
    source_data = api.liber_primus.load_source("koan_a_man")
    scoring = api.ScoringConfig(
        character_lane_enabled=True,
        wli_lane_enabled=True,
        character_order_weights=ORDER_WEIGHTS,
        wli_order_weights=ORDER_WEIGHTS,
    )

    manual_plaintexts = [
        tuple(reverse_shift(value, shift) for value in source_data.ct_idx)
        for shift in range(29)
    ]
    scores = api.score_many(
        [
            api.RuneInput(
                value=plaintext,
                word_length_information=source_data.wli,
            )
            for plaintext in manual_plaintexts
        ],
        scoring=scoring,
        text_direction=api.TextDirection.LTR,
    )
    best_shift = max(range(29), key=lambda shift: scores[shift])

    # A repeating key of length one represents the unknown constant shift.
    # The sweep expansion can visit every value in its 29-symbol key space.
    result = api.run(
        api.RunSpec(
            problem_input=source,
            cipher=api.experimental.define_cipher_map(
                reverse_shift,
                name="reverse_shift",
            ),
            key_space=api.KeySpec.repeating(length=1),
            solver=api.SolverSpec.beam_search(
                width=29,
                rounds=1,
                expansion=api.advanced.BeamExpansionMode.SWEEP,
                seed=2026,
            ),
            scoring=scoring,
            text_direction=api.TextDirection.LTR,
        )
    )
    if result.plaintext_indices is None:
        raise RuntimeError("the reverse-shift search did not return a candidate")

    print("Manual best shift:", best_shift)
    print("Solver key       :", result.key)
    print("Same plaintext   :", result.plaintext_indices == manual_plaintexts[best_shift])
    print("Same score       :", result.score == scores[best_shift])

    # Now remove the reverse-shift structure. The optimiser must search an
    # arbitrary permutation, so 2,000 iterations are only a first look.
    broad = api.run(
        api.RunSpec(
            problem_input=source,
            cipher=api.CipherSpec.substitution(),
            key_space=api.KeySpec.permutation(length=29),
            solver=api.SolverSpec.simulated_annealing(
                iterations=2000,
                automatic_cooling=True,
                seed=2026,
            ),
            scoring=scoring,
            text_direction=api.TextDirection.LTR,
        )
    )
    if broad.plaintext_indices is None:
        raise RuntimeError("the substitution search did not return a candidate")

    matches = sum(
        left == right
        for left, right in zip(broad.plaintext_indices, manual_plaintexts[best_shift])
    )
    print("General substitution matches:", f"{matches}/{len(result.plaintext_indices)}")
    print("General substitution text   :", broad.plaintext_runes)
    print("This broader run is incomplete; a larger search space needs a larger budget.")


if __name__ == "__main__":
    main()
