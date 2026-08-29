from __future__ import annotations
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tutorials" / "v1" / "tutorial_manifest_v1.json"
pytestmark = pytest.mark.tier_a


def _load_manifest() -> list[dict]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["schema"] == "rdp_tutorial_manifest.v1"
    return list(data["tutorials"])


def _scheduled_entries() -> list[dict]:
    return [
        item
        for item in _load_manifest()
        if item.get("cipher_family") == "scheduled_stream_lookup"
    ]


def test_scheduled_stream_lookup_short_smoke_pytest_gate_exists() -> None:
    smoke = (
        ROOT / "tests" / "tutorials" / "test_scheduled_stream_lookup_pipeline_smoke.py"
    )
    text = smoke.read_text(encoding="utf-8")
    expected_smokes = {
        "test_typed_scheduled_tutorial_fixture_round_trip",
        "test_typed_mask_schedule_fixture_round_trip",
    }
    for name in expected_smokes:
        assert f"def {name}" in text


def test_scheduled_stream_lookup_manifest_keeps_real_solve_coverage() -> None:
    entries = _scheduled_entries()
    by_path = {item["path"]: item for item in entries}
    expected = {
        "Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py": "v1_release",
        "Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py": "v1_extended",
        "Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py": "v1_partial_recovery",
    }
    for path, gate in expected.items():
        assert path in by_path
        assert by_path[path]["gate"] == gate
        assert by_path[path]["current_status"] == "active"
        assert (ROOT / "tutorials" / "v1" / path).is_file()


def test_only_exact_p13_sequence_real_solve_is_in_default_release_profile() -> None:
    release_gates = {"v1_smoke", "v1_release"}
    release_real_solves = {
        entry["path"]
        for entry in _scheduled_entries()
        if entry["path"].startswith("Tutorial_ScheduledStreamLookup_RealSolve_")
        and entry["gate"] in release_gates
    }
    assert release_real_solves == {
        "Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py"
    }
