from __future__ import annotations

"""
Build span_hamming_nose scorer assets (including word-length / profile features)
from one or more completed benchmark shard outputs.

IDE-friendly:
- edit the CONFIG block below
- run in PyCharm
- no CLI required

Inputs
------
This script expects completed run folders (either as directories, or inside .zip files).
Each run folder must contain:
- samples.csv
- summary.csv
- calibration.json

For word-length/profile features, samples.csv must include (JSON-serialised) columns:
- length_bins
- span_raw_by_len
- chars_covered_by_len

These columns exist only when WRITE_DETAILED_SAMPLE_FIELDS=True in the bench run.

Outputs
-------
- <OUTPUT_BASENAME>.json
- <OUTPUT_BASENAME>_manifest.json
- <OUTPUT_BASENAME>_group_summary.csv
"""

import csv
import io
import json
import math
import statistics
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Sequence, Tuple


# =============================================================================
# CONFIG
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parents[4]

INPUT_PATHS = [
    # Use real shard run directories (not zip archives).
    r"output/tools/benchmarks/scoring/span_hamming_nose_suite/20260304T053856Z__span_hamming_nose_suite__shard0of2",
    r"output/tools/benchmarks/scoring/span_hamming_nose_suite/20260304T053856Z__span_hamming_nose_suite__shard1of2",
]

OUTPUT_DIR = r"output/tools/benchmarks/scoring/span_hamming_nose_assets_wordlen_v1/20260304T053856Z__span_hamming_nose_assets_wordlen_v1"
OUTPUT_BASENAME = "span_hamming_nose_assets_wordlen_v1"
RUN_LABEL = "20260304T053856Z"

REQUIRE_COMPLETE_COVERAGE = True
REQUIRE_DETAILED_FIELDS = True

WRITE_GROUP_SUMMARY_CSV = True
WRITE_DEBUG_MANIFEST_JSON = True

# Keep these as hints only. Runtime should trust profile_length_bins.
LENGTH_BIN_EDGE_HINTS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]

QUANTILE_GRID = [
    0.001, 0.005, 0.01, 0.02, 0.05,
    0.10, 0.20, 0.30, 0.40, 0.50,
    0.60, 0.70, 0.80, 0.90, 0.95,
    0.98, 0.99, 0.995, 0.999,
]

SCALAR_MEASURES = ["quality", "coverage", "span_raw"]
PROFILE_VECTOR_MEASURES = ["span_raw_by_len", "chars_covered_by_len"]

REAL_GENERATOR = "REAL"
NOISE_GENERATORS = ("RAND_UNIGRAM", "SHUFFLE_UNIGRAM")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class SourceEntry:
    source_path: str
    kind: str  # "zip" or "dir"
    member_path: str
    run_dir_name: str
    file_name: str


# =============================================================================
# SOURCE DISCOVERY
# =============================================================================

def _resolve_repo_path(path_like: str | Path) -> Path:
    p = Path(path_like).expanduser()
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


def _iter_source_entries(input_paths: Sequence[str]) -> Iterator[SourceEntry]:
    for raw_path in input_paths:
        path = _resolve_repo_path(raw_path)
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {path}")

        if path.is_file() and path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path, "r") as zf:
                for member_name in zf.namelist():
                    if member_name.endswith("/"):
                        continue
                    parts = member_name.split("/")
                    if len(parts) < 2:
                        continue
                    run_dir_name = parts[0]
                    file_name = parts[-1]
                    if file_name not in {"samples.csv", "summary.csv", "calibration.json", "samples.jsonl"}:
                        continue
                    yield SourceEntry(
                        source_path=str(path),
                        kind="zip",
                        member_path=member_name,
                        run_dir_name=run_dir_name,
                        file_name=file_name,
                    )
        elif path.is_dir():
            direct_files = {"samples.csv", "summary.csv", "calibration.json"} & {p.name for p in path.iterdir() if p.is_file()}
            if direct_files:
                # Support direct run folders passed in INPUT_PATHS.
                for file_name in sorted(direct_files):
                    file_path = path / file_name
                    yield SourceEntry(
                        source_path=str(path),
                        kind="dir",
                        member_path=str(file_path),
                        run_dir_name=path.name,
                        file_name=file_name,
                    )
                continue

            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.name not in {"samples.csv", "summary.csv", "calibration.json", "samples.jsonl"}:
                    continue
                rel_parts = file_path.relative_to(path).parts
                if len(rel_parts) < 2:
                    continue
                yield SourceEntry(
                    source_path=str(path),
                    kind="dir",
                    member_path=str(file_path),
                    run_dir_name=rel_parts[0],
                    file_name=file_path.name,
                )
        else:
            raise ValueError(f"Unsupported input path: {path}")


def discover_runs(input_paths: Sequence[str]) -> Dict[str, Dict[str, SourceEntry]]:
    runs: Dict[str, Dict[str, SourceEntry]] = defaultdict(dict)
    for entry in _iter_source_entries(input_paths):
        runs[entry.run_dir_name][entry.file_name] = entry

    if not runs:
        raise RuntimeError("No shard outputs were found in INPUT_PATHS.")

    for run_dir_name, files in sorted(runs.items()):
        missing = {"samples.csv", "summary.csv", "calibration.json"} - set(files)
        if missing:
            raise RuntimeError(f"Run {run_dir_name} is missing required files: {sorted(missing)}")

    return dict(sorted(runs.items()))


# =============================================================================
# FILE IO HELPERS
# =============================================================================

def _open_text(entry: SourceEntry):
    if entry.kind == "zip":
        zf = zipfile.ZipFile(entry.source_path, "r")
        raw = zf.open(entry.member_path, "r")
        text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
        return zf, raw, text

    raw = open(entry.member_path, "r", encoding="utf-8", newline="")
    return None, raw, raw


def load_json(entry: SourceEntry) -> dict:
    zf, raw, text = _open_text(entry)
    try:
        return json.load(text)
    finally:
        text.close()
        raw.close()
        if zf is not None:
            zf.close()


def iter_csv_rows(entry: SourceEntry) -> Iterator[dict]:
    zf, raw, text = _open_text(entry)
    try:
        reader = csv.DictReader(text)
        for row in reader:
            yield row
    finally:
        text.close()
        raw.close()
        if zf is not None:
            zf.close()


# =============================================================================
# NUMERIC HELPERS
# =============================================================================

def parse_json_float_vector(value: str) -> List[float]:
    vec = json.loads(value)
    return [float(x) for x in vec]


def parse_json_int_vector(value: str) -> List[int]:
    vec = json.loads(value)
    return [int(x) for x in vec]


def normalise_vector(vec: Sequence[float]) -> List[float]:
    total = float(sum(vec))
    if total <= 0.0:
        return [0.0 for _ in vec]
    return [float(x) / total for x in vec]


def vector_add_inplace(dst: List[float], src: Sequence[float]) -> None:
    if len(dst) != len(src):
        raise ValueError(f"Vector length mismatch: {len(dst)} != {len(src)}")
    for i, value in enumerate(src):
        dst[i] += float(value)


def vector_mean(sum_vec: Sequence[float], count: int) -> List[float]:
    if count <= 0:
        return [0.0 for _ in sum_vec]
    return [float(x) / float(count) for x in sum_vec]


def l1_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return float(sum(abs(float(x) - float(y)) for x, y in zip(a, b)))


def weighted_mean_index(profile: Sequence[float]) -> float:
    return float(sum(i * float(value) for i, value in enumerate(profile)))


def weighted_mean_bin_value(profile: Sequence[float], length_bins: Sequence[int]) -> float:
    # length_bins are labels produced by the backend and recorded in samples.csv
    if len(profile) != len(length_bins):
        raise ValueError(f"profile/length_bins mismatch: {len(profile)} != {len(length_bins)}")
    return float(sum(float(length_bins[i]) * float(profile[i]) for i in range(len(profile))))


def tail_mass(profile: Sequence[float], start_index: int) -> float:
    return float(sum(float(x) for x in profile[start_index:]))


def percentile_sorted(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = q * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(sorted_values[lower])
    lower_value = float(sorted_values[lower])
    upper_value = float(sorted_values[upper])
    fraction = position - lower
    return lower_value + (upper_value - lower_value) * fraction


def quantiles_from_values(values: Sequence[float], quantile_grid: Sequence[float]) -> List[float]:
    if not values:
        return [0.0 for _ in quantile_grid]
    sorted_values = sorted(float(v) for v in values)
    return [percentile_sorted(sorted_values, q) for q in quantile_grid]


def stats_dict(values: Sequence[float]) -> dict:
    if not values:
        return {"n": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "median": 0.0}
    values = [float(v) for v in values]
    return {
        "n": len(values),
        "mean": float(statistics.fmean(values)),
        "std": float(statistics.pstdev(values)) if len(values) > 1 else 0.0,
        "min": float(min(values)),
        "max": float(max(values)),
        "median": float(statistics.median(values)),
    }


# =============================================================================
# VALIDATE + DISCOVER METADATA
# =============================================================================

def validate_runs(runs: Dict[str, Dict[str, SourceEntry]]) -> dict:
    manifest = {
        "run_dirs": [],
        "total_rows_from_summary": 0,
        "summary_rows_by_run": {},
        "normalization": {},
        "directions": set(),
        "length_buckets": set(),
        "generators": set(),
        "requires_detailed_fields": bool(REQUIRE_DETAILED_FIELDS),
    }

    for run_dir_name, files in runs.items():
        calibration = load_json(files["calibration.json"])
        summary_rows = list(iter_csv_rows(files["summary.csv"]))

        summary_total = sum(int(row["n"]) for row in summary_rows)
        manifest["run_dirs"].append(run_dir_name)
        manifest["summary_rows_by_run"][run_dir_name] = summary_total
        manifest["total_rows_from_summary"] += summary_total

        manifest["normalization"][run_dir_name] = calibration.get("normalization", {})

        for row in summary_rows:
            manifest["directions"].add(row["direction"])
            manifest["length_buckets"].add(int(row["length_bucket"]))
            manifest["generators"].add(row["generator"])

        if REQUIRE_COMPLETE_COVERAGE:
            sample_count = 0
            for _row in iter_csv_rows(files["samples.csv"]):
                sample_count += 1
            if sample_count != summary_total:
                raise RuntimeError(
                    f"Run {run_dir_name} is incomplete: samples.csv has {sample_count} rows "
                    f"but summary.csv reports {summary_total}."
                )

        if REQUIRE_DETAILED_FIELDS:
            # Check headers once by reading the first row.
            first = None
            for r in iter_csv_rows(files["samples.csv"]):
                first = r
                break
            if first is None:
                raise RuntimeError(f"Run {run_dir_name} has empty samples.csv")
            for needed in ("length_bins", "span_raw_by_len", "chars_covered_by_len"):
                if needed not in first or str(first.get(needed, "")).strip() == "":
                    raise RuntimeError(
                        f"Run {run_dir_name} is missing detailed field {needed}. "
                        f"Did the run have WRITE_DETAILED_SAMPLE_FIELDS=True?"
                    )

    manifest["run_dirs"] = sorted(manifest["run_dirs"])
    manifest["directions"] = sorted(manifest["directions"])
    manifest["length_buckets"] = sorted(manifest["length_buckets"])
    manifest["generators"] = sorted(manifest["generators"])
    return manifest


# =============================================================================
# PASS 1: REFERENCE PROFILES (REAL vs NOISE) + LENGTH BINS
# =============================================================================

def build_reference_profiles(
    runs: Dict[str, Dict[str, SourceEntry]]
) -> Tuple[dict, int, List[int]]:
    profile_accumulators = {
        measure: defaultdict(
            lambda: {"real_count": 0, "noise_count": 0, "real_sum": None, "noise_sum": None}
        )
        for measure in PROFILE_VECTOR_MEASURES
    }

    vector_length: int | None = None
    length_bins_ref: List[int] | None = None

    for _run_dir_name, files in runs.items():
        for row in iter_csv_rows(files["samples.csv"]):
            direction = str(row["direction"]).strip().lower()
            length_bucket = int(row["length_bucket"])
            generator = str(row["generator"]).strip().upper()
            key = (direction, length_bucket)

            length_bins = parse_json_int_vector(row["length_bins"])
            if length_bins_ref is None:
                length_bins_ref = list(length_bins)
            elif list(length_bins) != list(length_bins_ref):
                raise RuntimeError(
                    "length_bins mismatch across samples; refusing to guess.\n"
                    f"first={length_bins_ref}\nthis ={list(length_bins)}"
                )

            for measure in PROFILE_VECTOR_MEASURES:
                vec = parse_json_float_vector(row[measure])
                if vector_length is None:
                    vector_length = len(vec)
                elif len(vec) != vector_length:
                    raise RuntimeError(f"Vector length mismatch inside samples: {len(vec)} != {vector_length}")

                if len(vec) != len(length_bins):
                    raise RuntimeError(
                        f"Vector/length_bins mismatch: len({measure})={len(vec)} len(length_bins)={len(length_bins)}"
                    )

                profile = normalise_vector(vec)
                acc = profile_accumulators[measure][key]

                if generator == REAL_GENERATOR:
                    if acc["real_sum"] is None:
                        acc["real_sum"] = [0.0 for _ in profile]
                    vector_add_inplace(acc["real_sum"], profile)
                    acc["real_count"] += 1
                elif generator in NOISE_GENERATORS:
                    if acc["noise_sum"] is None:
                        acc["noise_sum"] = [0.0 for _ in profile]
                    vector_add_inplace(acc["noise_sum"], profile)
                    acc["noise_count"] += 1
                else:
                    raise RuntimeError(f"Unexpected generator: {generator}")

    if vector_length is None or length_bins_ref is None:
        raise RuntimeError("No sample rows were found.")

    references = {measure: {} for measure in PROFILE_VECTOR_MEASURES}
    for measure, grouped in profile_accumulators.items():
        for key, acc in grouped.items():
            if not acc["real_count"]:
                raise RuntimeError(f"No REAL rows found for {measure} {key}")
            if not acc["noise_count"]:
                raise RuntimeError(f"No noise rows found for {measure} {key}")
            references[measure][key] = {
                "real_mean": vector_mean(acc["real_sum"], acc["real_count"]),
                "noise_mean": vector_mean(acc["noise_sum"], acc["noise_count"]),
                "real_count": acc["real_count"],
                "noise_count": acc["noise_count"],
            }

    return references, vector_length, length_bins_ref


# =============================================================================
# PASS 2: BUILD TABLES
# =============================================================================

def build_tables(
    runs: Dict[str, Dict[str, SourceEntry]],
    references: dict,
    vector_length: int,
    length_bins: List[int],
) -> Tuple[dict, List[dict]]:
    scalar_values = {measure: defaultdict(list) for measure in SCALAR_MEASURES}

    profile_values = {
        measure: defaultdict(
            lambda: {
                "profile_margin_l1": [],
                "mean_bin_index": [],
                "mean_bin_value": [],
                "tail_mass_by_start_index": [[] for _ in range(vector_length)],
                "generator_mean_profile_sum": None,
                "generator_profile_count": 0,
            }
        )
        for measure in PROFILE_VECTOR_MEASURES
    }

    group_rows: List[dict] = []

    for _run_dir_name, files in runs.items():
        for row in iter_csv_rows(files["samples.csv"]):
            direction = str(row["direction"]).strip().lower()
            length_bucket = int(row["length_bucket"])
            generator = str(row["generator"]).strip().upper()
            group_key = (direction, length_bucket, generator)
            ref_key = (direction, length_bucket)

            # Safety: refuse bin drift.
            row_bins = parse_json_int_vector(row["length_bins"])
            if list(row_bins) != list(length_bins):
                raise RuntimeError("length_bins mismatch while building tables; refusing to guess.")

            for measure in SCALAR_MEASURES:
                scalar_values[measure][group_key].append(float(row[measure]))

            for measure in PROFILE_VECTOR_MEASURES:
                profile = normalise_vector(parse_json_float_vector(row[measure]))
                ref = references[measure][ref_key]
                margin = l1_distance(profile, ref["noise_mean"]) - l1_distance(profile, ref["real_mean"])
                mean_idx = weighted_mean_index(profile)
                mean_val = weighted_mean_bin_value(profile, length_bins)

                acc = profile_values[measure][group_key]
                acc["profile_margin_l1"].append(margin)
                acc["mean_bin_index"].append(mean_idx)
                acc["mean_bin_value"].append(mean_val)
                for start_index in range(vector_length):
                    acc["tail_mass_by_start_index"][start_index].append(tail_mass(profile, start_index))

                if acc["generator_mean_profile_sum"] is None:
                    acc["generator_mean_profile_sum"] = [0.0 for _ in profile]
                vector_add_inplace(acc["generator_mean_profile_sum"], profile)
                acc["generator_profile_count"] += 1

    asset = {
        "asset_version": 2,
        "asset_kind": "span_hamming_nose_lm_assets",
        "run_label": RUN_LABEL,
        "scalar_measures": SCALAR_MEASURES,
        "profile_vector_measures": PROFILE_VECTOR_MEASURES,
        "real_generator": REAL_GENERATOR,
        "noise_generators": list(NOISE_GENERATORS),
        "length_bin_edge_hints": list(LENGTH_BIN_EDGE_HINTS),
        "profile_vector_length": int(vector_length),
        # NEW: explicit labels from the backend (recorded per sample row)
        "profile_length_bins": list(length_bins),
        "quantile_grid": list(QUANTILE_GRID),
        "scalar_tables": {},
        "profile_tables": {},
    }

    all_group_keys = sorted({key for mm in scalar_values.values() for key in mm.keys()})

    # Scalar tables: per (direction, length_bucket, generator)
    for measure in SCALAR_MEASURES:
        measure_out = {}
        for group_key in all_group_keys:
            if group_key not in scalar_values[measure]:
                continue
            direction, length_bucket, generator = group_key
            values = scalar_values[measure][group_key]
            measure_out.setdefault(direction, {})
            measure_out[direction].setdefault(str(length_bucket), {})
            measure_out[direction][str(length_bucket)][generator] = {
                "stats": stats_dict(values),
                "ecdf": {"quantile_grid": list(QUANTILE_GRID), "breakpoints": quantiles_from_values(values, QUANTILE_GRID)},
            }
            group_rows.append(
                {"direction": direction, "length_bucket": length_bucket, "generator": generator, "measure": measure, **stats_dict(values)}
            )
        asset["scalar_tables"][measure] = measure_out

    # Profile tables
    for measure in PROFILE_VECTOR_MEASURES:
        measure_out = {}
        grouped = profile_values[measure]
        ref_grouped = references[measure]
        group_keys = sorted(grouped.keys())

        for group_key in group_keys:
            direction, length_bucket, generator = group_key
            acc = grouped[group_key]

            measure_out.setdefault(direction, {})
            measure_out[direction].setdefault(
                str(length_bucket),
                {
                    "references": {
                        "real_mean_profile": ref_grouped[(direction, length_bucket)]["real_mean"],
                        "noise_mean_profile": ref_grouped[(direction, length_bucket)]["noise_mean"],
                        "real_count": ref_grouped[(direction, length_bucket)]["real_count"],
                        "noise_count": ref_grouped[(direction, length_bucket)]["noise_count"],
                    },
                    "generators": {},
                },
            )

            generator_record = {
                "stats": {
                    "profile_margin_l1": stats_dict(acc["profile_margin_l1"]),
                    "mean_bin_index": stats_dict(acc["mean_bin_index"]),
                    "mean_bin_value": stats_dict(acc["mean_bin_value"]),
                },
                "ecdf": {
                    "profile_margin_l1": {"quantile_grid": list(QUANTILE_GRID), "breakpoints": quantiles_from_values(acc["profile_margin_l1"], QUANTILE_GRID)},
                    "mean_bin_index": {"quantile_grid": list(QUANTILE_GRID), "breakpoints": quantiles_from_values(acc["mean_bin_index"], QUANTILE_GRID)},
                    "mean_bin_value": {"quantile_grid": list(QUANTILE_GRID), "breakpoints": quantiles_from_values(acc["mean_bin_value"], QUANTILE_GRID)},
                    "tail_mass_by_start_index": {
                        str(start_index): {"quantile_grid": list(QUANTILE_GRID), "breakpoints": quantiles_from_values(values, QUANTILE_GRID)}
                        for start_index, values in enumerate(acc["tail_mass_by_start_index"])
                    },
                },
                "mean_profile": vector_mean(acc["generator_mean_profile_sum"], acc["generator_profile_count"]),
                "profile_count": acc["generator_profile_count"],
            }
            measure_out[direction][str(length_bucket)]["generators"][generator] = generator_record

        # Combined noise convenience block (per direction/length_bucket)
        by_bucket = defaultdict(list)
        for group_key in group_keys:
            direction, length_bucket, generator = group_key
            if generator in NOISE_GENERATORS:
                by_bucket[(direction, length_bucket)].append(grouped[group_key])

        for (direction, length_bucket), noise_accs in by_bucket.items():
            combined_margin: List[float] = []
            combined_mean_idx: List[float] = []
            combined_mean_val: List[float] = []
            combined_tails: List[List[float]] = [[] for _ in range(vector_length)]
            mean_profile_sum = [0.0 for _ in range(vector_length)]
            total_profiles = 0

            for acc in noise_accs:
                combined_margin.extend(acc["profile_margin_l1"])
                combined_mean_idx.extend(acc["mean_bin_index"])
                combined_mean_val.extend(acc["mean_bin_value"])
                for start_index in range(vector_length):
                    combined_tails[start_index].extend(acc["tail_mass_by_start_index"][start_index])
                vector_add_inplace(mean_profile_sum, acc["generator_mean_profile_sum"])
                total_profiles += acc["generator_profile_count"]

            measure_out[direction][str(length_bucket)]["combined_noise"] = {
                "stats": {
                    "profile_margin_l1": stats_dict(combined_margin),
                    "mean_bin_index": stats_dict(combined_mean_idx),
                    "mean_bin_value": stats_dict(combined_mean_val),
                },
                "ecdf": {
                    "profile_margin_l1": {"quantile_grid": list(QUANTILE_GRID), "breakpoints": quantiles_from_values(combined_margin, QUANTILE_GRID)},
                    "mean_bin_index": {"quantile_grid": list(QUANTILE_GRID), "breakpoints": quantiles_from_values(combined_mean_idx, QUANTILE_GRID)},
                    "mean_bin_value": {"quantile_grid": list(QUANTILE_GRID), "breakpoints": quantiles_from_values(combined_mean_val, QUANTILE_GRID)},
                    "tail_mass_by_start_index": {
                        str(start_index): {"quantile_grid": list(QUANTILE_GRID), "breakpoints": quantiles_from_values(values, QUANTILE_GRID)}
                        for start_index, values in enumerate(combined_tails)
                    },
                },
                "mean_profile": vector_mean(mean_profile_sum, total_profiles),
                "profile_count": total_profiles,
            }

        asset["profile_tables"][measure] = measure_out

    return asset, group_rows


# =============================================================================
# OUTPUT
# =============================================================================

def ensure_output_dir(path_str: str) -> Path:
    path = _resolve_repo_path(path_str)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, obj: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=False)


def write_group_summary_csv(path: Path, group_rows: Sequence[dict]) -> None:
    rows = sorted(group_rows, key=lambda r: (r["measure"], r["direction"], int(r["length_bucket"]), r["generator"]))
    fieldnames = ["measure", "direction", "length_bucket", "generator", "n", "mean", "std", "min", "median", "max"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    print("[span_hamming_wordlen_assets] discovering runs...")
    runs = discover_runs(INPUT_PATHS)
    for run_dir_name in runs:
        print(f"  found run: {run_dir_name}")

    print("[span_hamming_wordlen_assets] validating coverage + required fields...")
    manifest = validate_runs(runs)
    print(
        f"  summary rows total={manifest['total_rows_from_summary']} "
        f"directions={manifest['directions']} "
        f"length_buckets={manifest['length_buckets']} "
        f"generators={manifest['generators']}"
    )

    print("[span_hamming_wordlen_assets] building reference profiles + length_bins...")
    references, vector_length, length_bins = build_reference_profiles(runs)
    print(f"  profile vector length={vector_length} length_bins={length_bins}")

    print("[span_hamming_wordlen_assets] building scalar + word-profile tables...")
    asset, group_rows = build_tables(runs, references, vector_length, length_bins)

    output_dir = ensure_output_dir(OUTPUT_DIR)

    asset_path = output_dir / f"{OUTPUT_BASENAME}.json"
    write_json(asset_path, asset)
    print(f"  wrote asset json: {asset_path}")

    if WRITE_GROUP_SUMMARY_CSV:
        summary_path = output_dir / f"{OUTPUT_BASENAME}_group_summary.csv"
        write_group_summary_csv(summary_path, group_rows)
        print(f"  wrote group summary csv: {summary_path}")

    if WRITE_DEBUG_MANIFEST_JSON:
        manifest_path = output_dir / f"{OUTPUT_BASENAME}_manifest.json"
        write_json(manifest_path, manifest)
        print(f"  wrote manifest json: {manifest_path}")

    print("[span_hamming_wordlen_assets] done")


if __name__ == "__main__":
    main()
