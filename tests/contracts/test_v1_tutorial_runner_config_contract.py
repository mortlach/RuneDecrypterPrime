"""Contracts for the single, explicit V1 runnable-material selector."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a
REPO_ROOT = Path(__file__).resolve().parents[2]
TUTORIAL_DIR = REPO_ROOT / "tutorials" / "v1"
RUNNER = TUTORIAL_DIR / "run_tutorials.py"


def _runner_module():
    name = "rdp_v1_tutorial_runner_config_contract"
    spec = importlib.util.spec_from_file_location(name, RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_v1_tutorial_folder_has_one_public_runner() -> None:
    assert sorted(path.name for path in TUTORIAL_DIR.glob("run*.py")) == [
        "run_tutorials.py"
    ]


def test_runner_uses_file_constants_not_environment_or_cli() -> None:
    runner = _runner_module()
    assert runner.RUN_SET is runner.TutorialRunSet.RELEASE
    assert runner.CONSOLE_OUTPUT is runner.ConsoleOutput.COMPACT
    assert runner.STOP_ON_FIRST_FAILURE is False
    assert runner.WRITE_OUTPUT_LOGS is True
    assert runner.CLEAN_OUTPUT_LOGS is True
    assert runner.OUTPUT_DIR.as_posix() == "output/tutorial_logs"
    assert runner.FAILURE_TAIL_LINES == 80

    source = RUNNER.read_text(encoding="utf-8")
    for forbidden in (
        "os.environ",
        "argparse",
        "sys.argv",
        "tutorial_manifest_v1",
        "support.tutorial_runner",
    ):
        assert forbidden not in source


def test_runner_exposes_only_the_five_honest_groups() -> None:
    runner = _runner_module()
    assert [item.value for item in runner.TutorialRunSet] == [
        "getting_started",
        "release",
        "bundled_examples",
        "full_asset_examples",
        "qualification",
    ]
    assert [item.value for item in runner.ConsoleOutput] == ["compact", "full"]


def test_runner_discovers_the_route_and_preserves_the_baseline_examples() -> None:
    runner = _runner_module()
    route = runner._discover(runner.GETTING_STARTED_DIR, "[0-9][0-9]_*.py")
    assert [path.name for path in route] == [
        "01_known_key.py",
        "02_first_search.py",
        "03_repeating_key_search.py",
        "04_reproducible_runs.py",
        "05_known_interruptors.py",
        "06_partial_recovery.py",
        "07_liber_primus_source.py",
    ]

    examples = {
        path.name
        for path in runner._discover(runner.EXAMPLES_DIR, "*.py")
        if path.name != "__init__.py"
    }
    assert len(examples) >= 26
    assert set(runner.RELEASE_EXAMPLE_NAMES) <= examples
    assert set(runner.FULL_ASSET_ONLY_NAMES) <= examples


def test_runner_selection_keeps_heavy_work_explicit() -> None:
    runner = _runner_module()

    runner.RUN_SET = runner.TutorialRunSet.GETTING_STARTED
    getting_started = runner._selected_tutorials()
    assert len(getting_started) == 7

    runner.RUN_SET = runner.TutorialRunSet.RELEASE
    release = runner._selected_tutorials()
    assert release[:7] == getting_started
    assert tuple(path.name for path in release[7:]) == runner.RELEASE_EXAMPLE_NAMES

    runner.RUN_SET = runner.TutorialRunSet.BUNDLED_EXAMPLES
    bundled = runner._selected_tutorials()
    assert bundled
    assert not {path.name for path in bundled} & runner.FULL_ASSET_ONLY_NAMES

    runner.RUN_SET = runner.TutorialRunSet.FULL_ASSET_EXAMPLES
    assert tuple(path.name for path in runner._selected_tutorials()) == (
        runner.FULL_ASSET_EXAMPLE_NAMES
    )

    runner.RUN_SET = runner.TutorialRunSet.QUALIFICATION
    assert tuple(path.name for path in runner._selected_tutorials()) == (
        runner.QUALIFICATION_NAMES
    )


def test_qualification_warning_is_plain_and_unconditional() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "qualification programs may take several hours each" in source
    assert "requires the full V1 asset profile" in source
