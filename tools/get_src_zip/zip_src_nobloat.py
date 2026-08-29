from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / 'src'
OUTPUT_ROOT = REPO_ROOT / 'output' / 'tools' / 'get_src_zip' / 'src_only'
USE_TIMESTAMPED_NAME = True
ZIP_STEM = 'src_nobloat'
STATIC_ZIP_NAME = 'src_nobloat.zip'
WRITE_SUMMARY_JSON = True
_FIXED_ZIP_DATETIME = (1980, 1, 1, 0, 0, 0)
_FIXED_FILE_MODE = 33188
EXCLUDED_DIR_NAMES = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'data', 'build_tmp_fastlm', 'build_lib_fastlm', 'build_tmp_hamming', 'build_lib_hamming'}
EXCLUDED_FILE_SUFFIXES = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib', '.obj', '.o'}
EXCLUDED_FILE_NAMES = {'.DS_Store', 'Thumbs.db'}
EXCLUDED_FILE_GLOBS = {'*.bin', '*.bin.zst', '*.npz', '*.npy'}

def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

def _zip_name() -> str:
    return f'{ZIP_STEM}__{_utc_stamp()}.zip' if USE_TIMESTAMPED_NAME else STATIC_ZIP_NAME

def _has_excluded_dir(rel_from_src: Path) -> bool:
    return any((part in EXCLUDED_DIR_NAMES for part in rel_from_src.parts))

def _is_excluded_file(rel_from_src: Path) -> bool:
    name = rel_from_src.name
    if name in EXCLUDED_FILE_NAMES:
        return True
    if rel_from_src.suffix.lower() in EXCLUDED_FILE_SUFFIXES:
        return True
    return any((rel_from_src.match(glob) for glob in EXCLUDED_FILE_GLOBS))

def _to_repo_rel(path: Path, repo_root: Path) -> str:
    p = path.resolve()
    r = repo_root.resolve()
    try:
        return str(p.relative_to(r)).replace('\\', '/')
    except ValueError:
        return '<external>'

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def collect_src_files(src_root: Path) -> tuple[list[Path], list[str]]:
    if not src_root.exists():
        raise FileNotFoundError(f'src root not found: {src_root}')
    included: list[Path] = []
    excluded: list[str] = []
    for path in sorted(src_root.rglob('*'), key=lambda p: p.as_posix()):
        if path.is_dir():
            continue
        rel = path.relative_to(src_root)
        rel_prefixed = str(Path('src') / rel).replace('\\', '/')
        if _has_excluded_dir(rel) or _is_excluded_file(rel):
            excluded.append(rel_prefixed)
        else:
            included.append(path)
    return (included, excluded)

def _member_info(arcname: str) -> ZipInfo:
    info = ZipInfo(arcname, date_time=_FIXED_ZIP_DATETIME)
    info.compress_type = ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (_FIXED_FILE_MODE & 65535) << 16
    return info

def make_zip_src_nobloat(*, repo_root: Path=REPO_ROOT, src_root: Path=SRC_ROOT, output_root: Path=OUTPUT_ROOT, zip_path_override: Path | None=None) -> dict[str, object]:
    output_root.mkdir(parents=True, exist_ok=True)
    included, excluded = collect_src_files(src_root)
    zip_path = zip_path_override if zip_path_override is not None else output_root / _zip_name()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, mode='w', compression=ZIP_DEFLATED, compresslevel=9) as zf:
        for file_path in included:
            arcname = str(file_path.relative_to(repo_root)).replace('\\', '/')
            zf.writestr(_member_info(arcname), file_path.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)
    summary: dict[str, object] = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'repo_root': '.', 'src_root': _to_repo_rel(src_root, repo_root), 'zip_path': _to_repo_rel(zip_path, repo_root), 'included_files_count': len(included), 'excluded_files_count': len(excluded), 'zip_size_bytes': zip_path.stat().st_size, 'zip_sha256': _sha256(zip_path)}
    if WRITE_SUMMARY_JSON:
        summary_path = zip_path.with_suffix('.summary.json')
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        summary['summary_path'] = _to_repo_rel(summary_path, repo_root)
    return summary

def main() -> int:
    summary = make_zip_src_nobloat()
    print('[zip_src_nobloat] complete')
    print(f"[zip_src_nobloat] zip={summary['zip_path']}")
    print(f"[zip_src_nobloat] files included={summary['included_files_count']} excluded={summary['excluded_files_count']}")
    print(f"[zip_src_nobloat] size_bytes={summary['zip_size_bytes']}")
    print(f"[zip_src_nobloat] sha256={summary['zip_sha256']}")
    if 'summary_path' in summary:
        print(f"[zip_src_nobloat] summary={summary['summary_path']}")
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
