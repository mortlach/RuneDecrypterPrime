from __future__ import annotations

"""Pretty-print variant for the Welcome Pilgrim solved-LP tutorial.

The original tutorial wrapper and solved-LP workbook remain unchanged. This
variant imports the workbook contract explicitly and prints the result through
the standard RDP printer facade.
"""

import importlib.util
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
for path in (_ROOT, _SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.api import InterruptorConfig, KeySpec, NormalizedInput, RunSpec, by_name, print_rdp_result, run  # noqa: E402

_SOLVE_SCRIPT = _ROOT / "solving" / "solved_lp" / "02_Welcome_Pilgrim.py"


def _load_workbook():
    spec = importlib.util.spec_from_file_location("rdp_lp_welcome_pilgrim_workbook", _SOLVE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load Welcome Pilgrim workbook module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    workbook = _load_workbook()
    payload = workbook.lp.payload_from_label(workbook.SOURCE_LABEL)
    recipe = workbook.lp.resolve_solve_recipe_label(workbook.RECIPE_LABEL)
    ct_idx = list(payload.ct_idx)
    wli = [list(pair) for pair in payload.wli]
    metadata = payload.metadata
    interruptor_pool = workbook.zero_positions(ct_idx)

    if interruptor_pool != workbook.PINNED_CIPHERTEXT_ZERO_POOL:
        raise ValueError("Loaded Welcome Pilgrim ciphertext-zero pool does not match the pinned solve evidence")

    pool_validation = workbook.validate_interrupter_pool(ct_idx, interruptor_pool)
    if len(workbook.CANONICAL_WELCOME_PILGRIM_IDX) != len(ct_idx):
        raise ValueError("Canonical Welcome Pilgrim reference is not aligned with the loaded source payload")

    scorer_params = {
        "objective": workbook.SCORER_OBJECTIVE,
        "include_char": True,
        "use_word_breaks": True,
        "char_weights": workbook.CHAR_NGRAM_WEIGHTS,
        "wli_weights": workbook.WLI_NGRAM_WEIGHTS,
        "encoding_dir": workbook.ENCODING_DIRECTION,
    }
    display_scorer_params = {
        "objective": str(workbook.SCORER_OBJECTIVE),
        "include_char": True,
        "use_word_breaks": True,
        "encoding_dir": workbook.ENCODING_DIRECTION.value,
        "scorer_variant": str(workbook.SCORER_VARIANT),
    }
    workbook.print_run_config({
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
        "interrupter_pool_zero_validation": pool_validation["interrupter_pool_zero_validation"],
        "encoding_direction": workbook.ENCODING_DIRECTION.value,
        "scorer_variant": workbook.SCORER_VARIANT,
        "solver_variant": workbook.SOLVER_VARIANT,
        "solver_name": workbook.SOLVER.name,
        "solver_params": workbook.solver_params_dict(workbook.SOLVER),
        "acceptance_match_ratio": workbook.ACCEPTANCE_MATCH_RATIO,
    })

    interruptors = InterruptorConfig(
        mode="pool",
        pool=interruptor_pool,
        min_count=workbook.INTERRUPTOR_COUNT,
        max_count=workbook.INTERRUPTOR_COUNT,
        search_strategy="keyops",
    )
    cipher_spec = by_name.cipher("vigenere")
    key_spec = KeySpec.repeat(len=workbook.KEY_LENGTH)
    display_spec = RunSpec(
        problem_input=NormalizedInput(ct_idx=ct_idx, wli=wli),
        cipher=cipher_spec,
        key=key_spec,
        solver=workbook.SOLVER,
        scorer="rune",
        scorer_params=display_scorer_params,
        encoding_dir=workbook.ENCODING_DIRECTION,
        telemetry_on=True,
    )

    started = time.perf_counter()
    result = run(
        text=ct_idx,
        cipher=cipher_spec,
        key=key_spec,
        solver=workbook.SOLVER,
        scorer_params=scorer_params,
        wli_data=wli,
        encoding_dir=workbook.ENCODING_DIRECTION,
        telemetry_on=True,
        interruptors=interruptors,
        return_solver_report=True,
    )
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

    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=workbook.CANONICAL_WELCOME_PILGRIM_IDX,
        tutorial_entry={
            "path": "Tutorial_LP_Welcome_Pilgrim_Solve_PrettyPrint.py",
            "title": "Liber Primus Welcome Pilgrim pretty-print variant",
            "gate": "v1_release_pretty_print",
            "acceptance_kind": "min_match_ratio",
            "min_match_ratio": 1.0,
            "uses_oracle_stop_score": False,
        },
        lp_evidence={
            "source_label": workbook.SOURCE_LABEL,
            "resolved_source_label": metadata["source_label"],
            "recipe": recipe.recipe_label,
            "cipher_family": recipe.cipher_family,
            "solver_variant": workbook.SOLVER_VARIANT,
            "scorer_variant": workbook.SCORER_VARIANT,
        },
    )

    status = str(best_attempt.get("status"))
    return 0 if status == "solved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
