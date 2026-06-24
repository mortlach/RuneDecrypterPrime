from __future__ import annotations

"""Mono-substitution GA pretty-print tutorial for RTL rune encoding.

This is an independently generated RTL-encoded mono-substitution example. It is
not the same ciphertext as the LTR tutorial solved under a different assumption.
The purpose is to show that RDP can solve this cipher shape in RTL rune encoding
while preserving the standard printer/report contract.
"""

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
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DIRECTION = Direction.RTL
START_MODE = "seeded"
STOP_SCORE = 0.55
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345
SEED_KEYS = 120
SEED_SWAPS = 2
POPULATION = 96
GENERATIONS = 96
MIN_MATCH_RATIO = 0.97
TUTORIAL_PATH = "Tutorial_MonoSubstitution_GA_RTL.py"
TUTORIAL_TITLE = "Mono-substitution GA RTL pretty-print variant"


def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "..."


def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv


def _build_ciphertext(pt_en: str, *, encoding_direction: Direction, seed: int):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=encoding_direction.value)
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)
    ciph = cipher_instance(by_name.cipher("mono"))
    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    key_inv = _invert_perm(key_fwd)
    return ct_idx, ct_runes, wli, key_fwd.tolist(), key_inv.tolist(), pt_idx


def main() -> None:
    pt_en = plaintext_english_string
    ct_idx, ct_runes, wli, _key_fwd, _key_inv, pt_idx = _build_ciphertext(
        pt_en,
        encoding_direction=DIRECTION,
        seed=CIPHERTEXT_SEED,
    )
    ct_idx_list = [int(v) for v in ct_idx.tolist()]

    print("Mono-substitution GA problem")
    print(f"encoding direction: {DIRECTION.value}")
    print("example relation: independent generated RTL ciphertext, not paired with the LTR tutorial")
    print(f"ciphertext length: {len(ct_idx_list)}")
    print(f"ciphertext preview: {preview(ct_runes, 160)}")
    print_tutorial_debug_preview(label="plaintext", idx=pt_idx, wli=wli, direction=DIRECTION)
    print_tutorial_debug_preview(label="ciphertext", idx=ct_idx_list, wli=wli, direction=DIRECTION)

    seeds = None
    if START_MODE == "seeded":
        seeds = make_seeds_from_freq(
            ct_runes.replace(" ", ""),
            n_keys=SEED_KEYS,
            swaps_per_key=SEED_SWAPS,
            seed=TUTORIAL_SEED,
            direction=DIRECTION.value,
        )

    print(f"seeded starts: {0 if seeds is None else len(seeds)}")
    print(f"GA population: {POPULATION}")
    print(f"GA generations: {GENERATIONS}")

    scorer_params = dict(
        char_weights={2: 0.3},
        wli_weights={2: 0.7},
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
        fallback=STOP_SCORE,
    )
    print_stop_summary(f"Mono GA {DIRECTION.value}", stop)

    solver = SolverSpec.ga(
        pop_size=POPULATION,
        generations=GENERATIONS,
        stop_score=stop.stop_score,
        verbose=True,
        progress_pct=2,
        print_progress=True,
        progress_preview_chars=120,
        elite_frac=0.08,
        cx_frac=0.85,
        mut_prob=0.25,
        tournament_k=4,
        plateau_rounds=20,
        plateau_min_delta=1e-4,
        log_interval=5,
        seed=TUTORIAL_SEED,
    )
    key_spec = KeySpec.permutation(len=29)
    cipher_spec = by_name.cipher("mono")
    display_spec = RunSpec(
        problem_input=NormalizedInput(ct_idx=ct_idx_list, wli=wli),
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
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=DIRECTION,
        telemetry_on=True,
        return_solver_report=True,
        **({} if seeds is None else {"initial_keys": seeds}),
    )

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
        spec=display_spec,
        reference_idx=pt_idx,
        tutorial_entry={
            "path": TUTORIAL_PATH,
            "title": TUTORIAL_TITLE,
            "gate": "v1_release_pretty_print",
            "acceptance_kind": "human_readable",
            "min_match_ratio": MIN_MATCH_RATIO,
            "uses_oracle_stop_score": True,
        },
    )


if __name__ == "__main__":
    main()
