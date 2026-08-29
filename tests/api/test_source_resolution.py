from __future__ import annotations
import rdp.api.source_resolution
from rdp import api
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
import pytest
from rune_decrypter_prime.data.liber_primus.lp_main import MAIN_TRANSCRIPT_ASSET_ID, main_transcript_asset_identity

def _main_asset_version() -> str:
    return main_transcript_asset_identity()['asset_version']

def _source_ref(*, source_kind: str, ref: dict[str, object], asset_id: str=MAIN_TRANSCRIPT_ASSET_ID, asset_version: str | None=None) -> api.SourceReferenceInput:
    return api.SourceReferenceInput(source_kind=source_kind, asset_id=asset_id, asset_version=asset_version or _main_asset_version(), reference=ref)

def _valid_locator_ref_none() -> dict[str, object]:
    return {'page_scheme': 'canon_unsolved_page', 'page_number': 54, 'line': 0, 'line_end': 2, 'word': None, 'word_end': None, 'route_kind': 'none'}

def _valid_locator_ref_line() -> dict[str, object]:
    ref = _valid_locator_ref_none()
    ref.update({'route_kind': 'line', 'line_mode': 'boustrophedon', 'line_selector': 'first_only'})
    return ref

def _valid_partition_ref() -> dict[str, object]:
    return {'partition_scheme': 'red_rune_17', 'partition_ordinal': '1', 'canon_start': 0, 'canon_end': 2, 'intersect_page_scheme': None, 'intersect_page_number': None}

def _assert_resolved_payload_shape(resolved: rdp.api.source_resolution.ResolvedSourceInput) -> None:
    assert isinstance(resolved.ct_idx, tuple)
    assert resolved.ct_idx
    assert all((isinstance(item, int) and (not isinstance(item, bool)) for item in resolved.ct_idx))
    assert all((0 <= item <= 28 for item in resolved.ct_idx))
    assert isinstance(resolved.wli, tuple)
    assert len(resolved.wli) == len(resolved.ct_idx)
    assert all((isinstance(pair, tuple) and len(pair) == 2 for pair in resolved.wli))
    assert all((pos >= 0 and word_len > 0 and (pos < word_len) for pos, word_len in resolved.wli))

def _assert_path_free(value: object) -> None:
    assert not isinstance(value, Path)
    if isinstance(value, Mapping):
        for key, item in value.items():
            assert isinstance(key, str)
            _assert_path_free(item)
    elif isinstance(value, tuple):
        for item in value:
            _assert_path_free(item)

def test_resolve_lp_locator_ref_returns_tuple_solver_input() -> None:
    source_ref = _source_ref(source_kind='liber_primus.locator', ref=_valid_locator_ref_none())
    resolved = rdp.api.source_resolution.resolve_source_input_ref(source_ref)
    _assert_resolved_payload_shape(resolved)
    assert resolved.source_ref is source_ref
    assert resolved.source_metadata['source_kind'] == 'liber_primus.locator'
    assert resolved.source_metadata['asset_id'] == MAIN_TRANSCRIPT_ASSET_ID
    assert resolved.source_metadata['asset_version'] == _main_asset_version()

def test_resolve_lp_partition_ref_returns_tuple_solver_input() -> None:
    source_ref = _source_ref(source_kind='liber_primus.partition', ref=_valid_partition_ref())
    resolved = rdp.api.source_resolution.resolve_source_input_ref(source_ref)
    _assert_resolved_payload_shape(resolved)
    assert resolved.source_ref is source_ref
    assert resolved.source_metadata['source_kind'] == 'liber_primus.partition'

def test_resolve_lp_source_ref_rejects_stale_asset_version() -> None:
    source_ref = _source_ref(source_kind='liber_primus.locator', ref=_valid_locator_ref_none(), asset_version='stale-version')
    with pytest.raises(ValueError, match='asset_version'):
        rdp.api.source_resolution.resolve_source_input_ref(source_ref)

def test_resolve_lp_source_ref_rejects_wrong_asset_id() -> None:
    source_ref = _source_ref(source_kind='liber_primus.partition', ref=_valid_partition_ref(), asset_id='wrong.asset')
    with pytest.raises(ValueError, match='asset_id'):
        rdp.api.source_resolution.resolve_source_input_ref(source_ref)

def test_resolve_source_input_ref_fails_closed_for_unsupported_source_kind() -> None:
    source_ref = api.SourceReferenceInput(source_kind='other.source', asset_id='asset', asset_version='version', reference={'selector': 'one'})
    with pytest.raises(ValueError, match='unsupported source_kind'):
        rdp.api.source_resolution.resolve_source_input_ref(source_ref)

def test_resolve_source_input_ref_rejects_loose_dict_inputs() -> None:
    with pytest.raises(TypeError):
        rdp.api.source_resolution.resolve_source_input_ref({'source_kind': 'liber_primus.locator', 'asset_id': MAIN_TRANSCRIPT_ASSET_ID, 'asset_version': _main_asset_version(), 'ref': _valid_locator_ref_none()})

def test_resolved_source_input_is_copy_owned_and_metadata_is_immutable() -> None:
    source_ref = _source_ref(source_kind='liber_primus.partition', ref=_valid_partition_ref())
    resolved = rdp.api.source_resolution.resolve_source_input_ref(source_ref)
    assert isinstance(resolved.source_metadata, MappingProxyType)
    with pytest.raises(TypeError):
        resolved.source_metadata['source'] = 'changed'
    manual_metadata = {'nested': {'value': 1}, 'items': [1, 2, None]}
    manual = rdp.api.source_resolution.ResolvedSourceInput(ct_idx=[1, 2], wli=[[0, 1], [0, 1]], source_ref=source_ref, source_metadata=manual_metadata)
    manual_metadata['nested']['value'] = 99
    manual_metadata['items'].append(3)
    assert manual.source_metadata['nested']['value'] == 1
    assert manual.source_metadata['items'] == (1, 2, None)
    with pytest.raises(TypeError):
        manual.source_metadata['nested']['value'] = 2

def test_resolved_source_metadata_is_path_free() -> None:
    ref = _valid_partition_ref()
    ref['intersect_page_scheme'] = 'canon_unsolved_page'
    ref['intersect_page_number'] = 0
    source_ref = _source_ref(source_kind='liber_primus.partition', ref=ref)
    resolved = rdp.api.source_resolution.resolve_source_input_ref(source_ref)
    _assert_path_free(resolved.source_metadata)
    assert isinstance(resolved.source_metadata['intersect_page'], MappingProxyType)

def test_resolver_reconstructs_routes_from_split_fields_not_route_strings() -> None:
    line_ref = _source_ref(source_kind='liber_primus.locator', ref=_valid_locator_ref_line())
    resolved = rdp.api.source_resolution.resolve_source_input_ref(line_ref)
    _assert_resolved_payload_shape(resolved)
    assert resolved.source_metadata['route'] == 'line:boustrophedon:first_only'
    legacy_ref = _valid_locator_ref_line()
    legacy_ref['route'] = 'line:boustrophedon:first_only'
    with pytest.raises(ValueError):
        _source_ref(source_kind='liber_primus.locator', ref=legacy_ref)

def test_resolved_source_input_validates_materialized_output() -> None:
    source_ref = _source_ref(source_kind='liber_primus.locator', ref=_valid_locator_ref_none())
    with pytest.raises(ValueError):
        rdp.api.source_resolution.ResolvedSourceInput(ct_idx=[], wli=None, source_ref=source_ref, source_metadata={})
    with pytest.raises(ValueError):
        rdp.api.source_resolution.ResolvedSourceInput(ct_idx=[29], wli=None, source_ref=source_ref, source_metadata={})
    with pytest.raises(TypeError):
        rdp.api.source_resolution.ResolvedSourceInput(ct_idx=[True], wli=None, source_ref=source_ref, source_metadata={})
    with pytest.raises(ValueError):
        rdp.api.source_resolution.ResolvedSourceInput(ct_idx=[1], wli=[(1, 1)], source_ref=source_ref, source_metadata={})
    with pytest.raises(TypeError):
        rdp.api.source_resolution.ResolvedSourceInput(ct_idx=[1], wli=[(0, 1)], source_ref=source_ref, source_metadata={'path': Path('assets/input.txt')})
