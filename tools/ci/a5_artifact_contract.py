from __future__ import annotations
import email
import json
import tarfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
ROOT = Path(__file__).resolve().parents[2]
WHEEL_DIRS = (ROOT / 'wheelhouse', ROOT / 'dist')
SDIST_DIR = ROOT / 'dist'
CI_MANIFEST = ROOT / 'assets_manifest_ci_light_v1.json'
BLOCKED = ('rune_decrypter_prime/ciphers/dev/', 'rune_decrypter_prime/keyops/dev/', 'rune_decrypter_prime/data/liber_primus/old/')
REQUIRED_NATIVE_STEMS = ('_fastlm', '_hamming', '_span_hamming_fast')
WHEEL_ASSET_PREFIX = 'rune_decrypter_prime/data/assets/'
WHEEL_CI_MANIFEST = 'rune_decrypter_prime/data/assets_manifest_ci_light_v1.json'
INDEX_REL = 'language_model/lmp/index.json'

def _wheel() -> Path:
    found = [p for d in WHEEL_DIRS if d.exists() for p in d.glob('*.whl')]
    if len(found) != 1:
        raise RuntimeError(f'expected exactly one wheel, found {len(found)}: {found}')
    return found[0]

def _sdist() -> Path:
    found = list(SDIST_DIR.glob('*.tar.gz')) if SDIST_DIR.exists() else []
    if len(found) != 1:
        raise RuntimeError(f'expected exactly one sdist, found {len(found)}: {found}')
    return found[0]

def _blocked(names):
    bad = []
    for name in names:
        n = name.replace('\\', '/')
        for prefix in BLOCKED:
            if prefix in n:
                bad.append(n)
    return sorted(set(bad))

def _ci_paths() -> list[str]:
    data = json.loads(CI_MANIFEST.read_text(encoding='utf-8'))
    rows = data.get('installed_assets')
    if not isinstance(rows, list) or not rows:
        raise RuntimeError('CI-light manifest installed_assets missing')
    return [str(row['final_relpath']) for row in rows]

def _strip_sdist_root(name: str) -> str:
    parts = PurePosixPath(name.replace('\\', '/')).parts
    return PurePosixPath(*parts[1:]).as_posix() if len(parts) > 1 else ''

def main() -> int:
    wheel = _wheel()
    sdist = _sdist()
    ci_paths = _ci_paths()
    expected_wheel_assets = {WHEEL_ASSET_PREFIX + rel for rel in ci_paths}
    expected_wheel_assets.add(WHEEL_ASSET_PREFIX + INDEX_REL)
    with ZipFile(wheel) as zf:
        names = zf.namelist()
        names_set = set(names)
        bad = _blocked(names)
        if bad:
            raise AssertionError(f'blocked wheel members: {bad[:20]}')
        if not any((n.startswith('rune_decrypter_prime/') for n in names)):
            raise AssertionError('production package missing')
        if not any((n.startswith('rdp/') for n in names)):
            raise AssertionError('rdp facade missing')
        for stem in REQUIRED_NATIVE_STEMS:
            if not any((stem in n for n in names)):
                raise AssertionError(f'native module missing: {stem}')
        if WHEEL_CI_MANIFEST not in names_set:
            raise AssertionError('packaged CI-light manifest missing')
        missing = sorted(expected_wheel_assets - names_set)
        if missing:
            raise AssertionError(f'CI-light wheel assets missing: {missing[:20]}')
        actual_asset_members = {n for n in names if n.startswith(WHEEL_ASSET_PREFIX) and (not n.endswith('/'))}
        unexpected = sorted(actual_asset_members - expected_wheel_assets)
        if unexpected:
            raise AssertionError(f'unexpected wheel assets (possible local full_v1 leak): {unexpected[:20]}')
        meta_name = next((n for n in names if n.endswith('.dist-info/METADATA')))
        meta = email.message_from_bytes(zf.read(meta_name))
        reqs = [v.lower() for v in meta.get_all('Requires-Dist') or []]
        if not any((v.startswith('lark') for v in reqs)):
            raise AssertionError('lark runtime dependency missing from wheel metadata')
    with tarfile.open(sdist, 'r:gz') as tf:
        members = tf.getmembers()
        names = [member.name for member in members]
        bad = _blocked(names)
        if bad:
            raise AssertionError(f'blocked sdist members: {bad[:20]}')
        rel_names = {_strip_sdist_root(n) for n in names}
        rel_files = {_strip_sdist_root(member.name) for member in members if member.isfile()}
        expected_sdist_assets = {'assets/' + rel for rel in ci_paths}
        expected_sdist_assets.add('assets/' + INDEX_REL)
        missing = sorted(expected_sdist_assets - rel_names)
        if missing:
            raise AssertionError(f'CI-light sdist assets missing: {missing[:20]}')
        actual_lm_files = {n for n in rel_files if n.startswith('assets/language_model/lmp/')}
        unexpected = sorted(actual_lm_files - expected_sdist_assets)
        if unexpected:
            raise AssertionError(f'unexpected sdist LM assets (possible local full_v1 leak): {unexpected[:20]}')
        forbidden = [n for n in names if '/output/' in n or '/.git/' in n or '__pycache__' in n]
        if forbidden:
            raise AssertionError(f'generated/private members in sdist: {forbidden[:20]}')
    print(f'[a5-artifact-contract] PASS wheel={wheel.name} sdist={sdist.name} ci_assets={len(ci_paths)}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
