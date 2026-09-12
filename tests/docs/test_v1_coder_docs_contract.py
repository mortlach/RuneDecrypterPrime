from __future__ import annotations
import inspect
import re
from dataclasses import fields
from pathlib import Path

import rdp.api.run_artifact_manifest
from rdp import api
from rdp.data.runeglish import Runeglish

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / 'docs'

def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')

def test_targeted_public_contract_docstrings_exist() -> None:
    expected_terms = {api.score: ['Score one', 'probability'], api.score_many: ['input order', 'empty'], api.RuneInput: ['indices', 'RuneLatin', 'English', 'word'], api.SourceReferenceInput: ['source kind', 'asset', 'JSON primitive'], api.RunSpec: ['cipher spec', 'solver spec', 'routing'], rdp.api.run_artifact_manifest.RunArtifactManifestRow: ['known V1 run artifact', 'run-relative'], rdp.api.run_artifact_manifest.write_run_artifacts_manifest: ['META.json', 'config/logging.json', 'Returns']}
    for obj, terms in expected_terms.items():
        doc = inspect.getdoc(obj)
        assert doc, getattr(obj, '__name__', repr(obj))
        for term in terms:
            assert term in doc, f"{getattr(obj, '__name__', repr(obj))}: {term}"

def test_public_configuration_fields_have_current_parameter_owners() -> None:
    owners = {
        api.RuneInput: 'inputs.md',
        api.SourceReferenceInput: 'inputs.md', api.RunSpec: 'run_spec.md',
        api.CipherSpec: 'ciphers.md', api.KeySpec: 'keys.md',
        api.SolverSpec: 'solvers.md', api.LoggingConfig: 'logging.md',
        api.ScoringConfig: 'scoring.md',
    }
    for cls, owner in owners.items():
        text = _read(DOCS / 'reference' / 'parameters' / owner)
        for field in fields(cls):
            if field.name.startswith("_"):
                continue  # Private storage is not a public constructor parameter.
            assert f'`{field.name}`' in text, f'{cls.__name__}.{field.name}: {owner}'


def test_run_result_representation_names_match_reference() -> None:
    names = (
        'plaintext_indices',
        'word_length_information',
        'plaintext_runes',
        'plaintext_rune_latin',
        'plaintext_reading_rune_latin',
    )
    result_fields = tuple(field.name for field in fields(api.RunResult))
    assert result_fields[:5] == names

    reference = _read(DOCS / 'reference' / 'run_result.md')
    for name in names:
        assert f'`{name}`' in reference

    public_examples = [
        REPO_ROOT / 'README.md',
        *DOCS.rglob('*.md'),
        *(REPO_ROOT / 'tutorials' / 'v1' / 'getting_started').glob('*.py'),
        *(REPO_ROOT / 'tutorials' / 'v1' / 'examples').glob('*.py'),
        *(REPO_ROOT / 'solving' / 'getting_started').glob('*.py'),
        *(REPO_ROOT / 'solving' / 'lp_getting_started').glob('*.py'),
    ]
    stale_access = re.compile(
        r'\b(?:result|solution|winner\.result)\.'
        r'(?:plaintext|plaintext_text|plaintext_idx|plaintext_latin)\b'
    )
    for path in public_examples:
        assert not stale_access.search(_read(path)), path


def test_removed_input_classes_do_not_appear_in_public_docs_or_examples() -> None:
    public_files = [
        REPO_ROOT / 'README.md',
        *DOCS.rglob('*.md'),
        *(REPO_ROOT / 'tutorials').rglob('*.py'),
        *(REPO_ROOT / 'tutorials').rglob('*.md'),
        *(REPO_ROOT / 'solving').rglob('*.py'),
        *(REPO_ROOT / 'solving').rglob('*.md'),
    ]
    removed = ('RawTextInput', 'RuneIndexInput')
    for path in public_files:
        text = _read(path)
        for name in removed:
            assert name not in text, (path, name)


def test_result_fields_and_rune_input_formats_are_documented_directly() -> None:
    result_reference = _read(DOCS / 'reference' / 'run_result.md')
    for name in (
        'plaintext_indices',
        'word_length_information',
        'plaintext_runes',
        'plaintext_rune_latin',
        'plaintext_reading_rune_latin',
    ):
        assert f'`{name}`' in result_reference

    input_reference = _read(DOCS / 'reference' / 'parameters' / 'inputs.md')
    for value in api.RuneInputFormat:
        assert f'`{value.name}`' in input_reference


def test_runelatin_rendering_and_documented_defaults_match_public_api() -> None:
    assert Runeglish.to_delimited_rune_latin((16, 8, 18), ((0, 3), (1, 3), (2, 3))) == 'T·H·E'

    solver_reference = _read(DOCS / 'reference' / 'parameters' / 'solvers.md')
    beam_signature = inspect.signature(api.SolverSpec.beam_search)
    assert beam_signature.parameters['width'].default == 64
    assert beam_signature.parameters['rounds'].default is None
    assert re.search(r'\| `width` \|[^\n]+\| `64` \|', solver_reference)
    assert re.search(r'\| `rounds` \|[^\n]+\| `None` \(automatic\) \|', solver_reference)

    run_spec_reference = _read(DOCS / 'reference' / 'parameters' / 'run_spec.md')
    assert inspect.signature(api.RunSpec).parameters['text_direction'].default is api.TextDirection.LTR
    assert re.search(r'\| `text_direction` \|[^\n]+\| `LTR` \|', run_spec_reference)


def test_one_public_documentation_tree_without_generated_or_private_material() -> None:
    assert not (REPO_ROOT / 'v1_docs').exists()
    blocked = {'planning', 'output', 'assets_packed', 'handoff', 'logs', 'preview_site'}
    for path in DOCS.rglob('*'):
        assert path.suffix not in {'.html', '.doctree'}
        assert path.name not in blocked


def test_current_public_markdown_links_resolve() -> None:
    pages = [REPO_ROOT / 'README.md', REPO_ROOT / 'CONTRIBUTING.md', *DOCS.rglob('*.md')]
    windows_drive = re.compile(r'(?<![A-Za-z])[A-Za-z]:[\\/]')
    for page in pages:
        text = _read(page)
        assert not windows_drive.search(text), page
        for href in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
            if '://' in href or href.startswith('#'):
                continue
            target = href.split('#', 1)[0]
            if target:
                assert (page.parent / target).resolve().exists(), (page, href)
