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


def _build_railfence_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
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
    )
    setattr(cfg, "seed_length", seed_len)
    setattr(cfg, "alphabet_size", alphabet)
    return cfg


def _build_bigram_sub_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
) -> CipherConfig:
    key_spec = expect_key_plan(key, "perm", "Bigram substitution requires KeySpec.permutation(len=29*29)")
    length = int(key_spec.params.get("len", 0) or 0)
    alphabet_size = int(getattr(cipher, "alphabet_size", getattr(cipher, "N", 29)) or 29)
    key_len = alphabet_size * alphabet_size
    if length not in (0, key_len):
        raise ValueError(f"Bigram substitution permutation must have length {key_len}")
    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=key_len,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="bigram_sub",
    )
    extras = getattr(cipher, "extra", {}) or {}
    if "pad_value" in extras:
        setattr(cfg, "pad_value", int(extras["pad_value"]))
    crib_codes = extras.get("bigram_crib") or getattr(cipher, "crib", None)
    if crib_codes:
        setattr(cfg, "bigram_crib", crib_codes)
        pins_ct: list[int] = []
        pins_pt: list[int] = []
        multi_entries: list[dict] = []
        for entry in crib_codes:
            if isinstance(entry, dict):
                ct_code = int(entry.get("cipher"))
                if "plaintext" in entry:
                    pins_ct.append(ct_code)
                    pins_pt.append(int(entry["plaintext"]))
                options = entry.get("options")
                if options:
                    pt_codes: list[int] = []
                    weights: list[float | None] = []
                    for opt in options:
                        val = opt.get("plain")
                        if val is None:
                            val = opt.get("value")
                        pt_codes.append(int(val))
                        weights.append(None if opt.get("weight") is None else float(opt.get("weight")))
                    multi_entries.append(
                        {
                            "ct": ct_code,
                            "pt_codes": pt_codes,
                            "weights": weights if any(w is not None for w in weights) else None,
                        }
                    )
            else:
                ct_code, pt_code = entry
                pins_ct.append(int(ct_code))
                pins_pt.append(int(pt_code))
        hints: dict[str, object] = {}
        if pins_ct:
            hints["crib_ct_codes"] = pins_ct
            hints["crib_pt_codes"] = pins_pt
        if multi_entries:
            hints["crib_multi"] = multi_entries
        if hints:
            existing = dict(getattr(cfg, "keyops_hints", {}) or {})
            existing.update(hints)
            setattr(cfg, "keyops_hints", existing)
    active_codes = _active_bigram_codes(ct, alphabet_size=alphabet_size)
    if active_codes:
        existing = dict(getattr(cfg, "keyops_hints", {}) or {})
        existing["active_ct_codes"] = active_codes
        setattr(cfg, "keyops_hints", existing)
    return cfg


def _build_playfair_wrapper(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ct: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device: Device,
    encoding_dir: Direction,
    initial_text_permutation_indices: Optional[Sequence[int]],
) -> CipherConfig:
    key_spec = expect_key_plan(key, "perm", "Playfair requires KeySpec.permutation(len=25)")
    length = int(key_spec.params.get("len", 0) or 0)
    if length not in (0, 25):
        raise ValueError("Playfair permutation length must be 25")
    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=25,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        device=device,
        name="playfair29",
    )
    extras = getattr(cipher, "extra", {}) or {}
    if "filler_idx29" in extras:
        setattr(cfg, "filler_idx29", int(extras["filler_idx29"]))
    return cfg


def _active_bigram_codes(ct: np.ndarray, alphabet_size: int) -> list[int]:
    arr = np.asarray(ct, dtype=np.uint8).reshape(-1)
    limit = (arr.size // 2) * 2
    if limit == 0:
        return []
    pairs = arr[:limit].reshape(-1, 2).astype(np.int64, copy=False)
    codes = pairs[:, 0] * alphabet_size + pairs[:, 1]
    unique = np.unique(codes)
    return unique.astype(int).tolist()


_WRAPPER_BUILDERS = {
    "vigenere": _build_vigenere_wrapper,
    "columnar": _build_columnar_wrapper,
    "substitution": _build_substitution_wrapper,
    "hill": _build_hill_wrapper,
    "hill2x2": _build_hill_wrapper,
    "hill-2x2": _build_hill_wrapper,
    "railfence": _build_railfence_wrapper,
    "autokey": _build_autokey_wrapper,
    "bigram_sub": _build_bigram_sub_wrapper,
    "playfair29": _build_playfair_wrapper,
    "playfair": _build_playfair_wrapper,
}
