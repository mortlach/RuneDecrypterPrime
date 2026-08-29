# rune_decrypter_prime/telemetry/ciphers_pipeline.py
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Sequence

from rune_decrypter_prime.core.types import Direction, ensure_direction, Device, ensure_device

_DEFAULT_TELEMETRY_DIR = Path("output") / "telemetry" / "logs"

def device_request_str(dev: Device | str) -> str:
    """Return backend request token accepted by backends.xp.select_backend."""
    d = ensure_device(dev)
    # today backend names match Device.value, keep thin
    return d.value  # "cpu" or "cuda"

def _perm_summary(indices: Sequence[int] | None, length: int) -> dict[str, Any]:
    """
    Summarise a text permutation for telemetry.  Always returns a dict with
    ``kind``, ``length``, and ``hash`` keys.  The ``hash`` is a stable
    128-bit blake2b digest encoded as 32 hexadecimal characters.  When
    ``indices`` is ``None``, the identity permutation of ``length`` is
    assumed.
    """
    # Determine permutation kind and sequence
    if indices is None:
        perm_kind = "none"
        # Identity permutation 0..length-1
        perm_seq = list(range(int(length)))
    else:
        perm_kind = "custom"
        perm_seq = [int(x) for x in indices]
    # Ensure length is correct
    perm_length = int(length)
    # Build a stable representation and compute blake2b digest (16 bytes -> 32 hex chars)
    # Using a namespaced person to avoid collisions across versions
    payload = ("perm:" + ",".join(str(x) for x in perm_seq)).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=16, person=b"rdp-itp-v1").hexdigest()
    return {
        "kind": perm_kind,
        "length": perm_length,
        "hash": digest,
    }

def make_pipeline_block(
    *,
    text_encoding_direction: Direction | str | None,
    ciphertext_len: int,
    text_permutation: Sequence[int] | None,
) -> dict[str, Any]:
    """
    Build a canonical pipeline block for telemetry.  The block includes the
    text-encoding direction and a summary of the input permutation.  It
    contains exactly two top-level keys:

    ``text_encoding_direction``
        The canonicalised string representation of the direction (``"ltr"`` or
        ``"rtl"``).  If ``text_encoding_direction`` is ``None``, ``Direction.LTR``
        is assumed.

    ``input_permutation``
        A dict describing the permutation of input tokens, with keys:

        * ``kind`` – ``"none"`` if no permutation is specified (identity), or
          ``"custom"`` for an explicit permutation.
        * ``length`` – the number of tokens in the ciphertext.
        * ``hash`` – a 32-character hexadecimal digest uniquely identifying the
          permutation.  For the identity permutation, the digest is computed
          over the string ``"perm:0,1,2,..."`` for the given length; for a
          custom permutation, the digest is computed over ``"perm:"`` plus the
          comma-separated list of indices.  The digest is namespaced with
          ``person=b"rdp-itp-v1"`` to ensure stability across versions.
    """
    # Canonicalise direction
    d = ensure_direction(text_encoding_direction or Direction.LTR)
    # Build permutation summary using ciphertext length
    perm_info = _perm_summary(text_permutation, int(ciphertext_len))
    return {
        "text_encoding_direction": d.value,
        "input_permutation": perm_info,
    }

def dump_telemetry(sol, *, base_dir: str | Path | None = None) -> str:
    """
    Best-effort JSONL dump of ``sol.meta["telemetry"]``.

    When ``base_dir`` is omitted, telemetry is mirrored under
    ``output/telemetry/logs/`` with filenames ``run-<timestamp>.jsonl``.
    """
    # Respect a hard toggle if callers attached it to meta
    try:
        if hasattr(sol, "meta") and isinstance(sol.meta, dict) and sol.meta.get("telemetry_off", False):
            return ""
    except Exception:
        pass
    tel = getattr(sol, "meta", {}).get("telemetry", None) if hasattr(sol, "meta") else None
    if not isinstance(tel, dict):
        return ""
    dest = Path(base_dir) if base_dir is not None else _DEFAULT_TELEMETRY_DIR
    dest.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = dest / f"run-{ts}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(tel, ensure_ascii=False) + "\n")
    return str(path)



def finalize_run_meta(sol, cfg) -> None:
    """
    Normalize solution.meta for downstream pretty-printers.
    - Does not change solver logic.
    - Adds minimal 'scorer' and 'solver' blocks if missing.
    - Leaves strict nouns in place (no aliasing).
    """
    if not hasattr(sol, "meta") or sol.meta is None:
        sol.meta = {}
    meta: Dict[str, Any] = sol.meta

    tel = meta.get("telemetry")
    if not isinstance(tel, dict):
        tel = {}
    # ---- Scorer block (minimal, deterministic) ----
    sc = tel.get("scorer") or {}
    impl_raw = getattr(getattr(cfg, "scorer_params", None), "impl", None)
    impl_str = getattr(impl_raw, "value", impl_raw) if impl_raw is not None else "auto"

    dev_raw = getattr(getattr(cfg, "cipher", None), "device", None)
    try:
        dev_kind = ensure_device(dev_raw)
        dev_str = getattr(dev_kind, "value", str(dev_kind))
    except Exception:
        dev_str = str(dev_raw or "cpu")

    sc.setdefault("impl", impl_str)
    sc.setdefault("device", dev_str)
    tel["scorer"] = sc

    # ---- Solver block (minimal, deterministic) ----
    solver_cfg = getattr(cfg, "solver", None)
    solver_kind = getattr(solver_cfg, "kind", None)
    solver_name = getattr(solver_kind, "value", None) or getattr(solver_cfg, "name", None) or ""
    sv = tel.get("solver") or {}
    sv.setdefault("name", solver_name)
    tel["solver"] = sv

    # ---- Direction & pipeline passthrough if absent ----
    if "encoding_dir" not in tel:
        dir_raw = getattr(getattr(cfg, "scorer_params", None), "encoding_dir", None)
        tel["encoding_dir"] = getattr(dir_raw, "value", dir_raw) if dir_raw is not None else tel.get("encoding_dir", "ltr")

    meta["telemetry"] = tel

    # Optional convenience summary keys (non-binding)
    rm = meta.get("run_meta") or {}
    rm.setdefault("solver", solver_name)
    rm.setdefault("device", dev_str)
    meta["run_meta"] = rm
