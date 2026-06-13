from __future__ import annotations

import pytest

from rune_decrypter_prime.data.liber_primus.lp_registry import LPPageRef
from rune_decrypter_prime.data.liber_primus.lp_ui_parse import parse_page_token


pytestmark = pytest.mark.tier_a


def test_parse_canon_jpg_token() -> None:
    assert parse_page_token("54.jpg") == LPPageRef.canon_page(54)


def test_parse_canon_number_token() -> None:
    assert parse_page_token("54") == LPPageRef.canon_page(54)


def test_parse_bound_page_token() -> None:
    assert parse_page_token("page 54") == LPPageRef.bound_book_page(54)
    assert parse_page_token("p54") == LPPageRef.bound_book_page(54)


def test_parse_page_token_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        parse_page_token("canon:54")
