import rdp.api.normalize
import pytest
from rdp.core.types import Direction

@pytest.mark.parametrize('inp,expected', [('ltr', Direction.LTR), ('rtl', Direction.RTL), (Direction.LTR, Direction.LTR), (Direction.RTL, Direction.RTL)])
def test_normalize_direction_accepts_string_or_enum(inp, expected):
    assert rdp.api.normalize.normalize_encoding_dir(inp) is expected
