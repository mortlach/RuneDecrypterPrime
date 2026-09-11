"""Try a few number sequences as key streams for An End.

Instead of repeating a short key, take successive values from a sequence.
We vary where the sequence starts and add a constant shift, then let the
language model rank the resulting texts. No guessed opening phrase is used.
"""

from itertools import combinations

from rdp import api

# Start with a modest sweep; increase this to explore later sequence positions.
MAX_OFFSET = 20
ORDER_WEIGHTS = {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25}
RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛂᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"


def sequence_families(count: int) -> dict[str, list[int]]:
    """Build primes, Fibonacci numbers, triangular numbers and squares."""
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
    """Apply a shifted stream while leaving interruptors and the cursor alone."""
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
    """Return every subset of a deliberately small candidate pool."""
    return [
        frozenset(subset)
        for size in range(len(values) + 1)
        for subset in combinations(values, size)
    ]


def main() -> None:
    """Score the sequence sweep before looking at any reference plaintext."""
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

    # An End has only five ciphertext-zero positions, so all 32 subsets fit in
    # a short follow-up. The winning stream stays fixed while these are tried.
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
        range(len(interrupted_scores)), key=interrupted_scores.__getitem__
    )
    selected_positions = subsets[interrupted_index]
    plaintext = interrupted_plaintexts[interrupted_index]

    print("Selected interruptor positions:", tuple(sorted(selected_positions)))
    print("Final score:", interrupted_scores[interrupted_index])

    # Only now compare the selected candidate with the known solved text.
    reference = api.liber_primus.load_plaintext("an_end")
    exact_match = plaintext == reference.indices
    print("Matches all reference runes:", exact_match)
    print(
        "Plaintext:",
        reference.runes if exact_match else "".join(RUNES[v] for v in plaintext),
    )


if __name__ == "__main__":
    main()
