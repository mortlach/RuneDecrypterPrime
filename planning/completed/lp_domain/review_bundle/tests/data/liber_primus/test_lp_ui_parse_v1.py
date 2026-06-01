from rune_decrypter_prime.data.liber_primus.lp_registry_v1 import LPPageRef
from rune_decrypter_prime.data.liber_primus.lp_ui_parse_v1 import parse_page_token


def test_parse_canon_jpg_token() -> None:
    assert parse_page_token('54.jpg') == LPPageRef.canon_page(54)


def test_parse_canon_number_token() -> None:
    assert parse_page_token('54') == LPPageRef.canon_page(54)


def test_parse_bound_page_token() -> None:
    assert parse_page_token('page 54') == LPPageRef.bound_book_page(54)
    assert parse_page_token('p54') == LPPageRef.bound_book_page(54)
