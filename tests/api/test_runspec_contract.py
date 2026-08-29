from __future__ import annotations
from rdp import api
from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest
from rune_decrypter_prime.core.config.logging_config import LoggingConfig

def _minimal_runspec(problem_input: object) -> api.RunSpec:
    return api.RunSpec(problem_input=problem_input, cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=0))

def _valid_locator_ref_none() -> dict[str, object]:
    return {'page_scheme': 'canon_unsolved_page', 'page_number': 54, 'line': 0, 'line_end': 2, 'word': None, 'word_end': None, 'route_kind': 'none'}

def _valid_locator_ref_line() -> dict[str, object]:
    ref = _valid_locator_ref_none()
    ref.update({'route_kind': 'line', 'line_mode': 'boustrophedon', 'line_selector': 'first_only'})
    return ref

def _valid_locator_ref_spiral() -> dict[str, object]:
    ref = _valid_locator_ref_none()
    ref.update({'route_kind': 'spiral', 'spiral_direction': 'clockwise', 'spiral_start_corner': 'top_left', 'spiral_skip_empty': True})
    return ref

def _valid_partition_ref() -> dict[str, object]:
    return {'partition_scheme': 'red_rune_17', 'partition_ordinal': '1', 'canon_start': 0, 'canon_end': 2, 'intersect_page_scheme': None, 'intersect_page_number': None}

def test_raw_text_input_is_frozen_and_requires_real_string() -> None:
    raw = api.RawTextInput('ᚠᚢᚦ')
    assert raw.text == 'ᚠᚢᚦ'
    with pytest.raises(FrozenInstanceError):
        raw.text = 'changed'
    with pytest.raises(ValueError):
        api.RawTextInput('')
    with pytest.raises(TypeError):
        api.RawTextInput(Path('assets/input.txt'))

def test_normalized_input_copies_ct_idx_and_wli_to_tuples() -> None:
    ct_idx = [1, 2, 3]
    wli = [[0, 1], [1, 2], [2, 3]]
    payload = api.RuneIndexInput(indices=ct_idx, word_lengths=wli)
    ct_idx.append(4)
    wli[0][0] = 99
    assert payload.ct_idx == (1, 2, 3)
    assert payload.wli == ((0, 1), (1, 2), (2, 3))

def test_normalized_input_rejects_invalid_ct_idx_and_wli() -> None:
    with pytest.raises(ValueError):
        api.RuneIndexInput(indices=[])
    with pytest.raises(ValueError):
        api.RuneIndexInput(indices=[29])
    with pytest.raises(TypeError):
        api.RuneIndexInput(indices=[True])
    with pytest.raises(ValueError):
        api.RuneIndexInput(indices=[1, 2], word_lengths=[(0, 1)])
    with pytest.raises(ValueError):
        api.RuneIndexInput(indices=[1], word_lengths=[(0, 1, 2)])
    with pytest.raises(TypeError):
        api.RuneIndexInput(indices=[1], word_lengths=[('0', 1)])

def test_normalized_input_rejects_unordered_or_one_shot_ct_idx_containers() -> None:
    with pytest.raises(TypeError):
        api.RuneIndexInput(indices={1, 2, 3})
    with pytest.raises(TypeError):
        api.RuneIndexInput(indices=(item for item in [1, 2, 3]))
    with pytest.raises(TypeError):
        api.RuneIndexInput(indices={0: 1})

def test_normalized_input_accepts_deterministic_ordered_ct_idx_containers() -> None:
    assert api.RuneIndexInput(indices=[1, 2, 3]).ct_idx == (1, 2, 3)
    assert api.RuneIndexInput(indices=(1, 2, 3)).ct_idx == (1, 2, 3)
    assert api.RuneIndexInput(indices=range(3)).ct_idx == (0, 1, 2)

def test_normalized_input_rejects_unordered_or_one_shot_wli_containers() -> None:
    with pytest.raises(TypeError):
        api.RuneIndexInput(indices=[1], word_lengths={(0, 1)})
    with pytest.raises(TypeError):
        api.RuneIndexInput(indices=[1], word_lengths=(pair for pair in [(0, 1)]))
    with pytest.raises(TypeError):
        api.RuneIndexInput(indices=[1], word_lengths=[{0, 1}])
    with pytest.raises(TypeError):
        api.RuneIndexInput(indices=[1], word_lengths=[(item for item in [0, 1])])

def test_normalized_input_validates_wli_pair_semantics() -> None:
    with pytest.raises(ValueError):
        api.RuneIndexInput(indices=[1], word_lengths=[(-1, 3)])
    with pytest.raises(ValueError):
        api.RuneIndexInput(indices=[1], word_lengths=[(0, 0)])
    with pytest.raises(ValueError):
        api.RuneIndexInput(indices=[1], word_lengths=[(3, 3)])

def test_source_input_ref_copies_flat_json_primitive_ref_metadata() -> None:
    ref = {'page': 1, 'label': 'p1', 'ambiguous': False, 'note': None}
    source_ref = api.SourceReferenceInput(source_kind='other.source', asset_id='asset', asset_version='105f1c68', reference=ref)
    ref['page'] = 2
    assert dict(source_ref.ref) == {'page': 1, 'label': 'p1', 'ambiguous': False, 'note': None}
    with pytest.raises(TypeError):
        source_ref.ref['page'] = 3

def test_source_input_ref_accepts_valid_lp_locator_refs() -> None:
    for ref in (_valid_locator_ref_none(), _valid_locator_ref_line(), _valid_locator_ref_spiral()):
        source_ref = api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='liber_primus.main_transcript', asset_version='105f1c68', reference=ref)
        assert dict(source_ref.ref) == ref

def test_source_input_ref_rejects_invalid_lp_locator_keys_and_enum_values() -> None:
    ref = _valid_locator_ref_none()
    ref['route'] = 'none'
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_none()
    ref['page_scheme'] = 'bad'
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_line()
    ref['line_mode'] = 'bad'
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_line()
    ref['line_selector'] = 'bad'
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_spiral()
    ref['spiral_direction'] = 'bad'
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_spiral()
    ref['spiral_start_corner'] = 'bad'
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)

def test_source_input_ref_rejects_invalid_lp_locator_structure() -> None:
    ref = _valid_locator_ref_line()
    ref['word'] = 0
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_spiral()
    ref['word_end'] = 0
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_none()
    ref['line'] = None
    ref['line_end'] = 1
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_none()
    ref['line'] = -1
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_none()
    ref['line'] = 2
    ref['line_end'] = 1
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_none()
    ref['word'] = -1
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_none()
    ref['word'] = 2
    ref['word_end'] = 1
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_none()
    ref['page_scheme'] = 'bound_book_page'
    ref['page_number'] = 0
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_locator_ref_spiral()
    ref['spiral_skip_empty'] = 1
    with pytest.raises(TypeError):
        api.SourceReferenceInput(source_kind='liber_primus.locator', asset_id='a', asset_version='v', reference=ref)

def test_source_input_ref_accepts_valid_lp_partition_refs() -> None:
    no_intersection = api.SourceReferenceInput(source_kind='liber_primus.partition', asset_id='liber_primus.main_transcript', asset_version='105f1c68', reference=_valid_partition_ref())
    assert no_intersection.ref['intersect_page_scheme'] is None
    ref = _valid_partition_ref()
    ref['intersect_page_scheme'] = 'canon_unsolved_page'
    ref['intersect_page_number'] = 20
    with_intersection = api.SourceReferenceInput(source_kind='liber_primus.partition', asset_id='liber_primus.main_transcript', asset_version='105f1c68', reference=ref)
    assert with_intersection.ref['intersect_page_number'] == 20

def test_source_input_ref_rejects_invalid_lp_partition_refs() -> None:
    ref = _valid_partition_ref()
    ref['intersect_page'] = {'scheme': 'canon_unsolved_page', 'number': 1}
    with pytest.raises(TypeError):
        api.SourceReferenceInput(source_kind='liber_primus.partition', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_partition_ref()
    ref['partition_scheme'] = 'bad'
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.partition', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_partition_ref()
    ref['canon_end'] = -1
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.partition', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_partition_ref()
    ref['intersect_page_scheme'] = 'canon_unsolved_page'
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.partition', asset_id='a', asset_version='v', reference=ref)
    ref = _valid_partition_ref()
    ref['partition_ordinal'] = '1-0'
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.partition', asset_id='a', asset_version='v', reference=ref)

def test_source_input_ref_rejects_bad_identity_fields_and_unsupported_lp_kind() -> None:
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='', asset_id='a', asset_version='v')
    with pytest.raises(TypeError):
        api.SourceReferenceInput(source_kind=Path('locator'), asset_id='a', asset_version='v')
    with pytest.raises(ValueError):
        api.SourceReferenceInput(source_kind='liber_primus.section', asset_id='a', asset_version='v')

def test_source_input_ref_rejects_paths_objects_and_nested_mutable_ref_metadata() -> None:
    with pytest.raises(TypeError):
        api.SourceReferenceInput(source_kind='other.source', asset_id='a', asset_version='v', reference={'path': Path('x')})
    with pytest.raises(TypeError):
        api.SourceReferenceInput(source_kind='other.source', asset_id='a', asset_version='v', reference={'items': [1, 2]})
    with pytest.raises(TypeError):
        api.SourceReferenceInput(source_kind='other.source', asset_id='a', asset_version='v', reference={Path('k'): 'v'})

def test_runspec_defaults_and_copies_scorer_params() -> None:
    scorer_params = {'window_size': 10}
    spec = api.RunSpec(problem_input=api.RawTextInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=0), scoring=api.ScoringConfig.from_dict(scorer_params))
    scorer_params['window_size'] = 20
    assert spec.text_direction is api.TextDirection.RIGHT_TO_LEFT
    assert spec.compute_device is api.ComputeDevice.CPU
    assert spec.telemetry_enabled is True
    assert spec.scoring.window_size == 10
    with pytest.raises(FrozenInstanceError):
        spec.telemetry_enabled = False

def test_runspec_accepts_each_problem_input_form() -> None:
    for problem_input in (api.RawTextInput('abc'), api.RuneIndexInput(indices=[1, 2, 3]), api.SourceReferenceInput(source_kind='liber_primus.partition', asset_id='a', asset_version='v', reference=_valid_partition_ref())):
        spec = _minimal_runspec(problem_input)
        assert spec.problem_input is problem_input

def test_runspec_rejects_alias_problem_inputs_and_runtime_controls() -> None:
    with pytest.raises(TypeError):
        _minimal_runspec({'text': 'abc'})
    with pytest.raises(TypeError):
        api.RunSpec(problem_input=api.RawTextInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=0), telemetry_on=False)

def test_runspec_validates_nested_public_specs_without_execution_routing() -> None:
    with pytest.raises(TypeError):
        api.RunSpec(problem_input=api.RawTextInput('abc'), cipher=object(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=0))
    with pytest.raises(TypeError):
        api.RunSpec(problem_input=api.RawTextInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=(api.KeySpec.repeating(length=3), object()), solver=api.SolverSpec.beam_search(width=2, rounds=0))
    with pytest.raises(TypeError):
        api.RunSpec(problem_input=api.RawTextInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=object())
    with pytest.raises(TypeError):
        api.RunSpec(problem_input=api.RawTextInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=0), logging=object())
    spec = api.RunSpec(problem_input=api.RawTextInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=0), logging=api.LoggingConfig(portable_output=True))
    assert isinstance(spec.logging, LoggingConfig)
