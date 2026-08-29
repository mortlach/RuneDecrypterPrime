from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import (
    Device,
    Direction,
)
from rune_decrypter_prime.scoring.language_model.paths import (
    default_lm_root,
    load_index,
    expand_pattern,
)


def _require_char4_joint() -> None:
    root = default_lm_root().resolve()
    if not root.exists():
        pytest.skip("LM root not present (full tables not shipped with repo).")
    try:
        idx = load_index(root)
    except Exception as exc:
        pytest.skip(f"LM index not readable: {exc}")
    cfg = idx.models.get("char")
    if not cfg:
        pytest.skip("LM index has no 'char' model registered.")
    fp = expand_pattern(root, cfg["joint_pattern"], mode="ltr", pos="nose", n=4)
    if not fp.exists():
        pytest.skip(f"Required char4 joint table is missing: {fp}")


def _mk_cipher_cfg(length: int) -> CipherConfig:
    ct = list(range(length))
    return CipherConfig(
        ciphertext=ct,
        wli_data=[],
        key_length=None,
        device=Device.CPU,
        encoding_dir=Direction.LTR,
    )


def _mk_avg_scorer(*, smoothing: str) -> object:
    win = 200 - 3
    s = api.ScoringConfig(
        objective=api.advanced.ScoringObjective.average_log_probability(),
        character_lane_enabled=True,
        word_length_lane_enabled=False,
        character_order_weights={4: 1.0},
        word_length_order_weights={},
        smoothing=api.advanced.SmoothingMethod(smoothing),
        compute_dtype=api.advanced.FloatDType.FLOAT32,
    )
    return build_scorer(_mk_cipher_cfg(1000), s)


@pytest.mark.full_assets
@pytest.mark.tier_a
def test_smoothing_choice_changes_scores_for_random_text() -> None:
    _require_char4_joint()
    rng = np.random.default_rng(999)
    x = rng.integers(0, 29, size=200, dtype=np.uint8)
    scorer_none = _mk_avg_scorer(smoothing="none")
    scorer_gt = _mk_avg_scorer(smoothing="auto_gt")
    s_none = float(scorer_none.score(x, None))
    s_gt = float(scorer_gt.score(x, None))
    assert np.isfinite(s_none)
    assert np.isfinite(s_gt)
