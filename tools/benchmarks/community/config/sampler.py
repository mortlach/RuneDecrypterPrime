from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Mapping

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.benchmarks.community._campaign_common import load_json, write_json
from tools.benchmarks.community.config.profile_config import (
    PIPELINE_DEFAULT,
    load_knob_ranges,
    load_profile_catalog_from_path,
)


def _get_profile(catalog_path: Path, profile_id: str) -> dict[str, Any]:
    data = load_json(catalog_path)
    profiles = data.get("profiles", [])
    if not isinstance(profiles, list):
        raise ValueError("profile_catalog.profiles must be a list")
    for profile in profiles:
        if isinstance(profile, dict) and str(profile.get("profile_id")) == str(profile_id):
            return profile
    raise ValueError(f"profile_id not found: {profile_id}")


def _rand_int(rng: random.Random, lo: int, hi: int) -> int:
    if hi < lo:
        lo, hi = hi, lo
    return int(rng.randint(int(lo), int(hi)))


def _build_sample_overrides(
    *,
    base_overrides: Mapping[str, Any],
    ranges_data: Mapping[str, Any],
    rng: random.Random,
) -> dict[str, Any]:
    out = dict(base_overrides)
    space = ranges_data.get("sampling_spaces", {}).get("community_safe", {})
    if not isinstance(space, Mapping):
        return out

    scalar_ranges = space.get("scalar_ranges", {})
    if isinstance(scalar_ranges, Mapping):
        stage12 = dict(out.get("stage12_carry_through", {}))
        if "stage12_carry_through.promote_top" in scalar_ranges:
            lo, hi = scalar_ranges["stage12_carry_through.promote_top"]
            stage12["promote_top"] = _rand_int(rng, int(lo), int(hi))
        if "stage12_carry_through.archive_keep" in scalar_ranges:
            lo, hi = scalar_ranges["stage12_carry_through.archive_keep"]
            stage12["archive_keep"] = _rand_int(rng, int(lo), int(hi))
        if stage12:
            out["stage12_carry_through"] = stage12

    map_ranges = space.get("map_ranges", {})
    if isinstance(map_ranges, Mapping):
        stage1 = dict(out.get("stage1_breadth", {}))
        spec1 = map_ranges.get("stage1_breadth.sub_candidates_by_columns")
        if isinstance(spec1, Mapping):
            cols = [int(x) for x in spec1.get("columns", [])]
            lo = int(spec1.get("min", 8))
            hi = int(spec1.get("max", 64))
            stage1["sub_candidates_by_columns"] = {str(c): _rand_int(rng, lo, hi) for c in cols}
            out["stage1_breadth"] = stage1

        stage3 = dict(out.get("stage3_basin_exploration", {}))
        spec3 = map_ranges.get("stage3_basin_exploration.initial_keys_by_columns")
        if isinstance(spec3, Mapping):
            cols = [int(x) for x in spec3.get("columns", [])]
            lo = int(spec3.get("min", 12))
            hi = int(spec3.get("max", 64))
            stage3["initial_keys_by_columns"] = {str(c): _rand_int(rng, lo, hi) for c in cols}
            out["stage3_basin_exploration"] = stage3

    # Keep stage3 gating untouched unless base already set it.
    if "stage3_gating" not in out:
        out["stage3_gating"] = {
            "full_entry_score": PIPELINE_DEFAULT,
            "probe_entry_score": PIPELINE_DEFAULT,
        }

    return out


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample random community benchmark profiles from predefined ranges.")
    parser.add_argument(
        "--profile-catalog",
        type=Path,
        default=Path("tools/benchmarks/community/profile_catalog_v1_1.json"),
        help="Source profile catalog.",
    )
    parser.add_argument(
        "--ranges",
        type=Path,
        default=Path("tools/benchmarks/community/config/ranges_v1_1.json"),
        help="Knob ranges file.",
    )
    parser.add_argument("--base-profile-id", type=str, required=True, help="Base profile row to mutate.")
    parser.add_argument("--count", type=int, default=5, help="Number of sampled profiles.")
    parser.add_argument("--seed", type=int, default=12345, help="Deterministic random seed.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("tools/benchmarks/community/examples/sampled_profiles_v1_1.json"),
        help="Output JSON file.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    load_profile_catalog_from_path(args.profile_catalog, knob_ranges_path=args.ranges)
    ranges_data = load_json(args.ranges)
    base = _get_profile(args.profile_catalog, args.base_profile_id)
    base_overrides = base.get("overrides", {})
    if not isinstance(base_overrides, Mapping):
        raise ValueError("base profile overrides must be an object")

    rng = random.Random(int(args.seed))
    sampled_profiles: list[dict[str, Any]] = []
    for idx in range(int(max(1, args.count))):
        overrides = _build_sample_overrides(base_overrides=base_overrides, ranges_data=ranges_data, rng=rng)
        sampled_profiles.append(
            {
                "profile_id": f"{args.base_profile_id}__sample_{idx + 1:03d}",
                "description": f"Sampled from {args.base_profile_id} with seed {args.seed}.",
                "scorer_schedule": dict(base.get("scorer_schedule", {})),
                "overrides": overrides,
            }
        )

    payload = {
        "sampled_from_profile": str(args.base_profile_id),
        "seed": int(args.seed),
        "count": int(max(1, args.count)),
        "profiles": sampled_profiles,
    }
    write_json(args.out, payload)
    print(f"Wrote sampled profiles: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

