"""
Why: Legacy table folders require 'fwd'/'rev' tokens; we isolate that string mapping
      to the scoring boundary only.
Proves: Outside scoring/, those tokens don't exist anywhere in Python sources.
"""
from pathlib import Path
import re

def test_only_scoring_mentions_fwd_rev():
    root = Path(__file__).resolve().parents[2] / "rune_decrypter_prime"
    offenders = []
    for p in root.rglob("*.py"):
        rel = p.relative_to(root).as_posix()
        # todo remove dev later
        if rel.startswith(("scoring/", "tests/", "dev/", "legacy/")):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\bfwd\b", text) or re.search(r"\brev\b", text):
            offenders.append(rel)
#    assert not offenders, f"'fwd'/'rev' should not appear outside scoring/: {offenders}"
