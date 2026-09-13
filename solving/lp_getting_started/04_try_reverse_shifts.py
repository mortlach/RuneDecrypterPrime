"""Try all 29 reverse shifts on the koan A Man.

The proposed rule is simple:

    (28 - value + shift) % 29

and the shift can only be 0 to 28.

There are therefore 29 possibilities. This is not yet a problem that needs a
clever optimiser. We can just try all 29, score the resulting plaintexts and see
what comes out on top.

That gives us a complete result to compare with the solver in the next example.
"""

from rdp import api

# These examples use all four installed model orders.
ORDER_WEIGHTS = {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25}
RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛂᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"


def rune_preview(
    values: tuple[int, ...],
    wli: tuple[tuple[int, int], ...],
    *,
    limit: int = 120,
) -> str:
    """Render enough spaced runes to recognise a candidate."""
    text: list[str] = []
    for index, value in enumerate(values[:limit]):
        if index and wli[index][0] == 0:
            text.append(" ")
        text.append(RUNES[value])
    return "".join(text)


def main() -> None:
    """Score the complete 29-shift family."""
    source_data = api.liber_primus.load_source("koan_a_man")
    candidates = []
    plaintexts = []

    for shift in range(29):
        plaintext = tuple((28 - value + shift) % 29 for value in source_data.ct_idx)
        plaintexts.append(plaintext)
        candidates.append(
            api.RuneInput(
                value=plaintext,
                word_length_information=source_data.wli,
            )
        )

    scoring = api.ScoringConfig(
        character_lane_enabled=True,
        wli_lane_enabled=True,
        character_order_weights=ORDER_WEIGHTS,
        wli_order_weights=ORDER_WEIGHTS,
    )
    scores = api.score_many(
        candidates,
        scoring=scoring,
        text_direction=api.TextDirection.LTR,
    )

    ranking = sorted(range(29), key=lambda shift: scores[shift], reverse=True)

    print("Top five:")
    for shift in ranking[:5]:
        print(
            f"  shift={shift:2d} score={scores[shift]:.8f}",
            rune_preview(plaintexts[shift], source_data.wli),
        )

    best_shift = ranking[0]
    reference = api.liber_primus.load_plaintext("koan_a_man")
    exact_match = plaintexts[best_shift] == reference.indices

    print("Best shift              :", best_shift)
    print("Matches the solved text :", exact_match)

    # The transform is its own inverse, which is useful as a sanity check.
    # It does not tell us which shift is right: every shift passes this test.
    roundtrip = tuple(
        (28 - value + best_shift) % 29
        for value in plaintexts[best_shift]
    )
    print("Best candidate round-trips:", roundtrip == tuple(source_data.ct_idx))


if __name__ == "__main__":
    main()
