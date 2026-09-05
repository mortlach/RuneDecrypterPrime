# ruff: noqa: N999
"""Put together a search for Welcome Pilgrim.

We can now connect a real source to the cipher, key space and search settings.
This file prepares the request. The worked LP example runs the longer solve.
"""

from rdp import api

SOURCE_LABEL = "welcome_pilgrim"
# We know this length from the existing solved-source example.
KEY_LENGTH = 8
INTERRUPTOR_COUNT = 11


def main() -> None:
    payload = api.liber_primus.payload_from_label(SOURCE_LABEL)

    # We'll treat the zero-valued ciphertext runes as possible interruptors
    # and ask RDP to choose eleven of them. In example 05 we supplied the
    # exact positions; here the positions are part of the search.
    candidate_positions = tuple(
        index for index, value in enumerate(payload.ct_idx) if value == 0
    )
    interruptors = api.InterruptorConfig.search(
        candidate_positions,
        minimum_count=INTERRUPTOR_COUNT,
        maximum_count=INTERRUPTOR_COUNT,
        strategy=api.advanced.InterruptorSearchStrategy.KEY_OPERATIONS,
        maximum_combinations=5000,
    )

    # The key length and interruptor count come from the existing solution. We
    # aren't supplying the key values, but we are using that prior knowledge.
    # If you change the pool or the count, you're trying a different
    # explanation of the ciphertext, not simply giving the solver more time.
    request = api.RunSpec(
        problem_input=api.RuneIndexInput(
            indices=payload.ct_idx,
            word_lengths=payload.wli,
        ),
        cipher=api.CipherSpec.vigenere(alphabet_size=29),
        key_space=api.KeySpec.repeating(length=KEY_LENGTH),
        solver=api.SolverSpec.beam_search(
            width=64,
            expansion=api.advanced.BeamExpansionMode.SWEEP,
            plateau_rounds=5,
            plateau_minimum_delta=0.0001,
            seed=2026,
            rounds=0,
        ),
        scoring=api.ScoringConfig(
            character_lane_enabled=True,
            word_length_lane_enabled=True,
            character_order_weights={1: 0.3, 2: 0.7},
            word_length_order_weights={1: 0.3, 2: 0.7},
            objective=api.advanced.ScoringObjective.percentile_log_probability(
                window_size=10
            ),
        ),
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
        interruptors=interruptors,
    )

    print("Prepared real-source search")
    print("Source            :", payload.metadata["display_name"])
    print("Ciphertext length :", len(payload.ct_idx))
    print("Key shape         : repeating, length", KEY_LENGTH)
    print("Interruptor pool  :", len(candidate_positions))
    print("Interruptors sought:", INTERRUPTOR_COUNT)
    print("Solver            :", request.solver.kind.value)
    print("Execution         : not started")
    print("Next              : examples/lp_welcome_pilgrim_solve.py")

    if len(payload.ct_idx) != len(payload.wli) or len(payload.ct_idx) != 515:
        raise AssertionError("the source payload is no longer aligned")
    if len(candidate_positions) != 25:
        raise AssertionError("the reviewed interruptor candidate pool changed")


if __name__ == "__main__":
    main()
