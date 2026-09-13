"""Placement contracts for the scheduled-stream examples."""

from __future__ import annotations

from pathlib import Path

import pytest

from tutorials.v1 import run_tutorials as runner

pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "tutorials" / "v1" / "examples"
SCHEDULED = {
    "scheduled_stream_lookup_p13_sequence.py",
    "scheduled_stream_lookup_p13_primes.py",
    "scheduled_stream_lookup_p13_p31_segmented.py",
}


def test_scheduled_stream_lookup_short_smoke_pytest_gate_exists() -> None:
    smoke = (
        ROOT / "tests" / "tutorials" / "test_scheduled_stream_lookup_pipeline_smoke.py"
    )
    text = smoke.read_text(encoding="utf-8")
    for name in (
        "test_typed_scheduled_tutorial_fixture_round_trip",
        "test_typed_mask_schedule_fixture_round_trip",
    ):
        assert f"def {name}" in text


def test_all_real_solve_examples_remain_runnable_and_bundled() -> None:
    assert all((EXAMPLES / name).is_file() for name in SCHEDULED)
    runner.RUN_SET = runner.TutorialRunSet.BUNDLED_EXAMPLES
    bundled = {path.name for path in runner._selected_tutorials()}
    assert SCHEDULED <= bundled


def test_only_the_exact_p13_sequence_is_in_the_release_group() -> None:
    assert SCHEDULED & set(runner.RELEASE_EXAMPLE_NAMES) == {
        "scheduled_stream_lookup_p13_sequence.py"
    }
