# ============================================================
# rune_decrypter_prime/ciphers/vigenere_cipher.py  (unified CPU/GPU)
# ============================================================
from __future__ import annotations
from typing import Iterable, Union
import re
import numpy as np

from rune_decrypter_prime.backends.xp import select_backend
from rune_decrypter_prime.keyops.keyops_vigenere import KeyOpsVigenere
from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin  # transposition/interruptors mixin

A = 29
ArrayU8 = np.ndarray


def _as_u8(a) -> np.ndarray:
    """Coerce to contiguous uint8 array (preserve shape)."""
    return np.asarray(a, dtype=np.uint8, order="C")


def _as_u8_1d(a) -> np.ndarray:
    """Coerce to 1-D contiguous uint8 array."""
    x = np.asarray(a, dtype=np.uint8, order="C")
    return x.reshape(-1)


def _str_has_digits(s: str) -> bool:
    return any(ch.isdigit() for ch in s)


def _parse_int_tokens(s: str) -> list[int]:
    # Accept sequences like "0 1 2", "0,1,2", "0|1|2", etc.
    toks = re.findall(r"-?\d+", s)
    return [int(t) for t in toks]


def _letters_to_indices(s: str) -> list[int]:
    """
    Map A..Z -> 0..25 (mod A=29). Ignore whitespace and soft separators.
    NOTE: This is a convenience for tests only. It does not encode the full runeglish alphabet;
    remaining symbols (26..28) are not produced by letters.
    """
    out: list[int] = []
    for ch in s.upper():
        if "A" <= ch <= "Z":
            out.append(ord(ch) - ord("A"))
        elif ch in " \t\r\n-_,.":
            continue  # ignore separators/whitespace
        else:
            raise ValueError(f"Unsupported key character {ch!r} for letter-based key")
    return out


def _to_key_u8(key: Union[str, bytes, bytearray, Iterable[int], np.ndarray]) -> np.ndarray:
    """
    Coerce 'key' into a 1-D uint8 array of indices modulo A.

    Accepted forms:
      - sequence of ints (list/tuple/ndarray)
      - string/bytes:
          * if contains digits -> parse integer tokens
          * else -> map letters A..Z -> 0..25
    """
    if isinstance(key, (np.ndarray, list, tuple)):
        arr = np.asarray(key, dtype=np.int64).reshape(-1)
        return (arr % A).astype(np.uint8, copy=False)

    if isinstance(key, (bytes, bytearray)):
        key = key.decode("utf-8", errors="strict")

    if isinstance(key, str):
        key = key.strip()
        if len(key) == 0:
            raise ValueError("Empty key string")
        if _str_has_digits(key):
            vals = _parse_int_tokens(key)
        else:
            vals = _letters_to_indices(key)
        if not vals:
            raise ValueError("Parsed empty key sequence from string")
        arr = np.asarray(vals, dtype=np.int64)
        return (arr % A).astype(np.uint8, copy=False)

    # Fallback: try to interpret as iterable of ints
    try:
        arr = np.fromiter((int(x) for x in key), dtype=np.int64)
        return (arr % A).astype(np.uint8, copy=False)
    except Exception:
        raise TypeError(f"Unsupported key type {type(key)!r}; expected str/bytes/iterable/ndarray")


# ---------- convenience for tests (encrypt in index space) ----------
# TODO: confirm correctness details for base-29 handling in wider contexts.
def encrypt(pt: np.ndarray, key: Union[str, bytes, bytearray, Iterable[int], np.ndarray]) -> np.ndarray:
    """
    Index-space Vigenère encryption (c = p + k mod A), using the cipher module's A.
    This helper is used by tests; the library exports class-based APIs elsewhere.

    Accepts pt as list/tuple/np.ndarray and key as indices or string (A..Z -> 0..25),
    or numeric token string ("0 1 2").
    """
    pt_u8 = _as_u8_1d(pt)
    key_u8 = _to_key_u8(key)
    L, K = int(pt_u8.size), int(key_u8.size)
    if K <= 0:
        raise ValueError("Key length must be positive")
    cols = np.arange(L, dtype=np.int64) % K
    return ((pt_u8.astype(np.int16) + key_u8[cols].astype(np.int16)) % A).astype(np.uint8)


class RuneVigenereCipher(CipherPipelineMixin):
    """
    Canonical Vigenère implementation (mod 29).
    Backend is selected by cfg.device:
      - "cuda*" -> Torch on CUDA (if available), otherwise falls back to NumPy
      - "torch" -> Torch on CPU
      - anything else / None -> NumPy
    """

    A: int = A

    def __init__(self, cfg, *, text_transposition: str = "fwd", key_transposition: str = "fwd"):
        super().__init__(text_transposition=text_transposition, key_transposition=key_transposition)
        K = getattr(cfg, "key_length", None)
        if K is None:
            raise ValueError("Vigenere requires cfg.key_length")
        self.keyops = KeyOpsVigenere(K, self.A)

        self.cfg = cfg

        self._backend = "numpy"
        self._torch = None
        self._torch_device = None

        from typing import Optional
        device_req: Optional[str] = (getattr(cfg, "device", None) or "cpu").lower()

        if device_req.startswith("cuda"):
            # Explicit CUDA request: central selector enforces availability.
            dev_name, _xp = select_backend("cuda")
            if dev_name == "cuda":
                import torch
                self._backend = "torch"
                self._torch = torch
                self._torch_device = torch.device("cuda")
        elif device_req == "torch":
            # Torch requested without forcing CUDA: Torch CPU if available.
            try:
                dev_name, _xp = select_backend("torch")
                import torch
                self._backend = "torch"
                self._torch = torch
                self._torch_device = torch.device("cpu")
            except ImportError:
                # Torch not installed → remain on NumPy backend
                pass

    # ---------- required by CipherPipelineMixin ----------
    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        Input (already transposed/normalised by the pipeline):
          ct_tr  : (L,)   uint8
          keys_tr: (B,K)  uint8
        Output:
          (B,L) uint8 plaintexts
        """
        ct = _as_u8(ct_tr)
        keys = _as_u8(keys_tr)
        B, K = int(keys.shape[0]), int(keys.shape[1])
        L = int(ct.shape[0])

        if self._backend == "torch":
            t = self._torch
            device = self._torch_device

            ct_t = t.from_numpy(ct).to(device=device, dtype=t.uint8, non_blocking=True)      # (L,)
            keys_t = t.from_numpy(keys).to(device=device, dtype=t.uint8, non_blocking=True)  # (B,K)

            cols = t.arange(L, device=device, dtype=t.long) % K                              # (L,)
            ks = keys_t.gather(1, cols.unsqueeze(0).expand(B, L))                            # (B,L)

            # decrypt: p = (c - k) mod A
            pt = (ct_t.unsqueeze(0).to(t.int16) - ks.to(t.int16)) % self.A                   # (B,L)
            pt = pt.to(t.uint8)

            out = pt.detach().cpu().numpy().astype(np.uint8, copy=False)
            return out

        # -------- NumPy path --------
        cols = np.arange(L, dtype=np.int64) % K
        ks = keys[:, cols]                                                                     # (B,L)
        pt = (ct.astype(np.int16)[None, :] - ks.astype(np.int16)) % self.A                    # (B,L)
        return pt.astype(np.uint8, copy=False)

    # Optional convenience for benches
    def decrypt_batch(self, ct_u8: ArrayU8, keys_u8: ArrayU8) -> ArrayU8:
        return self._core_decrypt_batch(ct_u8, keys_u8)

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """
        Vigenère core encryption in transposed/core space (no interruptors here).
          Inputs:
            pt_tr   : (L,)   uint8
            keys_tr : (B,K)  uint8
          Output:
            (B,L) uint8 ciphertexts (core-only, transposed order)
        Phase policy: by core index (columns modulo K).
        """
        pt = _as_u8(pt_tr)
        keys = _as_u8(keys_tr)
        B, K = int(keys.shape[0]), int(keys.shape[1])
        L = int(pt.shape[0])

        if self._backend == "torch":
            t = self._torch
            device = self._torch_device

            pt_t = t.from_numpy(pt).to(device=device, dtype=t.uint8, non_blocking=True)       # (L,)
            keys_t = t.from_numpy(keys).to(device=device, dtype=t.uint8, non_blocking=True)   # (B,K)

            cols = t.arange(L, device=device, dtype=t.long) % K                               # (L,)
            ks = keys_t.gather(1, cols.unsqueeze(0).expand(B, L))                             # (B,L)

            ct = (pt_t.unsqueeze(0).to(t.int16) + ks.to(t.int16)) % self.A                    # (B,L)
            ct = ct.to(t.uint8)
            out = ct.detach().cpu().numpy().astype(np.uint8, copy=False)
            return out

        # NumPy path
        cols = np.arange(L, dtype=np.int64) % K
        ks = keys[:, cols]                                                                       # (B,L)
        ct = (pt.astype(np.int16)[None, :] + ks.astype(np.int16)) % self.A                       # (B,L)
        return ct.astype(np.uint8, copy=False)
