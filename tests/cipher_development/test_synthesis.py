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
        "reference_evaluation": (
            {"exact": False} if truth_policy == "benchmark_only" else None
        ),
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
        "hypothesis": "hypothesis",
        "alternative": "alternative",
        "configuration_hash": "b" * 40,
        "wli_mode": "with_wli",
        "truth_policy": truth_policy,
        "mechanisms": ["evidence_reproducibility"],
        "budget_seconds": 10.0,
        "budget_evaluations": 100,
        "lesson_ids": ["CSL-001"],
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


def test_synthesis_is_deterministic_and_excludes_reference_by_default(
    tmp_path: Path,
) -> None:
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
    assert first.selected_runs[0]["hypothesis"] == "hypothesis"
    assert first.selected_runs[0]["alternative"] == "alternative"
    assert first.selected_runs[0]["budget_seconds"] == 10.0
    assert first.selected_runs[0]["budget_evaluations"] == 100
    assert first.selected_runs[0]["lesson_ids"] == ["CSL-001"]
    assert render_milestone_markdown(first) == render_milestone_markdown(second)


def test_write_milestone_is_byte_stable(tmp_path: Path) -> None:
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


def test_unknown_and_duplicate_run_ids_are_rejected(tmp_path: Path) -> None:
    run_id = _fixture(tmp_path)
    with pytest.raises(ValueError, match="unique"):
        MilestoneSpec("m1", "demo_campaign", "M", "2026", (run_id, run_id))
    with pytest.raises(ValueError, match="absent"):
        build_milestone_summary(
            tmp_path,
            MilestoneSpec("m1", "demo_campaign", "M", "2026", ("missing",)),
        )


def test_ledger_result_disagreement_is_rejected(tmp_path: Path) -> None:
    run_id = _fixture(tmp_path)
    result = (
        tmp_path
        / "output/cipher_development/demo_campaign"
        / run_id
        / "artifacts/experiment_result.json"
    )
    payload = json.loads(result.read_text())
    payload["decision"] = "promote"
    result.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="decision mismatch"):
        build_milestone_summary(
            tmp_path,
            MilestoneSpec("m1", "demo_campaign", "M", "2026", (run_id,)),
        )


def test_blind_run_cannot_include_reference(tmp_path: Path) -> None:
    run_id = _fixture(tmp_path, truth_policy="none")
    result = (
        tmp_path
        / "output/cipher_development/demo_campaign"
        / run_id
        / "artifacts/experiment_result.json"
    )
    payload = json.loads(result.read_text())
    payload["reference_evaluation"] = {"bad": True}
    result.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="blind"):
        build_milestone_summary(
            tmp_path,
            MilestoneSpec(
                "m1",
                "demo_campaign",
                "M",
                "2026",
                (run_id,),
                include_reference_evaluation=True,
            ),
        )


def test_candidate_lesson_proposals_require_selected_evidence(tmp_path: Path) -> None:
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


def _replay_fixture(root: Path, *, duplicate: bool = False) -> str:
    from cipher_development.shared.archive import (
        ArchivePolicy,
        CandidateArchive,
        CandidateProvenance,
        CandidateRecord,
        candidate_id_for,
    )
    from cipher_development.shared.replay import (
        CandidateReplayContext,
        select_candidate_batch,
    )
    from cipher_development.shared.replay_binding import CandidateReplayBinding
    from cipher_development.shared.replay_evidence import write_candidate_replay
    from cipher_development.shared.replay_execution import replay_candidate_batch

    campaign = "demo_campaign"
    run_id = "run-001"
    run = root / "output/cipher_development" / campaign / run_id
    (run / "artifacts").mkdir(parents=True)
    archive = CandidateArchive(ArchivePolicy(2, "wli_decision_score"))
    for value in (1, 2):
        identity = {"key": [value]}
        archive.offer(
            CandidateRecord(
                candidate_id_for(identity),
                identity,
                {"key": [value]},
                {"wli_decision_score": float(value)},
                CandidateProvenance("test"),
            )
        )
    batch = select_candidate_batch(
        archive,
        purpose="replay",
        selection_label="test",
        limit=2,
    )
    context = CandidateReplayContext.create(
        campaign_id=campaign,
        run_id=run_id,
        configuration_hash="b" * 40,
        evaluator_id="test_evaluator",
        payload={"ciphertext": [1, 2]},
    )
    binding = CandidateReplayBinding.create(
        campaign_id=campaign,
        source_run_id=run_id,
        configuration_hash="b" * 40,
        benchmark_id="bench",
        context=context,
        batch=batch,
        context_artifact="artifacts/context.json",
        batch_artifact="artifacts/batch.json",
    )
    evidence = replay_candidate_batch(
        batch,
        context,
        binding,
        evaluator=lambda candidate, _: {
            "wli_decision_score": candidate.scores["wli_decision_score"]
        },
        mode="verify",
        decision_score="wli_decision_score",
        higher_is_better=True,
        evaluator_configuration={},
    )
    write_candidate_replay(run / "artifacts/candidate_replay.json", evidence)
    result_summary = {
        "source_binding_id": evidence.source_binding_id,
        "source_batch_id": evidence.source_batch_id,
        "source_context_id": evidence.source_context_id,
        "replay_id": evidence.replay_id,
        "deterministic": evidence.deterministic,
        "stored_scores_verified": evidence.stored_scores_verified,
        "ranking": list(evidence.ranking),
        "artifact": "artifacts/candidate_replay.json",
    }
    result = {
        "schema": "rdp_cipher_development_experiment_result.v1",
        "run_id": run_id,
        "campaign_id": campaign,
        "status": "completed",
        "decision": "refine",
        "result_summary": result_summary,
        "reference_evaluation": None,
    }
    (run / "artifacts/experiment_result.json").write_text(json.dumps(result))
    row = {
        "schema": "rdp_cipher_development_experiment_ledger.v1",
        "recorded_at": "2026-07-22T00:00:00+00:00",
        "run_id": run_id,
        "campaign_id": campaign,
        "experiment_id": "wp5_candidate_replay",
        "benchmark_id": "bench",
        "question": "q",
        "hypothesis": "h",
        "alternative": "a",
        "configuration_hash": "b" * 40,
        "wli_mode": "with_wli",
        "truth_policy": "none",
        "mechanisms": ["evidence_reproducibility"],
        "budget_seconds": None,
        "budget_evaluations": None,
        "lesson_ids": ["CSL-007"],
        "status": "completed",
        "decision": "refine",
        "stop_category": "success",
        "stop_reason": "done",
        "elapsed_s": 1.0,
        "telemetry": {},
        "result_summary": result_summary,
        "result_relpath": f"{run_id}/artifacts/experiment_result.json",
        "git_commit": None,
        "git_dirty": None,
    }
    campaign_out = root / "output/cipher_development" / campaign
    lines = [json.dumps(row)]
    if duplicate:
        lines.append(json.dumps(row))
    (campaign_out / "experiment_ledger.jsonl").write_text("\n".join(lines) + "\n")
    docs = root / "cipher_development"
    (docs / campaign).mkdir(parents=True)
    (docs / campaign / "CAMPAIGN.md").write_text("# Campaign\n")
    (docs / "LESSONS.md").write_text("# Lessons\n")
    return run_id


def test_synthesis_validates_and_hashes_replay_artifact(tmp_path: Path) -> None:
    run_id = _replay_fixture(tmp_path)
    summary = build_milestone_summary(
        tmp_path,
        MilestoneSpec("m1", "demo_campaign", "M", "2026", (run_id,)),
    )
    assert "replay:run-001" in summary.source_hashes
    assert summary.selected_runs[0]["replay_evidence"]["deterministic"] is True
    artifact = (
        tmp_path
        / "output/cipher_development/demo_campaign/run-001"
        / "artifacts/candidate_replay.json"
    )
    payload = json.loads(artifact.read_text())
    payload["ranking"] = list(reversed(payload["ranking"]))
    artifact.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        build_milestone_summary(
            tmp_path,
            MilestoneSpec("m1", "demo_campaign", "M", "2026", (run_id,)),
        )


def test_synthesis_rejects_duplicate_source_ledger_ids(tmp_path: Path) -> None:
    run_id = _replay_fixture(tmp_path, duplicate=True)
    with pytest.raises(ValueError, match="duplicate"):
        build_milestone_summary(
            tmp_path,
            MilestoneSpec("m1", "demo_campaign", "M", "2026", (run_id,)),
        )
