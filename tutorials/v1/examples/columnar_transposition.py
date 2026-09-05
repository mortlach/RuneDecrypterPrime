"""Recover the order of seven columns with a hybrid search.

The plaintext makes a controlled problem and calibrates its stopping score.
The solver receives ciphertext and the permitted column orders. Repository
text helpers prepare the rune input; the actual request uses the public API.
"""

from rdp import api
from rdp.data.runeglish import Runeglish
from tutorials.v1.data.plaintext_fixtures import plaintext_english_string
from tutorials.v1.support.tutorial_utils import oracle_stop_score, print_stop_summary

MIN_MATCH_RATIO = 1.0
TUTORIAL_SEED = 12345


def encrypt_columnar(pt: str, key: list[int]) -> str:
    """Write rows, then read columns in the supplied order."""
    columns = len(key)
    return "".join(pt[column::columns] for column in key)


def main() -> None:
    # Spaces are removed for this transposition example, so the scorer below
    # uses adjacent rune pairs without word-location information.
    direction = api.TextDirection.RIGHT_TO_LEFT
    _, _, plaintext_runes = Runeglish.encode_english_to_runes(
        plaintext_english_string, direction=direction
    )
    plaintext_runes = plaintext_runes.replace(" ", "")
    reference = Runeglish.rune_to_pos(plaintext_runes)
    known_key = [3, 6, 1, 4, 2, 0, 5]
    ciphertext = encrypt_columnar(plaintext_runes, known_key)
    indices = Runeglish.rune_to_pos(ciphertext)

    # A permutation contains each column exactly once. Repeating keys would
    # allow duplicates, which describe a different problem. To change the number
    # of columns, change the fixture key and its order together.
    cipher = api.CipherSpec.columnar(columns=len(known_key))
    key_space = api.KeySpec.permutation(length=len(known_key))
    scoring = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=False,
        character_order_weights={2: 1.0},
        word_length_order_weights={},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )

    # Known plaintext calibrates this example's stopping threshold. That makes
    # the run bounded, but it is reference use: an unknown-text investigation
    # would need a stopping rule that does not require its answer in advance.
    stop = oracle_stop_score(
        reference,
        None,
        scoring,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.45,
        fallback=0.503,
    )
    print_stop_summary("Columnar Hybrid", stop)

    # Hybrid combines beam exploration, a population search and annealing.
    # Each stage has its own budget. Increase one at a time when investigating
    # search cost; the retained settings below are this example's recipe.
    solver = api.SolverSpec.hybrid(
        use_beam_search=True,
        beam_width=96,
        beam_rounds=6,
        beam_expansion=api.advanced.BeamExpansionMode.SAMPLE,
        sample_per_parent=48,
        top_parents_fraction=0.4,
        genetic_algorithm=api.SolverSpec.genetic_algorithm(
            population_size=96,
            generations=40,
            elite_fraction=0.1,
            crossover_fraction=0.85,
            mutation_probability=0.3,
            tournament_size=3,
            plateau_generations=12,
            plateau_minimum_delta=0.0001,
            target_score=stop.stop_score,
        ),
        simulated_annealing=api.SolverSpec.simulated_annealing(
            iterations=3000,
            initial_temperature=0.95,
            minimum_temperature=0.0001,
            cooling_rate=0.997,
            plateau_iterations=300,
            plateau_minimum_delta=0.0001,
            local_improvement_on_accept=True,
            target_score=stop.stop_score,
        ),
        seed=TUTORIAL_SEED,
        plateau_rounds=8,
        plateau_minimum_delta=0.0001,
        target_score=stop.stop_score,
    )
    request = api.RunSpec(
        problem_input=api.RuneIndexInput(indices=indices, word_lengths=None),
        cipher=cipher,
        key_space=key_space,
        solver=solver,
        scoring=scoring,
        telemetry_enabled=True,
        text_direction=direction,
        compute_device=api.ComputeDevice.CPU,
    )
    print("Columnar transposition")
    print("Ciphertext preview:", ciphertext[:160])
    print("Reference use    : stop-score calibration and final comparison")
    result = api.run(request)

    match_ratio = sum(
        a == b for a, b in zip(result.plaintext, reference, strict=True)
    ) / len(reference)
    print(f"Match ratio: {match_ratio:.3f}")
    # The summary describes the same request that was executed. Use
    # SummaryOptions.for_debug() when you need additional diagnostics.
    api.display.print_result(
        result, spec=request, options=api.display.SummaryOptions.for_tutorial()
    )
    if match_ratio < MIN_MATCH_RATIO:
        raise AssertionError("columnar tutorial did not recover exact plaintext")


if __name__ == "__main__":
    main()
