from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.benchmarks.community._campaign_common import read_jsonl, write_json, write_jsonl
from tools.benchmarks.community.validate_run_bundle import (
    DEFAULT_MANIFEST_SCHEMA,
    DEFAULT_RESULT_SCHEMA,
    validate_run_bundle,
)


def _as_float(value: Any, *, default: float) -> float:
    try:
        out = float(value)
    except Exception:
        return float(default)
    if not math.isfinite(out):
        return float(default)
    return out


def _solved_priority(status: str) -> int:
    return 1 if str(status).strip().lower() == "solved" else 0


def _candidate_sort_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    row = candidate["row"]
    return (
        -_solved_priority(str(row.get("status", ""))),
        -_as_float(row.get("best_match_ratio"), default=0.0),
        _as_float(row.get("total_seconds"), default=float("inf")),
        str(candidate.get("runner_id", "")),
        str(candidate.get("finished_at_utc", "")),
        str(candidate.get("bundle_path", "")),
    )


def _choose_winner(candidates: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ordered = sorted(candidates, key=_candidate_sort_key)
    winner = ordered[0]
    discarded = ordered[1:]
    return winner, discarded


def combine_run_bundles(
    *,
    run_bundle_paths: list[Path],
    output_dir: Path,
    manifest_schema_path: Path,
    result_schema_path: Path,
    expected_campaign_id: str | None = None,
    expected_git_sha: str | None = None,
) -> dict[str, Any]:
    if not run_bundle_paths:
        raise ValueError("run_bundle_paths is empty")

    output_dir.mkdir(parents=True, exist_ok=True)
    sorted_bundles = sorted({p.resolve() for p in run_bundle_paths}, key=lambda p: str(p).lower())

    valid_bundles: list[dict[str, Any]] = []
    for bundle in sorted_bundles:
        report = validate_run_bundle(
            run_bundle_path=bundle,
            manifest_schema_path=manifest_schema_path,
            result_schema_path=result_schema_path,
            expected_campaign_id=expected_campaign_id,
            expected_git_sha=expected_git_sha,
            require_fastlm_true=True,
        )
        if not report["ok"]:
            raise ValueError(f"run bundle failed validation: {bundle} errors={report['errors']}")
        valid_bundles.append(report)

    by_job_id: dict[str, list[dict[str, Any]]] = {}
    for report in valid_bundles:
        bundle_path = Path(report["run_bundle_path"])
        run_meta = json.loads((bundle_path / "run_meta.json").read_text(encoding="utf-8"))
        rows = read_jsonl(bundle_path / "results.jsonl")
        for row in rows:
            job_id = str(row.get("job_id"))
            by_job_id.setdefault(job_id, []).append(
                {
                    "row": row,
                    "bundle_path": str(bundle_path),
                    "runner_id": str(run_meta.get("runner_id", "")),
                    "finished_at_utc": str(run_meta.get("finished_at_utc", "")),
                }
            )

    combined_rows: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    for job_id in sorted(by_job_id.keys()):
        candidates = by_job_id[job_id]
        winner, discarded = _choose_winner(candidates)
        combined_rows.append(dict(winner["row"]))
        if discarded:
            collisions.append(
                {
                    "job_id": job_id,
                    "winner": {
                        "runner_id": winner.get("runner_id"),
                        "bundle_path": winner.get("bundle_path"),
                        "finished_at_utc": winner.get("finished_at_utc"),
                        "status": winner["row"].get("status"),
                        "best_match_ratio": winner["row"].get("best_match_ratio"),
                        "total_seconds": winner["row"].get("total_seconds"),
                    },
                    "discarded": [
                        {
                            "runner_id": c.get("runner_id"),
                            "bundle_path": c.get("bundle_path"),
                            "finished_at_utc": c.get("finished_at_utc"),
                            "status": c["row"].get("status"),
                            "best_match_ratio": c["row"].get("best_match_ratio"),
                            "total_seconds": c["row"].get("total_seconds"),
                        }
                        for c in discarded
                    ],
                }
            )

    combined_path = output_dir / "combined_results.jsonl"
    collisions_path = output_dir / "collisions.jsonl"
    report_path = output_dir / "combine_report.json"
    write_jsonl(combined_path, combined_rows)
    write_jsonl(collisions_path, collisions)
    report = {
        "run_bundle_paths": [str(p) for p in sorted_bundles],
        "valid_bundle_count": len(valid_bundles),
        "combined_rows": len(combined_rows),
        "collision_rows": len(collisions),
        "combined_results_path": str(combined_path),
        "collisions_path": str(collisions_path),
    }
    write_json(report_path, report)
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Combine validated run_bundle results (v1.1).")
    parser.add_argument(
        "--run-bundle",
        type=Path,
        action="append",
        required=True,
        help="path to run_bundle directory (repeat flag for multiple bundles)",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="output directory")
    parser.add_argument(
        "--manifest-schema",
        type=Path,
        default=DEFAULT_MANIFEST_SCHEMA,
        help=f"path to manifest schema json (default: {DEFAULT_MANIFEST_SCHEMA})",
    )
    parser.add_argument(
        "--result-schema",
        type=Path,
        default=DEFAULT_RESULT_SCHEMA,
        help=f"path to result schema json (default: {DEFAULT_RESULT_SCHEMA})",
    )
    parser.add_argument("--campaign-id", type=str, default=None, help="optional expected campaign_id")
    parser.add_argument("--git-sha", type=str, default=None, help="optional expected git_sha")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = combine_run_bundles(
        run_bundle_paths=args.run_bundle,
        output_dir=args.output_dir,
        manifest_schema_path=args.manifest_schema,
        result_schema_path=args.result_schema,
        expected_campaign_id=args.campaign_id,
        expected_git_sha=args.git_sha,
    )
    print(
        "[community] combine complete "
        f"bundles={report['valid_bundle_count']} rows={report['combined_rows']} collisions={report['collision_rows']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
