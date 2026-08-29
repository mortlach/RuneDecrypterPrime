from __future__ import annotations
import contextlib
import hashlib
import importlib
import importlib.util
import json
import os
import tempfile
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = (PROJECT_ROOT / 'src').resolve()
REQUIRED_MODULES = ('rune_decrypter_prime', 'rdp', 'rune_decrypter_prime.scoring.language_model._fastlm', 'rune_decrypter_prime.scoring.hamming._hamming', 'rune_decrypter_prime.scoring.span_hamming._span_hamming_fast')
BLOCKED_MODULES = ('rune_decrypter_prime.ciphers.dev', 'rune_decrypter_prime.keyops.dev', 'rune_decrypter_prime.data.liber_primus.old')

def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    with tempfile.TemporaryDirectory(prefix='rdp_a5_wheel_smoke_') as td, contextlib.chdir(td):
        loaded = []
        for name in REQUIRED_MODULES:
            mod = importlib.import_module(name)
            file = getattr(mod, '__file__', None)
            if file:
                p = Path(file).resolve()
                if _under(p, SOURCE_ROOT):
                    raise AssertionError(f'source-tree contamination for {name}: {p}')
                loaded.append((name, str(p)))
        for name in BLOCKED_MODULES:
            if importlib.util.find_spec(name) is not None:
                raise AssertionError(f'development/old namespace present in wheel: {name}')
        from rune_decrypter_prime.data import asset_paths
        asset_root = asset_paths.find_assets_root()
        if _under(asset_root, PROJECT_ROOT / 'assets'):
            raise AssertionError(f'installed wheel fell back to checkout assets: {asset_root}')
        package_data = Path(asset_paths.__file__).resolve().parent
        manifest_path = package_data / 'assets_manifest_ci_light_v1.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        rows = manifest.get('installed_assets', [])
        if not rows:
            raise AssertionError('packaged CI-light manifest has no installed_assets')
        for row in rows:
            path = asset_root / row['final_relpath']
            if not path.is_file():
                raise AssertionError(f"packaged CI-light asset missing: {row['final_relpath']}")
            if path.stat().st_size != int(row['size_bytes']):
                raise AssertionError(f"packaged CI-light size mismatch: {row['final_relpath']}")
            if _sha256(path) != row['sha256']:
                raise AssertionError(f"packaged CI-light hash mismatch: {row['final_relpath']}")
        lm_index = asset_root / 'language_model' / 'lmp' / 'index.json'
        if not lm_index.is_file():
            raise AssertionError('packaged language-model index.json missing')
        from rune_decrypter_prime.scoring.language_model.paths import default_lm_root
        if default_lm_root() != lm_index.parent.resolve():
            raise AssertionError('default LM root does not resolve to packaged CI-light data')
        print(f'[a5-wheel-smoke] PASS assets={len(rows)}')
        for name, path in loaded:
            print(f'[a5-wheel-smoke] {name} -> {path}')
        print(f'[a5-wheel-smoke] package_asset_root -> {asset_root}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
