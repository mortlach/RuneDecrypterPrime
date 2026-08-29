from __future__ import annotations
import numpy as np
import pytest
from rune_decrypter_prime.scoring.rune_scorer import RuneScorer
from tests._helpers.configs import _mk_cfgs
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets

pytestmark = pytest.mark.tier_a


def test_wli_missing():
    require_full_lm_assets(
        models=("char", "wli"), modes=("ltr",), poses=("nose",), ns=(2,)
    )
    c_cfg, s_cfg = _mk_cfgs(
        device="cpu",
        encoding_dir="ltr",
        scorer_overrides={"word_length_lane_enabled": True},
    )
    scorer = RuneScorer(c_cfg, s_cfg)
    pt = np.arange(40, dtype=np.uint8) % 29
    with pytest.raises(ValueError):
        scorer.score(pt, wli_windows=None)
