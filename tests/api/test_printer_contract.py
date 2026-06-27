from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from rune_decrypter_prime.api import (
    CipherSpec,
    KeySpec,
    NormalizedInput,
    RdpBannerStyle,
    RdpPrintDetail,
    RdpPrintFormat,
    RdpPrintOptions,
    RunResult,
    RunSpec,
    SolverSpec,
    format_rdp_banner,
    format_rdp_kv_block,
    format_rdp_preview_block,
    format_rdp_section,
    format_rdp_status_block,
    print_rdp_block,
    print_rdp_result,
    print_rdp_text,
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


def test_printer_rejects_bad_format_run_dir_and_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="output_format"):
        render_rdp_summary(_result(), output_format="xml")
    with pytest.raises(TypeError, match="run_dir must be a Path"):
        write_rdp_summary_artifact(_result(), run_dir=str(tmp_path))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="repo-relative"):
        format_rdp_banner(output_root=tmp_path)
    drive_path = "".join(("C", chr(58), chr(47), "tmp", chr(47), "output"))
    with pytest.raises(ValueError, match="repo-relative"):
        format_rdp_banner(output_root=drive_path)


def test_rdp_print_options_are_small_and_explicit() -> None:
    detailed = RdpPrintOptions.detailed()

    assert detailed.detail is RdpPrintDetail.DETAILED
    assert detailed.banner_style is RdpBannerStyle.PLAIN
    assert RdpPrintOptions.standard().detail is RdpPrintDetail.STANDARD
    assert RdpPrintOptions.compact().detail is RdpPrintDetail.COMPACT
    assert RdpPrintOptions.debug().width > detailed.width


def test_format_rdp_banner_defaults_to_plain_ascii() -> None:
    banner = format_rdp_banner()

    assert banner == (
        "Rune Decrypter Prime\n"
        "====================\n"
        "RDP V1 pre-release\n"
        "output root : output/\n"
    )
    assert "+" not in banner

    boxed = format_rdp_banner(options=RdpPrintOptions(banner_style=RdpBannerStyle.BOX))
    assert "+" in boxed
    assert "Rune Decrypter Prime" in boxed


def test_format_rdp_section_and_blocks_preserve_order() -> None:
    section = format_rdp_section("Initialising RDP")
    block = format_rdp_kv_block("Tutorial", [("name", "Columnar"), ("score", 0.5), ("asset", None)])
    preview = format_rdp_preview_block("Preview", [("runes", "ᚠᚢᚦ"), ("indices", [0, 1, 2])])

    assert section.startswith("Initialising RDP\n")
    assert "name  : Columnar" in block
    assert "score : 0.500000" in block
    assert "asset : unavailable" in block
    assert block.index("name") < block.index("score") < block.index("asset")
    assert "Preview" in preview
    assert "ᚠᚢᚦ" in preview


def test_print_rdp_text_adds_trailing_newline_when_needed() -> None:
    stream = io.StringIO()

    print_rdp_text("hello", file=stream)

    assert stream.getvalue() == "hello\n"


def test_format_rdp_status_block_uses_standard_key_value_style() -> None:
    status = format_rdp_status_block(
        "Model loading",
        [("ecdf", "ecdf/char/rtl/model.npz"), ("status", "loaded")],
    )

    assert "Model loading" in status
    assert "ecdf   : ecdf/char/rtl/model.npz" in status
    assert "status : loaded" in status


def test_print_rdp_block_adds_single_blank_line_after_block() -> None:
    stream = io.StringIO()

    print_rdp_block("hello\n", file=stream)

    assert stream.getvalue() == "hello\n\n"
