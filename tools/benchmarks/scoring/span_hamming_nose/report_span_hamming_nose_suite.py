from __future__ import annotations

import json
from pathlib import Path


RUN_DIR_OVERRIDE: str | None = None
RUN_ROOT = Path("output/tools/benchmarks/scoring/span_hamming_nose_suite")
WRITE_REPORT_FILE = False
REPORT_OUTPUT_PATH = Path("output/tools/benchmarks/scoring/span_hamming_nose_suite/report_latest.txt")


def build_report(run_dir: Path) -> str:
    calibration_path = run_dir / "calibration.json"
    summary_path = run_dir / "summary.csv"
    if not calibration_path.exists():
        raise FileNotFoundError(f"Missing calibration file: {calibration_path}")
    payload = json.loads(calibration_path.read_text(encoding="utf-8"))
    calibrations = list(payload.get("calibrations", []))
    stable = []
    for row in calibrations:
        if "unstable" in row:
            if not bool(row.get("unstable", True)):
                stable.append(row)
            continue
        if bool(row.get("span_norm_valid", False)):
            stable.append(row)

    lines = []
    lines.append(f"run_dir={run_dir}")
    lines.append(f"calibration_rows={len(calibrations)}")
    lines.append(f"stable_rows={len(stable)}")
    lines.append(f"summary_csv_exists={summary_path.exists()}")
    for row in sorted(stable, key=lambda item: (item.get("direction", ""), int(item.get("length_bucket", 0)))):
        lines.append(
            "stable direction={direction} length={length_bucket} auc={auc:.4f} denom={denom:.6f}".format(
                direction=row.get("direction", ""),
                length_bucket=int(row.get("length_bucket", 0)),
                auc=float(row.get("auc", 0.0)),
                denom=float(row.get("denom", 0.0)),
            )
        )
    return "\n".join(lines)


def _resolve_latest_run_dir(root: Path) -> Path:
    if not root.exists():
        raise FileNotFoundError(f"Run root not found: {root}")
    candidates = [
        p
        for p in root.iterdir()
        if p.is_dir() and p.name.endswith("__span_hamming_nose_suite")
    ]
    if not candidates:
        raise FileNotFoundError(f"No suite runs found under: {root}")
    return sorted(candidates, key=lambda p: p.name)[-1]


def main() -> int:
    if RUN_DIR_OVERRIDE is not None:
        run_dir = Path(RUN_DIR_OVERRIDE).resolve()
    else:
        run_dir = _resolve_latest_run_dir(RUN_ROOT.resolve())
    report = build_report(run_dir)
    print(report)
    if WRITE_REPORT_FILE:
        REPORT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_OUTPUT_PATH.write_text(report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
