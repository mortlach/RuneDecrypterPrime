from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rdp.core.config.cipher import CipherConfig
from rdp.core.engine.builders import build_scorer
from rdp.core.types import Direction

pytestmark = pytest.mark.tier_a

class _DummyHamming:

    def total_min_hd_stats(self, pt, wli, direction, mode):
        return {'total_hd': 5.0, 'avg_hd_word': 2.0}

def test_torch_short_text_applies_hamming_penalty():
    pytest.importorskip("torch")
    cfg_c = CipherConfig(
        ciphertext=[0], wli_data=[], key_length=None, encoding_dir=Direction.LTR
    )
    cfg_s = api.ScoringConfig(
        backend=api.advanced.ScorerBackend.TORCH,
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_ngram_order=2,
        word_length_ngram_order=2,
        hamming_enabled=True,
        compute_dtype=api.advanced.FloatDType.FLOAT32,
    )
    scorer = build_scorer(cfg_c, cfg_s)
    scorer._hamming_backend = _DummyHamming()
    scorer._hamming_weight = 0.5
    pt = np.array([0, 1, 2, 3, 4], dtype=np.uint8)
    wli = np.array([[0, 5], [1, 5], [2, 5], [3, 5], [4, 5]], dtype=np.uint8)
    _ = float(scorer.score(pt, wli))
    stats = scorer.last_stats() if hasattr(scorer, 'last_stats') else scorer.telemetry()
    obj = stats.get('objective_stats') or stats.get('objective')
    assert obj is not None
    assert obj['penalty_hamming'] == pytest.approx(-1.0)
    assert stats.get('hamming_total_hd') == pytest.approx(5.0)
    assert stats.get('hamming_avg_hd') == pytest.approx(2.0)
