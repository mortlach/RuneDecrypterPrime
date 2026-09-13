# ruff: noqa: N999
"""Recover a fixed-length repeating Vigenere key."""

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
    # Spaces in RuneInput provide word boundaries, so WLI can be inferred.
    problem_input = api.RuneInput(value=CIPHERTEXT_RUNES)

    # KeySpec describes the valid search space. Runtime KeyOps supplies the
    # vector operations used by the solver to search it.
    key_space = api.KeySpec.repeating(length=len(SECRET_KEY))

    request = api.RunSpec(
        problem_input=problem_input,
        cipher=api.CipherSpec.vigenere(),
        key_space=key_space,
        solver=api.SolverSpec.beam_search(width=16, rounds=None, seed=4242),
        scoring=api.ScoringConfig(),
        text_direction=api.TextDirection.RTL,
    )
    result = api.run(request)

    print("Repeating-key search")
    print("Key length     :", len(SECRET_KEY))
    print("Recovered key  :", result.key)
    print("Recovered runes:", result.plaintext_runes)
    print("Score           :", result.score)

    # The known key and plaintext are used only to check the completed search.
    if result.key != SECRET_KEY or result.plaintext_indices != PLAINTEXT:
        raise AssertionError("the search did not recover the exact key and text")


if __name__ == "__main__":
    main()
