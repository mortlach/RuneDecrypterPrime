from __future__ import annotations

"""Mono-substitution SA pretty-print tutorial for LTR rune encoding."""

import sys
from pathlib import Path

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

DIRECTION = Direction.LTR
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345
MIN_MATCH_RATIO = 0.995


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


def _build_ciphertext(pt_en: str, *, seed: int):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=DIRECTION.value)
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)
    ciph = cipher_instance(by_name.cipher("mono"))
    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    key_inv = _invert_perm(key_fwd)
    return [int(v) for v in ct_idx.tolist()], ct_runes, wli, key_fwd.tolist(), key_inv.tolist(), pt_idx


def main() -> None:
    ct_idx, ct_runes, wli, _key_fwd, _key_inv, pt_idx = _build_ciphertext(
        plaintext_english_string,
        seed=CIPHERTEXT_SEED,
    )
    print("Mono-substitution SA problem")
    print(f"encoding direction: {DIRECTION.value}")
    print("solver path: simulated annealing with frequency-derived starting seeds")
    print(f"ciphertext length: {len(ct_idx)}")
    print(f"ciphertext preview: {preview(ct_runes, 160)}")

    seeds = make_seeds_from_freq(
        ct_runes.replace(" ", ""),
        n_keys=120,
        swaps_per_key=1,
        seed=TUTORIAL_SEED,
        direction=DIRECTION.value,
    )
    print(f"seeded starts: {len(seeds)}")

    scorer_params = dict(
        objective="pct.logp.win10",
        char_weights={2: 0.3},
        wli_weights={2: 0.7},
        include_char=True,
        use_word_breaks=True,
        encoding_dir=DIRECTION,
    )
    display_scorer_params = {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "encoding_dir": DIRECTION.value,
        "char_order_2_weight": 0.3,
        "wli_order_2_weight": 0.7,
    }

    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=DIRECTION,
        margin=0.02,
        min_score=0.50,
        fallback=0.55,
    )
    print_stop_summary("Mono SA", stop)

    cipher_spec = by_name.cipher("mono")
    key_spec = KeySpec.permutation(len=29)

    def _solve_with_sa(sa_kwargs: dict):
        solver = SolverSpec.sa(**sa_kwargs)
        display_spec = RunSpec(
            problem_input=NormalizedInput(ct_idx=ct_idx, wli=wli),
            cipher=cipher_spec,
            key=key_spec,
            solver=solver,
            scorer="rune",
            scorer_params=display_scorer_params,
            encoding_dir=DIRECTION,
            telemetry_on=True,
        )
        result = run(
            text=ct_runes,
            cipher=cipher_spec,
            key=key_spec,
            solver=solver,
            device="cpu",
            scorer="rune",
            scorer_params=dict(scorer_params),
            wli_data=wli,
            initial_keys=seeds,
            encoding_dir=DIRECTION,
            telemetry_on=True,
            return_solver_report=True,
        )
        return result, display_spec

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
        stop_score=stop.stop_score,
        progress_pct=2,
        print_progress=True,
        verbose=True,
        seed=TUTORIAL_SEED,
        tol=1e-6,
    )

    result, display_spec = _solve_with_sa(sa_base)
    if _match_ratio(result.solution, pt_idx) < 0.999:
        print("Retrying with stronger SA settings...")
        sa_retry = dict(sa_base)
        sa_retry.update(
            sa_iters=9000,
            sa_reseed_interval=250,
            sa_rescue_drop_abs=0.01,
            plateau_rounds=250,
            plateau_min_delta=1e-6,
        )
        result, display_spec = _solve_with_sa(sa_retry)

    recovered = getattr(result.solution, "plaintext_rune", "") or getattr(result.solution, "plaintext_str", "")
    print("Recovered plaintext:", preview(str(recovered)))
    print("Score:", round(result.solution.score, 6))

    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_MonoSubstitution_SA_LTR_PrettyPrint.py",
            "title": "Mono-substitution SA LTR pretty-print variant",
            "gate": "v1_slow_demo_pretty_print",
            "acceptance_kind": "min_match_ratio",
            "min_match_ratio": MIN_MATCH_RATIO,
            "uses_oracle_stop_score": True,
        },
    )


if __name__ == "__main__":
    main()
