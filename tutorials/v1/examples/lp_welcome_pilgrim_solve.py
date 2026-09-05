"""Lp welcome pilgrim solve.

See the example catalogue for assets, runtime and reference use.
"""

from __future__ import annotations

import time
from importlib import import_module

from rdp import api
from tutorials.v1.support import tutorial_pretty as pretty
from tutorials.v1.support.tutorial_output import print_tutorial_debug_preview


def _load_workbook():
    """Reuse the maintained solved-source workbook and its acceptance rules."""
    return import_module("solving.solved_lp.02_Welcome_Pilgrim")


def main() -> int:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Liber Primus Welcome Pilgrim label solve",
        cipher="liber primus label solve",
        solver="beam",
        direction="rtl",
        expected_result="exact solve",
        uses_reference_stop_score=False,
    )
    workbook = _load_workbook()
    payload = workbook.lp.payload_from_label(workbook.SOURCE_LABEL)
    recipe = workbook.lp.resolve_solve_recipe_label(workbook.RECIPE_LABEL)
    ct_idx = list(payload.ct_idx)
    wli = [list(pair) for pair in payload.wli]
    metadata = payload.metadata
    interruptor_pool = workbook.zero_positions(ct_idx)
    if interruptor_pool != workbook.PINNED_CIPHERTEXT_ZERO_POOL:
        raise ValueError(
            "Loaded Welcome Pilgrim ciphertext-zero pool does not match the pinned solve evidence"
        )
    pool_validation = workbook.validate_interrupter_pool(ct_idx, interruptor_pool)
    if len(workbook.CANONICAL_WELCOME_PILGRIM_IDX) != len(ct_idx):
        raise ValueError(
            "Canonical Welcome Pilgrim reference is not aligned with the loaded source payload"
        )
    scorer_params = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights=workbook.CHAR_NGRAM_WEIGHTS,
        word_length_order_weights=workbook.WLI_NGRAM_WEIGHTS,
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )
    workbook.print_run_config(
        {
            "source_label": workbook.SOURCE_LABEL,
            "resolved_source_label": metadata["source_label"],
            "display_name": metadata["display_name"],
            "recipe_label": recipe.recipe_label,
            "cipher_family": recipe.cipher_family,
            "ciphertext_length": len(ct_idx),
            "wli_length": len(wli),
            "key_text_hint": workbook.KEY_TEXT_HINT,
            "key_length": workbook.KEY_LENGTH,
            "interrupter_count_required": workbook.INTERRUPTOR_COUNT,
            "interrupter_pool_strategy": "ciphertext_zero_positions",
            "interrupter_pool_size": len(interruptor_pool),
            "interrupter_pool_zero_validation": pool_validation[
                "interrupter_pool_zero_validation"
            ],
            "encoding_direction": workbook.ENCODING_DIRECTION.value,
            "scorer_variant": workbook.SCORER_VARIANT,
            "solver_variant": workbook.SOLVER_VARIANT,
            "solver_name": workbook.SOLVER.kind.value,
            "solver_params": workbook.solver_params_dict(workbook.SOLVER),
            "acceptance_match_ratio": workbook.ACCEPTANCE_MATCH_RATIO,
        }
    )
    print_tutorial_debug_preview(
        label="reference_plaintext",
        idx=workbook.CANONICAL_WELCOME_PILGRIM_IDX,
        wli=wli,
        direction=workbook.ENCODING_DIRECTION,
    )
    print_tutorial_debug_preview(
        label="ciphertext", idx=ct_idx, wli=wli, direction=workbook.ENCODING_DIRECTION
    )
    interruptors = api.InterruptorConfig.search(
        interruptor_pool,
        minimum_count=workbook.INTERRUPTOR_COUNT,
        maximum_count=workbook.INTERRUPTOR_COUNT,
        strategy=api.advanced.InterruptorSearchStrategy.KEY_OPERATIONS,
        maximum_combinations=5000,
    )
    cipher_spec = api.CipherSpec.vigenere(alphabet_size=29)
    key_spec = api.KeySpec.repeating(length=workbook.KEY_LENGTH)
    started = time.perf_counter()
    request = api.RunSpec(
        problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli),
        cipher=cipher_spec,
        key_space=key_spec,
        solver=workbook.SOLVER,
        scoring=scorer_params,
        telemetry_enabled=True,
        text_direction=workbook.ENCODING_DIRECTION,
        interruptors=interruptors,
    )
    result = api.run(request)
    elapsed = time.perf_counter() - started
    best_attempt = workbook.collect_result_diagnostics(
        result=result,
        attempt_index=1,
        solver_variant=workbook.SOLVER_VARIANT,
        scorer_variant=workbook.SCORER_VARIANT,
        solver=workbook.SOLVER,
        key_length=workbook.KEY_LENGTH,
        interruptor_pool=interruptor_pool,
        interruptor_count=workbook.INTERRUPTOR_COUNT,
        reference_idx=workbook.CANONICAL_WELCOME_PILGRIM_IDX,
        ciphertext_length=len(ct_idx),
        wli=wli,
        elapsed_wall_time_s=elapsed,
    )
    workbook.print_attempt_summary(best_attempt)
    workbook.print_best_variant(best_attempt)
    pretty.print_summary_spacer()
    api.display.print_result(
        result, spec=request, options=api.display.SummaryOptions.for_tutorial()
    )
    status = str(best_attempt.get("status"))
    return 0 if status == "solved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
