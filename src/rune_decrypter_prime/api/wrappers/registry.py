from __future__ import annotations

from typing import Optional, Sequence, Tuple, Union
import numpy as np

from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.core.types import Device, Direction
from rune_decrypter_prime.api.api_utils import expect_key_plan, resolve_cipher_kind, resolve_key_length
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec


def build_cipher_config(
    *,
    cipher: CipherSpec,
    key: Union[KeySpec, Tuple[KeySpec, KeySpec]],
    ciphertext: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
    initial_keys: Optional[Sequence[Sequence[int]]],
) -> CipherConfig:
    kind = resolve_cipher_kind(cipher)
    if kind == "wrapper":
        return _build_wrapper_cipher_config(
            cipher=cipher,
            key=key,
            ct=ciphertext,
            wli=wli,
            device=device,
            encoding_dir=encoding_dir,
            initial_text_permutation_indices=initial_text_permutation_indices,
            initial_keys=initial_keys,
        )
    if kind in {"user_map2", "user_map3", "lookup"}:
        return _build_generic_cipher_config(
            cipher=cipher,
            key=key,
            ct=ciphertext,
            wli=wli,
            device=device,
            encoding_dir=encoding_dir,
            initial_text_permutation_indices=initial_text_permutation_indices,
            initial_keys=initial_keys,
        )
    raise ValueError(f"Unknown cipher kind: {cipher.kind}")


def _build_generic_cipher_config(
    *,
    cipher: CipherSpec,
    key: Union[KeySpec, Tuple[KeySpec, KeySpec]],
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
    initial_keys: Optional[Sequence[Sequence[int]]],
) -> CipherConfig:
    key_length = resolve_key_length(key, int(ct.size))
    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=key_length,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name=(cipher.name or cipher.kind),
    )
    setattr(cfg, "spec", cipher)
    if initial_keys is not None:
        cfg.initial_keys = list(initial_keys)
    return cfg


def _build_wrapper_cipher_config(
    *,
    cipher: CipherSpec,
    key: Union[KeySpec, Tuple[KeySpec, KeySpec]],
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
    initial_keys: Optional[Sequence[Sequence[int]]],
) -> CipherConfig:
    if isinstance(key, tuple):
        raise ValueError("Wrapper ciphers expect a single KeySpec, not a tuple")
    if not isinstance(key, KeySpec):
        raise TypeError("Wrapper ciphers require a KeySpec")

    core_name = (cipher.wrapper_core or "").lower()
    builder = _WRAPPER_BUILDERS.get(core_name)
    if builder is None:
        raise NotImplementedError(f"Wrapper core '{cipher.wrapper_core}' not supported.")
    cfg = builder(
        cipher=cipher,
        key=key,
        ct=ct,
        wli=wli,
        device=device,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
    )
    if initial_keys is not None:
        cfg.initial_keys = list(initial_keys)
    return cfg


def _build_vigenere_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
) -> CipherConfig:
    key_spec = expect_key_plan(key, "repeat", "Vigenere requires KeySpec.repeat(len=K)")
    period = int(key_spec.params.get("len", 0) or 0)
    if period <= 0:
        raise ValueError("Vigenere requires repeat key with len>0 (period)")
    return CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=period,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="vigenere",
    )


def _build_columnar_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
) -> CipherConfig:
    key_spec = expect_key_plan(key, "perm", "Columnar requires KeySpec.permutation(len=cols)")
    cols = int(key_spec.params.get("len", 0) or 0)
    if cols <= 1:
        raise ValueError("Columnar requires permutation len >= 2")
    return CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=cols,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="columnar",
    )


def _build_substitution_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
) -> CipherConfig:
    alphabet_size = int(getattr(cipher, "N", 0) or 29)
    return CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=alphabet_size,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="substitution",
    )


def _build_hill_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
) -> CipherConfig:
    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=2,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="hill",
    )
    setattr(cfg, "text_transposition", "ltr")
    return cfg


_WRAPPER_BUILDERS = {
    "vigenere": _build_vigenere_wrapper,
    "columnar": _build_columnar_wrapper,
    "substitution": _build_substitution_wrapper,
    "hill": _build_hill_wrapper,
    "hill2x2": _build_hill_wrapper,
    "hill-2x2": _build_hill_wrapper,
}
