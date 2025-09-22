# ============================================================
# rune_decrypter_prime/core/transpositions.py
# Columnar transposition helpers (single/batch); extensible hook
# for other transpositions via cipher config hints.
# ============================================================
from __future__ import annotations
import numpy as np

# ---------------- Columnar transposition helpers ---------------- #

def _columnar_decrypt_single(ct: np.ndarray, perm: np.ndarray) -> np.ndarray:
    """
    Decrypt a columnar-transposed ciphertext given a READ-ORDER permutation `perm` (len K).

    Conventions
    -----------
    • Encryption fills a rows×K matrix row-wise with plaintext, then **reads by columns**
      according to `perm` (read-order). Here we invert that:
      1) Split CT into slices that match the **physical** column lengths.
      2) Assign each slice into the physical column indicated by the **read order** `perm`.
      3) Read the reconstructed matrix row-wise across physical columns 0..K-1.

    Parameters
    ----------
    ct : np.ndarray (uint8) shape [L]
        Ciphertext as integer tokens (0..alphabet_len-1).
    perm : np.ndarray (int) shape [K]
        Read-order permutation (values 0..K-1), length K.

    Returns
    -------
    np.ndarray (uint8) shape [L]
        Recovered plaintext tokens (row-wise order).
    """
    L = int(ct.size)
    K = int(perm.size)
    if K <= 0:
        raise ValueError("Columnar key length must be positive")

    rows = (L + K - 1) // K  # ceil(L/K)
    rem = L % K

    # Column lengths by physical column index (0..K-1)
    if rem == 0:
        col_lens = np.full(K, rows, dtype=np.int64)
    else:
        col_lens = np.full(K, rows - 1, dtype=np.int64)
        col_lens[:rem] = rows

    # Slice CT into columns in the ORDER THEY WERE READ (perm)
    cols = [None] * K
    pos = 0
    for c in perm:
        ln = int(col_lens[int(c)])
        cols[int(c)] = ct[pos: pos + ln]
        pos += ln

    # Reconstruct PT row-wise across physical columns
    pt = np.empty(L, dtype=np.uint8)
    w = 0
    for r in range(rows):
        for c in range(K):
            col = cols[c]
            if r < col.size:
                pt[w] = col[r]
                w += 1
    return pt


def _columnar_decrypt_batch(ct: np.ndarray, keys: np.ndarray) -> np.ndarray:
    """
    Batch columnar decryption.

    Parameters
    ----------
    ct : np.ndarray (uint8) shape [L]
        Ciphertext tokens.
    keys : np.ndarray (uint8/int) shape [B, K] or [K]
        Each row is a read-order permutation (values 0..K-1).

    Returns
    -------
    np.ndarray (uint8) shape [B, L]
        Plaintext tokens for each key in the batch.
    """
    if keys.ndim == 1:
        keys = keys[None, :]
    B = int(keys.shape[0])
    L = int(ct.size)
    out = np.empty((B, L), dtype=np.uint8)
    for b in range(B):
        out[b] = _columnar_decrypt_single(ct, np.asarray(keys[b], dtype=np.int64))
    return out


def _apply_transposition_batch(cfg: "CipherConfig", keys_batch: np.ndarray) -> np.ndarray:
    """
    Dispatch transposition decryption for a batch of keys, using hints from the cipher config.

    Parameters
    ----------
    cfg : CipherConfig
        Must provide `ciphertext` and may include a private hint dict `cfg._transpose`.
        Example: `{"kind": "columnar"}`.
    keys_batch : np.ndarray
        Batch of keys; shape and dtype depend on the transposition kind.

    Returns
    -------
    np.ndarray
        Batch of plaintext tokens per key.

    Raises
    ------
    ValueError
        If an unknown transposition kind is requested.
    """
    hint = getattr(cfg, "_transpose", None) or {}
    kind = hint.get("kind", "")
    ct = cfg.ciphertext
    if kind == "columnar":
        return _columnar_decrypt_batch(ct, keys_batch)
    # TODO: add 'railfence', 'route', 'blockperm', 'double_transposition' here
    raise ValueError(f"Unknown transposition kind: {kind}")
