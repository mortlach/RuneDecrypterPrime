from __future__ import annotations

"""Evidence-producing bounded attempt for the LP koan "During a Lesson".

This mirrors the Welcome Pilgrim solve shape: load the LP source by label, use
period-13 Vigenere, search only ciphertext-zero positions as interrupter
candidates, run one beam_64 solve, and print honest evidence.
"""

import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.api import Direction, InterruptorConfig, KeySpec, SolverSpec, by_name, run  # noqa: E402
from rune_decrypter_prime.data import liber_primus as lp  # noqa: E402
from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402


SOURCE_LABEL = "koan_during_lesson"
RECIPE_LABEL = "recipe.koan_during_lesson.vigenere_interruptors"
KEY_TEXT_HINT = "CIRCUMFERENCE"
KEY_LENGTH = len(KEY_TEXT_HINT)
INTERRUPTOR_COUNT = 11
ENCODING_DIRECTION = Direction.LTR
SCORER_OBJECTIVE = "pct.logp.win10"
SCORER_VARIANT = SCORER_OBJECTIVE
CHAR_NGRAM_WEIGHTS = {1: 0.3, 2: 0.7}
WLI_NGRAM_WEIGHTS = {1: 0.3, 2: 0.7}
ACCEPTANCE_MATCH_RATIO = 1.0
EVIDENCE_DIR = ROOT / "output" / "solved_lp" / SOURCE_LABEL
SOLVER_VARIANT = "beam_64"
SOLVER = SolverSpec.beam(
    beam_width=64,
    expand_mode="sweep",
    plateau_rounds=5,
    plateau_min_delta=1e-4,
    progress_pct=10,
    seed=2026,
)


def as_int_list(values: object) -> list[int]:
    if values is None:
        return []
    if hasattr(values, "tolist"):
        values = values.tolist()
    return [int(value) for value in list(values)]


def zero_positions(ct_idx: list[int]) -> list[int]:
    return [index for index, value in enumerate(ct_idx) if int(value) == 0]


def split_found_key(found_key: object) -> tuple[list[int], list[int]]:
    values = as_int_list(found_key)
    return values[:KEY_LENGTH], [value for value in values[KEY_LENGTH:] if value >= 0]


def render_solution(solution: object, wli: list[list[int]]) -> tuple[list[int], str, str]:
    plaintext_idx = as_int_list(getattr(solution, "plaintext_idx", []))
    plaintext_latin = str(getattr(solution, "plaintext_latin", "") or "")
    plaintext_runes = str(getattr(solution, "plaintext_rune", "") or "")
    if plaintext_idx and not plaintext_latin:
        plaintext_latin = Runeglish.to_rune_latin(plaintext_idx, wli)
    if plaintext_idx and not plaintext_runes:
        plaintext_runes = Runeglish.to_rune(plaintext_idx, wli)
    return plaintext_idx, plaintext_latin, plaintext_runes


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}")


def main() -> int:
    payload = lp.payload_from_label(SOURCE_LABEL)
    recipe = lp.resolve_solve_recipe_label(RECIPE_LABEL)
    ct_idx = list(payload.ct_idx)
    wli = [list(pair) for pair in payload.wli]
    metadata = payload.metadata
    interruptor_pool = zero_positions(ct_idx)
    pool_zero_validation = all(int(ct_idx[index]) == 0 for index in interruptor_pool)
    pool_has_required_count = len(interruptor_pool) >= INTERRUPTOR_COUNT

    scorer_params = {
        "objective": SCORER_OBJECTIVE,
        "include_char": True,
        "use_word_breaks": True,
        "char_weights": CHAR_NGRAM_WEIGHTS,
        "wli_weights": WLI_NGRAM_WEIGHTS,
        "encoding_dir": ENCODING_DIRECTION,
    }
    print("\nLP_KOAN_DURING_LESSON_RUN_CONFIG_BEGIN")
    for key, value in (
        ("source_label", SOURCE_LABEL),
        ("resolved_source_label", metadata["source_label"]),
        ("main_page_start", metadata["main_page_start"]),
        ("main_page_end", metadata["main_page_end"]),
        ("ciphertext_length", len(ct_idx)),
        ("wli_length", len(wli)),
        ("recipe", recipe.recipe_label),
        ("cipher_family", recipe.cipher_family),
        ("key_text_hint", KEY_TEXT_HINT),
        ("key_length", KEY_LENGTH),
        ("interrupter_count_required", INTERRUPTOR_COUNT),
        ("interrupter_pool_strategy", "ciphertext_zero_positions"),
        ("interrupter_pool_size", len(interruptor_pool)),
        ("interrupter_pool", interruptor_pool),
        ("interrupter_pool_zero_validation", pool_zero_validation),
        ("interrupter_pool_has_required_count", pool_has_required_count),
        ("encoding_direction", ENCODING_DIRECTION.value),
        ("scorer_variant", SCORER_VARIANT),
        ("objective", SCORER_OBJECTIVE),
        ("include_char", True),
        ("use_word_breaks", True),
        ("char_weights", CHAR_NGRAM_WEIGHTS),
        ("wli_weights", WLI_NGRAM_WEIGHTS),
        ("solver_variant", SOLVER_VARIANT),
        ("solver_name", SOLVER.name),
        ("solver_params", {**SOLVER.params, "seed": SOLVER.seed}),
        ("acceptance_match_ratio", ACCEPTANCE_MATCH_RATIO),
        ("evidence_dir", EVIDENCE_DIR.relative_to(ROOT)),
    ):
        print_kv(key, value)
    print("LP_KOAN_DURING_LESSON_RUN_CONFIG_END")

    solution = None
    report = None
    plaintext_idx: list[int] = []
    plaintext_latin = ""
    plaintext_runes = ""
    found_key_core: list[int] = []
    found_interruptors: list[int] = []
    found_interruptors_in_pool = False
    found_key_matches_hint = False
    elapsed_wall_time_s = 0.0
    error_type = None
    error_message = None
    if pool_has_required_count:
        started = time.perf_counter()
        try:
            result = run(
                text=ct_idx,
                cipher=by_name.cipher("vigenere"),
                key=KeySpec.repeat(len=KEY_LENGTH),
                solver=SOLVER,
                scorer_params=scorer_params,
                wli_data=wli,
                encoding_dir=ENCODING_DIRECTION,
                telemetry_on=True,
                interruptors=InterruptorConfig(
                    mode="pool",
                    pool=interruptor_pool,
                    min_count=INTERRUPTOR_COUNT,
                    max_count=INTERRUPTOR_COUNT,
                    search_strategy="keyops",
                ),
                return_solver_report=True,
            )
            elapsed_wall_time_s = time.perf_counter() - started
            solution = result.solution
            report = result.solver_report
            plaintext_idx, plaintext_latin, plaintext_runes = render_solution(solution, wli)
            found_key_core, found_interruptors = split_found_key(getattr(solution, "key", []))
            found_interruptors_in_pool = all(value in interruptor_pool for value in found_interruptors)
            found_key_matches_hint = found_key_core == [2, 10, 18, 2, 20, 12, 5, 4, 18, 4, 13, 2, 4]
        except Exception as exc:
            elapsed_wall_time_s = time.perf_counter() - started
            error_type = type(exc).__name__
            error_message = str(exc)
    else:
        error_type = "PoolTooSmall"
        error_message = (
            f"loaded ciphertext-zero pool has {len(interruptor_pool)} positions; "
            f"configured interrupter count is {INTERRUPTOR_COUNT}"
        )
    status = "diagnostic_not_yet_solved"

    print("\nLP_KOAN_DURING_LESSON_ATTEMPT_SUMMARY_BEGIN")
    for key, value in (
        ("solver_variant", SOLVER_VARIANT),
        ("scorer_variant", SCORER_VARIANT),
        ("solver_name", SOLVER.name),
        ("solver_params", {**SOLVER.params, "seed": SOLVER.seed}),
        ("found_key_core", found_key_core),
        ("found_key_core_len", len(found_key_core)),
        ("found_key_text_hint_match", found_key_matches_hint),
        ("found_interruptors", found_interruptors),
        ("found_interrupter_count", len(found_interruptors)),
        ("found_interruptors_in_pool", found_interruptors_in_pool),
        ("best_score", getattr(solution, "score", None) if solution is not None else None),
        ("stop_reason", getattr(solution, "stop_reason", getattr(report, "stop_reason", None)) if solution is not None else None),
        ("match_ratio", None),
        ("plaintext_idx_length", len(plaintext_idx)),
        ("score_time_s", getattr(report, "score_time_s", None) if report is not None else None),
        ("decrypt_time_s", getattr(report, "decrypt_time_s", None) if report is not None else None),
        ("tokens", getattr(report, "tokens_processed", None) if report is not None else None),
        ("evals_or_candidates", getattr(report, "evals", None) if report is not None else None),
        ("elapsed_wall_time_s", elapsed_wall_time_s),
        ("status", status),
        ("error_type", error_type),
        ("error_message", error_message),
    ):
        print_kv(key, value)
    print("LP_KOAN_DURING_LESSON_ATTEMPT_SUMMARY_END")

    print("\nLP_KOAN_DURING_LESSON_FINAL_RESULT_BEGIN")
    for key, value in (
        ("source_label", SOURCE_LABEL),
        ("resolved_source_label", metadata["source_label"]),
        ("main_page_start", metadata["main_page_start"]),
        ("main_page_end", metadata["main_page_end"]),
        ("recipe", recipe.recipe_label),
        ("cipher_family", recipe.cipher_family),
        ("key_text_hint", KEY_TEXT_HINT),
        ("key_length", KEY_LENGTH),
        ("interrupter_pool_size", len(interruptor_pool)),
        ("interrupter_pool", interruptor_pool),
        ("interrupter_count_required", INTERRUPTOR_COUNT),
        ("interrupter_pool_has_required_count", pool_has_required_count),
        ("solver_variant", SOLVER_VARIANT),
        ("scorer_variant", SCORER_VARIANT),
        ("found_key_core", found_key_core),
        ("found_key_core_len", len(found_key_core)),
        ("found_key_text_hint_match", found_key_matches_hint),
        ("found_interruptors", found_interruptors),
        ("found_interrupter_count", len(found_interruptors)),
        ("found_interruptors_in_pool", found_interruptors_in_pool),
        ("best_score", getattr(solution, "score", None) if solution is not None else None),
        ("stop_reason", getattr(solution, "stop_reason", getattr(report, "stop_reason", None)) if solution is not None else None),
        ("match_ratio", None),
        ("plaintext_idx_length", len(plaintext_idx)),
        ("score_time_s", getattr(report, "score_time_s", None) if report is not None else None),
        ("decrypt_time_s", getattr(report, "decrypt_time_s", None) if report is not None else None),
        ("tokens", getattr(report, "tokens_processed", None) if report is not None else None),
        ("evals_or_candidates", getattr(report, "evals", None) if report is not None else None),
        ("elapsed_wall_time_s", elapsed_wall_time_s),
        ("status", status),
        ("error_type", error_type),
        ("error_message", error_message),
        ("notes", "configured like Welcome Pilgrim with period-13 Vigenere/interrupter search over ciphertext-zero pool; no solved claim without exact evidence"),
    ):
        print_kv(key, value)
    print("plaintext_latin:")
    print(plaintext_latin)
    print("plaintext_runes:")
    print(plaintext_runes)
    print("LP_KOAN_DURING_LESSON_FINAL_RESULT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
