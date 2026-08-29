from __future__ import annotations
import rdp.api.source_resolution
from rdp import api
from dataclasses import dataclass
import pytest
pytestmark = pytest.mark.tier_a

@dataclass(frozen=True)
class _Payload:
    ct_idx: list[int]
    wli: list[list[int]]
    metadata: dict[str, object]

def test_lp_label_source_ref_accepts_canonical_source_label() -> None:
    ref = api.SourceReferenceInput(source_kind='liber_primus.label', asset_id='liber_primus.main_transcript', asset_version='test-version', reference={'label': 'red_rune.welcome_pilgrim'})
    assert ref.source_kind == 'liber_primus.label'
    assert ref.ref['label'] == 'red_rune.welcome_pilgrim'

def test_lp_label_source_ref_accepts_simple_user_label() -> None:
    ref = api.SourceReferenceInput(source_kind='liber_primus.label', asset_id='liber_primus.main_transcript', asset_version='test-version', reference={'label': 'welcome_pilgrim'})
    assert ref.ref['label'] == 'welcome_pilgrim'

def test_lp_label_source_ref_accepts_solved_alias_namespace() -> None:
    ref = api.SourceReferenceInput(source_kind='liber_primus.label', asset_id='liber_primus.main_transcript', asset_version='test-version', reference={'label': 'solved.welcome_pilgrim'})
    assert ref.ref['label'] == 'solved.welcome_pilgrim'

def test_lp_label_source_ref_rejects_extra_keys() -> None:
    with pytest.raises(ValueError, match='unsupported keys'):
        api.SourceReferenceInput(source_kind='liber_primus.label', asset_id='liber_primus.main_transcript', asset_version='test-version', reference={'label': 'welcome_pilgrim', 'period': 7})

def test_source_resolution_dispatches_lp_label(monkeypatch) -> None:
    from rune_decrypter_prime.data.liber_primus import lp_source_catalogue
    monkeypatch.setattr(rdp.api.source_resolution, '_validate_lp_main_identity', lambda source_ref: None)

    def fake_payload_from_label(label: str):
        assert label == 'welcome_pilgrim'
        return _Payload(ct_idx=[1, 2, 3], wli=[[0, 3], [1, 3], [2, 3]], metadata={'source_kind': 'liber_primus.label', 'source_label': 'red_rune.welcome_pilgrim'})
    monkeypatch.setattr(lp_source_catalogue, 'payload_from_label', fake_payload_from_label)
    resolved = rdp.api.source_resolution.resolve_source_input_ref(api.SourceReferenceInput(source_kind='liber_primus.label', asset_id='liber_primus.main_transcript', asset_version='test-version', reference={'label': 'welcome_pilgrim'}))
    assert resolved.ct_idx == (1, 2, 3)
    assert resolved.wli == ((0, 3), (1, 3), (2, 3))
    assert resolved.source_metadata['source_kind'] == 'liber_primus.label'
    assert resolved.source_metadata['source_label'] == 'red_rune.welcome_pilgrim'
