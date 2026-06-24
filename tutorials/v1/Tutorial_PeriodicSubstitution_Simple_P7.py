from __future__ import annotations

"""Periodic substitution simple P7 pretty-print tutorial."""

import sys
from pathlib import Path
from typing import Sequence, Tuple

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, NormalizedInput, RunSpec, SolverSpec, by_name, cipher_instance, print_rdp_result, run
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.seed_utils import make_periodic_seed_pool, make_periodic_structured_key
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALPHABET = 29
PERIOD = 7
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345
USE_SEEDS = True
BLOCK_SEEDS = 8
SEED_KEYS = 48
SEED_SWAPS = 2
SOLVER_STEPS = 1200
SOLVER_RESTARTS = 3
SOLVER_INNER_BATCH = 96
SOLVER_SLIP_EVERY = 80
SOLVER_SLIP_BLOCKS = 1
SOLVER_STALL_ROUNDS = 140
SOLVER_STALL_SLIP_LIMIT = 3
SOLVER_SLIP_SWAPS = 30
MIN_MATCH_RATIO = 1.0


def _preview(text: str, n: int = 160) -> str:
    return text if len(text) <= n else text[:n] + "..."


def _match_ratio(solution, pt_idx: Sequence[int]) -> float:
    guess = getattr(solution, "plaintext_idx", None)
    if guess is None:
        return 0.0
    a = np.asarray(guess, dtype=np.int64).reshape(-1)
    b = np.asarray(pt_idx, dtype=np.int64).reshape(-1)
    n = min(a.size, b.size)
    return float(np.mean(a[:n] == b[:n])) if n > 0 else 0.0


def _build_ciphertext(
    pt_idx: np.ndarray,
    wli: Sequence[Sequence[int]],
    *,
    period: int,
    alphabet_size: int,
    seed: int,
) -> Tuple[np.ndarray, str, np.ndarray]:
    key = np.asarray(
        make_periodic_structured_key(period=period, alphabet_size=alphabet_size, seed=seed),
        dtype=np.int16,
    )
    cipher_spec = by_name.cipher("periodic_substitution", period=period, alphabet_size=alphabet_size)
    cipher = cipher_instance(cipher_spec)
    ct_idx = cipher.encrypt_single(plaintext=pt_idx, key=key)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    return ct_idx, ct_runes, key


def main() -> None:
    encoding_dir = Direction.RTL
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        plaintext_english_string,
        direction=encoding_dir.value,
    )
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)

    print("Periodic substitution simple problem")
    print(f"encoding direction: {encoding_dir.value}")
    print(f"period: {PERIOD}")
    print("Plaintext preview:", _preview(pt_runes))

    ct_idx, ct_runes, key = _build_ciphertext(
        pt_idx_arr,
        wli,
        period=PERIOD,
        alphabet_size=ALPHABET,
        seed=CIPHERTEXT_SEED + PERIOD,
    )
    ct_idx_list = [int(v) for v in ct_idx.tolist()]
    print("Ciphertext preview:", _preview(ct_runes))

    seed_keys = None
    if USE_SEEDS:
        seed_keys = make_periodic_seed_pool(
            ct_idx,
            period=PERIOD,
            direction=encoding_dir.value,
            seed=TUTORIAL_SEED + PERIOD,
            n_block_seeds=BLOCK_SEEDS,
            total_seeds=SEED_KEYS,
            swaps_per_block=SEED_SWAPS,
            alphabet_size=ALPHABET,
        )
        print(f"Seed pool: {len(seed_keys)} keys")

    cipher_spec = by_name.cipher("periodic_substitution", period=PERIOD, alphabet_size=ALPHABET)
    key_spec = KeySpec.periodic_substitution(period=PERIOD, alphabet_size=ALPHABET)
    scorer_params = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={3: 0.3, 4: 0.7},
        wli_weights={3: 0.4, 4: 0.6},
        encoding_dir=encoding_dir,
    )
    display_scorer_params = {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "encoding_dir": encoding_dir.value,
        "char_order_3_weight": 0.3,
        "char_order_4_weight": 0.7,
        "wli_order_3_weight": 0.4,
        "wli_order_4_weight": 0.6,
    }

    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=encoding_dir,
        margin=0.02,
        min_score=0.50,
        fallback=0.55,
    )
    print_stop_summary("PeriodicSub simple P7", stop)

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
    display_spec = RunSpec(
        problem_input=NormalizedInput(ct_idx=ct_idx_list, wli=wli),
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        scorer="rune",
        scorer_params=display_scorer_params,
        encoding_dir=encoding_dir,
        telemetry_on=True,
    )

    result = run(
        text=ct_runes,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        scorer_params=scorer_params,
        wli_data=wli,
        encoding_dir=encoding_dir,
        telemetry_on=True,
        return_solver_report=True,
        **({} if seed_keys is None else {"initial_keys": seed_keys}),
    )

    ratio = _match_ratio(result.solution, pt_idx)
    if ratio < 0.999:
        raise RuntimeError(f"Solve failed: match_ratio={ratio:.4f}")
    recovered = getattr(result.solution, "plaintext_rune", "") or getattr(result.solution, "plaintext_str", "")
    print("Recovered preview:", _preview(str(recovered)))

    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_PeriodicSubstitution_Simple_P7.py",
            "title": "Periodic substitution simple P7 pretty-print variant",
            "gate": "optional_lm3_pretty_print",
            "acceptance_kind": "min_match_ratio",
            "min_match_ratio": MIN_MATCH_RATIO,
            "uses_oracle_stop_score": True,
        },
    )
    print(f"True key length: {int(key.size)}")


if __name__ == "__main__":
    main()
