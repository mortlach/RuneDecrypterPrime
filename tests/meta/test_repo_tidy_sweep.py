from __future__ import annotations
import inspect
from pathlib import Path
import pytest
import sweep as sweep_mod
from sweep import ALLOWED_TOOLS_ROOT_FILES, ALLOWED_TOOLS_SUBDIRS, ALLOWED_TOP_DIRS, _check_tree_policy, run_sweep
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
    assert ALLOWED_TOP_DIRS == {'.github', 'assets', 'cipher_development', 'docs', 'requirements', 'solving', 'src', 'tests', 'tools', 'tutorials', 'v1_docs'}
    assert ALLOWED_TOOLS_SUBDIRS == {'assets', 'ci', 'data', 'get_src_zip', 'robustness'}
    assert ALLOWED_TOOLS_ROOT_FILES == {'README.md', '__init__.py', 'refresh_two_period_fixture_manifest.py', 'release_review_pack.py'}

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
    paths = (Path('cipher_development/experiment.py'), Path('solving/attempt.py'), Path('tools/data/helper.py'), Path('tutorials/v1/example.py'), Path('v1_docs/note.md'))
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'PATH = r"{private}"\n', encoding='utf-8')
    result = run_sweep(tmp_path)
    assert [issue.path for issue in result.absolute_path_issues] == [path.as_posix() for path in paths]
