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
from typing import Any, Dict, Tuple, Sequence
import itertools

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
BRUTEFORCE_SUB_THEN_COL = True
SWEEP_BLOCK_SEEDS = 3
SWEEP_KEYS = 6
SWEEP_KEEP = 2

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
            period=6,
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

FALLBACK_CFG: Dict[str, Any] = dict(
    steps=1400,
    restarts=4,
    inner_batch=96,
    slip_every=80,
    slip_blocks=2,
    slip_policy="stall",
    stall_rounds=140,
    stall_slip_limit=4,
    slip_swaps=40,
    plateau_min_delta=1e-6,
    col_every=3,
    col_batch=96,
    block_seeds=10,
    seed_keys=64,
    seed_swaps=3,
    sweep_keep=6,
)


def _preview(text: str, n: int = 120) -> str:
    return text if len(text) <= n else text[:n] + "..."


def _match_ratio(solution, pt_idx: list[int]) -> float:
    guess = getattr(solution, "plaintext_idx", None)
    if not guess:
        return 0.0
    a = np.asarray(guess, dtype=np.int64).reshape(-1)
    b = np.asarray(pt_idx, dtype=np.int64).reshape(-1)
    n = min(a.size, b.size)
    if n <= 0:
        return 0.0
    return float(np.mean(a[:n] == b[:n]))


def _seed_cfg(cfg: Dict[str, Any]) -> Dict[str, int]:
    return {
        "block_seeds": int(cfg.get("block_seeds", BLOCK_SEEDS)),
        "seed_keys": int(cfg.get("seed_keys", SEED_KEYS)),
        "seed_swaps": int(cfg.get("seed_swaps", SEED_SWAPS)),
    }


def _sweep_cfg(cfg: Dict[str, Any]) -> Dict[str, int]:
    return {
        "sweep_block_seeds": int(cfg.get("sweep_block_seeds", SWEEP_BLOCK_SEEDS)),
        "sweep_keys": int(cfg.get("sweep_keys", SWEEP_KEYS)),
        "sweep_keep": int(cfg.get("sweep_keep", SWEEP_KEEP)),
        "sweep_swaps": int(cfg.get("sweep_swaps", SEED_SWAPS)),
    }


def _build_solver_kwargs(cfg: Dict[str, Any]) -> Dict[str, Any]:
    plateau_rounds = int(cfg.get("plateau_rounds", max(10, int(cfg["steps"] * 0.1))))
    solver_kwargs = dict(
        steps=int(cfg["steps"]),
        restarts=int(cfg["restarts"]),
        inner_batch=int(cfg["inner_batch"]),
        slip_every=int(cfg["slip_every"]),
        slip_blocks=int(cfg["slip_blocks"]),
        block_schedule=str(cfg.get("block_schedule", "random") or "random"),
        plateau_rounds=plateau_rounds,
        plateau_min_delta=float(cfg.get("plateau_min_delta", 1e-4)),
        stop_score=float(cfg.get("stop_score", 0.55)),
        progress_pct=2,
        print_progress=True,
        seed=TUTORIAL_SEED,
    )
    if "col_every" in cfg:
        solver_kwargs["col_every"] = int(cfg["col_every"])
    if "col_batch" in cfg:
        solver_kwargs["col_batch"] = int(cfg["col_batch"])
    for key in (
        "slip_policy",
        "stall_rounds",
        "stall_slip_limit",
        "slip_swaps",
        "stall_stop_on_limit",
        "use_raw_score",
        "raw_accept_min_delta",
        "pct_plateau_min_delta",
        "delta_window",
        "top_k",
    ):
        if key in cfg:
            solver_kwargs[key] = cfg[key]
    return solver_kwargs


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


def _columnar_cipher(columns: int):
    cache = getattr(_columnar_cipher, "_cache", None)
    if cache is None:
        cache = {}
        setattr(_columnar_cipher, "_cache", cache)
    if columns in cache:
        return cache[columns]
    spec = by_name.cipher("columnar", key_length=columns)
    cipher = cipher_instance(spec)
    cache[columns] = cipher
    return cipher


def _columnar_undo(ct_idx: np.ndarray, columns: int, perm: Sequence[int]) -> np.ndarray:
    cipher = _columnar_cipher(columns)
    return cipher.decrypt_single(ciphertext=ct_idx, key=list(perm))


def _score_test_key(
    ct_idx: np.ndarray,
    *,
    period: int,
    direction: Direction,
    scorer_params: Dict[str, Any],
    wli: Sequence[Sequence[int]],
    key: Sequence[int],
    seed: int,
) -> float:
    cipher_spec = by_name.cipher(
        "periodic_substitution",
        period=period,
        alphabet_size=ALPHABET,
    )
    key_spec = KeySpec.periodic_substitution(period=period, alphabet_size=ALPHABET)
    solver = SolverSpec.kaeding(
        test_key=list(key),
        verbose=False,
        print_progress=False,
        seed=seed,
    )
    sol = run(
        text=ct_idx,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=False,
    )
    return float(sol.score)


def _solve_sub_then_col(
    ct_idx: np.ndarray,
    *,
    period: int,
    columns: int,
    direction: Direction,
    scorer_params: Dict[str, Any],
    wli: Sequence[Sequence[int]],
    solver_kwargs: Dict[str, Any],
    seed_cfg: Dict[str, int],
    sweep_cfg: Dict[str, int],
) -> tuple[Any, Sequence[int], Sequence[int]]:
    perms = list(itertools.permutations(range(columns)))
    ranked: list[tuple[float, Sequence[int], np.ndarray]] = []
    print(f"Brute-force columns: {len(perms)} permutations")

    for perm in perms:
        ct_ps = _columnar_undo(ct_idx, columns, perm)
        seeds = _make_periodic_seeds(
            ct_ps,
            period=period,
            direction=direction,
            seed=TUTORIAL_SEED + period + columns,
            n_block_seeds=sweep_cfg["sweep_block_seeds"],
            total_seeds=sweep_cfg["sweep_keys"],
            swaps_per_block=sweep_cfg["sweep_swaps"],
        )
        best = float("-inf")
        for seed_key in seeds:
            score = _score_test_key(
                ct_ps,
                period=period,
                direction=direction,
                scorer_params=scorer_params,
                wli=wli,
                key=seed_key,
                seed=TUTORIAL_SEED,
            )
            if score > best:
                best = score
        ranked.append((best, perm, ct_ps))

    ranked.sort(key=lambda x: x[0], reverse=True)
    top = ranked[: max(1, sweep_cfg["sweep_keep"])]
    for score, perm, _ in top:
        print(f"  sweep best score={score:.6f} perm={list(perm)}")

    best_sol = None
    best_perm = None
    best_score = float("-inf")
    for _, perm, ct_ps in top:
        seed_keys = None
        if USE_SEEDS:
            seed_keys = _make_periodic_seeds(
                ct_ps,
                period=period,
                direction=direction,
                seed=TUTORIAL_SEED + period + columns,
                n_block_seeds=seed_cfg["block_seeds"],
                total_seeds=seed_cfg["seed_keys"],
                swaps_per_block=seed_cfg["seed_swaps"],
            )

        cipher_spec = by_name.cipher(
            "periodic_substitution",
            period=period,
            alphabet_size=ALPHABET,
        )
        key_spec = KeySpec.periodic_substitution(period=period, alphabet_size=ALPHABET)
        solver = SolverSpec.kaeding(**solver_kwargs)
        sol = run(
            text=ct_ps,
            cipher=cipher_spec,
            key=key_spec,
            solver=solver,
            scorer_params=dict(scorer_params),
            wli_data=wli,
            encoding_dir=direction,
            telemetry_on=True,
            **({} if seed_keys is None else {"initial_keys": seed_keys}),
        )
        if sol.score > best_score:
            best_sol = sol
            best_perm = perm
            best_score = float(sol.score)

    if best_sol is None or best_perm is None:
        raise RuntimeError("sub_then_col solve failed to return a solution")
    return best_sol, best_perm, best_sol.key


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

            scorer_params = dict(
                objective="pct.logp.win10",
                include_char=True,
                use_word_breaks=True,
                char_weights={3: 0.3, 4: 0.7},
                wli_weights={3: 0.4, 4: 0.6},
                encoding_dir=direction,
            )

            solver_kwargs = _build_solver_kwargs(cfg)
            seed_cfg = _seed_cfg(cfg)
            sweep_cfg = _sweep_cfg(cfg)

            if order == "sub_then_col" and BRUTEFORCE_SUB_THEN_COL:
                sol, best_perm, best_key = _solve_sub_then_col(
                    ct_idx,
                    period=period,
                    columns=columns,
                    direction=direction,
                    scorer_params=scorer_params,
                    wli=wli,
                    solver_kwargs=solver_kwargs,
                    seed_cfg=seed_cfg,
                    sweep_cfg=sweep_cfg,
                )
                if _match_ratio(sol, pt_idx) < 0.999:
                    print("Retrying with stronger Kaeding settings...")
                    retry_cfg = dict(cfg)
                    retry_cfg.update(FALLBACK_CFG)
                    sol, best_perm, best_key = _solve_sub_then_col(
                        ct_idx,
                        period=period,
                        columns=columns,
                        direction=direction,
                        scorer_params=scorer_params,
                        wli=wli,
                        solver_kwargs=_build_solver_kwargs(retry_cfg),
                        seed_cfg=_seed_cfg(retry_cfg),
                        sweep_cfg=_sweep_cfg(retry_cfg),
                    )
                recovered = getattr(sol, "plaintext_rune", "") or getattr(sol, "plaintext_str", "")
                print("Recovered preview:", _preview(str(recovered)))
                key_full = list(best_key) + list(best_perm)

                print_run_report(
                    title=f"periodic-columnar-{label}-{order}",
                    cipher="periodic_columnar",
                    solution=sol,
                    match_ok=None,
                    app_version="tutorial-1.0",
                    key_idx=key_full,
                    key_len=int(len(key_full)),
                    ct_idx=ct_idx.tolist(),
                    ct_rune=ct_runes,
                    pt_rune_ref=pt_runes,
                    pt_idx_ref=pt_idx,
                    wli=wli,
                )
                continue

            seed_keys = None
            if USE_SEEDS and order == "col_then_sub":
                seed_keys = _make_periodic_seeds(
                    ct_idx,
                    period=period,
                    direction=direction,
                    seed=TUTORIAL_SEED + period + columns,
                    n_block_seeds=seed_cfg["block_seeds"],
                    total_seeds=seed_cfg["seed_keys"],
                    swaps_per_block=seed_cfg["seed_swaps"],
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

            solver = SolverSpec.kaeding(**solver_kwargs)

            sol = run(
                text=ct_idx.tolist(),
                cipher=cipher_spec,
                key=key_spec,
                solver=solver,
                scorer_params=dict(scorer_params),
                wli_data=wli,
                encoding_dir=direction,
                telemetry_on=True,
                **({} if seed_keys is None else {"initial_keys": seed_keys}),
            )

            if _match_ratio(sol, pt_idx) < 0.999:
                print("Retrying with stronger Kaeding settings...")
                retry_cfg = dict(cfg)
                retry_cfg.update(FALLBACK_CFG)
                seed_keys = None
                if USE_SEEDS and order == "col_then_sub":
                    seed_cfg = _seed_cfg(retry_cfg)
                    seed_keys = _make_periodic_seeds(
                        ct_idx,
                        period=period,
                        direction=direction,
                        seed=TUTORIAL_SEED + period + columns + 99,
                        n_block_seeds=seed_cfg["block_seeds"],
                        total_seeds=seed_cfg["seed_keys"],
                        swaps_per_block=seed_cfg["seed_swaps"],
                    )
                    seed_keys = _attach_column_tail(seed_keys, columns, seed=TUTORIAL_SEED + 1)
                    print(f"Seed pool (retry): {len(seed_keys)} keys (col_then_sub)")
                solver = SolverSpec.kaeding(**_build_solver_kwargs(retry_cfg))
                sol = run(
                    text=ct_idx.tolist(),
                    cipher=cipher_spec,
                    key=key_spec,
                    solver=solver,
                    scorer_params=dict(scorer_params),
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
