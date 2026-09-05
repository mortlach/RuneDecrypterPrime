# ruff: noqa: N999
"""Search for a Vigenere key when some positions are left unchanged.

These positions are called interruptors. Here we already know where they are,
so we can tell RDP to leave them alone while it searches for the key.
"""

from rdp import api

# fmt: off
PLAINTEXT = (
    2, 18, 4, 18, 7, 24, 15, 24, 16, 24, 17, 20, 18, 15,
    18, 16, 3, 1, 16, 1, 9, 23, 18, 4, 24, 16, 4, 18,
    18, 10, 9, 0, 4, 3, 9, 16, 3, 0, 2, 18, 8, 3,
    1, 15, 18, 24, 9, 23, 2, 18, 19, 24, 4, 5, 8, 8,
    24, 4, 18, 24, 9, 23, 2, 18, 8, 24, 16, 16, 18, 4,
    7, 18, 4, 18, 8, 24, 1, 21, 16, 28, 24, 16, 10, 16,
)
# fmt: on
SECRET_KEY: api.ConcreteKey = (7, 0, 13, 2, 0)
INTERRUPTOR_POSITIONS = (2, 7, 13)
INTERRUPTOR_SYMBOLS = (4, 24, 15)
CIPHERTEXT_RUNES = (
    "ᚾᛖᚱᚦ ᚾᚪᛟ ᚪ ᛏᚻᛗᛚᚫ ᛋᛖᚠ ᚳᚢᛞ ᚢᛟᚫᛖᛂ ᚪ ᚠᚷᛖᚫ ᛁᛟ "
    "ᚦᚱᛁᚾᚠ ᚳᚠ ᚾᛖ ᛝᚳᚢᛟᛖ ᚻᛂᛞ ᚾᛖ ᚩᚣᚱᛇᚻ ᛝᚣᚱᚫ ᚪᛟᚫ ᚦᚫ "
    "ᚻᚻᛖᛏᚫᚱ ᛚᛚᚱᚫ ᚻᚻᚩᛝ ᛞᛠ ᚻᛖ ᛁᛞ"
)


def main() -> None:
    # Positions are numbered from zero. RDP takes these symbols out before
    # applying Vigenere, then puts them back unchanged. They don't use up
    # positions in the repeating key.
    #
    # Use exact(...) when you know the positions. If you only have a set of
    # possible positions, search(...) lets RDP choose from that set.
    interruptors = api.InterruptorConfig.exact(INTERRUPTOR_POSITIONS)

    request = api.RunSpec(
        problem_input=api.RawTextInput(text=CIPHERTEXT_RUNES),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=len(SECRET_KEY)),
        solver=api.SolverSpec.beam_search(width=8, rounds=0, seed=2025),
        scoring=api.ScoringConfig(),
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
        interruptors=interruptors,
    )
    result = api.run(request)

    print("Known interruptors")
    print("Positions       :", INTERRUPTOR_POSITIONS)
    print("Untouched runes :", INTERRUPTOR_SYMBOLS)
    print("Searched symbols:", len(PLAINTEXT) - len(INTERRUPTOR_POSITIONS))
    print("Recovered key  :", result.key)
    print("Recovered runes:", result.plaintext_text)

    # Check that we've recovered the message and key, and that the interruptor
    # symbols are still where we left them.
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
