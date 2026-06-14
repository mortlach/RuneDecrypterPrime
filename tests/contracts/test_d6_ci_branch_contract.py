from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FULL_PROOF_WORKFLOW = ROOT / ".github" / "workflows" / "rdp_v1_full_proof.yml"


def test_full_proof_workflow_runs_on_active_d6_branch() -> None:
    text = FULL_PROOF_WORKFLOW.read_text(encoding="utf-8")

    assert "prelease/v1.0.0_d6" in text
    assert "preleasev1.0.0_d5" in text
    assert "workflow_dispatch" in text
