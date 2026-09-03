from __future__ import annotations
import pytest
from rdp.core.engine.builders import build_scorer
from rdp.scoring.rune_scorer import RuneScorer
from tests._helpers.configs import _mk_cfgs
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
pytestmark = pytest.mark.tier_a
try:
    import torch
except Exception:
    torch = None

def _make_wli(length: int, max_len: int=63) -> list[list[int]]:
    wli: list[list[int]] = []
    i = 0
    while i < length:
        ln = min(max_len, length - i)
        for j in range(ln):
            wli.append([j, ln])
        i += ln
    return wli

@pytest.mark.parametrize('encoding_dir', ['ltr', 'rtl'])
def test_backend_selection_cpu_uses_reference(encoding_dir: str):
    c_cfg, s_cfg = _mk_cfgs(device='cpu', encoding_dir=encoding_dir)
    scorer = build_scorer(c_cfg, s_cfg)
    assert isinstance(scorer, RuneScorer)

@pytest.mark.parametrize('encoding_dir', ['ltr', 'rtl'])
@pytest.mark.skipif(not (torch and torch.cuda.is_available()), reason='CUDA not available')
def test_backend_selection_cuda_prefers_torch(encoding_dir: str):
    from rdp.scoring.torch_rune_scorer import RuneScorerTorch
    c_cfg, s_cfg = _mk_cfgs(device='cuda', encoding_dir=encoding_dir)
    scorer = build_scorer(c_cfg, s_cfg)
    assert isinstance(scorer, RuneScorerTorch), 'CUDA build must select RuneScorerTorch'

@pytest.mark.skipif(not (torch and torch.cuda.is_available()), reason='CUDA not available')
def test_cuda_stats_align_with_cpu_reference():
    import numpy as np
    from rdp.scoring.torch_rune_scorer import RuneScorerTorch
    require_full_lm_assets(models=('char', 'wli'), modes=('ltr',), poses=('nose',), ns=(2,), ecdf_stats=('logp',))
    plaintext = np.arange(128, dtype=np.uint8) % 29
    wli = _make_wli(len(plaintext))
    c_cpu, s_cpu = _mk_cfgs(device='cpu', encoding_dir='ltr')
    cpu = build_scorer(c_cpu, s_cpu)
    assert isinstance(cpu, RuneScorer)
    c_cuda, s_cuda = _mk_cfgs(device='cuda', encoding_dir='ltr')
    cuda = build_scorer(c_cuda, s_cuda)
    assert isinstance(cuda, RuneScorerTorch)
    score_cpu = cpu.score(plaintext, wli)
    stats_cpu = cpu.last_stats()
    score_cuda = cuda.score(plaintext, wli)
    stats_cuda = cuda.last_stats()
    assert score_cuda == pytest.approx(score_cpu, rel=1e-05, abs=1e-07)
    for key in ('score_mean', 'score_std', 'n_windows'):
        assert key in stats_cpu and key in stats_cuda
        assert stats_cuda[key] == pytest.approx(stats_cpu[key], rel=1e-05, abs=1e-07)
