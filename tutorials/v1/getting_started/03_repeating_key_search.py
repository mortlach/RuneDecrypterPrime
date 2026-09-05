# ruff: noqa: N999
"""Recover a repeating Vigenere key from rune text with word boundaries."""

from rdp import api

PLAINTEXT = (
    16,
    8,
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
)
SECRET_KEY: api.ConcreteKey = (3, 1, 4, 1)
CIPHERTEXT_RUNES = "ᛗᚾᛟᚳᛝ ᚻᛠᛏ ᛡ ᛒᛠᛖᛞᛗ ᛗᛗᛗ ᚱᚳᛒ ᚱᛁᛡᛗᚹ ᚫ ᛚᚳᛝᛗ"


def main() -> None:
    request = api.RunSpec(
        problem_input=api.RawTextInput(text=CIPHERTEXT_RUNES),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=len(SECRET_KEY)),
        solver=api.SolverSpec.beam_search(width=16, rounds=0, seed=4242),
        scoring=api.ScoringConfig(),
        text_direction=api.TextDirection.RIGHT_TO_LEFT,
    )
    result = api.run(request)

    print("Repeating-key search")
    print("Key length     :", len(SECRET_KEY))
    print("Recovered key  :", result.key)
    print("Recovered runes:", result.plaintext_text)
    print("Score           :", result.score)

    if result.key != SECRET_KEY or result.plaintext != PLAINTEXT:
        raise AssertionError("the search did not recover the exact key and text")


if __name__ == "__main__":
    main()
