from __future__ import annotations
from types import SimpleNamespace
import numpy as np
import pytest
from rune_decrypter_prime.ciphers.scheduled_stream_lookup_cipher import ScheduledStreamLookupCipher, validate_operation_degeneracy
pytestmark = pytest.mark.tier_a

def test_xor_mod_and_lookup_require_explicit_degeneracy_allow() -> None:
    with pytest.raises(ValueError, match="requires degeneracy='allow'"):
        validate_operation_degeneracy('xor_mod', 'forbid')
    with pytest.raises(ValueError, match="requires degeneracy='allow'"):
        validate_operation_degeneracy('lookup', 'forbid')
    assert validate_operation_degeneracy('xor_mod', 'allow') == ('xor_mod', 'allow')
    assert validate_operation_degeneracy('lookup', 'allow') == ('lookup', 'allow')

def _identity_a_table(alphabet_size: int) -> list[list[int]]:
    return [[pt for _state in range(alphabet_size)] for pt in range(alphabet_size)]

def _identity_ab_table(alphabet_size: int) -> list[list[list[int]]]:
    return [[[pt for _b in range(alphabet_size)] for _a in range(alphabet_size)] for pt in range(alphabet_size)]

def test_degenerate_lookup_reports_multiple_candidates_not_unique_decrypt() -> None:
    A = 3
    a_table = _identity_a_table(A)
    a_table[1][0] = 0
    cipher = ScheduledStreamLookupCipher(SimpleNamespace(name='scheduled_stream_lookup', alphabet_size=A, streams=[{'name': 'A', 'kind': 'periodic', 'period': 1}], schedule='overlay', operation='lookup', degeneracy='allow', key_length=1, lookup={'a': a_table, 'b': _identity_a_table(A), 'ab': _identity_ab_table(A)}))
    ct = np.array([0], dtype=int)
    key = np.array([0], dtype=int)
    cands, lens, invalid = cipher.candidates_for(ct, key, limit=A)
    assert not bool(invalid[0, 0])
    assert int(lens[0, 0]) >= 2
    assert {0, 1} <= set(cands[0, 0, :int(lens[0, 0])].tolist())
