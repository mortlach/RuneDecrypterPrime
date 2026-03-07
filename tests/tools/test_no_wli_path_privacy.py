from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.path_hash_utils import to_repo_rel_path


pytestmark = pytest.mark.tier_a


def test_to_repo_rel_path_under_repo_returns_relative() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = repo_root / "output" / "tools"
    rel = to_repo_rel_path(run_dir, root=repo_root)
    assert rel.startswith("output/")
    assert not Path(rel).is_absolute()


def test_to_repo_rel_path_external_absolute_redacted() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    external = Path.home()
    rel = to_repo_rel_path(external, root=repo_root)
    if external.resolve() == repo_root.resolve():
        pytest.skip("home path equals repo root on this environment")
    assert rel == "<external>"
