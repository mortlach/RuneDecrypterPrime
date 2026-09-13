from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np


@dataclass(frozen=True)
class ECDFValidationResult:
    ok: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    meta: Dict[str, Any] | None
    meta_hash: str | None


_REQUIRED_META_TOP = (
    "model",
    "direction",
    "se_mode",
    "n",
    "stat",
    "win_ngrams",
    "window_def",
    "smoothing",
    "oov_policy",
    "mesh",
    "strict_increasing",
    "tie_policy",
    "ecdf_canonical",
)

_REQUIRED_WINDOW_DEF = (
    "win_ngrams",
    "span_formula",
    "start_index_rule",
    "tags",
    "tags_start_id",
    "tags_end_id",
)

_REQUIRED_SMOOTHING = ("kind", "alpha")
_REQUIRED_MESH = ("kind", "params", "num_knots")
_REQUIRED_STRICT = ("enforce", "method")

_ALLOW_DIR = {"ltr", "rtl"}
_ALLOW_SE = {"nose", "wise"}
_ALLOW_MODEL = {"char", "wli"}
_ALLOW_STAT = {"logp", "zsum", "madsum"}
_ALLOW_SMOOTH = {"none", "lidstone", "jeffreys", "auto_gt"}
_ALLOW_OOV = {"floor_min_seen", "lidstone"}
_ALLOW_MESH = {"linear", "logistic", "custom"}
_ALLOW_STRICT_METHOD = {"nextafter", "epsilon"}


def _coerce_meta_json(raw: Any) -> bytes | None:
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    if isinstance(raw, str):
        return raw.encode("utf-8")
    # numpy scalar / object array
    try:
        if isinstance(raw, np.ndarray):
            if raw.shape == ():
                raw = raw.item()
            elif raw.size == 1:
                raw = raw.reshape(()).item()
    except Exception:
        pass
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    if isinstance(raw, str):
        return raw.encode("utf-8")
    return None


def _hash_ecdf(meta_json_bytes: bytes, grid: np.ndarray, q: np.ndarray) -> str:
    h = hashlib.sha256()
    h.update(meta_json_bytes)
    h.update(np.ascontiguousarray(grid, dtype=np.float64).tobytes())
    h.update(np.ascontiguousarray(q, dtype=np.float64).tobytes())
    return h.hexdigest()


def _append_missing(errors: List[str], prefix: str, missing: Iterable[str]) -> None:
    missing_list = list(missing)
    if not missing_list:
        return
    errors.append(f"{prefix} missing keys: {', '.join(missing_list)}")


def validate_ecdf_npz(
    path: str | "os.PathLike[str]",
    *,
    ecdf_clamp_min: float | None = None,
    ecdf_clamp_max: float | None = None,
) -> ECDFValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    meta: Dict[str, Any] | None = None
    meta_hash: str | None = None

    try:
        arr = np.load(path, allow_pickle=True)
    except Exception as exc:
        return ECDFValidationResult(False, (f"failed to load npz: {exc}",), (), None, None)

    # Required arrays
    if "grid" not in arr or "q" not in arr:
        missing = [k for k in ("grid", "q") if k not in arr]
        errors.append(f"missing arrays: {', '.join(missing)}")
        return ECDFValidationResult(False, tuple(errors), tuple(warnings), None, None)

    grid = arr["grid"]
    q = arr["q"]

    # dtype checks
    if grid.dtype != np.float64:
        errors.append(f"grid dtype must be float64; got {grid.dtype}")
    if q.dtype != np.float64:
        errors.append(f"q dtype must be float64; got {q.dtype}")

    # shape checks
    if grid.ndim != 1 or q.ndim != 1:
        errors.append(f"grid/q must be 1D; got grid{grid.shape}, q{q.shape}")
    if grid.size != q.size:
        errors.append(f"grid/q length mismatch: {grid.size} vs {q.size}")

    # monotonicity
    try:
        if grid.size > 1 and not bool(np.all(np.diff(grid) > 0.0)):
            errors.append("grid must be strictly increasing (no ties)")
        if q.size > 1 and not bool(np.all(np.diff(q) > 0.0)):
            errors.append("q must be strictly increasing (no ties)")
    except Exception as exc:
        errors.append(f"monotonicity check failed: {exc}")

    # q range
    try:
        if q.size > 0:
            q0 = float(q[0])
            q1 = float(q[-1])
            if not (0.0 <= q0 < q1 <= 1.0):
                errors.append(f"q range invalid: q[0]={q0}, q[-1]={q1}")
    except Exception as exc:
        errors.append(f"q range check failed: {exc}")

    # clamp range
    if ecdf_clamp_min is not None and ecdf_clamp_max is not None and q.size > 0:
        try:
            q0 = float(q[0])
            q1 = float(q[-1])
            if not (q0 <= float(ecdf_clamp_min) and float(ecdf_clamp_max) <= q1):
                errors.append(
                    f"clamp range outside ECDF range: clamp_min={ecdf_clamp_min}, "
                    f"clamp_max={ecdf_clamp_max}, q0={q0}, q1={q1}"
                )
        except Exception as exc:
            errors.append(f"clamp range check failed: {exc}")

    # meta_json
    if "meta_json" not in arr:
        errors.append("meta_json missing")
    else:
        meta_bytes = _coerce_meta_json(arr["meta_json"])
        if meta_bytes is None:
            errors.append("meta_json could not be decoded as UTF-8 bytes")
        else:
            try:
                meta = json.loads(meta_bytes.decode("utf-8"))
            except Exception as exc:
                errors.append(f"meta_json invalid JSON: {exc}")
            else:
                # required keys
                _append_missing(errors, "meta_json", [k for k in _REQUIRED_META_TOP if k not in meta])
                if isinstance(meta.get("window_def"), dict):
                    _append_missing(errors, "window_def", [k for k in _REQUIRED_WINDOW_DEF if k not in meta["window_def"]])
                if isinstance(meta.get("smoothing"), dict):
                    _append_missing(errors, "smoothing", [k for k in _REQUIRED_SMOOTHING if k not in meta["smoothing"]])
                if isinstance(meta.get("mesh"), dict):
                    _append_missing(errors, "mesh", [k for k in _REQUIRED_MESH if k not in meta["mesh"]])
                    if meta["mesh"].get("kind") == "custom" and "custom_mesh_id" not in meta["mesh"]:
                        errors.append("mesh.custom_mesh_id required when kind == 'custom'")
                if isinstance(meta.get("strict_increasing"), dict):
                    _append_missing(errors, "strict_increasing", [k for k in _REQUIRED_STRICT if k not in meta["strict_increasing"]])

                # value checks (best-effort)
                if (model := meta.get("model")) is not None and model not in _ALLOW_MODEL:
                    errors.append(f"meta_json.model invalid: {model}")
                if (direction := meta.get("direction")) is not None and direction not in _ALLOW_DIR:
                    errors.append(f"meta_json.direction invalid: {direction}")
                if (se_mode := meta.get("se_mode")) is not None and se_mode not in _ALLOW_SE:
                    errors.append(f"meta_json.se_mode invalid: {se_mode}")
                if (stat := meta.get("stat")) is not None and stat not in _ALLOW_STAT:
                    errors.append(f"meta_json.stat invalid: {stat}")
                if (oov := meta.get("oov_policy")) is not None and oov not in _ALLOW_OOV:
                    errors.append(f"meta_json.oov_policy invalid: {oov}")
                if isinstance(meta.get("smoothing"), dict):
                    kind = meta["smoothing"].get("kind")
                    if kind is not None and kind not in _ALLOW_SMOOTH:
                        errors.append(f"meta_json.smoothing.kind invalid: {kind}")
                if isinstance(meta.get("mesh"), dict):
                    m_kind = meta["mesh"].get("kind")
                    if m_kind is not None and m_kind not in _ALLOW_MESH:
                        errors.append(f"meta_json.mesh.kind invalid: {m_kind}")
                if isinstance(meta.get("strict_increasing"), dict):
                    method = meta["strict_increasing"].get("method")
                    if method is not None and method not in _ALLOW_STRICT_METHOD:
                        errors.append(f"meta_json.strict_increasing.method invalid: {method}")

            if meta is not None and meta_bytes is not None and grid.dtype == np.float64 and q.dtype == np.float64:
                try:
                    meta_hash = _hash_ecdf(meta_bytes, grid, q)
                except Exception as exc:
                    warnings.append(f"meta_hash computation failed: {exc}")

    ok = len(errors) == 0
    return ECDFValidationResult(ok, tuple(errors), tuple(warnings), meta, meta_hash)


__all__ = ["ECDFValidationResult", "validate_ecdf_npz"]
