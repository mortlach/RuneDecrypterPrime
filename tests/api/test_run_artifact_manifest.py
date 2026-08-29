from __future__ import annotations
from rdp import api
import rdp.api.run_artifact_manifest
import json
import os
from pathlib import Path
import pytest

def _write_required_files(run_dir: Path) -> None:
    (run_dir / 'config').mkdir(parents=True, exist_ok=True)
    (run_dir / 'artifacts').mkdir(parents=True, exist_ok=True)
    (run_dir / 'META.json').write_text('{}\n', encoding='utf-8')
    (run_dir / 'config' / 'logging.json').write_text('{}\n', encoding='utf-8')

def _read_manifest(run_dir: Path) -> dict[str, object]:
    return json.loads((run_dir / rdp.api.run_artifact_manifest.MANIFEST_RELPATH).read_text(encoding='utf-8'))

def test_writes_v1_manifest_under_artifacts(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    relpath = rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path)
    assert relpath == 'artifacts/run_artifacts_manifest.json'
    payload = _read_manifest(tmp_path)
    assert payload['manifest_version'] == 'api_run_artifacts.v1'
    assert (tmp_path / relpath).is_file()

def test_manifest_uses_fixed_order_and_run_relative_posix_paths(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    (tmp_path / 'artifacts' / 'solver_report.json').write_text('{}\n', encoding='utf-8')
    (tmp_path / 'artifacts' / 'rdp_display_summary.json').write_text('{}\n', encoding='utf-8')
    rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path)
    rows = _read_manifest(tmp_path)['rows']
    assert isinstance(rows, list)
    assert [row['relpath'] for row in rows] == ['META.json', 'config/logging.json', 'artifacts/solver_report.json', 'artifacts/rdp_display_summary.json']
    assert all((not os.path.isabs(row['relpath']) for row in rows))
    assert all(('\\' not in row['relpath'] for row in rows))

def test_includes_required_rows_without_solver_report_or_display_summary(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path)
    rows = _read_manifest(tmp_path)['rows']
    assert isinstance(rows, list)
    assert [row['artifact_kind'] for row in rows] == ['run_meta', 'logging_config']
    assert all((row['present'] is True for row in rows))
    assert all((row['required'] is True for row in rows))

def test_includes_solver_report_row_when_requested(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    (tmp_path / 'artifacts' / 'solver_report.json').write_text('{}\n', encoding='utf-8')
    rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path, include_solver_report=True)
    rows = _read_manifest(tmp_path)['rows']
    assert isinstance(rows, list)
    solver_row = rows[-1]
    assert solver_row['relpath'] == 'artifacts/solver_report.json'
    assert solver_row['artifact_kind'] == 'solver_report'
    assert solver_row['required'] is False
    assert solver_row['present'] is True

def test_includes_existing_solver_report_row_when_not_requested(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    (tmp_path / 'artifacts' / 'solver_report.json').write_text('{}\n', encoding='utf-8')
    rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path, include_solver_report=False)
    rows = _read_manifest(tmp_path)['rows']
    assert isinstance(rows, list)
    assert [row['artifact_kind'] for row in rows] == ['run_meta', 'logging_config', 'solver_report']

def test_includes_existing_display_summary_row_when_present(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    (tmp_path / 'artifacts' / 'rdp_display_summary.json').write_text('{}\n', encoding='utf-8')
    rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path)
    rows = _read_manifest(tmp_path)['rows']
    assert isinstance(rows, list)
    assert [row['artifact_kind'] for row in rows] == ['run_meta', 'logging_config', 'rdp_display_summary']
    display_row = rows[-1]
    assert display_row['relpath'] == 'artifacts/rdp_display_summary.json'
    assert display_row['required'] is False
    assert display_row['present'] is True

def test_omits_missing_solver_report_and_display_summary_when_not_requested(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path, include_solver_report=False)
    rows = _read_manifest(tmp_path)['rows']
    assert isinstance(rows, list)
    assert 'solver_report' not in {row['artifact_kind'] for row in rows}
    assert 'rdp_display_summary' not in {row['artifact_kind'] for row in rows}

def test_raises_for_missing_required_meta(tmp_path: Path) -> None:
    (tmp_path / 'config').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'config' / 'logging.json').write_text('{}\n', encoding='utf-8')
    with pytest.raises(FileNotFoundError, match='META.json'):
        rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path)

def test_raises_for_missing_required_logging_snapshot(tmp_path: Path) -> None:
    (tmp_path / 'META.json').write_text('{}\n', encoding='utf-8')
    with pytest.raises(FileNotFoundError, match='config/logging.json'):
        rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path)

def test_raises_when_solver_report_requested_but_missing(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    with pytest.raises(FileNotFoundError, match='artifacts/solver_report.json'):
        rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path, include_solver_report=True)

def test_does_not_include_logs_or_trace(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    (tmp_path / 'logs').mkdir()
    (tmp_path / 'trace').mkdir()
    (tmp_path / 'logs' / 'app.jsonl').write_text('{}\n', encoding='utf-8')
    (tmp_path / 'trace' / 'sample.txt').write_text('trace\n', encoding='utf-8')
    rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path)
    rows = _read_manifest(tmp_path)['rows']
    assert isinstance(rows, list)
    relpaths = {row['relpath'] for row in rows}
    assert 'logs/app.jsonl' not in relpaths
    assert 'trace/sample.txt' not in relpaths

def test_does_not_include_hashes_sizes_mtimes_or_absolute_paths(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    (tmp_path / 'artifacts' / 'solver_report.json').write_text('{}\n', encoding='utf-8')
    (tmp_path / 'artifacts' / 'rdp_display_summary.json').write_text('{}\n', encoding='utf-8')
    rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path)
    rows = _read_manifest(tmp_path)['rows']
    assert isinstance(rows, list)
    forbidden = {'sha256', 'byte_size', 'mtime', 'absolute_path', 'canonical_json'}
    for row in rows:
        assert not forbidden.intersection(row)
        assert not os.path.isabs(row['relpath'])

def test_manifest_does_not_list_itself(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path)
    rows = _read_manifest(tmp_path)['rows']
    assert isinstance(rows, list)
    assert rdp.api.run_artifact_manifest.MANIFEST_RELPATH not in {row['relpath'] for row in rows}

def test_rows_use_classification_strings(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path)
    rows = _read_manifest(tmp_path)['rows']
    assert isinstance(rows, list)
    for row in rows:
        assert row['portable_classification'] == 'candidate'
        assert row['export_classification'] == 'candidate'
        assert 'portable_candidate' not in row
        assert 'export_candidate' not in row

def test_rejects_duplicate_relpaths() -> None:
    row = rdp.api.run_artifact_manifest.RunArtifactManifestRow(relpath='META.json', artifact_kind='run_meta', required=True, present=True, portable_classification='candidate', export_classification='candidate')
    duplicate = rdp.api.run_artifact_manifest.RunArtifactManifestRow(relpath='META.json', artifact_kind='logging_config', required=True, present=True, portable_classification='candidate', export_classification='candidate')
    with pytest.raises(ValueError, match='duplicate manifest relpath'):
        rdp.api.run_artifact_manifest._validate_unique_rows([row, duplicate])

def test_rejects_duplicate_artifact_kinds() -> None:
    row = rdp.api.run_artifact_manifest.RunArtifactManifestRow(relpath='META.json', artifact_kind='run_meta', required=True, present=True, portable_classification='candidate', export_classification='candidate')
    duplicate = rdp.api.run_artifact_manifest.RunArtifactManifestRow(relpath='config/logging.json', artifact_kind='run_meta', required=True, present=True, portable_classification='candidate', export_classification='candidate')
    with pytest.raises(ValueError, match='duplicate manifest artifact_kind'):
        rdp.api.run_artifact_manifest._validate_unique_rows([row, duplicate])

@pytest.mark.parametrize('bad_relpath', ['', '/absolute.json', '../outside.json', 'artifacts\\bad.json'])
def test_rejects_invalid_row_relpaths(bad_relpath: str) -> None:
    with pytest.raises(ValueError):
        rdp.api.run_artifact_manifest.RunArtifactManifestRow(relpath=bad_relpath, artifact_kind='run_meta', required=True, present=True, portable_classification='candidate', export_classification='candidate')

def test_rejects_non_path_run_dir(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    with pytest.raises(TypeError, match='run_dir must be a Path'):
        rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=str(tmp_path))

def test_rejects_non_bool_include_solver_report(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    with pytest.raises(TypeError, match='include_solver_report must be a bool'):
        rdp.api.run_artifact_manifest.write_run_artifacts_manifest(run_dir=tmp_path, include_solver_report=1)
