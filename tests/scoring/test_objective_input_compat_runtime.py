from __future__ import annotations
import numpy as np
import pytest
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import (
    ScorerImpl,
)
from rdp import api
from tests._helpers.configs import _mk_cfgs
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
pytestmark = pytest.mark.tier_a

@pytest.mark.parametrize('impl', [ScorerImpl.NUMPY, ScorerImpl.TORCH])
def test_runtime_accepts_objective_spec_dict_and_string(impl: ScorerImpl) -> None:
    if impl is ScorerImpl.TORCH:
        pytest.importorskip('torch')
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(2,), ecdf_stats=('logp',))
    token_text = np.asarray(list(range(64)), dtype=np.uint8) % 29
    base_overrides = {
        "backend": api.advanced.ScorerBackend(impl.value),
        "character_lane_enabled": True,
        "word_length_lane_enabled": False,
        "character_order_weights": {2: 1.0},
        "word_length_order_weights": {},
    }
    objective_variants = [
        api.advanced.ScoringObjective.percentile_log_probability(window_size=10),
        {
            "kind": "percentile",
            "statistic": "log_probability",
            "window_size": 10,
        },
    ]
    scores: list[float] = []
    for obj in objective_variants:
        c_cfg, s_cfg = _mk_cfgs(device='cpu', encoding_dir='ltr', scorer_overrides={**base_overrides, 'objective': obj})
        scorer = build_scorer(c_cfg, s_cfg)
        scores.append(float(scorer.score(token_text)))
    np.testing.assert_allclose(
        np.asarray(scores, dtype=np.float64),
        np.asarray([scores[0], scores[0]], dtype=np.float64),
        rtol=1e-06,
        atol=1e-08,
    )
