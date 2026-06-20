from __future__ import annotations

"""
Mono Substitution GA tutorial variant using the standard RDP printer facade.

The original tutorial remains unchanged; this variant proves the printer layer
against the same solve shape.
"""

import sys
from pathlib import Path

# Ensure project root is importable when run as a script.
_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, cipher_instance, print_rdp_result, run
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

START_MODE = "seeded"
RUN_PROFILE = "medium"
STOP_SCORE = 0.55
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345
SCENARIOS = [
    ("RTL telemetry on", Direction.RTL, True),
    ("LTR telemetry off", Direction.LTR, False),
]
_DEF_TITLE = "mono-ga-pretty-print"


def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "..."


def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv


def _build_ciphertext(pt_en: str, *, encoding_direction: Direction = Direction.RTL, seed: int = 42):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=encoding_direction.value)
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)
    ciph = cipher_instance(by_name.cipher("mono"))
    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    key_inv = _invert_perm(key_fwd)
    return ct_idx, ct_runes, wli, key_fwd.tolist(), key_inv.tolist(), pt_idx


def _solve_once(direction: Direction, telemetry_on: bool):
    pt_en = plaintext_english_string
    _ct_idx, ct_runes, wli, _key_fwd, _key_inv, pt_idx = _build_ciphertext(
        pt_en, encoding_direction=direction, seed=CIPHERTEXT_SEED
    )

    if direction == Direction.LTR:
        seed_keys = 240
        seed_swaps = 3
        run_profile = "long"
    else:
        seed_keys = 120
        seed_swaps = 2
        run_profile = RUN_PROFILE

    seeds = None
    if START_MODE == "seeded":
        seeds = make_seeds_from_freq(
            ct_runes.replace(" ", ""),
            n_keys=seed_keys,
            swaps_per_key=seed_swaps,
            seed=TUTORIAL_SEED,
            direction=direction.value,
        )

    if run_profile == "short":
        population, generations = 64, 48
    elif run_profile == "medium":
        population, generations = 96, 96
    elif run_profile == "long":
        population, generations = 144, 160
    else:
        raise ValueError(f"Unknown run_profile: {run_profile!r}")

    scorer_params = dict(
        char_weights={2: 0.3},
        wli_weights={2: 0.7},
        use_word_breaks=True,
        encoding_dir=direction,
    )

    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.50,
        fallback=STOP_SCORE,
    )
    print_stop_summary(f"Mono GA {direction.value}", stop)

    ga = SolverSpec.ga(
        pop_size=population,
        generations=generations,
        stop_score=stop.stop_score,
        verbose=True,
        progress_pct=2,
        print_progress=True,
        elite_frac=0.08,
        cx_frac=0.85,
        mut_prob=0.25,
        tournament_k=4,
        plateau_rounds=20,
        plateau_min_delta=1e-4,
        log_interval=5,
        seed=TUTORIAL_SEED,
    )

    result = run(
        text=ct_runes,
        cipher=by_name.cipher("mono"),
        key=KeySpec.permutation(len=29),
        solver=ga,
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=telemetry_on,
        return_solver_report=True,
        **({} if seeds is None else {"initial_keys": seeds}),
    )

    return result, pt_en, seeds, pt_idx, wli


def main() -> None:
    for label, direction, telemetry_on in SCENARIOS:
        print("=" * 72)
        print(f"{label} (direction={direction.value}, telemetry_on={telemetry_on})")
        result, _pt_en, seeds, pt_idx, _wli = _solve_once(direction, telemetry_on)

        mode_label = "GA (seeded start)" if seeds is not None else "GA (noise start)"
        print(f"Mode: {mode_label}")
        rec = getattr(result.solution, "plaintext_str", "") or getattr(result.solution, "plaintext_rune", "")
        print("Recovered plaintext:", preview(str(rec)))
        print("Score:", round(result.solution.score, 6))

        pipeline = getattr(result.solution, "pipeline", {}) or {}
        print("Pipeline block:", pipeline)
        has_tel = bool(getattr(result.solution, "meta", {}).get("telemetry"))
        print("Telemetry attached:", has_tel)

        print_rdp_result(
            result,
            reference_idx=pt_idx,
            tutorial_entry={
                "path": "Tutorial_MonoSubstitution_GA_PrettyPrint.py",
                "title": f"{_DEF_TITLE}-{direction.value.lower()}",
                "gate": "v1_release_pretty_print",
                "acceptance_kind": "min_match_ratio",
                "min_match_ratio": 0.97,
                "uses_oracle_stop_score": True,
            },
        )


if __name__ == "__main__":
    main()
