from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[2]
TUTORIAL_ROOT = REPO_ROOT / "tutorials" / "v1"
MANIFEST = TUTORIAL_ROOT / "tutorial_manifest_v1.json"
RUN_ALL = TUTORIAL_ROOT / "run_all.py"
SSL_HELPERS = REPO_ROOT / "src" / "rune_decrypter_prime" / "utils" / "scheduled_stream_lookup_tutorial_utils.py"
RELEASE_GATES = {"v1_smoke", "v1_release"}
FULL_V1_GATES = {"v1_smoke", "v1_release", "v1_extended", "v1_showcase_near_solve"}
KNOWN_BLOCKED_GATES = {"broken_contract_fix_needed", "wrapper_script_fix_needed", "remove_from_pure_release"}
ALLOWED_GATES = RELEASE_GATES | FULL_V1_GATES | {"v1_slow_demo", "optional_lm3"} | KNOWN_BLOCKED_GATES


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _entries() -> list[dict]:
    data = _manifest()
    assert data["schema"] == "rdp_tutorial_manifest.v1"
    assert isinstance(data["tutorials"], list)
    return data["tutorials"]


def _entry(path: str) -> dict:
    matches = [entry for entry in _entries() if entry["path"] == path]
    assert len(matches) == 1, path
    return matches[0]


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _run_all_module() -> ModuleType:
    return _load_module(RUN_ALL, "rdp_tutorial_run_all")


def test_manifest_entries_have_required_classification_fields() -> None:
    required = {
        "path",
        "title",
        "cipher_family",
        "tutorial_kind",
        "gate",
        "required_asset_profile",
        "expected_under_lm2_baseline",
        "acceptance_kind",
        "observed_lm2_baseline",
        "uses_oracle_stop_score",
        "supplies_true_key_to_solver",
        "current_status",
        "notes",
    }
    for entry in _entries():
        assert required <= set(entry), entry.get("path")
        assert entry["gate"] in ALLOWED_GATES, entry["path"]
        assert entry["notes"].strip(), entry["path"]


def test_all_release_tutorial_entries_exist_on_disk() -> None:
    missing = []
    for entry in _entries():
        if entry["gate"] == "v1_release":
            path = TUTORIAL_ROOT / entry["path"]
            if not path.is_file():
                missing.append(entry["path"])
    assert not missing


def test_release_gate_includes_scheduled_stream_lookup_exact_real_solve() -> None:
    entry = _entry("Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py")

    assert entry["gate"] == "v1_release"
    assert entry["acceptance_kind"] == "min_match_ratio"
    assert entry["min_match_ratio"] == 1.0
    assert entry["current_status"] == "active"
    assert entry["supplies_true_key_to_solver"] is False


def test_scheduled_stream_lookup_extended_and_showcase_are_classified_honestly() -> None:
    assert _entry("Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py")["gate"] == "v1_extended"
    segmented = _entry("Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py")
    assert segmented["gate"] == "v1_showcase_near_solve"
    assert segmented["acceptance_kind"] == "near_solve_min_match"


def test_known_broken_entries_are_not_selected_by_release_or_full_v1() -> None:
    for entry in _entries():
        assert entry["current_status"] != "known_broken", entry["path"]


def test_pretty_runner_selected_tutorials_are_manifested() -> None:
    runner = _load_module(TUTORIAL_ROOT / "run_pretty_print_release.py", "rdp_pretty_runner_manifest_alignment")
    entries = {entry["path"]: entry for entry in _entries()}

    for selected in runner.TUTORIALS:
        entry = entries[selected.path]
        assert entry["current_status"] == "active"
        assert entry["acceptance_kind"] in {"min_match_ratio", "near_solve_min_match"}
        assert entry["min_match_ratio"] == selected.min_match_ratio


def test_runner_parses_unified_tutorial_match_ratio_label() -> None:
    run_all = _run_all_module()

    assert run_all._parse_match_ratio("match_ratio : 1.000") == 1.0
    assert run_all._parse_match_ratio("Match ratio: 0.901") == 0.901


def test_scheduled_stream_lookup_real_tutorials_emit_session_benchmark_report() -> None:
    text = SSL_HELPERS.read_text(encoding="utf-8")

    assert "return_solver_report=True" in text
    assert "print_tutorial_session_report" in text
    assert "TutorialReference.key_and_plaintext" in text
    assert "TutorialStopPolicy" in text
    assert "TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK" in text
