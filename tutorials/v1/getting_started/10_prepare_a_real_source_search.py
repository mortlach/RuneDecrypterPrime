# ruff: noqa: N999
"""Prepare a Welcome Pilgrim search without running the longer solve."""

from rdp import api

SOURCE_LABEL = "welcome_pilgrim"

# These values come from the existing solved-source example.
KEY_LENGTH = 8
INTERRUPTOR_COUNT = 11


def main() -> None:
    payload = api.liber_primus.payload_from_label(SOURCE_LABEL)

    # Zero-valued ciphertext positions form the reviewed candidate pool.
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

    # Key length and interruptor count are prior information from the known
    # solution. The key values and exact interruptor positions are not supplied.
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
    print("Source             :", payload.metadata["display_name"])
    print("Ciphertext length  :", len(payload.ct_idx))
    print("Key shape          : repeating, length", KEY_LENGTH)
    print("Interruptor pool   :", len(candidate_positions))
    print("Interruptors sought:", INTERRUPTOR_COUNT)
    print("Solver             :", request.solver.kind.value)
    print("Execution          : not started")

    if len(payload.ct_idx) != len(payload.wli) or len(payload.ct_idx) != 515:
        raise AssertionError("the source payload is no longer aligned")
    if len(candidate_positions) != 25:
        raise AssertionError("the reviewed interruptor candidate pool changed")


if __name__ == "__main__":
    main()
