from __future__ import annotations

from types import SimpleNamespace

from rune_decrypter_prime.api.solver_report import SolverReportDetailKey, build_solver_report
from rune_decrypter_prime.utils.tutorial_report import (
    SCHEMA,
    build_tutorial_run_report,
    render_tutorial_run_report,
)


def _solution() -> SimpleNamespace:
    return SimpleNamespace(
        key=[3, 1, 4],
        plaintext_idx=[1, 2, 3, 4],
        plaintext_rune="ᚠᚢᚦᚩ",
        score=0.75,
        stop_reason="target_score",
        evals=42,
        tokens_processed=128,
        meta={
            "telemetry": {"events": []},
            "scorer_lanes": [
                {
                    "lane": "lm_char_wli",
                    "effective_state": "active",
                    "rank_effect": "production",
                }
            ],
        },
    )


def test_tutorial_report_builds_json_safe_payload_from_solution_and_solver_report() -> None:
    solver_report = build_solver_report(
        solver_name="beam",
        requested_seed=7,
        effective_seed=7,
        normalized_params={"beam_width": 4},
        stop_reason="target_score",
        best_score=0.75,
        best_key=[3, 1, 4],
        evals=42,
        tokens_processed=128,
        details={SolverReportDetailKey.SCORER_LANES.value: []},
    )

    report = build_tutorial_run_report(
        title="demo",
        cipher="scheduled_stream_lookup",
        solution=_solution(),
        solver_report=solver_report,
        match_ok=True,
        app_version="test-app",
        key_idx=[3, 1, 4],
        key_len=3,
        ct_idx=[9, 8, 7],
        ct_rune="ᚩᚦᚢ",
        pt_rune_ref="ᚠᚢᚦᚩ",
        pt_idx_ref=[1, 2, 3, 4],
    )

    assert report["schema"] == SCHEMA
    assert report["recovered"] is True
    assert report["match_ratio"] == 1.0
    assert report["solver"]["name"] == "beam"
    assert report["solver"]["score"] == 0.75
    assert report["key"]["exact"] is True
    assert report["solver_report"]["present"] is True
    assert report["solver_report"]["oracle_use"] == "none"
    assert report["solver_report"]["truth_data_policy"] == "none"


def test_tutorial_report_renderer_is_deterministic_and_includes_core_sections() -> None:
    report = build_tutorial_run_report(
        title="demo",
        cipher="vigenere",
        solution=_solution(),
        match_ok=True,
        key_idx=[3, 1, 4],
        pt_idx_ref=[1, 2, 3, 4],
    )

    lines = render_tutorial_run_report(report)

    assert lines[0] == "─" * 72
    assert any("RDP tutorial report · demo" in line for line in lines)
    assert any("schema" in line and SCHEMA in line for line in lines)
    assert any("cipher" in line and "vigenere" in line for line in lines)
    assert any("report" in line for line in lines)
