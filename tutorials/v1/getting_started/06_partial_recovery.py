# ruff: noqa: N999
"""Inspect an honest partial result from an intentionally narrow search."""

from rdp import api

REFERENCE_PLAINTEXT = (
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
CIPHERTEXT_RUNES = (
    "ᚳᛗᚻᛗ ᛇᚱᛒ ᚢ ᛗᚫᛝᛝᛞ ᚪᛚᛟ ᚷᚦᛚ ᚦᛉᚩᛚᛁ ᛡ ᛒᚻᛗᛞ ᛗᛂ "
    "ᚷᚹᚱᛈᛒ ᚻᚾ ᚱᚪ ᛂᚱᚳᛏᛞ ᚱᛂᚠ ᚳᛗ ᛞᚫᚾᛉᛁ ᛉᛡᚳᛟ ᚫᛉᚩ ᚱᚪ "
    "ᛂᚫᛚᛒᛞᛈ ᚾᚪᚹᛗ ᛇᚫᚷᚢ ᛖᚳ ᛡᛒ ᛉᛒ"
)


def match_ratio(candidate: tuple[int, ...]) -> float:
    matches = sum(
        observed == expected
        for observed, expected in zip(
            candidate, REFERENCE_PLAINTEXT, strict=True
        )
    )
    return matches / len(REFERENCE_PLAINTEXT)


def main() -> None:
    request = api.RunSpec(
        problem_input=api.RawTextInput(text=CIPHERTEXT_RUNES),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=8),
        solver=api.SolverSpec.beam_search(width=4, rounds=0, seed=909),
        scoring=api.ScoringConfig(),
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
    )
    first = api.run(request)
    second = api.run(request)
    ratio = match_ratio(first.plaintext)

    print("Bounded partial recovery")
    print("Recovered key  :", first.key)
    print("Recovered runes:", first.plaintext_text)
    print("Reference match:", f"{ratio:.3f}")
    print("Beam width     :", 4)
    print("Stop category  :", first.status.stop_category.value)
    print("Stop reason    :", first.status.stop_reason.value)
    print("Interpretation : partial evidence, not an exact solve")
    print("Acceptance     : route fixture check, not a production score")

    stable_partial = (
        first.key == second.key
        and first.plaintext == second.plaintext
        and 0.70 <= ratio < 1.0
        and first.status.stop_category.value == "budget"
    )
    if not stable_partial:
        raise AssertionError("the bounded run did not return its expected partial result")


if __name__ == "__main__":
    main()
