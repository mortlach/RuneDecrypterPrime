#!/usr/bin/env python3
"""
Migrate legacy ECDF .npz assets to the vNext ABI:
  - grid/q stored as float64
  - strict monotonicity enforced (nudged with nextafter if needed)
  - meta_json required and populated from legacy meta + file name

This script updates files in-place (atomic replace).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np


_FILENAME_RE = re.compile(
    r"^(?P<mode>ltr|rtl)_(?P<pos>nose|wise)_(?P<model>char|wli)_n(?P<n>\d+)_win(?P<win>\d+)_(?P<stat>[a-z]+)\.npz$"
)


def _parse_name(fp: Path) -> Dict[str, Any]:
    name = fp.name
    m = _FILENAME_RE.match(name)
    if not m:
        raise ValueError(f"Unrecognized ECDF filename: {fp}")
    out = m.groupdict()
    out["n"] = int(out["n"])
    out["win"] = int(out["win"])
    return out


def _coerce_meta(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, np.ndarray):
        if raw.shape == ():
            raw = raw.item()
        elif raw.size == 1:
            raw = raw.reshape(()).item()
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("utf-8")
        except Exception:
            return {}
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _ensure_strict_inc(
    arr: np.ndarray,
    *,
    lower: float | None = None,
    upper: float | None = None,
    toward: float | None = None,
) -> np.ndarray:
    out = np.asarray(arr, dtype=np.float64).copy()
    if lower is not None or upper is not None:
        out = np.clip(out, lower if lower is not None else -np.inf, upper if upper is not None else np.inf)

    # Forward pass: make strictly increasing.
    if out.size > 1:
        tgt = np.inf if toward is None else float(toward)
        for i in range(1, out.size):
            if out[i] <= out[i - 1]:
                out[i] = np.nextafter(out[i - 1], tgt)

    # Respect upper bound by pushing backward if needed.
    if upper is not None and out.size > 0 and out[-1] > upper:
        out[-1] = float(upper)
        tgt = lower if lower is not None else -np.inf
        for i in range(out.size - 2, -1, -1):
            if out[i] >= out[i + 1]:
                out[i] = np.nextafter(out[i + 1], tgt)

    # Respect lower bound by pushing forward if needed.
    if lower is not None and out.size > 0 and out[0] < lower:
        out[0] = float(lower)
        tgt = upper if upper is not None else np.inf
        for i in range(1, out.size):
            if out[i] <= out[i - 1]:
                out[i] = np.nextafter(out[i - 1], tgt)

    if out.size > 1 and not bool(np.all(np.diff(out) > 0.0)):
        raise ValueError("Could not enforce strict monotonicity")
    return out


def _build_meta(fp: Path, meta_src: Dict[str, Any], info: Dict[str, Any], *, win: int, num_knots: int) -> Dict[str, Any]:
    mode = info["mode"]
    pos = info["pos"]
    model = info["model"]
    n = int(info["n"])
    stat = info["stat"]

    mesh_kind = meta_src.get("quantile_mesh") or "linear"
    mesh_params: Dict[str, Any] = {}
    if mesh_kind == "logistic" and meta_src.get("logistic_a") is not None:
        mesh_params["a"] = float(meta_src.get("logistic_a"))

    strict_method = meta_src.get("strict_method") or "nextafter"

    meta = {
        "model": model,
        "direction": mode,
        "se_mode": pos,
        "n": int(n),
        "stat": stat,
        "win_ngrams": int(win),
        "window_def": {
            "win_ngrams": int(win),
            "span_formula": "nose: L_n = W + n - 1; wise: L_n = W + n + 1",
            "start_index_rule": "i = 0 .. T - L_max; L_max = max_n L_n",
            "tags": "wise uses [29]... [30], nose has no tags",
            "tags_start_id": 29,
            "tags_end_id": 30,
        },
        "smoothing": {"kind": "auto_gt", "alpha": 0.5},
        "oov_policy": "floor_min_seen",
        "mesh": {"kind": mesh_kind, "params": mesh_params, "num_knots": int(num_knots)},
        "strict_increasing": {"enforce": True, "method": str(strict_method)},
        "tie_policy": "builder nudges duplicate quantiles to enforce strict grid",
        "ecdf_canonical": True,
    }

    # Traceability
    for key in ("builder", "builder_version", "created_ts", "notes"):
        if key in meta_src:
            meta[key] = meta_src[key]
    meta["source_meta"] = meta_src
    meta["asset_path"] = str(fp)
    return meta


def migrate_file(fp: Path, *, dry_run: bool = False) -> Tuple[bool, str]:
    with np.load(fp, allow_pickle=True) as arr:
        if "grid" not in arr or "q" not in arr:
            return False, "missing grid/q"

        info = _parse_name(fp)
        meta_src = _coerce_meta(arr.get("meta")) or _coerce_meta(arr.get("meta_json"))

        # Read arrays eagerly so the underlying file handle can be closed on Windows.
        grid_src = np.array(arr["grid"], copy=True)
        q_src = np.array(arr["q"], copy=True)
        meta_raw = arr.get("meta")

    grid64 = _ensure_strict_inc(grid_src, toward=np.inf)
    q64 = _ensure_strict_inc(q_src, lower=0.0, upper=1.0, toward=1.0)

    meta = _build_meta(fp, meta_src, info, win=int(info["win"]), num_knots=int(grid64.size))
    meta_json = json.dumps(meta, sort_keys=True)

    payload = {
        "grid": grid64,
        "q": q64,
        "meta_json": np.array(meta_json, dtype=object),
    }
    if meta_raw is not None:
        payload["meta"] = meta_raw

    if dry_run:
        return True, "dry-run"

    tmp = fp.with_name(fp.stem + ".tmp" + fp.suffix)
    np.savez(tmp, **payload)
    tmp.replace(fp)
    return True, "migrated"


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate LM ECDF assets to vNext ABI.")
    ap.add_argument("root", nargs="?", default="src/rune_decrypter_prime/data/language_model/lmp/ecdf",
                    help="ECDF root directory (default: repo ECDF path)")
    ap.add_argument("--dry-run", action="store_true", help="Scan and report without writing files")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"ECDF root not found: {root}")
        return 1

    files = sorted(root.rglob("*.npz"))
    if not files:
        print(f"No ECDF .npz files found under {root}")
        return 1

    ok = 0
    fail = 0
    for fp in files:
        try:
            did, msg = migrate_file(fp, dry_run=args.dry_run)
        except Exception as exc:
            fail += 1
            print(f"[FAIL] {fp}: {exc}")
            continue
        if did:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {fp}: {msg}")

    print(f"Done. ok={ok}, failed={fail}, dry_run={args.dry_run}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
