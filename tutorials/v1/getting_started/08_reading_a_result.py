# ruff: noqa: N999
"""Inspect the result and reports from a small search."""

from rdp import api

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
        problem_input=api.RuneInput(value=ciphertext),
        cipher=cipher,
        key_space=api.KeySpec.scalar(minimum=2, maximum=8),
        solver=api.SolverSpec.beam_search(width=8, rounds=None, seed=2718),
        scoring=api.ScoringConfig(
            character_lane_enabled=True,
            wli_lane_enabled=False,
            character_order_weights={1: 0.2, 2: 0.8},
            wli_order_weights={},
        ),
        text_direction=api.TextDirection.LTR,
    )
    result = api.run(request)

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

    # The same information can be rendered through the standard display view.
    api.display.print_result(
        result,
        spec=request,
        options=api.display.SummaryOptions.for_console(),
    )

    exact_recovery = result.key == SECRET_KEY and result.plaintext_indices == PLAINTEXT
    report_agrees = (
        result.solver_report.best_key == result.key
        and result.solver_report.status == result.status
        and result.reproducibility.stop_reason == result.status.stop_reason
    )
    if not exact_recovery or not report_agrees or result.oracle.used_for_ranking:
        raise AssertionError("result evidence did not support the expected claim")


if __name__ == "__main__":
    main()
