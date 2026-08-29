"""
Why: Tests should use the supported api/ surface, not legacy UI packages.
Proves: No test file imports from the legacy UI module family.
"""
from pathlib import Path
import re

def test_no_tests_import_legacy_ui():
    root = Path(__file__).resolve().parents[1]
    legacy_ui_token = 'patche' + '_old_ui'
    offenders = []
    for p in root.rglob('*.py'):
        text = p.read_text(encoding='utf-8', errors='ignore')
        if re.search(f'^\\s*from\\s+.*\\b{legacy_ui_token}\\b\\.', text, flags=re.M):
            offenders.append(p.name)
        if re.search(f'^\\s*import\\s+.*\\b{legacy_ui_token}\\b(\\.|$)', text, flags=re.M):
            offenders.append(p.name)
    assert not offenders, 'Replace legacy UI imports with api.* in these tests: ' + ', '.join(sorted(set(offenders)))
