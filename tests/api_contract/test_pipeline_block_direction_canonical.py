from rdp.telemetry.pipeline import make_pipeline_block

def _mk(min_len=8):
    return dict(ciphertext_len=10, text_permutation=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

def test_pipeline_block_canonicalises_direction_from_enum():
    blk = make_pipeline_block(text_encoding_direction='ltr', **_mk())
    assert blk['text_encoding_direction'] == 'ltr'

def test_pipeline_block_canonicalises_direction_from_canonical_string():
    blk = make_pipeline_block(text_encoding_direction='rtl', **_mk())
    assert blk['text_encoding_direction'] == 'rtl'
