from __future__ import annotations
import json
from types import SimpleNamespace
import numpy as np
from solving.solve_output import as_int_list, collect_solver_attempt, json_value, match_ratio, print_block, print_final_result, render_plaintext, write_json_evidence, zero_positions

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
    assert latin == 'A·N'
    assert runes

def test_write_json_evidence(tmp_path) -> None:
    path = tmp_path / 'evidence.json'
    write_json_evidence(path, {'b': [1, 2], 'a': 'ok'})
    assert json.loads(path.read_text(encoding='utf-8')) == {'a': 'ok', 'b': [1, 2]}


def test_write_json_evidence_keeps_frozen_plaintext_arrays_lossless(tmp_path) -> None:
    path = tmp_path / 'evidence.json'
    indices = list(range(45))
    wli = [[index, 45] for index in range(45)]
    write_json_evidence(
        path,
        {
            'final': {
                'plaintext_indices': indices,
                'word_length_information': wli,
                'ordinary_diagnostic': indices,
            }
        },
    )
    saved = json.loads(path.read_text(encoding='utf-8'))['final']
    assert saved['plaintext_indices'] == indices
    assert saved['word_length_information'] == wli
    assert saved['ordinary_diagnostic']['length'] == 45


def test_collect_solver_attempt_accepts_canonical_public_result_fields() -> None:
    result = SimpleNamespace(
        plaintext_indices=(1, 2, 3),
        plaintext_rune_latin="F·U·TH·O·R·C",
        plaintext_runes="ᚠᚢᚦᚩᚱᚳ",
        key=(7, 11),
        score=2.5,
        solver_report=None,
    )
    record = collect_solver_attempt(
        result=result,
        solver_variant="test",
        scorer_variant="test",
        key_length=2,
        reference_idx=(1, 2, 3),
        ciphertext_length=3,
        wli=((0, 3), (1, 3), (2, 3)),
    )
    assert record["match_ratio"] == 1.0
    assert record["plaintext_rune_count"] == 3
    assert record["plaintext_indices"] == [1, 2, 3]
    assert record["word_length_information"] == [[0, 3], [1, 3], [2, 3]]
    assert record["plaintext_rune_latin"] == "F·U·TH·O·R·C"
    assert record["status"] == "solved"
    assert not {"plaintext_idx_length", "plaintext_latin", "wli_length"} & record.keys()


def test_final_result_uses_consistent_solved_output_fields(capsys) -> None:
    print_final_result(
        block_name="TEST_FINAL_RESULT",
        source_label="source",
        resolved_source_label="resolved",
        main_page_start=1,
        main_page_end=1,
        ciphertext_length=2,
        wli_length=2,
        recipe="recipe.test",
        cipher_family="test",
        method="test",
        key_or_params=None,
        match_ratio=1.0,
        status="solved",
        acceptance_rule="exact",
        plaintext_latin="A·N",
        plaintext_runes="ᚪᚾ",
    )
    out = capsys.readouterr().out
    assert "plaintext_rune_count: 2" in out
    assert "word_length_information_length: 2" in out
    assert "plaintext_rune_latin:\nA·N" in out
    assert "plaintext_runes:\nᚪᚾ" in out
    assert "plaintext_latin:" not in out
    assert "wli_length:" not in out
