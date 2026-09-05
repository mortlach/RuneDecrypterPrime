"""Two period cribs interruptors.

See the example catalogue for assets, runtime and reference use.
"""

from __future__ import annotations

from time import perf_counter

from data.two_period_cribs_demo import build_demo_fixture

from rdp import api
from tutorials.v1.support import tutorial_pretty as pretty
from tutorials.v1.support.tutorial_benchmark import TutorialRunKind, TutorialStopPolicy
from tutorials.v1.support.tutorial_reference import TutorialReference
from tutorials.v1.support.tutorial_session_report import print_tutorial_session_report

PERIOD_A = 13
PERIOD_B = 31
SEED = 101
STARTS = 1
REFERENCE_INTERRUPTORS = (190, 194)
INTERRUPTOR_POOL = (190, 192, 194)
INTERRUPTOR_COUNT = 2
FIXED_CRIBS = (
    ("uncomfortable", 188),
    ("dormouse", 81),
    ("dormouse", 206),
    ("suppose", 241),
    ("talcing", 169),
    ("sitting", 92),
    ("out", 12),
    ("front", 27),
)


def run_tutorial():
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Two-period cribs: structural interruptor pool",
        cipher="two_period_vigenere",
        solver="two_period_cribs",
        direction="ltr",
        expected_result="exact key, plaintext and interruptor positions",
        uses_reference_stop_score=False,
    )
    cipher, key = (
        api.CipherSpec.two_period_vigenere(
            first_period=PERIOD_A, second_period=PERIOD_B, alphabet_size=29
        ),
        api.KeySpec.repeating(length=PERIOD_A + PERIOD_B),
    )
    fixture = build_demo_fixture(cipher, interruptors=REFERENCE_INTERRUPTORS)
    solver = api.SolverSpec.two_period_cribs(
        fixed_cribs=FIXED_CRIBS, starts=STARTS, seed=SEED
    )
    interruptors = api.InterruptorConfig.search(
        INTERRUPTOR_POOL,
        minimum_count=INTERRUPTOR_COUNT,
        maximum_count=INTERRUPTOR_COUNT,
        strategy=api.advanced.InterruptorSearchStrategy.AUTO,
        maximum_combinations=5000,
    )
    started = perf_counter()
    result = api.run(
        problem_input=api.RuneIndexInput(
            indices=fixture.ciphertext, word_lengths=fixture.wli
        ),
        cipher=cipher,
        key_space=key,
        solver=solver,
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
        interruptors=interruptors,
    )
    elapsed_s = perf_counter() - started
    pretty.print_summary_spacer()
    api.display.print_result(result)
    reference = TutorialReference.key_and_plaintext(
        key_idx=fixture.reference_key,
        plaintext_idx=fixture.reference_plaintext,
        label="deterministic interruptor tutorial fixture",
    )
    report = print_tutorial_session_report(
        title="Two-period cribs: structural interruptor pool",
        cipher="two_period_vigenere",
        solution=result,
        solver_report=result.solver_report,
        reference=reference,
        run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
        stop_policy=TutorialStopPolicy(target_match_ratio=1.0),
    )
    details = result.solver_report.details["two_period_solve"]
    match_ratio = reference.match_ratio(result)
    key_exact = reference.key_exact(result)
    winning_interruptors = tuple(details["interruptors"]["winning_positions"])
    print(f"winning_interruptors : {winning_interruptors}")
    print(f"tutorial_elapsed_s : {elapsed_s:.6f}")
    print(f"match_ratio : {match_ratio:.6f}")
    assert report["benchmark"]["match_ratio"] == 1.0
    assert match_ratio == 1.0
    assert key_exact is True
    assert winning_interruptors == fixture.reference_interruptors
    return result


if __name__ == "__main__":
    run_tutorial()
