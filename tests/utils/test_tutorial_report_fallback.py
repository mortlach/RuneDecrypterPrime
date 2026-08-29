from __future__ import annotations
from rdp import api
import rdp.api.solver_report
from types import SimpleNamespace
from rune_decrypter_prime.utils.tutorial_report import build_tutorial_run_report

def test_tutorial_report_falls_back_to_solution_when_report_fields_are_none() -> None:
    solution = SimpleNamespace(key=[3, 1, 4], plaintext_idx=[1, 2, 3, 4], plaintext_rune='ᚠᚢᚦᚩ', score=0.75, stop_reason='target_score', evals=42, tokens_processed=128, meta={})
    solver_report = rdp.api.solver_report.build_solver_report(solver_name='beam', requested_seed=7, effective_seed=7, normalized_params={'beam_width': 4})
    report = build_tutorial_run_report(title='demo', cipher='scheduled_stream_lookup', solution=solution, solver_report=solver_report, key_idx=[3, 1, 4], pt_idx_ref=[1, 2, 3, 4])
    assert report['solver']['score'] == 0.75
    assert report['solver']['stop_reason'] == 'target_score'
    assert report['solver']['evals'] == 42
    assert report['solver']['tokens_processed'] == 128
