from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
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

"""
Tutorial: Liber Primus Welcome Pilgrim solve attempt

This is the first real LP solved-page example:

1) Load the Welcome Pilgrim ciphertext by source label.
2) Use WLI directly from the bundled master transcript.
3) Run the existing Vigenere solver with interruptor search enabled.
4) Bound the interrupter count so the example is controlled.
5) Compare the final result against the canonical solved text after the solve.

The solver is not given the canonical plaintext or the canonical key. The only
LP-specific source input is the label `welcome_pilgrim`.
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SOURCE_LABEL = "welcome_pilgrim"
KEY_LENGTH = 7  # DIVINITY is validation knowledge; the solve only receives period=7.
TUTORIAL_SEED = 2026

# Canonical solved Welcome Pilgrim plaintext as Runeglish positions, derived from
# the solved LP reference sheet. This is validation-only: it is not used to set
# the solver key, stop score, candidate pool, or search trajectory. It preserves
# the real LP typo WIDSOM.
CANONICAL_WELCOME_PILGRIM_IDX: tuple[int, ...] = (
    7, 18, 20, 5, 3, 19, 18, 7, 18, 20, 5, 3, 19, 18, 13, 10, 20, 6, 4, 10,
    19, 16, 3, 2, 18, 6, 4, 28, 16, 11, 3, 1, 4, 9, 18, 26, 16, 3, 7, 24,
    4, 23, 2, 18, 18, 9, 23, 3, 0, 24, 20, 20, 2, 21, 15, 10, 16, 10, 15, 9,
    3, 16, 24, 9, 28, 15, 26, 16, 4, 10, 13, 17, 1, 16, 0, 3, 4, 2, 3, 15,
    18, 7, 8, 3, 0, 10, 9, 23, 2, 18, 10, 4, 7, 24, 26, 8, 18, 4, 18, 10,
    16, 10, 15, 24, 9, 18, 5, 18, 15, 15, 24, 4, 26, 3, 9, 18, 24, 20, 3, 21,
    2, 18, 7, 24, 26, 26, 3, 1, 7, 10, 20, 20, 0, 10, 9, 23, 24, 9, 18, 9,
    23, 16, 3, 24, 20, 20, 15, 16, 4, 1, 6, 6, 20, 18, 24, 9, 23, 15, 1, 0,
    0, 18, 4, 21, 26, 3, 1, 4, 10, 9, 9, 3, 5, 18, 9, 5, 18, 26, 3, 1,
    4, 10, 20, 20, 1, 15, 27, 9, 15, 26, 3, 1, 4, 5, 18, 4, 16, 24, 10, 9,
    16, 26, 24, 9, 23, 26, 3, 1, 4, 4, 28, 20, 10, 16, 26, 1, 20, 16, 10, 19,
    24, 16, 18, 20, 26, 26, 3, 1, 7, 10, 20, 20, 23, 10, 15, 5, 3, 1, 18, 4,
    24, 9, 18, 9, 23, 16, 3, 15, 18, 20, 0, 10, 16, 10, 15, 2, 4, 3, 1, 6,
    8, 2, 10, 15, 13, 10, 20, 6, 4, 10, 19, 24, 6, 18, 2, 24, 16, 7, 18, 15,
    8, 24, 13, 18, 3, 1, 4, 15, 18, 20, 1, 18, 15, 24, 9, 23, 3, 1, 4, 4,
    28, 20, 10, 16, 10, 18, 15, 11, 3, 1, 4, 9, 18, 26, 23, 18, 18, 13, 7, 10,
    2, 10, 9, 24, 9, 23, 26, 3, 1, 7, 10, 20, 20, 24, 4, 4, 10, 1, 18, 3,
    1, 16, 15, 10, 23, 18, 20, 10, 5, 18, 2, 18, 10, 9, 15, 16, 24, 4, 10, 16,
    10, 15, 3, 9, 20, 26, 2, 4, 3, 1, 6, 8, 6, 3, 21, 7, 10, 2, 10, 9,
    2, 24, 16, 7, 18, 19, 24, 26, 18, 19, 18, 4, 6, 18, 7, 10, 23, 15, 3, 19,
    26, 3, 1, 24, 4, 18, 24, 17, 18, 21, 1, 9, 16, 3, 26, 3, 1, 4, 15, 18,
    20, 0, 26, 3, 1, 24, 4, 18, 24, 20, 24, 7, 1, 9, 16, 3, 26, 3, 1, 4,
    15, 18, 20, 0, 28, 5, 8, 10, 9, 16, 18, 20, 20, 10, 6, 18, 9, 5, 18, 10,
    15, 8, 3, 20, 26, 0, 3, 4, 24, 20, 20, 2, 24, 16, 20, 10, 1, 18, 15, 10,
    15, 8, 3, 20, 26, 24, 9, 10, 9, 15, 16, 4, 1, 5, 16, 27, 9, 5, 3, 19,
    19, 24, 9, 23, 26, 3, 1, 4, 3, 7, 9, 15, 18, 20, 0,
)


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return int(default)
    return int(value.strip())


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
    canonical_latin: str,
    canonical_runes: str,
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
    print("canonical_plaintext_latin:")
    print(canonical_latin)
    print("plaintext_latin:")
    print(plaintext_latin or "<empty>")
    print("canonical_plaintext_runes:")
    print(canonical_runes)
    print("plaintext_runes:")
    print(plaintext_runes or "<empty>")
    print("LP_WELCOME_FINAL_RESULT_END")


def main() -> None:
    max_interruptors = _env_int("RDP_LP_WELCOME_MAX_INTERRUPTERS", 5)
    # Backwards-compatible spelling used in the README before this tutorial was gated.
    max_interruptors = _env_int("RDP_LP_WELCOME_MAX_INTERRUPTORS", max_interruptors)
    beam_width = _env_int("RDP_LP_WELCOME_BEAM_WIDTH", 64)
    plateau_rounds = _env_int("RDP_LP_WELCOME_PLATEAU_ROUNDS", 5)
    direction = _env_direction("RDP_LP_WELCOME_DIRECTION", Direction.RTL)

    payload = lp.payload_from_label(SOURCE_LABEL)
    ct_idx = list(payload.ct_idx)
    wli = [list(pair) for pair in payload.wli]
    interruptor_pool = list(range(len(ct_idx)))
    canonical_idx = list(CANONICAL_WELCOME_PILGRIM_IDX)
    if len(canonical_idx) != len(ct_idx) or len(canonical_idx) != len(wli):
        raise ValueError(
            "Canonical Welcome Pilgrim reference is not aligned with the loaded source payload: "
            f"canonical={len(canonical_idx)} ct={len(ct_idx)} wli={len(wli)}"
        )
    canonical_latin = Runeglish.to_rune_latin(canonical_idx, wli)
    canonical_runes = Runeglish.to_rune(canonical_idx, wli)

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
    print("Canonical reference length:", len(canonical_idx))
    print("Key period:", KEY_LENGTH)
    print("Max interruptors:", max_interruptors)
    print("Encoding direction:", direction.value)

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
    print("Canonical plaintext preview:", canonical_latin[:300])
    print("Plaintext preview:", plaintext_latin[:300])

    print_run_report(
        title="LP Welcome Pilgrim label solve",
        cipher="vigenere",
        solution=solution,
        match_ok=None,
        app_version="tutorial-1.0",
        key_idx=found_core + found_interruptors,
        key_len=len(found_core) + len(found_interruptors),
        ct_idx=ct_idx,
        ct_rune=Runeglish.to_rune(ct_idx, wli),
        pt_rune_ref=canonical_runes,
        pt_idx_ref=canonical_idx,
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
        canonical_latin=canonical_latin,
        canonical_runes=canonical_runes,
        plaintext_idx=plaintext_idx,
        plaintext_latin=plaintext_latin,
        plaintext_runes=plaintext_runes,
    )


if __name__ == "__main__":
    main()
