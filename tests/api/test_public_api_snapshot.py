from __future__ import annotations

import importlib
from pathlib import Path

from rdp import api
from tools.ci import a5_installed_wheel_smoke

SNAPSHOT = Path(__file__).resolve().parents[1] / "fixtures" / "v1_public_api.txt"


def _snapshot_paths() -> list[str]:
    return SNAPSHOT.read_text(encoding="utf-8").splitlines()


def test_public_api_snapshot_has_no_duplicates() -> None:
    paths = _snapshot_paths()
    assert len(paths) == len(set(paths)) == 145


def test_public_api_snapshot_imports() -> None:
    for path in _snapshot_paths():
        module_name, attr_name = path.rsplit(".", 1)
        assert hasattr(importlib.import_module(module_name), attr_name), path


def test_public_api_snapshot_is_the_exact_five_namespace_surface() -> None:
    expected = {
        f"{prefix}.{name}"
        for prefix, namespace in (
            ("rdp.api", api),
            ("rdp.api.advanced", api.advanced),
            ("rdp.api.display", api.display),
            ("rdp.api.liber_primus", api.liber_primus),
            ("rdp.api.experimental", api.experimental),
        )
        for name in namespace.__all__
    }
    assert len(api.__all__) == 34
    assert set(_snapshot_paths()) == expected


def test_installed_wheel_surface_check_consumes_the_same_snapshot() -> None:
    assert a5_installed_wheel_smoke.PUBLIC_API_SNAPSHOT == SNAPSHOT
    a5_installed_wheel_smoke._assert_v1_public_contract()
