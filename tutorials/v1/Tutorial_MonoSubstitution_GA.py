
# -*- coding: utf-8 -*-
"""
Mono Substitution (29 runes) — GA tutorial (friendly version)

What this does
--------------
1) Turn a short English text into runes (one direction, kept consistent).
2) Make ciphertext by encrypting with a random key.
3) EITHER start GA from **noise** OR from **seeded keys** (your choice).
4) GA searches for a key that makes the text look like real language.
5) Stop early if we hit a good score (stop_score).

How to use
---------
• Set START_MODE = "seeded" (fast) or "noise" (pure random start).
• You can also pick a run profile: "short", "medium", "long".
• We keep parameter names the same as your GA solver.
"""
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from pathlib import Path

# Ensure project root is importable when run as a script (so "python Tutorial_*.py" works)
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name, define_map, cipher_instance
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# -------------------------- knobs you can tweak --------------------------
# Default to seeded keys for reproducible convergence
START_MODE = "seeded"
RUN_PROFILE = "medium"
STOP_SCORE = 0.150
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345

# -------------------------- small helpers --------------------------
def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "…"

def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv

def _build_ciphertext(pt_en: str, *, encoding_direction: Direction = Direction.RTL, seed: int = 42):
    """
    1) English -> rune indices
    2) Random pt->ct permutation
    3) Encrypt using the cipher's API
    4) Return ciphertext as runes (with spaces) and WLI metadata
    """
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=encoding_direction.value)
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)           # pt->ct
    ciph = cipher_instance(by_name.cipher("mono"))
    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    key_inv = _invert_perm(key_fwd)                          # ct->pt
    return ct_idx, ct_runes, wli, key_fwd.tolist(), key_inv.tolist(), pt_idx

# -------------------------- main tutorial --------------------------
SCENARIOS = [
    ("RTL telemetry on", Direction.RTL, True),
    ("LTR telemetry off", Direction.LTR, False),
]


_DEF_TITLE = "mono-ga-friendly"


def _solve_once(direction: Direction, telemetry_on: bool):
    pt_en = plaintext_english_string
    ct_idx, ct_runes, wli, _key_fwd, _key_inv, pt_idx = _build_ciphertext(
        pt_en, encoding_direction=direction, seed=CIPHERTEXT_SEED
    )

    seeds = None
    if START_MODE == "seeded":
        seeds = make_seeds_from_freq(
            ct_runes.replace(" ", ""),
            n_keys=120,
            swaps_per_key=2,
            seed=TUTORIAL_SEED,
            direction=direction.value,
        )

    if RUN_PROFILE == "short":
        population, generations = 64, 48
    elif RUN_PROFILE == "medium":
        population, generations = 96, 96
    elif RUN_PROFILE == "long":
        population, generations = 144, 160
    else:
        raise ValueError(f"Unknown RUN_PROFILE: {RUN_PROFILE!r}")

    ga = SolverSpec.ga(
        pop_size=population,
        generations=generations,
        stop_score=STOP_SCORE,
        verbose=True,
        progress_pct=2,
        print_progress=True,
        elite_frac=0.08,
        cx_frac=0.85,
        mut_prob=0.25,
        tournament_k=4,
        plateau_gens=20,
        log_interval=5,
        seed=TUTORIAL_SEED,
    )

    sol = run(
        text=ct_runes,
        cipher=by_name.cipher("mono"),
        key=KeySpec.permutation(len=29),
        solver=ga,
        scorer_params=dict(
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            use_word_breaks=True,
            encoding_dir=direction,
        ),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=telemetry_on,
        **({} if seeds is None else {"initial_keys": seeds}),
    )

    return sol, pt_en, seeds, pt_idx, wli


def main():
    for label, direction, telemetry_on in SCENARIOS:
        print("=" * 72)
        print(f"{label} (direction={direction.value}, telemetry_on={telemetry_on})")
        sol, pt_en, seeds, pt_idx, wli = _solve_once(direction, telemetry_on)

        mode_label = "GA (seeded start)" if seeds is not None else "GA (noise start)"
        print(f"Mode: {mode_label}")
        rec = getattr(sol, "plaintext_str", "") or getattr(sol, "plaintext_rune", "")
        print("Recovered plaintext:", preview(str(rec)))
        print("Score:", round(sol.score, 6))

        pipeline = getattr(sol, "pipeline", {}) or {}
        print("Pipeline block:", pipeline)
        has_tel = bool(getattr(sol, "meta", {}).get("telemetry"))
        print("Telemetry attached:", has_tel)

        pt_ref = Runeglish.to_rune(list(pt_idx), wli)
        print_run_report(
            title=f"{_DEF_TITLE}-{direction.value.lower()}",
            cipher="mono",
            solution=sol,
            match_ok=None,
            app_version="tutorial-1.3",
            pt_rune_ref=pt_ref,
            pt_idx_ref=pt_idx,
        )


if __name__ == "__main__":
    main()
