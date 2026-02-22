from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _run_community_tests_from_repo_root() -> None:
    """
    Community tests use repo-relative fixture paths (tools/..., docs/..., assets_packed/...).
    Force cwd to repo root so IDE test runners that launch from tests/ stay consistent.
    """
    prev_cwd = Path.cwd()
    repo_root = Path(__file__).resolve().parents[2]
    os.chdir(repo_root)
    try:
        yield
    finally:
        os.chdir(prev_cwd)
