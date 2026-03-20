from __future__ import annotations

from typing import Sequence

import numpy as np


def apply_slice_slip(
    *,
    key_vals: Sequence[int],
    target_slice: int,
    swaps: int,
    rng_obj: np.random.Generator,
    alphabet_size: int,
) -> list[int]:
    out = list(map(int, key_vals))
    if int(alphabet_size) <= 1:
        return out
    phase_base = int(target_slice) * int(alphabet_size)
    for _ in range(max(0, int(swaps))):
        a = int(rng_obj.integers(0, int(alphabet_size)))
        b = int(rng_obj.integers(0, int(alphabet_size - 1)))
        if b >= a:
            b += 1
        i1 = int(phase_base + int(a))
        i2 = int(phase_base + int(b))
        out[i1], out[i2] = int(out[i2]), int(out[i1])
    return out


def apply_slice_pair_swap(
    *,
    key_vals: Sequence[int],
    target_slice: int,
    pos_a: int,
    pos_b: int,
    alphabet_size: int,
) -> list[int]:
    out = list(map(int, key_vals))
    if int(alphabet_size) <= 1:
        return out
    phase_base = int(target_slice) * int(alphabet_size)
    i1 = int(phase_base + int(pos_a))
    i2 = int(phase_base + int(pos_b))
    out[i1], out[i2] = int(out[i2]), int(out[i1])
    return out


def target_slice_active_positions(
    *,
    ciphertext_idx: np.ndarray | Sequence[int],
    period: int,
    target_slice: int,
    alphabet_size: int,
    current_key: Sequence[int],
    probe_key: Sequence[int],
    top_symbols: int,
) -> list[int]:
    alphabet_i = int(max(1, int(alphabet_size)))
    residue = np.asarray(
        ciphertext_idx[int(target_slice) :: int(max(1, int(period)))],
        dtype=np.int64,
    ).reshape(-1)
    residue = residue[(residue >= 0) & (residue < alphabet_i)]
    counts = np.bincount(residue, minlength=alphabet_i).astype(np.int64)
    order = np.argsort(-counts, kind="stable").astype(np.int64).tolist()
    active: list[int] = [
        int(idx)
        for idx in order[: max(2, min(int(top_symbols), int(alphabet_i)))]
    ]
    phase_base = int(target_slice) * int(alphabet_i)
    cur_slice = list(map(int, current_key))[phase_base : phase_base + alphabet_i]
    probe_slice = list(map(int, probe_key))[phase_base : phase_base + alphabet_i]
    for pos_idx, (cur_v, probe_v) in enumerate(zip(cur_slice, probe_slice)):
        if int(cur_v) != int(probe_v):
            active.append(int(pos_idx))
    out = sorted({int(pos) for pos in active if 0 <= int(pos) < alphabet_i})
    if len(out) >= 2:
        return list(out)
    return list(range(alphabet_i))
