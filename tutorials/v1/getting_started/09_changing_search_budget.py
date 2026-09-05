# ruff: noqa: N999
"""Change a search budget while holding the cryptanalytic problem fixed.

A larger budget may explore more candidates, but it is not automatically a
better explanation of the evidence.  Here both bounded searches recover the
same answer; the wider one simply performs more evaluations.
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


def build_request(*, width: int) -> api.RunSpec:
    # Only beam width changes.  Ciphertext, cipher, key space, scoring,
    # direction and seed remain fixed so the comparison has one variable.
    return api.RunSpec(
        problem_input=api.RawTextInput(text=CIPHERTEXT_RUNES),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=len(SECRET_KEY)),
        solver=api.SolverSpec.beam_search(width=width, rounds=0, seed=4242),
        scoring=api.ScoringConfig(),
        text_direction=api.TextDirection.RIGHT_TO_LEFT,
    )


def main() -> None:
    narrow = api.run(build_request(width=1))
    wider = api.run(build_request(width=16))

    print("Changing search budget")
    print("Narrow key         :", narrow.key)
    print("Narrow evaluations :", narrow.solver_report.evaluations)
    print("Wider key          :", wider.key)
    print("Wider evaluations  :", wider.solver_report.evaluations)
    print("Same candidate     :", narrow.plaintext == wider.plaintext)

    both_exact = (
        narrow.key == wider.key == SECRET_KEY
        and narrow.plaintext == wider.plaintext == PLAINTEXT
    )
    if not both_exact:
        raise AssertionError("the controlled budget comparison changed its result")
    if wider.solver_report.evaluations <= narrow.solver_report.evaluations:
        raise AssertionError("the wider search did not perform more evaluations")


if __name__ == "__main__":
    main()
