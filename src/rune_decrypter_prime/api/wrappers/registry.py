from __future__ import annotations

from typing import Optional, Sequence, Tuple, Union
import numpy as np

from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.core.types import Device, Direction, KeyOpsFamily
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
    interruptors: Optional[object],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
) -> CipherConfig:
    if interruptors is not None and any(
        x is not None for x in (interruptors_exact, interruptors_pool, interruptors_max)
    ):
        raise ValueError("interruptors config cannot be combined with interruptors_exact/pool/max")
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
            interruptors=interruptors,
            interruptors_exact=interruptors_exact,
            interruptors_pool=interruptors_pool,
            interruptors_max=interruptors_max,
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
            interruptors=interruptors,
            interruptors_exact=interruptors_exact,
            interruptors_pool=interruptors_pool,
            interruptors_max=interruptors_max,
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
    interruptors: Optional[object],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
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
        interruptors_cfg=interruptors,
        interruptors_exact=None if interruptors_exact is None else list(interruptors_exact),
        interruptors_pool=None if interruptors_pool is None else list(interruptors_pool),
        interruptors_max=None if interruptors_max is None else int(interruptors_max),
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
    interruptors: Optional[object],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
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
        interruptors=interruptors,
        interruptors_exact=interruptors_exact,
        interruptors_pool=interruptors_pool,
        interruptors_max=interruptors_max,
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
    interruptors: Optional[object],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
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
        interruptors_cfg=interruptors,
        interruptors_exact=None if interruptors_exact is None else list(interruptors_exact),
        interruptors_pool=None if interruptors_pool is None else list(interruptors_pool),
        interruptors_max=None if interruptors_max is None else int(interruptors_max),
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
    interruptors: Optional[object],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
) -> CipherConfig:
    key_spec = expect_key_plan(key, "perm", "Columnar requires KeySpec.permutation(len=cols)")
    cols = int(key_spec.params.get("len", 0) or 0)
    if cols <= 1:
        raise ValueError("Columnar requires permutation len >= 2")
    if cols > 255:
        raise ValueError("Columnar requires permutation len <= 255 (uint8 key limit)")
    return CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=cols,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="columnar",
        interruptors_cfg=interruptors,
        interruptors_exact=None if interruptors_exact is None else list(interruptors_exact),
        interruptors_pool=None if interruptors_pool is None else list(interruptors_pool),
        interruptors_max=None if interruptors_max is None else int(interruptors_max),
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
    interruptors: Optional[object],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
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
        interruptors_cfg=interruptors,
        interruptors_exact=None if interruptors_exact is None else list(interruptors_exact),
        interruptors_pool=None if interruptors_pool is None else list(interruptors_pool),
        interruptors_max=None if interruptors_max is None else int(interruptors_max),
    )


def _build_periodic_substitution_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
    interruptors: Optional[object],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
) -> CipherConfig:
    key_spec = expect_key_plan(
        key,
        "periodic_structured",
        "Periodic substitution requires KeySpec.periodic_substitution(...)",
    )
    period = int(key_spec.params.get("period", 0) or 0)
    columns = key_spec.params.get("columns", None)
    if columns not in (None, 0):
        raise ValueError("Periodic substitution does not accept columns (use periodic_columnar)")
    alphabet_size = int(key_spec.params.get("alphabet_size", getattr(cipher, "N", 29)) or 29)
    if period <= 0:
        raise ValueError("Periodic substitution requires period >= 1")
    if alphabet_size <= 0:
        raise ValueError("Periodic substitution requires alphabet_size >= 1")

    key_length = int(period * alphabet_size)
    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=key_length,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="periodic_substitution",
        interruptors_cfg=interruptors,
        interruptors_exact=None if interruptors_exact is None else list(interruptors_exact),
        interruptors_pool=None if interruptors_pool is None else list(interruptors_pool),
        interruptors_max=None if interruptors_max is None else int(interruptors_max),
    )
    cfg.keyops_family = KeyOpsFamily.MATRIX
    cfg.keyops_hints = {"period": int(period), "A": int(alphabet_size)}
    cfg.period = int(period)
    cfg.alphabet_size = int(alphabet_size)
    return cfg


def _build_periodic_columnar_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
    interruptors: Optional[object],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
) -> CipherConfig:
    key_spec = expect_key_plan(
        key,
        "periodic_structured",
        "Periodic columnar requires KeySpec.periodic_columnar(...)",
    )
    period = int(key_spec.params.get("period", 0) or 0)
    columns = int(key_spec.params.get("columns", 0) or 0)
    alphabet_size = int(key_spec.params.get("alphabet_size", getattr(cipher, "N", 29)) or 29)
    if period <= 0:
        raise ValueError("Periodic columnar requires period >= 1")
    if columns <= 0:
        raise ValueError("Periodic columnar requires columns >= 1")
    if columns > 255:
        raise ValueError("Periodic columnar requires columns <= 255 (uint8 column limit)")
    if alphabet_size <= 0:
        raise ValueError("Periodic columnar requires alphabet_size >= 1")

    order = (getattr(cipher, "extra", {}) or {}).get("order", "sub_then_col")
    key_length = int(period * alphabet_size + columns)
    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=key_length,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="periodic_columnar",
        interruptors_cfg=interruptors,
        interruptors_exact=None if interruptors_exact is None else list(interruptors_exact),
        interruptors_pool=None if interruptors_pool is None else list(interruptors_pool),
        interruptors_max=None if interruptors_max is None else int(interruptors_max),
        order=str(order or "sub_then_col"),
    )
    cfg.keyops_family = KeyOpsFamily.MATRIX
    cfg.keyops_hints = {"period": int(period), "A": int(alphabet_size), "columns": int(columns)}
    cfg.period = int(period)
    cfg.columns = int(columns)
    cfg.alphabet_size = int(alphabet_size)
    return cfg

def _build_hill_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
    interruptors: Optional[object],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
) -> CipherConfig:
    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=2,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="hill",
        interruptors_cfg=interruptors,
        interruptors_exact=None if interruptors_exact is None else list(interruptors_exact),
        interruptors_pool=None if interruptors_pool is None else list(interruptors_pool),
        interruptors_max=None if interruptors_max is None else int(interruptors_max),
    )
    setattr(cfg, "text_transposition", "ltr")
    return cfg


def _build_railfence_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
    interruptors: Optional[object],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
) -> CipherConfig:
    key_spec = expect_key_plan(key, "scalar", "Railfence requires KeySpec.scalar(max_val=...)")
    extras = getattr(cipher, "extra", {}) or {}

    min_rails = max(2, int(extras.get("min_rails", 2)))
    max_hint = extras.get("max_rails")
    if max_hint is None:
        max_hint = key_spec.params.get("max_val", min_rails)
    max_rails = max(min_rails, int(max_hint))

    rails_fixed = extras.get("rails")
    if rails_fixed is not None:
        rails_fixed = int(rails_fixed)
        min_rails = max_rails = max(min_rails, rails_fixed)

    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=1,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="railfence",
        interruptors_cfg=interruptors,
        interruptors_exact=None if interruptors_exact is None else list(interruptors_exact),
        interruptors_pool=None if interruptors_pool is None else list(interruptors_pool),
        interruptors_max=None if interruptors_max is None else int(interruptors_max),
    )
    setattr(cfg, "min_rails", min_rails)
    setattr(cfg, "max_rails", max_rails)
    setattr(cfg, "rails_fixed", rails_fixed)
    return cfg


def _build_autokey_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
    interruptors: Optional[object],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
) -> CipherConfig:
    key_spec = expect_key_plan(key, "repeat", "Autokey requires KeySpec.repeat(len=seed_len)")
    seed_len = int(key_spec.params.get("len", 0) or 0)
    extras = getattr(cipher, "extra", {}) or {}
    if seed_len <= 0:
        seed_len = int(extras.get("seed_length", 0) or 0)
    if seed_len <= 0:
        raise ValueError("Autokey requires a positive seed length")
    alphabet = int(extras.get("alphabet_size", getattr(cipher, "N", 29)) or 29)

    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=seed_len,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="autokey",
        interruptors_cfg=interruptors,
        interruptors_exact=None if interruptors_exact is None else list(interruptors_exact),
        interruptors_pool=None if interruptors_pool is None else list(interruptors_pool),
        interruptors_max=None if interruptors_max is None else int(interruptors_max),
    )
    setattr(cfg, "seed_length", seed_len)
    setattr(cfg, "alphabet_size", alphabet)
    return cfg


_WRAPPER_BUILDERS = {
    "vigenere": _build_vigenere_wrapper,
    "columnar": _build_columnar_wrapper,
    "substitution": _build_substitution_wrapper,
    "periodic_substitution": _build_periodic_substitution_wrapper,
    "periodic_columnar": _build_periodic_columnar_wrapper,
    "hill": _build_hill_wrapper,
    "hill2x2": _build_hill_wrapper,
    "hill-2x2": _build_hill_wrapper,
    "railfence": _build_railfence_wrapper,
    "autokey": _build_autokey_wrapper,
}
