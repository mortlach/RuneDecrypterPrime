from __future__ import annotations

import json
from pathlib import Path

from cipher_development.two_period_overlay.b100_budget_sensitivity import (
    analyse_disjoint_blocks,
)
from cipher_development.two_period_overlay.review_pack import _required_artifacts


def _attempts(score_base: float) -> list[dict[str, object]]:
    return [
        {
            "input_index": index,
            "final_score": score_base + index * 0.0001,
            "candidate_id": f"candidate_{score_base}_{index}",
        }
        for index in range(160)
    ]


def test_disjoint_block_analysis_reports_rank_margin_and_survival() -> None:
    attempts = {
        "branch_controlled": _attempts(1.0),
        "branch_false_a": _attempts(0.2),
        "branch_false_b": _attempts(0.1),
    }
    result = analyse_disjoint_blocks(
        attempts,
        controlled_branch_id="branch_controlled",
        block_size=8,
        capacities=(2, 4),
    )
    assert result["block_count"] == 20
    assert result["top_1_block_count"] == 20
    assert result["top_3_block_count"] == 20
    assert result["survival_counts"] == {"2": 20, "4": 20}
    assert result["score_margin_summary"]["minimum"] > 0.7


def test_disjoint_block_analysis_rejects_incomplete_source() -> None:
    attempts = {
        "branch_controlled": _attempts(1.0)[:-1],
        "branch_false": _attempts(0.1),
    }
    try:
        analyse_disjoint_blocks(
            attempts,
            controlled_branch_id="branch_controlled",
            block_size=8,
        )
    except ValueError as exc:
        assert "complete" in str(exc)
    else:
        raise AssertionError("incomplete source attempts were accepted")


def test_sensitivity_review_pack_requires_diagnostic_artifacts() -> None:
    required = _required_artifacts("b100_scout_budget_sensitivity_v1")
    assert "artifacts/execution_timing.json" in required
    assert "artifacts/b100_budget_sensitivity/source_b100_gate.json" in required
    assert "artifacts/b100_budget_sensitivity/summary.json" in required


def test_b1000_review_pack_uses_dynamic_inventory(tmp_path: Path) -> None:
    inventory = tmp_path / "artifacts/experiment_b/required_artifacts.json"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        json.dumps({
            "schema": "rdp.two_period_overlay.dynamic_required_artifacts.v1",
            "paths": ["artifacts/experiment_b/branches/branch_a/scout/attempts.json"],
        }),
        encoding="utf-8",
    )
    required = _required_artifacts("candidate_word_branches_b1000_v1", tmp_path)
    assert "artifacts/experiment_b/branches/branch_a/scout/attempts.json" in required
