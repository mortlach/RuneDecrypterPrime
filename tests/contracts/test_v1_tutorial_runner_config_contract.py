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


def test_runner_uses_file_constants_for_selection() -> None:
    runner = _runner_module()
    assert runner.RUN_SET is runner.TutorialRunSet.RELEASE
    assert runner.CONSOLE_OUTPUT is runner.ConsoleOutput.COMPACT
    assert runner.STOP_ON_FIRST_FAILURE is False
    assert runner.WRITE_OUTPUT_LOGS is True
    assert runner.OUTPUT_DIR is None
    assert runner.FAILURE_TAIL_LINES == 80

    source = RUNNER.read_text(encoding="utf-8")
    for forbidden in (
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
    assert route
    assert all(path.parent == runner.GETTING_STARTED_DIR for path in route)
    assert list(route) == sorted(route)

    examples = {
        path.name
        for path in runner._discover(runner.EXAMPLES_DIR, "*.py")
        if path.name != "__init__.py"
    }
    assert examples
    assert set(runner.RELEASE_EXAMPLE_NAMES) <= examples
    assert set(runner.FULL_ASSET_ONLY_NAMES) <= examples


def test_runner_selection_keeps_heavy_work_explicit() -> None:
    runner = _runner_module()

    runner.RUN_SET = runner.TutorialRunSet.GETTING_STARTED
    getting_started = runner._selected_tutorials()
    assert getting_started

    runner.RUN_SET = runner.TutorialRunSet.RELEASE
    release = runner._selected_tutorials()
    assert release[: len(getting_started)] == getting_started
    assert (
        tuple(path.name for path in release[len(getting_started) :])
        == runner.RELEASE_EXAMPLE_NAMES
    )

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


def test_module_launch_preserves_script_failure(monkeypatch, capsys, tmp_path) -> None:
    """A failed script must remain a failure through the shared launcher."""
    from subprocess import CompletedProcess

    runner = _runner_module()
    runner.WRITE_OUTPUT_LOGS = False
    runner.OUTPUT_DIR = tmp_path
    runner._prepare_output_dir()
    script = runner.EXAMPLES_DIR / "columnar_transposition.py"
    launches = []

    def fail(command, **kwargs):
        launches.append((command, kwargs))
        return CompletedProcess(command, 1, stdout="", stderr="semantic check failed")

    monkeypatch.setattr(runner.subprocess, "run", fail)
    passed, log = runner._run_one(script)
    assert not passed and log is None
    command, options = launches[0]
    assert command[-2:] == ["-m", "tutorials.v1.examples.columnar_transposition"]
    assert options["cwd"] == REPO_ROOT
    assert "semantic check failed" in capsys.readouterr().out
