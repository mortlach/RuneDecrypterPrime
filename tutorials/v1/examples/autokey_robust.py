"""Autokey robust.

See the example catalogue for assets, runtime and reference use.
"""

from __future__ import annotations

from rdp import api
from rdp.data.runeglish import Runeglish
from tutorials.v1.data.plaintext_fixtures import plaintext_english_string
from tutorials.v1.support import tutorial_pretty as pretty

DIRECTION = api.TextDirection.RIGHT_TO_LEFT
TRUE_SEED = [6, 1, 4, 17, 3, 22, 9, 12]
SOLVER_SEED = 20260822
BEAM_WIDTH = 96
ROUNDS = 32
RESTARTS = 3
SCORER_PARAMS = api.ScoringConfig(
    character_lane_enabled=False,
    word_length_lane_enabled=True,
    character_order_weights={},
    word_length_order_weights={1: 0.3, 2: 0.7},
    objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10),
)
DISPLAY_SCORER_PARAMS = api.ScoringConfig(
    character_lane_enabled=False,
    word_length_lane_enabled=True,
    word_length_order_weights={1: 0.3, 2: 0.7},
    objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10),
)


def _ints(value: object) -> list[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [int(item) for item in value]


def _match(found: list[int], expected: list[int]) -> float:
    return sum((a == b for a, b in zip(found, expected, strict=True))) / len(expected)


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Autokey robust Beam solve",
        cipher="autokey",
        solver="beam",
        direction=DIRECTION.value,
        expected_result="exact solve",
        uses_reference_stop_score=False,
    )
    plaintext = plaintext_english_string
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(plaintext, direction=DIRECTION)
    seed_length = len(TRUE_SEED)
    cipher_spec = api.CipherSpec.autokey(alphabet_size=29)
    cipher = api.CipherSpec.autokey(alphabet_size=29)
    ciphertext = api.encrypt(
        tuple(int(value) for value in pt_idx),
        cipher=cipher,
        key=tuple(int(value) for value in TRUE_SEED),
    )
    solver = api.SolverSpec.beam_search(
        width=BEAM_WIDTH,
        rounds=ROUNDS,
        restarts=RESTARTS,
        expansion=api.advanced.BeamExpansionMode.SWEEP,
        plateau_rounds=None,
        seed=SOLVER_SEED,
    )
    print("Robust Autokey qualification-derived tutorial")
    print("recipe: autokey_wli12_beam_v1")
    print(f"direction: {DIRECTION.value}")
    print(f"seed length: {seed_length}")
    print(f"Beam width / rounds / restarts: {BEAM_WIDTH} / {ROUNDS} / {RESTARTS}")
    print("scorer: WLI1=0.30, WLI2=0.70; character lane disabled")
    print(f"deterministic solver seed: {SOLVER_SEED}")
    result = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(
                indices=_ints(ciphertext), word_lengths=wli
            ),
            cipher=cipher_spec,
            key_space=api.KeySpec.repeating(length=seed_length),
            solver=solver,
            scoring=SCORER_PARAMS,
            telemetry_enabled=True,
            text_direction=DIRECTION,
        )
    )
    recovered_plaintext = _ints(result.plaintext)
    recovered_seed = _ints(result.key)[:seed_length]
    plaintext_match = _match(recovered_plaintext, [int(v) for v in pt_idx])
    seed_match = recovered_seed == TRUE_SEED
    recovered_runes = Runeglish.to_rune(recovered_plaintext, wli)
    print(f"solver score: {float(result.score):.6f}")
    print(f"stop reason: {result.solver_report.status.stop_reason}")
    print(
        f"recovered plaintext: {recovered_runes[:240]}{('...' if len(recovered_runes) > 240 else '')}"
    )
    print(f"recovered seed: {recovered_seed}")
    print(f"plaintext match: {plaintext_match:.3f}")
    print(f"seed match: {seed_match}")
    print(f"Match ratio: {plaintext_match:.3f}")
    pretty.print_summary_spacer()
    api.display.print_result(result, options=api.display.SummaryOptions.for_tutorial())
    if plaintext_match != 1.0 or not seed_match:
        raise AssertionError("robust Autokey tutorial did not recover exact truth")


if __name__ == "__main__":
    main()
