from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from rune_decrypter_prime.utils.tutorial_benchmark import TutorialAcceptanceKind


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_ALL = REPO_ROOT / "tutorials" / "v1" / "run_all.py"
PRETTY_RUNNER = REPO_ROOT / "tutorials" / "v1" / "run_pretty_print_release.py"
OUTPUT_REVIEW_RUNNER = REPO_ROOT / "tutorials" / "v1" / "run_pretty_print_output_review.py"
TUTORIAL_INDEX = REPO_ROOT / "docs" / "tutorials" / "index.md"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _run_all_module():
    return _load_module(RUN_ALL, "rdp_tutorial_run_all_config_contract")


def _pretty_runner_module():
    return _load_module(PRETTY_RUNNER, "rdp_pretty_tutorial_runner_config_contract")


def _output_review_runner_module():
    sys.path.insert(0, str(OUTPUT_REVIEW_RUNNER.parent))
    try:
        return _load_module(OUTPUT_REVIEW_RUNNER, "rdp_pretty_tutorial_output_review_contract")
    finally:
        try:
            sys.path.remove(str(OUTPUT_REVIEW_RUNNER.parent))
        except ValueError:
            pass


def test_tutorial_runner_uses_file_constants_not_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RDP_TUTORIAL_GATE_PROFILE", "full_v1")
    monkeypatch.setenv("RDP_TUTORIAL_ASSET_PROFILE", "lm3_extended")
    monkeypatch.setenv("RDP_TUTORIAL_ECHO_OUTPUT", "1")
    monkeypatch.setenv("GATE_PROFILE", "smoke")
    monkeypatch.setenv("ASSET_PROFILE", "lm3_extended")
    monkeypatch.setenv("RUN_KNOWN_BROKEN", "1")

    run_all = _run_all_module()

    assert run_all._gate_profile() == run_all.GATE_PROFILE == "release"
    assert run_all._asset_profile() == run_all.ASSET_PROFILE == "lm2_baseline"
    assert run_all._echo_output() is run_all.ECHO_OUTPUT is False
    assert run_all._run_known_broken() is run_all.RUN_KNOWN_BROKEN is False
    assert run_all._selected_gates() == run_all.GATE_PRESETS["release"]


def test_tutorial_runner_source_does_not_advertise_rdp_env_control() -> None:
    text = RUN_ALL.read_text(encoding="utf-8")

    forbidden = (
        "RDP_TUTORIAL_GATE_PROFILE",
        "RDP_TUTORIAL_ASSET_PROFILE",
        "RDP_TUTORIAL_ECHO_OUTPUT",
        "os.environ",
        "Legacy GATE_PROFILE",
    )
    for token in forbidden:
        assert token not in text


def test_pretty_runner_keeps_review_config_in_file_constants() -> None:
    runner = _pretty_runner_module()

    assert runner.TITLE == "V1 pretty-print tutorial review"
    assert runner.SHOW_OUTPUT is False
    assert runner.STOP_ON_FIRST_FAILURE is False
    assert runner.WRITE_LOGS is True
    assert runner.OUTPUT_DIR.as_posix() == "output/tutorial_pretty_print_logs"
    assert runner.CLEAN_OUTPUT_DIR is True
    assert runner.TAIL_LINES == 80
    assert len(runner.TUTORIALS) >= 20
    assert all(entry.path.endswith(".py") for entry in runner.TUTORIALS)
    assert all(isinstance(entry.acceptance, TutorialAcceptanceKind) for entry in runner.TUTORIALS)
    assert not any("PrettyPrint" in entry.path for entry in runner.TUTORIALS)


def test_pretty_runner_has_no_external_config_file_dependency() -> None:
    text = PRETTY_RUNNER.read_text(encoding="utf-8")

    assert "tomllib" not in text
    assert "pretty_print_release_config.toml" not in text
    assert not (PRETTY_RUNNER.parent / "pretty_print_release_config.toml").exists()


def test_pretty_output_review_runner_echoes_all_output_without_env_or_cli() -> None:
    runner = _output_review_runner_module()
    text = OUTPUT_REVIEW_RUNNER.read_text(encoding="utf-8")

    assert runner.TITLE == "V1 pretty-print output review"
    assert runner.SHOW_OUTPUT is True
    assert runner.STOP_ON_FIRST_FAILURE is False
    assert runner.WRITE_LOGS is True
    assert runner.OUTPUT_DIR.as_posix() == "output/tutorial_pretty_print_output_review_logs"
    assert runner.CLEAN_OUTPUT_DIR is True
    assert "os.environ" not in text
    assert "argparse" not in text
    assert "sys.argv" not in text


def test_pretty_runner_final_list_is_documented() -> None:
    runner = _pretty_runner_module()
    text = TUTORIAL_INDEX.read_text(encoding="utf-8")

    assert "python tutorials/v1/run_pretty_print_release.py" in text
    assert "python tutorials/v1/run_pretty_print_output_review.py" in text
    for entry in runner.TUTORIALS:
        assert entry.path in text
        assert entry.acceptance.value in text
        assert f"{entry.min_match_ratio:.3f}" in text
