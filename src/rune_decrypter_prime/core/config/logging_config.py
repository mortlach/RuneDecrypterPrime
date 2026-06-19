# # ============================================================
# # rune_decrypter_prime/core/logging_config.py
# # Single-source logging config + run-dir lifecycle (no CLI).
# # ============================================================
from __future__ import annotations

import getpass
import json
import os
import socket
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import subprocess

# TODO(core/logging_config): avoid importing array libraries directly use dynamic __import__ with non-literal module tokens or collect versions in an allow-listed module.

# TODO(core/logging_config): move library-name literals into core/telemetry_helpers.py and reference them from here.

# ----------------------------
# Public configuration model
# ----------------------------

@dataclass
class LoggingConfig:
    """
    Configuration for initializing a run's logging/telemetry directories.

    Fields mirror the existing codebase to avoid breaking callers:
      - verbose:                     enable verbose console logging
      - print_progress:              allow progress printing
      - write_jsonl:                 write JSONL event stream under logs/
      - repo_root:                   explicit repository root (optional)
      - out_root:                    base output directory (optional, default: <repo_root>/out)
      - run_kind:                    short tag for the run kind (e.g., "test", "bench", "solve")
      - label:                       human-friendly label to include in the run directory name
      - fixed_run_dir:               if set, use this exact directory (absolute or relative to out_root/runs)
      - write_solver_report:         write artifacts/solver_report.json
      - write_rdp_display_summary:   write artifacts/rdp_display_summary.json
      - write_run_artifacts_manifest: write artifacts/run_artifacts_manifest.json

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
    redact_identity: bool = False
    portable_output: bool = False
    write_solver_report: bool = False
    write_rdp_display_summary: bool = False
    write_run_artifacts_manifest: bool = False

    def __post_init__(self) -> None:
        if type(self.write_solver_report) is not bool:
            raise TypeError("write_solver_report must be a bool")
        if type(self.write_rdp_display_summary) is not bool:
            raise TypeError("write_rdp_display_summary must be a bool")
        if type(self.write_run_artifacts_manifest) is not bool:
            raise TypeError("write_run_artifacts_manifest must be a bool")

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
    return repo_root / "output"


def _relativize_path(path: Path, base: Path) -> str:
    """
    Return a repo-local representation of `path`. Prefers Path.relative_to when possible,
    falls back to os.path.relpath, and ultimately to the basename if drives differ.
    """
    path = path.resolve()
    base = base.resolve()
    if path == base:
        return "."
    try:
        rel = path.relative_to(base)
        rel_str = rel.as_posix()
        return rel_str or "."
    except ValueError:
        try:
            rel = os.path.relpath(path, base)
            rel_str = rel.replace("\\", "/")
            return rel_str or "."
        except Exception:
            return path.name


def _effective_redact_identity(cfg: LoggingConfig) -> bool:
    return bool(cfg.redact_identity or cfg.portable_output)


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


def _git_info(repo_root: Path) -> Dict[str, Any]:
    info: Dict[str, Any] = {"commit": None, "short": None, "dirty": None}
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return info
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        short = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        dirty = subprocess.call(
            ["git", "diff", "--quiet"], cwd=repo_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ) != 0
        info.update({"commit": commit, "short": short, "dirty": dirty})
    except Exception:
        pass
    return info


def _write_meta(
    run_dir: Path,
    cfg: LoggingConfig,
    timestamp: str,
    repo_root: Path,
    out_root: Path,
    run_id: str,
    git_info: Dict[str, Any],
    kind_token: str,
) -> None:
    """
    Writes META.json into the run directory with stable, machine-readable keys.
    Includes both new contract keys and legacy fields for back-compat.
    """
    identity_redacted = _effective_redact_identity(cfg)
    meta: Dict[str, Any] = {
        # Legacy/previously observed fields (kept to avoid breaking readers)
        "created": timestamp,
        "user": None if identity_redacted else getpass.getuser(),
        "host": None if identity_redacted else socket.gethostname(),
        "repo_root": ".",
        "out_root": _relativize_path(out_root, repo_root),
        "run_kind": cfg.run_kind,
        "label": cfg.label,
        "verbose": cfg.verbose,
        "print_progress": cfg.print_progress,
        "write_jsonl": cfg.write_jsonl,
        "portable_output": bool(cfg.portable_output),
        "identity_redacted": identity_redacted,
        "pid": os.getpid(),
        "python": {
            "executable": Path(os.sys.executable).name,
            "version": os.sys.version,
        },
        # New, explicit contract keys:
        "timestamp": timestamp,
        "run_id": run_id,
        "kind": kind_token,
        "versions": _collect_versions(),
        "git": git_info,
    }

    if cfg.run_kind == "tests":
        short = git_info.get("short") or "nogit"
        meta["test_id"] = f"{short}-{timestamp}"
    logs_dir = run_dir / "logs"
    trace_dir = run_dir / "trace"
    artifacts_dir = run_dir / "artifacts"
    meta["pointers"] = {
        "logs": _relativize_path(logs_dir, repo_root),
        "trace": _relativize_path(trace_dir, repo_root),
        "artifacts": _relativize_path(artifacts_dir, repo_root),
    }

    (run_dir / "META.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _write_logging_snapshot(run_dir: Path, cfg: LoggingConfig, repo_root: Path, out_root: Path) -> None:
    snap = asdict(cfg)
    snap["repo_root"] = "."
    snap["out_root"] = _relativize_path(out_root, repo_root)
    value = snap.get("fixed_run_dir")
    if value:
        snap["fixed_run_dir"] = _relativize_path(Path(str(value)), repo_root)
    config_dir = run_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "logging.json").write_text(json.dumps(snap, indent=2), encoding="utf-8")


def _ensure_dirs(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)

# ----------------------------
# Public entry point
# ----------------------------

def init_logging(cfg: LoggingConfig) -> Path:
    """
    Initialize the run directory structure and write META/config snapshots.

    Returns:
        Path to the run directory.

    Side effects:
        - Creates <out_root>/<run_kind>/<run_id>/ with logs/, trace/, artifacts/.
        - Stores META.json and config/logging.json for reproducibility.
        - Updates module-global _PATHS so get_run_dir() and current_paths() work.
    """
    repo_root = Path(cfg.repo_root).resolve() if cfg.repo_root else _detect_repo_root()
    out_root = Path(cfg.out_root).resolve() if cfg.out_root else _default_out_root(repo_root)

    ts = _now_stamp()
    kind_token = _safe_token(cfg.run_kind, "run")
    label_token = _safe_token(cfg.label, kind_token)
    git_info = _git_info(repo_root)
    git_token = git_info.get("short") or "nogit"
    run_id = f"{ts}__{kind_token}__{label_token}__{git_token}"
    kind_root = out_root / kind_token

    if cfg.fixed_run_dir:
        fixed = Path(cfg.fixed_run_dir)
        if fixed.is_absolute():
            run_dir = fixed.resolve()
        else:
            run_dir = (kind_root / fixed).resolve()
    else:
        run_dir = (kind_root / run_id).resolve()

    logs_dir = run_dir / "logs"
    trace_dir = run_dir / "trace"
    artifacts_dir = run_dir / "artifacts"

    _ensure_dirs(logs_dir)
    _ensure_dirs(trace_dir)
    _ensure_dirs(artifacts_dir)

    _write_meta(run_dir, cfg, timestamp=ts, repo_root=repo_root, out_root=out_root,
                run_id=run_dir.name, git_info=git_info, kind_token=kind_token)
    _write_logging_snapshot(run_dir, cfg, repo_root=repo_root, out_root=out_root)

    _PATHS.clear()
    _PATHS.update({
        "run_dir": str(run_dir),
        "logs_dir": str(logs_dir),
        "trace_dir": str(trace_dir),
    })

    return run_dir
