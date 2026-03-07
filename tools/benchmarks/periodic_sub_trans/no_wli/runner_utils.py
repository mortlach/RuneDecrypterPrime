from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Sequence

import numpy as np


def extract_top_keys(sol: Any, *, limit: int) -> List[List[int]]:
    out: List[List[int]] = []
    try:
        tel = getattr(sol, "meta", {}).get("telemetry", {})
        km = tel.get("kaeding", {}) if isinstance(tel, dict) else {}
        top = km.get("top_keys", None) if isinstance(km, dict) else None
        if isinstance(top, list):
            out.extend([list(map(int, row)) for row in top])
    except Exception:
        pass
    try:
        if getattr(sol, "key", None) is not None:
            out.append(list(map(int, list(sol.key))))
    except Exception:
        pass

    seen: set[tuple[int, ...]] = set()
    dedup: List[List[int]] = []
    for k in out:
        t = tuple(int(x) for x in k)
        if t in seen:
            continue
        seen.add(t)
        dedup.append(list(k))
        if len(dedup) >= int(limit):
            break
    return dedup


def mutate_full_key(
    base_key: Sequence[int],
    *,
    period: int,
    columns: int,
    seed: int,
    n: int,
    alphabet_size: int,
) -> List[List[int]]:
    rng = np.random.default_rng(int(seed))
    base_arr = np.asarray(base_key, dtype=np.int16).copy()
    out = [base_arr.astype(int).tolist()]
    sub_len = int(period) * int(alphabet_size)
    while len(out) < int(n):
        k = base_arr.copy()
        ph = int(rng.integers(0, int(period)))
        a = int(rng.integers(0, int(alphabet_size)))
        b = int(rng.integers(0, int(alphabet_size - 1)))
        if b >= a:
            b += 1
        i1 = int(ph * int(alphabet_size) + a)
        i2 = int(ph * int(alphabet_size) + b)
        k[i1], k[i2] = k[i2], k[i1]
        if int(columns) > 1:
            a = int(rng.integers(0, int(columns)))
            b = int(rng.integers(0, int(columns - 1)))
            if b >= a:
                b += 1
            t1 = int(sub_len + a)
            t2 = int(sub_len + b)
            k[t1], k[t2] = k[t2], k[t1]
        out.append(k.astype(int).tolist())
    return out[: int(n)]


def key_hash16(key_vals: Sequence[int]) -> str:
    arr = np.asarray(list(map(int, key_vals)), dtype=np.int16).reshape(-1)
    return hashlib.sha1(arr.tobytes()).hexdigest()[:16]


def preview_latin(
    pt: Sequence[int],
    wli: Sequence[Sequence[int]],
    *,
    safe_preview_latin_fn: Any,
    limit: int,
) -> str:
    return str(safe_preview_latin_fn(pt, wli, limit=limit))


def print_stage_preview(
    *,
    label: str,
    pt: Sequence[int],
    wli: Sequence[Sequence[int]],
    match_ratio: float | None,
    preview_fn: Any,
    log_prefix: str = "[pipeline_no_wli]",
) -> None:
    txt = str(preview_fn(pt, wli))
    mr_txt = ""
    if match_ratio is not None and np.isfinite(float(match_ratio)):
        mr_txt = f" match_ratio={float(match_ratio):.3f}"
    print(
        f"{log_prefix} preview {label} scorer_wli=off "
        f"len={len(pt)} words={len(wli)}{mr_txt} text=\"{txt}\"",
        flush=True,
    )


def objective_text(obj: Any) -> str:
    family = str(getattr(obj, "family", "unknown"))
    stat = str(getattr(obj, "stat", "unknown"))
    win = getattr(obj, "win", None)
    fam_txt = family.split(".")[-1].lower()
    stat_txt = stat.split(".")[-1].lower()
    return f"{fam_txt}.{stat_txt}.win{int(win) if win is not None else 'na'}"


def weights_text(weights: Dict[int, float]) -> str:
    if not weights:
        return "{}"
    parts = [
        f"{int(k)}:{float(v):g}"
        for k, v in sorted(weights.items(), key=lambda kv: int(kv[0]))
    ]
    return "{" + ",".join(parts) + "}"
