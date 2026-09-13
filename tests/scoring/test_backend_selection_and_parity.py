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


@pytest.mark.parametrize('device', ['cpu', 'cuda'])
@pytest.mark.parametrize('dtype_form', ['numpy_type', 'numpy_dtype', 'torch_dtype'])
def test_torch_array_adapter_accepts_solver_dtypes(device, dtype_form):
    import numpy as np
    from rdp.backends.xp import _TorchXP
    if torch is None:
        pytest.skip('Torch not available')
    if device == 'cuda' and not torch.cuda.is_available():
        pytest.skip('CUDA not available')
    xp = _TorchXP(device)
    dtype = {'numpy_type': np.int16, 'numpy_dtype': np.dtype('int16'),
             'torch_dtype': torch.int16}[dtype_form]
    keys = np.array([[20, 6, 22], [19, 28, 11]], dtype=np.uint8)
    array = xp.asarray(keys, dtype=dtype)
    assert array.dtype == torch.int16 and array.device.type == device
    np.testing.assert_array_equal(xp.to_numpy(array), keys)
    for value in (xp.arange(3, dtype=dtype), xp.zeros((2, 3), dtype=dtype),
                  xp.zeros_like(array, dtype=dtype), xp.empty((2, 3), dtype=dtype),
                  xp.empty_like(array, dtype=dtype), xp.full((2, 3), 7, dtype=dtype),
                  xp.astype(xp.asarray(keys), dtype)):
        assert value.dtype == torch.int16 and value.device.type == device
    np.testing.assert_array_equal(xp.to_numpy(xp.arange(3, dtype=dtype)), [0, 1, 2])
    np.testing.assert_array_equal(xp.to_numpy(xp.astype(xp.asarray(keys), dtype)), keys)
    assert xp.asarray(keys).dtype == torch.uint8
    assert xp.zeros_like(array).dtype == torch.int16
    with pytest.raises(TypeError):
        xp.asarray(keys, dtype=np.dtype('O'))
