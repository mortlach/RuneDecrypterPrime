from __future__ import annotations

import json
from pathlib import Path

from rune_decrypter_prime.api.run import RunAPI


REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER = REPO_ROOT / "docs" / "release_contracts" / "v1" / "v1_cleanup_deprecation_ledger.json"


def test_run_api_solve_alias_is_retained_for_v1_boundary() -> None:
    assert hasattr(RunAPI, "run")
    assert hasattr(RunAPI, "solve")
    assert RunAPI.solve is RunAPI.run


def test_run_api_solve_alias_cleanup_requires_ledger_update() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in ledger["entries"]}
    solve_alias = entries["api.run.solve_alias"]

    assert solve_alias["status"] in {"deprecate_only", "retain"}
    assert "RunAPI.run" in solve_alias["replacement"]
    assert solve_alias["tests_required_before_removal"]
    assert solve_alias["rollback_note"]
