from __future__ import annotations
from rdp import api
import builtins
import sys
import tomllib
from pathlib import Path
import pytest
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.engine.builders import build_scorer

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / 'pyproject.toml'

def _pyproject() -> dict:
    assert PYPROJECT.exists(), f'missing pyproject.toml: {PYPROJECT}'
    return tomllib.loads(PYPROJECT.read_text(encoding='utf-8'))

def test_torch_is_declared_as_optional_v1_extra() -> None:
    optional = _pyproject()['project']['optional-dependencies']
    assert 'torch' in optional
    assert 'test-torch' in optional
    assert 'torch' in optional['torch']
    assert 'torch' in optional['test-torch']

def test_torch_pytest_marker_is_declared() -> None:
    markers = _pyproject()['tool']['pytest']['ini_options']['markers']
    assert any((marker.startswith('torch:') for marker in markers))

def test_requested_torch_scorer_errors_when_torch_runtime_unavailable(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, 'rune_decrypter_prime.scoring.torch_rune_scorer', raising=False)
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'rune_decrypter_prime.scoring.torch_rune_scorer':
            raise ModuleNotFoundError("No module named 'torch'", name='torch')
        return real_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, '__import__', fake_import)
    cfg = CipherConfig(ciphertext=[0, 1, 2, 3], wli_data=[], key_length=4)
    with pytest.raises(RuntimeError) as excinfo:
        build_scorer(cfg, api.ScoringConfig(backend=api.advanced.ScorerBackend.TORCH))
    message = str(excinfo.value)
    assert 'Requested scorer implementation is unavailable' in message
    assert "'torch'" in message
    assert "impl='numpy'" in message
    assert "device='cpu'" in message
