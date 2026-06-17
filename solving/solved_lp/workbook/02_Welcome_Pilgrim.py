from __future__ import annotations

"""Evidence-producing worked solve for the LP section "Welcome Pilgrim".

This file is intentionally self-contained. It loads the real LP source by
label, searches a period-8 Vigenere key with exactly 11 interrupters selected
from ciphertext-zero positions, validates against the canonical solved text,
prints structured evidence blocks, and writes a local JSON evidence file.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.api import Direction, InterruptorConfig, KeySpec, SolverSpec, by_name, run  # noqa: E402
from rune_decrypter_prime.data import liber_primus as lp  # noqa: E402
from rune_decrypter_prime.utils.solve_output import (  # noqa: E402
    collect_solver_attempt,
    configure_utf8_stdio,
    print_block,
    print_final_result,
    print_kv,
    safe_public_dict,
    write_latest_evidence,
    zero_positions,
)

from solving.solved_lp.welcome_pilgrim.reference import CANONICAL_WELCOME_PILGRIM_IDX  # noqa: E402

configure_utf8_stdio()


SOURCE_LABEL = "welcome_pilgrim"
RECIPE_LABEL = "recipe.welcome_pilgrim.vigenere_interruptors"
KEY_TEXT_HINT = "DIVINITY"
KEY_LENGTH = len(KEY_TEXT_HINT)
INTERRUPTOR_COUNT = 11
ENCODING_DIRECTION = Direction.LTR
SCORER_OBJECTIVE = "pct.logp.win10"
SCORER_VARIANT = SCORER_OBJECTIVE
CHAR_NGRAM_WEIGHTS = {1: 0.3, 2: 0.7}
WLI_NGRAM_WEIGHTS = {1: 0.3, 2: 0.7}
ACCEPTANCE_MATCH_RATIO = 1.0
EVIDENCE_DIR = ROOT / "output" / "solved_lp" / SOURCE_LABEL
PINNED_CIPHERTEXT_ZERO_POOL = [
    5, 14, 47, 48, 74, 84, 132, 144, 152, 159, 160, 165, 219,
    250, 317, 331, 398, 421, 423, 443, 465, 470, 499, 505, 514,
]

SOLVER_VARIANT = "beam_64"
SOLVER = SolverSpec.beam(
    beam_width=64,
    expand_mode="sweep",
    plateau_rounds=5,
    plateau_min_delta=1e-4,
    progress_pct=10,
    seed=2026,
)


def validate_interrupter_pool(ct_idx: list[int], pool: list[int]) -> dict[str, object]:
    expected = zero_positions(ct_idx)
    return {
        "ciphertext_zero_positions": expected,
        "ciphertext_zero_count": len(expected),
        "interrupter_pool_zero_validation": all(int(ct_idx[index]) == 0 for index in pool),
        "interrupter_pool_equals_ciphertext_zero_positions": pool == expected,
    }


def expected_ecdf_assets() -> list[str]:
    direction = ENCODING_DIRECTION.value
    assets: list[str] = []
    for n in sorted(CHAR_NGRAM_WEIGHTS):
        assets.append(f"ecdf/char/{direction}/{direction}_nose_char_n{n}_win10_logp.npz")
    for n in sorted(WLI_NGRAM_WEIGHTS):
        assets.append(f"ecdf/wli/{direction}/{direction}_nose_wli_n{n}_win10_logp.npz")
    return assets


def solver_params_dict(solver: SolverSpec) -> dict[str, object]:
    data = dict(solver.params)
    if solver.seed is not None:
        data["seed"] = int(solver.seed)
    return data


def collect_result_diagnostics(
    *,
    result: object,
    attempt_index: int,
    solver_variant: str,
    scorer_variant: str,
    solver: SolverSpec,
    key_length: int,
    interruptor_pool: list[int],
    interruptor_count: int,
    reference_idx: tuple[int, ...],
    ciphertext_length: int,
    wli: list[list[int]],
    elapsed_wall_time_s: float,
) -> dict[str, object]:
    record = collect_solver_attempt(
        result=result,
        solver_variant=solver_variant,
        scorer_variant=scorer_variant,
        key_length=key_length,
        interruptor_pool=interruptor_pool,
        interruptor_count=interruptor_count,
        reference_idx=reference_idx,
        ciphertext_length=ciphertext_length,
        wli=wli,
        elapsed_wall_time_s=elapsed_wall_time_s,
        acceptance_match_ratio=ACCEPTANCE_MATCH_RATIO,
    )
    found_key_core = list(record.get("found_key_core") or [])
    found_interruptors = list(record.get("found_interruptors") or [])
    extra_non_pool = [value for value in found_interruptors if value not in interruptor_pool]
    missing_pool = [value for value in interruptor_pool if value not in found_interruptors]

    record.update({
        "attempt_index": attempt_index,
        "solver_name": solver.name,
        "solver_params": solver_params_dict(solver),
        "found_key_core_len": len(found_key_core),
        "found_key_core_as_runes_or_latin_if_available": KEY_TEXT_HINT if found_key_core == [23, 10, 1, 10, 9, 10, 16, 26] else None,
        "found_interruptors_sorted": found_interruptors == sorted(found_interruptors),
        "found_interruptors_unique": len(found_interruptors) == len(set(found_interruptors)),
        "found_interrupter_count_matches_required": len(found_interruptors) == interruptor_count,
        "missing_pool_positions": missing_pool,
        "extra_non_pool_positions": extra_non_pool,
        "error_type": None,
        "error_message": None,
        "solver_report_fields": [name for name in safe_public_dict(getattr(result, "solver_report", None)).keys()],
    })
    return record


def print_run_config(config: dict[str, object]) -> None:
    print_block("LP_WELCOME_PILGRIM_RUN_CONFIG", config)


def print_attempt_summary(record: dict[str, object]) -> None:
    print("\nLP_WELCOME_PILGRIM_ATTEMPT_SUMMARY_BEGIN")
    for key in (
        "attempt_index",
        "solver_variant",
        "scorer_variant",
        "solver_name",
        "solver_params",
        "found_key_core",
        "found_key_core_len",
        "found_key_core_as_runes_or_latin_if_available",
        "found_interruptors",
        "found_interrupter_count",
        "found_interruptors_in_pool",
        "missing_pool_positions",
        "extra_non_pool_positions",
        "best_score",
        "stop_reason",
        "match_ratio",
        "plaintext_idx_length",
        "score_time_s",
        "decrypt_time_s",
        "tokens",
        "evals_or_candidates",
        "elapsed_wall_time_s",
        "status",
        "error_type",
        "error_message",
    ):
        print_kv(key, record.get(key))
    print("LP_WELCOME_PILGRIM_ATTEMPT_SUMMARY_END")


def print_best_variant(record: dict[str, object]) -> None:
    print("\nBEST_SOLVER_VARIANT_BEGIN")
    for key in (
        "solver_variant",
        "scorer_variant",
        "solver_name",
        "solver_params",
        "found_key_core",
        "found_interruptors",
        "best_score",
        "stop_reason",
        "match_ratio",
        "score_time_s",
        "decrypt_time_s",
        "tokens",
        "evals_or_candidates",
        "elapsed_wall_time_s",
        "status",
    ):
        print_kv(key, record.get(key))
    print("BEST_SOLVER_VARIANT_END")


def print_found_interrupter_detail(
    *,
    found_interruptors: list[int],
    ct_idx: list[int],
    reference_idx: tuple[int, ...],
    wli: list[list[int]],
) -> None:
    print("\nFOUND_INTERRUPTERS_DETAIL_BEGIN")
    print("index\tct_idx\tcanonical_pt_idx\twli_pair")
    for index in found_interruptors:
        canonical = reference_idx[index] if 0 <= index < len(reference_idx) else None
        pair = wli[index] if 0 <= index < len(wli) else None
        print(f"{index}\t{ct_idx[index] if 0 <= index < len(ct_idx) else None}\t{canonical}\t{pair}")
    print("FOUND_INTERRUPTERS_DETAIL_END")


def print_score_separation() -> dict[str, object]:
    data = {
        "score_separation_status": "unavailable",
        "score_separation_reason": "the workbook uses the API run scorer internally; no stable public single-plaintext scorer object is exposed here",
    }
    print("\nSCORE_SEPARATION_BEGIN")
    for key, value in data.items():
        print_kv(key, value)
    print("SCORE_SEPARATION_END")
    return data


def main() -> int:
    payload = lp.payload_from_label(SOURCE_LABEL)
    recipe = lp.resolve_solve_recipe_label(RECIPE_LABEL)
    ct_idx = list(payload.ct_idx)
    wli = [list(pair) for pair in payload.wli]
    metadata = payload.metadata
    interruptor_pool = zero_positions(ct_idx)
    if interruptor_pool != PINNED_CIPHERTEXT_ZERO_POOL:
        raise ValueError(
            "Loaded Welcome Pilgrim ciphertext-zero pool does not match the pinned solve evidence: "
            f"loaded={interruptor_pool} pinned={PINNED_CIPHERTEXT_ZERO_POOL}"
        )
    pool_validation = validate_interrupter_pool(ct_idx, interruptor_pool)

    if len(CANONICAL_WELCOME_PILGRIM_IDX) != len(ct_idx):
        raise ValueError(
            "Canonical Welcome Pilgrim reference is not aligned with the loaded source payload: "
            f"canonical={len(CANONICAL_WELCOME_PILGRIM_IDX)} ct={len(ct_idx)}"
        )

    scorer_params = {
        "objective": SCORER_OBJECTIVE,
        "include_char": True,
        "use_word_breaks": True,
        "char_weights": CHAR_NGRAM_WEIGHTS,
        "wli_weights": WLI_NGRAM_WEIGHTS,
        "encoding_dir": ENCODING_DIRECTION,
    }
    run_config = {
        "source_label": SOURCE_LABEL,
        "resolved_source_label": metadata["source_label"],
        "display_name": metadata["display_name"],
        "main_page_start": metadata["main_page_start"],
        "main_page_end": metadata["main_page_end"],
        "bound_book_start": metadata["bound_book_start"],
        "bound_book_end": metadata["bound_book_end"],
        "ciphertext_length": len(ct_idx),
        "wli_length": len(wli),
        "recipe_label": recipe.recipe_label,
        "cipher_family": recipe.cipher_family,
        "key_text_hint": KEY_TEXT_HINT,
        "key_length": KEY_LENGTH,
        "interrupter_count_required": INTERRUPTOR_COUNT,
        "interrupter_pool_strategy": "ciphertext_zero_positions",
        "interrupter_pool_size": len(interruptor_pool),
        "interrupter_pool": interruptor_pool,
        "ciphertext_zero_positions": pool_validation["ciphertext_zero_positions"],
        "ciphertext_zero_count": pool_validation["ciphertext_zero_count"],
        "interrupter_pool_zero_validation": pool_validation["interrupter_pool_zero_validation"],
        "interrupter_pool_equals_ciphertext_zero_positions": pool_validation[
            "interrupter_pool_equals_ciphertext_zero_positions"
        ],
        "encoding_direction": ENCODING_DIRECTION.value,
        "scorer_variant": SCORER_VARIANT,
        "objective": SCORER_OBJECTIVE,
        "include_char": True,
        "use_word_breaks": True,
        "char_weights": CHAR_NGRAM_WEIGHTS,
        "wli_weights": WLI_NGRAM_WEIGHTS,
        "ecdf_assets_expected": expected_ecdf_assets(),
        "solver_variant": SOLVER_VARIANT,
        "solver_name": SOLVER.name,
        "solver_params": solver_params_dict(SOLVER),
        "seed": SOLVER.seed,
        "acceptance_match_ratio": ACCEPTANCE_MATCH_RATIO,
    }
    print_run_config(run_config)

    interruptors = InterruptorConfig(
        mode="pool",
        pool=interruptor_pool,
        min_count=INTERRUPTOR_COUNT,
        max_count=INTERRUPTOR_COUNT,
        search_strategy="keyops",
    )

    started = time.perf_counter()
    result = run(
        text=ct_idx,
        cipher=by_name.cipher("vigenere"),
        key=KeySpec.repeat(len=KEY_LENGTH),
        solver=SOLVER,
        scorer_params=scorer_params,
        wli_data=wli,
        encoding_dir=ENCODING_DIRECTION,
        telemetry_on=True,
        interruptors=interruptors,
        return_solver_report=True,
    )
    elapsed = time.perf_counter() - started
    best_attempt = collect_result_diagnostics(
        result=result,
        attempt_index=1,
        solver_variant=SOLVER_VARIANT,
        scorer_variant=SCORER_VARIANT,
        solver=SOLVER,
        key_length=KEY_LENGTH,
        interruptor_pool=interruptor_pool,
        interruptor_count=INTERRUPTOR_COUNT,
        reference_idx=CANONICAL_WELCOME_PILGRIM_IDX,
        ciphertext_length=len(ct_idx),
        wli=wli,
        elapsed_wall_time_s=elapsed,
    )
    attempt_records = [best_attempt]
    print_attempt_summary(best_attempt)
    print_best_variant(best_attempt)
    print_found_interrupter_detail(
        found_interruptors=list(best_attempt.get("found_interruptors") or []),
        ct_idx=ct_idx,
        reference_idx=CANONICAL_WELCOME_PILGRIM_IDX,
        wli=wli,
    )
    score_separation = print_score_separation()

    plaintext_latin = str(best_attempt.get("plaintext_latin") or "")
    plaintext_runes = str(best_attempt.get("plaintext_runes") or "")
    status = str(best_attempt.get("status"))
    notes = (
        "exact solved reference match using beam_64, LTR char/WLI n1+n2 ECDF scoring, "
        "and 11 interrupters from the ciphertext-zero pool"
        if status == "solved"
        else "diagnostic_not_yet_solved; acceptance checks did not all pass"
    )

    print_final_result(
        block_name="LP_WELCOME_PILGRIM_FINAL_RESULT",
        source_label=SOURCE_LABEL,
        resolved_source_label=metadata["source_label"],
        main_page_start=metadata["main_page_start"],
        main_page_end=metadata["main_page_end"],
        ciphertext_length=len(ct_idx),
        wli_length=len(wli),
        recipe=recipe.recipe_label,
        cipher_family=recipe.cipher_family,
        method="beam_64_period_8_vigenere_interruptor_search",
        key_or_params={"key_text_hint": KEY_TEXT_HINT, "key_length": KEY_LENGTH},
        match_ratio=float(best_attempt.get("match_ratio") or 0.0),
        status=status,
        acceptance_rule="match_ratio >= 1.000 and 11 interrupters in pool and plaintext length equals ciphertext length",
        plaintext_latin=plaintext_latin,
        plaintext_runes=plaintext_runes,
        extra_fields={
            "solver_variant": best_attempt.get("solver_variant"),
            "scorer_variant": SCORER_VARIANT,
            "found_key_core": best_attempt.get("found_key_core"),
            "found_interruptors": best_attempt.get("found_interruptors"),
            "found_interruptors_sorted": best_attempt.get("found_interruptors_sorted"),
            "found_interruptors_unique": best_attempt.get("found_interruptors_unique"),
            "found_interruptors_in_pool": best_attempt.get("found_interruptors_in_pool"),
            "found_interrupter_count": best_attempt.get("found_interrupter_count"),
            "found_interrupter_count_matches_required": best_attempt.get("found_interrupter_count_matches_required"),
            "interrupter_pool_size": len(interruptor_pool),
            "interrupter_pool": interruptor_pool,
            "ciphertext_zero_positions": pool_validation["ciphertext_zero_positions"],
            "ciphertext_zero_count": pool_validation["ciphertext_zero_count"],
            "interrupter_pool_zero_validation": pool_validation["interrupter_pool_zero_validation"],
            "interrupter_pool_equals_ciphertext_zero_positions": pool_validation[
                "interrupter_pool_equals_ciphertext_zero_positions"
            ],
            "best_score": best_attempt.get("best_score"),
            "stop_reason": best_attempt.get("stop_reason"),
            "plaintext_idx_length": best_attempt.get("plaintext_idx_length"),
            "score_time_s": best_attempt.get("score_time_s"),
            "decrypt_time_s": best_attempt.get("decrypt_time_s"),
            "tokens": best_attempt.get("tokens"),
            "evals_or_candidates": best_attempt.get("evals_or_candidates"),
            "elapsed_wall_time_s": best_attempt.get("elapsed_wall_time_s"),
            "notes": notes,
        },
    )

    final = {
        "status": status,
        "match_ratio": best_attempt.get("match_ratio"),
        "found_key_core": best_attempt.get("found_key_core"),
        "found_interruptors": best_attempt.get("found_interruptors"),
        "notes": notes,
    }
    evidence = {
        "source_label": SOURCE_LABEL,
        "resolved_source_label": metadata["source_label"],
        "recipe": recipe.recipe_label,
        "cipher_family": recipe.cipher_family,
        "run_config": run_config,
        "attempts": attempt_records,
        "best_attempt": best_attempt,
        "score_separation": score_separation,
        "final": final,
    }
    latest_path, stamped_path = write_latest_evidence(EVIDENCE_DIR, evidence)
    print("json_evidence_latest:", latest_path.relative_to(ROOT))
    print("json_evidence_timestamped:", stamped_path.relative_to(ROOT) if stamped_path is not None else None)

    return 0 if status == "solved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
