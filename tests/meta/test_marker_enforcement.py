"""Meta tests ensuring every module participates in the tiered marker scheme."""

from __future__ import annotations
import re
from pathlib import Path
import pytest

pytestmark = pytest.mark.tier_a
ALLOWED_MARKERS = {"tier_a", "tier_b", "long", "legacy", "smoke", "cuda", "guardrails"}
TARGET_DIRS = {"ciphers", "solvers", "tutorials", "smoke", "telemetry", "meta"}


def test_test_modules_declare_allowed_markers():
    missing: list[str] = []
    bad: list[str] = []
    for path in Path("tests").rglob("test_*.py"):
        relative_parts = path.relative_to("tests").parts
        if not relative_parts:
            continue
        if relative_parts[0] not in TARGET_DIRS:
            continue
        if "_helpers" in path.parts or "pytest_cache" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "pytestmark" not in text:
            missing.append(str(path))
            continue
        markers = set(re.findall("pytest\\.mark\\.([A-Za-z0-9_]+)", text))
        if not markers & ALLOWED_MARKERS:
            bad.append(str(path))
    assert not missing, f"Modules missing pytestmark declaration: {missing}"
    assert not bad, f"Modules use pytestmark without allowed markers: {bad}"
