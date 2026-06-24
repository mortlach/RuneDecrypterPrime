from __future__ import annotations

"""ScheduledStreamLookup segmented P13/P31/P13 near-solve pretty tutorial."""

import sys
from pathlib import Path
from typing import Sequence

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import Direction, NormalizedInput, RunSpec, print_rdp_result, run
from rune_decrypter_prime.utils.scheduled_stream_lookup_tutorial_utils import (
    build_ciphertext,
    concat_keys,
    default_scorer_params,
    encode_plaintext,
    key_period13,
    key_period31,
    make_real_solve_solver,
    mask_from_segments,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MIN_MATCH_RATIO = 0.90
STOP_SCORE = 0.56
DIRECTION = Direction.RTL


def _as_int_list(value: object) -> list[int] | None:
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value]
    return None


def _match_ratio(found: Sequence[int], expected: Sequence[int]) -> float:
    n = min(len(found), len(expected))
    if n <= 0:
        return 0.0
    return sum(1 for i in range(n) if int(found[i]) == int(expected[i])) / float(n)


def _run_case(label: str, mask: list[int], key: list[int]) -> None:
    cipher_spec, key_spec, pt_idx, wli, _pt_runes, ct_idx_list, ct_runes, _key_arr, _cipher_obj = build_ciphertext(
        cipher_name="two_period_vigenere",
        cipher_kwargs=dict(
            period_a=13,
            period_b=31,
            alphabet_size=29,
            schedule="mask",
            mask=mask,
        ),
        key_values=key,
        expected_key_len=44,
        direction=DIRECTION,
    )

    print("=" * 72)
    print(f"ScheduledStreamLookup segmented near-solve problem: {label}")
    print(f"direction: {DIRECTION.value}")
    print("periods: P13 + P31")
    print("schedule: user-supplied mask")
    print("acceptance: near-solve match ratio, exact recovery not required")
    print(f"ciphertext length: {len(ct_idx_list)}")
    print(f"ciphertext preview: {ct_runes[:160]}{'...' if len(ct_runes) > 160 else ''}")

    scorer_params = default_scorer_params(DIRECTION)
    display_scorer_params = {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "encoding_dir": DIRECTION.value,
        "char_order_2_weight": 0.3,
        "wli_order_2_weight": 0.7,
    }
    solver = make_real_solve_solver(
        stop_score=STOP_SCORE,
        beam_width=96,
        plateau_rounds=16,
        max_children_per_parent=29,
    )
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
        device="cpu",
        scorer="rune",
        scorer_params=scorer_params,
        wli_data=wli,
        encoding_dir=DIRECTION,
        telemetry_on=True,
        initial_keys=None,
        return_solver_report=True,
    )

    found_key = _as_int_list(getattr(result.solution, "key", None))
    recovered = getattr(result.solution, "plaintext_idx", []) or []
    ratio = _match_ratio(recovered, pt_idx)
    print(f"Expected key length : {len(key)}")
    print(f"Found key length    : {0 if found_key is None else len(found_key)}")
    print(f"Plaintext match     : {ratio:.3f}")
    print(f"Near-solve accepted?: {ratio >= MIN_MATCH_RATIO}")

    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py",
            "title": f"ScheduledStreamLookup segmented {label} pretty-print variant",
            "gate": "v1_showcase_near_solve_pretty_print",
            "acceptance_kind": "showcase_near_solve",
            "min_match_ratio": MIN_MATCH_RATIO,
            "uses_oracle_stop_score": False,
        },
    )
    if ratio < MIN_MATCH_RATIO:
        raise AssertionError(f"near-solve below threshold: match_ratio={ratio:.3f}")


def main() -> None:
    pt_idx, _wli, _pt_runes = encode_plaintext(DIRECTION)
    n = len(pt_idx)
    key = concat_keys(key_period13(), key_period31())

    mask_13_31_13 = mask_from_segments(n, [("A", 0, 120), ("B", 120, 240), ("A", 240, None)])
    _run_case("P13/P31/P13", mask_13_31_13, key)

    mask_31_13_31 = mask_from_segments(n, [("B", 0, 124), ("A", 124, 236), ("B", 236, None)])
    _run_case("P31/P13/P31", mask_31_13_31, key)


if __name__ == "__main__":
    main()
