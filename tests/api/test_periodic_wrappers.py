import numpy as np

from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
from rune_decrypter_prime.api.wrappers.registry import build_cipher_config
from rune_decrypter_prime.core.types import Device, Direction, KeyOpsFamily


def test_build_periodic_substitution_config():
    cipher = CipherSpec.periodic_substitution(period=3, alphabet_size=29)
    key = KeySpec.periodic_substitution(period=3, alphabet_size=29)
    cfg = build_cipher_config(
        cipher=cipher,
        key=key,
        ciphertext=np.array([0, 1, 2], dtype=np.uint8),
        wli=None,
        device=Device.CPU,
        encoding_dir=Direction.LTR,
        initial_text_permutation_indices=None,
        initial_keys=None,
        interruptors=None,
        interruptors_exact=None,
        interruptors_pool=None,
        interruptors_max=None,
    )
    assert cfg.key_length == 3 * 29
    assert cfg.keyops_family == KeyOpsFamily.MATRIX
    assert cfg.keyops_hints == {"period": 3, "A": 29}


def test_build_periodic_columnar_config():
    cipher = CipherSpec.periodic_columnar(period=2, columns=4, alphabet_size=29, order="col_then_sub")
    key = KeySpec.periodic_columnar(period=2, columns=4, alphabet_size=29)
    cfg = build_cipher_config(
        cipher=cipher,
        key=key,
        ciphertext=np.array([0, 1, 2], dtype=np.uint8),
        wli=None,
        device=Device.CPU,
        encoding_dir=Direction.LTR,
        initial_text_permutation_indices=None,
        initial_keys=None,
        interruptors=None,
        interruptors_exact=None,
        interruptors_pool=None,
        interruptors_max=None,
    )
    assert cfg.key_length == 2 * 29 + 4
    assert cfg.keyops_family == KeyOpsFamily.MATRIX
    assert cfg.keyops_hints == {"period": 2, "A": 29, "columns": 4}
    assert cfg.order == "col_then_sub"
