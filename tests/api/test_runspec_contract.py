from __future__ import annotations
from rdp import api
from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest
from rdp.core.config.logging_config import LoggingConfig

def _minimal_runspec(problem_input: object) -> api.RunSpec:
    return api.RunSpec(problem_input=problem_input, cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=None))

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

def test_rune_input_is_frozen_and_infers_text_formats() -> None:
    raw = api.RuneInput('ᚠᚢᚦ')
    assert raw.value == 'ᚠᚢᚦ'
    assert raw.format is api.RuneInputFormat.RUNES
    with pytest.raises(FrozenInstanceError):
        raw.value = 'changed'
    with pytest.raises(ValueError):
        api.RuneInput('')
    with pytest.raises(TypeError):
        api.RuneInput(Path('assets/input.txt'))

    assert api.RuneInput('TH·E').format is api.RuneInputFormat.RUNE_LATIN
    assert api.RuneInput('T|H|E').format is api.RuneInputFormat.RUNE_LATIN
    assert api.RuneInput('the loss of').format is api.RuneInputFormat.ENGLISH
    with pytest.raises(ValueError, match='mix'):
        api.RuneInput('ᚦHE')


def test_rune_input_accepts_an_explicit_format() -> None:
    payload = api.RuneInput('TH', format=api.RuneInputFormat.RUNE_LATIN)
    assert payload.format is api.RuneInputFormat.RUNE_LATIN
    with pytest.raises(TypeError):
        api.RuneInput('TH', format='rune_latin')  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        api.RuneInput('TH', format=api.RuneInputFormat.INDICES)
    with pytest.raises(ValueError):
        api.RuneInput('TH', word_length_information=((0, 1),))

def test_normalized_input_copies_ct_idx_and_wli_to_tuples() -> None:
    ct_idx = [1, 2, 3]
    wli = [[0, 1], [1, 2], [2, 3]]
    payload = api.RuneInput(value=ct_idx, word_length_information=wli)
    ct_idx.append(4)
    wli[0][0] = 99
    assert payload.indices == (1, 2, 3)
    assert payload.word_length_information == ((0, 1), (1, 2), (2, 3))
    assert payload.indices == (1, 2, 3)
    with pytest.raises(TypeError):
        api.RuneInput(value=[1], word_lengths=[(0, 1)])  # type: ignore[call-arg]

def test_normalized_input_rejects_invalid_ct_idx_and_wli() -> None:
    with pytest.raises(ValueError):
        api.RuneInput(value=[])
    with pytest.raises(ValueError):
        api.RuneInput(value=[29])
    with pytest.raises(TypeError):
        api.RuneInput(value=[True])
    with pytest.raises(ValueError):
        api.RuneInput(value=[1, 2], word_length_information=[(0, 1)])
    with pytest.raises(ValueError):
        api.RuneInput(value=[1], word_length_information=[(0, 1, 2)])
    with pytest.raises(TypeError):
        api.RuneInput(value=[1], word_length_information=[('0', 1)])

def test_normalized_input_rejects_unordered_or_one_shot_ct_idx_containers() -> None:
    with pytest.raises(TypeError):
        api.RuneInput(value={1, 2, 3})
    with pytest.raises(TypeError):
        api.RuneInput(value=(item for item in [1, 2, 3]))
    with pytest.raises(TypeError):
        api.RuneInput(value={0: 1})

def test_normalized_input_accepts_deterministic_ordered_ct_idx_containers() -> None:
    assert api.RuneInput(value=[1, 2, 3]).indices == (1, 2, 3)
    assert api.RuneInput(value=(1, 2, 3)).indices == (1, 2, 3)
    assert api.RuneInput(value=range(3)).indices == (0, 1, 2)

def test_normalized_input_rejects_unordered_or_one_shot_wli_containers() -> None:
    with pytest.raises(TypeError):
        api.RuneInput(value=[1], word_length_information={(0, 1)})
    with pytest.raises(TypeError):
        api.RuneInput(value=[1], word_length_information=(pair for pair in [(0, 1)]))
    with pytest.raises(TypeError):
        api.RuneInput(value=[1], word_length_information=[{0, 1}])
    with pytest.raises(TypeError):
        api.RuneInput(value=[1], word_length_information=[(item for item in [0, 1])])

def test_normalized_input_validates_wli_pair_semantics() -> None:
    with pytest.raises(ValueError):
        api.RuneInput(value=[1], word_length_information=[(-1, 3)])
    with pytest.raises(ValueError):
        api.RuneInput(value=[1], word_length_information=[(0, 0)])
    with pytest.raises(ValueError):
        api.RuneInput(value=[1], word_length_information=[(3, 3)])

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
    spec = api.RunSpec(problem_input=api.RuneInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=None), scoring=api.ScoringConfig.from_dict(scorer_params))
    scorer_params['window_size'] = 20
    assert spec.text_direction is api.TextDirection.LTR
    assert spec.compute_device is api.ComputeDevice.CPU
    assert spec.telemetry_enabled is True
    assert spec.scoring.window_size == 10
    with pytest.raises(FrozenInstanceError):
        spec.telemetry_enabled = False

def test_runspec_accepts_each_problem_input_form() -> None:
    for problem_input in (api.RuneInput('abc'), api.RuneInput(value=[1, 2, 3]), api.SourceReferenceInput(source_kind='liber_primus.partition', asset_id='a', asset_version='v', reference=_valid_partition_ref())):
        spec = _minimal_runspec(problem_input)
        assert spec.problem_input is problem_input

def test_runspec_rejects_alias_problem_inputs_and_runtime_controls() -> None:
    with pytest.raises(TypeError):
        _minimal_runspec({'text': 'abc'})
    with pytest.raises(TypeError):
        api.RunSpec(problem_input=api.RuneInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=None), telemetry_on=False)

def test_runspec_validates_nested_public_specs_without_execution_routing() -> None:
    with pytest.raises(TypeError):
        api.RunSpec(problem_input=api.RuneInput('abc'), cipher=object(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=None))
    with pytest.raises(TypeError):
        api.RunSpec(problem_input=api.RuneInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=(api.KeySpec.repeating(length=3), object()), solver=api.SolverSpec.beam_search(width=2, rounds=None))
    with pytest.raises(TypeError):
        api.RunSpec(problem_input=api.RuneInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=object())
    with pytest.raises(TypeError):
        api.RunSpec(problem_input=api.RuneInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=None), logging=object())
    spec = api.RunSpec(problem_input=api.RuneInput('abc'), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=3), solver=api.SolverSpec.beam_search(width=2, rounds=None), logging=api.LoggingConfig(portable_output=True))
    assert isinstance(spec.logging, LoggingConfig)
