from __future__ import annotations
import importlib
import sys
from pathlib import Path
import pytest
pytestmark = pytest.mark.tier_a
_HAMMING_MODULES = ['rdp.scoring.hamming.loader', 'rdp.scoring.hamming.backend', 'rdp.scoring.hamming']

def _clear_hamming_modules() -> None:
    for name in _HAMMING_MODULES:
        sys.modules.pop(name, None)

def test_hamming_package_import_does_not_resolve_repo_assets(monkeypatch: pytest.MonkeyPatch) -> None:
    import rdp.data.asset_paths as asset_paths

    def _bomb(*_args, **_kwargs):
        raise AssertionError('asset resolution must not run during hamming package import')
    monkeypatch.setattr(asset_paths, 'resolve_assets_path', _bomb)
    _clear_hamming_modules()
    try:
        module = importlib.import_module('rdp.scoring.hamming')
        assert module.__all__ == ['HammingBackend', 'load_raw1grams_wordlists']
    finally:
        _clear_hamming_modules()

def test_hamming_loader_import_does_not_resolve_repo_assets(monkeypatch: pytest.MonkeyPatch) -> None:
    import rdp.data.asset_paths as asset_paths

    def _bomb(*_args, **_kwargs):
        raise AssertionError('asset resolution must not run during hamming loader import')
    monkeypatch.setattr(asset_paths, 'resolve_assets_path', _bomb)
    _clear_hamming_modules()
    try:
        loader = importlib.import_module('rdp.scoring.hamming.loader')
        assert callable(loader.load_raw1grams_wordlists)
    finally:
        _clear_hamming_modules()

def test_hamming_loader_resolves_default_assets_only_when_called(monkeypatch: pytest.MonkeyPatch) -> None:
    import rdp.data.asset_paths as asset_paths

    def _bomb(*_args, **_kwargs):
        raise FileNotFoundError('expected test sentinel')
    monkeypatch.setattr(asset_paths, 'resolve_assets_path', _bomb)
    _clear_hamming_modules()
    try:
        loader = importlib.import_module('rdp.scoring.hamming.loader')
        with pytest.raises(FileNotFoundError, match='expected test sentinel'):
            loader.load_raw1grams_wordlists()
    finally:
        _clear_hamming_modules()

def test_hamming_loader_explicit_dir_does_not_need_repo_root(tmp_path: Path) -> None:
    _clear_hamming_modules()
    try:
        loader = importlib.import_module('rdp.scoring.hamming.loader')
        with pytest.raises(FileNotFoundError, match='No raw1grams_\\*.csv files found'):
            loader.load_raw1grams_wordlists(tmp_path)
    finally:
        _clear_hamming_modules()
