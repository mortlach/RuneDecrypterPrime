# ============================================================
# rune_decrypter_prime/ciphers/bigram_substitution_cipher.py
# ============================================================
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.ciphers.ciphers_pipeline import ArrayU8, CipherPipelineMixin
from rune_decrypter_prime.ciphers.dev.base_keyed_cipher import KeyedCipherBase
from rune_decrypter_prime.ciphers.registry import register_cipher
from rune_decrypter_prime.core.types import KeyOpsFamily


@register_cipher("bigram_sub")
class BigramSubstitutionCipher(CipherPipelineMixin, KeyedCipherBase):
    """
    Generic bigram substitution over the 29-rune alphabet.

    Each plaintext pair (x, y) is mapped to a single code x*29 + y in [0, 840].
    Encryption applies a permutation P over the 841 codes; decryption uses P^{-1}.
    Odd trailing symbols are optionally left unchanged (default) or padded via cfg.pad_value.
    """

    alphabet_size: int = 29
    keyops_family: KeyOpsFamily = KeyOpsFamily.PERMUTATION
    mod_keys: bool = False  # permutation indices should not be reduced modulo alphabet

    def __init__(self, cfg, *, text_transposition: str = "ltr", key_transposition: str = "ltr") -> None:
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", text_transposition),
            key_transposition=getattr(cfg, "key_transposition", key_transposition),
        )
        self.cfg = cfg
        self.alphabet = int(getattr(cfg, "alphabet_size", self.alphabet_size) or self.alphabet_size)
        self.key_length = self.alphabet * self.alphabet
        self.A = self.key_length  # used by CipherPipelineMixin for key modulo
        req_len = getattr(cfg, "key_length", None)
        if req_len not in (None, self.key_length):
            raise ValueError(f"bigram_sub requires key_length={self.key_length}, got {req_len}")
        self._pad_value: Optional[int] = getattr(cfg, "pad_value", None)

        crib_pairs = getattr(cfg, "bigram_crib", None)
        self.crib_ct_codes, self.crib_pt_codes, self.crib_multi = self._parse_and_validate_crib(crib_pairs)
        if self.crib_ct_codes.size or self.crib_multi:
            # Switch to crib-aware key operations when constraints exist.
            self.keyops_family = KeyOpsFamily.CRIBBED_PERMUTATION
            hints = {
                "crib_ct_codes": self.crib_ct_codes.tolist(),
                "crib_pt_codes": self.crib_pt_codes.tolist(),
            }
            if self.crib_multi:
                hints["crib_multi"] = [
                    {
                        "ct": entry["ct"],
                        "pt_codes": entry["pt_codes"],
                        "weights": entry["weights"],
                    }
                    for entry in self.crib_multi
                ]
            self.keyops_hints = hints

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _pairs_to_codes(stream: np.ndarray, alphabet: int) -> Tuple[np.ndarray, Optional[int]]:
        L = int(stream.size)
        if L == 0:
            return np.empty(0, dtype=np.int64), None
        even = (L // 2) * 2
        reshaped = stream[:even].astype(np.int64, copy=False).reshape(-1, 2)
        codes = reshaped[:, 0] * alphabet + reshaped[:, 1]
        trailing = int(stream[-1]) if (L & 1) else None
        return codes, trailing

    @staticmethod
    def _codes_to_pairs(codes: np.ndarray, alphabet: int, trailing: Optional[int]) -> np.ndarray:
        if codes.size == 0:
            if trailing is None:
                return np.empty(0, dtype=np.uint8)
            return np.asarray([trailing], dtype=np.uint8)
        base = codes.astype(np.int64, copy=False).reshape(-1)
        left = (base // alphabet).astype(np.uint8, copy=False)
        right = (base % alphabet).astype(np.uint8, copy=False)
        pair_symbols = left.size * 2
        total = pair_symbols + (1 if trailing is not None else 0)
        out = np.empty(total, dtype=np.uint8)
        pairs_view = out[:pair_symbols]
        pairs_view[0::2] = left
        pairs_view[1::2] = right
        if trailing is not None:
            out[-1] = np.uint8(trailing)
        return out

    # ------------------------------------------------------------------ encrypt/decrypt
    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        text = pt_tr if pt_tr.ndim > 1 else pt_tr[None, :]
        keys = keys_tr if keys_tr.ndim > 1 else keys_tr[None, :]
        B_text, L = text.shape
        B_keys, K = keys.shape
        if K != self.key_length:
            raise ValueError(f"bigram_sub: expected key length {self.key_length}, got {K}")

        batch = max(B_text, B_keys)
        row_len = L
        if (L & 1) and self._pad_value is not None:
            row_len = L + 1
        out = np.empty((batch, row_len), dtype=np.uint8)

        for b in range(batch):
            pt = text[b % B_text]
            key = keys[b % B_keys].astype(np.int64, copy=False)

            trailing = None
            if (pt.size & 1) and self._pad_value is not None:
                pt = np.concatenate([pt, np.asarray([self._pad_value], dtype=np.uint8)], axis=0)

            codes, trailing = self._pairs_to_codes(pt, self.alphabet)
            mapped = key[codes]
            ct = self._codes_to_pairs(mapped, self.alphabet, trailing)
            if ct.size != row_len:
                raise ValueError("Internal error: ciphertext length mismatch")
            out[b] = ct
        return out

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        text = ct_tr if ct_tr.ndim > 1 else ct_tr[None, :]
        keys = keys_tr if keys_tr.ndim > 1 else keys_tr[None, :]
        B_text, L = text.shape
        B_keys, K = keys.shape
        if K != self.key_length:
            raise ValueError(f"bigram_sub: expected key length {self.key_length}, got {K}")

        batch = max(B_text, B_keys)
        out = np.empty((batch, L), dtype=np.uint8)

        inv_cache = np.empty_like(keys)
        base = np.arange(self.key_length, dtype=np.int64)
        for idx in range(B_keys):
            inv_cache[idx][keys[idx].astype(np.int64, copy=False)] = base

        for b in range(batch):
            ct = text[b % B_text]
            inv = inv_cache[b % B_keys].astype(np.int64, copy=False)
            codes, trailing = self._pairs_to_codes(ct, self.alphabet)
            mapped = inv[codes]
            pt = self._codes_to_pairs(mapped, self.alphabet, trailing)
            out[b, :] = 0
            size = min(pt.size, L)
            out[b, :size] = pt[:size]
        return out

    # ------------------------------------------------------------------ crib helper
    def _parse_and_validate_crib(
        self,
        crib: Optional[Iterable[Tuple[int, int]]],
    ) -> Tuple[np.ndarray, np.ndarray, list[dict]]:
        if crib is None:
            return (
                np.empty(0, dtype=np.int64),
                np.empty(0, dtype=np.int64),
                [],
            )

        entries = list(crib)
        if not entries:
            return (
                np.empty(0, dtype=np.int64),
                np.empty(0, dtype=np.int64),
                [],
            )

        K = self.key_length
        pins_ct: list[int] = []
        pins_pt: list[int] = []
        multi_entries: list[dict] = []
        seen_ct: set[int] = set()
        seen_pt: set[int] = set()

        for entry in entries:
            if isinstance(entry, dict):
                ct_code = int(entry.get("cipher"))
                payload = entry
            elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                ct_code = int(entry[0])
                payload = {"plaintext": int(entry[1])}
            else:
                raise ValueError("Crib entries must be dicts or (cipher_code, plaintext_code) tuples")

            if ct_code in seen_ct:
                raise ValueError(f"cipher bigram code {ct_code} appears multiple times in crib")
            if not (0 <= ct_code < K):
                raise ValueError("cipher bigram codes in crib must lie within [0, A*A)")

            if "plaintext" in payload:
                pt_code = int(payload["plaintext"])
                if not (0 <= pt_code < K):
                    raise ValueError("plaintext bigram codes in crib must lie within [0, A*A)")
                if pt_code in seen_pt:
                    raise ValueError(f"plaintext bigram code {pt_code} appears multiple times in crib")
                pins_ct.append(ct_code)
                pins_pt.append(pt_code)
                seen_pt.add(pt_code)
            elif "options" in payload:
                options = payload["options"] or []
                if not isinstance(options, Sequence) or not options:
                    raise ValueError("crib options must include at least one candidate")
                pt_codes = []
                weights = []
                local_seen: set[int] = set()
                for opt in options:
                    val = int(opt.get("plain"))
                    if not (0 <= val < K):
                        raise ValueError("plaintext bigram codes in crib must lie within [0, A*A)")
                    if val in local_seen:
                        continue
                    local_seen.add(val)
                    pt_codes.append(val)
                    weight = opt.get("weight")
                    weights.append(None if weight is None else float(weight))
                if not pt_codes:
                    raise ValueError("crib options must include at least one unique candidate")
                multi_entries.append(
                    {
                        "ct": ct_code,
                        "pt_codes": pt_codes,
                        "weights": weights if any(w is not None for w in weights) else None,
                    }
                )
            else:
                raise ValueError("crib dict entries must include 'plaintext' or 'options'")
            seen_ct.add(ct_code)

        return (
            np.asarray(pins_ct, dtype=np.int64),
            np.asarray(pins_pt, dtype=np.int64),
            multi_entries,
        )

    @classmethod
    def seed_key_from_crib(
        cls,
        ciphertext: Sequence[int],
        crib_idx: Sequence[int],
        *,
        offset: Optional[int] = None,
        alphabet: int = 29,
        rng_seed: Optional[int] = None,
    ) -> np.ndarray:
        rng = np.random.default_rng(rng_seed)
        ct = np.asarray(list(ciphertext), dtype=np.uint8).reshape(-1)
        crib = np.asarray(list(crib_idx), dtype=np.uint8).reshape(-1)
        ct_codes, _ = cls._pairs_to_codes(ct, alphabet)
        crib_codes, _ = cls._pairs_to_codes(crib, alphabet)
        if crib_codes.size == 0 or crib_codes.size > ct_codes.size:
            return rng.permutation(alphabet * alphabet).astype(np.int64)

        offsets = [offset] if offset is not None else range(ct_codes.size - crib_codes.size + 1)
        best_key = None
        best_hits = -1

        for start in offsets:
            mapping: Dict[int, int] = {}
            ok = True
            hits = 0
            for i, code in enumerate(crib_codes):
                c = int(ct_codes[start + i])
                p = int(code)
                prev = mapping.get(c)
                if prev is None:
                    mapping[c] = p
                    hits += 1
                elif prev != p:
                    ok = False
                    break
            if not ok:
                continue

            total = alphabet * alphabet
            key = np.full(total, -1, dtype=np.int64)
            used = np.zeros(total, dtype=bool)
            for src, dst in mapping.items():
                key[src] = dst
                used[dst] = True

            remaining_src = np.flatnonzero(key < 0)
            remaining_dst = np.flatnonzero(~used)
            rng.shuffle(remaining_dst)
            key[remaining_src] = remaining_dst

            if hits > best_hits:
                best_hits = hits
                best_key = key
                if offset is not None:
                    break

        if best_key is None:
            return rng.permutation(alphabet * alphabet).astype(np.int64)
        return best_key
