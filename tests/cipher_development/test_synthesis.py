from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cipher_development.shared.synthesis import (
    MilestoneSpec,
    build_milestone_summary,
    render_milestone_markdown,
    write_milestone,
)


def _fixture(root: Path, *, truth_policy: str = "benchmark_only") -> str:
    campaign = "demo_campaign"
    run_id = "run-001"
    campaign_out = root / "output/cipher_development" / campaign
    result = campaign_out / run_id / "artifacts/experiment_result.json"
    result.parent.mkdir(parents=True)
    payload = {
        "schema": "rdp_cipher_development_experiment_result.v1",
        "run_id": run_id,
        "campaign_id": campaign,
        "experiment_id": "demo",
        "status": "completed",
        "decision": "refine",
        "stop_category": "budget",
        "stop_reason": "max_rounds",
        "elapsed_s": 1.0,
        "telemetry": {},
        "result_summary": {"artifact": "artifacts/x.json"},
        "reference_evaluation": {"exact": False} if truth_policy == "benchmark_only" else None,
    }
    result.write_text(json.dumps(payload) + "\n")
    row = {
        "schema": "rdp_cipher_development_experiment_ledger.v1",
        "recorded_at": "2026-07-22T00:00:00+00:00",
        "run_id": run_id,
        "campaign_id": campaign,
        "experiment_id": "demo",
        "benchmark_id": "bench",
        "question": "question",
        "configuration_hash": "b" * 40,
        "wli_mode": "with_wli",
        "truth_policy": truth_policy,
        "mechanisms": ["evidence_reproducibility"],
        "status": "completed",
        "decision": "refine",
        "stop_category": "budget",
        "stop_reason": "max_rounds",
        "elapsed_s": 1.0,
        "telemetry": {},
        "result_summary": {},
        "result_relpath": f"{run_id}/artifacts/experiment_result.json",
        "git_commit": None,
        "git_dirty": None,
    }
    campaign_out.mkdir(parents=True, exist_ok=True)
    (campaign_out / "experiment_ledger.jsonl").write_text(json.dumps(row) + "\n")
    docs = root / "cipher_development"
    (docs / campaign).mkdir(parents=True)
    (docs / campaign / "CAMPAIGN.md").write_text("# Campaign\n")
    (docs / "LESSONS.md").write_text("# Lessons\n")
    return run_id


def test_synthesis_is_deterministic_and_excludes_reference_by_default(tmp_path: Path):
    run_id = _fixture(tmp_path)
    spec = MilestoneSpec(
        milestone_id="m1",
        campaign_id="demo_campaign",
        title="Milestone",
        as_of="2026-07-22",
        selected_run_ids=(run_id,),
    )
    first = build_milestone_summary(tmp_path, spec)
    second = build_milestone_summary(tmp_path, spec)
    assert first.to_json_dict() == second.to_json_dict()
    assert "reference_evaluation" not in first.selected_runs[0]
    assert render_milestone_markdown(first) == render_milestone_markdown(second)


def test_write_milestone_is_byte_stable(tmp_path: Path):
    run_id = _fixture(tmp_path)
    spec = MilestoneSpec("m1", "demo_campaign", "Milestone", "2026-07-22", (run_id,))
    json_path, md_path = write_milestone(tmp_path, spec)
    hashes = (
        hashlib.sha256(json_path.read_bytes()).hexdigest(),
        hashlib.sha256(md_path.read_bytes()).hexdigest(),
    )
    write_milestone(tmp_path, spec)
    assert hashes == (
        hashlib.sha256(json_path.read_bytes()).hexdigest(),
        hashlib.sha256(md_path.read_bytes()).hexdigest(),
    )


def test_unknown_and_duplicate_run_ids_are_rejected(tmp_path: Path):
    run_id = _fixture(tmp_path)
    with pytest.raises(ValueError, match="unique"):
        MilestoneSpec("m1", "demo_campaign", "M", "2026", (run_id, run_id))
    with pytest.raises(ValueError, match="absent"):
        build_milestone_summary(
            tmp_path,
            MilestoneSpec("m1", "demo_campaign", "M", "2026", ("missing",)),
        )


def test_ledger_result_disagreement_is_rejected(tmp_path: Path):
    run_id = _fixture(tmp_path)
    result = (
        tmp_path / "output/cipher_development/demo_campaign"
        / run_id / "artifacts/experiment_result.json"
    )
    payload = json.loads(result.read_text())
    payload["decision"] = "promote"
    result.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="decision mismatch"):
        build_milestone_summary(
            tmp_path,
            MilestoneSpec("m1", "demo_campaign", "M", "2026", (run_id,)),
        )


def test_blind_run_cannot_include_reference(tmp_path: Path):
    run_id = _fixture(tmp_path, truth_policy="none")
    result = (
        tmp_path / "output/cipher_development/demo_campaign"
        / run_id / "artifacts/experiment_result.json"
    )
    payload = json.loads(result.read_text())
    payload["reference_evaluation"] = {"bad": True}
    result.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="blind"):
        build_milestone_summary(
            tmp_path,
            MilestoneSpec(
                "m1", "demo_campaign", "M", "2026", (run_id,),
                include_reference_evaluation=True,
            ),
        )


def test_candidate_lesson_proposals_require_selected_evidence(tmp_path: Path):
    run_id = _fixture(tmp_path)
    proposal = {
        "proposal_id": "p1",
        "title": "Replay is useful",
        "suggested_status": "candidate",
        "scope": "demo",
        "evidence_run_ids": [run_id],
        "reason": "replayed",
        "known_limits": "one campaign",
    }
    spec = MilestoneSpec(
        "m1",
        "demo_campaign",
        "M",
        "2026",
        (run_id,),
        candidate_lesson_proposals=(proposal,),
    )
    assert spec.candidate_lesson_proposals[0]["proposal_id"] == "p1"
    proposal["evidence_run_ids"] = ["missing"]
    with pytest.raises(ValueError, match="not selected"):
        MilestoneSpec(
            "m1",
            "demo_campaign",
            "M",
            "2026",
            (run_id,),
            candidate_lesson_proposals=(proposal,),
        )
