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
BLOCKED = (
    'rune_decrypter_prime/',
    'rdp/utils/',
    'rdp/ciphers/dev/',
    'rdp/keyops/dev/',
    'rdp/data/cipher_tests/',
)
SDIST_BLOCKED_PREFIXES = (
    'tests/',
    'tutorials/',
    'cipher_development/',
    'solving/',
    'tools/',
)
SDIST_METADATA_PREFIX = 'src/rune_decrypter_prime.egg-info'
REQUIRED_NATIVE_STEMS = ('_fastlm', '_hamming', '_span_hamming_fast')
REQUIRED_NATIVE_PREFIXES = (
    'rdp/scoring/language_model/_fastlm',
    'rdp/scoring/hamming/_hamming',
    'rdp/scoring/span_hamming/_span_hamming_fast',
)
REQUIRED_NATIVE_SOURCES = {
    'src/rdp/scoring/language_model/fastlm.cpp',
    'src/rdp/scoring/hamming/Flat2DArray.cpp',
    'src/rdp/scoring/hamming/Flat2DArray.h',
    'src/rdp/scoring/hamming/Hamming.cpp',
    'src/rdp/scoring/hamming/Hamming.h',
    'src/rdp/scoring/hamming/Types.h',
    'src/rdp/scoring/hamming/bindings.cpp',
    'src/rdp/scoring/span_hamming/FastSpanHamming.h',
    'src/rdp/scoring/span_hamming/fast_bindings.cpp',
    'src/rdp/scoring/ngram_hamming/FastNgramHamming.h',
    'src/rdp/scoring/ngram_hamming/fast_bindings.cpp',
}
WHEEL_ASSET_PREFIX = 'rdp/data/assets/'
WHEEL_CI_MANIFEST = 'rdp/data/assets_manifest_ci_light_v1.json'
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
        native_sources = sorted(
            n for n in names if PurePosixPath(n).suffix.lower() in {'.cpp', '.h', '.hpp'}
        )
        if native_sources:
            raise AssertionError(f'native source files must not be installed in wheel: {native_sources[:20]}')
        if not any((n.startswith('rdp/') for n in names)):
            raise AssertionError('production package missing')
        for stem in REQUIRED_NATIVE_STEMS:
            if not any((stem in n for n in names)):
                raise AssertionError(f'native module missing: {stem}')
        for prefix in REQUIRED_NATIVE_PREFIXES:
            if not any((n.startswith(prefix) for n in names)):
                raise AssertionError(f'native module has wrong qualified path: {prefix}')
        if any(
            PurePosixPath(n).name.startswith('_ngram_hamming_fast.')
            and PurePosixPath(n).suffix in {'.pyd', '.so'}
            for n in names
        ):
            raise AssertionError('experimental _ngram_hamming_fast must remain unbuilt')
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
        top_level_name = next((n for n in names if n.endswith('.dist-info/top_level.txt')))
        if zf.read(top_level_name).decode('utf-8').split() != ['rdp']:
            raise AssertionError('wheel top_level.txt must contain only rdp')
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
        blocked_support = sorted(
            name
            for name in rel_names
            if any(name == prefix[:-1] or name.startswith(prefix) for prefix in SDIST_BLOCKED_PREFIXES)
        )
        if blocked_support:
            raise AssertionError(f'support/test members in sdist: {blocked_support[:20]}')
        wrong_source_packages = sorted(
            name
            for name in rel_names
            if name.startswith('src/')
            and name != 'src/rdp'
            and not name.startswith('src/rdp/')
            and name != SDIST_METADATA_PREFIX
            and not name.startswith(SDIST_METADATA_PREFIX + '/')
        )
        if wrong_source_packages:
            raise AssertionError(f'non-rdp source package in sdist: {wrong_source_packages[:20]}')
        missing_native_sources = sorted(REQUIRED_NATIVE_SOURCES - rel_files)
        if missing_native_sources:
            raise AssertionError(f'native sources missing from sdist: {missing_native_sources}')
        expected_sdist_assets = {'assets/' + rel for rel in ci_paths}
        expected_sdist_assets.add('assets/' + INDEX_REL)
        missing = sorted(expected_sdist_assets - rel_names)
        if missing:
            raise AssertionError(f'CI-light sdist assets missing: {missing[:20]}')
        actual_asset_files = {n for n in rel_files if n.startswith('assets/')}
        unexpected = sorted(actual_asset_files - expected_sdist_assets)
        if unexpected:
            raise AssertionError(f'unexpected sdist assets (possible local full_v1 leak): {unexpected[:20]}')
        forbidden = [n for n in names if '/output/' in n or '/.git/' in n or '__pycache__' in n]
        if forbidden:
            raise AssertionError(f'generated/private members in sdist: {forbidden[:20]}')
    print(f'[a5-artifact-contract] PASS wheel={wheel.name} sdist={sdist.name} ci_assets={len(ci_paths)}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
