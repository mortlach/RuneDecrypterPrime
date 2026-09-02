from rdp import api
from rdp.core.config.cipher import materialize_cipher_config
from rdp.core.types import KeyOpsFamily


def _cfg(cipher: api.CipherSpec, key: api.KeySpec):
    return materialize_cipher_config(
        cipher=cipher,
        key_space=key,
        ciphertext=(0, 1, 2),
        word_lengths=None,
        compute_device=api.ComputeDevice.CPU,
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
    )

def test_build_periodic_substitution_config():
    cipher = api.CipherSpec.periodic_substitution(period=3, alphabet_size=29)
    key = api.KeySpec.periodic_substitution(period=3, alphabet_size=29)
    cfg = _cfg(cipher, key)
    assert cfg.key_length == 3 * 29
    assert cfg.keyops_family == KeyOpsFamily.MATRIX
    assert cfg.keyops_hints == {'period': 3, 'A': 29}

def test_build_periodic_columnar_config():
    cipher = api.CipherSpec.periodic_columnar(period=2, columns=4, alphabet_size=29, order=api.advanced.PeriodicColumnarOrder.COLUMNAR_THEN_SUBSTITUTION)
    key = api.KeySpec.periodic_columnar(period=2, columns=4, alphabet_size=29)
    cfg = _cfg(cipher, key)
    assert cfg.key_length == 2 * 29 + 4
    assert cfg.keyops_family == KeyOpsFamily.MATRIX
    assert cfg.keyops_hints == {'period': 2, 'A': 29, 'columns': 4}
    assert cfg.order == 'col_then_sub'
