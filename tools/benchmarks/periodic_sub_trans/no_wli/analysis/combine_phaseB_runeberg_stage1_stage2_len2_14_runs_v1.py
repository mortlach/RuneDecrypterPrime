from __future__ import annotations

import csv
import gzip
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


# =============================================================================
# Hardcoded combine configuration. No CLI arguments.
# =============================================================================


RUN_LABEL = "stage1_stage2_fwd_full_len2_14_combined_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "stage1_stage2_fwd_full_len2_14_combined_v1"
)

LOCAL_REPO_ROOT = Path(__file__).resolve().parents[5]
DJ_REPO_ROOT = Path(r"\\DJ\sjduk\OneDrive\Documents\github\RuneDecrypterPrime")

RUN_SPECS = (
    {
        "source_key": "stage1_pc_a",
        "source_group": "stage1_raw",
        "repo_root": DJ_REPO_ROOT,
        "run_dir_rel": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "stage1_fwd_full_1k_pc_a"
        ),
    },
    {
        "source_key": "stage1_pc_b",
        "source_group": "stage1_raw",
        "repo_root": LOCAL_REPO_ROOT,
        "run_dir_rel": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "stage1_fwd_full_1k_pc_b"
        ),
    },
    {
        "source_key": "stage2_pc_a",
        "source_group": "stage2_len2_14_raw",
        "repo_root": DJ_REPO_ROOT,
        "run_dir_rel": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "stage2_fwd_full_len2_14_pc_a"
        ),
    },
    {
        "source_key": "stage2_pc_b",
        "source_group": "stage2_len2_14_raw",
        "repo_root": LOCAL_REPO_ROOT,
        "run_dir_rel": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "stage2_fwd_full_len2_14_pc_b"
        ),
    },
)

STAGE1_COMBINED_REFERENCE = {
    "source_key": "stage1_combined_reference",
    "repo_root": DJ_REPO_ROOT,
    "run_dir_rel": (
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "stage1_fwd_full_1k_combined_pc_a_pc_b"
    ),
}

NORM_FEATURES = ("exact_count_norm", "hd_le_count_norm")
HARD_NULLS = ("block_shuffle_10", "block_shuffle_25", "block_shuffle_50")


# =============================================================================
# Helpers
# =============================================================================


def _repo_rel(path: Path) -> str:
    path = path.resolve()
    for root in (LOCAL_REPO_ROOT.resolve(), DJ_REPO_ROOT.resolve()):
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            continue
    return path.name


def _resolve_local_output(rel: str) -> Path:
    path = (LOCAL_REPO_ROOT / rel).resolve()
    root = LOCAL_REPO_ROOT.resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"output path escapes repo root: {rel}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_dir(spec: dict[str, Any]) -> Path:
    return (Path(spec["repo_root"]) / str(spec["run_dir_rel"])).resolve()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON: {_repo_rel(path)}")
    return data


def _safe_float(text: Any) -> float:
    if text in (None, ""):
        return math.nan
    try:
        return float(text)
    except (TypeError, ValueError):
        return math.nan


def _safe_int(text: Any) -> int:
    if text in (None, ""):
        return 0
    return int(float(text))


def _sample_variance_from_stddev(stddev: float, count: int) -> float:
    if count <= 1 or not math.isfinite(stddev):
        return 0.0
    return stddev * stddev


@dataclass
class Stat:
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0

    @classmethod
    def from_summary(cls, count: int, mean: float, stddev: float) -> "Stat":
        if count <= 0:
            return cls()
        variance = _sample_variance_from_stddev(stddev, count)
        return cls(count=count, mean=mean, m2=variance * max(0, count - 1))

    def merge(self, other: "Stat") -> None:
        if other.count <= 0:
            return
        if self.count <= 0:
            self.count = other.count
            self.mean = other.mean
            self.m2 = other.m2
            return
        total = self.count + other.count
        delta = other.mean - self.mean
        self.mean = self.mean + delta * (other.count / total)
        self.m2 = self.m2 + other.m2 + delta * delta * self.count * other.count / total
        self.count = total

    @property
    def stddev(self) -> float:
        if self.count <= 1:
            return 0.0
        return math.sqrt(max(0.0, self.m2 / (self.count - 1)))


SUMMARY_KEY_FIELDS = (
    "direction",
    "source_kind",
    "damage_model",
    "damage_level",
    "null_model",
    "start_assumption",
    "start_shift",
    "score_region",
    "dictionary_cut",
    "ladder_profile",
    "span_length",
    "hd",
    "feature_name",
)

DAMAGED_KEY_FIELDS = (
    "direction",
    "score_region",
    "start_shift",
    "dictionary_cut",
    "ladder_profile",
    "span_length",
    "hd",
    "feature_name",
    "damage_model",
    "damage_level",
    "null_model",
)

DAMAGED_FIELDS = (
    *DAMAGED_KEY_FIELDS,
    "damaged_count",
    "damaged_mean",
    "damaged_stddev",
    "null_count",
    "null_mean",
    "null_stddev",
    "mean_diff",
    "cohen_d",
)

TOP_FIELDS = (
    *DAMAGED_KEY_FIELDS,
    "damaged_count",
    "damaged_mean",
    "damaged_stddev",
    "null_count",
    "null_mean",
    "null_stddev",
    "mean_diff",
    "cohen_d",
)

LENGTH_FIELDS = (
    "span_length",
    "norm_rows",
    "positive_rows_d_gt_0_2",
    "negative_rows_d_lt_neg_0_2",
    "weak_rows_abs_d_lt_0_2",
    "median_abs_d",
    "p90_abs_d",
    "max_abs_d",
    "best_signed_d",
    "best_dictionary_cut",
    "best_hd",
    "best_feature_name",
    "best_damage_model",
    "best_damage_level",
    "best_null_model",
    "hard_null_median_abs_d",
    "hard_null_p90_abs_d",
    "hard_null_max_abs_d",
    "hard_null_best_signed_d",
    "hard_null_best_hd",
    "hard_null_best_feature_name",
    "hard_null_best_null_model",
    "phaseA14_strict_selected_p90_abs_d",
    "phaseA14_strict_selected_max_abs_d",
    "phaseA14_normal_selected_p90_abs_d",
    "phaseA14_normal_selected_max_abs_d",
)


def _read_final_feature_summary(run_dir: Path) -> Iterable[dict[str, str]]:
    path = run_dir / "final_feature_summary.csv"
    with path.open("r", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def _read_sample_rows(run_dir: Path) -> Iterable[dict[str, str]]:
    path = run_dir / "sample_rows.csv"
    with path.open("r", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def _row_key(row: dict[str, str]) -> tuple[str, ...]:
    values = {field: str(row.get(field, "")) for field in SUMMARY_KEY_FIELDS}
    # Stage 1 used the full profile name because it still included length 1.
    # For lengths 2..14, the HD ladder is intentionally the same staged ladder
    # and should be pooled with Stage 2's explicit len2_14 profile.
    if values["span_length"] != "1":
        values["ladder_profile"] = "v0_3_plus_long_relaxed_v2_len2_14_combined"
    return tuple(values[field] for field in SUMMARY_KEY_FIELDS)


def _write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str], *, gzip_output: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if gzip_output else open
    with opener(path, "wt", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _format_float(value: float) -> str:
    if not math.isfinite(value):
        return ""
    return f"{value:.12g}"


def _percentile(values: Sequence[float], q: float) -> float:
    finite = sorted(v for v in values if math.isfinite(v))
    if not finite:
        return math.nan
    if len(finite) == 1:
        return finite[0]
    pos = (len(finite) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return finite[lo]
    frac = pos - lo
    return finite[lo] * (1.0 - frac) + finite[hi] * frac


def _cohen_d(a: Stat, b: Stat) -> float:
    if a.count <= 1 or b.count <= 1:
        return 0.0
    pooled_n = a.count + b.count - 2
    if pooled_n <= 0:
        return 0.0
    pooled_var = (a.m2 + b.m2) / pooled_n
    if pooled_var <= 0:
        return 0.0
    return (a.mean - b.mean) / math.sqrt(pooled_var)


def _build_run_check(run_infos: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[str] = []
    all_chunk_ids: set[str] = set()
    all_indices: set[int] = set()
    chunk_overlap = 0
    index_overlap = 0

    for info in run_infos:
        run_dir = info["_run_dir"]
        chunk_ids: set[str] = set()
        indices: set[int] = set()
        directions: set[str] = set()
        source_kinds: set[str] = set()
        for row in _read_sample_rows(run_dir):
            chunk_ids.add(str(row["chunk_id"]))
            indices.add(_safe_int(row["corpus_chunk_index"]))
            directions.add(str(row["direction"]))
            source_kinds.add(str(row["source_kind"]))
        info["unique_chunk_ids"] = len(chunk_ids)
        info["min_corpus_chunk_index"] = min(indices) if indices else None
        info["max_corpus_chunk_index"] = max(indices) if indices else None
        info["directions_from_sample_rows"] = sorted(directions)
        info["source_kinds_from_sample_rows"] = sorted(source_kinds)
        overlap_chunks = all_chunk_ids.intersection(chunk_ids)
        overlap_indices = all_indices.intersection(indices)
        chunk_overlap += len(overlap_chunks)
        index_overlap += len(overlap_indices)
        if overlap_chunks:
            issues.append(f"{info['source_key']} overlaps {len(overlap_chunks)} chunk_id values")
        if overlap_indices:
            issues.append(f"{info['source_key']} overlaps {len(overlap_indices)} corpus_chunk_index values")
        all_chunk_ids.update(chunk_ids)
        all_indices.update(indices)

    sorted_indices = sorted(all_indices)
    gaps: list[dict[str, int]] = []
    if sorted_indices:
        expected = set(range(sorted_indices[0], sorted_indices[-1] + 1))
        missing = sorted(expected.difference(all_indices))
        if missing:
            start = prev = missing[0]
            for value in missing[1:]:
                if value == prev + 1:
                    prev = value
                    continue
                gaps.append({"start": start, "end": prev, "count": prev - start + 1})
                start = prev = value
            gaps.append({"start": start, "end": prev, "count": prev - start + 1})

    return {
        "run_label": RUN_LABEL,
        "compatible": not issues and not gaps,
        "issues": issues,
        "corpus_chunk_index_gap_ranges": gaps,
        "chunk_id_overlap_count": chunk_overlap,
        "corpus_chunk_index_overlap_count": index_overlap,
        "combined_unique_chunks": len(all_indices),
        "combined_min_corpus_chunk_index": sorted_indices[0] if sorted_indices else None,
        "combined_max_corpus_chunk_index": sorted_indices[-1] if sorted_indices else None,
        "runs": {
            info["source_key"]: {
                key: value
                for key, value in info.items()
                if not key.startswith("_") and key not in {"source_group"}
            }
            for info in run_infos
        },
    }


def _combine_final_feature_stats(run_infos: list[dict[str, Any]]) -> dict[tuple[str, ...], Stat]:
    combined: dict[tuple[str, ...], Stat] = {}
    for info in run_infos:
        for row in _read_final_feature_summary(info["_run_dir"]):
            key = _row_key(row)
            stat = Stat.from_summary(
                _safe_int(row.get("count")),
                _safe_float(row.get("mean")),
                _safe_float(row.get("stddev")),
            )
            combined.setdefault(key, Stat()).merge(stat)
    return combined


def _index_stats_by_kind(stats: dict[tuple[str, ...], Stat]) -> tuple[dict[tuple[str, ...], Stat], dict[tuple[str, ...], Stat]]:
    damaged: dict[tuple[str, ...], Stat] = {}
    nulls: dict[tuple[str, ...], Stat] = {}
    for key, stat in stats.items():
        row = dict(zip(SUMMARY_KEY_FIELDS, key))
        base = (
            row["direction"],
            row["start_assumption"],
            row["start_shift"],
            row["score_region"],
            row["dictionary_cut"],
            row["ladder_profile"],
            row["span_length"],
            row["hd"],
            row["feature_name"],
        )
        if row["source_kind"] == "damaged":
            damaged[base + (row["damage_model"], row["damage_level"])] = stat
        elif row["source_kind"] == "null":
            nulls[base + (row["null_model"],)] = stat
    return damaged, nulls


def _build_damaged_vs_null_rows(stats: dict[tuple[str, ...], Stat]) -> list[dict[str, Any]]:
    damaged, nulls = _index_stats_by_kind(stats)
    rows: list[dict[str, Any]] = []
    for dkey, dstat in sorted(damaged.items()):
        base = dkey[:9]
        damage_model, damage_level = dkey[9], dkey[10]
        for nkey, nstat in sorted(nulls.items()):
            if nkey[:9] != base:
                continue
            null_model = nkey[9]
            direction, start_assumption, start_shift, score_region, dictionary_cut, ladder_profile, span_length, hd, feature_name = base
            row = {
                "direction": direction,
                "score_region": score_region,
                "start_shift": start_shift,
                "dictionary_cut": dictionary_cut,
                "ladder_profile": ladder_profile,
                "span_length": span_length,
                "hd": hd,
                "feature_name": feature_name,
                "damage_model": damage_model,
                "damage_level": damage_level,
                "null_model": null_model,
                "damaged_count": dstat.count,
                "damaged_mean": _format_float(dstat.mean),
                "damaged_stddev": _format_float(dstat.stddev),
                "null_count": nstat.count,
                "null_mean": _format_float(nstat.mean),
                "null_stddev": _format_float(nstat.stddev),
                "mean_diff": _format_float(dstat.mean - nstat.mean),
                "cohen_d": _format_float(_cohen_d(dstat, nstat)),
            }
            rows.append(row)
    return rows


def _length_summary(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_len: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["feature_name"] not in NORM_FEATURES:
            continue
        by_len.setdefault(str(row["span_length"]), []).append(row)

    out: list[dict[str, Any]] = []
    for span_length in sorted(by_len, key=lambda text: int(text)):
        rows_for_length = by_len[span_length]
        values = [_safe_float(row["cohen_d"]) for row in rows_for_length]
        abs_values = [abs(value) for value in values if math.isfinite(value)]
        positives = [value for value in values if value > 0.2]
        negatives = [value for value in values if value < -0.2]
        weak = [value for value in values if math.isfinite(value) and abs(value) < 0.2]

        best = max(rows_for_length, key=lambda row: _safe_float(row["cohen_d"]))
        hard_rows = [row for row in rows_for_length if row["null_model"] in HARD_NULLS]
        hard_abs = [abs(_safe_float(row["cohen_d"])) for row in hard_rows]
        hard_best = min(hard_rows, key=lambda row: _safe_float(row["cohen_d"])) if hard_rows else {}

        strict_abs = [
            abs(_safe_float(row["cohen_d"]))
            for row in rows_for_length
            if row["dictionary_cut"] == "phaseA14_strict_selected"
        ]
        normal_abs = [
            abs(_safe_float(row["cohen_d"]))
            for row in rows_for_length
            if row["dictionary_cut"] == "phaseA14_normal_selected"
        ]
        out.append(
            {
                "span_length": span_length,
                "norm_rows": len(rows_for_length),
                "positive_rows_d_gt_0_2": len(positives),
                "negative_rows_d_lt_neg_0_2": len(negatives),
                "weak_rows_abs_d_lt_0_2": len(weak),
                "median_abs_d": _format_float(_percentile(abs_values, 0.5)),
                "p90_abs_d": _format_float(_percentile(abs_values, 0.9)),
                "max_abs_d": _format_float(max(abs_values) if abs_values else math.nan),
                "best_signed_d": _format_float(_safe_float(best["cohen_d"])),
                "best_dictionary_cut": best.get("dictionary_cut", ""),
                "best_hd": best.get("hd", ""),
                "best_feature_name": best.get("feature_name", ""),
                "best_damage_model": best.get("damage_model", ""),
                "best_damage_level": best.get("damage_level", ""),
                "best_null_model": best.get("null_model", ""),
                "hard_null_median_abs_d": _format_float(_percentile(hard_abs, 0.5)),
                "hard_null_p90_abs_d": _format_float(_percentile(hard_abs, 0.9)),
                "hard_null_max_abs_d": _format_float(max(hard_abs) if hard_abs else math.nan),
                "hard_null_best_signed_d": _format_float(_safe_float(hard_best.get("cohen_d"))),
                "hard_null_best_hd": hard_best.get("hd", ""),
                "hard_null_best_feature_name": hard_best.get("feature_name", ""),
                "hard_null_best_null_model": hard_best.get("null_model", ""),
                "phaseA14_strict_selected_p90_abs_d": _format_float(_percentile(strict_abs, 0.9)),
                "phaseA14_strict_selected_max_abs_d": _format_float(max(strict_abs) if strict_abs else math.nan),
                "phaseA14_normal_selected_p90_abs_d": _format_float(_percentile(normal_abs, 0.9)),
                "phaseA14_normal_selected_max_abs_d": _format_float(max(normal_abs) if normal_abs else math.nan),
            }
        )
    return out


def _top_by_length(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    by_len: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["feature_name"] not in NORM_FEATURES:
            continue
        by_len.setdefault(str(row["span_length"]), []).append(row)
    for span_length in sorted(by_len, key=lambda text: int(text)):
        best = max(by_len[span_length], key=lambda row: _safe_float(row["cohen_d"]))
        out.append(dict(best))
    return out


def _load_run_infos() -> list[dict[str, Any]]:
    infos: list[dict[str, Any]] = []
    for spec in RUN_SPECS:
        run_dir = _run_dir(spec)
        summary = _load_json(run_dir / "final_summary.json")
        state = _load_json(run_dir / "run_state.json")
        if summary.get("status") != "complete" or state.get("status") != "complete":
            raise ValueError(f"incomplete run: {spec['source_key']}")
        infos.append(
            {
                "source_key": spec["source_key"],
                "source_group": spec["source_group"],
                "_run_dir": run_dir,
                "run_dir": _repo_rel(run_dir),
                "run_label": summary.get("run_label"),
                "run_mode": summary.get("run_mode"),
                "status": summary.get("status"),
                "CHUNK_START_INDEX": summary.get("CHUNK_START_INDEX"),
                "NUM_CLEAN_CHUNKS_THIS_RUN": summary.get("NUM_CLEAN_CHUNKS_THIS_RUN"),
                "actual_chunks_used": summary.get("actual_chunks_used"),
                "samples_done": summary.get("samples_done"),
                "feature_rows_done": summary.get("feature_rows_done"),
                "elapsed_s": summary.get("elapsed_s"),
                "first_chunk_id": summary.get("first_chunk_id"),
                "last_chunk_id": summary.get("last_chunk_id"),
                "next_chunk_start_index": summary.get("next_chunk_start_index"),
                "ladder_profile": summary.get("ladder_profile"),
                "total_rung_count": summary.get("total_rung_count"),
                "directions": summary.get("directions"),
            }
        )
    return infos


def _reference_check() -> dict[str, Any]:
    ref_dir = _run_dir(STAGE1_COMBINED_REFERENCE)
    ref_path = ref_dir / "combined_run_check.json"
    if not ref_path.exists():
        return {"available": False}
    ref = _load_json(ref_path)
    return {
        "available": True,
        "source_key": STAGE1_COMBINED_REFERENCE["source_key"],
        "run_dir": _repo_rel(ref_dir),
        "compatible": ref.get("compatible"),
        "combined_unique_chunks": ref.get("combined_unique_chunks"),
        "combined_min_corpus_chunk_index": ref.get("combined_min_corpus_chunk_index"),
        "combined_max_corpus_chunk_index": ref.get("combined_max_corpus_chunk_index"),
        "chunk_id_overlap_count": ref.get("chunk_id_overlap_count"),
        "corpus_chunk_index_overlap_count": ref.get("corpus_chunk_index_overlap_count"),
    }


def _write_readout(output_dir: Path, run_check: dict[str, Any], length_rows: list[dict[str, Any]], top_rows: list[dict[str, Any]]) -> None:
    total_elapsed = sum(float(info["elapsed_s"]) for info in run_check["runs"].values())
    total_samples = sum(int(info["samples_done"]) for info in run_check["runs"].values())
    total_feature_rows = sum(int(info["feature_rows_done"]) for info in run_check["runs"].values())
    lines = [
        f"# {RUN_LABEL}",
        "",
        "## Coverage",
        "",
        f"- compatible: `{run_check['compatible']}`",
        f"- unique chunks: `{run_check['combined_unique_chunks']}`",
        f"- corpus chunk index range: `{run_check['combined_min_corpus_chunk_index']}..{run_check['combined_max_corpus_chunk_index']}`",
        f"- chunk-id overlaps: `{run_check['chunk_id_overlap_count']}`",
        f"- corpus-index overlaps: `{run_check['corpus_chunk_index_overlap_count']}`",
        f"- gap ranges: `{len(run_check['corpus_chunk_index_gap_ranges'])}`",
        f"- total samples: `{total_samples}`",
        f"- total feature rows: `{total_feature_rows}`",
        f"- total elapsed seconds across source runs: `{total_elapsed:.2f}`",
        "",
        "## Source Runs",
        "",
    ]
    for key, info in run_check["runs"].items():
        lines.extend(
            [
                f"- `{key}`: `{info['run_label']}` chunks `{info.get('min_corpus_chunk_index')}`..`{info.get('max_corpus_chunk_index')}`, samples `{info['samples_done']}`, rows `{info['feature_rows_done']}`, elapsed `{float(info['elapsed_s']):.2f}s`",
            ]
        )
    lines.extend(
        [
            "",
            "## Best Normalized Rows By Length",
            "",
        ]
    )
    for row in top_rows:
        lines.append(
            "- len `{span_length}`: d=`{cohen_d}` `{dictionary_cut}` HD `{hd}` `{feature_name}` "
            "`{damage_model}` level `{damage_level}` vs `{null_model}`".format(**row)
        )
    lines.extend(
        [
            "",
            "## Length Summary",
            "",
        ]
    )
    for row in length_rows:
        lines.append(
            "- len `{span_length}`: median |d| `{median_abs_d}`, p90 |d| `{p90_abs_d}`, max |d| `{max_abs_d}`, weak rows `{weak_rows_abs_d_lt_0_2}`".format(**row)
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `combined_run_check.json`",
            "- `combined_damaged_vs_null_by_view.csv.gz`",
            "- `combined_top_by_length.csv`",
            "- `combined_length_update.csv`",
            "- `combined_readout.md`",
            "",
            "## Caveats",
            "",
            "- Stage 1 includes span length 1 under `v0_3_plus_long_relaxed_v2`; Stage 2 excludes length 1 under `v0_3_plus_long_relaxed_v2_len2_14`.",
            "- Lengths 2..14 are pooled across all four raw completed ranges.",
            "- This combine uses saved final summary statistics, not raw feature rows.",
        ]
    )
    (output_dir / "combined_readout.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    output_dir = _resolve_local_output(OUTPUT_DIR_REL)
    run_infos = _load_run_infos()
    run_check = _build_run_check(run_infos)
    run_check["stage1_combined_reference"] = _reference_check()

    stats = _combine_final_feature_stats(run_infos)
    damaged_rows = _build_damaged_vs_null_rows(stats)
    top_rows = _top_by_length(damaged_rows)
    length_rows = _length_summary(damaged_rows)

    (output_dir / "combined_run_check.json").write_text(
        json.dumps(run_check, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(output_dir / "combined_damaged_vs_null_by_view.csv.gz", damaged_rows, DAMAGED_FIELDS, gzip_output=True)
    _write_csv(output_dir / "combined_top_by_length.csv", top_rows, TOP_FIELDS)
    _write_csv(output_dir / "combined_length_update.csv", length_rows, LENGTH_FIELDS)
    _write_readout(output_dir, run_check, length_rows, top_rows)
    print(
        f"[{RUN_LABEL}] wrote {output_dir.relative_to(LOCAL_REPO_ROOT).as_posix()} "
        f"rows={len(damaged_rows)} compatible={run_check['compatible']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
