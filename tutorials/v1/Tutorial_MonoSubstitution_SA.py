"""
Mono Substitution (29 runes) - SA walkthrough

What you'll see
---------------
1) English -> runes (one direction, kept consistent).
2) Random key -> encrypt -> ciphertext.
3) Simple frequency-based seed guesses (optional but helpful).
4) Simulated Annealing (SA) recovers readable plaintext.
5) A short report at the end.

You can tweak the SA knobs below.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

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

TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345


def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "..."


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


def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:

    inv = np.empty_like(pt_to_ct)

    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)

    return inv





def _build_ciphertext(pt_en: str, *, encoding_direction: Direction, seed: int = 42):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=encoding_direction.value)
    rng = np.random.default_rng(seed)

    key_fwd = rng.permutation(29).astype(np.uint8)

    ciph = cipher_instance(by_name.cipher("mono"))

    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)

    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)

    key_inv = _invert_perm(key_fwd)

    return ct_idx, ct_runes, wli, key_fwd.tolist(), key_inv.tolist(), pt_idx




def main():

    encoding_direction = Direction.LTR


    # 1) English ... ciphertext

    pt_en = plaintext_english_string

    ct_idx, ct_runes, wli, _key_fwd, _key_inv, pt_idx = _build_ciphertext(
        pt_en, encoding_direction=encoding_direction, seed=CIPHERTEXT_SEED
    )


    # 2) Simple seeds from ciphertext (comment out to start from pure noise)

    seeds = make_seeds_from_freq(
        ct_runes.replace(" ", ""),
        n_keys=120,
        swaps_per_key=1,
        seed=TUTORIAL_SEED,
        direction=encoding_direction.value,
    )

    scorer_params = dict(
        objective="pct.logp.win10",
        char_weights={2: 0.3},
        wli_weights={2: 0.7},
        include_char=True,
        use_word_breaks=True,
        encoding_dir=encoding_direction,
    )

    def _solve_with_sa(sa_kwargs: dict) -> object:
        sa = SolverSpec.sa(**sa_kwargs)
        return run(
            text=ct_runes,
            cipher=by_name.cipher("mono"),
            key=KeySpec.permutation(len=29),
            solver=sa,
            device="cpu",
            scorer="rune",
            scorer_params=dict(scorer_params),
            wli_data=wli,
            initial_keys=seeds,
            encoding_dir=encoding_direction,
            telemetry_on=True,
        )

    sa_base = dict(
        sa_iters=3500,
        sa_init_temp=1.0,
        sa_min_temp=1e-4,
        sa_cooling=0.999,
        sa_auto_cooling=True,
        sa_reseed_interval=400,
        sa_rescue_drop_abs=0.02,
        sa_rescue_drop_ratio=0.5,
        local_improve_on_accept=True,
        log_interval=250,

        plateau_rounds=120,
        plateau_min_delta=1e-4,
        stop_score=0.55,
        progress_pct=2,
        print_progress=True,
        verbose=True,
        seed=TUTORIAL_SEED,
        tol=1e-6,
    )


    # 4) Run solver

    sol = _solve_with_sa(sa_base)
    if _match_ratio(sol, pt_idx) < 0.999:
        print("Retrying with stronger SA settings...")
        sa_retry = dict(sa_base)
        sa_retry.update(
            sa_iters=9000,
            sa_reseed_interval=250,
            sa_rescue_drop_abs=0.01,
            plateau_rounds=250,
            plateau_min_delta=1e-6,
        )
        sol = _solve_with_sa(sa_retry)


    # 5) Report

    print("-" * 72)

    print("Mono Substitution - SA")

    recovered = getattr(sol, "plaintext_rune", "") or getattr(sol, "plaintext_str", "")

    print("Recovered plaintext:", preview(str(recovered)))
    print("Score:", round(sol.score, 6))
    # Keep reference for pretty printer (auto match ratio)
    pt_ref = Runeglish.to_rune(list(pt_idx), wli)

    print_run_report(
        title="mono-sa",
        cipher="mono",
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.2",
        pt_rune_ref=pt_ref,
        pt_idx_ref=pt_idx,
    )


if __name__ == "__main__":

    main()





