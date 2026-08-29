from __future__ import annotations
from rdp import api
import io
import json
from pathlib import Path
import pytest
from rune_decrypter_prime.core.config import Solution
from tests._helpers.reports import completed_status, make_solver_report

def _solution() -> Solution:
    sol = Solution(key=[1, 2], plaintext=[1, 2], score=3.5)
    sol.plaintext_idx = [1, 2]
    sol.ciphertext_idx = [3, 4]
    sol.plaintext_latin = 'AB'
    sol.stop_reason = 'stop_score'
    return sol

def _result() -> api.RunResult:
    report = make_solver_report(
        requested_seed=42,
        effective_seed=42,
        parameters={"width": 2},
        status=completed_status(
            api.advanced.StopReason.TARGET_SCORE_REACHED,
            runtime_reason="stop_score",
        ),
        best_score=3.5,
        best_key=(1, 2),
    )
    return api.RunResult(
        plaintext=tuple(_solution().plaintext_idx),
        plaintext_text=_solution().plaintext_latin,
        key=tuple(_solution().key),
        score=float(_solution().score),
        status=report.status,
        solver_report=report,
        scorer_report=api.advanced.ScorerReport(
            objective=api.advanced.ScoringObjective.percentile_log_probability(
                window_size=10
            ),
            score=float(_solution().score),
        ),
        configuration=api.advanced.RunConfigurationReport(
            solver=report.parameters,
            scoring=api.advanced.ConfigurationResolution(),
            cipher=api.advanced.ConfigurationResolution(),
        ),
        reproducibility=api.advanced.ReproducibilityMetadata(),
        oracle=api.advanced.OracleReport(),
        telemetry=dict(getattr(_solution(), "meta", {}).get("telemetry", {})),
    )


def _spec() -> api.RunSpec:
    return api.RunSpec(
        problem_input=api.RuneIndexInput(indices=[3, 4]),
        cipher=api.CipherSpec.periodic_substitution(period=2),
        key_space=api.KeySpec.periodic_substitution(period=2),
        solver=api.SolverSpec.beam_search(width=2, rounds=0, seed=42),
    )


def test_render_rdp_summary_text_and_json() -> None:
    text = api.display.render_summary(
        api.display.build_summary(_result(), spec=_spec(), reference_idx=[1, 2])
    )
    payload = api.display.render_summary(
        api.display.build_summary(_result(), spec=_spec(), reference_idx=[1, 2]),
        output_format=api.display.PrintFormat.JSON,
    )
    assert "RDP standard summary" in text
    assert "match_ratio: 1.0" in text
    data = json.loads(payload)
    assert data['schema'] == 'api_display_summary.v1'
    assert data['result']['match_ratio'] == 1.0

def test_print_rdp_result_returns_summary_and_writes_stream() -> None:
    stream = io.StringIO()
    summary = api.display.print_result(_result(), file=stream)
    assert summary.schema == 'api_display_summary.v1'
    assert 'RDP standard summary' in stream.getvalue()

def test_write_rdp_summary_artifact_returns_relative_path(tmp_path: Path) -> None:
    relpath = api.display.write_summary_artifact(
        api.display.build_summary(_result(), spec=_spec()), run_dir=tmp_path
    )
    assert relpath == "artifacts/rdp_display_summary.json"
    assert (tmp_path / relpath).is_file()

def test_printer_rejects_bad_format_run_dir_and_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="PrintFormat"):
        api.display.render_summary(
            _result(), output_format=api.display.PrintFormat("xml")
        )
    with pytest.raises(TypeError, match="run_dir must be a Path"):
        api.display.write_summary_artifact(
            api.display.build_summary(_result()), run_dir=str(tmp_path)
        )
    with pytest.raises(ValueError, match="repo-relative"):
        api.display.format_banner(output_root=tmp_path)
    drive_path = ''.join(('C', chr(58), chr(47), 'tmp', chr(47), 'output'))
    with pytest.raises(ValueError, match='repo-relative'):
        api.display.format_banner(output_root=drive_path)

def test_rdp_print_options_are_small_and_explicit() -> None:
    detailed = api.display.PrintOptions.detailed()
    assert detailed.detail is api.display.PrintDetail.DETAILED
    assert detailed.banner_style is api.display.BannerStyle.PLAIN
    assert api.display.PrintOptions.standard().detail is api.display.PrintDetail.STANDARD
    assert api.display.PrintOptions.compact().detail is api.display.PrintDetail.COMPACT
    assert api.display.PrintOptions.debug().width > detailed.width

def test_format_rdp_banner_defaults_to_plain_ascii() -> None:
    banner = api.display.format_banner()
    assert banner == 'Rune Decrypter Prime\n====================\nRDP V1 pre-release\noutput root : output/\n'
    assert '+' not in banner
    boxed = api.display.format_banner(options=api.display.PrintOptions(banner_style=api.display.BannerStyle.BOX))
    assert '+' in boxed
    assert 'Rune Decrypter Prime' in boxed

def test_format_rdp_section_and_blocks_preserve_order() -> None:
    section = api.display.format_section('Initialising RDP')
    block = api.display.format_key_value_block('Tutorial', [('name', 'Columnar'), ('score', 0.5), ('asset', None)])
    preview = api.display.format_preview_block('Preview', [('runes', 'ᚠᚢᚦ'), ('indices', [0, 1, 2])])
    assert section.startswith('Initialising RDP\n')
    assert 'name  : Columnar' in block
    assert 'score : 0.500000' in block
    assert 'asset : unavailable' in block
    assert block.index('name') < block.index('score') < block.index('asset')
    assert 'Preview' in preview
    assert 'ᚠᚢᚦ' in preview

def test_print_rdp_text_adds_trailing_newline_when_needed() -> None:
    stream = io.StringIO()
    api.display.print_text('hello', file=stream)
    assert stream.getvalue() == 'hello\n'

def test_format_rdp_status_block_uses_standard_key_value_style() -> None:
    status = api.display.format_status_block('Model loading', [('ecdf', 'ecdf/char/rtl/model.npz'), ('status', 'loaded')])
    assert 'Model loading' in status
    assert 'ecdf   : ecdf/char/rtl/model.npz' in status
    assert 'status : loaded' in status

def test_print_rdp_block_adds_single_blank_line_after_block() -> None:
    stream = io.StringIO()
    api.display.print_block('hello\n', file=stream)
    assert stream.getvalue() == 'hello\n\n'
