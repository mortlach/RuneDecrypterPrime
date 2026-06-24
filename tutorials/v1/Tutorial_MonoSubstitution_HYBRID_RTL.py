from __future__ import annotations

"""Mono-substitution HYBRID pretty-print tutorial for RTL rune encoding."""

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
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DIRECTION = Direction.RTL
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345
MIN_MATCH_RATIO = 0.995


def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "..."


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
    print("Mono-substitution HYBRID problem")
    print(f"encoding direction: {DIRECTION.value}")
    print("solver path: Beam warm-start -> GA explore -> SA polish")
    print("start condition: no true-key seed supplied")
    print(f"ciphertext length: {len(ct_idx)}")
    print(f"ciphertext preview: {preview(ct_runes, 160)}")
    print_tutorial_debug_preview(label="plaintext", idx=pt_idx, wli=wli, direction=DIRECTION)
    print_tutorial_debug_preview(label="ciphertext", idx=ct_idx_list, wli=wli, direction=DIRECTION)

    scorer_params = dict(
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
    print_stop_summary("Mono Hybrid", stop)

    solver = SolverSpec.hybrid(
        use_beam=True,
        beam_width=12,
        rounds=6,
        expand_mode="sample",
        sample_per_parent=16,
        top_parents_factor=0.5,
        progress_pct=2,
        print_progress=True,
        progress_preview_chars=120,
        ga=dict(
            pop_size=60,
            generations=15,
            elite_frac=0.08,
            cx_frac=0.85,
            mut_prob=0.35,
            tournament_k=3,
            plateau_rounds=8,
            plateau_min_delta=1e-4,
            stop_score=stop.stop_score,
            print_progress=True,
            progress_preview_chars=120,
        ),
        sa=dict(
            sa_iters=1500,
            sa_init_temp=0.8,
            sa_min_temp=1e-3,
            sa_auto_cooling=True,
            sa_cooling=0.996,
            sa_reseed_interval=2000,
            sa_rescue_drop_abs=0.02,
            sa_rescue_drop_ratio=0.5,
            local_improve_on_accept=False,
            plateau_rounds=80,
            plateau_min_delta=1e-4,
            stop_score=stop.stop_score,
            print_progress=True,
            progress_preview_chars=120,
        ),
        seed=TUTORIAL_SEED,
        verbose=True,
        log_interval=10,
        plateau_rounds=8,
        plateau_min_delta=1e-4,
        stop_score=stop.stop_score,
    )
    cipher_spec = by_name.cipher("mono")
    key_spec = KeySpec.permutation(len=29)
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
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=DIRECTION,
        telemetry_on=True,
        return_solver_report=True,
    )

    recovered = getattr(result.solution, "plaintext_rune", "") or getattr(result.solution, "plaintext_str", "")
    print("Recovered plaintext:", preview(str(recovered)))
    print("Score:", round(result.solution.score, 6))

    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_MonoSubstitution_HYBRID_RTL.py",
            "title": "Mono-substitution HYBRID RTL pretty-print variant",
            "gate": "v1_extended_pretty_print",
            "acceptance_kind": "near_exact",
            "min_match_ratio": MIN_MATCH_RATIO,
            "uses_oracle_stop_score": True,
        },
    )


if __name__ == "__main__":
    main()
