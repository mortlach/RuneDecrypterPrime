from __future__ import annotations
import json
from pathlib import Path
import pytest
from tutorials.v1.support.tutorial_benchmark import TutorialAcceptanceKind
from tutorials.v1.support.scheduled_stream_lookup import make_real_solve_solver
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'tutorials' / 'v1' / 'tutorial_manifest_v1.json'
pytestmark = pytest.mark.tier_a

def test_real_solve_tutorials_are_manifested_for_release_runner_profiles() -> None:
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    entries = {item['path']: item for item in data['tutorials'] if item.get('cipher_family') == 'scheduled_stream_lookup'}
    expected_profiles = {'Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py': 'v1_release', 'Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py': 'v1_extended', 'Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py': 'v1_partial_recovery'}
    for path, gate in expected_profiles.items():
        entry = entries[path]
        assert entry['gate'] == gate
        assert entry['required_asset_profile'] == 'ci_light'
        assert TutorialAcceptanceKind(entry['acceptance_kind']) in {TutorialAcceptanceKind.EXACT, TutorialAcceptanceKind.PARTIAL_RECOVERY}
        assert (ROOT / 'tutorials' / 'v1' / path).is_file()
    release_entry = entries['Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py']
    assert release_entry['acceptance_kind'] == TutorialAcceptanceKind.EXACT.value
    assert release_entry['min_match_ratio'] == 1.0
    assert release_entry['supplies_true_key_to_solver'] is False


def test_real_solve_helper_preserves_the_original_automatic_round_budget() -> None:
    solver = make_real_solve_solver()
    assert solver.parameters['rounds'] == 0
