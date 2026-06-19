from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from rune_decrypter_prime.api import CipherSpec, KeySpec, NormalizedInput, RunResult, RunSpec, SolverSpec
from rune_decrypter_prime.api.printer import (
    RdpPrintFormat,
    print_rdp_result,
    render_rdp_summary,
    write_rdp_summary_artifact,
)
from rune_decrypter_prime.api.solver_report import build_solver_report
from rune_decrypter_prime.core.config import Solution


def _solution() -> Solution:
    sol = Solution(key=[1, 2], plaintext=[1, 2], score=3.5)
    sol.plaintext_idx = [1, 2]
    sol.ciphertext_idx = [3, 4]
    sol.plaintext_latin = "AB"
    sol.stop_reason = "stop_score"
    return sol


def _result() -> RunResult:
    report = build_solver_report(
        solver_name="beam",
        requested_seed=42,
        effective_seed=42,
        normalized_params={"beam_width": 2},
        stop_reason="stop_score",
        best_score=3.5,
        best_key=[1, 2],
    )
    return RunResult(solution=_solution(), solver_report=report)


def _spec() -> RunSpec:
    return RunSpec(
        problem_input=NormalizedInput(ct_idx=[3, 4]),
        cipher=CipherSpec.periodic_substitution(period=2),
        key=KeySpec.repeat(len=2),
        solver=SolverSpec(name="beam", params={"beam_width": 2}, seed=42),
    )


def test_render_rdp_summary_text_and_json() -> None:
    text = render_rdp_summary(_result(), spec=_spec(), reference_idx=[1, 2])
    payload = render_rdp_summary(
        _result(),
        spec=_spec(),
        reference_idx=[1, 2],
        output_format=RdpPrintFormat.JSON,
    )

    assert "RDP standard summary" in text
    assert "match_ratio: 1.0" in text
    data = json.loads(payload)
    assert data["schema"] == "api_display_summary.v1"
    assert data["result"]["match_ratio"] == 1.0


def test_print_rdp_result_returns_summary_and_writes_stream() -> None:
    stream = io.StringIO()

    summary = print_rdp_result(_result(), spec=_spec(), file=stream)

    assert summary.schema == "api_display_summary.v1"
    assert "RDP standard summary" in stream.getvalue()


def test_write_rdp_summary_artifact_returns_relative_path(tmp_path: Path) -> None:
    relpath = write_rdp_summary_artifact(_result(), run_dir=tmp_path, spec=_spec())

    assert relpath == "artifacts/rdp_display_summary.json"
    assert (tmp_path / relpath).is_file()


def test_printer_rejects_bad_format_and_run_dir(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="output_format"):
        render_rdp_summary(_result(), output_format="xml")
    with pytest.raises(TypeError, match="run_dir must be a Path"):
        write_rdp_summary_artifact(_result(), run_dir=str(tmp_path))  # type: ignore[arg-type]
