from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
D5_CONTRACT_DOC = ROOT / 'docs' / 'release_contracts' / 'v1' / 'D5_REPORT_AND_ARTIFACT_AGREEMENT.md'

def test_report_contract_names_reserved_solver_report_sections() -> None:
    text = D5_CONTRACT_DOC.read_text(encoding='utf-8')
    for phrase in ('report_contract', 'oracle_use', 'truth_data_policy', 'reproducibility', 'must not overwrite or pre-seed'):
        assert phrase in text

def test_d5_contract_still_names_report_only_no_rank_effect() -> None:
    text = D5_CONTRACT_DOC.read_text(encoding='utf-8')
    assert 'Report-only scorer lanes are diagnostic' in text
    assert 'must not affect score, raw score, ordering, or tie-breaks' in text
