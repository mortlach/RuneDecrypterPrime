# ruff: noqa: N999
"""Recover an unknown rail-fence key through the public RDP API.

This is the first search: RDP receives ciphertext plus a bounded recipe and
ranks candidate keys.  The known answer is retained only to check the result.
"""

from rdp import api

# fmt: off
PLAINTEXT = (
    2, 18, 4, 18, 7, 24, 15, 24, 16, 24, 17, 20, 18, 15,
    18, 16, 3, 1, 16, 1, 9, 23, 18, 4, 24, 16, 4, 18,
    18,
)
# fmt: on
SECRET_KEY: api.ConcreteKey = (7,)


def main() -> None:
    # CipherSpec describes how candidate keys will be applied.  The bounds here
    # also reject rail counts that this cipher instance cannot accept.
    cipher = api.CipherSpec.rail_fence(minimum_rails=2, maximum_rails=8)
    ciphertext = api.encrypt(PLAINTEXT, cipher=cipher, key=SECRET_KEY)

    # KeySpec describes what may be searched, not the answer.  A scalar key is
    # one integer in a range.  Other public shapes include repeating keys,
    # repeating-length ranges, permutations and structured periodic keys.
    # Custom key types and their search operations can also be implemented
    # as part of cipher development; see docs/howto/add_cipher.md.
    # Keep the true rail count within these bounds to make recovery possible.
    key_space = api.KeySpec.scalar(minimum=2, maximum=8)

    # SolverSpec is the search recipe.  Width is a work/coverage choice; the
    # seed records stochastic choices.  Neither is evidence that the best
    # candidate is correct. A wider beam retains more candidates at greater
    # cost. GA and simulated annealing offer other search strategies; see
    # docs/guides/solvers.md for compatible choices.
    solver = api.SolverSpec.beam_search(width=8, rounds=0, seed=7)

    # ScoringConfig says how candidates are ranked.  This small rail-fence case
    # uses character evidence only because it carries no word boundaries.
    scoring = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=False,
        character_order_weights={1: 0.2, 2: 0.8},
        word_length_order_weights={},
    )

    # RunSpec binds the evidence to one explicit cipher, key space, solver,
    # scorer and reading direction.  api.run has one object to execute and one
    # configuration to report afterwards.
    request = api.RunSpec(
        problem_input=api.RuneIndexInput(indices=ciphertext),
        cipher=cipher,
        key_space=key_space,
        solver=solver,
        scoring=scoring,
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
    )
    result = api.run(request)

    # A completed search returns its best candidate and a truthful stop reason.
    # Exact recovery is established separately by comparison with known truth.
    exact_recovery = result.key == SECRET_KEY and result.plaintext == PLAINTEXT

    print("First search")
    print("Recovered key  :", result.key)
    print("Recovered runes:", result.plaintext_text)
    print("Stop reason    :", result.status.stop_reason.value)
    print("Exact recovery :", exact_recovery)

    if not exact_recovery:
        raise AssertionError("the search did not recover the exact key and text")


if __name__ == "__main__":
    main()
