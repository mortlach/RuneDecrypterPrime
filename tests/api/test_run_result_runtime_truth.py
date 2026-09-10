from __future__ import annotations

import importlib
import json
from pathlib import Path

from rdp import api
from rdp.core.component_contracts import (
    CapabilityEffectiveState,
    CapabilityRequestState,
    FallbackPolicy,
    RankingEffect,
    ScorerCapabilityReport,
    ScoringLane,
    ScoringLaneStatus,
)
from rdp.core.config.solution import Solution


def _request(
    *,
    logging: api.LoggingConfig | None = None,
    scoring: api.ScoringConfig | None = None,
) -> api.RunSpec:
    return api.RunSpec(
        problem_input=api.RuneInput('a'),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=1),
        solver=api.SolverSpec.beam_search(width=1, rounds=1),
        scoring=api.ScoringConfig() if scoring is None else scoring,
        logging=logging,
    )


def _lane(
    lane: ScoringLane,
    *,
    request_state: CapabilityRequestState,
    effective_state: CapabilityEffectiveState,
    ranking_effect: RankingEffect,
    fallback_policy: FallbackPolicy,
) -> ScoringLaneStatus:
    return ScoringLaneStatus(
        lane=lane,
        request_state=request_state,
        effective_state=effective_state,
        ranking_effect=ranking_effect,
        fallback_policy=fallback_policy,
    )


def _capabilities() -> ScorerCapabilityReport:
    return ScorerCapabilityReport(
        lanes=(
            _lane(
                ScoringLane.LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH,
                request_state=CapabilityRequestState.REQUIRED,
                effective_state=CapabilityEffectiveState.ACTIVE,
                ranking_effect=RankingEffect.PRODUCTION,
                fallback_policy=FallbackPolicy.BLOCK,
            ),
            _lane(
                ScoringLane.HAMMING,
                request_state=CapabilityRequestState.REQUESTED,
                effective_state=CapabilityEffectiveState.ACTIVE,
                ranking_effect=RankingEffect.PRODUCTION,
                fallback_policy=FallbackPolicy.BLOCK,
            ),
            _lane(
                ScoringLane.SPAN_HAMMING_CALIBRATED,
                request_state=CapabilityRequestState.REQUESTED,
                effective_state=CapabilityEffectiveState.BLOCKED,
                ranking_effect=RankingEffect.PRODUCTION,
                fallback_policy=FallbackPolicy.BLOCK,
            ),
            _lane(
                ScoringLane.WORD_NGRAM_JUDGE_REPORT_ONLY,
                request_state=CapabilityRequestState.REQUESTED,
                effective_state=CapabilityEffectiveState.REPORT_ONLY,
                ranking_effect=RankingEffect.REPORT_ONLY,
                fallback_policy=FallbackPolicy.REPORT_ONLY,
            ),
        )
    )


def _solution(
    capabilities: ScorerCapabilityReport,
    *,
    stop_reason: str = 'max_rounds_reached',
) -> Solution:
    return Solution(
        key=[1],
        plaintext=[0],
        score=0.75,
        scorer_capabilities=capabilities,
        stop_reason=stop_reason,
        meta={
            'telemetry': {
                'run': {'start_ts': 0.0, 'solver': 'beam'},
                'scorer': {'impl': 'numpy', 'device': 'cpu', 'dtype': 'float32'},
                'solver_spans': {'beam': {'duration_s': 0.01}},
                'objective': {'raw_total': 0.25},
            },
            'scorer_lanes': capabilities.to_json_dict(),
        },
    )


def test_public_result_carries_runtime_scorer_truth(monkeypatch) -> None:
    run_module = importlib.import_module('rdp.api.run')
    capabilities = _capabilities()
    monkeypatch.setattr(run_module, 'execute_run', lambda **_kwargs: _solution(capabilities))

    result = api.run(_request())

    assert result.score == 0.75
    assert result.solver_report.best_score == 0.75
    assert result.scorer_report.score == 0.75
    assert result.scorer_report.raw_score == 0.25
    assert result.scorer_report.capabilities is capabilities
    assert result.scorer_report.capabilities.lanes[0].lane is ScoringLane.LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH
    assert [lane.effective_state for lane in result.scorer_report.capabilities.lanes[1:]] == [
        CapabilityEffectiveState.ACTIVE,
        CapabilityEffectiveState.BLOCKED,
        CapabilityEffectiveState.REPORT_ONLY,
    ]
    assert dict(result.scorer_report.telemetry) == {
        'impl': 'numpy',
        'device': 'cpu',
        'dtype': 'float32',
    }
    assert 'run' in result.telemetry
    assert 'solver_spans' in result.telemetry
    assert result.configuration.scoring.requested['backend'] == 'auto'
    assert result.configuration.scoring.effective['backend'] == 'numpy'
    assert result.reproducibility.backend is api.advanced.ScorerBackend.NUMPY
    assert result.reproducibility.scoring_config['backend'] == 'numpy'
    assert result.reproducibility.created_at_utc == '1970-01-01T00:00:00Z'


def test_logged_result_uses_authoritative_meta_identity(
    monkeypatch, tmp_path: Path
) -> None:
    run_module = importlib.import_module('rdp.api.run')
    capabilities = _capabilities()
    run_dir = tmp_path / 'run'
    (run_dir / 'config').mkdir(parents=True)
    (run_dir / 'artifacts').mkdir()
    (run_dir / 'META.json').write_text(
        json.dumps({
            'run_id': 'authoritative-run-id',
            'created_at_utc': '2026-09-09T10:11:12Z',
            'git': {'branch': 'release-test', 'commit': 'abc123'},
        }),
        encoding='utf-8',
    )
    (run_dir / 'config' / 'logging.json').write_text('{}', encoding='utf-8')
    monkeypatch.setattr(run_module, 'get_run_dir', lambda: run_dir)
    monkeypatch.setattr(run_module, 'execute_run', lambda **_kwargs: _solution(capabilities))

    result = api.run(_request(logging=api.LoggingConfig()))

    assert result.reproducibility.run_id == 'authoritative-run-id'
    assert result.reproducibility.created_at_utc == '2026-09-09T10:11:12Z'
    assert result.reproducibility.git_branch == 'release-test'
    assert result.reproducibility.git_commit == 'abc123'


def test_oracle_report_tracks_only_explicit_test_key_fastpath(monkeypatch) -> None:
    run_module = importlib.import_module('rdp.api.run')
    capabilities = ScorerCapabilityReport(lanes=())
    solutions = [
        _solution(capabilities, stop_reason='test_key'),
        _solution(capabilities, stop_reason='max_rounds_reached'),
    ]
    monkeypatch.setattr(run_module, 'execute_run', lambda **_kwargs: solutions.pop(0))

    test_key_result = api.run(_request())
    ordinary_result = api.run(_request())

    assert test_key_result.oracle.available is True
    assert test_key_result.oracle.used_for_stop is True
    assert test_key_result.oracle.mode is api.advanced.OracleMode.TEST
    assert test_key_result.oracle.stop_reason is api.advanced.StopReason.ORACLE_TEST_KEY_USED
    assert ordinary_result.oracle.available is False
    assert ordinary_result.oracle.used_for_stop is False
