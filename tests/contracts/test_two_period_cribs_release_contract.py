from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'docs' / 'release_contracts' / 'v1' / 'WP7_TWO_PERIOD_CRIBS.md'
SCOPE = ROOT / 'docs' / 'release_contracts' / 'v1' / 'v1_scope_lock.json'

def test_public_contract_documents_the_specialised_route() -> None:
    text = CONTRACT.read_text(encoding='utf-8')
    for fragment in ('from rdp import api', 'two_period_vigenere', 'SolverSpec.two_period_cribs', 'api.run', 'complete word', '29-rune', 'CPU-only', 'A-then-B', 'S2 scout', 'B1 bridge', 'F1 judge', 'complete deduplicated', 'InterruptorConfig', 'structural interruptor', 'compacted core', 'bruteforce_max', 'search_strategy="keyops"', 'RunResult', 'SolverReport'):
        assert fragment in text

def test_scope_lock_contains_two_period_crib_solver_without_hamming_drift() -> None:
    data = json.loads(SCOPE.read_text(encoding='utf-8'))
    solver = data['v1_included']['two_period_cribs']
    assert solver['status'] == 'v1_core'
    assert 'scheduled_stream_lookup' in solver['rule']
    assert 'complete-word' in solver['rule']
    assert 'complete-union' in solver['rule']
    assert 'rejects unsupported options' in solver['rule']
    assert data['v1_included']['span_hamming']['status'] == 'v1_optional'
    assert data['not_v1_production']['new_ngram_hamming_scoring']['status'] == 'experimental_report_only'

def test_production_package_never_imports_tutorials_or_cipher_development() -> None:
    offenders = []
    for path in (ROOT / 'src' / 'rune_decrypter_prime').rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        if 'cipher_development' in text or 'tutorials.v1' in text:
            offenders.append(path.relative_to(ROOT).as_posix())
    assert not offenders
