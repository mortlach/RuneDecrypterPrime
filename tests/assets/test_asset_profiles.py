from __future__ import annotations
import json
import subprocess
from pathlib import Path
import pytest
from tools.assets.asset_profiles import AssetProfileError, load_asset_profiles, select_asset_profile
from tools.assets.release_asset_installer import load_manifest
ROOT = Path(__file__).resolve().parents[2]
PROFILE_MANIFEST = ROOT / 'asset_profiles_v1.json'
RELEASE_MANIFEST = ROOT / 'assets_manifest_v1.json'
CI_MANIFEST = ROOT / 'assets_manifest_ci_light_v1.json'
pytestmark = pytest.mark.tier_a

def test_canonical_asset_profiles_are_exact_and_default_to_full_v1() -> None:
    default, profiles = load_asset_profiles(PROFILE_MANIFEST)
    assert default == 'full_v1'
    assert tuple(profiles) == ('ci_light', 'full_v1')
    assert profiles['ci_light'].language_model_orders == (1, 2)
    assert profiles['ci_light'].download_release_assets is False
    assert profiles['ci_light'].pytest_marker_expression == 'not full_assets'
    assert profiles['full_v1'].language_model_orders == (1, 2, 3, 4)
    assert profiles['full_v1'].download_release_assets is True
    assert profiles['full_v1'].pytest_marker_expression is None

def test_profile_asset_sets_exist_and_full_v1_uses_github_release_assets() -> None:
    _default, profiles = load_asset_profiles(PROFILE_MANIFEST)
    release = load_manifest(RELEASE_MANIFEST)
    ci = load_manifest(CI_MANIFEST)
    assert profiles['ci_light'].verification_manifest == CI_MANIFEST.name
    assert profiles['full_v1'].verification_manifest == RELEASE_MANIFEST.name
    assert profiles['ci_light'].release_asset_set in ci['release_asset_sets']
    assert profiles['full_v1'].release_asset_set in release['release_asset_sets']
    assert ci['release_asset_sets']['v1_lm_ci_light']['bundled_with_source'] is True
    full = release['release_asset_sets']['v1_lm_runtime_full']
    assert full['release_repository'] == 'mortlach/rdp_assets'
    assert full['release_tag'] == 'rdp-v1.0.0-lm-large'
    assert full['release_assets']
    assert all((item['url'].startswith('https://github.com/mortlach/rdp_assets/releases/download/') for item in full['release_assets']))

def test_ci_light_manifest_rows_are_source_bundled_and_hash_exact() -> None:
    release = load_manifest(CI_MANIFEST)
    rows = [row for row in release['installed_assets'] if 'v1_lm_ci_light' in row['required_for']]
    assert len(rows) == 33
    assert any((row['final_relpath'].endswith('index.json') for row in rows))
    assert not any(('_n3_' in row['final_relpath'] or '_n4_' in row['final_relpath'] for row in rows))
    from tools.assets.release_asset_installer import verify_installed_assets
    verify_installed_assets(release, 'v1_lm_ci_light', ROOT / 'assets')

def test_ci_light_manifest_text_asset_preserves_exact_checkout_bytes() -> None:
    attributes = (ROOT / '.gitattributes').read_text(encoding='utf-8').splitlines()
    assert 'assets/language_model/lmp/index.json -text' in attributes
    index_bytes = (ROOT / 'assets' / 'language_model' / 'lmp' / 'index.json').read_bytes()
    assert b'\r\n' not in index_bytes
    assert len(index_bytes) == 627

def test_full_v1_manifest_preserves_the_same_canonical_source_index() -> None:
    ci_manifest = load_manifest(CI_MANIFEST)
    full_manifest = load_manifest(RELEASE_MANIFEST)
    ci_index = next((row for row in ci_manifest['installed_assets'] if row['final_relpath'] == 'language_model/lmp/index.json'))
    full_index = next((row for row in full_manifest['installed_assets'] if row['final_relpath'] == 'language_model/lmp/index.json'))
    assert full_index['sha256'] == ci_index['sha256']
    assert full_index['size_bytes'] == ci_index['size_bytes'] == 627
    assert full_index['install_policy'] == 'preserve_existing_verified'

def test_full_only_asset_paths_are_gitignored() -> None:
    full_manifest = load_manifest(RELEASE_MANIFEST)
    ci_manifest = load_manifest(CI_MANIFEST)
    ci_paths = {row['final_relpath'] for row in ci_manifest['installed_assets']}
    full_only_paths = {
        row['final_relpath']
        for row in full_manifest['installed_assets']
        if row['final_relpath'] not in ci_paths
    }
    assert full_only_paths
    offenders = []
    for relpath in sorted(full_only_paths):
        completed = subprocess.run(
            ['git', 'check-ignore', '--no-index', '-q', f'assets/{relpath}'],
            cwd=ROOT,
            check=False,
        )
        if completed.returncode != 0:
            offenders.append(relpath)
    assert offenders == []

def test_unknown_or_malformed_profile_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(AssetProfileError, match='unknown asset profile'):
        select_asset_profile(PROFILE_MANIFEST, 'not_a_profile')
    raw = json.loads(PROFILE_MANIFEST.read_text(encoding='utf-8'))
    raw['profiles']['ci_light']['language_model_orders'] = [2, 1]
    bad = tmp_path / 'bad.json'
    bad.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(AssetProfileError, match='unique sorted orders'):
        load_asset_profiles(bad)
    raw = json.loads(PROFILE_MANIFEST.read_text(encoding='utf-8'))
    raw['profiles']['ci_light']['verification_manifest'] = '../outside.json'
    bad.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(AssetProfileError, match='safe repository-relative path'):
        load_asset_profiles(bad)
