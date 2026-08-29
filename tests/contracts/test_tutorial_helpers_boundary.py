from __future__ import annotations
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / 'src' / 'rune_decrypter_prime'
STRICT_RUNTIME_DIRS = (SRC_ROOT / 'api', SRC_ROOT / 'ciphers', SRC_ROOT / 'core', SRC_ROOT / 'scoring', SRC_ROOT / 'solvers')
FORBIDDEN_IMPORT_SNIPPETS = ('utils.tutorial_benchmark', 'utils.tutorial_reference', 'utils.tutorial_session_report', 'utils.tutorial_report')
ALLOWED_FILES = {SRC_ROOT / 'utils' / 'scheduled_stream_lookup_tutorial_utils.py', SRC_ROOT / 'utils' / 'tutorial_benchmark.py', SRC_ROOT / 'utils' / 'tutorial_reference.py', SRC_ROOT / 'utils' / 'tutorial_report.py', SRC_ROOT / 'utils' / 'tutorial_session_report.py'}

def test_tutorial_oracle_helpers_do_not_leak_into_strict_runtime_modules() -> None:
    offenders: list[str] = []
    for root in STRICT_RUNTIME_DIRS:
        if not root.exists():
            continue
        for path in root.rglob('*.py'):
            if path in ALLOWED_FILES:
                continue
            text = path.read_text(encoding='utf-8')
            if any((snippet in text for snippet in FORBIDDEN_IMPORT_SNIPPETS)):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, 'tutorial/session oracle helpers must stay outside strict runtime modules: ' + repr(offenders)
