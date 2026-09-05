from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DOC = ROOT / 'docs' / 'release_contracts' / 'v1' / 'D5_REPORT_AND_ARTIFACT_AGREEMENT.md'

def test_d5_contract_doc_names_report_and_artifact_contracts() -> None:
    text = CONTRACT_DOC.read_text(encoding='utf-8')
    for phrase in ('Artifact agreement', 'Run artifact manifest', 'Required by agreement', 'Listed in manifest', 'oracle_use', 'truth_data_policy', 'reproducibility', 'full-proof CI'):
        assert phrase in text

def test_d5_contract_doc_does_not_call_optional_solver_report_required() -> None:
    text = CONTRACT_DOC.read_text(encoding='utf-8')
    assert 'Required agreement rows are' not in text
    assert '`artifacts/solver_report.json` | `solver_report` | no' in text
