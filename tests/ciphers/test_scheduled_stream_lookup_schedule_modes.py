from __future__ import annotations
from types import SimpleNamespace
import numpy as np
import pytest
from rune_decrypter_prime.ciphers.scheduled_stream_lookup_cipher import ScheduledStreamLookupCipher
pytestmark = pytest.mark.tier_a

def _cipher(**kwargs) -> ScheduledStreamLookupCipher:
    return ScheduledStreamLookupCipher(SimpleNamespace(**kwargs))

def _two_period_cipher(**kwargs) -> ScheduledStreamLookupCipher:
    params = {'name': 'scheduled_stream_lookup', 'streams': [{'name': 'A', 'kind': 'periodic', 'period': 2}, {'name': 'B', 'kind': 'periodic', 'period': 3}], 'operation': 'add', 'key_length': 5}
    params.update(kwargs)
    return _cipher(**params)

def _roundtrip(cipher: ScheduledStreamLookupCipher, length: int=12) -> None:
    pt = np.arange(length, dtype=int) * 5 % 29
    key = np.array([1, 2, 7, 8, 9], dtype=int)
    ct = cipher.encrypt(plaintext=pt, key=key)[0]
    got = cipher.decrypt(ciphertext=ct, key=key)[0]
    assert np.array_equal(got, pt)

@pytest.mark.parametrize('params', [{'schedule': 'overlay'}, {'schedule': 'alternating', 'alternating_start': 'A'}, {'schedule': 'alternating', 'alternating_start': 'B'}, {'schedule': 'staggered_overlay', 'a_start': 0, 'b_start': 3}, {'schedule': 'ragged_overlap', 'a_start': 0, 'a_end': 8, 'b_start': 3, 'b_end': 11}, {'schedule': 'mask', 'mask': [1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0]}])
def test_schedule_modes_roundtrip(params: dict[str, object]) -> None:
    _roundtrip(_two_period_cipher(**params))

@pytest.mark.parametrize('direction', ['forward', 'backward'])
@pytest.mark.parametrize('anchor', ['start', 'end'])
def test_stream_direction_anchor_combinations_roundtrip(direction: str, anchor: str) -> None:
    cipher = _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 2, 'direction': direction, 'anchor': anchor}, {'name': 'B', 'kind': 'periodic', 'period': 3, 'direction': direction, 'anchor': anchor}], schedule='overlay', operation='add', key_length=5)
    _roundtrip(cipher)

def test_ragged_overlap_can_leave_positions_inactive() -> None:
    cipher = _two_period_cipher(schedule='ragged_overlap', a_start=1, a_end=3, b_start=5, b_end=7)
    sched = cipher._compile_schedule(8)
    assert sched.active.tolist() == [0, 1, 1, 0, 0, 2, 2, 0]
