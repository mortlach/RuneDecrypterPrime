from __future__ import annotations
from rdp import api
import sys
import types
from types import SimpleNamespace
import numpy as np
import pytest
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.engine import builders
from rune_decrypter_prime.core.types import Device, ScorerImpl
pytestmark = pytest.mark.tier_a

class _DummyNumpy:

    def __init__(self, c_cfg, s_cfg):
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg

class _DummyTorch:

    def __init__(self, c_cfg, s_cfg):
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg

class _DummyUnified:

    def __init__(self, c_cfg, s_cfg):
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg

def _cipher_cfg(*, device: Device=Device.CPU) -> CipherConfig:
    return CipherConfig(ciphertext=np.asarray([0], dtype=np.uint8), wli_data=None, key_length=None, device=device)

def _patch_scorer_classes(monkeypatch: pytest.MonkeyPatch) -> None:
    numpy_module = types.ModuleType('rune_decrypter_prime.scoring.rune_scorer')
    numpy_module.RuneScorer = _DummyNumpy
    torch_module = types.ModuleType('rune_decrypter_prime.scoring.torch_rune_scorer')
    torch_module.RuneScorerTorch = _DummyTorch
    unified_module = types.ModuleType('rune_decrypter_prime.scoring.unified_rune_scorer')
    unified_module.UnifiedRuneScorer = _DummyUnified
    monkeypatch.setitem(sys.modules, 'rune_decrypter_prime.scoring.rune_scorer', numpy_module)
    monkeypatch.setitem(sys.modules, 'rune_decrypter_prime.scoring.torch_rune_scorer', torch_module)
    monkeypatch.setitem(sys.modules, 'rune_decrypter_prime.scoring.unified_rune_scorer', unified_module)

def test_build_scorer_reads_impl_from_scoring_config(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scorer_classes(monkeypatch)
    scorer = builders.build_scorer(
        _cipher_cfg(),
        api.ScoringConfig(backend=api.advanced.ScorerBackend.TORCH),
    )
    assert isinstance(scorer, _DummyTorch)

def test_build_scorer_reads_unified_impl_from_scoring_config(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scorer_classes(monkeypatch)
    scorer = builders.build_scorer(
        _cipher_cfg(),
        api.ScoringConfig(backend=api.advanced.ScorerBackend.UNIFIED),
    )
    assert isinstance(scorer, _DummyUnified)

def test_build_scorer_rejects_dict_configs() -> None:
    with pytest.raises(TypeError, match='cfg_cipher must be CipherConfig'):
        builders.build_scorer({'device': 'cpu'}, api.ScoringConfig())
    with pytest.raises(TypeError, match='s_cfg must be ScoringConfig'):
        builders.build_scorer(_cipher_cfg(), {'impl': 'numpy'})

def test_build_scorer_rejects_object_config_bags() -> None:
    with pytest.raises(TypeError, match='cfg_cipher must be CipherConfig'):
        builders.build_scorer(SimpleNamespace(device='cpu'), api.ScoringConfig())
    with pytest.raises(TypeError, match='s_cfg must be ScoringConfig'):
        builders.build_scorer(_cipher_cfg(), SimpleNamespace(impl=ScorerImpl.UNIFIED))

def test_build_scorer_auto_cpu_defaults_to_numpy(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scorer_classes(monkeypatch)
    scorer = builders.build_scorer(
        _cipher_cfg(device=Device.CPU),
        api.ScoringConfig(backend=api.advanced.ScorerBackend.AUTO),
    )
    assert isinstance(scorer, _DummyNumpy)


def test_build_scorer_cuda_unavailable_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builders, "select_backend", lambda _req: ("cpu", object()))
    with pytest.raises(RuntimeError, match="Requested accelerator is unavailable"):
        builders.build_scorer(
            _cipher_cfg(device=Device.CUDA),
            api.ScoringConfig(backend=api.advanced.ScorerBackend.NUMPY),
        )
