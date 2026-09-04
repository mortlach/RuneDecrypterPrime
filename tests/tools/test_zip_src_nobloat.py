from __future__ import annotations
from pathlib import Path
from zipfile import ZipFile
import pytest
from tools.get_src_zip import zip_src_nobloat as zsn
pytestmark = pytest.mark.tier_a

def _write(path: Path, content: str='x\n') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

def test_collect_src_files_excludes_data_pycache_and_compiled(tmp_path: Path):
    src_root = tmp_path / 'src'
    _write(src_root / 'pkg' / 'core.py')
    _write(src_root / 'pkg' / 'notes.txt')
    _write(src_root / 'pkg' / 'data' / 'table.json', '{}\n')
    _write(src_root / 'pkg' / '__pycache__' / 'core.cpython-311.pyc')
    _write(src_root / 'pkg' / '_fastlm.pyd')
    included, excluded = zsn.collect_src_files(src_root)
    included_rel = {str(p.relative_to(src_root)).replace('\\', '/') for p in included}
    excluded_rel = set(excluded)
    assert 'pkg/core.py' in included_rel
    assert 'pkg/notes.txt' in included_rel
    assert 'src/pkg/data/table.json' in excluded_rel
    assert 'src/pkg/__pycache__/core.cpython-311.pyc' in excluded_rel
    assert 'src/pkg/_fastlm.pyd' in excluded_rel

def test_make_zip_src_nobloat_preserves_src_structure(tmp_path: Path):
    repo_root = tmp_path
    src_root = repo_root / 'src'
    output_root = repo_root / 'output'
    zip_path = output_root / 'src_nobloat_test.zip'
    _write(src_root / 'rdp' / '__init__.py', '')
    _write(src_root / 'rdp' / 'core' / 'types.py', '# ok\n')
    _write(src_root / 'rdp' / 'data' / 'huge.bin', 'NOPE')
    summary = zsn.make_zip_src_nobloat(repo_root=repo_root, src_root=src_root, output_root=output_root, zip_path_override=zip_path)
    assert zip_path.exists()
    assert int(summary['included_files_count']) == 2
    with ZipFile(zip_path, 'r') as zf:
        names = set(zf.namelist())
    assert 'src/rdp/__init__.py' in names
    assert 'src/rdp/core/types.py' in names
    assert 'src/rdp/data/huge.bin' not in names
