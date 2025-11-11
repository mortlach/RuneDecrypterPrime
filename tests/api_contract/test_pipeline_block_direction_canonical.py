# tests/api_contract/test_pipeline_block_direction_canonical.py
from rune_decrypter_prime.io.telemetry_utils import make_pipeline_block
from rune_decrypter_prime.core.types import Direction

def _mk(min_len=8):
    # minimal args the helper expects
    return dict(
        ciphertext_len=10,
        text_permutation=[0,1,2,3,4,5,6,7,8,9],
    )


def test_pipeline_block_canonicalises_direction_from_enum():
    blk = make_pipeline_block(text_encoding_direction="ltr", **_mk())
    assert blk["text_encoding_direction"] == "ltr"

def test_pipeline_block_canonicalises_direction_from_canonical_string():
    blk = make_pipeline_block(text_encoding_direction="rtl", **_mk())
    assert blk["text_encoding_direction"] == "rtl"
