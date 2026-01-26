# tests/scoring/test_scorer_kaeding_style_avg_logp.py
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device, Direction, ObjectiveFamily, ObjectiveSpec, SeMode, Stat
from rune_decrypter_prime.scoring.language_model.paths import default_lm_root, load_index, expand_pattern

from rune_decrypter_prime.data.cipher_tests.plaintext import (
    long_plaintext,
    plaintext1, plaintext1_rev,
    word_breaks1, word_breaks1_rev,
)


def _require_char4_joint(*, mode: str, pos: str) -> None:
    root = default_lm_root().resolve()
    if not root.exists():
        pytest.skip("LM root not present (full tables not shipped with repo).")
    try:
        idx = load_index(root)
    except Exception as exc:
        pytest.skip(f"LM index not readable: {exc}")
    model_cfg = idx.models.get("char")
    if not model_cfg:
        pytest.skip("LM index has no 'char' model registered.")
    pat = model_cfg.get("joint_pattern")
    if not pat:
        pytest.skip("LM index missing joint_pattern for char.")
    fp = expand_pattern(root, pat, mode=mode, pos=pos, n=4)
    if not fp.exists():
        pytest.skip(f"Required char4 joint table is missing: {fp}")


def _mk_cipher_cfg(length: int, *, encoding_dir: Direction) -> dict:
    # build_scorer expects a CipherConfig-like mapping.
    # ciphertext and wli_data are required by CipherConfig, but scoring only needs device/dir and lengths.
    ct = list(range(length))
    wli = [(i, i + 1) for i in range(length)]
    return CipherConfig(ciphertext=ct, wli_data=wli, key_length=None, device=Device.CPU, encoding_dir=encoding_dir).asdict()


def _mk_kaeding_scorer(win_ngrams: int, *, encoding_dir: Direction) -> object:
    # Kaeding's fitness: average log tetragram frequency across a passage.
    # W = number of n-grams per window (not rune length).
    n_order = 4
    span_len = int(win_ngrams) + n_order - 1
    s_cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.AVG, stat=Stat.LOGP, win=int(win_ngrams)),
        se_mode=SeMode.NOSE,
        encoding_dir=encoding_dir,
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        wli_weights={},
        dtype="float32",
    ).asdict()
    return build_scorer(_mk_cipher_cfg(span_len, encoding_dir=encoding_dir), s_cfg)


@pytest.mark.tier_a
def test_kaeding_style_avglogp_prefers_real_text_over_random() -> None:
    # Needs char4 / NOSE (no sentence tags).
    _require_char4_joint(mode="ltr", pos="nose")

    rng = np.random.default_rng(12345)
    pt = np.asarray(long_plaintext, dtype=np.uint8)

    N = 400
    W = N - 3  # n=4 -> W = L - n + 1
    scorer = _mk_kaeding_scorer(W, encoding_dir=Direction.LTR)

    # One real-ish slice vs one random control slice.
    start = int(rng.integers(0, pt.size - N))
    real = pt[start : start + N]
    rand = rng.integers(0, 29, size=N, dtype=np.uint8)

    s_real = float(scorer.score(real, None))
    s_rand = float(scorer.score(rand, None))

    # Kaeding reports random passages have markedly worse (more negative) avg log tetragram scores.
    assert s_real > s_rand


@pytest.mark.tier_a
def test_kaeding_style_sd_shrinks_with_length() -> None:
    # With longer passages, the SD of avg logp should shrink (law of large numbers).
    _require_char4_joint(mode="ltr", pos="nose")

    rng = np.random.default_rng(20260124)
    pt = np.asarray(long_plaintext, dtype=np.uint8)

    def sample_scores(N: int, K: int) -> np.ndarray:
        W = N - 3  # n=4 -> W = L - n + 1
        scorer = _mk_kaeding_scorer(W, encoding_dir=Direction.LTR)
        out = np.empty(K, dtype=np.float64)
        for i in range(K):
            start = int(rng.integers(0, pt.size - N))
            block = pt[start : start + N]
            out[i] = float(scorer.score(block, None))
        return out

    s100 = sample_scores(100, 80)
    s1000 = sample_scores(1000, 30)

    std100 = float(np.std(s100, ddof=0))
    std1000 = float(np.std(s1000, ddof=0))

    assert std100 > std1000


@pytest.mark.tier_a
def test_direction_symmetry_ltr_vs_rtl_on_reversed_text() -> None:
    # LTR and RTL are distinct encodings; do not assume symmetry.
    # This test only verifies the direction is applied and scores are finite.
    _require_char4_joint(mode="ltr", pos="nose")
    _require_char4_joint(mode="rtl", pos="nose")

    pt_ltr = np.asarray(plaintext1, dtype=np.uint8)
    pt_rtl = np.asarray(plaintext1_rev, dtype=np.uint8)

    W_ltr = int(pt_ltr.size) - 3
    W_rtl = int(pt_rtl.size) - 3
    scorer_ltr = _mk_kaeding_scorer(W_ltr, encoding_dir=Direction.LTR)
    scorer_rtl = _mk_kaeding_scorer(W_rtl, encoding_dir=Direction.RTL)

    s_ltr = float(scorer_ltr.score(pt_ltr, word_breaks1))
    s_rtl = float(scorer_rtl.score(pt_rtl, word_breaks1_rev))

    assert np.isfinite(s_ltr)
    assert np.isfinite(s_rtl)
    assert scorer_ltr.telemetry().get("direction") == "ltr"
    assert scorer_rtl.telemetry().get("direction") == "rtl"
