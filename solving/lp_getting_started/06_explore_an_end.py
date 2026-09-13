"""Try a few number sequences as key streams for An End.

This one is more exploratory.

Instead of a short repeating key, we take values from a number sequence. We try
primes, Fibonacci numbers, triangular numbers and squares, vary where the stream
starts, and add a constant shift.

We are not feeding the known opening phrase into the ranking. The language model
gets to choose the best candidate.

If the best stream then loses the text partway through, An End gives us a useful
small follow-up: there are only five ciphertext-zero positions, so every possible
interruptor subset is just 32 cases. We can try them all.
"""

from itertools import combinations

from rdp import api

MAX_OFFSET = 20
ORDER_WEIGHTS = {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25}
RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛂᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"


def sequence_families(count: int) -> dict[str, list[int]]:
    """Build the four sequence families used by this experiment."""
    primes: list[int] = []
    number = 2
    while len(primes) < count:
        is_prime = True
        for prime in primes:
            if prime * prime > number:
                break
            if number % prime == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(number)
        number += 1

    fibonacci: list[int] = []
    left, right = 0, 1
    for _ in range(count):
        fibonacci.append(left)
        left, right = right, left + right

    return {
        "primes": primes,
        "fibonacci": fibonacci,
        "triangular": [n * (n + 1) // 2 for n in range(count)],
        "squares": [n * n for n in range(count)],
    }


def decrypt_stream(
    ciphertext: tuple[int, ...],
    stream: list[int],
    *,
    offset: int,
    shift: int,
    interruptors: frozenset[int] = frozenset(),
) -> tuple[int, ...]:
    """Apply a shifted stream, leaving interruptors and the stream cursor alone."""
    plaintext: list[int] = []
    cursor = 0

    for position, value in enumerate(ciphertext):
        if position in interruptors:
            plaintext.append(value)
            continue

        key_value = (stream[offset + cursor] + shift) % 29
        plaintext.append((value - key_value) % 29)
        cursor += 1

    return tuple(plaintext)


def all_subsets(values: tuple[int, ...]) -> list[frozenset[int]]:
    """Return every subset of this deliberately small candidate pool."""
    return [
        frozenset(subset)
        for size in range(len(values) + 1)
        for subset in combinations(values, size)
    ]


def render_runes(
    values: tuple[int, ...],
    wli: tuple[tuple[int, int], ...],
) -> str:
    """Render rune indices with the source word boundaries."""
    text: list[str] = []
    for index, value in enumerate(values):
        if index and wli[index][0] == 0:
            text.append(" ")
        text.append(RUNES[value])
    return "".join(text)


def main() -> None:
    """Rank the sequence sweep, then try the small interruptor follow-up."""
    source_data = api.liber_primus.load_source("an_end")
    ciphertext = tuple(source_data.ct_idx)
    sequences = sequence_families(MAX_OFFSET + len(ciphertext))

    scoring = api.ScoringConfig(
        character_lane_enabled=True,
        wli_lane_enabled=True,
        character_order_weights=ORDER_WEIGHTS,
        wli_order_weights=ORDER_WEIGHTS,
    )

    descriptions: list[tuple[str, int, int]] = []
    plaintexts: list[tuple[int, ...]] = []

    for family, stream in sequences.items():
        for offset in range(MAX_OFFSET + 1):
            for shift in range(29):
                descriptions.append((family, offset, shift))
                plaintexts.append(
                    decrypt_stream(
                        ciphertext,
                        stream,
                        offset=offset,
                        shift=shift,
                    )
                )

    scores = api.score_many(
        [
            api.RuneInput(
                value=plaintext,
                word_length_information=source_data.wli,
            )
            for plaintext in plaintexts
        ],
        scoring=scoring,
        text_direction=api.TextDirection.LTR,
    )

    winning_index = max(range(len(scores)), key=scores.__getitem__)
    family, offset, shift = descriptions[winning_index]

    print("Best stream before interruptors:", family, "offset", offset, "shift", shift)
    print("Score:", scores[winning_index])

    # Only five ciphertext-zero positions: 2**5 == 32 possible subsets.
    zero_positions = tuple(
        index for index, value in enumerate(ciphertext) if value == 0
    )
    subsets = all_subsets(zero_positions)

    interrupted_plaintexts = [
        decrypt_stream(
            ciphertext,
            sequences[family],
            offset=offset,
            shift=shift,
            interruptors=subset,
        )
        for subset in subsets
    ]

    interrupted_scores = api.score_many(
        [
            api.RuneInput(
                value=plaintext,
                word_length_information=source_data.wli,
            )
            for plaintext in interrupted_plaintexts
        ],
        scoring=scoring,
        text_direction=api.TextDirection.LTR,
    )

    interrupted_index = max(
        range(len(interrupted_scores)),
        key=interrupted_scores.__getitem__,
    )
    selected_positions = subsets[interrupted_index]
    plaintext = interrupted_plaintexts[interrupted_index]

    # Only now compare with reference data, after candidate ranking is complete.
    reference = api.liber_primus.load_plaintext("an_end")
    print("Before interruptors matches solved text:", plaintexts[winning_index] == reference.indices)

    print("Selected interruptor positions:", tuple(sorted(selected_positions)))
    print("Final score:", interrupted_scores[interrupted_index])

    exact_match = plaintext == reference.indices
    print("Matches all solved runes:", exact_match)
    print("Plaintext:", render_runes(plaintext, source_data.wli))


if __name__ == "__main__":
    main()
