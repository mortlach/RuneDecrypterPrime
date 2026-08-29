from __future__ import annotations
from rdp import api

"Mono-substitution SA pretty-print tutorial for LTR rune encoding."
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
import numpy as np
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq
from rune_decrypter_prime.utils.tutorial_utils import (
    oracle_stop_score,
    print_stop_summary,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
DIRECTION = api.TextDirection.LEFT_TO_RIGHT
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345
MIN_MATCH_RATIO = 0.995


def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "..."


def _match_ratio(solution, pt_idx: list[int]) -> float:
    guess = solution.plaintext or None
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
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction="ltr")
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)
    ciph = api.CipherSpec.substitution(alphabet_size=29)
    ct_idx = api.encrypt(
        tuple(int(value) for value in pt_idx),
        cipher=ciph,
        key=tuple(int(value) for value in key_fwd),
    )
    ct_runes = Runeglish.to_rune(list(ct_idx), wli)
    key_inv = _invert_perm(key_fwd)
    return (
        [int(v) for v in list(ct_idx)],
        ct_runes,
        wli,
        key_fwd.tolist(),
        key_inv.tolist(),
        pt_idx,
    )


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Mono-substitution simulated annealing LTR",
        cipher="mono substitution",
        solver="simulated annealing",
        direction="ltr",
        expected_result="near-exact solve",
        uses_reference_stop_score=True,
    )
    ct_idx, ct_runes, wli, _key_fwd, _key_inv, pt_idx = _build_ciphertext(
        plaintext_english_string, seed=CIPHERTEXT_SEED
    )
    print("Mono-substitution SA problem")
    print(f"encoding direction: {DIRECTION.value}")
    print("solver path: simulated annealing with frequency-derived starting seeds")
    print(f"ciphertext length: {len(ct_idx)}")
    print(f"ciphertext preview: {preview(ct_runes, 160)}")
    print_tutorial_debug_preview(
        label="plaintext", idx=pt_idx, wli=wli, direction=DIRECTION
    )
    print_tutorial_debug_preview(
        label="ciphertext", idx=ct_idx, wli=wli, direction=DIRECTION
    )
    seeds = make_seeds_from_freq(
        ct_runes.replace(" ", ""),
        n_keys=120,
        swaps_per_key=1,
        seed=TUTORIAL_SEED,
        direction="ltr",
    )
    print(f"seeded starts: {len(seeds)}")
    scorer_params = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )
    display_scorer_params = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )
    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=DIRECTION,
        margin=0.02,
        min_score=0.5,
        fallback=0.55,
    )
    print_stop_summary("Mono SA", stop)
    cipher_spec = api.CipherSpec.substitution(alphabet_size=29)
    key_spec = api.KeySpec.permutation(length=29)

    def _solve_with_sa(solver: api.SolverSpec):
        display_spec = api.RunSpec(
            problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli),
            cipher=cipher_spec,
            key_space=key_spec,
            solver=solver,
            scoring=display_scorer_params,
            text_direction=DIRECTION,
            telemetry_enabled=True,
        )
        result = api.run(
            api.RunSpec(
                problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli),
                cipher=cipher_spec,
                key_space=key_spec,
                solver=solver,
                scoring=scorer_params,
                initial_keys=tuple(tuple(int(value) for value in key) for key in seeds),
                telemetry_enabled=True,
                text_direction=DIRECTION,
                compute_device=api.ComputeDevice.CPU,
            )
        )
        return (result, display_spec)

    solver_spec = api.SolverSpec.simulated_annealing(
        iterations=9000,
        initial_temperature=1.0,
        minimum_temperature=0.0001,
        cooling_rate=0.999,
        automatic_cooling=True,
        reseed_interval=250,
        local_improvement_on_accept=True,
        rescue_drop_absolute=0.01,
        rescue_drop_ratio=0.5,
        plateau_iterations=250,
        plateau_minimum_delta=1e-06,
        target_score=stop.stop_score,
        seed=TUTORIAL_SEED,
    )
    result, display_spec = _solve_with_sa(solver_spec)
    recovered = (result.plaintext_text or "") or (result.plaintext_text or "")
    print("Recovered plaintext:", preview(str(recovered)))
    print("Score:", round(result.score, 6))
    pretty.print_summary_spacer()
    api.display.print_result(
        result, spec=display_spec, options=api.display.SummaryOptions.for_tutorial()
    )


if __name__ == "__main__":
    main()
