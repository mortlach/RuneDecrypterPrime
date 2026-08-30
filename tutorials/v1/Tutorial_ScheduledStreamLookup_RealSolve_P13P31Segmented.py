from __future__ import annotations
from rdp import api
'ScheduledStreamLookup segmented P13/P31/P13 partial-recovery tutorial.'
import sys
from pathlib import Path
from typing import Sequence
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.scheduled_stream_lookup_tutorial_utils import build_ciphertext, concat_keys, default_scorer_params, encode_plaintext, key_period13, key_period31, make_real_solve_solver, mask_from_segments
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
MIN_MATCH_RATIO = 0.9
STOP_SCORE = 0.56
DIRECTION = api.TextDirection.RIGHT_TO_LEFT

def _as_int_list(value: object) -> list[int] | None:
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value]
    return None

def _match_ratio(found: Sequence[int], expected: Sequence[int]) -> float:
    n = min(len(found), len(expected))
    if n <= 0:
        return 0.0
    return sum((1 for i in range(n) if int(found[i]) == int(expected[i]))) / float(n)

def _run_case(label: str, mask: list[int], key: list[int]) -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='ScheduledStreamLookup segmented P13/P31/P13 partial-recovery tutorial', cipher='scheduled stream lookup', solver='beam', direction=DIRECTION.value, expected_result='partial recovery', uses_reference_stop_score=False, extra_rows=[('case', label)])
    cipher_spec = api.CipherSpec.two_period_vigenere(
        first_period=13,
        second_period=31,
        schedule=api.advanced.ScheduledStreamSchedule.MASK,
        mask=mask,
    )
    key_spec = api.KeySpec.repeating(length=44)
    cipher_spec, key_spec, pt_idx, wli, _pt_runes, ct_idx_list, ct_runes, _key = build_ciphertext(
        cipher_spec=cipher_spec,
        key_spec=key_spec,
        key_values=key,
        direction=DIRECTION,
    )
    print('=' * 72)
    print(f'ScheduledStreamLookup segmented partial-recovery problem: {label}')
    print(f'direction: {DIRECTION.value}')
    print('periods: P13 + P31')
    print('schedule: user-supplied mask')
    print('acceptance: partial-recovery match ratio, exact recovery not required')
    print(f'ciphertext length: {len(ct_idx_list)}')
    print(f"ciphertext preview: {ct_runes[:160]}{('...' if len(ct_runes) > 160 else '')}")
    scorer_params = default_scorer_params(DIRECTION)
    solver = make_real_solve_solver(stop_score=STOP_SCORE, beam_width=96, plateau_rounds=16, max_children_per_parent=29)
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=scorer_params, initial_keys=None, telemetry_enabled=True, text_direction=DIRECTION, compute_device=api.ComputeDevice.CPU))
    found_key = _as_int_list(result.key or None)
    recovered = (result.plaintext or []) or []
    ratio = _match_ratio(recovered, pt_idx)
    print(f'Expected key length : {len(key)}')
    print(f'Found key length    : {(0 if found_key is None else len(found_key))}')
    print(f'Plaintext match     : {ratio:.3f}')
    print(f'Partial recovery accepted?: {ratio >= MIN_MATCH_RATIO}')
    print(f'Match ratio: {ratio:.3f}')
    pretty.print_summary_spacer()
    api.display.print_result(result, options=api.display.SummaryOptions.for_tutorial())
    if ratio < MIN_MATCH_RATIO:
        raise AssertionError(f'partial recovery below threshold: match_ratio={ratio:.3f}')

def main() -> None:
    pt_idx, _wli, _pt_runes = encode_plaintext(DIRECTION)
    n = len(pt_idx)
    key = concat_keys(key_period13(), key_period31())
    mask_13_31_13 = mask_from_segments(n, [('A', 0, 120), ('B', 120, 240), ('A', 240, None)])
    _run_case('P13/P31/P13', mask_13_31_13, key)
    mask_31_13_31 = mask_from_segments(n, [('B', 0, 124), ('A', 124, 236), ('B', 236, None)])
    _run_case('P31/P13/P31', mask_31_13_31, key)
if __name__ == '__main__':
    main()
