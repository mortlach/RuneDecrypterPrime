"""Scientific-boundary checks for the scheduled-stream examples."""

from __future__ import annotations

from pathlib import Path

import pytest

from tutorials.v1.support.scheduled_stream_lookup import make_real_solve_solver

pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "tutorials" / "v1" / "examples"


def test_real_solve_examples_keep_truth_out_of_solver_setup() -> None:
    expectations = {
        "scheduled_stream_lookup_p13_sequence.py": "exact",
        "scheduled_stream_lookup_p13_primes.py": "exact",
        "scheduled_stream_lookup_p13_p31_segmented.py": "partial recovery",
    }
    for filename, expected_result in expectations.items():
        source = (EXAMPLES / filename).read_text(encoding="utf-8").lower()
        assert "oracle_stop_score(" not in source
        assert "initial_keys=none" in source
        assert expected_result in source
        assert "match ratio:" in source


def test_real_solve_helper_preserves_the_original_automatic_round_budget() -> None:
    solver = make_real_solve_solver()
    assert solver.parameters["rounds"] == 0
