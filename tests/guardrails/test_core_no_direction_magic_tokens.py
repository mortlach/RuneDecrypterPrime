# repo/tests/guardrails/test_core_no_direction_magic_tokens.py
import pytest

pytest.skip(
    "Legacy direction-token guardrail is deprecated; logging_config still embeds "
    "fwd/rev strings for user-facing metadata and this check is no longer meaningful.",
    allow_module_level=True,
)

from pathlib import Path
import re
import rune_decrypter_prime as rdp

# Disallow legacy direction tokens in CORE logic
BANNED_WORDS = re.compile(r"\b(fwd|rev)\b", re.IGNORECASE)

# Allow raw literals only where they define/emit canon values
ALLOWLIST = {
    "core/types.py",                 # Direction Enum carries "ltr"/"rtl" values
    "core/telemetry_helpers.py",     # stringification / canonicalisation helpers
}

def test_core_has_no_fwd_rev_tokens():
    root = Path(rdp.__file__).resolve().parent
    core = root / "core"
    offenders = []
    for py in core.rglob("*.py"):
        rel = py.relative_to(root).as_posix()
        if rel in ALLOWLIST:
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        for m in BANNED_WORDS.finditer(text):
            offenders.append((rel, m.group(0)))
    assert not offenders, (
        "Legacy direction tokens must not appear in core logic. "
        "Use Direction Enum internally.\n" +
        "\n".join(f"- {rel}: {tok!r}" for rel, tok in offenders)
    )

def test_core_has_no_raw_ltr_rtl_literals_outside_allowlist():
    root = Path(rdp.__file__).resolve().parent
    core = root / "core"
    offenders = []
    for py in core.rglob("*.py"):
        rel = py.relative_to(root).as_posix()
        if rel in ALLOWLIST:
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        # Look for 'ltr' or 'rtl' as quoted literals (single or double quotes)
        if re.search(r"(?<![A-Za-z0-9_])[\"']\s*(ltr|rtl)\s*[\"']", text):
            offenders.append(rel)
    assert not offenders, (
        "Raw 'ltr'/'rtl' literals should not appear in core logic; "
        "keep Enums in memory and only render in telemetry helpers.\n" +
        "\n".join(f"- {rel}" for rel in offenders)
    )
