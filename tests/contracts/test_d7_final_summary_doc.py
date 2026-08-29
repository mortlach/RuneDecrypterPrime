from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SUMMARY_DOC = ROOT / 'docs' / 'release_contracts' / 'v1' / 'D7_FINAL_SUMMARY.md'

def _summary_text() -> str:
    assert SUMMARY_DOC.exists()
    return SUMMARY_DOC.read_text(encoding='utf-8')

def test_d7_summary_names_branch_and_scope() -> None:
    text = _summary_text()
    assert 'prelease/v1.0.0_d7' in text
    assert 'not a feature branch' in text
    assert 'new solvers' in text
    assert 'new ciphers' in text
    assert 'new scorer lanes' in text

def test_d7_summary_names_owned_label_domains() -> None:
    text = _summary_text()
    assert 'ComponentKind' in text
    assert 'ScorerLaneName' in text
    assert 'SpanHammingMode' in text
    assert 'SpanHammingGateFailPolicy' in text
    assert 'ScorerTelemetryPrefix' in text
    assert 'ScorerTelemetryKey' in text

def test_d7_summary_names_runtime_bridge_hardening() -> None:
    text = _summary_text()
    assert 'Runtime capability report bridges' in text
    assert 'core/engine/builders.py' in text
    assert 'NumPy wrapper' in text
    assert 'unified scorer' in text
    assert 'span_hamming_raw' in text

def test_d7_summary_names_output_and_report_only_rules() -> None:
    text = _summary_text()
    assert 'public strings' in text
    assert 'score' in text
    assert 'raw_score' in text
    assert 'tie-breaks' in text
    assert 'solver stopping' in text

def test_d7_summary_names_resolved_backend_enum_overlay() -> None:
    text = _summary_text()
    assert 'Backend enum-state overlay resolved' in text
    assert 'superseded by equivalent in-repo code and tests' in text
    assert 'src/rune_decrypter_prime/scoring/rune_scorer_impl.py' in text
    assert 'src/rune_decrypter_prime/scoring/torch_rune_scorer.py' in text
    assert 'tests/scoring/test_base_scorer_enum_assignment_contract.py' in text
    assert 'old local-overlay closeout blocker' in text
    assert 'Known local overlay not yet pushed' not in text
    assert 'branch should not close' not in text
