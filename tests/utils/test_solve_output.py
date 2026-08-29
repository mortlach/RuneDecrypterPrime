from __future__ import annotations
import json
import numpy as np
from rune_decrypter_prime.utils.solve_output import as_int_list, json_value, match_ratio, print_block, render_plaintext, write_json_evidence, zero_positions

def test_as_int_list_accepts_plain_and_numpy_values() -> None:
    assert as_int_list([1, '2', 3]) == [1, 2, 3]
    assert as_int_list(np.asarray([4, 5], dtype=np.uint8)) == [4, 5]

def test_zero_positions_returns_ciphertext_zero_indices() -> None:
    assert zero_positions([0, 3, 0, 4, 5, 0]) == [0, 2, 5]

def test_match_ratio_uses_longer_length_as_denominator() -> None:
    assert match_ratio([1, 2, 3], [1, 9, 3]) == 2 / 3
    assert match_ratio([1, 2], [1, 2, 3, 4]) == 0.5

def test_json_value_summarizes_large_lists_and_arrays() -> None:
    assert json_value(list(range(5)), max_list=3) == {'type': 'list', 'length': 5, 'preview': [0, 1, 2]}
    assert json_value(np.asarray([[1, 2], [3, 4]], dtype=np.uint8)) == {'type': 'ndarray', 'shape': [2, 2], 'preview': [1, 2, 3, 4]}

def test_print_block_formats_begin_fields_and_end(capsys) -> None:
    print_block('TEST_BLOCK', [('a', 1), ('b', [2, 3])])
    out = capsys.readouterr().out
    assert 'TEST_BLOCK_BEGIN' in out
    assert 'a: 1' in out
    assert 'b: [2, 3]' in out
    assert 'TEST_BLOCK_END' in out

def test_render_plaintext_on_tiny_sequence() -> None:
    latin, runes = render_plaintext([24, 9], [[0, 2], [1, 2]])
    assert latin == 'AN'
    assert runes

def test_write_json_evidence(tmp_path) -> None:
    path = tmp_path / 'evidence.json'
    write_json_evidence(path, {'b': [1, 2], 'a': 'ok'})
    assert json.loads(path.read_text(encoding='utf-8')) == {'a': 'ok', 'b': [1, 2]}
