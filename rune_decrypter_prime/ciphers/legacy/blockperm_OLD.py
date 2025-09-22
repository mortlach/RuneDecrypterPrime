import numpy as np

def enc_blockperm(pt: np.ndarray, key: np.ndarray, A: int = 29) -> np.ndarray:
    pt = np.asarray(pt, dtype=np.uint8)
    key = np.asarray(key, dtype=np.uint8)
    n = pt.size

    B = key.size // 2
    if B <= 0:
        raise ValueError("Block size must be > 0")
    perm = key[:B]
    shifts = key[B:]
    if not np.array_equal(np.sort(perm), np.arange(B, dtype=np.uint8)):
        raise ValueError("Invalid permutation part of key")

    pad = (-n) % B
    if pad:
        pt = np.concatenate([pt, np.zeros(pad, dtype=np.uint8)])
    M = pt.size // B
    blocks = pt.reshape(M, B)
    blocks = blocks[:, perm]
    blocks = (blocks.astype(np.int16) + shifts.astype(np.int16)) % A
    return blocks.reshape(-1)[:n].astype(np.uint8)

def dec_blockperm(ct: np.ndarray, key: np.ndarray, A: int = 29) -> np.ndarray:
    ct = np.asarray(ct, dtype=np.uint8)
    key = np.asarray(key, dtype=np.uint8)
    n = ct.size

    B = key.size // 2
    if B <= 0:
        raise ValueError("Block size must be > 0")
    perm = key[:B]
    shifts = key[B:]

    pad = (-n) % B
    if pad:
        ct = np.concatenate([ct, np.zeros(pad, dtype=np.uint8)])
    M = ct.size // B
    blocks = ct.reshape(M, B)
    blocks = (blocks.astype(np.int16) - shifts.astype(np.int16)) % A
    inv = np.argsort(perm)
    blocks = blocks[:, inv]
    return blocks.reshape(-1)[:n].astype(np.uint8)
