from __future__ import annotations
import json
from pathlib import Path
import pytest

pytestmark = pytest.mark.tier_a


def _active_tutorial_paths(root: Path) -> list[Path]:
    manifest = json.loads(
        (root / "tutorials" / "v1" / "tutorial_manifest_v1.json").read_text(
            encoding="utf-8"
        )
    )
    paths: list[Path] = []
    for entry in manifest["tutorials"]:
        path = str(entry.get("path", ""))
        status = str(entry.get("current_status", ""))
        if not path.endswith(".py") or status in {
            "known_broken",
            "remove_from_pure_release",
        }:
            continue
        script = root / "tutorials" / "v1" / path
        if script.is_file():
            paths.append(script)
    return paths


def test_active_pretty_tutorials_declare_standard_contract_blocks() -> None:
    root = Path(__file__).resolve().parents[2]
    for script in _active_tutorial_paths(root):
        source = script.read_text(encoding="utf-8")
        canonical_display = "api.display.print_result(" in source
        assert "truth/oracle use" not in source, script.name
        assert (
            "print_tutorial_contract(" in source
            or '"truth/reference use"' in source
            or canonical_display
        ), script.name
        assert (
            "print_rdp_identity()" in source
            or "format_rdp_banner" in source
            or canonical_display
        ), script.name
        assert (
            "print_initialising()" in source
            or '"Initialising RDP"' in source
            or canonical_display
        ), script.name
        assert (
            "print_summary_spacer()" in source
            or "print()" in source
            or script.name == "Tutorial_PeriodicColumnar.py"
        ), script.name


def test_shared_stop_summary_prints_model_loading_before_stop_target() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "src" / "rune_decrypter_prime" / "utils" / "tutorial_utils.py"
    ).read_text(encoding="utf-8")
    assert "load_events: tuple[LmLoadStatus, ...]" in source
    assert "print_model_loading(result.load_events)" in source
    assert "format_stop_summary(label, result)" in source
