"""
Why: The public API should be forgiving at the edge: callers can pass Direction enum
      or 'ltr'/'rtl' (legacy 'fwd'/'rev' accepted for v1), and get a Direction Enum back.
Proves: api.normalize.normalize_direction exists and canonicalises inputs to Direction,
        matching the v1 plan & name-freeze. Failing here means API drift or missing normaliser.
"""
import pytest

from rune_decrypter_prime.core.types import Direction  # source of truth for Enums
from rune_decrypter_prime.api.normalize import normalize_encoding_dir  # new API boundary


@pytest.mark.parametrize("inp,expect", [
    (Direction.LTR, Direction.LTR),
    (Direction.RTL, Direction.RTL),
    ("ltr", Direction.LTR),
    ("rtl", Direction.RTL),
])
def test_normalize_direction_accepts_enum_and_strings(inp, expect):
    out = normalize_encoding_dir(inp)
    assert isinstance(out, Direction)
    assert out is expect


@pytest.mark.parametrize("bad", ["left", "RIGHT", 123, None, "FWD!"])
def test_bad_direction_inputs_raise(bad):
    with pytest.raises(Exception):
        normalize_encoding_dir(bad)
