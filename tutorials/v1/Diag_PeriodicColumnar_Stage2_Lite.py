"""
Diag_PeriodicColumnar_Stage2_Lite.py

Goal:
- Strip things down to the minimum needed to diagnose Stage-2 (columnar) search.
- Keep everything as a standalone *tutorial/diag* script (no registered cipher changes).
- Provide a staged scoring path that is usually needed for hard transposition problems:
  (A) char n-grams without word breaks  -> find basin
  (B) full objective (word breaks + WLI) -> refine

This script prints:
- Oracle scores under (A) and (B)
- Random-key score distribution under (A) and (B)
- A staged solve (A then B) and checks whether it reaches the true basin
"""

from __future__ import annotations

import numpy as np

from rune_decrypter_prime.core.config import KeySpec, CipherSpec, SolverSpec, Direction
from rune_decrypter_prime.core.registry import by_name
from rune_decrypter_prime.core.factory import cipher_instance
from rune_decrypter_prime.api.run import run
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string
from rune_decrypter_prime.utils.runeglish import Runeglish


# -----------------------------
# Config knobs (edit here)
# -----------------------------

SEED = 12345

PERIOD = 13
COLUMNS = 13
ORDER = "col_then_sub"  # must match the scenario you care about

# Speed knobs
FAST_MODE = True
RANDOM_SAMPLES = 48 if FAST_MODE else 256

# Stage-2 (A): "transposition-friendly" scorer
#   - no word breaks
#   - no WLI
SCORER_STAGE_A = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=False,
    char_weights={3: 0.3, 4: 0.7},
    wli_weights={},  # deliberately empty
)

# Stage-2 (B): full scorer (your current hard objective)
SCORER_FULL = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=True,
    char_weights={3: 0.3, 4: 0.7},
    wli_weights={3: 0.4, 4: 0.6},
)


def _rng():
    return np.random.default_rng(SEED)


def _rand_perm(n: int, rng: np.random.Generator) -> list[int]:
    return rng.permutation(n).tolist()


def _is_perm(key: list[int], n: int) -> bool:
    return len(key) == n and set(key) == set(range(n))


def _score_test_key(
    *,
    text_idx: np.ndarray,
    cipher: CipherSpec,
    key: KeySpec,
    test_key: list[int],
    scorer_params: dict,
    wli_data: dict,
    encoding_dir: Direction,
) -> float:
    """
    Uses beam_width=1 + test_key to score a single key through the *same* pipeline/score object
    the solver uses.
    """
    sol = run(
        text=text_idx.tolist(),
        cipher=cipher,
        key=key,
        solver=SolverSpec.beam(
            beam_width=1,
            rounds=1,
            expand_mode="sample",
            sample_per_parent=1,
            top_parents_factor=1.0,
            stop_score=-1.0,
            progress_pct=100,
            print_progress=False,
            seed=SEED,
            log_interval=999999,
            test_key=test_key,
        ),
        scorer_params=scorer_params,
        wli_data=wli_data,
        encoding_dir=encoding_dir,
        telemetry_on=False,
    )
    return float(sol.score)


def _summ(name: str, arr: np.ndarray) -> None:
    p = np.percentile(arr, [0, 5, 25, 50, 75, 95, 100])
    print(
        f"{name}: n={len(arr)}  "
        f"min={p[0]:.6f}  p05={p[1]:.6f}  p25={p[2]:.6f}  "
        f"med={p[3]:.6f}  p75={p[4]:.6f}  p95={p[5]:.6f}  max={p[6]:.6f}"
    )


def _make_solver_stage_a(stop_score: float) -> SolverSpec:
    # NOTE: for permutation keys, beam expand_mode="position" is *very* different from "sample".
    return SolverSpec.hybrid(
        use_beam=True,
        beam_width=32 if FAST_MODE else 64,
        rounds=2 if FAST_MODE else 4,
        expand_mode="position",  # critical: uses position-wise expansion rather than a tiny random neighbourhood
        sample_per_parent=0,     # unused in "position" mode
        top_parents_factor=1.0,  # unused in "position" mode
        stop_score=stop_score,
        progress_pct=10 if FAST_MODE else 5,
        print_progress=True,
        seed=SEED,
        log_interval=10,
        # Keep GA/SA modest for diagnosis
        ga_pop_size=140 if FAST_MODE else 220,
        ga_generations=80 if FAST_MODE else 160,
        ga_elite_frac=0.10,
        ga_cx_frac=0.85,
        ga_mut_prob=0.30,
        ga_tournament_k=3,
        ga_plateau_rounds=999999,
        sa_iters=2000 if FAST_MODE else 6000,
        sa_init_temp=0.90,
        sa_min_temp=0.0001,
        sa_cooling=0.997,
        sa_plateau_rounds=999999,
        local_improve_on_accept=True,
    )


def _make_solver_stage_b(stop_score: float) -> SolverSpec:
    return SolverSpec.hybrid(
        use_beam=True,
        beam_width=32 if FAST_MODE else 64,
        rounds=2 if FAST_MODE else 4,
        expand_mode="sample",   # keep cheaper here; we're just refining
        sample_per_parent=64,
        top_parents_factor=0.4,
        stop_score=stop_score,
        progress_pct=10 if FAST_MODE else 5,
        print_progress=True,
        seed=SEED,
        log_interval=10,
        ga_pop_size=160 if FAST_MODE else 240,
        ga_generations=100 if FAST_MODE else 200,
        ga_elite_frac=0.10,
        ga_cx_frac=0.85,
        ga_mut_prob=0.30,
        ga_tournament_k=3,
        ga_plateau_rounds=999999,
        sa_iters=2500 if FAST_MODE else 8000,
        sa_init_temp=0.90,
        sa_min_temp=0.0001,
        sa_cooling=0.997,
        sa_plateau_rounds=999999,
        local_improve_on_accept=True,
    )


def main() -> None:
    rng = _rng()

    # Text + runes
    rune_text = Runeglish().to_runes(long_plaintext_string.upper(), keep_spaces=True).strip()
    pt_idx = by_name.alphabet("cicada").encode(rune_text)  # int array

    # True keys (same structure as the hard tutorial)
    true_sub_key = by_name.key_generator("periodic_key").random_key(period=PERIOD, seed=SEED)
    true_col_key = _rand_perm(COLUMNS, rng)

    # Full cipher: periodic columnar (col then sub)
    cipher_full = CipherSpec(
        kind="periodic_columnar",
        period=PERIOD,
        columns=COLUMNS,
        order=ORDER,
    )

    # Build ciphertext (full) and intermediate (after undoing substitution only)
    full_key = np.array(true_sub_key + true_col_key, dtype=np.int16)
    cipher_full_inst = cipher_instance(cipher_full)
    ct_idx = cipher_full_inst.encrypt_batch(pt_idx[None, :], full_key[None, :])[0]

    cipher_sub = CipherSpec(kind="periodic_substitution", period=PERIOD)
    cipher_sub_inst = cipher_instance(cipher_sub)
    inter_idx = cipher_sub_inst.undo_batch(
        ct_idx[None, :],
        np.array(true_sub_key, dtype=np.int16)[None, :],
    )[0]

    # Columnar-only cipher for Stage-2 search
    cipher_col = CipherSpec(kind="columnar_transposition", key_length=COLUMNS)
    key_col = KeySpec.permutation(key_length=COLUMNS)

    # Language model data (WLI)
    wli_data = by_name.wli("wli").data()
    encoding_dir = Direction.RTL

    # --- Oracle scores for the *columnar* stage ---
    print("\n--- Oracle sanity check (columnar stage, inter_idx) ---")
    oracle_a = _score_test_key(
        text_idx=inter_idx,
        cipher=cipher_col,
        key=key_col,
        test_key=true_col_key,
        scorer_params=SCORER_STAGE_A,
        wli_data=wli_data,
        encoding_dir=encoding_dir,
    )
    oracle_full = _score_test_key(
        text_idx=inter_idx,
        cipher=cipher_col,
        key=key_col,
        test_key=true_col_key,
        scorer_params=SCORER_FULL,
        wli_data=wli_data,
        encoding_dir=encoding_dir,
    )
    ident = list(range(COLUMNS))
    ident_a = _score_test_key(
        text_idx=inter_idx,
        cipher=cipher_col,
        key=key_col,
        test_key=ident,
        scorer_params=SCORER_STAGE_A,
        wli_data=wli_data,
        encoding_dir=encoding_dir,
    )
    ident_full = _score_test_key(
        text_idx=inter_idx,
        cipher=cipher_col,
        key=key_col,
        test_key=ident,
        scorer_params=SCORER_FULL,
        wli_data=wli_data,
        encoding_dir=encoding_dir,
    )
    print(f" true_col_key: stageA={oracle_a:.6f}  full={oracle_full:.6f}  key={true_col_key}")
    print(f" identity    : stageA={ident_a:.6f}  full={ident_full:.6f}  key={ident}")

    # Suggested stop scores (relative to oracle)
    stop_a = 0.92 * oracle_a
    stop_full = 0.92 * oracle_full
    print(f" suggested stop scores: stageA≈{stop_a:.6f}  full≈{stop_full:.6f}")

    # --- Random-key distributions ---
    print("\n--- Random key score distribution (inter_idx) ---")
    rnd_keys = [_rand_perm(COLUMNS, rng) for _ in range(RANDOM_SAMPLES)]
    scores_a = np.array([
        _score_test_key(text_idx=inter_idx, cipher=cipher_col, key=key_col, test_key=k,
                        scorer_params=SCORER_STAGE_A, wli_data=wli_data, encoding_dir=encoding_dir)
        for k in rnd_keys
    ], dtype=float)
    scores_full = np.array([
        _score_test_key(text_idx=inter_idx, cipher=cipher_col, key=key_col, test_key=k,
                        scorer_params=SCORER_FULL, wli_data=wli_data, encoding_dir=encoding_dir)
        for k in rnd_keys
    ], dtype=float)

    _summ("stageA", scores_a)
    _summ("full  ", scores_full)

    # --- Stage-2 solve, staged ---
    print("\n--- Stage-2 staged solve: (A) then (B) ---")

    solver_a = _make_solver_stage_a(stop_a)
    solver_b = _make_solver_stage_b(stop_full)

    # Solve under stage-A scorer
    sol_a = run(
        text=inter_idx.tolist(),
        cipher=cipher_col,
        key=key_col,
        solver=solver_a,
        scorer_params=SCORER_STAGE_A,
        wli_data=wli_data,
        encoding_dir=encoding_dir,
        telemetry_on=False,
        initial_keys=rnd_keys,
    )
    best_a_key = list(sol_a.key)
    best_a_score = float(sol_a.score)
    print(f"\nstage-A best: score={best_a_score:.6f}  key={best_a_key}  (valid_perm={_is_perm(best_a_key, COLUMNS)})")

    # Refine under full scorer, seeding from stage-A best
    seeds_b = [best_a_key] + [_rand_perm(COLUMNS, rng) for _ in range(16)]
    sol_b = run(
        text=inter_idx.tolist(),
        cipher=cipher_col,
        key=key_col,
        solver=solver_b,
        scorer_params=SCORER_FULL,
        wli_data=wli_data,
        encoding_dir=encoding_dir,
        telemetry_on=False,
        initial_keys=seeds_b,
    )
    best_b_key = list(sol_b.key)
    best_b_score = float(sol_b.score)
    print(f"\nfull best: score={best_b_score:.6f}  key={best_b_key}  (valid_perm={_is_perm(best_b_key, COLUMNS)})")

    # Re-score the returned key explicitly (sanity: solver score == score_test_key)
    check_b = _score_test_key(
        text_idx=inter_idx,
        cipher=cipher_col,
        key=key_col,
        test_key=best_b_key,
        scorer_params=SCORER_FULL,
        wli_data=wli_data,
        encoding_dir=encoding_dir,
    )
    print(f"re-score(full, best_key) = {check_b:.6f}")

    # Compare to oracle
    print("\n--- Outcome ---")
    print(f"oracle(full, true_col_key) = {oracle_full:.6f}")
    print(f"best(full, found_key)      = {best_b_score:.6f}")


if __name__ == "__main__":
    main()
