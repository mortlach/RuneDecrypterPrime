import pytest

from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.ciphers.columnar_transposition_cipher import ColumnarTranspositionCipher


def test_columnar_key_length_limit():
    cfg = CipherConfig(
        ciphertext=[0],
        wli_data=[],
        key_length=256,
        name="columnar",
    )
    with pytest.raises(ValueError):
        ColumnarTranspositionCipher(cfg)
