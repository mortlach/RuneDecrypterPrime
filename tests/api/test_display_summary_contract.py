from __future__ import annotations

import json
from pathlib import Path

import pytest

from rune_decrypter_prime.api import (
    DISPLAY_SUMMARY_RELPATH,
    DISPLAY_SUMMARY_SCHEMA,
    CipherSpec,
    KeySpec,
    NormalizedInput,
    RdpDisplayOptions,
    RunResult,
    RunSpec,
    SolverSpec,
    build_rdp_summary,
    format_rdp_summary,
    write_rdp_summary_json,
)
from rune_decrypter_prime.api.solver_report import build_solver_report
from rune_decrypter_prime.core.config import Solution


def _solution() -> Solution:
    sol = Solution(key=[1, 2, 3], plaintext=[1, 2, 3], score=12.5)
    sol.plaintext_idx = [1, 2, 3]
    sol.ciphertext_idx = [4, 5, 6]
    sol.plaintext_latin = "ABC"
    sol.plaintext_rune = "ABC_RUNES"
    sol.ciphertext_latin = "DEF"
    sol.ciphertext_rune = "DEF_RUNES"
    sol.stop_reason = "stop_score"
    sol.tokens_processed = 7
    sol.score_time_s = 0.25
    sol.meta = {
        "telemetry": {
            "run": {"seed": 123, "solver": "beam"},
            "solver": {"name": "beam"},
            "scorer": {"impl": "auto"},
        },
        "scorer_lanes": {"lanes": [], "components": []},
    }
    return sol


def _solver_report():
    return build_solver_report(
        solver_name="beam",
        requested_seed=123,
        effective_seed=123,
        normalized_params={"beam_width": 4},
        stop_reason="stop_score",
        best_score=12.5,
        best_key=[1, 2, 3],
        tokens_processed=7,
        score_time_s=0.25,
        details={"scorer_lanes": {"lanes": [], "components": []}},
    )


def _run_result() -> RunResult:
    return RunResult(solution=_solution(), solver_report=_solver_report())


def _run_spec() -> RunSpec:
    return RunSpec(
        problem_input=NormalizedInput(ct_idx=[4, 5, 6], wli=[[0, 3], [1, 3], [2, 3]]),
        cipher=CipherSpec.periodic_substitution(period=3),
        key=KeySpec.repeat(len=3),
        solver=SolverSpec(name="beam", params={"beam_width": 4}, seed=123),
        scorer="rune",
        scorer_params={"objective": "pct.logp.win10", "include_char": True},
    )


def test_builds_spec_aware_display_summary() -> None:
    summary = build_rdp_summary(
        _run_result(),
        spec=_run_spec(),
        reference_idx=[1, 2, 4],
        tutorial_entry={
            "path": "Tutorial_Demo.py",
            "title": "Demo",
            "gate": "v1_smoke",
            "acceptance_kind": "min_match_ratio",
            "min_match_ratio": 1.0,
        },
        artifacts={"solver_report_path": "artifacts/solver_report.json"},
        options=RdpDisplayOptions.for_tutorial(),
    )

    data = summary.to_json_dict()

    assert data["schema"] == DISPLAY_SUMMARY_SCHEMA
    assert data["problem"]["input_kind"] == "normalized"
    assert data["problem"]["ciphertext_length"] == 3
    assert data["cipher"]["name"] == "periodic_substitution"
    assert data["cipher"]["extra"]["period"] == 3
    assert data["key"]["requested_key_spec"]["plan"] == "repeat"
    assert data["key"]["recovered_key"] == {"length": 3, "preview": [1, 2, 3], "truncated": False}
    assert data["solver"]["name"] == "beam"
    assert data["solver"]["effective_seed"] == 123
    assert data["scoring"]["scorer"] == "rune"
    assert data["result"]["match_ratio"] == pytest.approx(2 / 3)
    assert data["result"]["reference_kind"] == "plaintext_idx"
    assert data["stop"]["stop_category"] == "success"
    assert data["oracle"]["oracle_use"] == "none"
    assert data["tutorial"]["path"] == "Tutorial_Demo.py"
    assert data["artifacts"]["display_summary_relpath"] == DISPLAY_SUMMARY_RELPATH
    assert data["artifacts"]["solver_report_path"] == "artifacts/solver_report.json"
    assert data["solver_report"]["details"]["scorer_lanes"] == {"lanes": [], "components": []}


def test_missing_runspec_is_visible_as_warning() -> None:
    summary = build_rdp_summary(_run_result())

    assert any("RunSpec was not supplied" in warning for warning in summary.warnings)
    assert summary.problem["scope_note"] == "Problem display is complete only when RunSpec is supplied."


def test_text_reference_match_ratio_uses_normalised_plaintext() -> None:
    result = _run_result()
    result.solution.plaintext_latin = "HELLO WORLD"

    summary = build_rdp_summary(result, reference_plaintext="hello there")

    assert summary.result["reference_kind"] == "plaintext_text"
    assert summary.result["match_ratio"] == pytest.approx(0.5)


def test_near_solve_tutorial_policy_is_warned() -> None:
    summary = build_rdp_summary(
        _run_result(),
        tutorial_entry={"acceptance_kind": "near_solve_min_match"},
    )

    assert "tutorial accepts a near-solve threshold; exact recovery is not required" in summary.warnings


def test_format_and_write_json_summary(tmp_path: Path) -> None:
    summary = build_rdp_summary(_run_result(), spec=_run_spec())

    text = format_rdp_summary(summary)
    assert "RDP standard summary" in text
    assert "stop_category: success" in text
    assert "Plaintext" in text

    out = tmp_path / "artifacts" / "rdp_display_summary.json"
    written = write_rdp_summary_json(summary, out)

    assert written.endswith("artifacts/rdp_display_summary.json")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == DISPLAY_SUMMARY_SCHEMA
    assert payload["solver"]["solver_name"] == "beam"


def test_write_json_accepts_default_standard_relpath(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    summary = build_rdp_summary(_run_result(), spec=_run_spec())

    written = write_rdp_summary_json(summary)

    assert written == DISPLAY_SUMMARY_RELPATH
    assert (tmp_path / DISPLAY_SUMMARY_RELPATH).is_file()


def test_display_options_validate_types() -> None:
    with pytest.raises(TypeError):
        RdpDisplayOptions(include_key=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        RdpDisplayOptions(max_sequence_preview=-1)
