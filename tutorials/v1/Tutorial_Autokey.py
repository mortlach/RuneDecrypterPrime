from __future__ import annotations

"""Autokey pretty-print tutorial.

This variant keeps the original tutorial's teaching shape: first a no-crib GA
solve, then a crib-assisted GA solve. It prints compact problem context, solver
calibration/progress, and a standard RDP summary for each solve.
"""

import sys
from pathlib import Path
from typing import List, Sequence

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, NormalizedInput, RunSpec, SolverSpec, by_name, cipher_instance, print_rdp_result, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SEED = [6, 1, 4]
SEED_LEN = len(SEED)
ALPHABET_SIZE = 29
MATCH_THRESHOLD = 1.0
CRIB_TEXT = "WHITE RABBIT"
TUTORIAL_SEED_BASELINE = 2024
TUTORIAL_SEED_CRIB = 4242


def _match_ratio(found: Sequence[int], reference: Sequence[int]) -> float:
    n = min(len(found), len(reference))
    if n == 0:
        return 0.0
    matches = sum(1 for i in range(n) if int(found[i]) == int(reference[i]))
    return matches / float(n)


def _preview_text(label: str, value: str, *, limit: int = 160) -> None:
    suffix = "..." if len(value) > limit else ""
    print(f"{label} length: {len(value)}")
    print(f"{label} preview: {value[:limit]}{suffix}")


def _crib_seeds_from_prefix(
    ct_idx: Sequence[int],
    crib_text: str,
    *,
    direction: Direction,
    seed_len: int,
    alphabet: int,
) -> List[List[int]]:
    crib_idx, _, _ = Runeglish.encode_english_to_runes(crib_text, direction=direction.value)
    crib_idx = [int(v) for v in crib_idx if v >= 0]
    if len(crib_idx) < seed_len or len(ct_idx) < seed_len:
        return []

    base = [int((int(ct_idx[i]) - crib_idx[i]) % alphabet) for i in range(seed_len)]
    seeds: List[List[int]] = [base]
    for delta in (-1, 1):
        seeds.append([(val + delta) % alphabet for val in base])
    return seeds


def main() -> None:
    direction = Direction.RTL
    plaintext = (
        "WHEN THE WHITE RABBIT READ THESE WORDS HE SEEMED SUDDENLY ALARMED "
        "FOR A SHOWER OF LITTLE GLASS BOXES CAME TUMBLING UPON HIM"
    )
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(plaintext, direction=direction.value)
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)

    autokey_cipher = cipher_instance(by_name.cipher("autokey", seed_len=SEED_LEN, alphabet_size=ALPHABET_SIZE))
    seed_arr = np.asarray(SEED, dtype=np.uint8)
    ct_idx = autokey_cipher.encrypt_single(plaintext=pt_idx_arr, key=seed_arr)
    ct_idx_list = [int(v) for v in ct_idx.tolist()]
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)

    print("Autokey problem")
    print(f"encoding direction: {direction.value}")
    print(f"seed length: {SEED_LEN}")
    print(f"crib text used only for second run: {CRIB_TEXT}")
    _preview_text("plaintext runes", pt_runes)
    _preview_text("ciphertext runes", ct_runes)

    cipher_spec = by_name.cipher("autokey", seed_len=SEED_LEN, alphabet_size=ALPHABET_SIZE)
    key_spec = KeySpec.repeat(len=SEED_LEN)
    scorer_params = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={2: 0.3},
        wli_weights={2: 0.7},
        encoding_dir=direction,
    )
    display_scorer_params = {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "encoding_dir": direction.value,
        "char_order_2_weight": 0.3,
        "wli_order_2_weight": 0.7,
    }

    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.50,
        fallback=0.54,
    )
    print_stop_summary("Autokey GA", stop)

    solver_kwargs = dict(
        pop_size=144,
        generations=120,
        elite_frac=0.08,
        cx_frac=0.9,
        mut_prob=0.25,
        tournament_k=4,
        plateau_rounds=25,
        plateau_min_delta=1e-4,
        stop_score=stop.stop_score,
    )

    def _run(label: str, solver: SolverSpec, initial_keys: Sequence[Sequence[int]] | None):
        print(f"\n=== Autokey solve: {label} ===")
        display_spec = RunSpec(
            problem_input=NormalizedInput(ct_idx=ct_idx_list, wli=wli),
            cipher=cipher_spec,
            key=key_spec,
            solver=solver,
            scorer="rune",
            scorer_params=display_scorer_params,
            encoding_dir=direction,
            telemetry_on=True,
        )
        result = run(
            text=ct_runes,
            cipher=cipher_spec,
            key=key_spec,
            solver=solver,
            device="cpu",
            scorer="rune",
            scorer_params=scorer_params,
            wli_data=wli,
            encoding_dir=direction,
            telemetry_on=True,
            initial_keys=initial_keys,
            return_solver_report=True,
        )
        ratio = _match_ratio(result.solution.plaintext_idx, pt_idx)
        print(f"Match ratio ({label}): {ratio:.3f}")
        print_rdp_result(
            result,
            spec=display_spec,
            reference_idx=pt_idx,
            tutorial_entry={
                "path": "Tutorial_Autokey.py",
                "title": f"Autokey pretty-print variant ({label})",
                "gate": "v1_smoke_pretty_print",
                "acceptance_kind": "min_match_ratio",
                "min_match_ratio": MATCH_THRESHOLD,
                "uses_oracle_stop_score": True,
            },
        )
        return ratio

    baseline_solver = SolverSpec.ga(seed=TUTORIAL_SEED_BASELINE, **solver_kwargs)
    baseline_ratio = _run("no crib", baseline_solver, initial_keys=None)

    crib_seeds = _crib_seeds_from_prefix(
        ct_idx_list,
        CRIB_TEXT,
        direction=direction,
        seed_len=SEED_LEN,
        alphabet=ALPHABET_SIZE,
    )
    print(f"crib seed candidates: {len(crib_seeds)}")
    crib_solver = SolverSpec.ga(seed=TUTORIAL_SEED_CRIB, **solver_kwargs)
    _run("crib assisted", crib_solver, initial_keys=crib_seeds or None)

    print(f"\nBaseline ratio: {baseline_ratio:.3f}")


if __name__ == "__main__":
    main()
