"""Prepare the reviewed Welcome Pilgrim search without running it.

Welcome Pilgrim uses a repeating Vigenere key and interruptors. We know the
key length and how many interruptors to seek, but leave their values and exact
positions for the solver.
"""

from rdp import api

SOURCE_LABEL = "welcome_pilgrim"
KEY_LENGTH = 8
INTERRUPTOR_COUNT = 11


def build_request() -> api.RunSpec:
    """Build the real-source request used by the runnable example."""
    source = api.liber_primus.source(SOURCE_LABEL)
    source_data = api.liber_primus.load_source(SOURCE_LABEL)

    # The solved-page analysis narrows the possible interruptors to positions
    # where the ciphertext rune has index zero.
    candidate_positions = tuple(
        index for index, value in enumerate(source_data.ct_idx) if value == 0
    )

    return api.RunSpec(
        problem_input=source,
        cipher=api.CipherSpec.vigenere(alphabet_size=29),
        key_space=api.KeySpec.repeating(length=KEY_LENGTH),
        solver=api.SolverSpec.beam_search(
            width=64,
            expansion=api.advanced.BeamExpansionMode.SWEEP,
            plateau_rounds=5,
            plateau_minimum_delta=0.0001,
            seed=2026,
            rounds=None,
        ),
        scoring=api.ScoringConfig(
            character_lane_enabled=True,
            wli_lane_enabled=True,
            character_order_weights={1: 0.3, 2: 0.7},
            wli_order_weights={1: 0.3, 2: 0.7},
            objective=api.advanced.ScoringObjective.percentile_log_probability(
                window_size=10
            ),
        ),
        text_direction=api.TextDirection.LTR,
        interruptors=api.InterruptorConfig.search(
            candidate_positions,
            minimum_count=INTERRUPTOR_COUNT,
            maximum_count=INTERRUPTOR_COUNT,
            strategy=api.advanced.InterruptorSearchStrategy.KEY_OPERATIONS,
            maximum_combinations=5000,
        ),
    )


def main() -> None:
    """Build the request and summarize the search that would run."""
    request = build_request()
    positions = request.interruptors.parameters["candidate_positions"]

    print("Source             :", SOURCE_LABEL)
    print("Cipher             : Vigenere")
    print("Known key length   :", KEY_LENGTH)
    print("Interruptor pool   :", len(positions))
    print("Interruptors sought:", INTERRUPTOR_COUNT)
    print("Solver             :", request.solver.kind.value)
    print("Execution          : not started")


if __name__ == "__main__":
    main()
