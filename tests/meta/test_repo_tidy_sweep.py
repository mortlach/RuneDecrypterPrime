from __future__ import annotations
import inspect
from pathlib import Path
import pytest
import sweep as sweep_mod
from sweep import ALLOWED_TOP_DIRS, IGNORED_TOOL_DIRS, _check_tree_policy, _iter_repo_files, _is_text_candidate, run_sweep
pytestmark = pytest.mark.tier_a

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def test_repo_tree_matches_tidy_policy() -> None:
    result = run_sweep(_repo_root())
    assert not result.tree_issues, 'Unexpected tracked tree policy issues:\n' + '\n'.join((f'- {i.path}: {i.detail}' for i in result.tree_issues))

def test_repo_has_no_absolute_machine_paths() -> None:
    result = run_sweep(_repo_root())
    assert not result.absolute_path_issues, 'Absolute paths found in tracked files:\n' + '\n'.join((f'- {i.path}:{i.line}: {i.detail}' for i in result.absolute_path_issues))

def test_repo_tidy_sweep_does_not_require_git_cli() -> None:
    source = inspect.getsource(sweep_mod)
    assert 'git ls-files' not in source
    assert '["git"' not in source

def test_tidy_policy_names_the_current_v1_projects() -> None:
    assert ALLOWED_TOP_DIRS == {'.github', 'assets', 'cipher_development', 'docs', 'requirements', 'solving', 'src', 'tests', 'tools', 'tutorials'}

def test_repo_tidy_flags_root_runtime_artifacts() -> None:
    issues = _check_tree_policy([Path('setup.log'), Path('setup_report.json')])
    assert issues
    assert any((issue.path == 'setup.log' for issue in issues))

def test_absolute_path_sweep_distinguishes_local_and_fixture_surfaces(tmp_path: Path) -> None:
    windows_root = 'c:' + '\\Python'
    unix_private = '/' + 'home/name/private'
    tmp_private = '/' + 'tmp/private'
    windows_private = 'C:' + '\\Users\\name\\private.txt'
    (tmp_path / 'AGENTS.md').write_text(f'Python is likely at {windows_root}\n', encoding='utf-8')
    (tmp_path / 'planning').mkdir()
    (tmp_path / 'planning' / 'note.md').write_text(f'local {unix_private} note\n', encoding='utf-8')
    (tmp_path / 'tests' / 'scoring').mkdir(parents=True)
    (tmp_path / 'tests' / 'test_artifact_policy.py').write_text(f'RuntimeError("cannot write {unix_private}/secret.txt")\n', encoding='utf-8')
    (tmp_path / 'tests' / 'scoring' / 'test_retained_state_plaintext_rescore.py').write_text(f'Path("{tmp_private}")\n', encoding='utf-8')
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'leak.py').write_text(f'PATH = r"{windows_private}"\n', encoding='utf-8')
    result = run_sweep(tmp_path)
    assert [issue.path for issue in result.absolute_path_issues] == ['src/leak.py']

def test_absolute_path_sweep_checks_current_supporting_projects(tmp_path: Path) -> None:
    private = 'C:' + '\\Users\\name\\private.txt'
    paths = (Path('cipher_development/experiment.py'), Path('solving/attempt.py'), Path('tools/data/helper.py'), Path('tutorials/v1/example.py'), Path('docs/note.md'))
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'PATH = r"{private}"\n', encoding='utf-8')
    result = run_sweep(tmp_path)
    assert [issue.path for issue in result.absolute_path_issues] == sorted(path.as_posix() for path in paths)


def test_absolute_path_sweep_checks_tool_sources_without_name_allowlists(tmp_path: Path) -> None:
    private = '/' + 'home/name/private'
    paths = {Path('tools/new_helper.py')}
    paths.update(Path(f'tools/new_area/nested/helper{suffix}') for suffix in ('.py', '.md', '.json', '.ps1', '.bat', '.sh', '.js', '.mjs'))
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'private = "{private}"\n', encoding='utf-8')
    result = run_sweep(tmp_path, strict_top_level=True)
    assert not result.tree_issues
    assert [issue.path for issue in result.absolute_path_issues] == sorted(path.as_posix() for path in paths)


def test_tool_scan_excludes_nested_generated_directories(tmp_path: Path) -> None:
    private = '/' + 'home/name/private'
    for directory in (*IGNORED_TOOL_DIRS, 'fixture.egg-info'):
        for parent in ('tools', 'tools/new_area/nested'):
            target = tmp_path / parent / directory / 'generated.py'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f'private = "{private}"\n', encoding='utf-8')
    source = tmp_path / 'tools/new_area/source.py'
    source.write_text('SOURCE = True\n', encoding='utf-8')
    # Retained binary fixtures are not source-content scan inputs.
    fixture = tmp_path / 'tools/robustness/fixtures/example.npz'
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_bytes(b'\x00' + private.encode('utf-8'))
    assert _iter_repo_files(tmp_path) == [Path('tools/new_area/source.py')]
    assert not run_sweep(tmp_path, strict_top_level=True).has_issues


def test_tool_scan_covers_current_repository_source_files() -> None:
    root = _repo_root()
    expected = {
        path.relative_to(root)
        for path in (root / 'tools').rglob('*')
        if path.is_file() and _is_text_candidate(path)
        and not any(part in IGNORED_TOOL_DIRS or part.endswith('.egg-info') for part in path.relative_to(root / 'tools').parts[:-1])
    }
    scanned = {path for path in _iter_repo_files(root) if path.parts[0] == 'tools'}
    assert scanned == expected


def test_virtual_filesystem_paths_do_not_exempt_host_paths(tmp_path: Path) -> None:
    virtual_tmp = '/' + 'tmp/'
    output = f"RDP_OUTPUT_ROOT: '{virtual_tmp}rdp-smoke'"
    wheel = f"const virtualWheel = '{virtual_tmp}' + path.basename(wheelPath);"
    path = tmp_path / 'tools/pyodide/run_smoke.mjs'
    path.parent.mkdir(parents=True)
    path.write_text(f'{output}\n{wheel}\n', encoding='utf-8')
    assert not run_sweep(tmp_path).has_issues
    private = '/' + 'home/name/private'
    path.write_text(f'{output}; host = "{private}"\n{wheel}\n', encoding='utf-8')
    assert [(i.path, i.line) for i in run_sweep(tmp_path).absolute_path_issues] == [('tools/pyodide/run_smoke.mjs', 1)]
    path.write_text(f"const host = '{virtual_tmp}private';\n", encoding='utf-8')
    assert run_sweep(tmp_path).absolute_path_issues
    path.write_text('', encoding='utf-8')
    other = path.with_name('other.mjs')
    other.write_text(f'{output}\n{wheel}\n', encoding='utf-8')
    assert [i.path for i in run_sweep(tmp_path).absolute_path_issues] == ['tools/pyodide/other.mjs'] * 2
