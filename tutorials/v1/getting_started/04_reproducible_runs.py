# ruff: noqa: N999
"""Run the same bounded search twice and inspect its repeatability record.

Repeatability is an observable property of a complete recipe.  Recording a
seed is necessary for stochastic work, but is not by itself a correctness
claim or a promise that unrelated devices and backends are interchangeable.
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


def build_request() -> api.RunSpec:
    cipher = api.CipherSpec.rail_fence(minimum_rails=2, maximum_rails=8)
    ciphertext = api.encrypt(PLAINTEXT, cipher=cipher, key=SECRET_KEY)
    # Keeping request construction in one function makes it harder for the two
    # runs to drift apart while we are claiming to compare identical recipes.
    return api.RunSpec(
        problem_input=api.RuneIndexInput(indices=ciphertext),
        cipher=cipher,
        key_space=api.KeySpec.scalar(minimum=2, maximum=8),
        solver=api.SolverSpec.beam_search(width=8, rounds=0, seed=314159),
        scoring=api.ScoringConfig(
            character_lane_enabled=True,
            word_length_lane_enabled=False,
            character_order_weights={1: 0.2, 2: 0.8},
            word_length_order_weights={},
        ),
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
    )


def main() -> None:
    # The request is rebuilt, not reused after mutation: public specs are
    # immutable values and each run records its own effective configuration.
    first = api.run(build_request())
    second = api.run(build_request())

    print("Reproducible runs")
    print("Requested seed:", first.reproducibility.requested_seed)
    print("Effective seed:", first.reproducibility.effective_seed)
    print("Backend       :", first.reproducibility.backend.value)
    print("Same result   :", first.plaintext == second.plaintext)
    print("Same status   :", first.status == second.status)

    # We compare candidate, score, status and effective seed.  Matching only the
    # recovered plaintext would miss meaningful execution differences.
    same_observations = (
        first.key == second.key == SECRET_KEY
        and first.plaintext == second.plaintext == PLAINTEXT
        and first.score == second.score
        and first.status == second.status
        and first.reproducibility.requested_seed
        == second.reproducibility.requested_seed
        == 314159
        and first.reproducibility.effective_seed
        == second.reproducibility.effective_seed
        == 314159
    )
    if not same_observations:
        raise AssertionError(
            "identical seeded requests produced different observations"
        )


if __name__ == "__main__":
    main()
