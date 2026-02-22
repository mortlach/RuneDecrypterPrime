from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def output_root() -> Path:
    """Canonical benchmark output root (mirrors tools/ path under output/)."""
    return repo_root() / "output" / "tools" / "benchmarks"


def run_tag(default: str = "nogit") -> str:
    """
    Deterministic run label suffix without invoking git.

    If RDP_RUN_TAG is set, use it (trimmed). Otherwise fall back to "nogit".
    """
    value = os.environ.get("RDP_RUN_TAG", "").strip()
    return value or default


def make_flavor_run_dir(*, flavor: str, run_prefix: str = "bench_solve_pipeline") -> Path:
    """Create a run directory under output/tools/benchmarks/periodic_sub_trans/<flavor>/."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = output_root() / "periodic_sub_trans" / str(flavor).strip()
    out.mkdir(parents=True, exist_ok=True)
    run_dir = out / f"{stamp}__{run_prefix}__{run_tag()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def ensure_output_path_policy(path: Path) -> None:
    """Raise if path is not under output/tools/benchmarks."""
    root = output_root().resolve()
    resolved = path.resolve()
    if root == resolved:
        return
    if root not in resolved.parents:
        raise ValueError(f"Path violates output policy: {resolved} (must be under {root})")
