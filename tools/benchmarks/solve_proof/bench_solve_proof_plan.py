from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ACTIVE_PROFILE = "proof_standard_2h"


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    period: int
    columns: int
    length: int
    enabled: bool


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _main() -> None:
    base = Path(__file__).resolve().parent
    fixtures_cfg = _load_json(base / "fixtures_periodic_columnar_v1.json")
    profiles_cfg = _load_json(base / "solver_profiles_v1.json")

    fixtures = {
        row["fixture_id"]: Fixture(
            fixture_id=str(row["fixture_id"]),
            period=int(row["period"]),
            columns=int(row["columns"]),
            length=int(row["length"]),
            enabled=bool(row.get("enabled", True)),
        )
        for row in fixtures_cfg.get("tiers", [])
    }
    profiles = {str(p["profile_id"]): p for p in profiles_cfg.get("profiles", [])}
    if ACTIVE_PROFILE not in profiles:
        raise ValueError(f"Unknown ACTIVE_PROFILE={ACTIVE_PROFILE!r}")
    prof = profiles[ACTIVE_PROFILE]

    tiers = [fixtures[t] for t in prof.get("tiers", []) if t in fixtures and fixtures[t].enabled]
    text_offsets = [int(x) for x in prof.get("text_offsets", [])]
    key_seeds = [int(x) for x in prof.get("key_seeds", [])]
    modes = [str(x) for x in prof.get("modes", [])]

    rows = []
    run_idx = 0
    for tier in tiers:
        for text_id, off in enumerate(text_offsets):
            for key_seed in key_seeds:
                for mode in modes:
                    run_idx += 1
                    rows.append(
                        {
                            "run_index": run_idx,
                            "fixture_id": tier.fixture_id,
                            "period": tier.period,
                            "columns": tier.columns,
                            "length": tier.length,
                            "mode": mode,
                            "text_id": text_id,
                            "offset": off,
                            "key_seed": key_seed,
                        }
                    )

    out_root = _repo_root() / "output" / "tools" / "benchmarks"
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"{stamp}__solve_proof_plan"
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "kind": "solve_proof_plan",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "active_profile": ACTIVE_PROFILE,
        "fixture_file": "tools/benchmarks/solve_proof/fixtures_periodic_columnar_v1.json",
        "profile_file": "tools/benchmarks/solve_proof/solver_profiles_v1.json",
        "tiers": [t.fixture_id for t in tiers],
        "text_offsets": text_offsets,
        "key_seeds": key_seeds,
        "modes": modes,
        "planned_runs": len(rows),
        "estimated_wall_minutes": int(prof.get("estimated_wall_minutes", 0) or 0),
    }
    (run_dir / "plan_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with (run_dir / "planned_runs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["run_index"])
        w.writeheader()
        w.writerows(rows)

    print(
        f"[solve_proof_plan] profile={ACTIVE_PROFILE} runs={len(rows)} "
        f"est={manifest['estimated_wall_minutes']}m output={run_dir.relative_to(_repo_root())}",
        flush=True,
    )


if __name__ == "__main__":
    _main()
