from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def output_root() -> Path:
    """Canonical benchmark output root (mirrors tools/ path under output/)."""
    return repo_root() / "output" / "tools" / "benchmarks"


def run_tag(default: str = "nogit") -> str:
    """
    Deterministic run label suffix.

    Uses current git short SHA when available, otherwise falls back to `default`.
    """
    root = repo_root()
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=root,
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
            or default
        )
    except Exception:
        return default


def make_flavor_run_dir(*, flavor: str, run_prefix: str = "bench_solve_pipeline") -> Path:
    """Create a run directory under output/tools/benchmarks/periodic_sub_trans/<flavor>/."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = output_root() / "periodic_sub_trans" / str(flavor).strip()
    out.mkdir(parents=True, exist_ok=True)
    base_name = f"{stamp}__{run_prefix}__{run_tag()}"
    for n in range(0, 1000):
        run_name = base_name if n == 0 else f"{base_name}__r{int(n)}"
        run_dir = out / run_name
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            return run_dir
        except FileExistsError:
            continue
    raise RuntimeError(f"Unable to allocate unique run directory under {out}")


def ensure_output_path_policy(path: Path) -> None:
    """Raise if path is not under output/tools/benchmarks."""
    root = output_root().resolve()
    resolved = path.resolve()
    if root == resolved:
        return
    if root not in resolved.parents:
        raise ValueError(f"Path violates output policy: {resolved} (must be under {root})")
