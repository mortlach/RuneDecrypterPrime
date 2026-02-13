"""
Tutorial: Periodic Columnar (simple, period=7, order=sub_then_col)

- Single scenario, deterministic setup.
- Uses the registered 'periodic_columnar' cipher and Kaeding solver.
- Uses a small seed pool and an oracle stop score.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import numpy as np

# Ensure repo root on sys.path so "python tutorials/v1/..." works
_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name, cipher_instance
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string

# Assumed helpers (you said: “assume helper functions exist”)
from rune_decrypter_prime.utils.seed_utils import (
    make_true_periodic_columnar_key,
    make_periodic_columnar_seed_pool,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALPHABET = 29
PERIOD = 7
COLUMNS = 13  # tweakable; keep constant in both tutorials for comparability
ORDER = "sub_then_col"  # must match what your cipher expects

TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 54321

USE_SEEDS = True
SEED_KEYS = 48

SOLVER_STEPS = 2600
SOLVER_RESTARTS = 4
SOLVER_INNER_BATCH = 128
SOLVER_SLIP_EVERY = 80
SOLVER_SLIP_BLOCKS = 1

# stall/slip policy: same “simple tutorial” style as PeriodicSubstitution_Simple_P7
SOLVER_STALL_ROUNDS = 160
SOLVER_STALL_SLIP_LIMIT = 3
SOLVER_SLIP_SWAPS = 40


def _preview(text: str, n: int = 120) -> str:
    return text if len(text) <= n else text[:n] + "..."


def _match_ratio(solution, pt_idx: Sequence[int]) -> float:
    guess = getattr(solution, "plaintext_idx", None)
    if guess is None:
        return 0.0
    a = np.asarray(guess, dtype=np.int64).reshape(-1)
    b = np.asarray(pt_idx, dtype=np.int64).reshape(-1)
    n = min(a.size, b.size)
    if n <= 0:
        return 0.0
    return float(np.mean(a[:n] == b[:n]))


def main() -> None:
    direction = Direction.RTL

    # Plaintext -> rune indices + WLI
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        plaintext_english_string,
        direction=direction.value,
    )
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)

    print("Plaintext preview:", _preview(pt_runes))

    # Build true key + ciphertext (registered cipher path)
    rng_key = np.random.default_rng(CIPHERTEXT_SEED)
    true_key = make_true_periodic_columnar_key(
        rng=rng_key,
        period=PERIOD,
        alphabet_size=ALPHABET,
        columns=COLUMNS,
        order=ORDER,
    )

    cipher_spec = by_name.cipher(
        "periodic_columnar",
        period=PERIOD,
        alphabet_size=ALPHABET,
        columns=COLUMNS,
        order=ORDER,
    )
    cipher = cipher_instance(cipher_spec)
    ct_idx = cipher.encrypt_single(plaintext=pt_idx_arr, key=true_key)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)

    print("=" * 72)
    print(f"Scenario: simple (period={PERIOD}, columns={COLUMNS}, order={ORDER})")
    print("Ciphertext preview:", _preview(ct_runes))

    # Seed pool (assumed helper)
    seed_keys = None
    if USE_SEEDS:
        seed_keys = make_periodic_columnar_seed_pool(
            ciphertext_idx=ct_idx,
            period=PERIOD,
            alphabet_size=ALPHABET,
            columns=COLUMNS,
            order=ORDER,
            direction=direction,
            seed=TUTORIAL_SEED,
            n_keys=SEED_KEYS,
        )
        print(f"Seed pool: {len(seed_keys)} keys")

    # KeySpec + scorer + oracle stop
    key_spec = KeySpec.periodic_columnar(
        period=PERIOD,
        alphabet_size=ALPHABET,
        columns=COLUMNS,
        order=ORDER,
    )

    scorer_params = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={3: 0.3, 4: 0.7},
        wli_weights={3: 0.4, 4: 0.6},
        encoding_dir=direction,
    )

    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.50,
        fallback=0.55,
    )
    print_stop_summary("PeriodicColumnar simple P7 (sub→col)", stop)

    plateau_rounds = max(10, int(SOLVER_STEPS * 0.1))
    solver = SolverSpec.kaeding(
        steps=SOLVER_STEPS,
        restarts=SOLVER_RESTARTS,
        inner_batch=SOLVER_INNER_BATCH,
        slip_every=SOLVER_SLIP_EVERY,
        slip_blocks=SOLVER_SLIP_BLOCKS,
        block_schedule="round_robin",
        plateau_rounds=plateau_rounds,
        plateau_min_delta=1e-4,
        stop_score=stop.stop_score,
        progress_pct=2,
        print_progress=True,
        seed=TUTORIAL_SEED,
        slip_policy="stall",
        stall_rounds=SOLVER_STALL_ROUNDS,
        stall_slip_limit=SOLVER_STALL_SLIP_LIMIT,
        slip_swaps=SOLVER_SLIP_SWAPS,
        stall_stop_on_limit=True,
    )

    sol = run(
        text=ct_runes,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        scorer_params=scorer_params,
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        **({} if seed_keys is None else {"initial_keys": seed_keys}),
    )

    ratio = _match_ratio(sol, pt_idx)
    if ratio < 0.999:
        raise RuntimeError(f"Solve failed: match_ratio={ratio:.4f}")

    recovered = getattr(sol, "plaintext_rune", "") or getattr(sol, "plaintext_str", "")
    print("Recovered preview:", _preview(str(recovered)))

    # Keep the report shape consistent with your other tutorials
    key_idx = true_key.tolist() if hasattr(true_key, "tolist") else list(true_key)

    print_run_report(
        title="periodic-columnar-simple-p7-sub-then-col",
        cipher="periodic_columnar",
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.0",
        key_idx=key_idx,
        key_len=int(len(key_idx)),
        ct_idx=ct_idx.tolist(),
        ct_rune=ct_runes,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
        wli=wli,
    )


if __name__ == "__main__":
    main()
