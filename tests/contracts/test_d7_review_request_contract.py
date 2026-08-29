from __future__ import annotations
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_REQUEST = REPO_ROOT / 'docs' / 'release_contracts' / 'v1' / 'D7_REVIEW_REQUEST.md'

def test_d7_review_request_exists_and_names_review_scope() -> None:
    assert REVIEW_REQUEST.is_file(), 'missing D7 review request'
    text = REVIEW_REQUEST.read_text(encoding='utf-8')
    required = ['Branch under review: `prelease/v1.0.0_d7`', 'D7 is intended to close V1 contract ambiguity', 'Requested reviewer checks', 'Full D7 gate']
    for phrase in required:
        assert phrase in text
