from __future__ import annotations

"""Evidence-producing worked solve for the LP section "Welcome Pilgrim".

This file is intentionally self-contained. It loads the real LP source by
label, searches a period-8 Vigenere key with exactly 11 interrupters selected
from ciphertext-zero positions, validates against the canonical solved text,
prints structured evidence blocks, and writes a local JSON evidence file.
"""

import dataclasses
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

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

from solving.solved_lp.welcome_pilgrim.reference import CANONICAL_WELCOME_PILGRIM_IDX  # noqa: E402


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


def as_int_list(values: object) -> list[int]:
    if values is None:
        return []
    if hasattr(values, "tolist"):
        values = values.tolist()
    return [int(value) for value in list(values)]


def match_ratio(candidate: list[int], reference: tuple[int, ...]) -> float:
    total = max(len(candidate), len(reference))
    if total == 0:
        return 0.0
    limit = min(len(candidate), len(reference))
    matches = sum(1 for index in range(limit) if int(candidate[index]) == int(reference[index]))
    return matches / float(total)


def zero_positions(ct_idx: list[int]) -> list[int]:
    return [index for index, value in enumerate(ct_idx) if int(value) == 0]


def render_plaintext(plaintext_idx: list[int], wli: list[list[int]]) -> tuple[str, str]:
    if not plaintext_idx:
        return "", ""
    return Runeglish.to_rune_latin(plaintext_idx, wli), Runeglish.to_rune(plaintext_idx, wli)


def split_found_key(found_key: object, key_length: int) -> tuple[list[int], list[int]]:
    values = as_int_list(found_key)
    return values[:key_length], [value for value in values[key_length:] if value >= 0]


def get_nested(obj: object, *names: str, default: object = None) -> object:
    current = obj
    for name in names:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(name, default)
        else:
            current = getattr(current, name, default)
    return current


def json_value(value: object, *, max_list: int = 25) -> object:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if hasattr(value, "shape") and hasattr(value, "tolist"):
        shape = tuple(int(part) for part in getattr(value, "shape", ()))
        flat = value.reshape(-1).tolist() if hasattr(value, "reshape") else value.tolist()
        preview = [json_value(item) for item in list(flat)[:max_list]]
        return {"type": type(value).__name__, "shape": list(shape), "preview": preview}
    if dataclasses.is_dataclass(value):
        return json_value(dataclasses.asdict(value), max_list=max_list)
    if isinstance(value, dict):
        return {str(key): json_value(val, max_list=max_list) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        if len(items) > max_list:
            return {
                "type": type(value).__name__,
                "length": len(items),
                "preview": [json_value(item, max_list=max_list) for item in items[:max_list]],
            }
        return [json_value(item, max_list=max_list) for item in items]
    if hasattr(value, "to_json_dict"):
        return json_value(value.to_json_dict(), max_list=max_list)
    if hasattr(value, "__dict__"):
        return json_value(vars(value), max_list=max_list)
    return repr(value)


def safe_public_dict(obj: object) -> dict[str, object]:
    if obj is None:
        return {}
    if hasattr(obj, "to_json_dict"):
        data = obj.to_json_dict()
    elif dataclasses.is_dataclass(obj):
        data = dataclasses.asdict(obj)
    elif isinstance(obj, dict):
        data = obj
    else:
        data = {
            name: getattr(obj, name)
            for name in dir(obj)
            if not name.startswith("_") and not callable(getattr(obj, name, None))
        }
    return json_value(data)  # type: ignore[return-value]


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
    solution = getattr(result, "solution", result)
    report = getattr(result, "solver_report", None)
    plaintext_idx = as_int_list(getattr(solution, "plaintext_idx", []))
    plaintext_latin = str(getattr(solution, "plaintext_latin", "") or "")
    plaintext_runes = str(getattr(solution, "plaintext_rune", "") or "")
    if plaintext_idx and (not plaintext_latin or not plaintext_runes):
        plaintext_latin, plaintext_runes = render_plaintext(plaintext_idx, wli)

    found_key_core, found_interruptors = split_found_key(getattr(solution, "key", []), key_length)
    found_interruptors_in_pool = all(value in interruptor_pool for value in found_interruptors)
    extra_non_pool = [value for value in found_interruptors if value not in interruptor_pool]
    missing_pool = [value for value in interruptor_pool if value not in found_interruptors]
    ratio = match_ratio(plaintext_idx, reference_idx)
    best_score = get_nested(solution, "score", default=get_nested(report, "best_score"))
    stop_reason = get_nested(solution, "stop_reason", default=get_nested(report, "stop_reason"))
    status = (
        "solved"
        if ratio >= ACCEPTANCE_MATCH_RATIO
        and len(found_interruptors) == interruptor_count
        and found_interruptors_in_pool
        and len(plaintext_idx) == ciphertext_length
        else "diagnostic_not_yet_solved"
    )

    return {
        "attempt_index": attempt_index,
        "solver_variant": solver_variant,
        "scorer_variant": scorer_variant,
        "solver_name": solver.name,
        "solver_params": solver_params_dict(solver),
        "found_key_core": found_key_core,
        "found_key_core_len": len(found_key_core),
        "found_key_core_as_runes_or_latin_if_available": KEY_TEXT_HINT if found_key_core == [23, 10, 1, 10, 9, 10, 16, 26] else None,
        "found_interruptors": found_interruptors,
        "found_interrupter_count": len(found_interruptors),
        "found_interruptors_sorted": found_interruptors == sorted(found_interruptors),
        "found_interruptors_unique": len(found_interruptors) == len(set(found_interruptors)),
        "found_interruptors_in_pool": found_interruptors_in_pool,
        "found_interrupter_count_matches_required": len(found_interruptors) == interruptor_count,
        "missing_pool_positions": missing_pool,
        "extra_non_pool_positions": extra_non_pool,
        "best_score": best_score,
        "stop_reason": stop_reason,
        "match_ratio": ratio,
        "plaintext_idx_length": len(plaintext_idx),
        "score_time_s": get_nested(report, "score_time_s", default=get_nested(solution, "score_time_s")),
        "decrypt_time_s": get_nested(report, "decrypt_time_s", default=get_nested(solution, "decrypt_time_s")),
        "tokens": get_nested(report, "tokens_processed", default=get_nested(solution, "tokens_processed")),
        "evals_or_candidates": get_nested(report, "evals", default=get_nested(solution, "evals")),
        "elapsed_wall_time_s": elapsed_wall_time_s,
        "status": status,
        "error_type": None,
        "error_message": None,
        "solver_report_fields": [name for name in safe_public_dict(report).keys()] if report is not None else [],
        "solution_meta_keys": sorted(getattr(solution, "meta", {}).keys()) if isinstance(getattr(solution, "meta", None), dict) else [],
        "solver_report": safe_public_dict(report),
        "solution_meta": json_value(getattr(solution, "meta", None)),
        "plaintext_idx": plaintext_idx,
        "plaintext_latin": plaintext_latin,
        "plaintext_runes": plaintext_runes,
    }


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {json.dumps(json_value(value), ensure_ascii=False) if isinstance(value, (dict, list, tuple)) else value}")


def print_run_config(config: dict[str, object]) -> None:
    print("\nLP_WELCOME_PILGRIM_RUN_CONFIG_BEGIN")
    for key, value in config.items():
        print_kv(key, value)
    print("LP_WELCOME_PILGRIM_RUN_CONFIG_END")


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


def write_json_evidence(path: Path, evidence: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


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

    print("\nLP_WELCOME_PILGRIM_FINAL_RESULT_BEGIN")
    for key, value in (
        ("source_label", SOURCE_LABEL),
        ("resolved_source_label", metadata["source_label"]),
        ("main_page_start", metadata["main_page_start"]),
        ("main_page_end", metadata["main_page_end"]),
        ("recipe", recipe.recipe_label),
        ("cipher_family", recipe.cipher_family),
        ("solver_variant", best_attempt.get("solver_variant")),
        ("scorer_variant", SCORER_VARIANT),
        ("key_text_hint", KEY_TEXT_HINT),
        ("key_length", KEY_LENGTH),
        ("found_key_core", best_attempt.get("found_key_core")),
        ("found_interruptors", best_attempt.get("found_interruptors")),
        ("found_interruptors_sorted", best_attempt.get("found_interruptors_sorted")),
        ("found_interruptors_unique", best_attempt.get("found_interruptors_unique")),
        ("found_interruptors_in_pool", best_attempt.get("found_interruptors_in_pool")),
        ("found_interrupter_count", best_attempt.get("found_interrupter_count")),
        ("found_interrupter_count_matches_required", best_attempt.get("found_interrupter_count_matches_required")),
        ("interrupter_pool_size", len(interruptor_pool)),
        ("interrupter_pool", interruptor_pool),
        ("ciphertext_zero_positions", pool_validation["ciphertext_zero_positions"]),
        ("ciphertext_zero_count", pool_validation["ciphertext_zero_count"]),
        ("interrupter_pool_zero_validation", pool_validation["interrupter_pool_zero_validation"]),
        ("interrupter_pool_equals_ciphertext_zero_positions", pool_validation["interrupter_pool_equals_ciphertext_zero_positions"]),
        ("best_score", best_attempt.get("best_score")),
        ("stop_reason", best_attempt.get("stop_reason")),
        ("match_ratio", f"{float(best_attempt.get('match_ratio') or 0.0):.3f}"),
        ("plaintext_idx_length", best_attempt.get("plaintext_idx_length")),
        ("score_time_s", best_attempt.get("score_time_s")),
        ("decrypt_time_s", best_attempt.get("decrypt_time_s")),
        ("tokens", best_attempt.get("tokens")),
        ("evals_or_candidates", best_attempt.get("evals_or_candidates")),
        ("elapsed_wall_time_s", best_attempt.get("elapsed_wall_time_s")),
        ("status", status),
        ("acceptance_rule", "match_ratio >= 1.000 and 11 interrupters in pool and plaintext length equals ciphertext length"),
        ("notes", notes),
    ):
        print_kv(key, value)
    print("plaintext_latin:")
    print(plaintext_latin)
    print("plaintext_runes:")
    print(plaintext_runes)
    print("LP_WELCOME_PILGRIM_FINAL_RESULT_END")

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
    latest_path = EVIDENCE_DIR / "latest_solve_evidence.json"
    stamped_path = EVIDENCE_DIR / f"solve_evidence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    write_json_evidence(latest_path, evidence)
    write_json_evidence(stamped_path, evidence)
    print("json_evidence_latest:", latest_path.relative_to(ROOT))
    print("json_evidence_timestamped:", stamped_path.relative_to(ROOT))

    return 0 if status == "solved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
