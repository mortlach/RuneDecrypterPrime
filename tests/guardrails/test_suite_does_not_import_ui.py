"""
Why: We are migrating tests to the new api/ surface so we can eventually delete patche_old_ui/.
Proves: No test file imports from the legacy patche_old_ui.* modules.
"""
from pathlib import Path
import re

def test_no_tests_import_legacy_ui():
    root = Path(__file__).resolve().parents[1]  # tests/
    offenders = []
    for p in root.rglob("*.py"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^\s*from\s+.*\bpatche_old_ui\b\.", text, flags=re.M):
            offenders.append(p.name)
        if re.search(r"^\s*import\s+.*\bpatche_old_ui\b(\.|$)", text, flags=re.M):
            offenders.append(p.name)
    assert not offenders, "Replace patche_old_ui.* imports with api.* in these tests: " + ", ".join(sorted(set(offenders)))
