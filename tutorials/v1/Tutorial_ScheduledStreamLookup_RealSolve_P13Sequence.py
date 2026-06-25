from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import Direction, NormalizedInput, RunSpec, print_rdp_result, run
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.scheduled_stream_lookup_tutorial_utils import (
    build_ciphertext,
    default_scorer_params,
    key_period13,
    make_real_solve_solver,
    sample_sequence,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _as_int_list(value: object) -> list[int] | None:
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value]
    return None


def _match_ok(found: Sequence[int], expected: Sequence[int]) -> bool:
    return [int(v) for v in found[: len(expected)]] == [int(v) for v in expected]


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name='ScheduledStreamLookup P13 plus supplied sequence',
        cipher='scheduled stream lookup',
        solver='beam',
        direction='rtl',
        expected_result='exact solve',
        uses_reference_stop_score=True,
    )
    sequence = sample_sequence(64)
    key_values = key_period13()
    expected_key_len = 13
    stop_score = 0.56
    direction = Direction.RTL

    cipher_spec, key_spec, pt_idx, wli, _pt_runes, ct_idx_list, ct_runes, _key_arr, _cipher_obj = build_ciphertext(
        cipher_name="scheduled_stream_lookup",
        cipher_kwargs=dict(
            streams=[
                {"name": "A", "kind": "periodic", "period": 13},
                {"name": "S", "kind": "sequence", "values": sequence},
            ],
            schedule="overlay",
            operation="add",
            alphabet_size=29,
        ),
        key_values=key_values,
        expected_key_len=expected_key_len,
        direction=direction,
    )

    print("ScheduledStreamLookup real-solve problem")
    print(f"direction: {direction.value}")
    print(f"periodic key length: {expected_key_len}")
    print(f"sequence length: {len(sequence)}")
    print(f"ciphertext length: {len(ct_idx_list)}")
    print(f"ciphertext preview: {ct_runes[:160]}{'...' if len(ct_runes) > 160 else ''}")

    scorer_params = default_scorer_params(direction)
    display_scorer_params = {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "encoding_dir": direction.value,
        "char_order_2_weight": 0.3,
        "wli_order_2_weight": 0.7,
    }
    solver = make_real_solve_solver(stop_score=stop_score)
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
        initial_keys=None,
        return_solver_report=True,
    )

    found_key = _as_int_list(getattr(result.solution, "key", None))
    expected_key = [int(v) for v in key_values]
    if found_key is None:
        raise AssertionError("real solve did not return a key")
    key_ok = found_key == expected_key
    plaintext_ok = _match_ok(getattr(result.solution, "plaintext_idx", []) or [], pt_idx)

    print(f"Expected key : {expected_key}")
    print(f"Found key    : {found_key}")
    print(f"Key accepted?: {key_ok}")
    print(f"Plaintext OK?: {plaintext_ok}")

    pretty.print_summary_spacer()
    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py",
            "title": "ScheduledStreamLookup P13 supplied sequence pretty-print variant",
            "gate": "v1_release_pretty_print",
            "acceptance_kind": "exact",
            "min_match_ratio": 1.0,
            "uses_oracle_stop_score": False,
        },
    )

    if not plaintext_ok:
        raise AssertionError("real solve did not recover the expected plaintext")
    if not key_ok:
        raise AssertionError("real solve did not recover the expected key")


if __name__ == "__main__":
    main()
