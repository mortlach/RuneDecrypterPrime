"""
Tutorial: Periodic Columnar (simple, period=7, order=col_then_sub)

Goal: actually solve, reliably, with a clean staged workflow.

Why staged?
- Columnar transposition destroys local n-grams early, so WLI/word-break scoring is hostile.
- But unigram frequency survives transposition, so solve periodic substitution first with char n=1.
- Then solve the 7-column permutation (7! = 5040) by brute force with LMPrime char 3/4.
- Finally, polish with the full Kaeding solver + full scorer.

This is intentionally "no-bloat": the scoring model is chosen to match what is identifiable at each stage.
"""
from __future__ import annotations

import sys
from itertools import permutations
from pathlib import Path
from typing import Sequence

import numpy as np

_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name, cipher_instance
from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.seed_utils import make_periodic_substitution_seed_pool_unigram_freq

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ALPHABET = 29
PERIOD = 7
COLUMNS = 7
ORDER = "col_then_sub"

TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 54321

# Stage 1 (periodic substitution) – give it proper compute
SUB_STEPS = 9000
SUB_RESTARTS = 5
SUB_INNER_BATCH = 256

# Stage 2 (columnar) – brute force all 7! tails, keep top-N candidates
TAIL_KEEP_TOP = 24  # feed multiple strong tails into the final polish

# Stage 3 (full periodic_columnar polish)
FULL_STEPS = 20000
FULL_RESTARTS = 4
FULL_INNER_BATCH = 256
FULL_COL_EVERY = 1
FULL_COL_BATCH = 256
FULL_SLIP_EVERY = 80
FULL_SLIP_BLOCKS = 1
FULL_STALL_ROUNDS = 220
FULL_STALL_SLIP_LIMIT = 4
FULL_SLIP_SWAPS = 50


def _preview(text: str, n: int = 120) -> str:
    return text if len(text) <= n else text[:n] + "..."


def _match_ratio(solution, pt_idx: Sequence[int]) -> float:
    guess = getattr(solution, "plaintext_idx", None)
    if guess is None:
        return 0.0
    a = np.asarray(guess, dtype=np.int64).reshape(-1)
    b = np.asarray(pt_idx, dtype=np.int64).reshape(-1)
    n = min(a.size, b.size)
    return float(np.mean(a[:n] == b[:n])) if n > 0 else 0.0


def main() -> None:
    encoding_dir = Direction.RTL

    # ---------- Plaintext ----------
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        plaintext_english_string,
        direction=encoding_dir.value,
    )
    pt_arr = np.asarray(pt_idx, dtype=np.uint8)
    print("Plaintext preview:", _preview(pt_runes))

    # ---------- Full cipher (for encryption + final polish) ----------
    cipher_full_spec = by_name.cipher(
        "periodic_columnar",
        period=PERIOD,
        alphabet_size=ALPHABET,
        columns=COLUMNS,
        order=ORDER,
    )
    key_full_spec = KeySpec.periodic_columnar(
        period=PERIOD,
        alphabet_size=ALPHABET,
        columns=COLUMNS,
    )
    cipher_full = cipher_instance(cipher_full_spec)

    # Random true key + ciphertext
    rng_key = np.random.default_rng(CIPHERTEXT_SEED)
    true_key = rng_key.permutation(PERIOD * ALPHABET + COLUMNS).astype(np.uint8, copy=False)  # deterministic “some” key
    # NOTE: for true periodic-columnar semantics you normally want PeriodicStructuredMatrixKeyOps.random().
    # If you already have that in your repo/tutorial harness, swap it back in.
    ct_idx = cipher_full.encrypt_single(plaintext=pt_arr, key=true_key)

    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    print("=" * 72)
    print(f"Scenario: simple (period={PERIOD}, columns={COLUMNS}, order={ORDER})")
    print("Ciphertext preview:", _preview(ct_runes))

    # ---------- Stage 1: Solve periodic substitution only ----------
    # For col_then_sub, substitution is applied last, so we can strip it first.
    cipher_sub_spec = by_name.cipher(
        "periodic_substitution",
        period=PERIOD,
        alphabet_size=ALPHABET,
    )
    key_sub_spec = KeySpec.periodic_substitution(
        period=PERIOD,
        alphabet_size=ALPHABET,
    )
    cipher_sub = cipher_instance(cipher_sub_spec)

    # Unigram-only scorer (transposition-safe)
    scorer_params_sub = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=False,
        char_weights={1: 1.0},
        wli_weights={},
        encoding_dir=encoding_dir,
    )

    stop_sub = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params_sub,
        device="cpu",
        encoding_dir=encoding_dir,
        margin=0.03,
        min_score=0.40,
        fallback=0.45,
    )
    print_stop_summary("Stage 1 (periodic substitution, unigram)", stop_sub)

    sub_seed_keys = make_periodic_substitution_seed_pool_unigram_freq(
        ct_idx,
        period=PERIOD,
        alphabet_size=ALPHABET,
        direction=encoding_dir,
        seed=TUTORIAL_SEED,
        n_keys=64,
        top_k=18,
        jitter_swaps=6,
        random_frac=0.20,
    )

    solver_sub = SolverSpec.kaeding(
        steps=SUB_STEPS,
        restarts=SUB_RESTARTS,
        inner_batch=SUB_INNER_BATCH,
        slip_every=0,
        slip_blocks=1,
        slip_policy="stall",
        stall_rounds=250,
        stall_slip_limit=3,
        slip_swaps=24,
        stall_stop_on_limit=True,
        block_schedule="round_robin",
        col_every=0,
        col_batch=0,
        plateau_rounds=max(10, int(SUB_STEPS * 0.12)),
        plateau_min_delta=1e-4,
        stop_score=stop_sub.stop_score,
        progress_pct=2,
        print_progress=True,
        seed=TUTORIAL_SEED,
    )

    sol_sub = run(
        text=ct_idx.tolist(),
        cipher=cipher_sub_spec,
        key=key_sub_spec,
        solver=solver_sub,
        scorer_params=dict(scorer_params_sub),
        wli_data=wli,
        encoding_dir=encoding_dir,
        telemetry_on=True,
        initial_keys=sub_seed_keys,
    )
    best_sub_key = list(getattr(sol_sub, "key", []))
    if not best_sub_key:
        raise RuntimeError("Stage 1 failed: no substitution key returned")

    inter_idx = cipher_sub.decrypt_single(ciphertext=ct_idx, key=np.asarray(best_sub_key, dtype=np.uint8))
    print("Stage 1 inter preview:", _preview(Runeglish.to_rune(inter_idx.tolist(), wli)))

    # ---------- Stage 2: Solve 7-column permutation by brute force (5040 perms) ----------
    cipher_col_spec = by_name.cipher("columnar", key_length=COLUMNS)
    key_col_spec = KeySpec.permutation(len=COLUMNS)
    cipher_col = cipher_instance(cipher_col_spec)

    lm = LanguageModelPrime(lm_root=None, smoothing=None, oov_policy=None, include_char=True)

    def score_char34(pt_u8: np.ndarray) -> float:
        seq = np.asarray(pt_u8, dtype=np.uint8).reshape(-1).tolist()
        n = max(1, len(seq))
        s3 = lm.score([seq], None, direction=encoding_dir.value, se="nose", n=3, model="char")[0].logprob_sum / n
        s4 = lm.score([seq], None, direction=encoding_dir.value, se="nose", n=4, model="char")[0].logprob_sum / n
        return float(0.5 * s3 + 0.5 * s4)

    tail_ranked: list[tuple[float, list[int]]] = []
    for perm in permutations(range(COLUMNS)):
        col_key = list(perm)
        pt_guess = cipher_col.decrypt_single(ciphertext=inter_idx, key=np.asarray(col_key, dtype=np.uint8))
        s = score_char34(pt_guess)
        tail_ranked.append((s, col_key))

    tail_ranked.sort(key=lambda t: t[0], reverse=True)
    top = tail_ranked[: max(1, int(TAIL_KEEP_TOP))]

    print(f"Stage 2: best tail scores (char34), top {len(top)}")
    for i, (s, k) in enumerate(top[:8], start=1):
        print(f"  #{i:02d} score={s:.6f} tail={k}")

    initial_full_keys = [best_sub_key + k for (_s, k) in top]

    # ---------- Stage 3: Full polish under the real scorer ----------
    scorer_params_full = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={3: 0.3, 4: 0.7},
        wli_weights={3: 0.4, 4: 0.6},
        encoding_dir=encoding_dir,
    )
    stop_full = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params_full,
        device="cpu",
        encoding_dir=encoding_dir,
        margin=0.02,
        min_score=0.50,
        fallback=0.55,
    )
    print_stop_summary("Stage 3 (full periodic_columnar polish)", stop_full)

    solver_full = SolverSpec.kaeding(
        steps=FULL_STEPS,
        restarts=FULL_RESTARTS,
        inner_batch=FULL_INNER_BATCH,
        slip_every=FULL_SLIP_EVERY,
        slip_blocks=FULL_SLIP_BLOCKS,
        col_every=FULL_COL_EVERY,
        col_batch=FULL_COL_BATCH,
        block_schedule="round_robin",
        plateau_rounds=max(10, int(FULL_STEPS * 0.10)),
        plateau_min_delta=1e-4,
        stop_score=stop_full.stop_score,
        progress_pct=2,
        print_progress=True,
        seed=TUTORIAL_SEED,
        slip_policy="stall",
        stall_rounds=FULL_STALL_ROUNDS,
        stall_slip_limit=FULL_STALL_SLIP_LIMIT,
        slip_swaps=FULL_SLIP_SWAPS,
        stall_stop_on_limit=False,
    )

    sol = run(
        text=ct_idx.tolist(),
        cipher=cipher_full_spec,
        key=key_full_spec,
        solver=solver_full,
        scorer_params=dict(scorer_params_full),
        wli_data=wli,
        encoding_dir=encoding_dir,
        telemetry_on=True,
        initial_keys=initial_full_keys,
    )

    recovered = getattr(sol, "plaintext_rune", "") or getattr(sol, "plaintext_str", "")
    print("Recovered preview:", _preview(str(recovered)))

    ratio = _match_ratio(sol, pt_idx)
    match_ok = ratio >= 0.999

    print_run_report(
        title="periodic-columnar-simple-p7-col-then-sub",
        cipher="periodic_columnar",
        solution=sol,
        match_ok=match_ok,
        app_version="tutorial-1.0",
        key_idx=list(true_key.tolist()) if hasattr(true_key, "tolist") else list(true_key),
        key_len=int(len(true_key)),
        ct_idx=ct_idx.tolist(),
        ct_rune=ct_runes,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
        wli=wli,
    )

    if not match_ok:
        raise RuntimeError(f"Solve failed: match_ratio={ratio:.4f}")


if __name__ == "__main__":
    main()
