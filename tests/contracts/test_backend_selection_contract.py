from __future__ import annotations
import pytest
from rune_decrypter_prime.backends import xp

def test_explicit_cuda_request_does_not_silently_fallback_to_numpy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(xp, 'have_cupy', lambda: False)
    monkeypatch.setattr(xp, 'have_torch_cuda', lambda: False)
    with pytest.raises(RuntimeError, match='CUDA requested'):
        xp.select_backend('cuda')

def test_explicit_torch_request_does_not_fallback_to_numpy_when_torch_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(xp, '_torch', None)
    with pytest.raises(ImportError, match='torch not available'):
        xp.select_backend('torch')

def test_auto_request_may_fallback_to_numpy_when_optional_backends_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(xp, '_torch', None)
    monkeypatch.setattr(xp, '_cp', None)
    monkeypatch.setattr(xp, 'have_cupy', lambda: False)
    monkeypatch.setattr(xp, 'have_torch_cuda', lambda: False)
    device, backend = xp.select_backend('auto')
    assert device == 'cpu'
    assert backend.backend == 'numpy'
