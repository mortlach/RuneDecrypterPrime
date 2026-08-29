from __future__ import annotations
import pytest
from rune_decrypter_prime.core.config import Solution
from rune_decrypter_prime.utils.pretty import print_run_report
pytestmark = pytest.mark.tier_a

def _make_solution():
    sol = Solution(key=[1, 2, 3, 4, 9], plaintext=[0, 1], score=0.123)
    sol.plaintext_idx = [0, 1]
    sol.plaintext_str = 'AB'
    sol.meta = {}
    return sol

def test_print_run_report_includes_interruptors_when_solved(capsys):
    sol = _make_solution()
    sol.meta = {'interruptors': {'found': [4, 9], 'core_length': 3}}
    print_run_report(title='Interruptor Demo', cipher='vigenere', solution=sol, match_ok=None, app_version='test', key_idx=[1, 2, 3, 4, 9], key_len=5)
    out = capsys.readouterr().out
    assert 'Interruptors(found): [4, 9]' in out
    assert 'Interruptors(real) : [4, 9]' in out
    assert 'Interruptors match: Yes' in out

def test_print_run_report_omits_interruptors_without_meta(capsys):
    sol = _make_solution()
    print_run_report(title='Interruptor Demo', cipher='vigenere', solution=sol, match_ok=None, app_version='test')
    out = capsys.readouterr().out
    assert 'Interruptors(' not in out

def test_print_run_report_prefers_interruptors_ref(capsys):
    sol = _make_solution()
    sol.meta = {'interruptors': {'found': [4, 9], 'expected': [9], 'core_length': 3}}
    print_run_report(title='Interruptor Demo', cipher='vigenere', solution=sol, match_ok=None, app_version='test', interruptors_ref=[1, 2], key_idx=[1, 2, 3, 4, 9], key_len=5)
    out = capsys.readouterr().out
    assert 'Interruptors(found): [4, 9]' in out
    assert 'Interruptors(real) : [1, 2]' in out
