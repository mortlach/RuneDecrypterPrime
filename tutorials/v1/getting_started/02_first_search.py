# ruff: noqa: N999
"""Find a rail-fence key from the ciphertext.

This time we won't give the solver the key. We'll tell it which rail counts
to consider, then check whether it finds the one we used.
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
    # We'll make our ciphertext using seven rails. The solver will only
    # receive the ciphertext and the range of rail counts below.
    cipher = api.CipherSpec.rail_fence(minimum_rails=2, maximum_rails=8)
    ciphertext = api.encrypt(PLAINTEXT, cipher=cipher, key=SECRET_KEY)

    # KeySpec defines which candidate keys the solver may consider.
    # Here the unknown is one integer: the number of rails.
    # Other problems use a repeating vector of values or a permutation, such
    # as the order of columns in a columnar transposition.
    # Custom key types and their search operations can also be implemented as
    # part of cipher development; see docs/howto/add_cipher.md.
    #
    # Keep seven within these bounds if you want the solver to find our key.
    key_space = api.KeySpec.scalar(minimum=2, maximum=8)

    # SolverSpec tells RDP how to search. We'll use beam search here.
    # A wider beam keeps more alternatives, but also takes more work. The seed
    # lets us repeat the random choices made during a run.
    #
    # GA and simulated annealing are other options. See docs/guides/solvers.md
    # for when they might be useful.
    solver = api.SolverSpec.beam_search(width=8, rounds=0, seed=7)

    # The scorer decides which decrypted candidates look most plausible.
    # This message has no word boundaries, so we'll use individual runes and
    # pairs of runes. The weights below set their contributions.
    scoring = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=False,
        character_order_weights={1: 0.2, 2: 0.8},
        word_length_order_weights={},
    )

    # RunSpec puts those choices together: our input, cipher, possible keys,
    # search method and scorer. We can then pass the whole request to api.run.
    request = api.RunSpec(
        problem_input=api.RuneIndexInput(indices=ciphertext),
        cipher=cipher,
        key_space=key_space,
        solver=solver,
        scoring=scoring,
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
    )
    result = api.run(request)

    # RDP returns the best candidate it found. Since we made this problem
    # ourselves, we can check both the key and the original message.
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
