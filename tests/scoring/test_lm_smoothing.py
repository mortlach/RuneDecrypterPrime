from __future__ import annotations
import numpy as np
import pytest
from rune_decrypter_prime.scoring.rune_scorer import RuneScorer
from tests._helpers.configs import _mk_cfgs
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
pytestmark = pytest.mark.tier_a

def _make_scorer(smoothing: str):
    c_cfg, s_cfg = _mk_cfgs(device='cpu', encoding_dir='ltr', scorer_overrides={'smoothing': smoothing, 'use_word_breaks': False, 'include_char': True, 'char_weights': {2: 1.0}, 'wli_weights': {}})
    return RuneScorer(c_cfg, s_cfg)

def test_lm_smoothing():
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(2,))
    pt = np.arange(64, dtype=np.uint8) % 29
    scorer_none = _make_scorer('none')
    score_a = float(scorer_none.score(pt))
    scorer_smooth = _make_scorer('lidstone')
    _ = scorer_smooth.score(pt)
    score_b = float(scorer_none.score(pt))
    assert score_b == pytest.approx(score_a, rel=0.0, abs=0.0)
