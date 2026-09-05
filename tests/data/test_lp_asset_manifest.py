from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pytest
import rdp.data.liber_primus.lp_main as lp_main
pytestmark = pytest.mark.tier_a

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def test_lp_main_transcript_has_manifest_integrity_entry() -> None:
    root = _repo_root()
    manifest = json.loads((root / 'assets_manifest_v1.json').read_text(encoding='utf-8'))
    rows = [row for row in manifest['required_assets'] if row.get('asset_id') == 'liber_primus.main_transcript']
    assert len(rows) == 1
    row = rows[0]
    assert row['version_scheme'] == 'sha256'
    assert row['asset_version'] == row['sha256']
    assert row['final_relpath'] == 'liber_primus/liber-primus__transcription--master-v2.txt'
    assert row['parts'] == ['liber_primus/liber-primus__transcription--master-v2.txt.part001']
    packed_part = root / manifest['packed_root'] / row['parts'][0]
    assert packed_part.is_file()
    assert packed_part.stat().st_size == row['size_bytes']
    assert _sha256(packed_part) == row['sha256']
    installed = root / manifest['assets_root'] / row['final_relpath']
    assert installed.read_bytes() == packed_part.read_bytes()
    assert lp_main.default_main_transcript_path() == installed.resolve()

def test_lp_main_transcript_identity_returns_fresh_mutable_copy() -> None:
    lp_main._cached_main_transcript_asset_identity.cache_clear()
    first = lp_main.main_transcript_asset_identity()
    first['asset_version'] = 'bad'
    second = lp_main.main_transcript_asset_identity()
    assert second == {'asset_id': 'liber_primus.main_transcript', 'asset_version': 'ad516b6d88106d68b3334cee0800ac83fa2e4d27c1a5c52bf8b0c2fb3ebc45d6'}
    assert second is not first

def test_lp_main_transcript_identity_rejects_duplicate_manifest_rows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    row = {'asset_id': 'liber_primus.main_transcript', 'asset_version': 'a' * 64, 'version_scheme': 'sha256', 'sha256': 'a' * 64}
    manifest = {'required_assets': [row, dict(row)]}
    (tmp_path / 'assets_manifest_v1.json').write_text(json.dumps(manifest), encoding='utf-8')
    lp_main._cached_main_transcript_asset_identity.cache_clear()
    monkeypatch.setattr(lp_main, 'find_repo_root', lambda _start: tmp_path)
    try:
        with pytest.raises(RuntimeError, match='expected exactly one'):
            lp_main.main_transcript_asset_identity()
    finally:
        lp_main._cached_main_transcript_asset_identity.cache_clear()

def test_lp_main_transcript_identity_rejects_version_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manifest = {'required_assets': [{'asset_id': 'liber_primus.main_transcript', 'asset_version': 'a' * 64, 'version_scheme': 'sha256', 'sha256': 'b' * 64}]}
    (tmp_path / 'assets_manifest_v1.json').write_text(json.dumps(manifest), encoding='utf-8')
    lp_main._cached_main_transcript_asset_identity.cache_clear()
    monkeypatch.setattr(lp_main, 'find_repo_root', lambda _start: tmp_path)
    try:
        with pytest.raises(RuntimeError, match='asset_version must match sha256'):
            lp_main.main_transcript_asset_identity()
    finally:
        lp_main._cached_main_transcript_asset_identity.cache_clear()
