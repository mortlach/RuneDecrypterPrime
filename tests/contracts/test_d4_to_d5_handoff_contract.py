from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HANDOFF = REPO_ROOT / "docs" / "release_contracts" / "v1" / "d4_summary_for_d5.md"


def test_d4_to_d5_handoff_names_real_d4_lessons() -> None:
    assert HANDOFF.exists(), f"missing D4 to D5 handoff note: {HANDOFF}"
    text = HANDOFF.read_text(encoding="utf-8")

    for phrase in (
        "D4 summary and D5 handoff note",
        "UnifiedRuneScorer",
        "Dict-like scorer params are rejected",
        "Run, block, or report",
        "Partition work into meaningful chunks",
        "New tests should prevent old bad behaviours from returning",
        "stale D3 wording",
    ):
        assert phrase in text

    assert "D3 is now ready for external review" not in text
