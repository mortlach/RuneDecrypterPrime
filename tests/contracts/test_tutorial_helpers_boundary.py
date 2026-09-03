from __future__ import annotations
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / 'src' / 'rdp'
FORBIDDEN_IMPORT_SNIPPETS = (
    'from tests',
    'from tutorials',
    'from tools',
    'from cipher_development',
    'from solving',
    'import tests',
    'import tutorials',
    'import tools',
    'import cipher_development',
    'import solving',
)

def test_tutorial_oracle_helpers_do_not_leak_into_strict_runtime_modules() -> None:
    offenders: list[str] = []
    for path in SRC_ROOT.rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        if any((snippet in text for snippet in FORBIDDEN_IMPORT_SNIPPETS)):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, 'tutorial/session oracle helpers must stay outside strict runtime modules: ' + repr(offenders)
