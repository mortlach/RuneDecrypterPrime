from __future__ import annotations
from rdp import api
import sys
from types import ModuleType, SimpleNamespace
import pytest
from rdp.core.component_contracts import (
    CapabilityIssue,
    CapabilityStatus,
    CapabilityEffectiveState,
    ScoringLane,
)
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rdp.core.types import Device
from rune_decrypter_prime.scoring.unified_rune_scorer import UnifiedRuneScorer

class _FakeBackendScorer:
    hamming_backend = None
    hamming_issue = None

    def __init__(self, c_cfg: CipherConfig, s_cfg: ScoringConfig) -> None:
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg
        self._hamming_backend = type(self).hamming_backend
        self._hamming_issue = type(self).hamming_issue
        self._span_hamming_backend = None
        self._span_hamming_assets = None
        self._span_hamming_mode = api.advanced.SpanHammingMode.OFF
        self._word_ngram_judge = None

    def score(self, plaintext, wli_windows=None) -> float:
        return 0.0

    def batch_score(self, pts, wlis=None):
        return [0.0 for _ in pts]

def _install_fake_numpy_backend(monkeypatch) -> None:
    module = ModuleType('rune_decrypter_prime.scoring.rune_scorer')
    module.RuneScorer = _FakeBackendScorer
    monkeypatch.setitem(sys.modules, module.__name__, module)

def _cipher_cfg() -> CipherConfig:
    return CipherConfig(ciphertext=[0, 1, 2, 3], wli_data=[], key_length=4, device=Device.CPU)

def _lane_by_name(report, lane: ScoringLane):
    matches = [status for status in report.lanes if status.lane is lane]
    assert len(matches) == 1
    return matches[0]

def _issue(code: str) -> CapabilityIssue:
    return CapabilityIssue(code=code, message=f'{code} message', status=CapabilityStatus.UNAVAILABLE, source='hamming')

def test_unified_scorer_requires_typed_config_objects() -> None:
    with pytest.raises(TypeError, match='CipherConfig'):
        UnifiedRuneScorer(SimpleNamespace(ciphertext=[0, 1, 2, 3]), api.ScoringConfig())
    with pytest.raises(TypeError, match='ScoringConfig'):
        UnifiedRuneScorer(_cipher_cfg(), {'hamming_enabled': True})
    with pytest.raises(TypeError, match='ScoringConfig'):
        UnifiedRuneScorer(_cipher_cfg(), SimpleNamespace(hamming_enabled=True))

def test_unified_scorer_reports_missing_backend_lane_without_builder(monkeypatch) -> None:
    _install_fake_numpy_backend(monkeypatch)
    _FakeBackendScorer.hamming_backend = None
    _FakeBackendScorer.hamming_issue = None
    scorer = UnifiedRuneScorer(_cipher_cfg(), api.ScoringConfig(hamming_enabled=True))
    lane = _lane_by_name(scorer.capability_report(), ScoringLane.HAMMING)
    assert lane.is_blocking
    assert lane.effective_state is CapabilityEffectiveState.BLOCKED

def test_unified_scorer_preserves_backend_capability_issue_without_builder(monkeypatch) -> None:
    _install_fake_numpy_backend(monkeypatch)
    _FakeBackendScorer.hamming_backend = None
    _FakeBackendScorer.hamming_issue = _issue('custom_hamming_backend_failure')
    scorer = UnifiedRuneScorer(_cipher_cfg(), api.ScoringConfig(hamming_enabled=True))
    lane = _lane_by_name(scorer.capability_report(), ScoringLane.HAMMING)
    assert lane.is_blocking
    assert lane.issues[0].code == 'custom_hamming_backend_failure'

def test_unified_scorer_reports_active_backend_lane_without_builder(monkeypatch) -> None:
    _install_fake_numpy_backend(monkeypatch)
    _FakeBackendScorer.hamming_backend = object()
    _FakeBackendScorer.hamming_issue = None
    scorer = UnifiedRuneScorer(_cipher_cfg(), api.ScoringConfig(hamming_enabled=True))
    lane = _lane_by_name(scorer.capability_report(), ScoringLane.HAMMING)
    assert lane.effective_state is CapabilityEffectiveState.ACTIVE
    assert scorer._backend._capability_report is scorer._capability_report
