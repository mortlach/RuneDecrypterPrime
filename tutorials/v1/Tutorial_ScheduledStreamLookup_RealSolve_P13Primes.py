from __future__ import annotations
from rdp import api
'ScheduledStreamLookup generated-primes pretty-print tutorial.'
import sys
from pathlib import Path
from typing import Sequence
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from tutorials.v1.support import tutorial_pretty as pretty
from tutorials.v1.data.plaintext_fixtures import plaintext_english_string
from tutorials.v1.support.scheduled_stream_lookup import build_ciphertext, default_scorer_params, key_period13, make_real_solve_solver
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def _as_int_list(value: object) -> list[int] | None:
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value]
    return None

def _match_ratio(found: Sequence[int], expected: Sequence[int]) -> float:
    if len(found) != len(expected) or not expected:
        return 0.0
    return sum(
        int(actual) == int(wanted)
        for actual, wanted in zip(found, expected, strict=True)
    ) / len(expected)

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='ScheduledStreamLookup P13 plus generated primes', cipher='scheduled stream lookup', solver='beam', direction='rtl', expected_result='exact solve', uses_reference_stop_score=True)
    key_values = key_period13()
    expected_key_len = 13
    stop_score = 0.56
    direction = api.TextDirection.RIGHT_TO_LEFT
    cipher_spec = api.CipherSpec.periodic_with_prime_stream(period=13, prime_offset=0)
    key_spec = api.KeySpec.repeating(length=expected_key_len)
    cipher_spec, key_spec, pt_idx, wli, _pt_runes, ct_idx_list, ct_runes, _key = build_ciphertext(
        plaintext=plaintext_english_string,
        cipher_spec=cipher_spec,
        key_spec=key_spec,
        key_values=key_values,
        direction=direction,
    )
    print('ScheduledStreamLookup generated-primes real-solve problem')
    print(f'direction: {direction.value}')
    print(f'periodic key length: {expected_key_len}')
    print('generated stream: primes modulo alphabet, prime_offset=0')
    print(f'ciphertext length: {len(ct_idx_list)}')
    print(f"ciphertext preview: {ct_runes[:160]}{('...' if len(ct_runes) > 160 else '')}")
    scorer_params = default_scorer_params(direction)
    solver = make_real_solve_solver(stop_score=stop_score)
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=scorer_params, initial_keys=None, telemetry_enabled=True, text_direction=direction, compute_device=api.ComputeDevice.CPU))
    found_key = _as_int_list(result.key or None)
    expected_key = [int(v) for v in key_values]
    if found_key is None:
        raise AssertionError('real solve did not return a key')
    key_ok = found_key == expected_key
    match_ratio = _match_ratio(result.plaintext, pt_idx)
    plaintext_ok = match_ratio == 1.0
    print(f'Expected key : {expected_key}')
    print(f'Found key    : {found_key}')
    print(f'Key accepted?: {key_ok}')
    print(f'Plaintext OK?: {plaintext_ok}')
    print(f'Match ratio: {match_ratio:.3f}')
    pretty.print_summary_spacer()
    api.display.print_result(result, options=api.display.SummaryOptions.for_tutorial())
    if not plaintext_ok:
        raise AssertionError('real solve did not recover the expected plaintext')
    if not key_ok:
        raise AssertionError('real solve did not recover the expected key')
if __name__ == '__main__':
    main()
