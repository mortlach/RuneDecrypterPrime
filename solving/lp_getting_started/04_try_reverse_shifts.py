"""Try all 29 reverse shifts on the koan A Man.

Rune indices run from 0 to 28. Reversing that alphabet gives 28 - value;
adding a shift and reducing modulo 29 rotates it. There are only 29 choices,
so an ordinary loop can try the complete family before we involve a solver.
"""

from rdp import api

# These examples use all four model orders, equally weighted within each lane.
# They require the full language-model files obtained by the source installer.
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
    """Rank the complete shift family, then check the known shift."""
    source_data = api.liber_primus.load_source("koan_a_man")
    candidates = []
    plaintexts = []
    for shift in range(29):
        plaintext = tuple((28 - value + shift) % 29 for value in source_data.ct_idx)
        # This changes rune values, so the original word boundaries still apply.
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
    for shift in ranking[:5]:
        print(
            f"shift={shift:2d} score={scores[shift]:.8f}",
            rune_preview(plaintexts[shift], source_data.wli),
        )

    best_shift = ranking[0]
    print("Best shift:", best_shift)
    print("Known shift ranks first:", best_shift == 3)

    reference = api.liber_primus.load_plaintext("koan_a_man")
    print(
        "Matches the complete solved text:",
        plaintexts[best_shift] == reference.indices,
    )

    # Reversibility is useful, but it cannot choose the key: every shift passes.
    roundtrip = tuple((28 - value + best_shift) % 29 for value in plaintexts[best_shift])
    print("Best candidate round-trips:", roundtrip == tuple(source_data.ct_idx))


if __name__ == "__main__":
    main()
