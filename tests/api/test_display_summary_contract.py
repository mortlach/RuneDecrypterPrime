from __future__ import annotations
from rdp import api
import json
import os
from pathlib import Path
from dataclasses import replace
import pytest
from rune_decrypter_prime.core.config import Solution
from rune_decrypter_prime.utils.tutorial_benchmark import TutorialAcceptanceKind
from tests._helpers.reports import completed_status, make_solver_report

def _solution() -> Solution:
    sol = Solution(key=[1, 2, 3], plaintext=[1, 2, 3], score=12.5)
    sol.plaintext_idx = [1, 2, 3]
    sol.ciphertext_idx = [4, 5, 6]
    sol.plaintext_latin = 'ABC'
    sol.plaintext_rune = 'ABC_RUNES'
    sol.ciphertext_latin = 'DEF'
    sol.ciphertext_rune = 'DEF_RUNES'
    sol.stop_reason = 'stop_score'
    sol.tokens_processed = 7
    sol.score_time_s = 0.25
    sol.meta = {'telemetry': {'run': {'seed': 123, 'solver': 'beam'}, 'solver': {'name': 'beam'}, 'scorer': {'impl': 'auto'}}, 'scorer_lanes': {'lanes': [], 'components': []}}
    return sol

def _solver_report():
    return make_solver_report(
        requested_seed=123,
        effective_seed=123,
        parameters={"width": 4},
        status=completed_status(
            api.advanced.StopReason.TARGET_SCORE_REACHED,
            runtime_reason="stop_score",
        ),
        best_score=12.5,
        best_key=(1, 2, 3),
        tokens_processed=7,
        score_time_seconds=0.25,
        details={"scorer_lanes": {"lanes": [], "components": []}},
    )


def _run_result() -> api.RunResult:
    return api.RunResult(plaintext=tuple(_solution().plaintext_idx), plaintext_text=_solution().plaintext_latin, key=tuple(_solution().key), score=float(_solution().score), status=_solver_report().status, solver_report=_solver_report(), scorer_report=api.advanced.ScorerReport(objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10), score=float(_solution().score)), configuration=api.advanced.RunConfigurationReport(solver=_solver_report().parameters, scoring=api.advanced.ConfigurationResolution(), cipher=api.advanced.ConfigurationResolution()), reproducibility=api.advanced.ReproducibilityMetadata(), oracle=api.advanced.OracleReport(), telemetry=dict(getattr(_solution(), 'meta', {}).get('telemetry', {})))

def _run_spec() -> api.RunSpec:
    return api.RunSpec(
        problem_input=api.RuneIndexInput(
            indices=[4, 5, 6], word_lengths=[[0, 3], [1, 3], [2, 3]]
        ),
        cipher=api.CipherSpec.periodic_substitution(period=3),
        key_space=api.KeySpec.periodic_substitution(period=3),
        solver=api.SolverSpec.beam_search(width=4, rounds=0, seed=123),
        scoring=api.ScoringConfig(
            objective=api.advanced.ScoringObjective.percentile_log_probability(
                window_size=10
            ),
            character_lane_enabled=True,
        ),
    )


def test_builds_spec_aware_display_summary() -> None:
    summary = api.display.build_summary(
        _run_result(),
        spec=_run_spec(),
        reference_idx=[1, 2, 4],
        tutorial_entry={
            "path": "Tutorial_Demo.py",
            "title": "Demo",
            "gate": "v1_smoke",
            "acceptance_kind": TutorialAcceptanceKind.EXACT.value,
            "min_match_ratio": 1.0,
        },
        artifacts={"solver_report_path": "artifacts/solver_report.json"},
        options=api.display.SummaryOptions.for_tutorial(),
    )
    data = summary.to_json_dict()
    assert data["schema"] == api.display.SUMMARY_SCHEMA
    assert data["problem"]["input_kind"] == "normalized"
    assert data["problem"]["ciphertext_length"] == 3
    assert data["cipher"]["name"] == "periodic_substitution"
    assert data["cipher"]["parameters"]["period"] == 3
    assert data["key"]["requested_key_spec"]["kind"] == "periodic_substitution"
    assert data["key"]["recovered_key"] == {
        "length": 3,
        "preview": [1, 2, 3],
        "truncated": False,
    }
    assert data["solver"]["name"] == "beam_search"
    assert data["solver"]["effective_seed"] == 123
    assert data["scoring"]["scorer"] == "auto"
    assert data["result"]["match_ratio"] == pytest.approx(2 / 3)
    assert data["result"]["reference_kind"] == "plaintext_idx"
    assert data["stop"]["stop_category"] == "success"
    assert data["oracle"]["mode"] == "real_solve"
    assert data["oracle"]["available"] is False
    assert data["tutorial"]["path"] == "Tutorial_Demo.py"
    assert (
        data["artifacts"]["display_summary_relpath"]
        == api.display.SUMMARY_RELATIVE_PATH
    )
    assert data["artifacts"]["solver_report_path"] == "artifacts/solver_report.json"
    assert data["solver_report"]["details"]["scorer_lanes"] == {
        "lanes": [],
        "components": [],
    }


def test_missing_runspec_is_visible_as_warning() -> None:
    summary = api.display.build_summary(_run_result())
    assert any(('RunSpec was not supplied' in warning for warning in summary.warnings))
    assert summary.problem['scope_note'] == 'Problem display is complete only when RunSpec is supplied.'

def test_text_reference_match_ratio_uses_normalised_plaintext() -> None:
    result = replace(_run_result(), plaintext_text="HELLO WORLD")
    summary = api.display.build_summary(result, reference_plaintext="hello there")
    assert summary.result["reference_kind"] == "plaintext_text"
    assert summary.result["match_ratio"] == pytest.approx(0.5)


def test_partial_recovery_tutorial_policy_is_warned() -> None:
    summary = api.display.build_summary(
        _run_result(),
        tutorial_entry={
            "acceptance_kind": TutorialAcceptanceKind.PARTIAL_RECOVERY.value
        },
    )
    assert (
        "tutorial accepts a partial-recovery threshold; exact recovery is not required"
        in summary.warnings
    )


def test_format_and_write_json_summary(tmp_path: Path) -> None:
    summary = api.display.build_summary(_run_result(), spec=_run_spec())
    text = api.display.format_summary(summary)
    assert "RDP standard summary" in text
    assert "encoding_dir: right_to_left" in text
    assert "stop_category: success" in text
    assert "Plaintext" in text
    out = tmp_path / "artifacts" / "rdp_display_summary.json"
    written = api.display.write_summary_json(summary, out)
    assert written == 'artifacts/rdp_display_summary.json'
    assert not os.path.isabs(written)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == api.display.SUMMARY_SCHEMA
    assert payload["solver"]["solver_name"] == "beam_search"

def test_write_json_accepts_default_standard_relpath(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    summary = api.display.build_summary(_run_result(), spec=_run_spec())
    written = api.display.write_summary_json(summary)
    assert written == api.display.SUMMARY_RELATIVE_PATH
    assert (tmp_path / api.display.SUMMARY_RELATIVE_PATH).is_file()

def test_artifact_paths_are_display_safe_not_absolute(tmp_path: Path) -> None:
    posix_abs = tmp_path / "runs" / "demo" / "artifacts" / "solver_report.json"
    drive = "C:"
    windows_abs = (
        drive + "\\Users\\alice\\runs\\demo\\artifacts\\rdp_display_summary.json"
    )
    summary = api.display.build_summary(
        _run_result(),
        spec=_run_spec(),
        artifacts={
            "solver_report_path": posix_abs,
            "display_summary_path": windows_abs,
            "nested": {"raw_log": "logs/app.jsonl"},
        },
    )
    data = summary.to_json_dict()
    assert data['artifacts']['solver_report_path'] == 'artifacts/solver_report.json'
    assert data['artifacts']['display_summary_path'] == 'artifacts/rdp_display_summary.json'
    assert data['artifacts']['nested']['raw_log'] == 'logs/app.jsonl'
    rendered = api.display.format_summary(summary)
    user_root_marker = drive + '/' + 'Users' + '/' + 'alice'
    assert str(tmp_path) not in rendered
    assert user_root_marker not in rendered

def test_display_options_validate_types() -> None:
    with pytest.raises(TypeError):
        api.display.SummaryOptions(include_key=1)
    with pytest.raises(ValueError):
        api.display.SummaryOptions(max_sequence_preview=-1)

def test_format_summary_prints_explicit_encoding_direction() -> None:
    spec = api.RunSpec(
        problem_input=api.RuneIndexInput(indices=[3, 4]),
        cipher=api.CipherSpec.periodic_substitution(period=2),
        key_space=api.KeySpec.periodic_substitution(period=2),
        solver=api.SolverSpec.beam_search(width=2, rounds=0, seed=42),
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
    )
    text = api.display.format_summary(
        api.display.build_summary(_run_result(), spec=spec)
    )
    assert "encoding_dir: left_to_right" in text


def test_display_prefers_canonical_run_status_over_legacy_solution_reason() -> None:
    solution = _solution()
    solution.stop_reason = "test_key"
    status = api.RunStatus(
        execution_status=api.advanced.ExecutionStatus.COMPLETED,
        stop_category=api.advanced.StopCategory.SUCCESS,
        stop_reason=api.advanced.StopReason.KNOWN_KEY_EXECUTION_COMPLETED,
        runtime_reason="test_key",
    )
    report = make_solver_report(
        requested_seed=None,
        effective_seed=0,
        parameters={"width": 1},
        best_key=tuple(solution.key),
        details={"execution_route": "known_key_fastpath"},
        status=status,
    )
    summary = api.display.build_summary(
        api.RunResult(
            plaintext=tuple(solution.plaintext_idx),
            plaintext_text=solution.plaintext_latin,
            key=tuple(solution.key),
            score=float(solution.score),
            status=report.status,
            solver_report=report,
            scorer_report=api.advanced.ScorerReport(
                objective=api.advanced.ScoringObjective.percentile_log_probability(
                    window_size=10
                ),
                score=float(solution.score),
            ),
            configuration=api.advanced.RunConfigurationReport(
                solver=report.parameters,
                scoring=api.advanced.ConfigurationResolution(),
                cipher=api.advanced.ConfigurationResolution(),
            ),
            reproducibility=api.advanced.ReproducibilityMetadata(),
            oracle=api.advanced.OracleReport(),
            telemetry=dict(getattr(solution, "meta", {}).get("telemetry", {})),
        )
    )
    data = summary.to_json_dict()
    assert data["stop"]["stop_reason"] == "known_key_execution_completed"
    assert data["stop"]["runtime_reason"] == "test_key"
    assert data["oracle"]["mode"] == "real_solve"
    assert data["oracle"]["available"] is False
