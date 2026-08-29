from __future__ import annotations
import json
from pathlib import Path
import pytest
from rune_decrypter_prime.scoring.language_model.paths import load_index, resolve_lm_root

def _write_index(root: Path, *, payload: dict | None=None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / 'index.json').write_text(json.dumps(payload if payload is not None else {'version': 'test.v1', 'base': '.', 'ecdf_root': 'ecdf', 'joint_root': 'joint', 'models': {}}), encoding='utf-8')

def test_resolve_lm_root_accepts_existing_absolute_config_path(tmp_path: Path) -> None:
    _write_index(tmp_path)
    assert resolve_lm_root({'model_root': tmp_path}) == tmp_path.resolve()

def test_resolve_lm_root_rejects_missing_path_with_safe_display_message(tmp_path: Path) -> None:
    missing = tmp_path / 'missing_model'
    with pytest.raises(FileNotFoundError, match='Language-model root not found') as excinfo:
        resolve_lm_root({'model_root': missing})
    message = str(excinfo.value)
    assert 'Available local asset models' in message
    assert 'Requested:' in message

def test_load_index_rejects_missing_index_with_clear_message(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match='LM index.json not found'):
        load_index(tmp_path)

def test_load_index_rejects_missing_models_key(tmp_path: Path) -> None:
    _write_index(tmp_path, payload={'version': 'test.v1', 'base': '.', 'ecdf_root': 'ecdf', 'joint_root': 'joint'})
    with pytest.raises(ValueError, match="missing required key 'models'"):
        load_index(tmp_path)

def test_load_index_returns_structured_index_object(tmp_path: Path) -> None:
    _write_index(tmp_path)
    idx = load_index(tmp_path)
    assert idx.version == 'test.v1'
    assert idx.ecdf_root == 'ecdf'
    assert isinstance(idx.models, dict)
