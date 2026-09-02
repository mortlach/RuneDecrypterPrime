from __future__ import annotations
from rdp import api
import warnings
import numpy as np
import pytest
from rdp.core.component_contracts import RequestedLaneUnavailableError
from rdp.core.config.cipher import CipherConfig
from rdp.scoring import rune_scorer

class _StubECDF:

    def validate_clamp_range(self, **_kwargs):
        return None

    def load(self, **_kwargs):
        grid = np.array([0.0, 1.0], dtype=np.float64)
        q = np.array([0.0, 1.0], dtype=np.float64)
        return (grid, q)

    def interp_percentile(self, grid, q, x):
        x_arr = np.asarray(x, dtype=np.float64)
        return np.full_like(x_arr, 0.8, dtype=np.float64)

    @staticmethod
    def energy(p: np.ndarray) -> np.ndarray:
        p = np.asarray(p, dtype=np.float64)
        return (-np.log1p(-np.clip(p, 0.0, 1.0))).astype(np.float64, copy=False)

    def asset_id(self, **_kwargs):
        return 'stub'

    def meta_hash(self, **_kwargs):
        return 'stub'

    def interp_dtype(self, **_kwargs):
        return 'float64'

    def meta(self, **_kwargs):
        return {}

class _StubRt:

    def __init__(self, *_, **__):
        self.ecdf = _StubECDF()

    def _score_batch_char(self, _dir, _se, _n, pt_windows):
        nwin = int(pt_windows.shape[0]) if hasattr(pt_windows, 'shape') else len(pt_windows or [])
        zeros = np.zeros((nwin,), dtype=np.float64)
        return (zeros, zeros, zeros)

    def _score_batch_wli(self, _dir, _se, _n, pt_windows, _wli_windows):
        nwin = int(pt_windows.shape[0]) if hasattr(pt_windows, 'shape') else len(pt_windows or [])
        zeros = np.zeros((nwin,), dtype=np.float64)
        return (zeros, zeros, zeros)

def _patch_runtime(monkeypatch) -> None:
    monkeypatch.setattr(rune_scorer, 'LmPrimeRuntime', _StubRt)

def _cipher_cfg() -> CipherConfig:
    return CipherConfig(ciphertext=[0, 1, 2, 3], wli_data=[], key_length=4)

def _warning_messages(caught) -> list[str]:
    return [str(item.message).lower() for item in caught]

def test_requested_raw_span_missing_wordlist_blocks_without_warning(monkeypatch, tmp_path) -> None:
    _patch_runtime(monkeypatch)
    cfg = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=False, span_hamming_enabled=True, span_hamming_weight=0.5, span_hamming_wordlist_directory=tmp_path / 'missing_span_wordlists')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        with pytest.raises(RequestedLaneUnavailableError, match='span_hamming'):
            rune_scorer.RuneScorer(_cipher_cfg(), cfg)
    assert not any(('skipping span-hamming' in msg for msg in _warning_messages(caught)))

def test_explicit_raw_span_mode_missing_wordlist_blocks_even_with_zero_weight(monkeypatch, tmp_path) -> None:
    _patch_runtime(monkeypatch)
    cfg = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=False, span_hamming_mode=api.advanced.SpanHammingMode.RAW_BONUS, span_hamming_weight=0.0, span_hamming_wordlist_directory=tmp_path / 'missing_span_wordlists')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        with pytest.raises(RequestedLaneUnavailableError, match='span_hamming'):
            rune_scorer.RuneScorer(_cipher_cfg(), cfg)
    assert not any(('skipping span-hamming' in msg for msg in _warning_messages(caught)))

def test_unrequested_raw_span_missing_wordlist_does_not_block(monkeypatch, tmp_path) -> None:
    _patch_runtime(monkeypatch)
    cfg = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=False, span_hamming_enabled=False, span_hamming_mode=api.advanced.SpanHammingMode.OFF, span_hamming_weight=0.0, span_hamming_wordlist_directory=tmp_path / 'missing_span_wordlists')
    scorer = rune_scorer.RuneScorer(_cipher_cfg(), cfg)
    assert scorer is not None
    assert getattr(scorer, '_span_hamming_backend') is None
