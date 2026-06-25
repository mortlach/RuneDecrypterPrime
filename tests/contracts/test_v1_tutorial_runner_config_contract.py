from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from rune_decrypter_prime.utils.tutorial_benchmark import TutorialAcceptanceKind
from rune_decrypter_prime.utils.tutorial_runner import ConsoleOutput, TutorialEntry, TutorialRunSet


REPO_ROOT = Path(__file__).resolve().parents[2]
TUTORIAL_DIR = REPO_ROOT / "tutorials" / "v1"
RUNNER = TUTORIAL_DIR / "run_tutorials.py"
TUTORIAL_INDEX = REPO_ROOT / "docs" / "tutorials" / "index.md"
ARCHIVED_RUNNERS = {
    "run_" + "all.py",
    "run_" + "all_pretty_tutorials.py",
    "run_" + "pretty_print_release.py",
    "run_" + "pretty_print_output_review.py",
}


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _runner_module():
    return _load_module(RUNNER, "rdp_v1_tutorial_single_runner_config_contract")


def test_v1_tutorial_folder_has_one_public_runner() -> None:
    runners = sorted(path.name for path in TUTORIAL_DIR.glob("run*.py"))

    assert runners == ["run_tutorials.py"]
    for archived in ARCHIVED_RUNNERS:
        assert not (TUTORIAL_DIR / archived).exists()


def test_single_runner_uses_file_constants_not_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RDP_TUTORIAL_GATE_PROFILE", "full_v1")
    monkeypatch.setenv("RDP_TUTORIAL_ASSET_PROFILE", "lm3_extended")
    monkeypatch.setenv("RDP_TUTORIAL_ECHO_OUTPUT", "1")
    monkeypatch.setenv("GATE_PROFILE", "smoke")
    monkeypatch.setenv("ASSET_PROFILE", "lm3_extended")
    monkeypatch.setenv("RUN_KNOWN_BROKEN", "1")

    runner = _runner_module()

    assert runner.RUN_SET is runner.TutorialRunSet.RELEASE
    assert runner.CONSOLE_OUTPUT is runner.ConsoleOutput.COMPACT
    assert runner.STOP_ON_FIRST_FAILURE is False
    assert runner.WRITE_OUTPUT_LOGS is True
    assert runner.CLEAN_OUTPUT_LOGS is True
    assert runner.OUTPUT_DIR.as_posix() == "output/tutorial_logs"
    assert runner.FAILURE_TAIL_LINES == 80


def test_single_runner_source_does_not_advertise_rdp_env_or_cli_control() -> None:
    text = RUNNER.read_text(encoding="utf-8")

    forbidden = (
        "RDP_TUTORIAL_GATE_PROFILE",
        "RDP_TUTORIAL_ASSET_PROFILE",
        "RDP_TUTORIAL_ECHO_OUTPUT",
        "os.environ",
        "argparse",
        "sys.argv",
        "pretty_print_release_config.toml",
    )
    for token in forbidden:
        assert token not in text


def test_single_runner_uses_shared_package_runner_model() -> None:
    text = RUNNER.read_text(encoding="utf-8")

    assert "from dataclasses import dataclass" not in text
    assert "class TutorialRunSet" not in text
    assert "class ConsoleOutput" not in text
    assert "class TutorialEntry" not in text
    assert "class TutorialResult" not in text
    assert "from rune_decrypter_prime.utils.tutorial_runner import" in text


def test_single_runner_prints_rdp_startup_before_compact_output_policy() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    startup = text.index("pretty.print_rdp_identity()")
    setup = text.index("Tutorial runner setup")

    assert "pretty.print_initialising()" in text
    assert "runner" in text
    assert "run set" in text
    assert "console output" in text
    assert "output logs" in text
    assert startup < setup


def test_single_runner_has_clear_enum_run_sets_and_console_modes() -> None:
    runner = _runner_module()

    assert [item.value for item in runner.TutorialRunSet] == [
        "fast",
        "release",
        "extended",
        "partial_recovery",
        "optional_lm3",
        "all_working",
    ]
    assert [item.value for item in runner.ConsoleOutput] == ["compact", "full"]
    assert len(runner.TUTORIALS) >= 20
    assert runner.TutorialRunSet is TutorialRunSet
    assert runner.ConsoleOutput is ConsoleOutput
    assert all(isinstance(entry, TutorialEntry) for entry in runner.TUTORIALS)
    assert all(entry.path.startswith("Tutorial_") for entry in runner.TUTORIALS)
    assert all(entry.path.endswith(".py") for entry in runner.TUTORIALS)
    assert all(isinstance(entry.acceptance, TutorialAcceptanceKind) for entry in runner.TUTORIALS)
    assert all(entry.run_sets for entry in runner.TUTORIALS)
    assert not any("PrettyPrint" in entry.path for entry in runner.TUTORIALS)


def test_single_runner_selects_expected_review_sets() -> None:
    runner = _runner_module()

    runner.RUN_SET = runner.TutorialRunSet.FAST
    assert len(runner._selected_tutorials()) == 5

    runner.RUN_SET = runner.TutorialRunSet.RELEASE
    release = runner._selected_tutorials()
    assert len(release) >= 10
    assert all(runner.TutorialRunSet.RELEASE in entry.run_sets for entry in release)

    runner.RUN_SET = runner.TutorialRunSet.PARTIAL_RECOVERY
    partial = runner._selected_tutorials()
    assert [entry.acceptance for entry in partial] == [TutorialAcceptanceKind.PARTIAL_RECOVERY]

    runner.RUN_SET = runner.TutorialRunSet.ALL_WORKING
    assert runner._selected_tutorials() == runner.TUTORIALS


def test_single_runner_final_list_is_documented() -> None:
    runner = _runner_module()
    text = TUTORIAL_INDEX.read_text(encoding="utf-8")

    assert "python tutorials/v1/run_tutorials.py" in text
    assert "run_" + "pretty_print_release.py" not in text
    assert "run_" + "pretty_print_output_review.py" not in text
    for entry in runner.TUTORIALS:
        assert entry.path in text
        assert entry.acceptance.value in text
        assert f"{entry.min_match_ratio:.3f}" in text
