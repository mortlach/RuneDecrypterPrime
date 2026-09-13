from __future__ import annotations

import json
from pathlib import Path

from rdp.api.solver_report import SolverReport


def write_solver_report_json(report: SolverReport, *, run_dir: Path) -> str:
    if not isinstance(report, SolverReport):
        raise TypeError("report must be a SolverReport")
    if not isinstance(run_dir, Path):
        raise TypeError("run_dir must be a Path")

    run_root = run_dir.resolve()
    artifacts_dir = (run_root / "artifacts").resolve()
    if not artifacts_dir.is_relative_to(run_root):
        raise ValueError("solver report artifacts directory must be under run_dir")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifacts_dir / "solver_report.json"
    report_path.write_text(
        json.dumps(report.to_json_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return "artifacts/solver_report.json"


__all__ = ["write_solver_report_json"]
