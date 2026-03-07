from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict

import numpy as np


def resolve_repo_path(path_like: Path | str | None, *, root: Path) -> Path | None:
    if path_like is None:
        return None
    p = Path(path_like).expanduser()
    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()
    return p


def to_repo_rel_path(path_like: Path | str | None, *, root: Path) -> str:
    if path_like is None:
        return ""
    raw = Path(path_like).expanduser()
    root_resolved = root.resolve()
    try:
        p = raw.resolve()
        return str(p.relative_to(root_resolved)).replace("\\", "/")
    except Exception:
        if not raw.is_absolute():
            return str(raw).replace("\\", "/")
        return "<external>"


def scorer_cfg_for_output(cfg: Dict[str, Any], *, root: Path) -> Dict[str, Any]:
    out = dict(cfg)
    if "span_hamming_assets_dir" in out:
        out["span_hamming_assets_dir"] = to_repo_rel_path(
            out.get("span_hamming_assets_dir"),
            root=root,
        )
    return out


def scoring_meta_for_output(meta: Dict[str, Any], *, root: Path) -> Dict[str, Any]:
    out = dict(meta)
    if "span_assets_dir" in out:
        out["span_assets_dir"] = to_repo_rel_path(out.get("span_assets_dir"), root=root)
    return out


def git_short(*, repo_root: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8", errors="replace").strip() or "nogit"
    except Exception:
        return "nogit"


def git_commit(*, repo_root: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8", errors="replace").strip() or "nogit"
    except Exception:
        return "nogit"


def git_dirty(*, repo_root: Path) -> bool:
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
        )
        return bool(out.decode("utf-8", errors="replace").strip())
    except Exception:
        return False


def sanitize_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): sanitize_jsonable(v)
            for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return v if np.isfinite(v) else None
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        sanitize_jsonable(value),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_payload(payload: Dict[str, Any]) -> str:
    return sha256_text(canonical_json(payload))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
