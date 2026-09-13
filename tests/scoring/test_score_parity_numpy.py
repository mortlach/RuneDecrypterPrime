from __future__ import annotations
import numpy as np
import pytest
from rdp import api
from rdp.core.engine.builders import build_scorer
from tests._helpers.configs import _mk_cfgs
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
from tests.scoring.golden_vectors import GOLDEN_SCORE_VECTORS, PLAINTEXT_TOKEN_VECTORS
pytestmark = pytest.mark.tier_a

@pytest.mark.full_assets
@pytest.mark.parametrize('case_name', sorted(GOLDEN_SCORE_VECTORS.keys()))
def test_numpy_scores_match_golden_vectors(case_name: str) -> None:
    require_full_lm_assets(models=('char',), modes=('ltr',), poses=('nose',), ns=(2, 4), ecdf_stats=('logp',))
    case = GOLDEN_SCORE_VECTORS[case_name]
    overrides = dict(case["scorer_overrides"])
    c_cfg, s_cfg = _mk_cfgs(
        device="cpu",
        encoding_dir="ltr",
        scorer_overrides={
            "backend": api.advanced.ScorerBackend.NUMPY,
            **overrides,
        },
    )
    scorer = build_scorer(c_cfg, s_cfg)
    observed = np.asarray([float(scorer.score(np.asarray(pt, dtype=np.uint8))) for pt in PLAINTEXT_TOKEN_VECTORS], dtype=np.float64)
    expected = np.asarray(case['numpy'], dtype=np.float64)
    np.testing.assert_allclose(observed, expected, rtol=1e-06, atol=1e-08)
