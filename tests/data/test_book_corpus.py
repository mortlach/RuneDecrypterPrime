from __future__ import annotations
from pathlib import Path
import tomllib
import numpy as np
import pytest
from rdp.core.types import Direction
from rune_decrypter_prime.data.cipher_tests import book_corpus
pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]

def _book() -> str:
    books = book_corpus.available_books()
    assert books
    return books[0]

def test_inventory_exposes_complete_direction_pairs() -> None:
    for book in book_corpus.available_books():
        ltr = book_corpus.load_book(book, Direction.LTR)
        rtl = book_corpus.load_book(book, Direction.RTL)
        assert ltr.book == rtl.book == book
        assert ltr.direction is Direction.LTR
        assert rtl.direction is Direction.RTL
        assert ltr.metadata == rtl.metadata

def test_loader_forces_safe_numpy_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []
    original = book_corpus.np.load

    def checked_load(*args, **kwargs):
        calls.append(kwargs.get('allow_pickle'))
        return original(*args, **kwargs)
    monkeypatch.setattr(book_corpus.np, 'load', checked_load)
    book_corpus.load_book(_book(), Direction.LTR)
    assert calls == [False]

@pytest.mark.parametrize('direction', [Direction.LTR, Direction.RTL])
def test_corpus_is_nose_only_with_consistent_wli(direction: Direction) -> None:
    corpus = book_corpus.load_book(_book(), direction)
    assert corpus.plaintext.dtype == np.uint8
    assert corpus.plaintext.ndim == 1
    assert corpus.wli.dtype == np.uint8
    assert corpus.wli.shape == (len(corpus.plaintext), 2)
    assert int(corpus.plaintext.max()) <= 28
    assert not np.isin(corpus.plaintext, (29, 30)).any()

@pytest.mark.parametrize('direction', [Direction.LTR, Direction.RTL])
def test_passage_is_deterministic_whole_word_and_rebased(direction: Direction) -> None:
    corpus = book_corpus.load_book(_book(), direction)
    first = book_corpus.select_passage(corpus, seed=7123, target_runes=300, tolerance_runes=30)
    repeated = book_corpus.select_passage(corpus, seed=7123, target_runes=300, tolerance_runes=30)
    assert first.book == corpus.book
    assert first.direction is direction
    assert 270 <= len(first.plaintext) <= 330
    assert len(first.plaintext) == len(first.wli)
    assert int(first.wli[0, 0]) == 0
    assert int(first.wli[-1, 0]) + 1 == int(first.wli[-1, 1])
    book_corpus._validate_wli(first.plaintext, first.wli)
    np.testing.assert_array_equal(first.plaintext, repeated.plaintext)
    np.testing.assert_array_equal(first.wli, repeated.wli)

def test_distinct_directions_are_not_reinterpreted_at_load_time() -> None:
    ltr = book_corpus.load_book(_book(), Direction.LTR)
    rtl = book_corpus.load_book(_book(), Direction.RTL)
    assert ltr.direction is not rtl.direction
    assert not np.array_equal(ltr.plaintext, rtl.plaintext)

def test_invalid_wli_is_rejected_clearly() -> None:
    plaintext = np.asarray([1, 2], dtype=np.uint8)
    invalid = np.asarray([[0, 2], [0, 2]], dtype=np.uint8)
    with pytest.raises(ValueError, match='word ends are inconsistent'):
        book_corpus._validate_wli(plaintext, invalid)

def test_passage_selection_enforces_requested_tolerance() -> None:
    plaintext = np.arange(6, dtype=np.uint8)
    wli = np.asarray([[0, 3], [1, 3], [2, 3], [0, 3], [1, 3], [2, 3]], dtype=np.uint8)
    corpus = book_corpus.BookCorpus('synthetic', Direction.LTR, plaintext, wli, {'book_id': 'synthetic'})
    with pytest.raises(ValueError, match='no whole-word passage lies within'):
        book_corpus.select_passage(corpus, seed=1, target_runes=4, tolerance_runes=0)

def test_book_corpus_has_a_narrow_package_data_allowlist() -> None:
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    patterns = project['tool']['setuptools']['package-data']['rune_decrypter_prime']
    assert patterns == ['data/cipher_tests/books/*.npz', 'data/cipher_tests/books/*.json']
