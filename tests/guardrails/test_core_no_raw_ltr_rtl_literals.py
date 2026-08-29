from pathlib import Path
import re
import rune_decrypter_prime as rdp

LITERAL = re.compile("(?<![A-Za-z0-9_])([\\'\\\"])\\\\s*(ltr|rtl)\\\\s*\\\\1")
ALLOWLIST = {"core/types.py", "core/telemetry_helpers.py"}


def test_core_has_no_raw_ltr_rtl_literals_outside_allowlist():
    root = Path(rdp.__file__).resolve().parent
    core = root / "core"
    offenders = []
    for py in core.rglob("*.py"):
        rel = py.relative_to(root).as_posix()
        text = py.read_text(encoding="utf-8", errors="ignore")
        if rel in ALLOWLIST:
            continue
        for m in LITERAL.finditer(text):
            offenders.append((rel, m.group(0)))
    assert not offenders, (
        "Raw 'ltr'/'rtl' literals should not appear in core logic. Use Direction Enum internally; only Enum and telemetry code may render strings.\n"
        + "\n".join((f"- {rel}: {tok}" for rel, tok in offenders))
    )
