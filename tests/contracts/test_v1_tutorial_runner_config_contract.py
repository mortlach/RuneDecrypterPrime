from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_ALL = REPO_ROOT / "tutorials" / "v1" / "run_all.py"


def _run_all_module():
    name = "rdp_tutorial_run_all_config_contract"
    spec = importlib.util.spec_from_file_location(name, RUN_ALL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_tutorial_runner_uses_ide_defaults_without_environment_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GATE_PROFILE", raising=False)
    monkeypatch.delenv("ASSET_PROFILE", raising=False)
    run_all = _run_all_module()

    assert run_all._gate_profile() == "release"
    assert run_all._asset_profile() == "lm2_baseline"
    assert run_all._selected_gates() == ("v1_smoke", "v1_release")


def test_tutorial_runner_allows_environment_gate_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATE_PROFILE", "full_v1")
    run_all = _run_all_module()

    assert run_all._gate_profile() == "full_v1"
    assert run_all._selected_gates() == (
        "v1_smoke",
        "v1_release",
        "v1_extended",
        "v1_showcase_near_solve",
    )


def test_tutorial_runner_allows_environment_asset_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSET_PROFILE", "lm3_extended")
    run_all = _run_all_module()

    assert run_all._asset_profile() == "lm3_extended"


def test_tutorial_runner_rejects_invalid_boolean_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUN_KNOWN_BROKEN", "maybe")
    run_all = _run_all_module()

    with pytest.raises(ValueError, match="Invalid boolean override"):
        run_all._run_known_broken()
