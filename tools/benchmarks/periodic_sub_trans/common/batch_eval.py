from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence, Tuple
import time

import numpy as np


@dataclass
class BatchEvalStats:
    candidates: int = 0
    batch_calls: int = 0
    scalar_fallback_calls: int = 0
    decrypt_seconds: float = 0.0
    score_seconds: float = 0.0


def _as_u8_plaintext_matrix(plaintexts: Sequence[Iterable[int]] | np.ndarray) -> np.ndarray:
    if isinstance(plaintexts, np.ndarray):
        arr = np.asarray(plaintexts, dtype=np.uint8)
        if arr.ndim == 1:
            arr = arr[None, :]
        if arr.ndim != 2:
            raise ValueError(f"plaintext batch must be rank-2, got shape={arr.shape}")
        return np.ascontiguousarray(arr, dtype=np.uint8)

    rows = []
    for pt in plaintexts:
        row = np.asarray(pt, dtype=np.uint8).reshape(-1)
        rows.append(row)
    if not rows:
        return np.empty((0, 0), dtype=np.uint8)
    return np.ascontiguousarray(np.stack(rows, axis=0), dtype=np.uint8)


def _as_key_matrix(keys: Sequence[Iterable[int]] | np.ndarray, *, dtype=np.int16) -> np.ndarray:
    if isinstance(keys, np.ndarray):
        arr = np.asarray(keys, dtype=dtype)
        if arr.ndim == 1:
            arr = arr[None, :]
        if arr.ndim != 2:
            raise ValueError(f"key batch must be rank-2, got shape={arr.shape}")
        return np.ascontiguousarray(arr, dtype=dtype)

    rows = []
    for key in keys:
        row = np.asarray(key, dtype=dtype).reshape(-1)
        rows.append(row)
    if not rows:
        return np.empty((0, 0), dtype=dtype)
    return np.ascontiguousarray(np.stack(rows, axis=0), dtype=dtype)


def score_plaintexts_chunked(
    *,
    scorer: Any,
    plaintexts: Sequence[Iterable[int]] | np.ndarray,
    wli: Any,
    chunk_size: int = 256,
    require_batch: bool = True,
    stats: BatchEvalStats | None = None,
) -> Tuple[np.ndarray, BatchEvalStats]:
    st = stats if stats is not None else BatchEvalStats()
    pts = _as_u8_plaintext_matrix(plaintexts)
    n = int(pts.shape[0])
    if n == 0:
        return np.empty((0,), dtype=np.float64), st

    chunk = max(1, int(chunk_size))
    out = np.empty((n,), dtype=np.float64)
    for lo in range(0, n, chunk):
        hi = min(n, lo + chunk)
        pts_chunk = pts[lo:hi]
        t_sc = time.perf_counter()
        if hasattr(scorer, "batch_score") and callable(scorer.batch_score):
            st.batch_calls += 1
            try:
                sc = np.asarray(scorer.batch_score(pts_chunk, wli), dtype=np.float64).reshape(-1)
                if sc.shape[0] != (hi - lo):
                    raise ValueError(
                        f"scorer.batch_score returned {sc.shape[0]} scores for batch size {hi - lo}"
                    )
            except Exception:
                st.scalar_fallback_calls += 1
                if bool(require_batch):
                    raise
                sc = np.asarray(
                    [float(scorer.score(pt, wli)) for pt in pts_chunk],
                    dtype=np.float64,
                )
        else:
            st.scalar_fallback_calls += 1
            if bool(require_batch):
                raise RuntimeError("scorer does not provide batch_score while require_batch=True")
            sc = np.asarray([float(scorer.score(pt, wli)) for pt in pts_chunk], dtype=np.float64)
        st.score_seconds += float(time.perf_counter() - t_sc)
        out[lo:hi] = sc

    st.candidates += int(n)
    return out, st


def decrypt_and_score_keys_chunked(
    *,
    cipher: Any,
    ciphertext: Sequence[int] | np.ndarray,
    keys: Sequence[Iterable[int]] | np.ndarray,
    scorer: Any,
    wli: Any,
    key_dtype=np.int16,
    chunk_size: int = 256,
    require_batch: bool = True,
    stats: BatchEvalStats | None = None,
) -> Tuple[np.ndarray, np.ndarray, BatchEvalStats]:
    st = stats if stats is not None else BatchEvalStats()
    key_mat = _as_key_matrix(keys, dtype=key_dtype)
    n = int(key_mat.shape[0])
    if n == 0:
        return np.empty((0, 0), dtype=np.uint8), np.empty((0,), dtype=np.float64), st

    ct = np.asarray(ciphertext, dtype=np.uint8).reshape(-1)
    chunk = max(1, int(chunk_size))
    pts_chunks = []
    scores = np.empty((n,), dtype=np.float64)
    out_pos = 0
    for lo in range(0, n, chunk):
        hi = min(n, lo + chunk)
        k_chunk = np.ascontiguousarray(key_mat[lo:hi], dtype=key_dtype)
        t_dec = time.perf_counter()
        dec = cipher.decrypt(
            ciphertext=ct,
            key=k_chunk,
            interrupt_idx=None,
            interrupt_sym=None,
        )
        st.decrypt_seconds += float(time.perf_counter() - t_dec)
        pts_chunk = _as_u8_plaintext_matrix(dec)
        if pts_chunk.shape[0] != (hi - lo):
            raise ValueError(
                f"cipher.decrypt returned {pts_chunk.shape[0]} plaintexts for {hi - lo} keys"
            )

        sc_chunk, st = score_plaintexts_chunked(
            scorer=scorer,
            plaintexts=pts_chunk,
            wli=wli,
            chunk_size=max(1, int(chunk_size)),
            require_batch=require_batch,
            stats=st,
        )
        pts_chunks.append(pts_chunk)
        scores[out_pos : out_pos + int(sc_chunk.shape[0])] = sc_chunk
        out_pos += int(sc_chunk.shape[0])

    pts_all = np.ascontiguousarray(np.vstack(pts_chunks), dtype=np.uint8)
    return pts_all, scores, st
