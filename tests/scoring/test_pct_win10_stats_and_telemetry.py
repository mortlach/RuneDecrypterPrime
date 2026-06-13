# ============================================================
# tests/scoring/test_pct_win10_stats_and_telemetry.py
# ============================================================
import numpy as np
import pytest

from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.solver_engine import build_scorer
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1
from rune_decrypter_prime.core.types import Device, ScorerImpl, Direction
from rune_decrypter_prime.scoring.windowing import aligned_window_count
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets


A = 29


def _require_pct_assets() -> None:
    require_full_lm_assets(models=("char", "wli"), modes=("ltr",), poses=("nose",), ns=(2,), ecdf_stats=("logp",))


def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


@pytest.mark.tier_a
def test_pct_win10_stats_present_numpy():
    _require_pct_assets()
    pt = np.asarray(plaintext1, dtype=np.uint8)
    wli = np.asarray(word_breaks1, dtype=np.uint8)
    cfg_c = CipherConfig(
        ciphertext=pt,
        wli_data=wli,
        key_length=None,
        encoding_dir=Direction.LTR,
        initial_text_permutation_indices=None,
    )
    cfg_s = ScoringConfig(
        include_char=True,
        encoding_dir=Direction.LTR,
        use_word_breaks=True,
        n_char=2,
        n_wli=2,
        dtype="float32",
    )

    scorer = build_scorer(cfg_c, cfg_s)
    _ = float(scorer.score(pt, wli))  # triggers stats
    tel = getattr(scorer, "telemetry")() if hasattr(scorer, "telemetry") else {}
    stats = getattr(scorer, "last_stats")() if hasattr(scorer, "last_stats") else tel

    assert "score_mean" in stats and "score_std" in stats and "n_windows" in stats
    assert "stat.mean_per_ngram_penalized" in stats
    assert 0.0 <= stats["score_mean"] <= 1.0
    assert 0 <= stats["score_std"] < 0.5  # sanity: dispersion should be bounded
    assert stats["n_windows"] > 0
    obj = stats.get("objective_stats") or stats.get("objective")
    assert isinstance(obj, dict)
    assert "pct_logp_mean_per_ngram_total" in obj
    assert "energy_logp_mean_per_ngram_total" in obj
    assert "logp_mean_per_ngram_total" in obj
    assert "logp_mean_per_ngram_interior" in obj
    assert "logp_mean_per_ngram_penalized" in obj
    assert "penalty_hamming" in obj and "components" in obj and "windows" in obj
    assert isinstance(obj["components"], dict)
    assert "char_n2" in obj["components"]
    assert "wli_n2" in obj["components"]


def test_pct_win10_wli_numpy_vs_list_equivalence():
    """Regression guard: ndarray and list inputs must score identically."""
    _require_pct_assets()
    pt = np.asarray(plaintext1, dtype=np.uint8)
    wli_np = np.asarray(word_breaks1, dtype=np.uint8)
    wli_list = [tuple(map(int, pair)) for pair in wli_np.tolist()]

    cfg_c = CipherConfig(
        ciphertext=pt,
        wli_data=wli_np,
        key_length=None,
        initial_text_permutation_indices=None,
    )
    cfg_s = ScoringConfig(
        include_char=True,
        use_word_breaks=True,
        n_char=2,
        n_wli=2,
        dtype="float32",
    )
    scorer = build_scorer(cfg_c, cfg_s)

    score_np = float(scorer.score(pt, wli_np))
    score_list = float(scorer.score(pt, wli_list))
    assert score_np == pytest.approx(score_list, rel=0, abs=1e-8)

    pts = [pt, pt]
    wlis_np = [wli_np, wli_np]
    wlis_list = [wli_list, wli_list]
    bs_np = scorer.batch_score(pts, wlis_np)
    bs_list = scorer.batch_score(pts, wlis_list)
    np.testing.assert_allclose(bs_np, bs_list, rtol=0, atol=1e-8)


@pytest.mark.tier_a
@pytest.mark.skipif(not _cuda_available(), reason="CUDA not available")
def test_pct_win10_stats_cpu_cuda_parity():
    _require_pct_assets()
    pt = np.asarray(plaintext1, dtype=np.uint8)
    wli = np.asarray(word_breaks1, dtype=np.uint8)

    base = dict(ciphertext=pt, wli_data=wli, key_length=None)

    cpu = build_scorer(
        CipherConfig(**base),
        ScoringConfig(include_char=True, use_word_breaks=True, n_char=2, n_wli=2, dtype="float32"),
    )
    gpu = build_scorer(
        CipherConfig(**base, device=Device.CUDA),
        ScoringConfig(include_char=True, use_word_breaks=True, n_char=2, n_wli=2, impl=ScorerImpl.TORCH, dtype="float32"),
    )
    s_cpu = float(cpu.score(pt, wli))
    t_cpu = cpu.telemetry()
    s_gpu = float(gpu.score(pt, wli))
    t_gpu = gpu.telemetry()

    # Mean parity (you already had this very tight)
    assert abs(s_cpu - s_gpu) <= 3e-6

    # Std parity: keep the same tolerance band
    assert "score_std" in t_cpu and "score_std" in t_gpu
    assert abs(float(t_cpu["score_std"]) - float(t_gpu["score_std"])) <= 4e-6


@pytest.mark.tier_a
def test_pct_win10_batch_stats_present_numpy():
    _require_pct_assets()
    # Data
    pt = np.asarray(plaintext1, dtype=np.uint8)
    wli = np.asarray(word_breaks1, dtype=np.uint8)
    B = 3
    pts = [pt] * B
    wlis = [wli] * B

    # Scorer (NumPy on CPU)
    cfg_c = CipherConfig(
        ciphertext=pt,
        wli_data=wli,
        key_length=None,
        initial_text_permutation_indices=None,
    )
    cfg_s = ScoringConfig(
        include_char=True,
        use_word_breaks=True,
        n_char=2,
        n_wli=2,
        dtype="float32",
    )
    scorer = build_scorer(cfg_c, cfg_s)

    # Batch score
    bs = scorer.batch_score(pts, wlis)
    assert isinstance(bs, np.ndarray) and bs.shape == (B,)

    # Telemetry should include batch stats
    tel = scorer.telemetry()
    assert "score_mean_batch" in tel and "score_std_batch" in tel and "n_windows" in tel
    assert "stat.mean_per_ngram_penalized_batch" in tel
    assert len(tel["score_mean_batch"]) == B
    assert len(tel["score_std_batch"]) == B
    assert len(tel["stat.mean_per_ngram_penalized_batch"]) == B

    # n_windows sanity
    expected_nwin = aligned_window_count(length=int(pt.shape[0]), n_set=(2,), W=10, se_mode="nose", stride=1)
    assert tel["n_windows"] == expected_nwin

    # batch_score equals telemetry means
    np.testing.assert_allclose(
        bs,
        np.asarray(tel["score_mean_batch"], dtype=np.float32),
        rtol=0,
        atol=3e-6,
    )


def test_pct_win10_batch_score_with_raw_numpy():
    _require_pct_assets()
    pt = np.asarray(plaintext1, dtype=np.uint8)
    wli = np.asarray(word_breaks1, dtype=np.uint8)
    pts = [pt, pt]
    wlis = [wli, wli]

    cfg_c = CipherConfig(
        ciphertext=pt,
        wli_data=wli,
        key_length=None,
        initial_text_permutation_indices=None,
    )
    cfg_s = ScoringConfig(include_char=True, use_word_breaks=True, n_char=2, n_wli=2, dtype="float32")
    scorer = build_scorer(cfg_c, cfg_s)

    pct, raw = scorer.batch_score_with_raw(pts, wlis)
    assert isinstance(pct, np.ndarray) and isinstance(raw, np.ndarray)
    assert pct.shape == raw.shape == (2,)
    tel = scorer.telemetry()
    assert "stat.mean_per_ngram_penalized_batch" in tel


@pytest.mark.tier_a
@pytest.mark.skipif(not _cuda_available(), reason="CUDA not available")
def test_pct_win10_batch_stats_cpu_cuda_parity():
    _require_pct_assets()
    pt = np.asarray(plaintext1, dtype=np.uint8)
    wli = np.asarray(word_breaks1, dtype=np.uint8)
    B = 4
    pts = [pt] * B
    wlis = [wli] * B

    base = dict(ciphertext=pt, wli_data=wli, key_length=None)

    cpu = build_scorer(
        CipherConfig(**base),
        ScoringConfig(include_char=True, use_word_breaks=True, n_char=2, n_wli=2, dtype="float32"),
    )
    gpu = build_scorer(
        CipherConfig(**base, device=Device.CUDA),
        ScoringConfig(include_char=True, use_word_breaks=True, n_char=2, n_wli=2, impl=ScorerImpl.TORCH, dtype="float32"),
    )

    bs_cpu = cpu.batch_score(pts, wlis)
    bs_gpu = gpu.batch_score(pts, wlis)

    # Mean parity per batch element (tight like the single-item test)
    np.testing.assert_allclose(bs_cpu, bs_gpu, rtol=0, atol=3e-6)

    # Telemetry batch stats must be present on both
    t_cpu = cpu.telemetry()
    t_gpu = gpu.telemetry()
    for t in (t_cpu, t_gpu):
        assert "score_mean_batch" in t and "score_std_batch" in t and "n_windows" in t
