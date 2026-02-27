from __future__ import annotations

import json
import numpy as np
import pytest

from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device, Direction, ObjectiveFamily, ObjectiveSpec, SeMode, Stat
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext, plaintext1
import rune_decrypter_prime.scoring.span_hamming as span_hamming_pkg
from rune_decrypter_prime.scoring.span_hamming.backend import SpanHammingBackend as RealSpanHammingBackend
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets


def _mk_cipher_cfg(length: int) -> dict:
    return CipherConfig(
        ciphertext=list(range(length)),
        wli_data=[],
        key_length=None,
        device=Device.CPU,
        encoding_dir=Direction.LTR,
    ).asdict()


def _mk_char4_avg_logp_scorer(text_len: int) -> object:
    # Kaeding-style objective shape for n=4:
    # use AVG LOGP over the full text span (W = L - 4 + 1).
    win = int(text_len) - 3
    s_cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.AVG, stat=Stat.LOGP, win=win),
        se_mode=SeMode.NOSE,
        encoding_dir=Direction.LTR,
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        wli_weights={},
        dtype="float32",
    ).asdict()
    return build_scorer(_mk_cipher_cfg(text_len), s_cfg)


def _mk_char4_pct_logp_scorer_with_span_calibrated(text_len: int, *, assets_dir: str) -> object:
    s_cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        se_mode=SeMode.NOSE,
        encoding_dir=Direction.LTR,
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        wli_weights={},
        dtype="float32",
        span_hamming_enabled=True,
        span_hamming_mode="calibrated",
        span_hamming_assets_dir=assets_dir,
        span_hamming_combine_mode="min",
        span_hamming_weight_span=1.0,
        span_hamming_weight_char=1.0,
        span_hamming_len_min=5,
        span_hamming_len_max=8,
        span_hamming_max_hd=2,
        span_hamming_coverage_min=0.0,
        span_hamming_quality_min=0.0,
    ).asdict()
    return build_scorer(_mk_cipher_cfg(text_len), s_cfg)


def _repeat_motif(motif: list[int], length: int) -> np.ndarray:
    m = np.asarray(motif, dtype=np.uint8)
    reps = int(np.ceil(int(length) / int(m.size)))
    return np.tile(m, reps)[: int(length)].astype(np.uint8, copy=False)


def _build_span_wordlists_from_real_text() -> dict[int, list[list[int]]]:
    pt = np.asarray(long_plaintext, dtype=np.uint8)
    out: dict[int, list[list[int]]] = {}
    for L in (5, 6, 7, 8):
        uniq: set[tuple[int, ...]] = set()
        rows: list[list[int]] = []
        stop = min(pt.size - L, 3000)
        for i in range(0, stop, 3):
            key = tuple(int(v) for v in pt[i : i + L])
            if key in uniq:
                continue
            uniq.add(key)
            rows.append(list(key))
        out[L] = rows
    return out


def _write_span_calibrated_assets(root, *, length_bucket: int) -> str:
    root.mkdir(parents=True, exist_ok=True)
    ecdf_dir = root / "ecdf" / "span_x"
    ecdf_dir.mkdir(parents=True, exist_ok=True)
    cal = {
        "version": "v1",
        "rows": [
            {
                "direction": "ltr",
                "length_bucket": int(length_bucket),
                "span_neg_ref": 0.45,
                "span_denom": 0.55,
                "span_valid": True,
                "char4_neg_ref": -11.0,
                "char4_denom": 1.0,
                "char4_valid": True,
            }
        ],
    }
    (root / "combined_calibration.json").write_text(json.dumps(cal), encoding="utf-8")
    meta = {
        "model": "span",
        "stat": "x_span",
        "direction": "ltr",
        "length_bucket": int(length_bucket),
    }
    np.savez(
        ecdf_dir / f"ltr_nose_span_lb{int(length_bucket)}_fulltext_x_span.npz",
        grid=np.asarray([-1.0, 0.0, 1.0], dtype=np.float64),
        q=np.asarray([0.05, 0.5, 0.95], dtype=np.float64),
        meta_json=np.array(json.dumps(meta), dtype=np.str_),
    )
    return str(root)


@pytest.mark.tier_a
def test_char4_overfit_motif_beats_real_anchor() -> None:
    # Require only the assets this test uses.
    require_full_lm_assets(
        models=("char",),
        modes=("ltr",),
        poses=("nose",),
        ns=(4,),
        ecdf_stats=("logp",),
    )

    length = 400
    scorer = _mk_char4_avg_logp_scorer(length)

    # Deterministic overfit motif (found via seeded motif search).
    # Repeating this motif produces an unrealistically strong char4 score.
    adversarial = _repeat_motif([4, 24, 16, 18], length)
    anchor = np.asarray(plaintext1[:length], dtype=np.uint8)

    s_adv = float(scorer.score(adversarial, None))
    s_anchor = float(scorer.score(anchor, None))
    assert s_adv > s_anchor


@pytest.mark.tier_a
def test_char4_overfit_motif_beats_high_real_slice_quantile() -> None:
    require_full_lm_assets(
        models=("char",),
        modes=("ltr",),
        poses=("nose",),
        ns=(4,),
        ecdf_stats=("logp",),
    )

    length = 400
    scorer = _mk_char4_avg_logp_scorer(length)
    adversarial = _repeat_motif([4, 24, 16, 18], length)
    s_adv = float(scorer.score(adversarial, None))

    rng = np.random.default_rng(42)
    pt = np.asarray(long_plaintext, dtype=np.uint8)
    assert pt.size > length
    real_scores = []
    for _ in range(64):
        start = int(rng.integers(0, pt.size - length))
        block = pt[start : start + length]
        real_scores.append(float(scorer.score(block, None)))
    q95 = float(np.quantile(np.asarray(real_scores, dtype=np.float64), 0.95))
    assert s_adv > q95


@pytest.mark.tier_a
def test_calibrated_span_char_min_recovers_real_over_char4_overfit(tmp_path, monkeypatch) -> None:
    require_full_lm_assets(
        models=("char",),
        modes=("ltr",),
        poses=("nose",),
        ns=(4,),
        ecdf_stats=("logp",),
    )

    length = 400
    real = np.asarray(long_plaintext[600 : 600 + length], dtype=np.uint8)
    adversarial = _repeat_motif([4, 24, 16, 18], length)

    # First prove the failure mode on char4 AVG/logp.
    avg_char4 = _mk_char4_avg_logp_scorer(length)
    s_real_avg = float(avg_char4.score(real, None))
    s_adv_avg = float(avg_char4.score(adversarial, None))
    assert s_adv_avg > s_real_avg

    # Patch span backend constructor to use deterministic in-test wordlists.
    class _PatchedSpanHammingBackend(RealSpanHammingBackend):
        def __init__(self, config=None, *, wordlist_dir=None, require_selected=True, wordlists=None):
            super().__init__(config=config, wordlists=_build_span_wordlists_from_real_text())

    monkeypatch.setattr(span_hamming_pkg, "SpanHammingBackend", _PatchedSpanHammingBackend)
    assets_dir = _write_span_calibrated_assets(tmp_path / "span_assets", length_bucket=length)

    combined = _mk_char4_pct_logp_scorer_with_span_calibrated(length, assets_dir=assets_dir)
    s_real_combined = float(combined.score(real, None))
    stats_real = dict(combined.last_stats())
    s_adv_combined = float(combined.score(adversarial, None))
    stats_adv = dict(combined.last_stats())

    # Combined scorer should reject the char-only overfit and restore preference for real text.
    assert s_real_combined > s_adv_combined
    assert float(stats_real["span_hamming_pct"]) > float(stats_adv["span_hamming_pct"])
    assert float(stats_adv["span_hamming_char_pct"]) > float(stats_real["span_hamming_char_pct"])
