from __future__ import annotations

import json
from pathlib import Path

import pytest

from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    CandidateProvenance,
    CandidateRecord,
    candidate_id_for,
)
from cipher_development.shared.replay import (
    CandidateBatchPurpose,
    CandidateReplayContext,
    read_replay_context,
    select_candidate_batch,
    write_replay_context,
)
from cipher_development.shared.replay_evidence import (
    ReplayEvaluation,
    ReplayMode,
    read_candidate_replay,
    write_candidate_replay,
)
from cipher_development.shared.replay_execution import replay_candidate_batch


def _record(value: int, score: float) -> CandidateRecord:
    identity = {"key": [value]}
    return CandidateRecord(
        candidate_id=candidate_id_for(identity),
        identity=identity,
        payload={"key": [value]},
        scores={"wli_decision_score": score},
        provenance=CandidateProvenance(source="test"),
    )


def _batch():
    archive = CandidateArchive(ArchivePolicy(4, "wli_decision_score"))
    archive.offer(_record(1, 1.0))
    archive.offer(_record(2, 2.0))
    return select_candidate_batch(
        archive,
        purpose=CandidateBatchPurpose.REPLAY,
        selection_label="test",
        limit=2,
    )


def _context():
    return CandidateReplayContext.create(
        campaign_id="test_campaign",
        run_id="run-001",
        configuration_hash="a" * 40,
        evaluator_id="test_evaluator",
        payload={"ciphertext": [1, 2, 3], "wli": [[0, 3], [1, 3], [2, 3]]},
    )


def test_context_round_trip_and_truth_guard(tmp_path: Path):
    context = _context()
    path = tmp_path / "context.json"
    write_replay_context(path, context)
    assert read_replay_context(path) == context
    with pytest.raises(ValueError):
        CandidateReplayContext.create(
            campaign_id="test_campaign",
            run_id="run-001",
            configuration_hash="a" * 40,
            evaluator_id="test_evaluator",
            payload={"rune_matches": 3},
        )


def test_verify_replay_is_deterministic_and_round_trips(tmp_path: Path):
    batch = _batch()
    context = _context()

    def evaluator(candidate, _context):
        value = float(candidate.payload["key"][0])
        return ReplayEvaluation(
            scores={"wli_decision_score": value},
            stable_metrics={"candidate_id": candidate.candidate_id},
        )

    evidence = replay_candidate_batch(
        batch,
        context,
        evaluator=evaluator,
        mode=ReplayMode.VERIFY,
        decision_score="wli_decision_score",
        higher_is_better=True,
        evaluator_configuration={"surface": "test"},
        repeat_count=2,
    )
    assert evidence.deterministic is True
    assert evidence.stored_scores_verified is True
    assert evidence.ranking == batch.candidate_ids
    path = tmp_path / "replay.json"
    write_candidate_replay(path, evidence)
    assert read_candidate_replay(path) == evidence


def test_verify_detects_stored_score_drift():
    batch = _batch()
    context = _context()

    def evaluator(candidate, _context):
        return {"wli_decision_score": float(candidate.payload["key"][0]) + 1.0}

    evidence = replay_candidate_batch(
        batch,
        context,
        evaluator=evaluator,
        mode="verify",
        decision_score="wli_decision_score",
        higher_is_better=True,
        evaluator_configuration={"surface": "changed"},
    )
    assert evidence.stored_scores_verified is False


def test_rerank_uses_candidate_id_tie_breaker():
    batch = _batch()
    context = _context()
    evidence = replay_candidate_batch(
        batch,
        context,
        evaluator=lambda candidate, _: {"new_score": 1.0},
        mode="rerank",
        decision_score="new_score",
        higher_is_better=True,
        evaluator_configuration={"surface": "new"},
    )
    assert evidence.ranking == tuple(sorted(batch.candidate_ids))
    assert evidence.stored_scores_verified is None


def test_stable_metric_drift_is_rejected():
    batch = _batch()
    context = _context()
    calls = 0

    def evaluator(candidate, _context):
        nonlocal calls
        calls += 1
        return ReplayEvaluation(
            scores={"wli_decision_score": candidate.scores["wli_decision_score"]},
            stable_metrics={"call": calls},
        )

    with pytest.raises(ValueError, match="stable metrics"):
        replay_candidate_batch(
            batch,
            context,
            evaluator=evaluator,
            mode="verify",
            decision_score="wli_decision_score",
            higher_is_better=True,
            evaluator_configuration={"surface": "test"},
        )


def test_replay_tampering_is_rejected(tmp_path: Path):
    batch = _batch()
    context = _context()
    evidence = replay_candidate_batch(
        batch,
        context,
        evaluator=lambda candidate, _: {
            "wli_decision_score": candidate.scores["wli_decision_score"]
        },
        mode="verify",
        decision_score="wli_decision_score",
        higher_is_better=True,
        evaluator_configuration={"surface": "test"},
    )
    path = tmp_path / "replay.json"
    write_candidate_replay(path, evidence)
    payload = json.loads(path.read_text())
    payload["ranking"] = list(reversed(payload["ranking"]))
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="ranking|replay_id"):
        read_candidate_replay(path)


def test_context_reader_rejects_unknown_fields_and_paths(tmp_path: Path):
    context = _context()
    path = tmp_path / "context.json"
    write_replay_context(path, context)
    payload = json.loads(path.read_text())
    payload["unknown"] = 1
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="unknown"):
        read_replay_context(path)
    with pytest.raises(TypeError):
        CandidateReplayContext.create(
            campaign_id="test_campaign",
            run_id="run-001",
            configuration_hash="a" * 40,
            evaluator_id="test_evaluator",
            payload={"path": Path("x")},
        )


def test_score_repeat_drift_marks_replay_nondeterministic():
    batch = _batch()
    context = _context()
    calls = 0

    def evaluator(candidate, _context):
        nonlocal calls
        calls += 1
        return {"wli_decision_score": candidate.scores["wli_decision_score"] + calls * 0.1}

    evidence = replay_candidate_batch(
        batch,
        context,
        evaluator=evaluator,
        mode="verify",
        decision_score="wli_decision_score",
        higher_is_better=True,
        evaluator_configuration={"surface": "unstable"},
        repeat_count=2,
    )
    assert evidence.deterministic is False
    assert evidence.stored_scores_verified is False


def test_campaign_contexts_are_truth_free_and_content_addressed():
    from types import SimpleNamespace
    import numpy as np
    from cipher_development.two_period_overlay.replay import make_replay_context as wp3_context
    from cipher_development.periodic_sub_trans_wli.replay import make_replay_context as wp4_context

    wp3_case = SimpleNamespace(
        ciphertext=np.arange(30, dtype=np.uint8),
        wli=tuple((i, 30) for i in range(30)),
        crib=np.arange(3, dtype=np.uint8),
        particular=np.arange(30, dtype=np.uint8),
        basis=np.zeros((2, 30), dtype=np.uint8),
        free_columns=(0, 1),
    )
    first = wp3_context(wp3_case, run_id="run-001", configuration_hash="a" * 40)
    second = wp3_context(wp3_case, run_id="run-001", configuration_hash="a" * 40)
    assert first.context_id == second.context_id
    assert "truth" not in json.dumps(first.to_json_dict()).lower()

    wp4_case = SimpleNamespace(
        benchmark_id="bench", family="target", period=2, columns=3, length=30,
        order="col_then_sub", ciphertext=tuple(range(30)),
        wli=tuple((i, 30) for i in range(30)),
     )
    context = wp4_context(
        wp4_case, run_id="run-002", configuration_hash="b" * 40,
        raw_scoring={"char_weights": {3: 0.5}},
        wli_scoring={"wli_weights": {3: 0.5}},
    )
    encoded = json.dumps(context.to_json_dict()).lower()
    assert "truth_key" not in encoded
    assert context.payload["raw_scoring"]["char_weights"]["3"] == 0.5


def test_source_run_paths_cannot_escape(tmp_path: Path):
    from cipher_development.two_period_overlay.replay import _resolve_source_run as wp3_resolve
    from cipher_development.periodic_sub_trans_wli.replay import _resolve_source_run as wp4_resolve
    with pytest.raises(ValueError, match="directory name"):
        wp3_resolve(tmp_path, "../escape")
    with pytest.raises(ValueError, match="directory name"):
        wp4_resolve(tmp_path, "a/b")


def test_verify_checks_every_repeat_against_stored_score():
    batch = _batch()
    context = _context()
    calls = 0

    def evaluator(candidate, _context):
        nonlocal calls
        calls += 1
        score = candidate.scores["wli_decision_score"]
        if calls % 2 == 0:
            score += 0.5
        return {"wli_decision_score": score}

    evidence = replay_candidate_batch(
        batch,
        context,
        evaluator=evaluator,
        mode="verify",
        decision_score="wli_decision_score",
        higher_is_better=True,
        evaluator_configuration={"surface": "repeat_check"},
        repeat_count=2,
    )
    assert evidence.stored_scores_verified is False
