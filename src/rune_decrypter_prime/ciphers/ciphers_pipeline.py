# ============================================================
# rune_decrypter_prime/ciphers/ciphers_pipeline.py
# ============================================================
"""
Cipher pipeline mixin for canonical encrypt/decrypt orchestration.

Overview
--------
This module provides `CipherPipelineMixin`, a reusable orchestration layer that
standardises the encrypt/decrypt flow across ciphers while delegating the
cipher-specific maths to two abstract, batch-oriented hooks:

    - _core_encrypt_batch(pt_tr, keys_tr) -> (B, L_core_tr) uint8
    - _core_decrypt_batch(ct_tr, keys_tr) -> (B, L_core_tr) uint8

The mixin handles the "plumbing":
    * Input normalisation to uint8.
    * Optional removal and reinsertion of interruptors.
    * Text and key transposition (forward and inverse).
    * Batch shaping for keys ([K] or [B,K]) and outputs ([B, L]).
    * Optional additive invariant checks for debugging.
    * 1-D convenience wrappers (`encrypt_1d` / `decrypt_1d`) built on the batch hooks.

The design favours separation of concerns: cipher implementations focus on
core kernels in a single, transposed "core space", while the mixin ensures
consistent UX, determinism, and telemetry-friendly shapes.

Terminology
-----------
- "core": the text after interruptors are removed and before reinsertion.
- "transposed": the representation used by the transposition manager; the
  core kernels operate in this space for parity across algorithms.
- (B, L): batch dimension B and sequence length L.
- Keys are accepted as [K] or [B,K] and are transposed consistently with text.

This mixin must be combined with a concrete cipher class that implements the
abstract core hooks and exposes required helpers/managers described below.
"""

from __future__ import annotations
from typing import Optional, Sequence
import numpy as np

from rune_decrypter_prime.utils.interrupter import InterruptorManager, InterruptorInfo  # noqa: F401
from rune_decrypter_prime.utils.transposition import TranspositionManager
from rune_decrypter_prime.core.types import KEY_DTYPE

ArrayU8 = np.ndarray


class CipherPipelineMixin:
    """Common encrypt/decrypt pipeline shared by concrete ciphers.

    Responsibilities
    ----------------
    - Normalise inputs (uint8) and support legacy defaults to bound cfg fields.
    - Manage interruptors through `InterruptorManager`.
    - Apply/undo text and key transposition through `TranspositionManager`.
    - Prepare keys for batch use ([K] -> [1,K]).
    - Call cipher-specific core kernels in transposed core space.
    - Reassemble full outputs and enforce shape/consistency.
    - Provide 1-D convenience wrappers built on the batch APIs.

    Requirements on subclasses
    --------------------------
    Subclasses (or composing classes) are expected to provide:
      * `self._as_u8(x, name) -> np.ndarray[uint8]`
      * `self._as_intp(x, name) -> np.ndarray[intp]`
      * `self._intr_mgr: InterruptorManager`
      * `self._trans_mgr: TranspositionManager`
      * `_core_encrypt_batch(pt_tr, keys_tr)`
      * `_core_decrypt_batch(ct_tr, keys_tr)`

    Attributes
    ----------
    A : int
        Alphabet size used for mod reduction of key/material (default 29).
    _additive_debug : bool
        When enabled by additive ciphers, a re-encrypt/re-decrypt invariant is
        checked as a runtime assertion (disabled by default).
    """

    A: int = 29  # alphabet size; override if needed
    mod_keys: bool = True  # apply key % A before passing to core kernels

    def __init__(
        self,
        *,
        text_transposition: str = "ltr",
        key_transposition: str = "ltr",
        initial_text_permutation_indices: Optional[Sequence[int]] = None,
    ) -> None:
        """Initialise pipeline managers and debugging flags.

        Parameters
        ----------
        text_transposition : {"ltr","rtl"}, optional
            Initial text transposition mode to be managed by `TranspositionManager`.
        key_transposition : {"ltr","rtl"}, optional
            Initial key transposition mode to be managed by `TranspositionManager`.

        initial_text_permutation_indices: Explicit permutation over full ciphertext
        token indices (including interruptors). Applied before interruptor removal;
        inverse is applied after reinsertion so plaintext returns in natural order.
        When provided, it overrides text_transposition.

        Notes
        -----
        The `_additive_debug` flag is left disabled by default and should be
        enabled by additive ciphers that want the optional invariant check.
        """
        self._intr_mgr = InterruptorManager()
        self._text_perm_full = None
        self._text_perm_inv = None

        if initial_text_permutation_indices is not None:
            perm = np.asarray(initial_text_permutation_indices, dtype=np.int64).reshape(
                -1
            )
            self._validate_full_perm(perm)
            self._text_perm_full = perm
            inv = np.empty_like(perm)
            inv[perm] = np.arange(perm.size, dtype=np.int64)
            self._text_perm_inv = inv
            # Explicit permutations override named text modes; keep text transposition neutral.
            self._trans_mgr = TranspositionManager(
                text_mode="ltr", key_mode=key_transposition
            )
        else:
            self._trans_mgr = TranspositionManager(
                text_mode=text_transposition, key_mode=key_transposition
            )
        # Only additive ciphers (e.g., Vigenère) should enable this in their __init__
        # self._additive_debug = False

    @property
    def initial_text_permutation_indices(self) -> Optional[list[int]]:
        """Ground truth: explicit ciphertext-index permutation applied in full-text space, or None."""
        if self._text_perm_full is not None:
            return [
                int(x)
                for x in np.asarray(self._text_perm_full, dtype=np.int64).tolist()
            ]
        if getattr(self._trans_mgr, "text_mode", None) != "perm":
            return None
        tp = getattr(self._trans_mgr, "_text_perm", None)
        return (
            None
            if tp is None
            else [int(x) for x in np.asarray(tp, dtype=np.int64).tolist()]
        )

    @staticmethod
    def _validate_full_perm(perm: np.ndarray) -> None:
        if perm.ndim != 1:
            raise ValueError("text_perm must be 1-D")
        n = int(perm.size)
        if n == 0:
            return
        if (perm < 0).any() or (perm >= n).any():
            raise ValueError("text_perm must be a permutation of 0..n-1")
        if np.unique(perm).size != n:
            raise ValueError("text_perm must not contain duplicates")

    def _apply_full_text_perm(self, arr: np.ndarray) -> np.ndarray:
        if self._text_perm_full is None:
            return arr
        if self._text_perm_full.size != arr.size:
            raise ValueError("text_perm must match text length")
        return arr[self._text_perm_full]

    def _undo_full_text_perm(self, arr: np.ndarray) -> np.ndarray:
        if self._text_perm_full is None:
            return arr
        if self._text_perm_inv is None or self._text_perm_inv.size != arr.size:
            raise ValueError("text_perm must match text length")
        return arr[self._text_perm_inv]

    def _map_interrupt_idx_for_perm(self, idx: np.ndarray, length: int) -> np.ndarray:
        if self._text_perm_full is None:
            return idx
        if self._text_perm_inv is None or self._text_perm_full.size != int(length):
            raise ValueError("text_perm must match text length")
        return self._text_perm_inv[idx]

    # ---------- Decrypt (canonical pipeline) ----------
    def decrypt(
        self,
        *,
        ciphertext: Optional[ArrayU8],
        key: ArrayU8,
        interrupt_idx: Optional[ArrayU8] = None,
        interrupt_sym: Optional[ArrayU8] = None,
    ) -> ArrayU8:
        """Decrypt in canonical pipeline form.

        The decrypt flow is:
            1) Normalise inputs (fallback to bound `cfg.ciphertext` if None).
            2) Apply full-text permutation (if provided).
            3) Remove interruptors -> `(ct_core, info)`.
            4) Apply text transposition -> `ct_tr`.
            5) Prepare key to `[B,K]` and apply key transposition -> `keys_tr`.
            6) Delegate to `_core_decrypt_batch(ct_tr, keys_tr)` -> `plains_tr`.
            7) Optionally assert additive invariant for debugging.
            8) Undo text transposition, reinsert interruptors, undo permutation, and stack batches.

        Parameters
        ----------
        ciphertext : (L,) uint8 or None
            Ciphertext indices. When None, a bound `cfg.ciphertext` is used.
        key : (K,) or (B,K) uint8
            Key or a batch of keys. Keys are reduced modulo `A`.
        interrupt_idx : (M,) intp, optional
            Absolute positions to be treated as interruptors and removed/reinserted.
        interrupt_sym : optional
            Kept for signature compatibility; not used by the pipeline.

        Returns
        -------
        np.ndarray uint8 with shape (B, L)
            Batch of plaintext sequences matching the input text length.

        Raises
        ------
        ValueError
            If required inputs are missing, shapes are invalid, or interrupt indices
            are out of bounds or non-unique.
        AssertionError
            If the optional additive invariant is enabled and fails.
        """

        # 1) normalise ciphertext (support legacy defaulting to cfg.ciphertext)
        if ciphertext is None:
            cfg = getattr(self, "cfg", None)
            bound_ct = getattr(cfg, "ciphertext", None) if cfg is not None else None
            if bound_ct is None:
                raise ValueError(
                    "ciphertext is required (no bound cfg.ciphertext present)"
                )
            ct_idx = self._as_u8(bound_ct, "ciphertext")
        else:
            ct_idx = self._as_u8(ciphertext, "ciphertext")

        # 2) optional full-text permutation (applies before interruptor removal)
        ct_full = ct_idx
        ct_idx = self._apply_full_text_perm(ct_idx)

        # 3) remove interruptors (absolute index-space, mapped if permuted)
        if interrupt_idx is not None:
            idx = self._as_intp(interrupt_idx, "interrupt_idx")
            self._validate_interrupt_idx(idx, int(ct_full.size))
            idx = self._map_interrupt_idx_for_perm(idx, int(ct_full.size))
            ct_core, info = self._intr_mgr.remove_from(ct_idx, possible_idx=idx)
        else:
            ct_core, info = self._intr_mgr.remove_from(ct_idx, possible_idx=None)

        # 4) text transposition (core-only)
        ct_tr = self._trans_mgr.apply_text(ct_core)

        # 5) key -> [B,K] and key transposition (core semantics)
        key_arr = self._as_key_dtype(key, "key")
        if getattr(self, "mod_keys", True):
            self._validate_key_range(key_arr)
            key_arr = key_arr % self.A
        if key_arr.ndim == 1:
            key_arr = key_arr[None, :]  # [1,K]
        keys_tr = self._trans_mgr.apply_key(key_arr)
        if keys_tr.size == 0 or keys_tr.shape[0] == 0:
            return np.empty((0, int(ct_idx.size)), dtype=np.uint8)

        # 6) cipher-specific batch decrypt in transposed/core space
        plains_tr = self._core_decrypt_batch(ct_tr, keys_tr)  # [B,L_core_tr] uint8

        # 7) optional invariant (do NOT reimplement maths here)
        if (
            getattr(self, "_additive_debug", False)
            or (
                hasattr(self, "keyops")
                and getattr(self.keyops.caps, "can_additive_invariant", False)
            )
        ) and keys_tr.shape[0] >= 1:
            re_enc = self._core_encrypt_batch(plains_tr[0], keys_tr)[0]
            if not np.array_equal(re_enc, ct_tr):
                raise AssertionError("core re-encrypt mismatch")

        # 8) undo transposition; reinsert interruptors; undo full permutation; stack
        B, _ = plains_tr.shape
        L_full = int(ct_full.size)
        batch_out: list[np.ndarray] = []
        for i in range(B):
            cand_core = self._trans_mgr.undo_text(plains_tr[i])
            cand_full = self._intr_mgr.insert_into(cand_core, info)
            cand_full = self._undo_full_text_perm(cand_full)
            cand_full = np.asarray(cand_full, dtype=np.uint8)
            if cand_full.ndim != 1 or cand_full.size != L_full:
                raise ValueError(
                    f"insert_into returned shape {cand_full.shape}, expected ({L_full},)"
                )
            batch_out.append(cand_full.copy())

        out = np.stack(batch_out, axis=0)  # [B, L_full]
        return out

    # ---------- Encrypt (canonical pipeline; mirror of decrypt) ----------
    def encrypt(
        self,
        *,
        plaintext: ArrayU8,
        key: ArrayU8,
        interrupt_idx: Optional[ArrayU8] = None,
        interrupt_sym: Optional[ArrayU8] = None,
    ) -> ArrayU8:
        """Encrypt in canonical pipeline form (mirror of `decrypt`). Full-text permutations apply before interruptor removal."""
        # 1) normalise
        pt_idx = self._as_u8(plaintext, "plaintext")

        # 2) optional full-text permutation (applies before interruptor removal)
        pt_full = pt_idx
        pt_idx = self._apply_full_text_perm(pt_idx)

        # 3) remove interruptors (absolute index-space, mapped if permuted)
        if interrupt_idx is not None:
            idx = self._as_intp(interrupt_idx, "interrupt_idx")
            self._validate_interrupt_idx(idx, int(pt_full.size))
            idx = self._map_interrupt_idx_for_perm(idx, int(pt_full.size))
            pt_core, info = self._intr_mgr.remove_from(pt_idx, possible_idx=idx)
        else:
            pt_core, info = self._intr_mgr.remove_from(pt_idx, possible_idx=None)

        # 4) text transposition (core-only)
        pt_tr = self._trans_mgr.apply_text(pt_core)

        # 5) key -> [B,K] and key transposition (core semantics)
        key_arr = self._as_key_dtype(key, "key")
        if getattr(self, "mod_keys", True):
            self._validate_key_range(key_arr)
            key_arr = key_arr % self.A
        if key_arr.ndim == 1:
            key_arr = key_arr[None, :]  # [1,K]
        keys_tr = self._trans_mgr.apply_key(key_arr)

        # 6) cipher-specific batch encrypt in transposed/core space
        cts_tr = self._core_encrypt_batch(pt_tr, keys_tr)  # [B,L_core_tr] uint8

        # 7) optional invariant (do NOT reimplement maths here)
        if (
            getattr(self, "_additive_debug", False)
            or (
                hasattr(self, "keyops")
                and getattr(self.keyops.caps, "can_additive_invariant", False)
            )
        ) and keys_tr.shape[0] >= 1:
            recon = self._core_decrypt_batch(cts_tr[0], keys_tr)[0]
            if not np.array_equal(recon, pt_tr):
                raise AssertionError("core re-decrypt mismatch")

        # 8) undo transposition; reinsert interruptors; undo full permutation; stack
        B, _ = cts_tr.shape
        L_full = int(pt_full.size)
        batch_out: list[np.ndarray] = []
        for i in range(B):
            cand_core = self._trans_mgr.undo_text(cts_tr[i])
            cand_full = self._intr_mgr.insert_into(cand_core, info)
            cand_full = self._undo_full_text_perm(cand_full)
            cand_full = np.asarray(cand_full, dtype=np.uint8)
            if cand_full.ndim != 1 or cand_full.size != L_full:
                raise ValueError(
                    f"insert_into returned shape {cand_full.shape}, expected ({L_full},)"
                )
            batch_out.append(cand_full.copy())

        out = np.stack(batch_out, axis=0)  # [B, L_full]
        return out

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """Abstract: cipher-specific batch decrypt in transposed core space."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _core_decrypt_batch(ct_tr, keys_tr)"
        )

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """Abstract: cipher-specific batch encrypt in transposed core space."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _core_encrypt_batch(pt_tr, keys_tr)"
        )

    # ---------- dtype helpers ----------
    @staticmethod
    def _as_u8(x, name: str) -> ArrayU8:
        """Coerce an input to a contiguous `np.uint8` array."""
        arr = x.get() if hasattr(x, "get") else x
        arr = np.asarray(arr, dtype=np.uint8)
        if arr.ndim < 1:
            raise ValueError(f"{name} must be array-like")
        return arr

    @staticmethod
    def _as_key_dtype(x, name: str) -> ArrayU8:
        """Coerce an input to a contiguous `KEY_DTYPE` array (keys only)."""
        arr = x.get() if hasattr(x, "get") else x
        arr = np.asarray(arr, dtype=KEY_DTYPE)
        if arr.ndim < 1:
            raise ValueError(f"{name} must be array-like")
        return arr

    def _validate_key_range(self, key_arr: np.ndarray) -> None:
        """Validate key values are within [0, A) when mod_keys is enabled."""
        if not getattr(self, "mod_keys", True):
            return
        A = getattr(self, "A", None)
        if A is None:
            return
        arr = np.asarray(key_arr)
        if arr.size == 0:
            return
        if np.any(arr < 0) or np.any(arr >= int(A)):
            raise ValueError(
                f"key values must be in [0, {int(A)}) when mod_keys is enabled"
            )

    @staticmethod
    def _as_intp(x, name: str) -> ArrayU8:
        """Coerce an input to a 1-D `np.intp` array."""
        arr = np.asarray(x, dtype=np.intp)
        if arr.ndim != 1:
            raise ValueError(f"{name} must be 1D")
        return arr

    # ---------- utilities ----------
    def _repeat_key_like(self, L: int, key_row: np.ndarray) -> np.ndarray:
        """Tile a single key row to length `L` and truncate."""
        K = int(key_row.shape[0])
        reps = (L + K - 1) // K
        return np.tile(key_row, reps)[:L].astype(KEY_DTYPE)

    def _validate_interrupt_idx(self, idx: np.ndarray, length: int) -> None:
        """Validate interruptor indices (shape, range, uniqueness)."""
        if idx.ndim != 1:
            raise ValueError(f"interrupt_idx must be 1D; got shape {idx.shape}")
        if length < 0:
            raise ValueError("length must be non-negative")
        if (idx < 0).any() or (idx >= length).any():
            raise ValueError(
                f"interrupt_idx contains out-of-range values for length {length}"
            )
        if np.unique(idx).size != idx.size:
            raise ValueError("interrupt_idx contains duplicates")

    def decrypt_single(
        self,
        *,
        ciphertext: np.ndarray | list | tuple,
        key: np.ndarray | list | tuple,
        interrupt_idx: np.ndarray | list | tuple | None = None,
        interrupt_sym: np.ndarray | list | tuple | None = None,
    ) -> np.ndarray:
        """Decrypt a single key against a single ciphertext and return 1-D plaintext."""
        plains = self.decrypt(
            ciphertext=np.asarray(ciphertext, dtype=np.uint8),
            key=self._as_key_dtype(key, "key"),
            interrupt_idx=None
            if interrupt_idx is None
            else np.asarray(interrupt_idx, dtype=np.intp),
            interrupt_sym=None
            if interrupt_sym is None
            else np.asarray(interrupt_sym, dtype=np.uint8),
        )
        return plains[0]

    def encrypt_single(
        self,
        *,
        plaintext: np.ndarray | list | tuple,
        key: np.ndarray | list | tuple,
        interrupt_idx: np.ndarray | list | tuple | None = None,
        interrupt_sym: np.ndarray | list | tuple | None = None,
    ) -> np.ndarray:
        """Encrypt a single key against a single plaintext and return 1-D ciphertext."""
        cts = self.encrypt(
            plaintext=np.asarray(plaintext, dtype=np.uint8),
            key=self._as_key_dtype(key, "key"),
            interrupt_idx=None
            if interrupt_idx is None
            else np.asarray(interrupt_idx, dtype=np.intp),
            interrupt_sym=None
            if interrupt_sym is None
            else np.asarray(interrupt_sym, dtype=np.uint8),
        )
        return cts[0]

    def encrypt_1d(self, plaintext: np.ndarray, key: np.ndarray) -> np.ndarray:
        """Convenience wrapper to encrypt 1-D inputs via the batch core."""
        pt = np.asarray(plaintext, np.uint8)[None, :]
        kk = np.asarray(key, KEY_DTYPE)[None, :]
        return self._core_encrypt_batch(pt, kk)[0]

    def decrypt_1d(self, ciphertext: np.ndarray, key: np.ndarray) -> np.ndarray:
        """Convenience wrapper to decrypt 1-D inputs via the batch core."""
        ct = np.asarray(ciphertext, np.uint8)[None, :]
        kk = self._as_key_dtype(key, "key")[None, :]
        return self._core_decrypt_batch(ct, kk)[0]


#
#
# from __future__ import annotations
# from typing import Optional
# import os
# import numpy as np
#
# from rune_decrypter_prime.utils.interrupter import InterruptorManager, InterruptorInfo  # noqa: F401
# from rune_decrypter_prime.utils.transposition import TranspositionManager
#
# ArrayU8 = np.ndarray
# def _as_u8(a) -> np.ndarray:
#     def _as_u8(a) -> np.ndarray:
#         """Coerce `a` to a contiguous `np.uint8` array.
#
#         This utility is kept for local, internal use where contiguous layout is
#         desired. Prefer the mixin’s `_as_u8` for standardized error messages.
#         """
#     x = np.asarray(a, dtype=np.uint8, order="C")
#     return x
#
# class CipherPipelineMixin:
#     """Common encrypt/decrypt pipeline shared by concrete ciphers.
#
#     Responsibilities
#     ----------------
#     - Normalize inputs (uint8) and support legacy defaults to bound cfg fields.
#     - Manage interruptors through `InterruptorManager`.
#     - Apply/undo text and key transposition through `TranspositionManager`.
#     - Prepare keys for batch use ([K] -> [1,K]).
#     - Call cipher-specific core kernels in transposed core space.
#     - Reassemble full outputs and enforce shape/consistency.
#     - Provide 1-D convenience wrappers built on the batch APIs.
#
#     Requirements on subclasses
#     --------------------------
#     Subclasses (or composing classes) are expected to provide:
#       * `self._as_u8(x, name) -> np.ndarray[uint8]`
#       * `self._as_intp(x, name) -> np.ndarray[intp]`
#       * `self._intr_mgr: InterruptorManager`
#       * `self._trans_mgr: TranspositionManager`
#       * `_core_encrypt_batch(pt_tr, keys_tr)`
#       * `_core_decrypt_batch(ct_tr, keys_tr)`
#
#     Attributes
#     ----------
#     A : int
#         Alphabet size used for mod reduction of key/material (default 29).
#     _additive_debug : bool
#         When enabled by additive ciphers, a re-encrypt/re-decrypt invariant is
#         checked as a runtime assertion (disabled by default).
#     """
#     A: int = 29  # alphabet size; override if needed
#
#     def __init__(self, *, text_transposition: str = "ltr", key_transposition: str = "ltr") -> None:
#         """Initialize pipeline managers and debugging flags.
#
#         Parameters
#         ----------
#         text_transposition : {"ltr","rtl"}, optional
#             Initial text transposition mode to be managed by `TranspositionManager`.
#         key_transposition : {"ltr","rtl"}, optional
#             Initial key transposition mode to be managed by `TranspositionManager`.
#
#         Notes
#         -----
#         The `_additive_debug` flag is left disabled by default and should be
#         enabled by additive ciphers that want the optional invariant check.
#         """
#         self._intr_mgr = InterruptorManager()
#         self._trans_mgr = TranspositionManager(text_mode=text_transposition, key_mode=key_transposition)
#         # Only additive ciphers (e.g., Vigenère) should enable this in their __init__
#         self._additive_debug = False
#
#     # ---------- Decrypt (canonical pipeline) ----------
#     def decrypt(
#             self,
#             *,
#             ciphertext: Optional[ArrayU8],
#             key: ArrayU8,
#             interrupt_idx: Optional[ArrayU8] = None,
#             interrupt_sym: Optional[ArrayU8] = None,
#     ) -> ArrayU8:
#         """Decrypt in canonical pipeline form.
#
#         The decrypt flow is:
#             1) Normalize inputs (fallback to bound `cfg.ciphertext` if None).
#             2) Remove interruptors → `(ct_core, info)`.
#             3) Apply text transposition → `ct_tr`.
#             4) Prepare key to `[B,K]` and apply key transposition → `keys_tr`.
#             5) Delegate to `_core_decrypt_batch(ct_tr, keys_tr)` → `plains_tr`.
#             6) Optionally assert additive invariant for debugging.
#             7) Undo text transposition, reinsert interruptors, and stack batches.
#
#         Parameters
#         ----------
#         ciphertext : (L,) uint8 or None
#             Ciphertext indices. When None, a bound `cfg.ciphertext` is used.
#         key : (K,) or (B,K) uint8
#             Key or a batch of keys. Keys are reduced modulo `A`.
#         interrupt_idx : (M,) intp, optional
#             Absolute positions to be treated as interruptors and removed/reinserted.
#         interrupt_sym : optional
#             Kept for signature compatibility; not used by the pipeline.
#
#         Returns
#         -------
#         np.ndarray uint8 with shape (B, L)
#             Batch of plaintext sequences matching the input text length.
#
#         Raises
#         ------
#         ValueError
#             If required inputs are missing, shapes are invalid, or interrupt indices
#             are out of bounds or non-unique.
#         AssertionError
#             If the optional additive invariant is enabled and fails.
#         """
#
#         # 1) normalize ciphertext (support legacy defaulting to cfg.ciphertext)
#         if ciphertext is None:
#             cfg = getattr(self, "cfg", None)
#             bound_ct = getattr(cfg, "ciphertext", None) if cfg is not None else None
#             if bound_ct is None:
#                 raise ValueError("ciphertext is required (no bound cfg.ciphertext present)")
#             ct_idx = self._as_u8(bound_ct, "ciphertext")
#         else:
#             ct_idx = self._as_u8(ciphertext, "ciphertext")
#
#         # 2) remove interruptors (absolute index-space)
#         if interrupt_idx is not None:
#             idx = self._as_intp(interrupt_idx, "interrupt_idx")
#             self._validate_interrupt_idx(idx, int(ct_idx.size))
#             ct_core, info = self._intr_mgr.remove_from(ct_idx, possible_idx=idx)
#         else:
#             ct_core, info = self._intr_mgr.remove_from(ct_idx, possible_idx=None)
#
#         # 3) text transposition (core-only)
#         ct_tr = self._trans_mgr.apply_text(ct_core)
#
#         # 4) key -> [B,K] and key transposition (core semantics)
#         key_arr = self._as_u8(key, "key") % self.A
#         if key_arr.ndim == 1:
#             key_arr = key_arr[None, :]  # [1,K]
#         keys_tr = self._trans_mgr.apply_key(key_arr)
#
#         # 5) cipher-specific batch decrypt in transposed/core space
#         plains_tr = self._core_decrypt_batch(ct_tr, keys_tr)  # [B,L_core_tr] uint8
#
#         # 6) optional invariant (do NOT reimplement math here)
#         if (getattr(self, "_additive_debug", False) or
#             (hasattr(self, "keyops") and getattr(self.keyops.caps, "can_additive_invariant", False))) \
#                 and keys_tr.shape[0] >= 1:
#             re_enc = self._core_encrypt_batch(plains_tr[0], keys_tr)[0]
#             if not np.array_equal(re_enc, ct_tr):
#                 raise AssertionError("core re-encrypt mismatch")
#
#         # 7) undo transposition; reinsert interruptors; stack
#         B, _ = plains_tr.shape
#         L_full = int(ct_idx.size)
#         batch_out: list[np.ndarray] = []
#         for i in range(B):
#             cand_core = self._trans_mgr.undo_text(plains_tr[i])
#             cand_full = self._intr_mgr.insert_into(cand_core, info)
#             cand_full = np.asarray(cand_full, dtype=np.uint8)
#             if cand_full.ndim != 1 or cand_full.size != L_full:
#                 raise ValueError(f"insert_into returned shape {cand_full.shape}, expected ({L_full},)")
#             batch_out.append(cand_full.copy())
#
#         out = np.stack(batch_out, axis=0)  # [B, L_full]
#         return out
#
#     # ---------- Encrypt (canonical pipeline; mirror of decrypt) ----------
#     def encrypt(
#             self,
#             *,
#             plaintext: ArrayU8,
#             key: ArrayU8,
#             interrupt_idx: Optional[ArrayU8] = None,
#             interrupt_sym: Optional[ArrayU8] = None,
#     ) -> ArrayU8:
#         """Encrypt in canonical pipeline form (mirror of `decrypt`).
#
#         The encrypt flow mirrors `decrypt`:
#             1) Normalize inputs.
#             2) Remove interruptors → `(pt_core, info)`.
#             3) Apply text transposition → `pt_tr`.
#             4) Prepare key to `[B,K]` and apply key transposition → `keys_tr`.
#             5) Delegate to `_core_encrypt_batch(pt_tr, keys_tr)` → `cts_tr`.
#             6) Optionally assert additive invariant for debugging.
#             7) Undo text transposition, reinsert interruptors, and stack batches.
#
#         Parameters
#         ----------
#         plaintext : (L,) uint8
#             Plaintext indices.
#         key : (K,) or (B,K) uint8
#             Key or a batch of keys. Keys are reduced modulo `A`.
#         interrupt_idx : (M,) intp, optional
#             Absolute positions to be treated as interruptors and removed/reinserted.
#         interrupt_sym : optional
#             Kept for signature compatibility; not used by the pipeline.
#
#         Returns
#         -------
#         np.ndarray uint8 with shape (B, L)
#             Batch of ciphertext sequences matching the input text length.
#
#         Raises
#         ------
#         ValueError
#             If input shapes are invalid or interrupt indices are invalid.
#         AssertionError
#             If the optional additive invariant is enabled and fails.
#         """
#
#         # 1) normalize
#         pt_idx = self._as_u8(plaintext, "plaintext")
#
#         # 2) remove interruptors (absolute index-space)
#         if interrupt_idx is not None:
#             idx = self._as_intp(interrupt_idx, "interrupt_idx")
#             self._validate_interrupt_idx(idx, int(pt_idx.size))
#             pt_core, info = self._intr_mgr.remove_from(pt_idx, possible_idx=idx)
#         else:
#             pt_core, info = self._intr_mgr.remove_from(pt_idx, possible_idx=None)
#
#         # 3) text transposition (core-only)
#         pt_tr = self._trans_mgr.apply_text(pt_core)
#
#         # 4) key -> [B,K] and key transposition (core semantics)
#         key_arr = self._as_u8(key, "key") % self.A
#         if key_arr.ndim == 1:
#             key_arr = key_arr[None, :]  # [1,K]
#         keys_tr = self._trans_mgr.apply_key(key_arr)
#
#         # 5) cipher-specific batch encrypt in transposed/core space
#         cts_tr = self._core_encrypt_batch(pt_tr, keys_tr)  # [B,L_core_tr] uint8
#
#         # 6) optional invariant (do NOT reimplement math here)
#         if (getattr(self, "_additive_debug", False) or
#             (hasattr(self, "keyops") and getattr(self.keyops.caps, "can_additive_invariant", False))) \
#                 and keys_tr.shape[0] >= 1:
#             recon = self._core_decrypt_batch(cts_tr[0], keys_tr)[0]
#             if not np.array_equal(recon, pt_tr):
#                 raise AssertionError("core re-decrypt mismatch")
#
#         # 7) undo transposition; reinsert interruptors; stack
#         B, _ = cts_tr.shape
#         L_full = int(pt_idx.size)
#         batch_out: list[np.ndarray] = []
#         for i in range(B):
#             cand_core = self._trans_mgr.undo_text(cts_tr[i])
#             cand_full = self._intr_mgr.insert_into(cand_core, info)
#             cand_full = np.asarray(cand_full, dtype=np.uint8)
#             if cand_full.ndim != 1 or cand_full.size != L_full:
#                 raise ValueError(f"insert_into returned shape {cand_full.shape}, expected ({L_full},)")
#             batch_out.append(cand_full.copy())
#
#         out = np.stack(batch_out, axis=0)  # [B, L_full]
#         return out
#
#     def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
#         """Cipher-specific batch decrypt in transposed core space.
#
#         Parameters
#         ----------
#         ct_tr : (L_core_tr,) or (B, L_core_tr) uint8
#             Ciphertext in transposed, core space. Concrete ciphers may accept
#             either shape but must return a batch output of shape (B, L_core_tr).
#         keys_tr : (B, K) uint8
#             Batch of keys in transposed key space.
#
#         Returns
#         -------
#         np.ndarray uint8 with shape (B, L_core_tr)
#             Decrypted plaintexts in transposed core space.
#
#         Notes
#         -----
#         This is an abstract hook and must be implemented by concrete ciphers.
#         """
#         raise NotImplementedError(
#             f"{self.__class__.__name__} must implement _core_decrypt_batch(ct_tr, keys_tr)"
#         )
#
#     def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
#         """Cipher-specific batch encrypt in transposed core space.
#
#         Parameters
#         ----------
#         pt_tr : (L_core_tr,) or (B, L_core_tr) uint8
#             Plaintext in transposed, core space. Concrete ciphers may accept
#             either shape but must return a batch output of shape (B, L_core_tr).
#         keys_tr : (B, K) uint8
#             Batch of keys in transposed key space.
#
#         Returns
#         -------
#         np.ndarray uint8 with shape (B, L_core_tr)
#             Ciphertexts in transposed core space.
#
#         Notes
#         -----
#         This is an abstract hook and must be implemented by concrete ciphers.
#         """
#         raise NotImplementedError(
#             f"{self.__class__.__name__} must implement _core_encrypt_batch(pt_tr, keys_tr)"
#         )
#
#     # ---------- dtype helpers ----------
#     @staticmethod
#     def _as_u8(x, name: str) -> ArrayU8:
#         """Coerce an input to a contiguous `np.uint8` array.
#
#         Parameters
#         ----------
#         x : array-like
#             Input to coerce.
#         name : str
#             Logical name used in error messages.
#
#         Returns
#         -------
#         np.ndarray uint8
#             The coerced array.
#
#         Raises
#         ------
#         ValueError
#             If the result has no dimensions (not array-like).
#         """
#         arr = np.asarray(x, dtype=np.uint8)
#         if arr.ndim < 1:
#             raise ValueError(f"{name} must be array-like")
#         return arr
#
#     @staticmethod
#     def _as_intp(x, name: str) -> ArrayU8:
#         """Coerce an input to a 1-D `np.intp` array.
#
#         Parameters
#         ----------
#         x : array-like
#             Input to coerce.
#         name : str
#             Logical name used in error messages.
#
#         Returns
#         -------
#         np.ndarray intp with shape (N,)
#
#         Raises
#         ------
#         ValueError
#             If the result is not 1-D.
#         """
#         arr = np.asarray(x, dtype=np.intp)
#         if arr.ndim != 1:
#             raise ValueError(f"{name} must be 1D")
#         return arr
#
#     # ---------- utilities ----------
#     def _repeat_key_like(self, L: int, key_row: np.ndarray) -> np.ndarray:
#         """Tile a single key row to length `L` and truncate.
#
#         Parameters
#         ----------
#         L : int
#             Desired output length.
#         key_row : (K,) uint8
#             Single key to tile.
#
#         Returns
#         -------
#         np.ndarray uint8 with shape (L,)
#             Tiled key values truncated to `L`.
#         """
#         K = int(key_row.shape[0])
#         reps = (L + K - 1) // K
#         return np.tile(key_row, reps)[:L].astype(np.uint8)
#
#     def _validate_interrupt_idx(self, idx: np.ndarray, length: int) -> None:
#         """Validate interruptor indices.
#
#         Contract
#         --------
#         - `idx` must be 1-D.
#         - All values must satisfy `0 <= i < length`.
#         - No duplicates are permitted.
#
#         Parameters
#         ----------
#         idx : (M,) intp
#             Interrupt positions.
#         length : int
#             Target text length used for range checks.
#
#         Raises
#         ------
#         ValueError
#             If shape, range, or uniqueness constraints are violated.
#         """
#         if idx.ndim != 1:
#             raise ValueError(f"interrupt_idx must be 1D; got shape {idx.shape}")
#         if length < 0:
#             raise ValueError("length must be non-negative")
#         if (idx < 0).any() or (idx >= length).any():
#             raise ValueError(f"interrupt_idx contains out-of-range values for length {length}")
#         # exact uniqueness (no duplicates)
#         if np.unique(idx).size != idx.size:
#             raise ValueError("interrupt_idx contains duplicates")
#
#     def encrypt_single(
#             self,
#             *,
#             plaintext: np.ndarray | list | tuple,
#             key: np.ndarray | list | tuple,
#             interrupt_idx: np.ndarray | list | tuple | None = None,
#             interrupt_sym: np.ndarray | list | tuple | None = None,
#     ) -> np.ndarray:
#         """Encrypt a single key against a single plaintext and return 1-D ciphertext.
#
#         Parameters
#         ----------
#         plaintext : (L,) uint8 or sequence
#             Plaintext indices.
#         key : (K,) uint8 or sequence
#             Key values.
#         interrupt_idx : (M,) intp or sequence, optional
#             Absolute positions treated as interruptors.
#         interrupt_sym : optional
#             Reserved for compatibility; unused.
#
#         Returns
#         -------
#         np.ndarray uint8 with shape (L,)
#             Ciphertext indices.
#         """
#         cts = self.encrypt(
#             plaintext=np.asarray(plaintext, dtype=np.uint8),
#             key=np.asarray(key, dtype=np.uint8),
#             interrupt_idx=None if interrupt_idx is None else np.asarray(interrupt_idx, dtype=np.intp),
#             interrupt_sym=None if interrupt_sym is None else np.asarray(interrupt_sym, dtype=np.uint8),
#         )
#         return cts[0]
#
#     def encrypt_1d(self, plaintext: np.ndarray, key: np.ndarray) -> np.ndarray:
#         """Convenience wrapper to encrypt 1-D inputs via the batch core.
#
#         Parameters
#         ----------
#         plaintext : (L,) uint8
#             Plaintext indices.
#         key : (K,) uint8
#             Key values.
#
#         Returns
#         -------
#         np.ndarray uint8 with shape (L,)
#             Ciphertext indices.
#
#         Notes
#         -----
#         This helper reshapes inputs to `[1, ·]`, calls `_core_encrypt_batch`, and
#         returns the first row of the batch result.
#         """
#         pt = np.asarray(plaintext, np.uint8)[None, :]
#         kk = np.asarray(key, np.uint8)[None, :]
#         return self._core_encrypt_batch(pt, kk)[0]
#
#     def decrypt_1d(self, ciphertext: np.ndarray, key: np.ndarray) -> np.ndarray:
#         """Convenience wrapper to decrypt 1-D inputs via the batch core.
#
#         Parameters
#         ----------
#         ciphertext : (L,) uint8
#             Ciphertext indices.
#         key : (K,) uint8
#             Key values.
#
#         Returns
#         -------
#         np.ndarray uint8 with shape (L,)
#             Plaintext indices.
#
#         Notes
#         -----
#         This helper reshapes inputs to `[1, ·]`, calls `_core_decrypt_batch`, and
#         returns the first row of the batch result.
#         """
#         ct = np.asarray(ciphertext, np.uint8)[None, :]
#         kk = np.asarray(key, np.uint8)[None, :]
#         return self._core_decrypt_batch(ct, kk)[0]
#
