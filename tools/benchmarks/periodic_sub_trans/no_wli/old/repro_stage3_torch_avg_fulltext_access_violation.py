from __future__ import annotations

"""Manual repro harness for the no-WLI Stage-3 Torch AVG full-text crash.

This script intentionally targets the previously crashing path:
  - objective=avg.logp.win20
  - avg_window_policy=full_text
  - impl=torch
  - periodic_columnar Stage-3 style kaeding solve loop

Expected behavior on affected builds:
  - process may terminate with Windows access-violation (0xC0000005 / -1073741819)
    without a Python traceback.

Run from IDE or shell:
  python tools/benchmarks/periodic_sub_trans/no_wli/repro_stage3_torch_avg_fulltext_access_violation.py
"""

import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, run
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from tools.benchmarks.periodic_sub_trans.common import bench_solve_periodic_columnar_kaeding as base


# Repro knobs (edit directly; no environment variables).
PERIOD = 7
COLUMNS = 5
TEXT_LENGTH = 452
ALPHABET_SIZE = 29
ORDER = "col_then_sub"
KEY_SEED = 111
INITIAL_KEYS = 24
REPEAT_RUNS = 8
SEARCH_SEED_BASE = 910000
PROGRESS_PCT = 5


def _make_initial_keys(keyops: PeriodicStructuredMatrixKeyOps, *, seed: int, count: int) -> list[list[int]]:
    rng = np.random.default_rng(int(seed))
    return [keyops.random(rng).astype(int).tolist() for _ in range(int(count))]


def _build_ciphertext() -> tuple[np.ndarray, int]:
    direction = Direction.LTR
    base._require_assets(direction, ns=(3, 4), need_wli=False)
    pt_base, wli_base = base._encode_long_plaintext(direction)
    pt_idx, _wli, _off = base._slice_word_aligned(
        pt_base, wli_base, length=int(TEXT_LENGTH), offset_hint=0
    )
    key_len = int(PERIOD * ALPHABET_SIZE + COLUMNS)
    keyops = PeriodicStructuredMatrixKeyOps(
        K=key_len, period=int(PERIOD), A=int(ALPHABET_SIZE), columns=int(COLUMNS)
    )
    key_true = keyops.random(np.random.default_rng(int(KEY_SEED))).astype(np.int16, copy=False)
    cipher = PeriodicColumnarCipher(
        period=int(PERIOD),
        columns=int(COLUMNS),
        alphabet_size=int(ALPHABET_SIZE),
        order=str(ORDER),
    )
    ct_idx = np.asarray(cipher.encrypt(plaintext=pt_idx, key=key_true), dtype=np.uint8).reshape(-1)
    return ct_idx, key_len


def main() -> int:
    ct_idx, key_len = _build_ciphertext()
    keyops = PeriodicStructuredMatrixKeyOps(
        K=int(key_len), period=int(PERIOD), A=int(ALPHABET_SIZE), columns=int(COLUMNS)
    )
    print(
        "[repro_avg_fulltext_torch] start "
        f"period={PERIOD} cols={COLUMNS} len={TEXT_LENGTH} repeats={REPEAT_RUNS}",
        flush=True,
    )

    scorer_params = dict(
        objective="avg.logp.win20",
        include_char=True,
        use_word_breaks=False,
        char_weights={3: 0.2, 4: 0.8},
        wli_weights={},
        avg_window_policy="full_text",
        impl="torch",
        encoding_dir=Direction.LTR,
    )

    for i in range(int(REPEAT_RUNS)):
        run_seed = int(SEARCH_SEED_BASE + i)
        solver_cfg = dict(
            steps=3200,
            restarts=2,
            inner_batch=128,
            col_every=1,
            col_batch=112,
            slip_every=80,
            slip_blocks=1,
            slip_policy="stall",
            stall_rounds=220,
            stall_slip_limit=4,
            slip_swaps=40,
            use_raw_score=False,
            raw_accept_min_delta=1e-6,
            pct_plateau_min_delta=1e-4,
            plateau_rounds=320,
            plateau_min_delta=4e-4,
            delta_window=200,
            top_k=20,
            progress_pct=int(PROGRESS_PCT),
            print_progress=True,
            seed=int(run_seed),
        )
        init_keys = _make_initial_keys(keyops, seed=run_seed + 777, count=int(INITIAL_KEYS))
        t0 = time.time()
        sol = run(
            text=ct_idx.tolist(),
            cipher=by_name.cipher(
                "periodic_columnar",
                period=int(PERIOD),
                columns=int(COLUMNS),
                order=str(ORDER),
                alphabet_size=int(ALPHABET_SIZE),
            ),
            key=KeySpec.periodic_columnar(
                period=int(PERIOD),
                columns=int(COLUMNS),
                alphabet_size=int(ALPHABET_SIZE),
            ),
            solver=SolverSpec.kaeding(**solver_cfg),
            scorer_params=scorer_params,
            wli_data=[],
            encoding_dir=Direction.LTR,
            telemetry_on=False,
            force_no_wli=True,
            initial_keys=init_keys,
        )
        dt = time.time() - t0
        score = float(getattr(sol, "score", float("nan")))
        print(
            f"[repro_avg_fulltext_torch] iter={i + 1}/{REPEAT_RUNS} "
            f"seed={run_seed} score={score:.6f} seconds={dt:.1f}",
            flush=True,
        )

    print("[repro_avg_fulltext_torch] completed without native crash", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

