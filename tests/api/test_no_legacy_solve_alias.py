from __future__ import annotations

import json
from pathlib import Path

from rune_decrypter_prime.api.run import RunAPI


REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER = REPO_ROOT / "docs" / "release_contracts" / "v1" / "v1_cleanup_deprecation_ledger.json"


def test_v1_retained_solve_alias_is_not_a_second_core_api() -> None:
    assert RunAPI.__dict__["solve"] is RunAPI.__dict__["run"]


def test_solve_alias_cleanup_boundary_is_documented_in_ledger() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in ledger["entries"]}
    entry = entries["api.run.solve_alias"]

    assert entry["status"] == "deprecate_only"
    assert "RunAPI.run" in entry["replacement"]
    assert "breaking API cleanup" in entry["reason"]
