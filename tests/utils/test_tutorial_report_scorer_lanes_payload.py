from __future__ import annotations
from types import SimpleNamespace
from rune_decrypter_prime.utils.tutorial_report import build_tutorial_run_report

def test_tutorial_report_preserves_scorer_lanes_dict_payload() -> None:
    solution = SimpleNamespace(
        key=[3, 1, 4], plaintext_idx=[1, 2, 3], plaintext_rune="abc", score=0.7, meta={}
    )
    lanes_payload = {
        "lanes": [{"lane": "language_model", "effective_state": "active"}],
        "components": [],
    }
    report = build_tutorial_run_report(
        title="contract",
        cipher="scheduled_stream_lookup",
        solution=solution,
        solver_report={"details": {"scorer_lanes": lanes_payload}},
        key_idx=[3, 1, 4],
        pt_idx_ref=[1, 2, 3],
    )
    assert report["solver_report"]["scorer_lanes"] == lanes_payload


def test_tutorial_report_wraps_legacy_scorer_lanes_list_payload() -> None:
    solution = SimpleNamespace(key=[], plaintext_idx=[1], plaintext_rune='a', meta={})
    report = build_tutorial_run_report(title='contract', cipher='scheduled_stream_lookup', solution=solution, solver_report={'details': {'scorer_lanes': [{'lane': 'legacy'}]}})
    assert report['solver_report']['scorer_lanes'] == {'lanes': [{'lane': 'legacy'}]}
