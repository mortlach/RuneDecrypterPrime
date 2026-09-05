# ruff: noqa: N999
"""Read a RunResult without confusing completion with correctness.

The earlier stops inspect selected fields.  This one names the main result
sections and the different questions they answer after a small exact search.
"""

from rdp import api

# Known truth is present so this example can assess recovery after the run.  It
# is not included in the RunSpec and therefore cannot affect candidate ranking.
# fmt: off
PLAINTEXT = (
    2, 18, 4, 18, 7, 24, 15, 24, 16, 24, 17, 20, 18, 15,
    18, 16, 3, 1, 16, 1, 9, 23, 18, 4, 24, 16, 4, 18,
    18,
)
# fmt: on
SECRET_KEY: api.ConcreteKey = (7,)


def main() -> None:
    cipher = api.CipherSpec.rail_fence(minimum_rails=2, maximum_rails=8)
    ciphertext = api.encrypt(PLAINTEXT, cipher=cipher, key=SECRET_KEY)
    request = api.RunSpec(
        problem_input=api.RuneIndexInput(indices=ciphertext),
        cipher=cipher,
        key_space=api.KeySpec.scalar(minimum=2, maximum=8),
        solver=api.SolverSpec.beam_search(width=8, rounds=0, seed=2718),
        scoring=api.ScoringConfig(
            character_lane_enabled=True,
            word_length_lane_enabled=False,
            character_order_weights={1: 0.2, 2: 0.8},
            word_length_order_weights={},
        ),
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
    )
    result = api.run(request)

    # RunResult keeps several kinds of evidence separate:
    # - key/plaintext/score: the best candidate found;
    # - status: how and why execution stopped;
    # - solver_report: work performed by the solver;
    # - configuration: requested and effective component settings;
    # - reproducibility: seed, backend, device and version context;
    # - oracle: whether known truth influenced scoring, ranking or stopping.
    # For a formatted overview, api.display.print_result(result) is available.
    # Its SummaryOptions.for_debug() preset includes more diagnostic detail;
    # start with the fields below when you only need the answer and its cost.
    print("Reading a result")
    print("Best key       :", result.key)
    print("Best score     :", result.score)
    print("Execution      :", result.status.execution_status.value)
    print("Stop category  :", result.status.stop_category.value)
    print("Stop reason    :", result.status.stop_reason.value)
    print("Solver         :", result.solver_report.solver.value)
    print("Evaluations    :", result.solver_report.evaluations)
    print("Requested seed :", result.reproducibility.requested_seed)
    print("Effective seed :", result.reproducibility.effective_seed)
    print("Oracle ranking :", result.oracle.used_for_ranking)

    exact_recovery = result.key == SECRET_KEY and result.plaintext == PLAINTEXT
    report_agrees = (
        result.solver_report.best_key == result.key
        and result.solver_report.status == result.status
        and result.reproducibility.stop_reason == result.status.stop_reason
    )
    if not exact_recovery or not report_agrees or result.oracle.used_for_ranking:
        raise AssertionError("result evidence did not support the expected claim")


if __name__ == "__main__":
    main()
