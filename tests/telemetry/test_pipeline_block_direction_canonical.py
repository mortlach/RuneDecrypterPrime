import pytest
from rune_decrypter_prime.telemetry.pipeline import make_pipeline_block
from rune_decrypter_prime.core.types import Direction

pytestmark = pytest.mark.tier_a


def _mk(min_len=8):
    return dict(ciphertext_len=min_len, text_permutation=None)


def test_pipeline_block_canonicalises_direction_from_canonical_string():
    blk = make_pipeline_block(text_encoding_direction=Direction.RTL, **_mk())
    assert blk["text_encoding_direction"] == Direction.RTL.value


def test_pipeline_block_canonicalises_direction_from_legacy_alias():
    blk = make_pipeline_block(text_encoding_direction=Direction.LTR, **_mk())
    assert blk["text_encoding_direction"] == Direction.LTR.value
