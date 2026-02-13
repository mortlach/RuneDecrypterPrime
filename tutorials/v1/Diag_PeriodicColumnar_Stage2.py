from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import numpy as np

_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name, cipher_instance
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string


ALPHABET = 29
PERIOD = 13
COLUMNS = 13
ORDER = "col_then_sub"
SEED = 12345


def _inverse_perm(p: List[int]) -> List[int]:
    inv = [0] * len(p)
    for i, v in enumerate(p):
        inv[int(v)] = i
    return inv


def _swap_perm(p: List[int], i: int, j: int) -> List[int]:
    q = list(p)
    q[i], q[j] = q[j], q[i]
    return q


def main() -> None:
    direction = Direction.RTL
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        long_plaintext_string,
        direction=direction.value,
    )
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)

    # Build ciphertext using the real periodic_columnar cipher
    rng = np.random.default_rng(SEED)
    sub_key = np.concatenate([rng.permutation(ALPHABET) for _ in range(PERIOD)]).astype(np.int16)
    col_key = rng.permutation(COLUMNS).astype(np.int16)
    full_key = np.concatenate([sub_key, col_key]).astype(np.int16)

    cipher_full = by_name.cipher(
        "periodic_columnar",
        period=PERIOD,
        columns=COLUMNS,
        order=ORDER,
        alphabet_size=ALPHABET,
    )
    cipher_sub = by_name.cipher("periodic_substitution", period=PERIOD, alphabet_size=ALPHABET)
    cipher_col = by_name.cipher("columnar", key_length=COLUMNS)

    key_full = KeySpec.periodic_columnar(period=PERIOD, columns=COLUMNS, alphabet_size=ALPHABET)
    key_sub = KeySpec.periodic_substitution(period=PERIOD, alphabet_size=ALPHABET)
    key_col = KeySpec.permutation(len=COLUMNS)

    cipher_full_inst = cipher_instance(cipher_full)
    cipher_sub_inst = cipher_instance(cipher_sub)

    ct_idx = cipher_full_inst.encrypt_single(plaintext=pt_idx_arr, key=full_key)

    true_sub_key = full_key[: PERIOD * ALPHABET].tolist()
    true_col_key = full_key[PERIOD * ALPHABET :].tolist()
    inv_true_col = _inverse_perm(true_col_key)
    identity_col = list(range(COLUMNS))

    scorer_full = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={3: 0.3, 4: 0.7},
        wli_weights={3: 0.4, 4: 0.6},
        encoding_dir=direction,
    )

    # Stage-2 input: decrypt with true_sub_key
    inter_idx = cipher_sub_inst.decrypt_single(ciphertext=ct_idx, key=true_sub_key)

    def score_col(k: List[int], label: str) -> float:
        sol = run(
            text=inter_idx.tolist(),
            cipher=cipher_col,
            key=key_col,
            solver=SolverSpec.beam(beam_width=1, test_key=k, verbose=False, print_progress=False, seed=SEED),
            scorer_params=dict(scorer_full),
            wli_data=wli,
            encoding_dir=direction,
            telemetry_on=False,
        )
        s = float(sol.score)
        print(f"{label:>22}: {s:.6f}  key={k}")
        return s

    print("\n--- Columnar key semantics sanity check (scores on inter_idx) ---")
    s_id = score_col(identity_col, "identity")
    s_true = score_col(true_col_key, "true_col_key")
    s_inv = score_col(inv_true_col, "inverse(true_col)")

    # A tiny neighbourhood check: if true key is right, swaps should usually get worse.
    print("\n--- Local swap neighbourhood around true_col_key ---")
    base = s_true
    worse = 0
    total = 0
    for (i, j) in [(0,1), (0,2), (1,2), (3,7), (5,9), (10,12)]:
        total += 1
        ss = score_col(_swap_perm(true_col_key, i, j), f"swap({i},{j})")
        if ss < base:
            worse += 1
    print(f"\nSwap tests worse-than-true: {worse}/{total}")

    # Now run your hybrid solver ON THE SAME inter_idx, then check key vs inverse(key)
    print("\n--- Run Stage-2 solver and test returned key semantics ---")
    solver_col = SolverSpec.hybrid(
        use_beam=True,
        beam_width=128,
        rounds=8,
        expand_mode="sample",
        sample_per_parent=64,
        top_parents_factor=0.4,
        progress_pct=10,
        print_progress=True,
        ga=dict(
            pop_size=180,
            generations=80,
            elite_frac=0.1,
            cx_frac=0.85,
            mut_prob=0.3,
            tournament_k=3,
            plateau_rounds=20,
            stop_score=0.50,
            print_progress=True,
        ),
        sa=dict(
            sa_iters=2000,
            sa_init_temp=0.95,
            sa_min_temp=1e-4,
            sa_cooling=0.997,
            plateau_rounds=250,
            local_improve_on_accept=True,
            stop_score=0.50,
            print_progress=True,
        ),
        seed=SEED,
        verbose=True,
        log_interval=10,
        stop_score=0.50,
    )

    sol = run(
        text=inter_idx.tolist(),
        cipher=cipher_col,
        key=key_col,
        solver=solver_col,
        scorer_params=dict(scorer_full),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        initial_keys=[identity_col] + [np.random.default_rng(SEED + i).permutation(COLUMNS).tolist() for i in range(8)],
    )

    found = list(getattr(sol, "key", []) or [])
    if not found:
        print("Solver returned empty key?!")
        return

    print(f"\nsolver returned: {found}")
    score_col(found, "solver_key")
    score_col(_inverse_perm(found), "inverse(solver_key)")

    # Finally, verify full-key score for whichever of (found/inv(found)) is best
    best_col = found
    best_score = score_col(found, "solver_key(rescore)")
    inv_score = score_col(_inverse_perm(found), "inv(rescore)")
    if inv_score > best_score:
        best_col = _inverse_perm(found)

    verify_key = true_sub_key + best_col
    print("\n--- Full verify on original ciphertext ---")
    sol_verify = run(
        text=ct_idx.tolist(),
        cipher=cipher_full,
        key=key_full,
        solver=SolverSpec.beam(beam_width=1, test_key=verify_key, verbose=False, print_progress=False, seed=SEED),
        scorer_params=dict(scorer_full),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=False,
    )
    print(f"verify score: {float(sol_verify.score):.6f}")

    print_run_report(
        title="diag-periodic-columnar-stage2",
        cipher="periodic_columnar",
        solution=sol_verify,
        match_ok=None,
        app_version="diag-1.0",
        key_idx=full_key.tolist(),
        key_len=int(full_key.size),
        ct_idx=ct_idx.tolist(),
        ct_rune=Runeglish.to_rune(ct_idx.tolist(), wli),
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
        wli=wli,
    )


if __name__ == "__main__":
    main()
