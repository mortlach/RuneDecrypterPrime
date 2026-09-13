import re
import pytest
from rdp.telemetry.pipeline import make_pipeline_block
pytestmark = pytest.mark.tier_a
HEX32 = re.compile('^[0-9a-f]{32}$')

def test_make_pipeline_block_with_and_without_itp():
    n = 21
    block_none = make_pipeline_block(text_encoding_direction='ltr', ciphertext_len=n, text_permutation=None)
    assert block_none['text_encoding_direction'] in ('ltr', 'rtl')
    ip_none = block_none['input_permutation']
    assert ip_none['kind'] == 'none'
    assert ip_none['length'] == n
    assert HEX32.match(ip_none['hash'])
    perm = list(range(n))[::-1]
    block_custom = make_pipeline_block(text_encoding_direction='ltr', ciphertext_len=n, text_permutation=perm)
    ip_custom = block_custom['input_permutation']
    assert ip_custom['kind'] == 'custom'
    assert ip_custom['length'] == n
    assert HEX32.match(ip_custom['hash'])
    assert ip_custom['hash'] != ip_none['hash']
