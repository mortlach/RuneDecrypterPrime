from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PUSH_GATE = REPO_ROOT / ".github" / "workflows" / "rdp_v1_full_ci.yml"
FULL_PROOF = REPO_ROOT / ".github" / "workflows" / "rdp_v1_full_proof.yml"


def test_v1_push_gate_is_the_only_automatic_ci_gate() -> None:
    text = PUSH_GATE.read_text(encoding="utf-8")
    assert "name: RDP V1 push gate" in text
    assert "push:" in text
    assert "pull_request:" in text
    assert '"prelease/**"' in text
    assert "python tools/ci/install_light.py" in text
    assert '"not full_assets"' in text
    assert "TutorialRunSet.CI_LIGHT" in text


def test_v1_full_proof_is_manual_full_asset_release_gate() -> None:
    text = FULL_PROOF.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "\n  push:\n" not in text
    assert "windows-latest" in text
    assert "ubuntu-latest" in text
    assert '"3.11"' in text
    assert "python install.py" in text
    assert "complete pytest suite with full assets" in text
    assert "TutorialRunSet.ALL_WORKING" in text


def test_v1_full_proof_preserves_install_test_and_tutorial_logs() -> None:
    text = FULL_PROOF.read_text(encoding="utf-8")
    assert "Upload full-proof logs" in text
    assert "output/install_logs/*.log" in text
    assert "output/test_logs/*.log" in text
    assert "output/tutorial_logs/*.txt" in text
