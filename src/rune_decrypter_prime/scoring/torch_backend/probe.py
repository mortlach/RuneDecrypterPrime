from __future__ import annotations

import torch


def lookup_logp_linear_probe(
    h: torch.Tensor,
    keys_i64: torch.Tensor,
    logp_f32: torch.Tensor,
    mask: int,
    fallback_logp: float,
    *,
    max_probes: int = 1024,
) -> tuple[torch.Tensor, int, bool]:
    if max_probes <= 0:
        raise ValueError("max_probes must be >= 1")
    if h.dtype != torch.int64:
        h = h.to(torch.int64)
    if keys_i64.dtype != torch.int64:
        raise ValueError(f"keys_i64 must be torch.int64, got {keys_i64.dtype}")
    if logp_f32.dtype != torch.float32:
        raise ValueError(f"logp_f32 must be torch.float32, got {logp_f32.dtype}")
    if keys_i64.numel() == 0:
        raise ValueError("keys_i64 must not be empty")
    if mask < 0:
        raise ValueError("mask must be >= 0")
    if keys_i64.device != h.device or logp_f32.device != h.device:
        raise ValueError("h, keys_i64, and logp_f32 must be on the same device")

    idx = (h & torch.tensor(mask, dtype=keys_i64.dtype, device=h.device)).to(torch.long)
    out = torch.full(
        h.shape, fill_value=float(fallback_logp), dtype=torch.float32, device=h.device
    )
    found = torch.zeros(h.shape, dtype=torch.bool, device=h.device)
    probe_exhausted = False

    for _ in range(int(max_probes)):
        k = keys_i64[idx]
        is_empty = k == 0
        is_match = k == h
        take = (~found) & is_match
        if bool(take.any()):
            out[take] = logp_f32[idx[take]]
            found[take] = True
        cont = (~found) & (~is_empty)
        if not bool(cont.any()):
            break
        idx[cont] = (idx[cont] + 1) & int(mask)
    else:
        probe_exhausted = bool(((~found) & (keys_i64[idx] != 0)).any().item())

    unresolved = int((~found).sum().item())
    return out, unresolved, probe_exhausted
