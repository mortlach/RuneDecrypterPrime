from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "rdp_v1_full_proof.yml"


def _workflow_text() -> str:
    assert WORKFLOW.exists(), f"missing V1 full-proof workflow: {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


def test_v1_full_proof_workflow_is_manual_release_gate() -> None:
    text = _workflow_text()

    assert "workflow_dispatch:" in text
    assert "windows-latest" in text
    assert "ubuntu-latest" in text
    assert '"3.11"' in text


def test_v1_full_proof_workflow_runs_install_pytest_and_tutorials() -> None:
    text = _workflow_text()

    assert "python install.py" in text
    assert '"pytest"' in text
    assert '"tests"' in text
    assert "tutorials" in text
    assert "v1" in text
    assert "run_all.py" in text


def test_v1_full_proof_workflow_preserves_failure_logs() -> None:
    text = _workflow_text()

    assert "Upload installer logs on failure" in text
    assert "Upload full pytest log" in text
    assert "Upload V1 release tutorial log" in text
