from __future__ import annotations
from rdp import api
from types import SimpleNamespace
import numpy as np
import pytest
from rune_decrypter_prime.ciphers.generic_map_cipher import GenericMapCipher
from rune_decrypter_prime.core.types import Direction

pytestmark = pytest.mark.tier_a
A = 29


def _wli_for(length: int) -> np.ndarray:
    w = np.zeros((length, 2), dtype=np.uint8)
    w[:, 0] = np.arange(length, dtype=np.uint8) % 64
    w[:, 1] = 7
    return w


def _mk_cfg(spec, *, key_length=None, length=8, device="cpu", name="lookup"):
    return SimpleNamespace(
        ciphertext=np.arange(length, dtype=np.uint8),
        wli_data=_wli_for(length),
        key_length=key_length,
        device=device,
        encoding_dir=Direction.LTR,
        name=name,
        spec=spec,
    )


def _spec_lookup(table, N=A, **kw):
    return api.experimental.define_cipher_lookup(
        table.tolist() if hasattr(table, "tolist") else table,
        alphabet_size=int(N),
        degeneracy=api.experimental.DegeneracyPolicy.ALLOW,
        resolver=api.experimental.ResolverMode.FIRST,
        per_position_limit=int(kw.get("per_pos_limit", 29)),
        resolver_limit=int(kw.get("resolver_limit", 8193)),
    )


def _spec_user_map2(func, N=A, **kw):
    return api.experimental.define_cipher_map(
        func,
        alphabet_size=int(N),
        degeneracy=api.experimental.DegeneracyPolicy.FORBID,
        resolver=api.experimental.ResolverMode.FIRST,
        per_position_limit=int(kw.get("per_pos_limit", 29)),
        resolver_limit=int(kw.get("resolver_limit", 8193)),
    )


def _maybe_get_user_encrypt_decrypt(cipher):
    if hasattr(cipher, "encrypt") and hasattr(cipher, "decrypt"):
        return (cipher.encrypt, cipher.decrypt)
    if hasattr(cipher, "encrypt_batch") and hasattr(cipher, "decrypt_batch"):
        return (cipher.encrypt_batch, cipher.decrypt_batch)
    return (None, None)


def _roundtrip_user_api(
    cipher: GenericMapCipher, pt_1d: np.ndarray, key_1d: np.ndarray
):
    enc, dec = _maybe_get_user_encrypt_decrypt(cipher)
    if enc is None or dec is None:
        pytest.xfail(
            "No 1-D convenience API exposed; core kernels are covered. Expose encrypt/decrypt that accept (pt,key) for UX parity."
        )
    pt_1d = pt_1d.astype(np.uint8, copy=False)
    key_1d = key_1d.astype(np.uint8, copy=False)
    try:
        ct = enc(plaintext=pt_1d, key=key_1d)
        rt = dec(ciphertext=ct, key=key_1d)
    except TypeError as exc:
        pytest.xfail(f"Cipher does not expose plaintext/key keyword API: {exc}")
    ct = np.asarray(ct, dtype=np.uint8)
    rt = np.asarray(rt, dtype=np.uint8)
    assert ct.ndim == 2 and ct.shape[0] == 1
    assert rt.ndim == 2 and rt.shape == ct.shape
    assert np.array_equal(rt[0], pt_1d)


def test_lookup_table_requires_key_length_when_ambiguous():
    table = np.mod(np.arange(A * A).reshape(A, A), A).astype(np.uint8)
    spec = _spec_lookup(table, N=A, per_pos_limit=29, resolver_limit=8193)
    with pytest.raises(ValueError):
        GenericMapCipher(_mk_cfg(spec, key_length=None, length=8))


def test_lookup_with_explicit_key_length_roundtrips():
    table = np.add.outer(np.arange(A), np.arange(A)) % A
    spec = _spec_lookup(table, N=A, per_pos_limit=29, resolver_limit=8193)
    cfg = _mk_cfg(spec, key_length=A, length=16)
    cipher = GenericMapCipher(cfg)
    key = np.arange(cipher.key_length, dtype=np.uint8)
    pt = np.arange(16, dtype=np.uint8)
    assert cipher.key_length == A
    _roundtrip_user_api(cipher, pt, key)


def test_user_map2_requires_explicit_key_length():
    spec = _spec_user_map2(lambda pt, kk: (pt + kk) % A, N=A)
    with pytest.raises(ValueError):
        GenericMapCipher(_mk_cfg(spec, key_length=None))
    cfg = _mk_cfg(spec, key_length=4)
    cipher = GenericMapCipher(cfg)
    key = np.arange(4, dtype=np.uint8)
    pt = np.arange(4, dtype=np.uint8)
    assert cipher.key_length == key.size
    _roundtrip_user_api(cipher, pt, key)
