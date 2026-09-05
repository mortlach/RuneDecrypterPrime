from __future__ import annotations
import hashlib
import importlib
import inspect
import re
from dataclasses import fields
from pathlib import Path

import rdp.api.run_artifact_manifest
from rdp import api
from rdp.core.config.logging_config import LoggingConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
V1_DOCS = REPO_ROOT / 'v1_docs'
PUBLIC_API_ALLOWLIST = V1_DOCS / 'reference' / 'public_api_allowlist.md'
PUBLIC_API_SNAPSHOT_SHA256 = '13ab2964ddc40706b0be4b01dac496e6d30005ba98a8117ae1c43bfac19c219a'
CODER_MODULE_MAP = V1_DOCS / 'coder' / 'module_map.md'
CODER_README = V1_DOCS / 'coder' / 'README.md'
CODER_PUBLIC_API = V1_DOCS / 'coder' / 'public_api.md'
CODER_RUN_FLOW = V1_DOCS / 'coder' / 'run_flow.md'
CODER_CONFIG_OBJECTS = V1_DOCS / 'coder' / 'config_objects.md'
CODER_TELEMETRY_AND_REPORTS = V1_DOCS / 'coder' / 'telemetry_and_reports.md'
CODER_EXTENSION_POINTS = V1_DOCS / 'coder' / 'extension_points.md'
HOWTO_PAGES = [V1_DOCS / 'howto' / 'add_cipher.md', V1_DOCS / 'howto' / 'add_solver.md', V1_DOCS / 'howto' / 'add_scorer_lane.md']
CODER_PIPELINE_PAGES = [V1_DOCS / 'coder' / 'cipher_pipeline.md', V1_DOCS / 'coder' / 'key_pipeline.md', V1_DOCS / 'coder' / 'solver_pipeline.md', V1_DOCS / 'coder' / 'scoring_pipeline.md']

def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')

def _import_paths_from_allowlist() -> list[str]:
    paths: list[str] = []
    for line in _read(PUBLIC_API_ALLOWLIST).splitlines():
        match = re.match('^\\| `([^`]+)` \\|', line)
        if match:
            import_path = match.group(1)
            if import_path.startswith('rdp.'):
                paths.append(import_path)
    return paths

def _allowlist_rows() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in _read(PUBLIC_API_ALLOWLIST).splitlines():
        match = re.match('^\\| `([^`]+)` \\| ([^|]+) \\| ([^|]+) \\|$', line)
        if match and match.group(1) != 'Import path':
            rows.append((match.group(1).strip(), match.group(2).strip(), match.group(3).strip()))
    return rows

def _markdown_links(text: str) -> list[str]:
    return re.findall('\\[[^\\]]+\\]\\(([^)]+)\\)', text)

def test_public_api_allowlist_imports() -> None:
    import_paths = _import_paths_from_allowlist()
    assert import_paths, 'public API allowlist must contain import paths'
    for import_path in import_paths:
        module_name, attr_name = import_path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        assert hasattr(module, attr_name), import_path

def test_public_api_allowlist_labels_are_controlled() -> None:
    allowed = {'Public V1 surface', 'Semi-stable contributor surface', 'Internal helper', 'Test-only helper', 'Legacy / transitional'}
    rows = _allowlist_rows()
    assert rows, 'public API allowlist must contain rows'
    for _import_path, stability, _notes in rows:
        assert stability in allowed

def test_public_api_allowlist_has_no_duplicates() -> None:
    import_paths = [row[0] for row in _allowlist_rows()]
    assert len(import_paths) == len(set(import_paths))


def test_public_api_allowlist_is_the_exact_five_namespace_contract() -> None:
    expected = {
        f"{prefix}.{name}"
        for prefix, namespace in (
            ("rdp.api", api),
            ("rdp.api.advanced", api.advanced),
            ("rdp.api.display", api.display),
            ("rdp.api.liber_primus", api.liber_primus),
            ("rdp.api.experimental", api.experimental),
        )
        for name in namespace.__all__
    }
    paths = {row[0] for row in _allowlist_rows()}
    assert len(paths) == 141
    assert len(api.__all__) == 32
    assert paths == expected


def test_public_api_allowlist_preserves_the_accepted_crlf_snapshot() -> None:
    canonical = ('\r\n'.join(_read(PUBLIC_API_ALLOWLIST).splitlines()) + '\r\n').encode(
        'utf-8'
    )
    assert hashlib.sha256(canonical).hexdigest() == PUBLIC_API_SNAPSHOT_SHA256


def test_module_map_source_paths_exist() -> None:
    text = _read(CODER_MODULE_MAP)
    source_paths = sorted({item for item in re.findall('`((?:src|tests|tutorials)/[^`]+)`', text) if not item.endswith('.md')})
    assert source_paths, 'module map must name source paths'
    for relpath in source_paths:
        assert (REPO_ROOT / relpath).exists(), relpath

def test_module_map_covers_top_level_source_packages() -> None:
    text = _read(CODER_MODULE_MAP)
    expected_paths = {
        "src/rdp/backends/",
        "src/rdp/core/",
        "src/rdp/data/",
        "src/rdp/io/",
        "src/rdp/telemetry/",
        "src/rdp/ciphers/",
        "src/rdp/keyops/",
        "src/rdp/scoring/",
        "src/rdp/solvers/",
        "src/rdp/api/",
        "tutorials/v1/",
        "cipher_development/",
        "solving/",
        "tools/robustness/fixtures/",
        "tests/",
    }
    for relpath in sorted(expected_paths):
        assert f'`{relpath}`' in text

def test_runspec_fields_are_documented() -> None:
    text = _read(CODER_PUBLIC_API)
    documented = set(re.findall('\\| `([^`]+)` \\|', text))
    actual = {field.name for field in fields(api.RunSpec)}
    assert actual <= documented

def test_public_config_object_fields_are_documented() -> None:
    text = _read(CODER_CONFIG_OBJECTS)
    classes = [api.RawTextInput, api.RuneIndexInput, api.SourceReferenceInput, api.RunSpec, api.CipherSpec, api.KeySpec, api.SolverSpec, LoggingConfig]
    for cls in classes:
        for field in fields(cls):
            assert f'`{field.name}`' in text, f'{cls.__name__}.{field.name}'

def test_targeted_public_contract_docstrings_exist() -> None:
    expected_terms = {api.RawTextInput: ['non-empty string', 'input source'], api.RuneIndexInput: ['ct_idx', 'wli', '0..28'], api.SourceReferenceInput: ['source kind', 'asset', 'JSON primitive'], api.RunSpec: ['cipher spec', 'solver spec', 'routing'], rdp.api.run_artifact_manifest.RunArtifactManifestRow: ['known V1 run artifact', 'run-relative'], rdp.api.run_artifact_manifest.write_run_artifacts_manifest: ['META.json', 'config/logging.json', 'Returns']}
    for obj, terms in expected_terms.items():
        doc = inspect.getdoc(obj)
        assert doc, getattr(obj, '__name__', repr(obj))
        for term in terms:
            assert term in doc, f"{getattr(obj, '__name__', repr(obj))}: {term}"

def test_public_config_object_enums_are_documented() -> None:
    text = _read(CODER_CONFIG_OBJECTS)
    for enum_member in [
        api.TextDirection.LEFT_TO_RIGHT,
        api.TextDirection.RIGHT_TO_LEFT,
        api.ComputeDevice.CPU,
        api.ComputeDevice.CUDA,
    ]:
        assert f"`{enum_member.__class__.__name__}.{enum_member.name}`" in text
        assert f'`"{enum_member.value}"`' in text

def test_run_flow_documents_core_runtime_path() -> None:
    text = _read(CODER_RUN_FLOW)
    required_terms = {'api.run', 'RunSpec', 'CipherSpec', 'KeySpec', 'SolverSpec', 'ProblemSpec', 'ProblemInstance', 'DecryptionProblem', 'EngineConfig', 'SolverReport'}
    for term in sorted(required_terms):
        assert term in text

def test_pipeline_pages_follow_required_pattern() -> None:
    required_sections = ['## Purpose', '## What This Layer Owns', '## What This Layer Must Not Own', '## Main Objects', '## How It Fits Into A Run', '## Contracts And Invariants', '## Determinism Notes', '## Report And Telemetry Outputs', '## Extension Checklist', '## What Not To Rely On']
    for path in CODER_PIPELINE_PAGES:
        text = _read(path)
        for section in required_sections:
            assert section in text, f'{path.name}: {section}'

def test_scoring_pipeline_documents_signal_effects() -> None:
    text = _read(V1_DOCS / 'coder' / 'scoring_pipeline.md')
    required_terms = {'ranking', 'stopping', 'tie-breaks', 'candidate selection', 'Report-only'}
    for term in sorted(required_terms):
        assert term in text

def test_telemetry_and_reports_documents_public_evidence_surfaces() -> None:
    text = _read(CODER_TELEMETRY_AND_REPORTS)
    required_terms = {'RunResult', 'SolverReport', 'ScorerReport', 'RdpDisplaySummary', 'RunArtifactManifestRow', 'report_contract', 'oracle_use', 'truth_data_policy', 'artifacts/solver_report.json', 'artifacts/rdp_display_summary.json', 'artifacts/run_artifacts_manifest.json', 'META.json', 'config/logging.json'}
    for term in sorted(required_terms):
        assert term in text

def test_telemetry_and_reports_documents_report_only_boundary() -> None:
    text = _read(CODER_TELEMETRY_AND_REPORTS)
    required_terms = {'ranking', 'stopping', 'tie-break', 'candidate selection', 'Report-only', 'oracle', 'truth data', 'Telemetry is best-effort'}
    for term in sorted(required_terms):
        assert term in text

def test_extension_points_documents_supported_contributor_paths() -> None:
    text = _read(CODER_EXTENSION_POINTS)
    required_terms = {'Cipher', 'KeyOps family', 'Solver', 'Scorer runtime', 'Scorer lane', 'Report/artifact', 'Tutorial', 'ranking', 'stopping', 'tie-breaks', 'candidate selection'}
    for term in sorted(required_terms):
        assert term in text

def test_howto_pages_have_contract_shape() -> None:
    required_sections = {'## Goal', '## Steps', '## Tests', '## Do Not Do'}
    for path in HOWTO_PAGES:
        text = _read(path)
        for section in sorted(required_sections):
            assert section in text, f'{path.name}: {section}'

def test_howto_pages_name_core_owner_paths() -> None:
    expected = {
        "add_cipher.md": [
            "src/rdp/ciphers/",
            "src/rdp/ciphers/cipher_runtime_registry.py",
            "src/rdp/api/experimental.py",
        ],
        "add_solver.md": [
            "src/rdp/solvers/",
            "src/rdp/core/types.py",
            "src/rdp/core/engine/engine.py",
        ],
        "add_scorer_lane.md": [
            "src/rdp/core/component_contracts.py",
            "src/rdp/core/config/scoring.py",
            "src/rdp/scoring/scorer_report_builder.py",
        ],
    }
    for path in HOWTO_PAGES:
        text = _read(path)
        for relpath in expected[path.name]:
            assert relpath in text, f'{path.name}: {relpath}'
            assert (REPO_ROOT / relpath).exists(), relpath

def test_no_generated_html_under_v1_docs() -> None:
    generated_suffixes = {'.html', '.doctree'}
    generated_dirs = {'_build', 'html', 'doctrees', 'generated'}
    offenders: list[str] = []
    for path in V1_DOCS.rglob('*'):
        rel = path.relative_to(V1_DOCS)
        if path.is_dir() and path.name in generated_dirs:
            offenders.append(rel.as_posix())
        elif path.is_file() and path.suffix.lower() in generated_suffixes:
            offenders.append(rel.as_posix())
    assert offenders == []

def test_no_absolute_local_paths_in_new_coder_or_howto_docs() -> None:
    roots = [V1_DOCS / 'coder', V1_DOCS / 'howto']
    offenders: list[str] = []
    drive_path = re.compile('[A-Za-z]:[\\\\/]')
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('*.md'):
            text = _read(path)
            if drive_path.search(text):
                offenders.append(path.relative_to(REPO_ROOT).as_posix())
    assert offenders == []

def test_no_blocked_material_dirs_under_v1_docs() -> None:
    blocked_names = {'planning', 'output', 'assets_packed', 'patch_bundles', 'handoff', 'cache', 'logs', 'review_zips'}
    offenders = [path.relative_to(V1_DOCS).as_posix() for path in V1_DOCS.rglob('*') if path.is_dir() and path.name in blocked_names]
    assert offenders == []

def test_v1_docs_readme_draft_pages_exist() -> None:
    text = _read(V1_DOCS / 'README.md')
    entries = re.findall('^- `([^`]+\\.md)`$', text, flags=re.MULTILINE)
    assert entries, 'README draft pages list must contain markdown files'
    for relpath in entries:
        assert (V1_DOCS / relpath).is_file(), relpath

def test_coder_readme_page_rows_exist() -> None:
    text = _read(CODER_README)
    entries = re.findall('^\\| `([^`]+\\.md)` \\|', text, flags=re.MULTILINE)
    assert entries, 'coder README must list coder pages'
    for relpath in entries:
        assert (CODER_README.parent / relpath).is_file(), relpath

def test_new_coder_and_howto_markdown_links_resolve() -> None:
    roots = [V1_DOCS / 'coder', V1_DOCS / 'howto']
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob('*.md'):
            for href in _markdown_links(_read(path)):
                if '://' in href or href.startswith('#'):
                    continue
                target_text = href.split('#', 1)[0]
                if not target_text:
                    continue
                target = (path.parent / target_text).resolve()
                if not target.is_file():
                    offenders.append(f'{path.relative_to(REPO_ROOT).as_posix()} -> {href}')
    assert offenders == []
