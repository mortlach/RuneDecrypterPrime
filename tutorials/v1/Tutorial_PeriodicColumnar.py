"""
Tutorial: Periodic Columnar (Kaeding solver)

- Periodic substitution plus columnar transposition.
- Two difficulty presets: easy and medium.
- Runs both orderings: sub_then_col and col_then_sub.
- WLI scoring uses 3- and 4-grams to speed tuning.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

# Ensure repo root on sys.path so "python tutorials/v1/..." works
_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name, cipher_instance
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALPHABET = 29
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345

USE_SEEDS = True
BLOCK_SEEDS = 6
SEED_KEYS = 32
SEED_SWAPS = 2

ORDERS = ("sub_then_col", "col_then_sub")
SCENARIOS: Tuple[Tuple[str, Dict[str, Any]], ...] = (
    (
        "easy",
        dict(
            period=2,
            columns=3,
            steps=500,
            restarts=1,
            inner_batch=64,
            slip_every=120,
            slip_blocks=1,
            col_every=6,
            col_batch=48,
        ),
    ),
    (
        "medium",
        dict(
            period=3,
            columns=4,
            steps=800,
            restarts=2,
            inner_batch=80,
            slip_every=100,
            slip_blocks=1,
            col_every=5,
            col_batch=64,
        ),
    ),
)


def _preview(text: str, n: int = 120) -> str:
    return text if len(text) <= n else text[:n] + "..."


def _make_periodic_columnar_key(
    period: int,
    columns: int,
    alphabet_size: int,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    blocks = [rng.permutation(alphabet_size).astype(np.int16) for _ in range(period)]
    col_key = rng.permutation(columns).astype(np.int16)
    return np.concatenate(blocks + [col_key], axis=0).astype(np.int16, copy=False)


def _build_ciphertext(
    pt_idx: np.ndarray,
    *,
    period: int,
    columns: int,
    order: str,
    alphabet_size: int,
    seed: int,
) -> Tuple[np.ndarray, str, np.ndarray]:
    key = _make_periodic_columnar_key(period, columns, alphabet_size, seed)
    cipher_spec = by_name.cipher(
        "periodic_columnar",
        period=period,
        columns=columns,
        order=order,
        alphabet_size=alphabet_size,
    )
    cipher = cipher_instance(cipher_spec)
    ct_idx = cipher.encrypt_single(plaintext=pt_idx, key=key)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli=None)
    return ct_idx, ct_runes, key


def _make_periodic_seeds(
    ct_idx: np.ndarray,
    *,
    period: int,
    direction: Direction,
    seed: int,
    n_block_seeds: int,
    total_seeds: int,
    swaps_per_block: int,
) -> list[list[int]]:
    rng = np.random.default_rng(seed)
    block_seeds: list[list[list[int]]] = []
    for r in range(period):
        phase_idx = ct_idx[r::period]
        phase_runes = Runeglish.to_rune(phase_idx.tolist(), wli=None)
        seeds = make_seeds_from_freq(
            phase_runes,
            n_keys=n_block_seeds,
            swaps_per_key=swaps_per_block,
            seed=seed + r,
            A=ALPHABET,
            direction=direction.value,
        )
        block_seeds.append(seeds)

    def _concat(blocks: list[list[int]]) -> list[int]:
        out: list[int] = []
        for block in blocks:
            out.extend(block)
        return out

    keys: list[list[int]] = []
    base = _concat([seeds[0] for seeds in block_seeds])
    keys.append(base)
    for _ in range(max(0, total_seeds - 1)):
        pick = [_s[int(rng.integers(0, len(_s)))] for _s in block_seeds]
        keys.append(_concat(pick))
    return keys


def _attach_column_tail(keys: list[list[int]], columns: int, seed: int) -> list[list[int]]:
    rng = np.random.default_rng(seed)
    out: list[list[int]] = []
    for i, key in enumerate(keys):
        if i == 0:
            col = list(range(columns))
        else:
            col = rng.permutation(columns).astype(np.int16).tolist()
        out.append(key + col)
    return out


def main() -> None:
    direction = Direction.RTL
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        plaintext_english_string,
        direction=direction.value,
    )
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)

    print("Plaintext preview:", _preview(pt_runes))

    for label, cfg in SCENARIOS:
        period = int(cfg["period"])
        columns = int(cfg["columns"])

        for order in ORDERS:
            ct_idx, ct_runes, key = _build_ciphertext(
                pt_idx_arr,
                period=period,
                columns=columns,
                order=order,
                alphabet_size=ALPHABET,
                seed=CIPHERTEXT_SEED + period + columns,
            )

            print("=" * 72)
            print(f"Scenario: {label} (period={period}, columns={columns}, order={order})")
            print("Ciphertext preview:", _preview(ct_runes))

            seed_keys = None
            if USE_SEEDS and order == "col_then_sub":
                seed_keys = _make_periodic_seeds(
                    ct_idx,
                    period=period,
                    direction=direction,
                    seed=TUTORIAL_SEED + period + columns,
                    n_block_seeds=BLOCK_SEEDS,
                    total_seeds=SEED_KEYS,
                    swaps_per_block=SEED_SWAPS,
                )
                seed_keys = _attach_column_tail(seed_keys, columns, seed=TUTORIAL_SEED)
                print(f"Seed pool: {len(seed_keys)} keys (col_then_sub)")

            cipher_spec = by_name.cipher(
                "periodic_columnar",
                period=period,
                columns=columns,
                order=order,
                alphabet_size=ALPHABET,
            )
            key_spec = KeySpec.periodic_columnar(
                period=period,
                columns=columns,
                alphabet_size=ALPHABET,
            )

            solver_kwargs = dict(
                steps=cfg["steps"],
                restarts=cfg["restarts"],
                inner_batch=cfg["inner_batch"],
                slip_every=cfg["slip_every"],
                slip_blocks=cfg["slip_blocks"],
                col_every=cfg["col_every"],
                col_batch=cfg["col_batch"],
                block_schedule="random",
                plateau_rounds=0,
                plateau_min_delta=0.0,
                progress_pct=2,
                print_progress=True,
                seed=TUTORIAL_SEED,
            )
            solver = SolverSpec.kaeding(**solver_kwargs)

            scorer_params = dict(
                objective="pct.logp.win10",
                include_char=True,
                use_word_breaks=True,
                char_weights={3: 0.3, 4: 0.7},
                wli_weights={3: 0.4, 4: 0.6},
                encoding_dir=direction,
            )

            sol = run(
                text=ct_idx.tolist(),
                cipher=cipher_spec,
                key=key_spec,
                solver=solver,
                scorer_params=scorer_params,
                wli_data=wli,
                encoding_dir=direction,
                telemetry_on=True,
                **({} if seed_keys is None else {"initial_keys": seed_keys}),
            )

            recovered = getattr(sol, "plaintext_rune", "") or getattr(sol, "plaintext_str", "")
            print("Recovered preview:", _preview(str(recovered)))

            print_run_report(
                title=f"periodic-columnar-{label}-{order}",
                cipher="periodic_columnar",
                solution=sol,
                match_ok=None,
                app_version="tutorial-1.0",
                key_idx=key.tolist(),
                key_len=int(key.size),
                ct_idx=ct_idx.tolist(),
                ct_rune=ct_runes,
                pt_rune_ref=pt_runes,
                pt_idx_ref=pt_idx,
                wli=wli,
            )


if __name__ == "__main__":
    main()
