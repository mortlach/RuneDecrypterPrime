from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCOPE_LOCK_JSON = REPO_ROOT / "docs" / "release_contracts" / "v1" / "v1_scope_lock.json"


def test_full_save_restore_solving_is_not_v1() -> None:
    scope = json.loads(SCOPE_LOCK_JSON.read_text(encoding="utf-8"))
    resume = scope["not_v1_production"]["full_save_restore_solving"]
    assert resume["status"] == "roadmap"
    assert "experimental" in resume["allowed_only_if"]
    assert "unsupported" in resume["allowed_only_if"]


def test_resume_boundary_is_named_in_forbidden_v1_behaviour() -> None:
    scope = json.loads(SCOPE_LOCK_JSON.read_text(encoding="utf-8"))
    assert "full resume/checkpoint solving promised as V1" in scope["forbidden_v1_behaviour"]
