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

The solver is not given the canonical plaintext or the canonical key. The only
LP-specific source input is the label `welcome_pilgrim`.
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SOURCE_LABEL = "welcome_pilgrim"
KEY_LENGTH = 7  # DIVINITY is validation knowledge; the solve only receives period=7.
TUTORIAL_SEED = 2026


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


def main() -> None:
    max_interruptors = _env_int("RDP_LP_WELCOME_MAX_INTERRUPTORS", 5)
    beam_width = _env_int("RDP_LP_WELCOME_BEAM_WIDTH", 64)
    plateau_rounds = _env_int("RDP_LP_WELCOME_PLATEAU_ROUNDS", 5)
    direction = _env_direction("RDP_LP_WELCOME_DIRECTION", Direction.RTL)

    payload = lp.payload_from_label(SOURCE_LABEL)
    ct_idx = list(payload.ct_idx)
    wli = [list(pair) for pair in payload.wli]
    interruptor_pool = list(range(len(ct_idx)))

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

    print("Found key core:", found_core)
    print("Found interruptors:", found_interruptors)
    print("Found interruptor count:", len(found_interruptors))
    print("Best score:", getattr(solution, "score", None))
    print("Stop reason:", getattr(solution, "stop_reason", None))
    print("Solver report best score:", getattr(report, "best_score", None))

    plaintext_idx = _as_int_list(getattr(solution, "plaintext_idx", []))
    plaintext_latin = Runeglish.to_rune_latin(plaintext_idx, wli) if plaintext_idx else ""
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
        wli=wli,
        interruptors_ref=None,
        compact=True,
    )


if __name__ == "__main__":
    main()
