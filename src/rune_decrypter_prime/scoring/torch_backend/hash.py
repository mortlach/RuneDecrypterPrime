from __future__ import annotations

import numpy as np
import torch


def as_lut_keys_int64_torch(keys_uint64, device: torch.device) -> torch.Tensor:
    if hasattr(keys_uint64, "dtype"):
        if keys_uint64.dtype == np.uint64:
            view_i64 = keys_uint64.view(np.int64)
            return torch.as_tensor(view_i64, dtype=torch.int64, device=device)
        if keys_uint64.dtype == np.int64:
            return torch.as_tensor(keys_uint64, dtype=torch.int64, device=device)
    t = torch.as_tensor(keys_uint64, device=device)
    return t.to(torch.int64)


def as_lut_logp_float32_torch(logp, device: torch.device) -> torch.Tensor:
    t = torch.as_tensor(logp, device=device)
    if t.dtype != torch.float32:
        t = t.to(torch.float32)
    return t


def _validate_u32_hash_input_cpu(tokens_u32: torch.Tensor | np.ndarray) -> np.ndarray:
    arr: np.ndarray
    if isinstance(tokens_u32, torch.Tensor):
        arr = tokens_u32.detach().cpu().numpy()
    else:
        arr = np.asarray(tokens_u32)
    if arr.dtype != np.uint32:
        raise ValueError(f"xxh64 cpu hash expects uint32 tokens, got dtype={arr.dtype}")
    if arr.ndim < 1:
        raise ValueError("xxh64 cpu hash expects rank >= 1 input")
    n = int(arr.shape[-1])
    if n not in (1, 2, 3, 4):
        raise ValueError(f"xxh64 cpu hash expects n-gram width in [1..4], got n={n}")
    return arr


def _validate_u32_hash_input_device(tokens_u32: torch.Tensor) -> torch.Tensor:
    if not isinstance(tokens_u32, torch.Tensor):
        raise TypeError("xxh64 device hash expects a torch.Tensor input")
    if tokens_u32.dtype != torch.uint32:
        raise ValueError(
            f"xxh64 device hash expects torch.uint32 tokens, got dtype={tokens_u32.dtype}"
        )
    if tokens_u32.ndim < 1:
        raise ValueError("xxh64 device hash expects rank >= 1 input")
    n = int(tokens_u32.shape[-1])
    if n not in (1, 2, 3, 4):
        raise ValueError(f"xxh64 device hash expects n-gram width in [1..4], got n={n}")
    return tokens_u32


def xxh64_u32words_cpu(tokens_u32: torch.Tensor | np.ndarray) -> np.ndarray:
    t = _validate_u32_hash_input_cpu(tokens_u32)
    n = t.shape[-1]
    u64 = np.uint64

    def rotl64(x: np.ndarray, r: int) -> np.ndarray:
        return ((x << r) | (x >> u64(64 - r))) & u64(0xFFFFFFFFFFFFFFFF)

    p1 = u64(0x9E3779B185EBCA87)
    p2 = u64(0xC2B2AE3D27D4EB4F)
    p3 = u64(0x165667B19E3779F9)
    p4 = u64(0x85EBCA77C2B2AE63)
    p5 = u64(0x27D4EB2F165667C5)
    mask64 = u64(0xFFFFFFFFFFFFFFFF)

    total_len = u64(n * 4)
    h = (p5 + total_len) & mask64
    t_u64 = t.astype(u64, copy=False)

    pairs = n // 2
    for i in range(pairs):
        k1 = (t_u64[..., 2 * i] | (t_u64[..., 2 * i + 1] << u64(32))) & mask64
        k1 = (k1 * p2) & mask64
        k1 = rotl64(k1, 31)
        k1 = (k1 * p1) & mask64
        h ^= k1
        h = (rotl64(h, 27) * p1 + p4) & mask64

    if n % 2 == 1:
        k1 = (t_u64[..., -1] * p1) & mask64
        h ^= k1
        h = (rotl64(h, 23) * p2 + p3) & mask64

    h ^= h >> u64(33)
    h = (h * p2) & mask64
    h ^= h >> u64(29)
    h = (h * p3) & mask64
    h ^= h >> u64(32)
    return h


def xxh64_u32words_device(tokens_u32: torch.Tensor) -> torch.Tensor:
    tokens_u32 = _validate_u32_hash_input_device(tokens_u32)
    n = tokens_u32.shape[-1]
    device = tokens_u32.device
    try:
        p1 = torch.tensor(0x9E3779B185EBCA87, dtype=torch.uint64, device=device)
        p2 = torch.tensor(0xC2B2AE3D27D4EB4F, dtype=torch.uint64, device=device)
        p3 = torch.tensor(0x165667B19E3779F9, dtype=torch.uint64, device=device)
        p4 = torch.tensor(0x85EBCA77C2B2AE63, dtype=torch.uint64, device=device)
        p5 = torch.tensor(0x27D4EB2F165667C5, dtype=torch.uint64, device=device)
        mask64 = torch.tensor(0xFFFFFFFFFFFFFFFF, dtype=torch.uint64, device=device)

        total_len = torch.tensor(n * 4, dtype=torch.uint64, device=device)
        h = (p5 + total_len) & mask64
        t = tokens_u32.to(torch.uint64)

        def _rotl(x: torch.Tensor, r: int) -> torch.Tensor:
            return ((x << r) | (x >> (64 - r))) & mask64

        pairs = n // 2
        for i in range(pairs):
            k1 = (t[..., 2 * i] | (t[..., 2 * i + 1] << 32)) & mask64
            k1 = (k1 * p2) & mask64
            k1 = _rotl(k1, 31) * p1 & mask64
            h ^= k1
            h = (_rotl(h, 27) * p1 + p4) & mask64

        if n % 2 == 1:
            k1 = (t[..., -1] * p1) & mask64
            h ^= k1
            h = (_rotl(h, 23) * p2 + p3) & mask64

        h ^= h >> 33
        h = (h * p2) & mask64
        h ^= h >> 29
        h = (h * p3) & mask64
        h ^= h >> 32
        return h.to(torch.int64)
    except Exception:
        return torch.from_numpy(xxh64_u32words_cpu(tokens_u32).view(np.int64)).to(
            device
        )
