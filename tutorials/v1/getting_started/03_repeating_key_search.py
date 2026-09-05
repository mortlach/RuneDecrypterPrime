# ruff: noqa: N999
"""Find a repeating Vigenere key.

We know the key has four values, but we'll ask RDP to find what they are.
We'll also supply the ciphertext as runes this time, with spaces between words.
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
    # RawTextInput lets us supply the runes directly. RDP converts them to
    # numbers and uses the spaces to work out where the words are.
    # This word-location information (WLI) gives the scorer something else to
    # work with alongside the rune sequences.
    problem_input = api.RawTextInput(text=CIPHERTEXT_RUNES)

    # A repeating key cycles through the same values along the message.
    # Here we know its length. If we wanted to search different lengths too,
    # we could use KeySpec.repeating_range(...).
    key_space = api.KeySpec.repeating(length=len(SECRET_KEY))

    # Set the reading direction to match how the text was prepared. It affects
    # the rune and word information RDP builds, so changing it is more than
    # turning the display around.
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

    # Now compare the result with our original message and key. We kept these
    # for checking afterwards; they weren't given to the solver.
    if result.key != SECRET_KEY or result.plaintext != PLAINTEXT:
        raise AssertionError("the search did not recover the exact key and text")


if __name__ == "__main__":
    main()
