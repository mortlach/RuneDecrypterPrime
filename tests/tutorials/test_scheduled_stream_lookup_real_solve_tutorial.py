from __future__ import annotations

import json
from pathlib import Path

import pytest

from rune_decrypter_prime.utils.tutorial_benchmark import TutorialAcceptanceKind


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tutorials" / "v1" / "tutorial_manifest_v1.json"

pytestmark = pytest.mark.tier_a


def test_real_solve_tutorials_are_manifested_for_release_runner_profiles() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = {
        item["path"]: item
        for item in data["tutorials"]
        if item.get("cipher_family") == "scheduled_stream_lookup"
    }

    expected_profiles = {
        "Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py": "v1_release",
        "Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py": "v1_extended",
        "Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py": "v1_showcase_near_solve",
    }
    for path, gate in expected_profiles.items():
        entry = entries[path]
        assert entry["gate"] == gate
        assert entry["required_asset_profile"] == "lm2_baseline"
        assert TutorialAcceptanceKind(entry["acceptance_kind"]) in {
            TutorialAcceptanceKind.EXACT,
            TutorialAcceptanceKind.SHOWCASE_NEAR_SOLVE,
        }
        assert (ROOT / "tutorials" / "v1" / path).is_file()

    release_entry = entries["Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py"]
    assert release_entry["acceptance_kind"] == TutorialAcceptanceKind.EXACT.value
    assert release_entry["min_match_ratio"] == 1.0
    assert release_entry["supplies_true_key_to_solver"] is False
