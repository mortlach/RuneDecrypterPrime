from __future__ import annotations

import inspect
from pathlib import Path

import tools.repo_tidy.sweep as sweep_mod
from tools.repo_tidy.sweep import _check_tree_policy, run_sweep


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_repo_tree_matches_tidy_policy() -> None:
    result = run_sweep(_repo_root())
    assert not result.tree_issues, "Unexpected tracked tree policy issues:\n" + "\n".join(
        f"- {i.path}: {i.detail}" for i in result.tree_issues
    )


def test_repo_has_no_absolute_machine_paths() -> None:
    result = run_sweep(_repo_root())
    assert not result.absolute_path_issues, "Absolute paths found in tracked files:\n" + "\n".join(
        f"- {i.path}:{i.line}: {i.detail}" for i in result.absolute_path_issues
    )


def test_repo_tidy_sweep_does_not_require_git_cli() -> None:
    source = inspect.getsource(sweep_mod)
    assert "git ls-files" not in source
    assert '["git"' not in source


def test_repo_tidy_flags_root_runtime_artifacts() -> None:
    issues = _check_tree_policy([Path("setup.log"), Path("setup_report.json")])
    assert issues
    assert any(issue.path == "setup.log" for issue in issues)
