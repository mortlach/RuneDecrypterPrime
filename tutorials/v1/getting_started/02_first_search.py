# ruff: noqa: N999
"""Recover an unknown rail-fence key through the public RDP API."""

from rdp import api

PLAINTEXT = (
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
)
SECRET_KEY: api.ConcreteKey = (7,)


def main() -> None:
    cipher = api.CipherSpec.rail_fence(minimum_rails=2, maximum_rails=8)
    ciphertext = api.encrypt(PLAINTEXT, cipher=cipher, key=SECRET_KEY)
    request = api.RunSpec(
        problem_input=api.RuneIndexInput(indices=ciphertext),
        cipher=cipher,
        key_space=api.KeySpec.scalar(minimum=2, maximum=8),
        solver=api.SolverSpec.beam_search(width=8, rounds=0, seed=7),
        scoring=api.ScoringConfig(
            character_lane_enabled=True,
            word_length_lane_enabled=False,
            character_order_weights={1: 0.2, 2: 0.8},
            word_length_order_weights={},
        ),
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
    )
    result = api.run(request)
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
