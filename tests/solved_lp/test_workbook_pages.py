from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKBOOK_ROOT = REPO_ROOT / "solving" / "solved_lp"
WORKBOOK_FILES = (
    "01_A_Warning.py",
    "02_Welcome_Pilgrim.py",
    "03_Some_Wisdom.py",
    "04_Koan_A_Man.py",
    "05_Loss_Of_Divinity.py",
    "06_Koan_During_Lesson.py",
    "07_Instruction.py",
    "08_An_End.py",
    "09_Parable.py",
)
RUN_ALL = WORKBOOK_ROOT / "run_all.py"


def test_all_workbook_files_exist() -> None:
    for filename in WORKBOOK_FILES:
        assert (WORKBOOK_ROOT / filename).is_file()
    assert RUN_ALL.is_file()


def test_solved_lp_folder_is_flat() -> None:
    directories = [path.name for path in WORKBOOK_ROOT.iterdir() if path.is_dir() and path.name != "__pycache__"]
    assert directories == []


def test_no_local_workbook_common_helper_exists() -> None:
    assert not (WORKBOOK_ROOT / "_common.py").exists()


def test_workbook_files_have_source_recipe_and_main() -> None:
    for filename in WORKBOOK_FILES:
        path = WORKBOOK_ROOT / filename
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

        assert "SOURCE_LABEL" in text
        assert "RECIPE_LABEL" in text
        assert "main" in names
        assert "workbook._common" not in text
        assert "from solving.solved_lp.workbook" not in text


@pytest.mark.tier_a
def test_run_all_workbook_solves_require_solved_status() -> None:
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", str(RUN_ALL)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=360,
        check=False,
    )
    output = completed.stdout + completed.stderr

    assert completed.returncode == 0, output[-4000:]
    assert "LP_WORKBOOK_RUN_ALL_BEGIN" in output
    assert "LP_WORKBOOK_RUN_ALL_END" in output
    assert "solves_passed: 9" in output
