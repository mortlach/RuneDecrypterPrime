from __future__ import annotations
import json
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
D4_DOC = REPO_ROOT / 'docs' / 'release_contracts' / 'v1' / 'd4_contract_closure.md'
SCOPE_LOCK = REPO_ROOT / 'docs' / 'release_contracts' / 'v1' / 'v1_scope_lock.json'

def _text(path: str | Path) -> str:
    p = REPO_ROOT / path if isinstance(path, str) else path
    assert p.exists(), f'missing expected D4 contract evidence: {p}'
    return p.read_text(encoding='utf-8')

def test_d4_closure_doc_covers_every_stage() -> None:
    text = _text(D4_DOC)
    for stage in ('D4.0', 'D4.1', 'D4.2', 'D4.3', 'D4.4', 'D4.5', 'D4.6', 'D4.7', 'D4.8'):
        assert stage in text
    for required_phrase in ('requested production lane must be either `active` or `blocked`', 'scorer_lanes', 'target_score', 'no_improve_*', 'typed config objects', "degeneracy='allow'", 'fixed stream text values', 'Broad `except Exception` blocks are allowed only', 'full-proof workflow pass'):
        assert required_phrase in text

def test_d4_source_gates_are_present() -> None:
    builders = _text("src/rune_decrypter_prime/core/engine/builders.py")
    assert "_ensure_capability_report_method" in builders
    assert "raise_if_requested_lane_blocked(report)" in builders
    assert "hamming_issue=getattr" in builders
    unified = _text("src/rune_decrypter_prime/scoring/unified_rune_scorer.py")
    assert "def capability_report" in unified
    assert "cfg_scorer must be ScoringConfig" in unified
    assert "hamming_issue=getattr" in unified
    stop_reason = _text("src/rdp/api/stop_reason_contract.py")
    assert "target_score" in stop_reason
    assert "stop_score" in stop_reason
    assert "test_key" in stop_reason
    assert "BUDGET_REASON_PREFIXES" in stop_reason
    scheduled = _text(
        "src/rdp/ciphers/scheduled_stream_lookup_cipher.py"
    )
    assert "requires degeneracy='allow'" in scheduled
    assert 'fixed stream values must be a sequence of integer symbols, not text' in scheduled

def test_d4_test_gates_are_present() -> None:
    expected_tests = ['tests/contracts/test_v1_full_proof_workflow_contract.py', 'tests/core/test_scorer_capability_builder_contract.py', 'tests/api/test_scorer_lanes_report_visibility_contract.py', 'tests/api/test_stop_reason_contract.py', 'tests/core/test_public_builder_config_boundary_contract.py', 'tests/contracts/test_torch_optional_dependency_contract.py', 'tests/torch/test_torch_scorer_optional_runtime.py', 'tests/ciphers/test_scheduled_stream_lookup_contract.py']
    for path in expected_tests:
        _text(path)

def test_scope_lock_names_d4_v1_boundaries() -> None:
    data = json.loads(_text(SCOPE_LOCK))
    included = data['v1_included']
    forbidden = set(data['forbidden_v1_behaviour'])
    for key in ('scheduled_stream_lookup', 'scorer_capability_status', 'span_hamming', 'stop_reason_schema', 'typed_builder_config_boundary', 'optional_torch_runtime', 'release_full_proof_gate'):
        assert key in included
    assert 'explicit TORCH request silently falls back to NumPy' in forbidden
    assert 'fixed scheduled-stream values treated as text characters' in forbidden
