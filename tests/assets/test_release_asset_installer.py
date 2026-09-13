from __future__ import annotations
import hashlib
import json
import pathlib
import zipfile
import pytest
from tools.assets.release_asset_installer import AssetInstallError, install_release_asset_set, load_manifest, safe_extract_zip, select_release_asset_set, verify_file
pytestmark = pytest.mark.tier_a

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _write_zip(path: pathlib.Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)

def _manifest(tmp_path: pathlib.Path, zip_path: pathlib.Path, payload: bytes) -> pathlib.Path:
    manifest = {'schema_version': 2, 'assets_root': 'assets', 'release_asset_sets': {'v1_lm_runtime_full': {'required_by_default_install': True, 'description': 'Tiny fake LM asset set.', 'release_repository': 'mortlach/RuneDecrypterPrime', 'release_tag': 'v1.0.0-assets-lm-large-test', 'release_assets': [{'name': zip_path.name, 'url': zip_path.as_uri(), 'sha256': _sha256(zip_path.read_bytes()), 'size_bytes': zip_path.stat().st_size}]}, 'v1_lm_large_required': {'required_by_default_install': True, 'description': 'Tiny fake required large set.', 'included_in': 'v1_lm_runtime_full'}}, 'installed_assets': [{'asset_id': 'lm.lmp.fake.n3', 'final_relpath': 'language_model/lmp/fake_n3.bin.zst', 'sha256': _sha256(payload), 'size_bytes': len(payload), 'required_for': ['v1_lm_runtime_full', 'v1_lm_large_required'], 'policy': 'required_large_v1_lm_asset'}]}
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    return path

def test_valid_manifest_loads_and_child_set_uses_parent_release_assets(tmp_path: pathlib.Path) -> None:
    payload = b'fake n3 model'
    zip_path = tmp_path / 'rdp-v1-lm-large-part001.zip'
    _write_zip(zip_path, {'language_model/lmp/fake_n3.bin.zst': payload})
    manifest = load_manifest(_manifest(tmp_path, zip_path, payload))
    selected = select_release_asset_set(manifest, 'v1_lm_large_required')
    assert selected['release_assets'][0]['name'] == 'rdp-v1-lm-large-part001.zip'

def test_child_asset_set_verifies_only_child_installed_rows(tmp_path: pathlib.Path) -> None:
    payload = b'fake n3 model'
    zip_path = tmp_path / 'rdp-v1-lm-large-part001.zip'
    _write_zip(zip_path, {'language_model/lmp/fake_n2.bin.zst': b'fake n2 model', 'language_model/lmp/fake_n3.bin.zst': payload})
    manifest_path = _manifest(tmp_path, zip_path, payload)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['installed_assets'].append({'asset_id': 'lm.lmp.fake.n2', 'final_relpath': 'language_model/lmp/fake_n2.bin.zst', 'sha256': _sha256(b'fake n2 model'), 'size_bytes': len(b'fake n2 model'), 'required_for': ['v1_lm_runtime_full'], 'policy': 'required_v1_lm_runtime_asset'})
    manifest['release_asset_sets']['v1_lm_runtime_full']['release_assets'][0]['sha256'] = _sha256(zip_path.read_bytes())
    manifest['release_asset_sets']['v1_lm_runtime_full']['release_assets'][0]['size_bytes'] = zip_path.stat().st_size
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    install_release_asset_set(manifest_path, 'v1_lm_large_required', tmp_path / 'downloads', tmp_path / 'assets')

def test_install_reuses_valid_download_and_verifies_final_asset(tmp_path: pathlib.Path) -> None:
    payload = b'fake n3 model'
    source_zip = tmp_path / 'source.zip'
    _write_zip(source_zip, {'language_model/lmp/fake_n3.bin.zst': payload})
    manifest_path = _manifest(tmp_path, source_zip, payload)
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    (downloads / source_zip.name).write_bytes(source_zip.read_bytes())
    install_release_asset_set(manifest_path, 'v1_lm_large_required', downloads, tmp_path / 'assets')
    verify_file(tmp_path / 'assets' / 'language_model' / 'lmp' / 'fake_n3.bin.zst', _sha256(payload), len(payload))

def test_install_preserves_verified_source_bundled_asset(tmp_path: pathlib.Path) -> None:
    payload = b'fake n3 model'
    canonical_index = b'{\n  "version": "v1"\n}\n'
    archived_index = canonical_index.replace(b'\n', b'\r\n')
    source_zip = tmp_path / 'source.zip'
    _write_zip(source_zip, {'language_model/lmp/fake_n3.bin.zst': payload, 'language_model/lmp/index.json': archived_index})
    manifest_path = _manifest(tmp_path, source_zip, payload)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['installed_assets'].append({'asset_id': 'lm.lmp.index.json', 'final_relpath': 'language_model/lmp/index.json', 'sha256': _sha256(canonical_index), 'size_bytes': len(canonical_index), 'required_for': ['v1_lm_runtime_full'], 'policy': 'source_bundled_shared_v1_asset', 'install_policy': 'preserve_existing_verified'})
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    index_path = tmp_path / 'assets' / 'language_model' / 'lmp' / 'index.json'
    index_path.parent.mkdir(parents=True)
    index_path.write_bytes(canonical_index)
    install_release_asset_set(manifest_path, 'v1_lm_runtime_full', tmp_path / 'downloads', tmp_path / 'assets')
    assert index_path.read_bytes() == canonical_index
    verify_file(index_path, _sha256(canonical_index), len(canonical_index))
    verify_file(tmp_path / 'assets' / 'language_model' / 'lmp' / 'fake_n3.bin.zst', _sha256(payload), len(payload))

def test_install_rejects_invalid_preserved_source_bundled_asset(tmp_path: pathlib.Path) -> None:
    payload = b'fake n3 model'
    canonical_index = b'{\n  "version": "v1"\n}\n'
    source_zip = tmp_path / 'source.zip'
    _write_zip(source_zip, {'language_model/lmp/fake_n3.bin.zst': payload, 'language_model/lmp/index.json': canonical_index.replace(b'\n', b'\r\n')})
    manifest_path = _manifest(tmp_path, source_zip, payload)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['installed_assets'].append({'asset_id': 'lm.lmp.index.json', 'final_relpath': 'language_model/lmp/index.json', 'sha256': _sha256(canonical_index), 'size_bytes': len(canonical_index), 'required_for': ['v1_lm_runtime_full'], 'policy': 'source_bundled_shared_v1_asset', 'install_policy': 'preserve_existing_verified'})
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    index_path = tmp_path / 'assets' / 'language_model' / 'lmp' / 'index.json'
    index_path.parent.mkdir(parents=True)
    index_path.write_bytes(b'corrupt')
    with pytest.raises(AssetInstallError, match='preserved source-bundled asset is invalid'):
        install_release_asset_set(manifest_path, 'v1_lm_runtime_full', tmp_path / 'downloads', tmp_path / 'assets')
    assert index_path.read_bytes() == b'corrupt'

def test_corrupt_existing_download_is_rejected_then_replaced_from_url(tmp_path: pathlib.Path) -> None:
    payload = b'fake n4 model'
    source_zip = tmp_path / 'source.zip'
    _write_zip(source_zip, {'language_model/lmp/fake_n3.bin.zst': payload})
    manifest_path = _manifest(tmp_path, source_zip, payload)
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    (downloads / source_zip.name).write_bytes(b'corrupt')
    install_release_asset_set(manifest_path, 'v1_lm_runtime_full', downloads, tmp_path / 'assets')
    assert (downloads / source_zip.name).read_bytes() == source_zip.read_bytes()

def test_bundle_sha_mismatch_fails(tmp_path: pathlib.Path) -> None:
    payload = b'fake n3 model'
    zip_path = tmp_path / 'source.zip'
    _write_zip(zip_path, {'language_model/lmp/fake_n3.bin.zst': payload})
    manifest_path = _manifest(tmp_path, zip_path, payload)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['release_asset_sets']['v1_lm_runtime_full']['release_assets'][0]['sha256'] = '0' * 64
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(AssetInstallError, match='SHA256 mismatch'):
        install_release_asset_set(manifest_path, 'v1_lm_runtime_full', tmp_path / 'downloads', tmp_path / 'assets')

def test_final_runtime_sha_mismatch_fails(tmp_path: pathlib.Path) -> None:
    payload = b'fake n3 model'
    zip_path = tmp_path / 'source.zip'
    _write_zip(zip_path, {'language_model/lmp/fake_n3.bin.zst': b'wrong'})
    manifest_path = _manifest(tmp_path, zip_path, payload)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['release_asset_sets']['v1_lm_runtime_full']['release_assets'][0]['sha256'] = _sha256(zip_path.read_bytes())
    manifest['release_asset_sets']['v1_lm_runtime_full']['release_assets'][0]['size_bytes'] = zip_path.stat().st_size
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(AssetInstallError, match='lm.lmp.fake.n3'):
        install_release_asset_set(manifest_path, 'v1_lm_runtime_full', tmp_path / 'downloads', tmp_path / 'assets')

def test_safe_extract_rejects_parent_traversal(tmp_path: pathlib.Path) -> None:
    zip_path = tmp_path / 'bad.zip'
    _write_zip(zip_path, {'../escape.txt': b'bad'})
    with pytest.raises(AssetInstallError, match='must not contain'):
        safe_extract_zip(zip_path, tmp_path / 'assets')

def test_safe_extract_rejects_absolute_member(tmp_path: pathlib.Path) -> None:
    zip_path = tmp_path / 'bad.zip'
    _write_zip(zip_path, {'/absolute.txt': b'bad'})
    with pytest.raises(AssetInstallError, match='must not be absolute'):
        safe_extract_zip(zip_path, tmp_path / 'assets')

def test_manifest_rejects_duplicate_asset_ids(tmp_path: pathlib.Path) -> None:
    payload = b'fake'
    zip_path = tmp_path / 'source.zip'
    _write_zip(zip_path, {'language_model/lmp/fake_n3.bin.zst': payload})
    manifest_path = _manifest(tmp_path, zip_path, payload)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['installed_assets'].append(dict(manifest['installed_assets'][0]))
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(AssetInstallError, match='duplicate asset_id'):
        load_manifest(manifest_path)

def test_manifest_rejects_duplicate_final_paths(tmp_path: pathlib.Path) -> None:
    payload = b'fake'
    zip_path = tmp_path / 'source.zip'
    _write_zip(zip_path, {'language_model/lmp/fake_n3.bin.zst': payload})
    manifest_path = _manifest(tmp_path, zip_path, payload)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    second = dict(manifest['installed_assets'][0])
    second['asset_id'] = 'lm.lmp.fake.other'
    manifest['installed_assets'].append(second)
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(AssetInstallError, match='duplicate final_relpath'):
        load_manifest(manifest_path)
