from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
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
from cipher_development.shared.replay_binding import CandidateReplayBinding
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


def _context(run_id: str = "run-001"):
    return CandidateReplayContext.create(
        campaign_id="test_campaign",
        run_id=run_id,
        configuration_hash="a" * 40,
        evaluator_id="test_evaluator",
        payload={"ciphertext": [1, 2, 3], "wli": [[0, 3], [1, 3], [2, 3]]},
    )


def _binding(batch=None, context=None):
    batch = _batch() if batch is None else batch
    context = _context() if context is None else context
    return CandidateReplayBinding.create(
        campaign_id=context.campaign_id,
        source_run_id=context.run_id,
        configuration_hash=context.configuration_hash,
        benchmark_id="test_benchmark",
        context=context,
        batch=batch,
        context_artifact="artifacts/context.json",
        batch_artifact="artifacts/batch.json",
    )


def _replay(batch, context, binding, evaluator, **overrides):
    options = {
        "mode": ReplayMode.VERIFY,
        "decision_score": "wli_decision_score",
        "higher_is_better": True,
        "evaluator_configuration": {"surface": "test"},
        "repeat_count": 2,
    }
    options.update(overrides)
    return replay_candidate_batch(
        batch,
        context,
        binding,
        evaluator=evaluator,
        **options,
    )


def test_context_round_trip_and_truth_guard(tmp_path: Path):
    context = _context()
    path = tmp_path / "context.json"
    write_replay_context(path, context)
    assert read_replay_context(path) == context
    for key in ("rune_matches", "plaintext", "truth_key_seed"):
        with pytest.raises(ValueError):
            CandidateReplayContext.create(
                campaign_id="test_campaign",
                run_id="run-001",
                configuration_hash="a" * 40,
                evaluator_id="test_evaluator",
                payload={key: 3},
            )


def test_verify_replay_is_bound_deterministic_and_round_trips(tmp_path: Path):
    batch = _batch()
    context = _context()
    binding = _binding(batch, context)

    def evaluator(candidate, _context):
        value = float(candidate.payload["key"][0])
        return ReplayEvaluation(
            scores={"wli_decision_score": value},
            stable_metrics={"candidate_id": candidate.candidate_id},
        )

    evidence = _replay(batch, context, binding, evaluator)
    assert evidence.deterministic is True
    assert evidence.stored_scores_verified is True
    assert evidence.source_binding_id == binding.binding_id
    assert evidence.ranking == batch.candidate_ids
    path = tmp_path / "replay.json"
    write_candidate_replay(path, evidence)
    assert read_candidate_replay(path) == evidence


def test_binding_rejects_context_or_batch_mixing():
    batch = _batch()
    context = _context()
    binding = _binding(batch, context)
    with pytest.raises(ValueError, match="binding"):
        _replay(
            batch,
            _context("run-002"),
            binding,
            lambda candidate, _: {
                "wli_decision_score": candidate.scores["wli_decision_score"]
            },
        )
    other_batch = _batch()
    other_payload = other_batch.to_json_dict()
    other_payload["selection_label"] = "different"
    from cipher_development.shared.replay import CandidateReplayBatch, _batch_id
    content = {key: value for key, value in other_payload.items() if key != "batch_id"}
    other_payload["batch_id"] = _batch_id(content)
    other_batch = CandidateReplayBatch.from_json_dict(other_payload)
    with pytest.raises(ValueError, match="binding"):
        _replay(
            other_batch,
            context,
            binding,
            lambda candidate, _: {
                "wli_decision_score": candidate.scores["wli_decision_score"]
            },
        )


def test_verify_detects_stored_score_drift():
    batch = _batch()
    context = _context()
    evidence = _replay(
        batch,
        context,
        _binding(batch, context),
        lambda candidate, _: {
            "wli_decision_score": float(candidate.payload["key"][0]) + 1.0
        },
    )
    assert evidence.stored_scores_verified is False


def test_rerank_uses_candidate_id_tie_breaker():
    batch = _batch()
    context = _context()
    evidence = _replay(
        batch,
        context,
        _binding(batch, context),
        lambda candidate, _: {"new_score": 1.0},
        mode="rerank",
        decision_score="new_score",
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
        _replay(batch, context, _binding(batch, context), evaluator)


def test_replay_tampering_is_rejected(tmp_path: Path):
    batch = _batch()
    context = _context()
    evidence = _replay(
        batch,
        context,
        _binding(batch, context),
        lambda candidate, _: {
            "wli_decision_score": candidate.scores["wli_decision_score"]
        },
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
        return {
            "wli_decision_score": candidate.scores["wli_decision_score"] + calls * 0.1
        }

    evidence = _replay(batch, context, _binding(batch, context), evaluator)
    assert evidence.deterministic is False
    assert evidence.stored_scores_verified is False


def test_campaign_contexts_are_truth_free_and_content_addressed():
    from cipher_development.two_period_overlay.replay import make_replay_context as wp3_context
    from cipher_development.periodic_sub_trans_wli.replay import make_replay_context as wp4_context

    provenance = {
        "evaluator_source_sha256": "a" * 64,
        "git_commit": "b" * 40,
        "git_dirty": False,
        "package_version": "1.0.0",
        "language_model_assets": [{
            "logical_path": "asset.bin", "sha256": "c" * 64, "size_bytes": 1,
        }],
        "asset_manifest_complete": True,
    }
    wp3_case = SimpleNamespace(
        ciphertext=np.arange(30, dtype=np.uint8),
        wli=tuple((i, 30) for i in range(30)),
        crib=np.arange(3, dtype=np.uint8),
        particular=np.arange(30, dtype=np.uint8),
        basis=np.zeros((30, 2), dtype=np.uint8),
        free_columns=(0, 1),
    )
    first = wp3_context(
        wp3_case,
        run_id="run-001",
        configuration_hash="a" * 40,
        evaluator_provenance=provenance,
    )
    second = wp3_context(
        wp3_case,
        run_id="run-001",
        configuration_hash="a" * 40,
        evaluator_provenance=provenance,
    )
    assert first.context_id == second.context_id
    assert "truth" not in json.dumps(first.to_json_dict()).lower()

    wp4_case = SimpleNamespace(
        benchmark_id="bench", family="target", period=2, columns=3, length=30,
        order="col_then_sub", ciphertext=tuple(range(30)),
        wli=tuple((i, 30) for i in range(30)),
    )
    context = wp4_context(
        wp4_case,
        run_id="run-002",
        configuration_hash="b" * 40,
        raw_scoring={"model_root": None, "encoding_direction": "ltr"},
        wli_scoring={"model_root": None, "encoding_direction": "ltr"},
        evaluator_provenance=provenance,
    )
    encoded = json.dumps(context.to_json_dict()).lower()
    assert "truth_key" not in encoded
    assert context.payload["evaluator_provenance"]["asset_manifest_complete"] is True


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

    evidence = _replay(batch, context, _binding(batch, context), evaluator)
    assert evidence.stored_scores_verified is False


def test_load_bound_source_requires_completed_recorded_binding(tmp_path: Path):
    from cipher_development.shared.replay import write_candidate_batch
    from cipher_development.shared.replay_binding import (
        load_bound_replay_source,
        write_replay_binding,
    )

    run = tmp_path / "run-001"
    (run / "artifacts").mkdir(parents=True)
    batch = _batch()
    context = _context()
    binding = _binding(batch, context)
    write_candidate_batch(run / "artifacts/batch.json", batch)
    write_replay_context(run / "artifacts/context.json", context)
    write_replay_binding(run / "artifacts/binding.json", binding)
    (run / "artifacts/experiment_manifest.json").write_text(json.dumps({
        "schema": "rdp_cipher_development_experiment_manifest.v1",
        "run_id": "run-001",
        "campaign_id": "test_campaign",
        "configuration_hash": "a" * 40,
    }))
    result = {
        "schema": "rdp_cipher_development_experiment_result.v1",
        "run_id": "run-001",
        "campaign_id": "test_campaign",
        "status": "completed",
        "result_summary": {
            "replay_bindings": {
                "x": {
                    "binding_id": binding.binding_id,
                    "artifact": "artifacts/binding.json",
                }
            }
        },
    }
    (run / "artifacts/experiment_result.json").write_text(json.dumps(result))
    loaded = load_bound_replay_source(
        run,
        "artifacts/binding.json",
        expected_campaign_id="test_campaign",
        expected_run_id="run-001",
    )
    assert loaded[2].binding_id == binding.binding_id
    result["result_summary"]["replay_bindings"]["x"]["binding_id"] = "0" * 40
    (run / "artifacts/experiment_result.json").write_text(json.dumps(result))
    with pytest.raises(ValueError, match="does not record"):
        load_bound_replay_source(
            run,
            "artifacts/binding.json",
            expected_campaign_id="test_campaign",
            expected_run_id="run-001",
        )


def test_wp3_candidate_identity_payload_and_gauge_are_enforced():
    from cipher_development.two_period_overlay.replay import validate_candidate_payload

    period_a, period_b = 13, 17
    particular = np.zeros(period_a + period_b, dtype=np.uint8)
    basis = np.zeros((period_a + period_b, 1), dtype=np.uint8)
    basis[0, 0] = 1
    context = CandidateReplayContext.create(
        campaign_id="two_period_overlay",
        run_id="r",
        configuration_hash="a" * 40,
        evaluator_id="e",
        payload={
            "benchmark_id": "alice_308_p13_p17",
            "gauge": "B[0]=0",
            "period_a": period_a,
            "period_b": period_b,
            "particular": particular.tolist(),
            "basis": basis.tolist(),
        },
    )
    key = np.zeros(period_a + period_b, dtype=int)
    key[0] = 3
    identity = {"expanded_key": key.tolist()}
    record = CandidateRecord(
        candidate_id_for(identity),
        identity,
        {"variables": [3], "expanded_key": key.tolist()},
        {"wli_decision_score": 1.0},
        CandidateProvenance("test"),
    )
    assert np.array_equal(validate_candidate_payload(record, context), key)
    bad_identity = {"expanded_key": np.ones(period_a + period_b, dtype=int).tolist()}
    bad = CandidateRecord(
        candidate_id_for(bad_identity),
        bad_identity,
        record.payload,
        record.scores,
        record.provenance,
    )
    with pytest.raises(ValueError, match="identity"):
        validate_candidate_payload(bad, context)


def test_wp4_candidate_identity_payload_and_context_are_enforced():
    from cipher_development.periodic_sub_trans_wli.replay import validate_candidate_payload

    period, columns = 1, 3
    key = [*range(29), 0, 1, 2]
    context = CandidateReplayContext.create(
        campaign_id="periodic_sub_trans_wli",
        run_id="r",
        configuration_hash="a" * 40,
        evaluator_id="e",
        payload={
            "period": period,
            "columns": columns,
            "alphabet_size": 29,
            "order": "col_then_sub",
            "raw_score": "seed_raw_score",
            "wli_score": "wli_decision_score",
            "key_contract": {"key_length": 32},
        },
    )
    identity = {
        "cipher": "periodic_columnar",
        "order": "col_then_sub",
        "period": period,
        "columns": columns,
        "expanded_key": key,
    }
    payload = {
        "expanded_key": key,
        "period": period,
        "columns": columns,
        "order": "col_then_sub",
    }
    record = CandidateRecord(
        candidate_id_for(identity),
        identity,
        payload,
        {"seed_raw_score": 1.0, "wli_decision_score": 2.0},
        CandidateProvenance("test"),
    )
    assert validate_candidate_payload(record, context).size == 32
    other = key.copy()
    other[0], other[1] = other[1], other[0]
    bad = CandidateRecord(
        candidate_id_for(identity),
        identity,
        {**payload, "expanded_key": other},
        record.scores,
        record.provenance,
    )
    with pytest.raises(ValueError, match="identity"):
        validate_candidate_payload(bad, context)


def test_evaluator_provenance_hashes_source_and_explicit_assets(tmp_path: Path):
    from cipher_development.shared.replay_provenance import (
        build_evaluator_provenance,
        validate_evaluator_provenance,
    )

    source = tmp_path / "evaluator.py"
    source.write_text("x = 1\n")
    assets = tmp_path / "models"
    assets.mkdir()
    (assets / "model.json").write_text('{"x": 1}\n')
    provenance = build_evaluator_provenance(
        repo_root=tmp_path,
        evaluator_source=source,
        scoring_contracts=({"model_root": "models"},),
        run_meta={"git": {"commit": "a" * 40, "dirty": False}},
        require_assets=True,
    )
    assert provenance["asset_manifest_complete"] is True
    assert provenance["language_model_assets"][0]["logical_path"].startswith(
        "contract_0/"
    )
    validate_evaluator_provenance(provenance, dict(provenance))
    changed = dict(provenance)
    changed["evaluator_source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="provenance"):
        validate_evaluator_provenance(provenance, changed)
