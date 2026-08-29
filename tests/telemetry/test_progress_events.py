from __future__ import annotations
import pytest
from tests._helpers.runner import run_vigenere_roundtrip_baseline
from rune_decrypter_prime.core.types import Device

pytestmark = pytest.mark.tier_a


def test_progress_events_use_canonical_timing_keys(small_problem_cfg):
    _, _, meta = run_vigenere_roundtrip_baseline(
        device=Device.CPU,
        seed=small_problem_cfg["seed"],
        beam_width=small_problem_cfg["beam_width"],
        preview=small_problem_cfg["preview"],
        logging_over={"show_progress": False},
        use_test_key=False,
    )
    telemetry = meta.get("telemetry", {})
    progress_events = telemetry.get("solver_progress", [])
    assert progress_events, "solver_progress block missing progress events"
    for ev in progress_events:
        assert "decrypt_time" not in ev and "score_time" not in ev
        assert "decrypt_time_s" in ev and "score_time_s" in ev
        if "step" in ev:
            assert isinstance(ev["step"], int)
