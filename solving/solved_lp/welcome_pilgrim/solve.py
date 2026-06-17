from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import (  # noqa: E402
    Direction,
    InterruptorConfig,
    KeySpec,
    SolverSpec,
    by_name,
    run,
)
from rune_decrypter_prime.data import liber_primus as lp  # noqa: E402
from rune_decrypter_prime.utils.pretty import print_run_report  # noqa: E402
from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402

from solving.solved_lp.welcome_pilgrim.reference import CANONICAL_WELCOME_PILGRIM_IDX  # noqa: E402

"""
Welcome Pilgrim solved-LP solve attempt.

This is intentionally small and readable:

1. Load the real LP ciphertext/WLI by source label.
2. Run the existing Vigenere solver with interruptor search enabled.
3. Print the key, interruptors, score, recovered plaintext, and match ratio.

No canonical plaintext or canonical key is supplied to the solver. The canonical
reference is imported only after the solve for validation/reporting.
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SOURCE_LABEL = "welcome_pilgrim"
KEY_LENGTH = 7
TUTORIAL_SEED = 2026
DEFAULT_MIN_MATCH = 1.0


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return int(default)
    return int(value.strip())


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return float(default)
    return float(value.strip())


def _env_direction(name: str, default: Direction) -> Direction:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return Direction(value.strip().lower())


def _as_int_list(values: object) -> list[int]:
    if values is None:
        return []
    if hasattr(values, "tolist"):
        values = values.tolist()
    return [int(v) for v in list(values)]


def _split_found_key(found_key: object, *, key_length: int) -> tuple[list[int], list[int]]:
    values = _as_int_list(found_key)
    core = values[:key_length]
    interrupters = [v for v in values[key_length:] if v >= 0]
    return core, interrupters


def _match_ratio(found: list[int], reference: tuple[int, ...]) -> float:
    denominator = max(len(found), len(reference))
    if denominator == 0:
        return 0.0
    limit = min(len(found), len(reference))
    matches = sum(1 for idx in range(limit) if int(found[idx]) == int(reference[idx]))
    return matches / float(denominator)


def _render_plaintext(solution: object, wli: list[list[int]]) -> tuple[list[int], str, str]:
    plaintext_idx = _as_int_list(getattr(solution, "plaintext_idx", []))
    plaintext_latin = str(getattr(solution, "plaintext_latin", "") or "")
    plaintext_runes = str(getattr(solution, "plaintext_rune", "") or "")
    if plaintext_idx and not plaintext_latin:
        plaintext_latin = Runeglish.to_rune_latin(plaintext_idx, wli)
    if plaintext_idx and not plaintext_runes:
        plaintext_runes = Runeglish.to_rune(plaintext_idx, wli)
    return plaintext_idx, plaintext_latin, plaintext_runes


def _print_final_result_block(
    *,
    payload: object,
    solution: object,
    report: object,
    found_core: list[int],
    found_interruptors: list[int],
    match_ratio: float,
    min_match: float,
    plaintext_idx: list[int],
    plaintext_latin: str,
    plaintext_runes: str,
) -> None:
    print("\nLP_WELCOME_FINAL_RESULT_BEGIN")
    print("source_label:", SOURCE_LABEL)
    print("resolved_source_label:", getattr(payload, "metadata", {}).get("source_label"))
    print("master_page_start:", getattr(payload, "metadata", {}).get("master_page_start"))
    print("master_page_end:", getattr(payload, "metadata", {}).get("master_page_end"))
    print("key_period:", KEY_LENGTH)
    print("found_key_core:", found_core)
    print("found_interruptors:", found_interruptors)
    print("found_interruptor_count:", len(found_interruptors))
    print("best_score:", getattr(solution, "score", None))
    print("stop_reason:", getattr(solution, "stop_reason", None))
    print("solver_report_best_score:", getattr(report, "best_score", None))
    print("plaintext_idx_length:", len(plaintext_idx))
    print(f"Match ratio: {match_ratio:.3f}")
    print(f"Required match ratio: {min_match:.3f}")
    print("plaintext_latin:")
    print(plaintext_latin or "<empty>")
    print("plaintext_runes:")
    print(plaintext_runes or "<empty>")
    print("LP_WELCOME_FINAL_RESULT_END")


def main() -> None:
    max_interruptors = _env_int("RDP_LP_WELCOME_MAX_INTERRUPTERS", 5)
    max_interruptors = _env_int("RDP_LP_WELCOME_MAX_INTERRUPTORS", max_interruptors)
    beam_width = _env_int("RDP_LP_WELCOME_BEAM_WIDTH", 64)
    plateau_rounds = _env_int("RDP_LP_WELCOME_PLATEAU_ROUNDS", 5)
    min_match = _env_float("RDP_LP_WELCOME_MIN_MATCH", DEFAULT_MIN_MATCH)
    direction = _env_direction("RDP_LP_WELCOME_DIRECTION", Direction.RTL)

    payload = lp.payload_from_label(SOURCE_LABEL)
    ct_idx = list(payload.ct_idx)
    wli = [list(pair) for pair in payload.wli]
    interruptor_pool = list(range(len(ct_idx)))

    if len(CANONICAL_WELCOME_PILGRIM_IDX) != len(ct_idx):
        raise ValueError(
            "Canonical Welcome Pilgrim reference is not aligned with the loaded source payload: "
            f"canonical={len(CANONICAL_WELCOME_PILGRIM_IDX)} ct={len(ct_idx)}"
        )

    print("LP source label:", SOURCE_LABEL)
    print("Resolved source label:", payload.metadata.get("source_label"))
    print(
        "Master transcript pages:",
        payload.metadata.get("master_page_start"),
        "to",
        payload.metadata.get("master_page_end"),
    )
    print("Ciphertext length:", len(ct_idx))
    print("WLI length:", len(wli))
    print("Key period:", KEY_LENGTH)
    print("Max interruptors:", max_interruptors)
    print("Encoding direction:", direction.value)
    print("Required match ratio:", f"{min_match:.3f}")

    interrupt_cfg = InterruptorConfig(
        mode="pool",
        pool=interruptor_pool,
        min_count=0,
        max_count=max_interruptors,
        search_strategy="keyops",
    )

    scorer_params = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={2: 0.3},
        wli_weights={2: 0.7},
        encoding_dir=direction,
    )

    solver = SolverSpec.beam(
        beam_width=beam_width,
        expand_mode="sweep",
        plateau_rounds=plateau_rounds,
        plateau_min_delta=1e-4,
        progress_pct=10,
        seed=TUTORIAL_SEED,
    )

    result = run(
        text=ct_idx,
        cipher=by_name.cipher("vigenere"),
        key=KeySpec.repeat(len=KEY_LENGTH),
        solver=solver,
        scorer_params=scorer_params,
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        interruptors=interrupt_cfg,
        return_solver_report=True,
    )

    solution = result.solution
    report = result.solver_report
    found_core, found_interruptors = _split_found_key(getattr(solution, "key", []), key_length=KEY_LENGTH)
    plaintext_idx, plaintext_latin, plaintext_runes = _render_plaintext(solution, wli)
    match_ratio = _match_ratio(plaintext_idx, CANONICAL_WELCOME_PILGRIM_IDX)

    print("Found key core:", found_core)
    print("Found interruptors:", found_interruptors)
    print("Found interruptor count:", len(found_interruptors))
    print("Best score:", getattr(solution, "score", None))
    print("Stop reason:", getattr(solution, "stop_reason", None))
    print("Solver report best score:", getattr(report, "best_score", None))
    print("Match ratio:", f"{match_ratio:.3f}")
    print("Plaintext preview:", plaintext_latin[:300])

    print_run_report(
        title="LP Welcome Pilgrim label solve",
        cipher="vigenere",
        solution=solution,
        match_ok=match_ratio >= min_match,
        app_version="tutorial-1.0",
        ct_idx=ct_idx,
        ct_rune=Runeglish.to_rune(ct_idx, wli),
        pt_idx_ref=list(CANONICAL_WELCOME_PILGRIM_IDX),
        wli=wli,
        interruptors_ref=None,
        compact=True,
    )

    _print_final_result_block(
        payload=payload,
        solution=solution,
        report=report,
        found_core=found_core,
        found_interruptors=found_interruptors,
        match_ratio=match_ratio,
        min_match=min_match,
        plaintext_idx=plaintext_idx,
        plaintext_latin=plaintext_latin,
        plaintext_runes=plaintext_runes,
    )

    if match_ratio < min_match:
        raise SystemExit(
            f"LP Welcome solve failed validation: match_ratio={match_ratio:.3f}; expected >= {min_match:.3f}"
        )


if __name__ == "__main__":
    main()
