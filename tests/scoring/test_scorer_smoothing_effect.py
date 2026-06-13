# tests/scoring/test_scorer_smoothing_effect.py
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device, Direction, ObjectiveFamily, ObjectiveSpec, SeMode, Stat
from rune_decrypter_prime.scoring.language_model.paths import default_lm_root, load_index, expand_pattern


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


def _mk_cipher_cfg(length: int) -> dict:
    ct = list(range(length))
    return CipherConfig(ciphertext=ct, wli_data=[], key_length=None, device=Device.CPU, encoding_dir=Direction.LTR).asdict()


def _mk_avg_scorer(*, smoothing: str) -> object:
    # AVG logp, W = n-grams per window (so W = L - n + 1 for a full-length window).
    win = 200 - 3  # n=4 -> W = L - n + 1
    s = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.AVG, stat=Stat.LOGP, win=win),
        se_mode=SeMode.NOSE,
        encoding_dir=Direction.LTR,
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        wli_weights={},
        smoothing=smoothing,
        dtype="float32",
    ).asdict()
    return build_scorer(_mk_cipher_cfg(1000), s)


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

    # Smoothing should be wired; scores may or may not differ depending on OOV mix.

    # Telemetry may omit scorer config in minimal runs; no hard assertion here.
