"""Try several starts on a Vigenere interruptor problem.

Choose the best-scoring attempt first, then compare it with the original
message. This avoids using the answer to decide which attempt to keep.
"""

from __future__ import annotations

import numpy as np

from rdp import api
from rdp.data.runeglish import Runeglish
from tutorials.v1.data.plaintext_fixtures import plaintext1, word_breaks1
from tutorials.v1.data.two_period_cribs_demo import encrypt_interruptor_fixture
from tutorials.v1.support import tutorial_pretty as pretty

DIRECTION = api.TextDirection.LEFT_TO_RIGHT
TRUE_KEY = [7, 0, 13, 2, 5, 21, 8]
TRUE_INTERRUPTORS = [190, 194]
INTERRUPTOR_COUNT = 2
INTERRUPTOR_POOL = [71, 108, 156, 190, 194, 231, 278, 315]
SOLVER_SEED = 20260822
BEAM_WIDTH = 64
RESTARTS = 3
SCORER_PARAMS = api.ScoringConfig(
    character_lane_enabled=True,
    word_length_lane_enabled=True,
    character_order_weights={2: 0.3},
    word_length_order_weights={2: 0.7},
    objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10),
)
DISPLAY_SCORER_PARAMS = api.ScoringConfig(
    character_lane_enabled=True,
    word_length_lane_enabled=True,
    character_order_weights={2: 0.3},
    word_length_order_weights={2: 0.7},
    objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10),
)


def _ints(value: object) -> list[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [int(item) for item in value]


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Vigenere interruptors robust three-restart Beam search",
        cipher="vigenere interruptors",
        solver="beam",
        direction=DIRECTION.value,
        expected_result="exact solve",
        uses_reference_stop_score=False,
    )
    pt_idx = [int(v) for v in plaintext1]
    wli = [list(pair) for pair in word_breaks1]
    if max(INTERRUPTOR_POOL) >= len(pt_idx):
        raise ValueError("interruptor tutorial fixture is shorter than its search pool")
    cipher_spec = api.CipherSpec.vigenere(alphabet_size=29)
    cipher = api.CipherSpec.vigenere(alphabet_size=29)
    ciphertext = encrypt_interruptor_fixture(
        np.asarray(pt_idx, dtype=np.uint8),
        cipher=cipher,
        key=tuple(
            int(_concrete_key_value)
            for _concrete_key_value in np.asarray(TRUE_KEY, dtype=np.uint8)
        ),
        interruptor_positions=TRUE_INTERRUPTORS,
    )
    solver = api.SolverSpec.beam_search(
        width=BEAM_WIDTH,
        restarts=RESTARTS,
        expansion=api.advanced.BeamExpansionMode.SWEEP,
        plateau_rounds=10,
        seed=SOLVER_SEED,
        rounds=0,
    )
    search = api.InterruptorConfig.search(
        INTERRUPTOR_POOL,
        minimum_count=INTERRUPTOR_COUNT,
        maximum_count=INTERRUPTOR_COUNT,
        strategy=api.advanced.InterruptorSearchStrategy.AUTO,
        maximum_combinations=5000,
    )
    print("Robust Vigenere interruptor qualification-derived tutorial")
    print("recipe: vigenere_interruptors_char2_wli2_beam3_v1")
    print(f"Beam width / restarts: {BEAM_WIDTH} / {RESTARTS}")
    print("scorer: char2=0.30, WLI2=0.70")
    print(f"interruptor search pool: {INTERRUPTOR_POOL}")
    print(f"deterministic solver seed: {SOLVER_SEED}")
    result = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(
                indices=_ints(ciphertext), word_lengths=wli
            ),
            cipher=cipher_spec,
            key_space=api.KeySpec.repeating(length=len(TRUE_KEY)),
            solver=solver,
            scoring=SCORER_PARAMS,
            telemetry_enabled=True,
            text_direction=DIRECTION,
            interruptors=search,
        )
    )
    recovered_plaintext = _ints(result.plaintext)
    recovered_values = _ints(result.key)
    recovered_key = recovered_values[: len(TRUE_KEY)]
    recovered_interruptors = sorted(recovered_values[len(TRUE_KEY) :])
    plaintext_match = sum(
        (a == b for a, b in zip(recovered_plaintext, pt_idx, strict=True))
    ) / len(pt_idx)
    key_match = recovered_key == TRUE_KEY
    interruptor_match = recovered_interruptors == TRUE_INTERRUPTORS
    recovered_runes = Runeglish.to_rune(recovered_plaintext, wli)
    print(f"solver score: {float(result.score):.6f}")
    print(f"stop reason: {result.solver_report.status.stop_reason}")
    print(
        f"recovered plaintext: {recovered_runes[:240]}{('...' if len(recovered_runes) > 240 else '')}"
    )
    print(f"recovered key: {recovered_key}")
    print(f"plaintext match: {plaintext_match:.3f}")
    print(f"key match: {key_match}")
    print(f"interruptor match: {interruptor_match}")
    print(f"recovered interruptors: {recovered_interruptors}")
    print(f"Match ratio: {plaintext_match:.3f}")
    pretty.print_summary_spacer()
    api.display.print_result(result, options=api.display.SummaryOptions.for_tutorial())
    if len(TRUE_INTERRUPTORS) != INTERRUPTOR_COUNT:
        raise AssertionError(
            "generated fixture does not contain the declared interruptor count"
        )
    if plaintext_match != 1.0 or not key_match or (not interruptor_match):
        raise AssertionError("robust interruptor tutorial did not recover exact truth")


if __name__ == "__main__":
    main()
