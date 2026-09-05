"""Two period cribs p13 p31 search.

See the example catalogue for assets, runtime and reference use.
"""

from __future__ import annotations

import json
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
STARTS = 8
REFERENCE_INTERRUPTORS = (300,)
INTERRUPTOR_POOL = (300, 192)
INTERRUPTOR_COUNT = 1
FIXED_CRIBS = (("uncomfortable", 188), ("dormouse", 81))
WORDS_TO_TRY = ("dormouse",)


def run_tutorial():
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Two-period cribs: P13/P31 interruptor search",
        cipher="two_period_vigenere",
        solver="two_period_cribs",
        direction="ltr",
        expected_result="exact d14 solve",
        uses_reference_stop_score=False,
    )
    cipher, key = (
        api.CipherSpec.two_period_vigenere(
            first_period=PERIOD_A, second_period=PERIOD_B, alphabet_size=29
        ),
        api.KeySpec.repeating(length=PERIOD_A + PERIOD_B),
    )
    fixture = build_demo_fixture(cipher, interruptors=REFERENCE_INTERRUPTORS)
    interruptors = api.InterruptorConfig.search(
        INTERRUPTOR_POOL,
        minimum_count=INTERRUPTOR_COUNT,
        maximum_count=INTERRUPTOR_COUNT,
        strategy=api.advanced.InterruptorSearchStrategy.AUTO,
        maximum_combinations=5000,
    )
    solver = api.SolverSpec.two_period_cribs(
        fixed_cribs=FIXED_CRIBS, candidate_words=WORDS_TO_TRY, starts=STARTS, seed=SEED
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
        label="deterministic P13/P31 tutorial fixture",
    )
    report = print_tutorial_session_report(
        title="Two-period cribs: P13/P31 interruptor search",
        cipher="two_period_vigenere",
        solution=result,
        solver_report=result.solver_report,
        reference=reference,
        run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
        stop_policy=TutorialStopPolicy(target_match_ratio=1.0),
    )
    details = result.solver_report.details["two_period_solve"]
    portable_details = result.solver_report.to_json_dict()["details"][
        "two_period_solve"
    ]
    match_ratio = reference.match_ratio(result)
    key_exact = reference.key_exact(result)
    print(f"derived_dimension : {details['derived_dimension']}")
    print(
        "stage_summary : "
        + json.dumps(
            portable_details["stage_summaries"], sort_keys=True, separators=(",", ":")
        )
    )
    winning_interruptors = tuple(details["interruptors"]["winning_positions"])
    print(f"winning_interruptors : {list(winning_interruptors)}")
    print(f"tutorial_elapsed_s : {elapsed_s:.6f}")
    print(f"match_ratio : {match_ratio:.6f}")
    assert details["derived_dimension"] == 14
    assert details["interruptors"]["hypothesis_count"] == 2
    assert winning_interruptors == REFERENCE_INTERRUPTORS
    assert report["benchmark"]["match_ratio"] == 1.0
    assert match_ratio == 1.0
    assert key_exact is True
    return result


if __name__ == "__main__":
    run_tutorial()
