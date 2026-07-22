from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_lesson_registry_has_unique_ids_and_allowed_statuses():
    text = (ROOT / "cipher_development/LESSONS.md").read_text(encoding="utf-8")
    ids = re.findall(r"^## (CSL-\d{3})", text, re.MULTILINE)
    assert ids and len(ids) == len(set(ids))
    statuses = re.findall(r"^Status: (\w+)", text, re.MULTILINE)
    assert set(statuses) <= {
        "candidate", "supported", "general", "limited", "superseded", "rejected"
    }
    assert len(statuses) == len(ids)
    assert "No general solver-performance lesson" in text
    assert "never reused or deleted" in text
    assert "never edit this file automatically" in text


def test_each_lesson_has_required_fields():
    text = (ROOT / "cipher_development/LESSONS.md").read_text(encoding="utf-8")
    blocks = re.split(r"(?=^## CSL-\d{3})", text, flags=re.MULTILINE)[1:]
    for block in blocks:
        for field in (
            "Status:", "Category:", "Scope:", "Observation:",
            "Operational implication:", "Evidence:", "Counterexamples or limits:",
            "Last reviewed:", "Supersedes:", "Superseded by:",
        ):
            assert field in block


def test_campaign_template_contains_required_discipline():
    text = (ROOT / "cipher_development/CAMPAIGN_TEMPLATE.md").read_text(encoding="utf-8")
    for heading in (
        "Applicable prior lessons", "Intentional departures", "Replay plan",
        "Candidate lessons awaiting promotion", "Stop criteria",
    ):
        assert heading in text
    assert "Do not use argparse or environment variables" in text
    assert "not a campaign engine" in text


def test_established_campaigns_reference_lessons_and_replay():
    for campaign in ("two_period_overlay", "periodic_sub_trans_wli"):
        text = (ROOT / "cipher_development" / campaign / "CAMPAIGN.md").read_text()
        assert "Applicable prior lessons" in text
        assert "Replay plan" in text
        assert "Candidate lessons awaiting promotion" in text
        assert "CSL-001" in text


def test_replay_adapters_do_not_call_discovery_or_exploitation():
    import ast

    forbidden = {
        "run_search", "run_case", "coordinate_search", "anneal_and_polish",
        "generate_seed_keys_periodic_columnar",
    }
    for campaign in ("two_period_overlay", "periodic_sub_trans_wli"):
        path = ROOT / "cipher_development" / campaign / "replay.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert not (called & forbidden)


def test_campaign_runs_write_replay_contexts_and_replay_always_refines():
    for campaign in ("two_period_overlay", "periodic_sub_trans_wli"):
        run_text = (ROOT / "cipher_development" / campaign / "run.py").read_text()
        replay_text = (ROOT / "cipher_development" / campaign / "replay.py").read_text()
        assert "write_replay_context" in run_text
        assert "replay_context.json" in run_text
        assert "ExperimentDecision.REFINE" in replay_text
