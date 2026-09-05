# ruff: noqa: N999
"""Recover a Vigenere key when interruptor positions are known evidence."""

from rdp import api

PLAINTEXT = (
    2,
    18,
    4,
    18,
    7,
    24,
    15,
    24,
    16,
    24,
    17,
    20,
    18,
    15,
    18,
    16,
    3,
    1,
    16,
    1,
    9,
    23,
    18,
    4,
    24,
    16,
    4,
    18,
    18,
    10,
    9,
    0,
    4,
    3,
    9,
    16,
    3,
    0,
    2,
    18,
    8,
    3,
    1,
    15,
    18,
    24,
    9,
    23,
    2,
    18,
    19,
    24,
    4,
    5,
    8,
    8,
    24,
    4,
    18,
    24,
    9,
    23,
    2,
    18,
    8,
    24,
    16,
    16,
    18,
    4,
    7,
    18,
    4,
    18,
    8,
    24,
    1,
    21,
    16,
    28,
    24,
    16,
    10,
    16,
)
SECRET_KEY: api.ConcreteKey = (7, 0, 13, 2, 0)
INTERRUPTOR_POSITIONS = (2, 7, 13)
INTERRUPTOR_SYMBOLS = (4, 24, 15)
CIPHERTEXT_RUNES = (
    "ᚾᛖᚱᚦ ᚾᚪᛟ ᚪ ᛏᚻᛗᛚᚫ ᛋᛖᚠ ᚳᚢᛞ ᚢᛟᚫᛖᛂ ᚪ ᚠᚷᛖᚫ ᛁᛟ "
    "ᚦᚱᛁᚾᚠ ᚳᚠ ᚾᛖ ᛝᚳᚢᛟᛖ ᚻᛂᛞ ᚾᛖ ᚩᚣᚱᛇᚻ ᛝᚣᚱᚫ ᚪᛟᚫ ᚦᚫ "
    "ᚻᚻᛖᛏᚫᚱ ᛚᛚᚱᚫ ᚻᚻᚩᛝ ᛞᛠ ᚻᛖ ᛁᛞ"
)


def main() -> None:
    request = api.RunSpec(
        problem_input=api.RawTextInput(text=CIPHERTEXT_RUNES),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=len(SECRET_KEY)),
        solver=api.SolverSpec.beam_search(width=8, rounds=0, seed=2025),
        scoring=api.ScoringConfig(),
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
        interruptors=api.InterruptorConfig.exact(INTERRUPTOR_POSITIONS),
    )
    result = api.run(request)

    print("Known interruptors")
    print("Positions       :", INTERRUPTOR_POSITIONS)
    print("Untouched runes :", INTERRUPTOR_SYMBOLS)
    print("Searched symbols:", len(PLAINTEXT) - len(INTERRUPTOR_POSITIONS))
    print("Recovered key  :", result.key)
    print("Recovered runes:", result.plaintext_text)

    untouched_symbols = tuple(
        result.plaintext[position] for position in INTERRUPTOR_POSITIONS
    )
    if (
        result.key != SECRET_KEY
        or result.plaintext != PLAINTEXT
        or untouched_symbols != INTERRUPTOR_SYMBOLS
    ):
        raise AssertionError("known interruptors did not produce exact recovery")


if __name__ == "__main__":
    main()
