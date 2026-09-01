# ============================================================
# rune_decrypter_prime/ciphers/vigenere_cipher.py  (unified CPU/Torch)
# ============================================================
from __future__ import annotations
from typing import Iterable, Union
import re
import numpy as np

from rdp.backends.xp import select_backend
from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin  # transposition/interruptors mixin
from rune_decrypter_prime.ciphers.base_keyed_cipher import KeyedCipherBase
from rune_decrypter_prime.ciphers.cipher_runtime_registry import register_cipher
from rune_decrypter_prime.core.types import (
    Device,
    Direction,
    KeyOpsFamily,
    ensure_device,
    ensure_direction,
)

A = 29
ArrayU8 = np.ndarray


def _str_has_digits(s: str) -> bool:
    return any(ch.isdigit() for ch in s)


def _parse_int_tokens(s: str) -> list[int]:
    return [int(t) for t in re.findall(r"-?\d+", s)]


def _letters_to_indices(s: str) -> list[int]:
    out: list[int] = []
    for ch in s.upper():
        if "A" <= ch <= "Z":
            out.append(ord(ch) - ord("A"))
        elif ch in " \t\r\n-_,.":
            continue
        else:
            raise ValueError(f"Unsupported key character {ch!r}")
    return out


def _to_key_u8(key: Union[str, bytes, bytearray, Iterable[int], np.ndarray]) -> np.ndarray:
    """
    Coerce 'key' into a 1-D uint8 array of indices modulo A.

    Accepted:
      - sequence of ints (list/tuple/ndarray)
      - string/bytes: digits parsed as ints; otherwise A..Z -> 0..25
    """
    if isinstance(key, (np.ndarray, list, tuple)):
        arr = np.asarray(key, dtype=np.int64).reshape(-1)
        return (arr % A).astype(np.uint8, copy=False)
    if isinstance(key, (bytes, bytearray)):
        key = key.decode("utf-8", errors="strict")
    if isinstance(key, str):
        key = key.strip()
        if not key:
            raise ValueError("Empty key string")
        vals = _parse_int_tokens(key) if _str_has_digits(key) else _letters_to_indices(key)
        arr = np.asarray(vals, dtype=np.int64)
        return (arr % A).astype(np.uint8, copy=False)
    # fallback: iterable of ints
    arr = np.fromiter((int(x) for x in key), dtype=np.int64)
    return (arr % A).astype(np.uint8, copy=False)


# convenience for tests (index space)
def encrypt(pt: np.ndarray, key: Union[str, bytes, bytearray, Iterable[int], np.ndarray]) -> np.ndarray:
    pt_u8 = np.asarray(pt, dtype=np.uint8).reshape(-1)
    key_u8 = _to_key_u8(key)
    L, K = int(pt_u8.size), int(key_u8.size)
    if K <= 0:
        raise ValueError("Key length must be positive")
    cols = np.arange(L, dtype=np.int64) % K
    return ((pt_u8.astype(np.int16) + key_u8[cols].astype(np.int16)) % A).astype(np.uint8)


@register_cipher("vigenere")
class RuneVigenereCipher(CipherPipelineMixin, KeyedCipherBase):
    """
    Canonical Vigenère implementation (mod 29).

    Key model
    ---------
    Vector key of length K, each entry k[i] ∈ [0..A-1]. Phase by column index (pos % K).

    Inputs / Outputs
    ----------------
    _core_decrypt_batch:
      ct_tr  : [L] uint8  (transposed core order)
      keys_tr: [B,K] uint8
      returns: [B,L] uint8 plaintexts

    Notes
    -----
    - Does not normalize keys in decrypt path; assumes keys are valid/uint8.
    - Problem attaches KeyOps based on `keyops_family="vector"` and `key_length`.
    """
    keyops_family: KeyOpsFamily = KeyOpsFamily.VECTOR
    A: int = A

    def __init__(self, cfg, *, text_transposition: Direction | str = Direction.LTR, key_transposition: Direction | str = Direction.LTR):
        text_dir = ensure_direction(getattr(cfg, "text_transposition", text_transposition))
        key_dir = ensure_direction(getattr(cfg, "key_transposition", key_transposition))
        super().__init__(
            text_transposition=text_dir.value,
            key_transposition=key_dir.value,
            initial_text_permutation_indices=getattr(cfg, "initial_text_permutation_indices", None),
        )
        K = getattr(cfg, "key_length", None)
        if K is None:
            raise ValueError("Vigenere requires cfg.key_length")
        self.key_length = int(K)
        self.A = int(getattr(cfg, "alphabet_size", A) or A)
        if self.A < 2:
            raise ValueError("Vigenere alphabet_size must be >= 2")
        self.cfg = cfg
        self.text_direction = text_dir
        self.key_direction = key_dir

        # backend selection
        self.device: Device = ensure_device(getattr(cfg, "device", Device.CPU))
        self._backend = "numpy"
        self._torch = None
        self._torch_device = None

        dev_name, xp = select_backend(self.device.value)
        self._backend = getattr(xp, "backend", "numpy")
        if self._backend == "torch":
            import torch
            device = torch.device(dev_name if "cuda" in dev_name else "cpu")
            self._torch = torch
            self._torch_device = device

        # device_req: Optional[str] = (getattr(cfg, "device", None) or "cpu").lower()
        # if device_req.startswith("cuda"):
        #     dev_name, _xp = select_backend("cuda")
        #     if dev_name == "cuda":
        #         import torch
        #         self._backend = "torch"; self._torch = torch; self._torch_device = torch.device("cuda")
        # elif device_req == "torch":
        #     try:
        #         _dev_name, _xp = select_backend("torch")
        #         import torch
        #         self._backend = "torch"; self._torch = torch; self._torch_device = torch.device("cpu")
        #     except ImportError:
        #         pass

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """Vectorized decrypt: p = (c - k) mod A."""
        ct = self._as_u8(ct_tr, "ct")
        keys = self._as_u8(keys_tr, "keys")
        if keys.ndim == 1:
            keys = keys[None, :]
        B, K = int(keys.shape[0]), int(keys.shape[1])
        L = int(ct.shape[0])

        if self._backend == "torch":
            t = self._torch; device = self._torch_device
            ct_t = t.as_tensor(ct, device=device, dtype=t.uint8).reshape(-1)        # (L,)
            keys_t = t.as_tensor(keys, device=device, dtype=t.uint8)                # (B,K)
            cols = t.arange(L, device=device, dtype=t.long) % K                     # (L,)
            ks = keys_t.gather(1, cols.unsqueeze(0).expand(B, L))                   # (B,L)
            pt = (ct_t.unsqueeze(0).to(t.int16) - ks.to(t.int16)) % self.A          # (B,L)
            return pt.to(t.uint8).cpu().numpy().astype(np.uint8, copy=False)

        cols = np.arange(L, dtype=np.int64) % K
        ks = keys[:, cols]                                                          # (B,L)
        pt = (ct[None, :].astype(np.int16) - ks.astype(np.int16)) % self.A
        return pt.astype(np.uint8, copy=False)

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """Vectorized encrypt: c = (p + k) mod A."""
        pt = self._as_u8(pt_tr, "pt")
        keys = self._as_u8(keys_tr, "keys")
        if keys.ndim == 1:
            keys = keys[None, :]
        B, K = int(keys.shape[0]), int(keys.shape[1])
        L = int(pt.shape[0])

        if self._backend == "torch":
            t = self._torch; device = self._torch_device
            pt_t = t.as_tensor(pt, device=device, dtype=t.uint8).reshape(-1)        # (L,)
            keys_t = t.as_tensor(keys, device=device, dtype=t.uint8)                # (B,K)
            cols = t.arange(L, device=device, dtype=t.long) % K
            ks = keys_t.gather(1, cols.unsqueeze(0).expand(B, L))                   # (B,L)
            ct = (pt_t.unsqueeze(0).to(t.int16) + ks.to(t.int16)) % self.A
            return ct.to(t.uint8).cpu().numpy().astype(np.uint8, copy=False)

        cols = np.arange(L, dtype=np.int64) % K
        ks = keys[:, cols]
        ct = (pt[None, :].astype(np.int16) + ks.astype(np.int16)) % self.A
        return ct.astype(np.uint8, copy=False)
