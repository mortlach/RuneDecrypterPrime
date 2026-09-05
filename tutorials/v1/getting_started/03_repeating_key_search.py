# ruff: noqa: N999
"""Recover a repeating Vigenere key from rune text with word boundaries.

This stop changes both the key shape and the input representation while keeping
the same RunSpec -> api.run -> RunResult route introduced in stop 02.
"""

from rdp import api

# fmt: off
PLAINTEXT = (
    16, 8, 18, 4, 18, 7, 24, 15, 24, 16, 24, 17, 20, 18,
    15, 18, 16, 3, 1, 16, 1, 9, 23, 18, 4, 24, 16, 4,
    18, 18,
)
# fmt: on
SECRET_KEY: api.ConcreteKey = (3, 1, 4, 1)
CIPHERTEXT_RUNES = "ᛗᚾᛟᚳᛝ ᚻᛠᛏ ᛡ ᛒᛠᛖᛞᛗ ᛗᛗᛗ ᚱᚳᛒ ᚱᛁᛡᛗᚹ ᚫ ᛚᚳᛝᛗ"


def main() -> None:
    # RawTextInput accepts visible rune text.  Spaces become word-location
    # information (WLI), allowing the default scorer to use both character and
    # word-shape evidence without asking this file to build WLI itself.
    problem_input = api.RawTextInput(text=CIPHERTEXT_RUNES)

    # A repeating key is a vector whose values cycle across the text.  Its
    # length is fixed here; repeating_range is available when length itself is
    # part of the search question.
    key_space = api.KeySpec.repeating(length=len(SECRET_KEY))

    # Direction is part of the evidence model, not a display preference.  It
    # affects rune tokenisation and the interpretation of word positions.
    request = api.RunSpec(
        problem_input=problem_input,
        cipher=api.CipherSpec.vigenere(),
        key_space=key_space,
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

    # As before, known truth checks the returned candidate after the search; it
    # was not supplied to ranking or stopping.
    if result.key != SECRET_KEY or result.plaintext != PLAINTEXT:
        raise AssertionError("the search did not recover the exact key and text")


if __name__ == "__main__":
    main()
