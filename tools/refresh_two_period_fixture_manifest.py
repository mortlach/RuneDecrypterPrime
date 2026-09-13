from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / 'cipher_development' / 'two_period_overlay' / 'fixture_manifest.json'

def local_import_closure(root: Path, entry_point: str) -> set[str]:
    pending = [entry_point]
    closure: set[str] = set()
    while pending:
        relpath = pending.pop()
        if relpath in closure:
            continue
        source = root / relpath
        if not source.is_file():
            raise FileNotFoundError(f'fixture dependency is missing: {relpath}')
        closure.add(relpath)
        tree = ast.parse(source.read_text(encoding='utf-8'), filename=relpath)
        modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend((alias.name for alias in node.names))
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
        for module in modules:
            if not module.startswith('cipher_development'):
                continue
            candidate = Path(*module.split('.')).with_suffix('.py').as_posix()
            if (root / candidate).is_file():
                pending.append(candidate)
    return closure

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def refresh_manifest(root: Path=ROOT, manifest_path: Path=MANIFEST_PATH) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    entry_point = manifest['entry_point']
    closure = local_import_closure(root, entry_point)
    rows_by_path = {row['path']: dict(row) for row in manifest['retained_sources']}
    rows: list[dict] = []
    for path in sorted(closure):
        row = rows_by_path.get(path, {'path': path})
        if path == entry_point:
            row['role'] = 'retained experiment adapter'
        elif path.endswith('/experiment_e.py'):
            row['role'] = 'Pack 09 experiment implementation'
        elif path.endswith('/pack09_support.py'):
            row['role'] = 'Pack 09 search, archive and replay support'
        elif path.endswith('/review_pack.py'):
            row['role'] = 'Pack 09 review-pack generation'
        else:
            row.setdefault('role', 'recursive local dependency')
        digest = sha256_file(root / path)
        row['sha256'] = digest
        rows.append(row)
    manifest['retained_sources'] = rows
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest

def main() -> int:
    manifest = refresh_manifest()
    print(f"Pack 09 fixture manifest refreshed: {len(manifest['retained_sources'])} files")
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
