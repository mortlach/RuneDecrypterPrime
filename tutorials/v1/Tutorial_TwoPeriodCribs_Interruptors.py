from __future__ import annotations

"""Fast P13/P31 walkthrough with structural interruptor pool search."""

import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rdp import api  # noqa: E402
from rune_decrypter_prime.utils.tutorial_benchmark import (  # noqa: E402
    TutorialRunKind,
    TutorialStopPolicy,
)
from rune_decrypter_prime.utils.tutorial_reference import TutorialReference  # noqa: E402
from rune_decrypter_prime.utils.tutorial_session_report import (  # noqa: E402
    print_tutorial_session_report,
)
from rune_decrypter_prime.utils import tutorial_pretty as pretty  # noqa: E402

from data.two_period_cribs_demo import build_demo_fixture  # noqa: E402


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
    cipher, key = api.by_name.cipher_with_key(
        "two_period_vigenere",
        period_a=PERIOD_A,
        period_b=PERIOD_B,
        alphabet_size=29,
        default_key=True,
    )
    fixture = build_demo_fixture(cipher, interruptors=REFERENCE_INTERRUPTORS)
    solver = api.SolverSpec.two_period_cribs(
        fixed_cribs=FIXED_CRIBS,
        starts=STARTS,
        seed=SEED,
    )
    interruptors = api.InterruptorConfig(
        mode="pool",
        pool=INTERRUPTOR_POOL,
        min_count=INTERRUPTOR_COUNT,
        max_count=INTERRUPTOR_COUNT,
    )

    started = perf_counter()
    result = api.run(
        text=(fixture.ciphertext, fixture.wli),
        cipher=cipher,
        key=key,
        solver=solver,
        interruptors=interruptors,
        encoding_dir=api.Direction.LTR,
        return_solver_report=True,
    )
    elapsed_s = perf_counter() - started

    pretty.print_summary_spacer()
    api.print_rdp_result(result)
    reference = TutorialReference.key_and_plaintext(
        key_idx=fixture.reference_key,
        plaintext_idx=fixture.reference_plaintext,
        label="deterministic interruptor tutorial fixture",
    )
    report = print_tutorial_session_report(
        title="Two-period cribs: structural interruptor pool",
        cipher="two_period_vigenere",
        solution=result.solution,
        solver_report=result.solver_report,
        reference=reference,
        run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
        stop_policy=TutorialStopPolicy(target_match_ratio=1.0),
    )
    details = result.solver_report.details["two_period_solve"]
    match_ratio = reference.match_ratio(result.solution)
    key_exact = reference.key_exact(result.solution)
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
