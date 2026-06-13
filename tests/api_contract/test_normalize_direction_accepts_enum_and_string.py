# tests/api_contract/test_core_normalize_direction_accepts_enum_and_string.py
import pytest
from rune_decrypter_prime.api.normalize import normalize_encoding_dir
from rune_decrypter_prime.core.types import Direction

@pytest.mark.parametrize("inp,expected", [
    ("ltr", Direction.LTR),
    ("rtl", Direction.RTL),
    (Direction.LTR, Direction.LTR),
    (Direction.RTL, Direction.RTL),
    # v1-compat aliases (accepted at API edge, never bubble into core)
])
def test_normalize_direction_accepts_string_or_enum(inp, expected):
    out = normalize_encoding_dir(inp)
    assert out is expected
