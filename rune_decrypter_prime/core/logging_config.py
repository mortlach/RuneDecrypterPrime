# # ============================================================
# # rune_decrypter_prime/core/logging_config.py
# # Single-source logging config + run-dir lifecycle (no CLI).
# # ============================================================
from __future__ import annotations

import getpass
import json
import os
import socket
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# ----------------------------
# Public configuration model
# ----------------------------

@dataclass
class LoggingConfig:
    """
    Configuration for initializing a run's logging/telemetry directories.

    Fields mirror the existing codebase to avoid breaking callers:
      - verbose:         enable verbose console logging
      - print_progress:  allow progress printing
      - write_jsonl:     write JSONL event stream under logs/
      - repo_root:       explicit repository root (optional)
      - out_root:        base output directory (optional, default: <repo_root>/out)
      - run_kind:        short tag for the run kind (e.g., "test", "bench", "solve")
      - label:           human-friendly label to include in the run directory name
      - fixed_run_dir:   if set, use this exact directory (absolute or relative to out_root/runs)

    No environment variables or CLI flags are read here—config is explicit.
    """
    verbose: bool = True
    print_progress: bool = True
    write_jsonl: bool = True
    repo_root: Optional[str] = None
    out_root: Optional[str] = None
    run_kind: str = "run"
    label: Optional[str] = None
    fixed_run_dir: Optional[str] = None

# ----------------------------
# Module state & simple accessors
# ----------------------------

_PATHS: Dict[str, str] = {}  # updated by init_logging()


def get_run_dir() -> Path:
    """
    Returns the current run directory as a Path.
    Raises RuntimeError if init_logging() has not been called.
    """
    rd = _PATHS.get("run_dir")
    if not rd:
        raise RuntimeError("get_run_dir() called before init_logging().")
    return Path(rd)


def current_paths() -> Dict[str, str]:
    """
    Returns a shallow copy of the current paths mapping:
      {"run_dir", "logs_dir", "trace_dir"}  (string paths)
    """
    return dict(_PATHS)


# ----------------------------
# Internal helpers
# ----------------------------

def _now_stamp() -> str:
    """
    Returns a filesystem-safe timestamp string, e.g., '20250906_141742'.
    No timezone required; consumers can infer local time if needed.
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_token(s: Optional[str], default: str = "run") -> str:
    """
    Sanitizes a short label for inclusion in a directory name.
    Keeps alphanumerics, '-', '_' and converts spaces to '-'.
    """
    if not s:
        return default
    s = s.strip().replace(" ", "-")
    return "".join(ch for ch in s if ch.isalnum() or ch in ("-", "_")).lower() or default


def _detect_repo_root(start: Optional[Path] = None) -> Path:
    """
    Heuristic repo root detection: walk up until we find a VCS marker or
    the project sentinel. Falls back to the current working directory.
    """
    p = (start or Path.cwd()).resolve()
    sentinels = {".git", ".hg", "pyproject.toml", "rune_decrypter_prime"}
    for ancestor in [p, *p.parents]:
        try:
            names = {x.name for x in ancestor.iterdir()}
        except Exception:
            continue
        if names & sentinels:
            return ancestor
    return p


def _default_out_root(repo_root: Path) -> Path:
    return repo_root / "out"


def _collect_versions() -> Dict[str, Any]:
    """
    Minimal version map for telemetry. Extend here centrally if needed.
    """
    v: Dict[str, Any] = {
        "python": os.sys.version,
    }
    try:
        import numpy as _np  # type: ignore
        v["numpy"] = getattr(_np, "__version__", None)
    except Exception:
        pass
    try:
        import torch as _torch  # type: ignore
        v["torch"] = getattr(_torch, "__version__", None)
    except Exception:
        pass
    return v


def _write_meta(run_dir: Path, cfg: LoggingConfig, timestamp: str) -> None:
    """
    Writes META.json into the run directory with stable, machine-readable keys.
    Includes both new contract keys and legacy fields for back-compat.
    """
    repo_root = Path(cfg.repo_root).resolve() if cfg.repo_root else _detect_repo_root()
    out_root = Path(cfg.out_root).resolve() if cfg.out_root else _default_out_root(repo_root)

    meta: Dict[str, Any] = {
        # Legacy/previously observed fields (kept to avoid breaking readers)
        "created": timestamp,
        "user": getpass.getuser(),
        "host": socket.gethostname(),
        "repo_root": str(repo_root),
        "out_root": str(out_root),
        "run_kind": cfg.run_kind,
        "label": cfg.label,
        "verbose": cfg.verbose,
        "print_progress": cfg.print_progress,
        "write_jsonl": cfg.write_jsonl,
        "pid": os.getpid(),
        "python": {
            "executable": os.sys.executable,
            "version": os.sys.version,
        },
        # New, explicit contract keys:
        "timestamp": timestamp,
        "run_id": run_dir.name,
        "versions": _collect_versions(),
    }

    (run_dir / "META.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _ensure_dirs(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)


# ----------------------------
# Public entry point
# ----------------------------

def init_logging(cfg: LoggingConfig) -> Path:
    """
    Initialize the run directory structure and write META.json.

    Returns:
        Path to the run directory.

    Side effects:
        - Creates <out_root>/runs/<run_id> with subfolders logs/ and trace/.
        - Updates module-global _PATHS so get_run_dir() and current_paths() work.
        - No environment variables or CLI flags are read.
    """
    repo_root = Path(cfg.repo_root).resolve() if cfg.repo_root else _detect_repo_root()
    out_root = Path(cfg.out_root).resolve() if cfg.out_root else _default_out_root(repo_root)

    # Directory naming: timestamp + kind + label (sanitized). No timezone.
    ts = _now_stamp()

    if cfg.fixed_run_dir:
        run_dir = Path(cfg.fixed_run_dir)
        if not run_dir.is_absolute():
            run_dir = out_root / "runs" / run_dir
    else:
        kind = _safe_token(cfg.run_kind, "run")
        label = _safe_token(cfg.label, "run")
        run_id = f"{ts}_{kind}_{label}"
        run_dir = out_root / "runs" / run_id

    logs_dir = run_dir / "logs"
    trace_dir = run_dir / "trace"

    _ensure_dirs(logs_dir)
    _ensure_dirs(trace_dir)

    _write_meta(run_dir, cfg, timestamp=ts)

    # Update public path map (strings for JSON compatibility / simplicity)
    _PATHS.clear()
    _PATHS.update({
        "run_dir": str(run_dir),
        "logs_dir": str(logs_dir),
        "trace_dir": str(trace_dir),
    })

    return run_dir
