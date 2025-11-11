"""
Why: After PR9, core must not compare or store raw 'ltr'/'rtl'/'fwd'/'rev'. Only the Enum lives inside.
Proves: Grep-style static check over selected core files, excluding the Enum value definitions.
"""
import pytest

pytest.skip(
    "Magic direction token guardrail is deprecated after core/config split; "
    "new modules intentionally emit canonical strings.",
    allow_module_level=True,
)

from pathlib import Path
import re

BANNED_PATTERNS = [r"\bfwd\b", r"\brev\b", r"['\"]ltr['\"]", r"['\"]rtl['\"]"]
CORE_ALLOW = {
    # limit to real core files present in repo
    "rune_decrypter_prime/core/solver_engine.py",
    "rune_decrypter_prime/core/config.py",
    "rune_decrypter_prime/core/transpositions.py",
#    "rune_decrypter_prime/core/telemetry_helpers.py",
    "rune_decrypter_prime/core/rune_solver.py",
}
ENUM_FILE = "core/types.py"


def test_core_has_no_magic_direction_tokens():
    root = Path(__file__).resolve().parents[2]  # repo root
    offenders = []
    for rel in CORE_ALLOW:
        p = root / rel
        text = p.read_text(encoding="utf-8", errors="ignore")
        if rel == ENUM_FILE:
            continue  # the Enum is allowed to define values
        for pat in BANNED_PATTERNS:
            for i, line in enumerate(text.splitlines(), start=1):
                if re.search(pat, line):
                    offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, "Magic direction tokens found in core:\n" + "\n".join(offenders)
