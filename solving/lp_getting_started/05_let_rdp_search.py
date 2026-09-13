"""Now let RDP search the same A Man problem.

In the previous example we tried all 29 shifts ourselves. That is useful because
we now know the complete ranking before asking an optimiser to do anything.

First we describe exactly the same reverse-shift rule as a cipher and let Beam
search its one-value key. If that disagrees with the exhaustive sweep, we should
stop and work out why.

After that we remove the nice one-parameter structure and allow any substitution
of the 29-rune alphabet. The Python only changes a little. The search problem
does not.
"""

from rdp import api

ORDER_WEIGHTS = {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25}


def reverse_shift(plaintext: int, shift: int) -> int:
    """The reverse-shift rule; applying it twice with the same shift restores input."""
    return (28 - plaintext + shift) % 29


def main() -> None:
    """Compare the exhaustive sweep, a narrow search and a much broader one."""
    source = api.liber_primus.source("koan_a_man")
    source_data = api.liber_primus.load_source("koan_a_man")
    scoring = api.ScoringConfig(
        character_lane_enabled=True,
        wli_lane_enabled=True,
        character_order_weights=ORDER_WEIGHTS,
        wli_order_weights=ORDER_WEIGHTS,
    )

    # Recreate the complete 29-way comparison from the previous example.
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

    # A repeating key of length one is enough to hold the unknown shift.
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

    print("Manual best shift  :", best_shift)
    print("Solver key         :", result.key)
    print("Same plaintext     :", result.plaintext_indices == manual_plaintexts[best_shift])
    print("Same score         :", result.score == scores[best_shift])

    # Now remove the reverse-shift assumption. Any permutation of the 29-rune
    # alphabet is allowed. Two thousand SA iterations are only a first look.
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

    # Reference data is loaded only after both searches have produced candidates.
    reference = api.liber_primus.load_plaintext("koan_a_man")
    print("Matches solved text:", result.plaintext_indices == reference.indices)

    matches = sum(
        left == right
        for left, right in zip(broad.plaintext_indices, reference.indices)
    )

    print("General substitution matches:", f"{matches}/{len(reference.indices)}")
    print("General substitution text   :", broad.plaintext_runes)
    print("The broader model is nowhere near exhausted by this little run.")


if __name__ == "__main__":
    main()
