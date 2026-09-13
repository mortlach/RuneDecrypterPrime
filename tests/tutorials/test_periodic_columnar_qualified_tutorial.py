from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tutorials.v1.data.periodic_columnar_p7_warm_start import (
    QUALIFICATION_CANDIDATE_ID,
    QUALIFICATION_RECIPE_ID,
    QUALIFIED_INITIAL_KEY,
)
from tutorials.v1.examples import (
    periodic_columnar_p7_column_then_substitution as tutorial,
)

pytestmark = pytest.mark.tier_a


def test_qualified_tutorial_builds_one_public_non_oracle_run() -> None:
    request, expected_plaintext = tutorial.build_run_spec()
    solver = request.solver.to_dict()
    parameters = solver["parameters"]

    assert QUALIFICATION_RECIPE_ID == "periodic_columnar_decomposed_v2"
    assert len(QUALIFIED_INITIAL_KEY) == 210
    assert QUALIFIED_INITIAL_KEY[-7:] == (3, 5, 6, 4, 2, 1, 0)
    payload = ",".join(str(value) for value in QUALIFIED_INITIAL_KEY).encode("ascii")
    assert (
        hashlib.blake2b(
            payload,
            digest_size=20,
            person=b"rdp-pc-qual-v1",
        ).hexdigest()
        == QUALIFICATION_CANDIDATE_ID
    )
    assert request.initial_keys == (QUALIFIED_INITIAL_KEY,)
    assert len(expected_plaintext) == tutorial.PLAINTEXT_LENGTH
    assert tuple(request.problem_input.indices) != expected_plaintext
    assert parameters["steps"] == 360
    assert parameters["use_raw_score"] is True
    assert parameters["restarts"] == 1
    assert parameters["inner_batch_size"] == 192
    assert parameters["column_interval"] == 1
    assert parameters["column_batch_size"] == 384
    assert parameters["block_schedule"] == "round_robin"
    assert parameters["slip_policy"] == "on_stall"
    assert parameters["slip_interval"] == 60
    assert parameters["slip_blocks"] == 1
    assert parameters["stall_rounds"] == 220
    assert parameters["stall_slip_limit"] == 3
    assert parameters["slip_swaps"] == 50
    assert parameters["stop_after_stall_slip_limit"] is False
    assert solver["seed"] == 12_446
    assert parameters["target_score"] is None
    assert dict(request.scoring.character_order_weights) == {3: 0.5, 4: 0.5}
    assert request.scoring.wli_lane_enabled is False
    assert request.scoring.objective == tutorial.api.advanced.ScoringObjective.percentile_log_probability(window_size=10)
    assert request.text_direction is tutorial.api.TextDirection.RTL
    assert request.compute_device is tutorial.api.ComputeDevice.CPU


def test_qualified_tutorial_exposes_no_development_or_oracle_api() -> None:
    source = Path(tutorial.__file__).read_text(encoding="utf-8")

    assert "from rdp import api" in source
    for forbidden in (
        "cipher_development",
        "materialize_cipher_config",
        "build_scorer",
        "DecryptionProblem",
        "generate_seed_keys_periodic_columnar",
        "oracle_stop_score",
        "target_score=stop",
    ):
        assert forbidden not in source


def test_progress_prints_only_ten_percent_milestones_without_changing_events(capsys):
    for percent in range(101):
        payload = {"pct": percent, "step": percent * 360 // 100,
            "evals": percent * 2073, "best_score": 0.45}
        original = dict(payload)
        tutorial._progress(payload)
        assert payload == original
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 10
    for percent, line in zip(range(10, 101, 10), lines):
        assert line.startswith(f"[Kaeding] {percent}% ")
        assert "percentile=0.450000" in line
    assert "step=360" in lines[-1]


def test_startup_sets_cpu_expectations_without_initialisation_boilerplate(monkeypatch, capsys):
    class SearchBoundaryReached(Exception):
        pass

    expected_request, _ = tutorial.build_run_spec()

    def stop_at_search(request, *, progress_callback):
        assert request == expected_request
        assert progress_callback is tutorial._progress
        raise SearchBoundaryReached

    monkeypatch.setattr(tutorial.api, "run", stop_at_search)
    with pytest.raises(SearchBoundaryReached):
        tutorial.main()
    output = capsys.readouterr().out
    assert "This will likely take tens of minutes on a CPU, depending on its specifications." in output
    assert "expected result" in output
    assert "not supplied to solver" in output
    assert "15 minutes" not in output
    assert "qualification machine" not in output
    assert "Initialising RDP" not in output
    assert "display schema" not in output
    assert len(output.splitlines()) <= 13
