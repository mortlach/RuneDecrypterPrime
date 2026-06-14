from __future__ import annotations

import sys
from types import ModuleType

import pytest

from rune_decrypter_prime.core.component_contracts import (
    EffectiveState,
    RankEffect,
    RequestedLaneUnavailableError,
    ScorerLaneName,
)
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import ScorerImpl


class _FakeRuntimeScorer:
    hamming_backend = None
    span_hamming_backend = None
    span_hamming_assets = None
    word_ngram_judge = None

    def __init__(self, c_cfg: CipherConfig, s_cfg: ScoringConfig, tables=None) -> None:
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg
        self.tables = tables
        self._hamming_backend = type(self).hamming_backend
        self._span_hamming_backend = type(self).span_hamming_backend
        self._span_hamming_assets = type(self).span_hamming_assets
        self._word_ngram_judge = type(self).word_ngram_judge
        self._span_hamming_mode = str(s_cfg.span_hamming_mode or "off").strip().lower()


class _FakeUnifiedScorer:
    def __init__(self, c_cfg: CipherConfig, s_cfg: ScoringConfig) -> None:
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg
        self._backend = _FakeRuntimeScorer(c_cfg, s_cfg)


@pytest.fixture(autouse=True)
def _reset_fake_runtime_scorer():
    _FakeRuntimeScorer.hamming_backend = None
    _FakeRuntimeScorer.span_hamming_backend = None
    _FakeRuntimeScorer.span_hamming_assets = None
    _FakeRuntimeScorer.word_ngram_judge = None


def _install_fake_torch(monkeypatch) -> None:
    module = ModuleType("rune_decrypter_prime.scoring.torch_rune_scorer")
    module.RuneScorerTorch = _FakeRuntimeScorer
    monkeypatch.setitem(sys.modules, module.__name__, module)


def _install_fake_unified(monkeypatch) -> None:
    module = ModuleType("rune_decrypter_prime.scoring.unified_rune_scorer")
    module.UnifiedRuneScorer = _FakeUnifiedScorer
    monkeypatch.setitem(sys.modules, module.__name__, module)


def _cipher_cfg() -> CipherConfig:
    return CipherConfig(ciphertext=[0, 1, 2, 3], wli_data=[], key_length=4)


def _lane_by_name(report, lane: ScorerLaneName):
    matches = [status for status in report.lanes if status.lane is lane]
    assert len(matches) == 1
    return matches[0]


def test_torch_requested_hamming_missing_backend_blocks(monkeypatch) -> None:
    _install_fake_torch(monkeypatch)

    with pytest.raises(RequestedLaneUnavailableError, match="hamming"):
        build_scorer(_cipher_cfg(), ScoringConfig(impl=ScorerImpl.TORCH, hamming_enabled=True))


def test_torch_requested_hamming_backend_is_reported_active(monkeypatch) -> None:
    _install_fake_torch(monkeypatch)
    _FakeRuntimeScorer.hamming_backend = object()

    scorer = build_scorer(_cipher_cfg(), ScoringConfig(impl=ScorerImpl.TORCH, hamming_enabled=True))
    lane = _lane_by_name(scorer.capability_report(), ScorerLaneName.HAMMING)

    assert lane.effective_state is EffectiveState.ACTIVE
    assert lane.rank_effect is RankEffect.PRODUCTION


def test_torch_requested_raw_span_missing_backend_blocks(monkeypatch) -> None:
    _install_fake_torch(monkeypatch)

    with pytest.raises(RequestedLaneUnavailableError, match="span_hamming_raw"):
        build_scorer(_cipher_cfg(), ScoringConfig(impl=ScorerImpl.TORCH, span_hamming_mode="raw_bonus"))


def test_torch_requested_calibrated_span_missing_assets_blocks(monkeypatch) -> None:
    _install_fake_torch(monkeypatch)

    with pytest.raises(RequestedLaneUnavailableError, match="span_hamming_calibrated"):
        build_scorer(_cipher_cfg(), ScoringConfig(impl=ScorerImpl.TORCH, span_hamming_mode="calibrated"))


def test_torch_report_only_word_ngram_missing_runtime_does_not_block(monkeypatch, tmp_path) -> None:
    _install_fake_torch(monkeypatch)

    scorer = build_scorer(
        _cipher_cfg(),
        ScoringConfig(
            impl=ScorerImpl.TORCH,
            word_ngram_judge_enabled=True,
            word_ngram_judge_sqlite_path=tmp_path / "word_ngram.sqlite",
        ),
    )
    lane = _lane_by_name(scorer.capability_report(), ScorerLaneName.WORD_NGRAM_JUDGE_REPORT_ONLY)

    assert lane.effective_state is EffectiveState.REPORT_ONLY
    assert lane.rank_effect is RankEffect.REPORT_ONLY
    assert not lane.is_blocking


def test_unified_facade_requested_hamming_missing_backend_blocks(monkeypatch) -> None:
    _install_fake_unified(monkeypatch)

    with pytest.raises(RequestedLaneUnavailableError, match="hamming"):
        build_scorer(_cipher_cfg(), ScoringConfig(impl=ScorerImpl.UNIFIED, hamming_enabled=True))


def test_unified_facade_attaches_backend_capability_report_to_public_scorer(monkeypatch) -> None:
    _install_fake_unified(monkeypatch)
    _FakeRuntimeScorer.hamming_backend = object()

    scorer = build_scorer(_cipher_cfg(), ScoringConfig(impl=ScorerImpl.UNIFIED, hamming_enabled=True))
    lane = _lane_by_name(scorer.capability_report(), ScorerLaneName.HAMMING)

    assert lane.effective_state is EffectiveState.ACTIVE
    assert scorer.capability_report() is scorer._capability_report
    assert scorer._backend.capability_report() is scorer._capability_report
