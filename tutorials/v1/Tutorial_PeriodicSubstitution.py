from __future__ import annotations

"""Periodic substitution Kaeding pretty-print tutorial."""

import sys
from pathlib import Path
from typing import Any, Dict, Tuple

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, NormalizedInput, RunSpec, SolverSpec, by_name, cipher_instance, print_rdp_result, run
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALPHABET = 29
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345
USE_SEEDS = True
BLOCK_SEEDS = 6
SEED_KEYS = 32
SEED_SWAPS = 2
MIN_MATCH_RATIO = 1.0
SCENARIOS: Tuple[Tuple[str, Dict[str, Any]], ...] = (
    ("easy", dict(period=2, steps=400, restarts=1, inner_batch=48, slip_every=0, slip_blocks=1)),
    ("medium", dict(period=3, steps=700, restarts=2, inner_batch=64, slip_every=80, slip_blocks=1)),
)
FALLBACK_CFG: Dict[str, Any] = dict(
    steps=1400,
    restarts=4,
    inner_batch=96,
    slip_every=60,
    slip_blocks=2,
    slip_policy="stall",
    stall_rounds=120,
    stall_slip_limit=4,
    slip_swaps=40,
    plateau_min_delta=1e-6,
    block_seeds=10,
    seed_keys=64,
    seed_swaps=3,
)


def _preview(text: str, n: int = 160) -> str:
    return text if len(text) <= n else text[:n] + "..."


def _match_ratio(solution, pt_idx: list[int]) -> float:
    guess = getattr(solution, "plaintext_idx", None)
    if not guess:
        return 0.0
    a = np.asarray(guess, dtype=np.int64).reshape(-1)
    b = np.asarray(pt_idx, dtype=np.int64).reshape(-1)
    n = min(a.size, b.size)
    return float(np.mean(a[:n] == b[:n])) if n > 0 else 0.0


def _seed_cfg(cfg: Dict[str, Any]) -> Dict[str, int]:
    return {
        "block_seeds": int(cfg.get("block_seeds", BLOCK_SEEDS)),
        "seed_keys": int(cfg.get("seed_keys", SEED_KEYS)),
        "seed_swaps": int(cfg.get("seed_swaps", SEED_SWAPS)),
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


def _make_periodic_key(period: int, alphabet_size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    blocks = [rng.permutation(alphabet_size).astype(np.int16) for _ in range(period)]
    return np.concatenate(blocks, axis=0).astype(np.int16, copy=False)


def _build_ciphertext(pt_idx: np.ndarray, wli: list[list[int]], *, period: int, alphabet_size: int, seed: int):
    key = _make_periodic_key(period, alphabet_size, seed)
    cipher_spec = by_name.cipher("periodic_substitution", period=period, alphabet_size=alphabet_size)
    cipher = cipher_instance(cipher_spec)
    ct_idx = cipher.encrypt_single(plaintext=pt_idx, key=key)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    return ct_idx, ct_runes, key


def _make_periodic_seeds(ct_idx: np.ndarray, *, period: int, direction: Direction, seed: int, n_block_seeds: int, total_seeds: int, swaps_per_block: int) -> list[list[int]]:
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

    keys: list[list[int]] = [_concat([seeds[0] for seeds in block_seeds])]
    for _ in range(max(0, total_seeds - 1)):
        pick = [_s[int(rng.integers(0, len(_s)))] for _s in block_seeds]
        keys.append(_concat(pick))
    return keys


def main() -> None:
    direction = Direction.RTL
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(plaintext_english_string, direction=direction.value)
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)

    print("Periodic substitution problem")
    print(f"encoding direction: {direction.value}")
    print("Plaintext preview:", _preview(pt_runes))

    display_scorer_params = {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "encoding_dir": direction.value,
        "char_order_3_weight": 0.3,
        "char_order_4_weight": 0.7,
        "wli_order_3_weight": 0.4,
        "wli_order_4_weight": 0.6,
    }

    for label, cfg in SCENARIOS:
        period = int(cfg["period"])
        ct_idx, ct_runes, key = _build_ciphertext(
            pt_idx_arr,
            wli,
            period=period,
            alphabet_size=ALPHABET,
            seed=CIPHERTEXT_SEED + period,
        )
        ct_idx_list = [int(v) for v in ct_idx.tolist()]

        print("=" * 72)
        print(f"Scenario: {label} (period={period})")
        print("Ciphertext preview:", _preview(ct_runes))

        seed_keys = None
        if USE_SEEDS:
            seed_cfg = _seed_cfg(cfg)
            seed_keys = _make_periodic_seeds(
                ct_idx,
                period=period,
                direction=direction,
                seed=TUTORIAL_SEED + period,
                n_block_seeds=seed_cfg["block_seeds"],
                total_seeds=seed_cfg["seed_keys"],
                swaps_per_block=seed_cfg["seed_swaps"],
            )
            print(f"Seed pool: {len(seed_keys)} keys")

        cipher_spec = by_name.cipher("periodic_substitution", period=period, alphabet_size=ALPHABET)
        key_spec = KeySpec.periodic_substitution(period=period, alphabet_size=ALPHABET)
        scorer_params = dict(
            objective="pct.logp.win10",
            include_char=True,
            use_word_breaks=True,
            char_weights={3: 0.3, 4: 0.7},
            wli_weights={3: 0.4, 4: 0.6},
            encoding_dir=direction,
        )

        stop = oracle_stop_score(pt_idx, wli, scorer_params, device="cpu", encoding_dir=direction, margin=0.02, min_score=0.50, fallback=0.55)
        print_stop_summary(f"PeriodicSub {label}", stop)

        solver_kwargs = _build_solver_kwargs(cfg)
        solver_kwargs["stop_score"] = stop.stop_score
        solver = SolverSpec.kaeding(**solver_kwargs)

        result = run(
            text=ct_runes,
            cipher=cipher_spec,
            key=key_spec,
            solver=solver,
            scorer_params=scorer_params,
            wli_data=wli,
            encoding_dir=direction,
            telemetry_on=True,
            return_solver_report=True,
            **({} if seed_keys is None else {"initial_keys": seed_keys}),
        )

        if _match_ratio(result.solution, pt_idx) < 0.999:
            print("Retrying with stronger Kaeding settings...")
            retry_cfg = dict(cfg)
            retry_cfg.update(FALLBACK_CFG)
            seed_keys = None
            if USE_SEEDS:
                seed_cfg = _seed_cfg(retry_cfg)
                seed_keys = _make_periodic_seeds(
                    ct_idx,
                    period=period,
                    direction=direction,
                    seed=TUTORIAL_SEED + period + 99,
                    n_block_seeds=seed_cfg["block_seeds"],
                    total_seeds=seed_cfg["seed_keys"],
                    swaps_per_block=seed_cfg["seed_swaps"],
                )
                print(f"Seed pool (retry): {len(seed_keys)} keys")
            retry_kwargs = _build_solver_kwargs(retry_cfg)
            retry_kwargs["stop_score"] = stop.stop_score
            solver = SolverSpec.kaeding(**retry_kwargs)
            result = run(
                text=ct_runes,
                cipher=cipher_spec,
                key=key_spec,
                solver=solver,
                scorer_params=scorer_params,
                wli_data=wli,
                encoding_dir=direction,
                telemetry_on=True,
                return_solver_report=True,
                **({} if seed_keys is None else {"initial_keys": seed_keys}),
            )

        recovered = getattr(result.solution, "plaintext_rune", "") or getattr(result.solution, "plaintext_str", "")
        print("Recovered preview:", _preview(str(recovered)))
        display_spec = RunSpec(
            problem_input=NormalizedInput(ct_idx=ct_idx_list, wli=wli),
            cipher=cipher_spec,
            key=key_spec,
            solver=solver,
            scorer="rune",
            scorer_params=display_scorer_params,
            encoding_dir=direction,
            telemetry_on=True,
        )
        print_rdp_result(
            result,
            spec=display_spec,
            reference_idx=pt_idx,
            tutorial_entry={
                "path": "Tutorial_PeriodicSubstitution.py",
                "title": f"Periodic substitution {label} pretty-print variant",
                "gate": "optional_lm3_pretty_print",
                "acceptance_kind": "min_match_ratio",
                "min_match_ratio": MIN_MATCH_RATIO,
                "uses_oracle_stop_score": True,
            },
        )
        print(f"True key length ({label}): {int(key.size)}")


if __name__ == "__main__":
    main()
