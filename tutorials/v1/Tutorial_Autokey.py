from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Sequence

import numpy as np

_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, cipher_instance, run
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish


SEED = [6, 1, 4]
SEED_LEN = len(SEED)
ALPHABET_SIZE = 29
APP_VERSION = "tutorial-autokey-1.0"
MATCH_THRESHOLD = 0.90
CRIB_TEXT = "WHITE RABBIT"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _match_ratio(found: Sequence[int], reference: Sequence[int]) -> float:
    n = min(len(found), len(reference))
    if n == 0:
        return 0.0
    matches = sum(1 for i in range(n) if found[i] == reference[i])
    return matches / float(n)


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

    base = [int((ct_idx[i] - crib_idx[i]) % alphabet) for i in range(seed_len)]
    seeds: List[List[int]] = [base]

    # Add a couple of noisy variants so Beam/GA have nearby options.
    for delta in (-1, 1):
        mutated = [(val + delta) % alphabet for val in base]
        seeds.append(mutated)
    return seeds


def main() -> None:
    direction = Direction.RTL
    plaintext = (
        "WHEN THE WHITE RABBIT READ THESE WORDS HE LOOKED SUDDENLY ALARMED "
        "FOR A SHOWER OF LITTLE GLASS BOXES CAME TUMBLING UPON HIM"
    )
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(plaintext, direction=direction.value)
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)

    autokey_cipher = cipher_instance(by_name.cipher("autokey", seed_len=SEED_LEN, alphabet_size=ALPHABET_SIZE))
    seed_arr = np.asarray(SEED, dtype=np.uint8)
    ct_idx = autokey_cipher.encrypt_single(plaintext=pt_idx_arr, key=seed_arr)
    ct_idx_list = ct_idx.tolist()
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)

    cipher_spec = by_name.cipher("autokey", seed_len=SEED_LEN, alphabet_size=ALPHABET_SIZE)
    key_spec = KeySpec.repeat(len=SEED_LEN)

    solver_kwargs = dict(
        pop_size=144,
        generations=120,
        elite_frac=0.08,
        cx_frac=0.9,
        mut_prob=0.25,
        tournament_k=4,
        plateau_rounds=25,
    )
    baseline_solver = SolverSpec.ga(seed=2024, **solver_kwargs)
    crib_solver = SolverSpec.ga(seed=4242, **solver_kwargs)

    scorer_params = dict(
        objective="pct.logp.win10",
        n_char=2,
        n_wli=2,
        include_char=True,
        use_word_breaks=True,
        encoding_dir=direction,
    )

    def _run(label: str, solver: SolverSpec, initial_keys: Sequence[Sequence[int]] | None):
        solution = run(
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
        )
        ratio = _match_ratio(solution.plaintext_idx, pt_idx)
        match_ok = ratio >= MATCH_THRESHOLD
        key_view = getattr(solution, "key", None)
        key_list = [int(k) for k in key_view] if isinstance(key_view, (list, tuple)) else None
        print(f"\n=== Autokey solve ({label}) ===")
        print_run_report(
            title=f"Autokey ({label})",
            cipher="autokey",
            solution=solution,
            match_ok=match_ok,
            app_version=APP_VERSION,
            key_idx=key_list,
            key_len=SEED_LEN,
            ct_idx=ct_idx_list,
            ct_rune=ct_runes,
            pt_rune_ref=pt_runes,
            pt_idx_ref=pt_idx,
            wli=wli,
        )
        print(f"Match ratio ({label}): {ratio:.3f}")
        return ratio

    baseline_ratio = _run("no crib", baseline_solver, initial_keys=None)

    crib_seeds = _crib_seeds_from_prefix(
        ct_idx_list,
        CRIB_TEXT,
        direction=direction,
        seed_len=SEED_LEN,
        alphabet=ALPHABET_SIZE,
    )
    crib_initial = crib_seeds or None
    _run("crib assisted", crib_solver, initial_keys=crib_initial)

    print(f"\nBaseline ratio: {baseline_ratio:.3f}")


if __name__ == "__main__":
    main()

