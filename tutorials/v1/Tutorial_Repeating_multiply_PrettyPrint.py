from __future__ import annotations

"""Repeating multiply pretty-print tutorial.

This variant demonstrates a custom user map, ct = pt * k mod 29, and reports the
real solve through the standard RDP printer contract.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, NormalizedInput, RunSpec, SolverSpec, define_map, print_rdp_result, run
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1_rev, word_breaks1_rev
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

N = 29
TUTORIAL_SEED = 12345
KEY_LEN = 13
MIN_MATCH_RATIO = 1.0
DIRECTION = Direction.RTL


def mult_map(pt: int, k: int) -> int:
    return (pt * k) % N


def _preview(label: str, text: str, limit: int = 160) -> None:
    suffix = "..." if len(text) > limit else ""
    print(f"{label} length: {len(text)}")
    print(f"{label} preview: {text[:limit]}{suffix}")


def main() -> None:
    rng = np.random.default_rng(TUTORIAL_SEED)
    key_nums = rng.integers(1, N, size=KEY_LEN).tolist()

    pt_idx = [int(v) for v in plaintext1_rev]
    wli = [list(pair) for pair in word_breaks1_rev]

    pt_runes = Runeglish.to_rune(pt_idx, wli)
    stream = [key_nums[i % KEY_LEN] for i in range(len(pt_idx))]
    ct_idx = [int((p * k) % N) for p, k in zip(pt_idx, stream)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    print("Repeating multiply problem")
    print(f"encoding direction: {DIRECTION.value}")
    print(f"map: ct = pt * k mod {N}")
    print(f"key length: {KEY_LEN}")
    _preview("plaintext runes", pt_runes)
    _preview("ciphertext runes", ct_runes)

    cipher = define_map(function=mult_map, N=N)
    key_spec = KeySpec.repeat(len=KEY_LEN)
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
    print_stop_summary("Repeating Multiply Beam", stop)

    solve_spec = SolverSpec.beam(
        beam_width=32,
        max_children_per_parent=24,
        plateau_rounds=8,
        plateau_min_delta=1e-4,
        stop_score=stop.stop_score,
        verbose=True,
        progress_pct=2,
        print_progress=True,
        seed=TUTORIAL_SEED,
    )
    display_spec = RunSpec(
        problem_input=NormalizedInput(ct_idx=ct_idx, wli=wli),
        cipher=cipher,
        key=key_spec,
        solver=solve_spec,
        scorer="rune",
        scorer_params=display_scorer_params,
        encoding_dir=DIRECTION,
        telemetry_on=True,
    )

    result = run(
        text=ct_runes,
        cipher=cipher,
        key=key_spec,
        solver=solve_spec,
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=DIRECTION,
        telemetry_on=True,
        return_solver_report=True,
    )

    recovered = getattr(result.solution, "plaintext_rune", "") or getattr(result.solution, "plaintext_str", "")
    print("Recovered plaintext preview:", str(recovered)[:120] + ("..." if len(str(recovered)) > 120 else ""))

    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_Repeating_multiply_PrettyPrint.py",
            "title": "Repeating multiply pretty-print variant",
            "gate": "v1_extended_pretty_print",
            "acceptance_kind": "min_match_ratio",
            "min_match_ratio": MIN_MATCH_RATIO,
            "uses_oracle_stop_score": True,
        },
    )


if __name__ == "__main__":
    main()
