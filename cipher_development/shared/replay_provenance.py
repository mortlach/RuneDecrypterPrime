from __future__ import annotations
import hashlib
import importlib.metadata
import importlib.util
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from rdp.scoring.language_model.paths import default_lm_root
_DATA_SUFFIXES = {'.bin', '.csv', '.db', '.json', '.npy', '.npz', '.sqlite', '.tsv', '.txt', '.zst'}
_ASSET_TOKENS = {'asset', 'assets', 'language_model', 'models', 'model'}

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _candidate_asset_files(repo_root: Path, scoring_contracts: Sequence[Mapping[str, Any]]):
    seen: set[Path] = set()
    candidates: list[tuple[str, Path]] = []
    for index, contract in enumerate(scoring_contracts):
        model_root = contract.get('model_root')
        if model_root:
            root = Path(str(model_root))
            root = root if root.is_absolute() else repo_root / root
            root = root.resolve()
        else:
            root = default_lm_root().resolve()
        if root.is_file():
            candidates.append((f'contract_{index}/{root.name}', root))
        elif root.is_dir():
            for path in sorted(root.rglob('*')):
                if path.is_file():
                    candidates.append((f'contract_{index}/{path.relative_to(root).as_posix()}', path))
    try:
        distribution = importlib.metadata.distribution('rune-decrypter-prime')
        for item in distribution.files or ():
            logical = Path(str(item))
            tokens = {part.lower() for part in logical.parts}
            if logical.suffix.lower() not in _DATA_SUFFIXES:
                continue
            if not tokens & _ASSET_TOKENS:
                continue
            path = Path(distribution.locate_file(item)).resolve()
            if path.is_file():
                candidates.append((f'distribution/{logical.as_posix()}', path))
    except importlib.metadata.PackageNotFoundError:
        pass
    spec = importlib.util.find_spec('rune_decrypter_prime')
    if spec is not None and spec.submodule_search_locations:
        package_root = Path(next(iter(spec.submodule_search_locations))).resolve()
        for relative_root in (Path('scoring/language_model'), Path('assets')):
            root = package_root / relative_root
            if root.is_dir():
                for path in sorted(root.rglob('*')):
                    if path.is_file() and path.suffix.lower() in _DATA_SUFFIXES:
                        candidates.append((f'package/{path.relative_to(package_root).as_posix()}', path))
    out: list[tuple[str, Path]] = []
    for logical, path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append((logical, resolved))
    return out

def build_evaluator_provenance(*, repo_root: Path, evaluator_source: Path, scoring_contracts: Sequence[Mapping[str, Any]], run_meta: Mapping[str, Any] | None=None, require_assets: bool=True) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    source = evaluator_source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    files = _candidate_asset_files(repo_root, scoring_contracts)
    assets = [{'logical_path': logical, 'sha256': _sha256(path), 'size_bytes': path.stat().st_size} for logical, path in files]
    if require_assets and (not assets):
        raise RuntimeError('could not fingerprint the active language-model assets')
    git = run_meta.get('git', {}) if isinstance(run_meta, Mapping) else {}
    git = git if isinstance(git, Mapping) else {}
    if not git:
        try:
            commit = subprocess.run(['git', '-C', str(repo_root), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True, timeout=5).stdout.strip()
            dirty = bool(subprocess.run(['git', '-C', str(repo_root), 'status', '--porcelain'], check=True, capture_output=True, text=True, timeout=5).stdout.strip())
            git = {'commit': commit, 'dirty': dirty}
        except (OSError, subprocess.SubprocessError):
            git = {}
    try:
        package_version = importlib.metadata.version('rune-decrypter-prime')
    except importlib.metadata.PackageNotFoundError:
        package_version = 'unavailable'
    return {'evaluator_source_sha256': _sha256(source), 'git_commit': git.get('commit'), 'git_dirty': git.get('dirty'), 'package_version': package_version, 'language_model_assets': assets, 'asset_manifest_complete': bool(assets)}

def validate_evaluator_provenance(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> None:
    if dict(expected) != dict(actual):
        raise ValueError('current evaluator or language-model provenance does not match the source run')
__all__ = ['build_evaluator_provenance', 'validate_evaluator_provenance']
