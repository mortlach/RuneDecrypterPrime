from __future__ import annotations
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCOPE_LOCK_JSON = REPO_ROOT / "docs" / "release_contracts" / "v1" / "v1_scope_lock.json"


def _scope() -> dict[str, object]:
    assert SCOPE_LOCK_JSON.exists(), f"missing scope lock file: {SCOPE_LOCK_JSON}"
    return json.loads(SCOPE_LOCK_JSON.read_text(encoding="utf-8"))


def test_v1_scope_lock_schema_is_stable() -> None:
    scope = _scope()
    assert scope["schema"] == "rdp_v1_scope_lock.v1"
    assert scope["scope_date"] == "2026-06-10"
    assert (
        scope["source_handoff"]
        == "rdp_v1_final_integrated_handoff_post_crosscheck_2026-06-10"
    )


def test_v1_includes_span_hamming_and_scheduled_stream_lookup() -> None:
    scope = _scope()
    included = scope["v1_included"]
    assert included["span_hamming"]["status"] == "v1_optional"
    assert included["scheduled_stream_lookup"]["status"] == "v1_core"
    assert included["scorer_capability_status"]["status"] == "v1_core"
    assert included["stop_reason_schema"]["status"] == "v1_core"
    assert included["typed_builder_config_boundary"]["status"] == "v1_core"


def test_v1_excludes_new_ngram_hamming_as_production_scoring() -> None:
    not_v1 = _scope()["not_v1_production"]
    ngram = not_v1["new_ngram_hamming_scoring"]
    assert ngram["status"] == "experimental_report_only"
    assert "production_rank_effect is none" in ngram["allowed_only_if"]


def test_v1_excludes_huge_ngram_assets_and_full_resume_solving() -> None:
    not_v1 = _scope()["not_v1_production"]
    assert not_v1["huge_ngram_assets"]["status"] == "experimental"
    assert not_v1["full_save_restore_solving"]["status"] == "roadmap"


def test_forbidden_v1_behaviour_names_all_locked() -> None:
    forbidden = set(_scope()["forbidden_v1_behaviour"])
    expected = {
        "requested scoring lane warning-and-silent-drop",
        "new n-gram Hamming rank effect in V1",
        "sample n-gram assets treated as V1 authority",
        "full resume/checkpoint solving promised as V1",
        "absolute paths in public artifact manifests",
        "explicit TORCH request silently falls back to NumPy",
        "fixed scheduled-stream values treated as text characters",
        "dynamic stop reasons left outside the V1 stop schema",
    }
    assert expected <= forbidden
