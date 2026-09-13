"""Run the learner's copyable code, including its cross-page result inspection."""
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
LEARN = ROOT / 'docs/learn'


def test_learning_examples_execute_exactly_as_documented():
    pages = ['01_apply_a_known_key.md', '02_search_a_key.md', '03_change_one_thing.md',
             '04_use_liber_primus.md', '05_read_the_result.md']
    blocks = []
    for name in pages:
        text = (LEARN / name).read_text(encoding='utf-8')
        assert len(re.findall(r'^```', text, re.MULTILINE)) % 2 == 0, name
        examples = re.findall(r'^```python\s*\n(.*?)^```\s*$', text, re.MULTILINE | re.DOTALL)
        assert examples, name
        for example in examples:
            compile(example, name, 'exec')
        blocks.extend(examples)
    code = '\n\n'.join(blocks)
    completed = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code],
                               cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
                               timeout=180)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_learning_track_has_split_glossaries_and_canonical_named_source_route():
    learner_glossary = (LEARN / '00_words_used_here.md').read_text(encoding='utf-8')
    reference_glossary = (LEARN.parent / 'reference/glossary.md').read_text(
        encoding='utf-8'
    )
    for term in (
        'Beam search', 'Candidate', 'Width', 'Round', 'Seed', 'Search budget',
        'Plateau', 'Score', 'Scorer', 'Language model', 'WLI', 'CipherSpec',
        'KeySpec', 'SolverSpec', 'RunSpec', 'RunResult', 'Stop reason',
        'Source label', 'load_source', 'load_plaintext',
    ):
        assert term in learner_glossary
    for term in (
        'RuneInputFormat', 'RuneIndices', 'SourceReferenceInput', 'SourceData',
        'Source resolver', 'ConcreteKey', 'InitialKeys', 'KeyOps',
        'ProblemInput', 'Text permutation', 'score_many', 'ScoringConfig',
        'Objective', 'Character lane', 'WLI lane', 'ScorerReport',
        'SolverReport', 'RunStatus', 'Stop category', 'Telemetry', 'Oracle',
        'Artifact', 'LoggingConfig', 'InterruptorConfig', 'Asset profile',
        'CI-light', 'WordLengthPolicy', 'ComputeDevice', 'CUDA',
    ):
        assert term in reference_glossary
    assert '../reference/glossary.md' in learner_glossary
    assert '../learn/00_words_used_here.md' in reference_glossary
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        assert f'[{letter.upper()}](#{letter})' in reference_glossary
        assert f'## {letter.upper()}' in reference_glossary
    for page in LEARN.glob('*.md'):
        if page.name != '00_words_used_here.md':
            assert '00_words_used_here.md' in page.read_text(encoding='utf-8'), page
    source_page = (LEARN / '04_use_liber_primus.md').read_text(encoding='utf-8')
    assert 'api.liber_primus.source(' in source_page
    assert 'payload_from_label' not in source_page
    assert 'RuneInput' not in source_page


def test_public_learning_and_solve_material_uses_interruptor_spelling():
    public_roots = [ROOT / 'solving', ROOT / 'tutorials' / 'v1']
    for root in public_roots:
        for path in root.rglob('*'):
            if path.suffix not in {'.py', '.md'}:
                continue
            assert 'interrupter' not in path.read_text(encoding='utf-8').lower(), path
