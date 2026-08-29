from __future__ import annotations
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / 'output' / 'tools' / 'release_review_pack'
ZIP_STEM = 'rdp_v1_review_pack'
MAX_FILE_BYTES = 256 * 1024
ROOT_FILE_NAMES: tuple[str, ...] = ('AGENTS.md', '.gitattributes', '.gitignore', 'CONTRIBUTING.md', 'README.md', 'CHANGELOG.md', 'LICENSE', 'LICENSE.txt', 'LICENSE_MIT.txt', 'MANIFEST.in', 'pyproject.toml', 'pytest.ini', 'requirements.txt', 'install.py', 'install.bat', 'install.ps1', 'install.sh', 'assets_manifest_v1.json', 'setup.py')
REVIEW_DIRS: tuple[str, ...] = ('src', 'tests', 'docs', 'tutorials', '.github/workflows')
REVIEW_TOOL_FILES: tuple[str, ...] = ('tools/release_review_pack.py',)
EXCLUDED_DIR_NAMES = frozenset({'.git', '.idea', '.mypy_cache', '.pytest_cache', '.ruff_cache', '.venv', '.vscode', '__pycache__', 'assets', 'build', 'dist', 'node_modules', 'output', 'planning', 'venv'})
EXCLUDED_SUFFIXES = frozenset({'.7z', '.bin', '.bz2', '.dll', '.dylib', '.exe', '.gz', '.jpg', '.jpeg', '.npy', '.npz', '.o', '.obj', '.pdb', '.png', '.pyc', '.pyd', '.pyo', '.so', '.tar', '.webp', '.whl', '.zip', '.zst'})
ALLOWED_SUFFIXES = frozenset({'', '.cfg', '.csv', '.gitignore', '.in', '.ini', '.json', '.lock', '.md', '.py', '.pyi', '.rst', '.toml', '.bat', '.ps1', '.sh', '.tsv', '.txt', '.yaml', '.yml'})

@dataclass(frozen=True)
class ReviewPackSummary:
    zip_path: str
    summary_path: str | None
    timestamp_utc: str
    max_file_bytes: int
    included_files_count: int
    excluded_entries_count: int
    included_bytes: int
    git_branch: str | None
    git_commit_sha: str | None
    git_working_tree_dirty: bool | None

    def to_json_dict(self) -> dict[str, object]:
        return {'schema': 'rdp_v1_review_pack_summary.v1', 'zip_path': self.zip_path, 'summary_path': self.summary_path, 'timestamp_utc': self.timestamp_utc, 'max_file_bytes': self.max_file_bytes, 'included_files_count': self.included_files_count, 'excluded_entries_count': self.excluded_entries_count, 'included_bytes': self.included_bytes, 'git_branch': self.git_branch, 'git_commit_sha': self.git_commit_sha, 'git_working_tree_dirty': self.git_working_tree_dirty}

def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

def _repo_rel(path: Path, repo_root: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve())).replace('\\', '/')

def _is_under_excluded_dir(rel: Path) -> bool:
    return any((part in EXCLUDED_DIR_NAMES for part in rel.parts[:-1]))

def _suffix(path: Path) -> str:
    name = path.name
    if name == '.gitignore':
        return '.gitignore'
    return path.suffix.lower()

def _git_output(repo_root: Path, *args: str, empty_is_none: bool=True) -> str | None:
    try:
        proc = subprocess.run(['git', '-C', str(repo_root), *args], text=True, encoding='utf-8', errors='replace', capture_output=True, check=False)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    if value:
        return value
    return None if empty_is_none else ''

def _git_metadata(repo_root: Path) -> dict[str, object]:
    commit_sha = _git_output(repo_root, 'rev-parse', 'HEAD')
    branch = _git_output(repo_root, 'rev-parse', '--abbrev-ref', 'HEAD')
    status = _git_output(repo_root, 'status', '--porcelain', empty_is_none=False)
    if branch == 'HEAD':
        branch = None
    return {'git_branch': branch, 'git_commit_sha': commit_sha, 'git_working_tree_dirty': None if status is None else bool(status)}

def _should_include_file(path: Path, repo_root: Path, *, max_file_bytes: int) -> tuple[bool, str | None]:
    rel = Path(_repo_rel(path, repo_root))
    if _is_under_excluded_dir(rel):
        return (False, 'excluded_dir')
    suffix = _suffix(path)
    if suffix in EXCLUDED_SUFFIXES:
        return (False, 'excluded_suffix')
    if suffix not in ALLOWED_SUFFIXES:
        return (False, 'unsupported_suffix')
    size = path.stat().st_size
    if size > max_file_bytes:
        return (False, f'too_large>{max_file_bytes}')
    return (True, None)

def _iter_files_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        return [root]
    return [p for p in root.rglob('*') if p.is_file()]

def _candidate_files(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for name in ROOT_FILE_NAMES:
        p = repo_root / name
        if p.exists() and p.is_file():
            candidates.append(p)
    for name in REVIEW_DIRS:
        candidates.extend(_iter_files_under(repo_root / name))
    for name in REVIEW_TOOL_FILES:
        p = repo_root / name
        if p.exists() and p.is_file():
            candidates.append(p)
    unique = {_repo_rel(p, repo_root): p for p in candidates}
    return [unique[key] for key in sorted(unique)]

def _review_pack_readme() -> str:
    return '# RDP V1 review pack\n\nThis ZIP is generated by `tools/release_review_pack.py`.\n\nIt is intended for code/contract review, not for release installation. It includes small\nsource, tests, docs, workflows, tutorials, and root config files needed to understand\nthe V1 repo state. It deliberately excludes generated output, caches, benchmark data,\nlarge assets, binary/native files, archives, and other bulky evidence packs.\n\nSee `REVIEW_PACK_MANIFEST.json` for included and excluded paths.\n'

def make_release_review_pack(*, repo_root: Path=REPO_ROOT, output_root: Path=OUTPUT_ROOT, zip_path_override: Path | None=None, max_file_bytes: int=MAX_FILE_BYTES, write_summary_json: bool=True, git_metadata: dict[str, object] | None=None) -> dict[str, object]:
    repo_root = repo_root.resolve()
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = _utc_stamp()
    zip_path = zip_path_override or output_root / f'{ZIP_STEM}__{timestamp}.zip'
    git_info = _git_metadata(repo_root) if git_metadata is None else dict(git_metadata)
    included: list[tuple[Path, str, int]] = []
    excluded: list[dict[str, object]] = []
    for path in _candidate_files(repo_root):
        rel = _repo_rel(path, repo_root)
        include, reason = _should_include_file(path, repo_root, max_file_bytes=max_file_bytes)
        if include:
            included.append((path, rel, path.stat().st_size))
        else:
            excluded.append({'path': rel, 'reason': reason})
    manifest = {'schema': 'rdp_v1_review_pack_manifest.v1', 'timestamp_utc': timestamp, 'max_file_bytes': max_file_bytes, 'root_file_selection': 'strict_root_allowlist_filtered_by_review_pack_rules', 'included_roots': list(REVIEW_DIRS), 'preferred_root_files': list(ROOT_FILE_NAMES), 'included_tool_files': list(REVIEW_TOOL_FILES), 'excluded_dir_names': sorted(EXCLUDED_DIR_NAMES), 'excluded_suffixes': sorted(EXCLUDED_SUFFIXES), 'git_branch': git_info.get('git_branch'), 'git_commit_sha': git_info.get('git_commit_sha'), 'git_working_tree_dirty': git_info.get('git_working_tree_dirty'), 'included_files': [{'path': rel, 'size_bytes': size} for _, rel, size in included], 'excluded_entries': excluded}
    with ZipFile(zip_path, 'w', compression=ZIP_DEFLATED) as zf:
        zf.writestr('REVIEW_PACK_README.md', _review_pack_readme())
        zf.writestr('REVIEW_PACK_MANIFEST.json', json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        for path, rel, _size in included:
            zf.write(path, rel)
    summary_path: Path | None = None
    if write_summary_json:
        summary_path = zip_path.with_suffix('.summary.json')
    summary = ReviewPackSummary(zip_path=str(zip_path), summary_path=None if summary_path is None else str(summary_path), timestamp_utc=timestamp, max_file_bytes=max_file_bytes, included_files_count=len(included), excluded_entries_count=len(excluded), included_bytes=sum((size for _, _, size in included)), git_branch=None if git_info.get('git_branch') is None else str(git_info.get('git_branch')), git_commit_sha=None if git_info.get('git_commit_sha') is None else str(git_info.get('git_commit_sha')), git_working_tree_dirty=None if git_info.get('git_working_tree_dirty') is None else bool(git_info.get('git_working_tree_dirty'))).to_json_dict()
    summary['manifest_path_in_zip'] = 'REVIEW_PACK_MANIFEST.json'
    if summary_path is not None:
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return summary

def main() -> int:
    summary = make_release_review_pack()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
