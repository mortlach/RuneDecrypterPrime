from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_asset_provenance_inventory_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_asset_provenance_inventory_v1"
)
FILTERED_INDEX_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_filtered_ngram_index_v1/20260514T044954Z__phaseB_filtered_ngram_index_v1"
)
ASSET_VALIDATION_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_asset_validation_v1"
)
PHRASE_INDEX_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_phrase_index_v1"
)
RUN_OUTPUTS = (
    "phaseB_ngram_hamming_exact_no_cap_full_pilot_v1",
    "phaseB_ngram_hamming_bounded_expansion_v1",
    "phaseB_ngram_hamming_balanced_readout_v1",
)
RUN_OUTPUT_BASE_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def read_json(rel_path: str) -> Any:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def read_csv(rel_path: str) -> list[dict[str, str]]:
    with (REPO_ROOT / rel_path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: Iterable[str] | None = None) -> None:
    ensure_under_repo(path)
    names = list(fieldnames) if fieldnames is not None else sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def int_value(value: Any) -> int:
    if value in ("", None):
        return 0
    return int(float(value))


def build_asset_inventory_rows() -> list[dict[str, Any]]:
    summary_rows = read_csv(f"{FILTERED_INDEX_REL}/filtered_ngram_summary.csv")
    out: list[dict[str, Any]] = []
    for row in summary_rows:
        output_rel = row["output_file"].replace("\\", "/")
        asset_path = REPO_ROOT / FILTERED_INDEX_REL / output_rel
        out.append(
            {
                "asset_root": FILTERED_INDEX_REL,
                "asset_path": f"{FILTERED_INDEX_REL}/{output_rel}",
                "exists": asset_path.exists(),
                "sha256": sha256_file(asset_path) if asset_path.exists() else "",
                "dictionary_cut": row["dictionary_cut"],
                "direction": row["encoding_direction"],
                "ngram_order": int_value(row["n"]),
                "input_rows_seen": int_value(row["input_rows_seen"]),
                "valid_format_rows": int_value(row["valid_format_rows"]),
                "dictionary_kept_rows": int_value(row["dictionary_kept_rows"]),
                "dictionary_rejected_rows": int_value(row["dictionary_rejected_rows"]),
                "aggregate_rows": int_value(row["aggregate_rows"]),
                "count_sum": int_value(row["count_sum"]),
            }
        )
    return sorted(out, key=lambda item: (item["dictionary_cut"], item["direction"], item["ngram_order"]))


def build_run_scope_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_label in RUN_OUTPUTS:
        run_rel = f"{RUN_OUTPUT_BASE_REL}/{run_label}"
        phrase_manifest_path = REPO_ROOT / run_rel / "phrase_index_manifest_used.json"
        pilot_manifest_path = REPO_ROOT / run_rel / "pilot_manifest.json"
        config_path = REPO_ROOT / run_rel / "config.json"
        phrase_manifest = json.loads(phrase_manifest_path.read_text(encoding="utf-8")) if phrase_manifest_path.exists() else {}
        pilot_manifest = json.loads(pilot_manifest_path.read_text(encoding="utf-8")) if pilot_manifest_path.exists() else {}
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        entry_counts = phrase_manifest.get("entry_counts_by_order", {})
        loaded_counts = phrase_manifest.get("loaded_phrase_entry_counts_by_profile_cut_order", {})
        for key, loaded_count in sorted(loaded_counts.items()):
            profile_id, dictionary_cut, order_text = key.split("|")
            rows.append(
                {
                    "run_label": run_label,
                    "run_status": pilot_manifest.get("status", ""),
                    "backend_impl": pilot_manifest.get("backend_impl", ""),
                    "python_fallback_allowed": pilot_manifest.get("python_fallback_allowed", ""),
                    "claim_mode": pilot_manifest.get("claim_mode", ""),
                    "dictionary_cut": dictionary_cut,
                    "direction": phrase_manifest.get("direction", ""),
                    "ngram_order": int_value(order_text),
                    "profile_id": profile_id,
                    "loaded_phrase_entry_count": int_value(loaded_count),
                    "entry_count_by_order": int_value(entry_counts.get(order_text)),
                    "candidate_limit": config.get("MAX_CANDIDATES", config.get("candidate_limit", "")),
                    "chunks_per_candidate": config.get("MAX_CHUNKS_PER_CANDIDATE", config.get("chunks_per_candidate", "")),
                    "output_dir": run_rel,
                }
            )
    return rows


def build_inventory() -> dict[str, Any]:
    filtered_config = read_json(f"{FILTERED_INDEX_REL}/config.json")
    dictionary_manifest = read_json(f"{FILTERED_INDEX_REL}/dictionary_manifest.json")
    asset_validation_manifest = read_json(f"{ASSET_VALIDATION_REL}/ngram_hamming_asset_manifest.json")
    phrase_index_manifest = read_json(f"{PHRASE_INDEX_REL}/phrase_index_manifest.json")
    phrase_index_path = REPO_ROOT / phrase_index_manifest["phrase_index_path"]
    asset_rows = build_asset_inventory_rows()
    run_scope_rows = build_run_scope_rows()
    asset_mode = phrase_index_manifest.get("asset_mode", "")
    full_asset_available = bool(phrase_index_manifest.get("full_asset_available"))
    normal_orders = sorted(
        {
            int(row["ngram_order"])
            for row in asset_rows
            if row["dictionary_cut"] == "normal" and row["direction"] == "fwd" and row["exists"]
        }
    )
    strict_orders = sorted(
        {
            int(row["ngram_order"])
            for row in asset_rows
            if row["dictionary_cut"] == "strict" and row["direction"] == "fwd" and row["exists"]
        }
    )
    latest_scanned_orders = sorted(
        {
            int(row["ngram_order"])
            for row in run_scope_rows
            if row["run_label"] == "phaseB_ngram_hamming_balanced_readout_v1"
        }
    )
    latest_scanned_cuts = sorted(
        {
            str(row["dictionary_cut"])
            for row in run_scope_rows
            if row["run_label"] == "phaseB_ngram_hamming_balanced_readout_v1"
        }
    )
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "dataset_status": "sample_index_confirmed",
        "full_raw_ngram_rebuild_confirmed": False,
        "matrix_launch_recommendation": "do_not_claim_full_raw; full matrix may use this sample index only if labelled sample",
        "filtered_index": {
            "asset_root": FILTERED_INDEX_REL,
            "run_mode": filtered_config.get("run_mode"),
            "sample_line_limit_per_order": filtered_config.get("sample_line_limit_per_order"),
            "enabled_cuts": filtered_config.get("enabled_cuts"),
            "enabled_directions": filtered_config.get("enabled_directions"),
            "enabled_orders": filtered_config.get("enabled_orders"),
            "dictionary_manifest": dictionary_manifest,
            "raw_ngram_root_recorded_as_absolute": bool(str(filtered_config.get("raw_ngram_root", "")).startswith(("C:\\", "/"))),
            "raw_ngram_root_name": Path(str(filtered_config.get("raw_ngram_root", ""))).name,
        },
        "asset_validation": {
            "manifest_path": f"{ASSET_VALIDATION_REL}/ngram_hamming_asset_manifest.json",
            "status": asset_validation_manifest.get("status"),
            "asset_mode": asset_validation_manifest.get("asset_mode"),
            "full_asset_available": asset_validation_manifest.get("full_asset_available"),
            "core_fwd_asset_validation_pass": asset_validation_manifest.get("core_fwd_asset_validation_pass"),
            "dictionary_cuts": asset_validation_manifest.get("dictionary_cuts"),
            "directions": asset_validation_manifest.get("directions"),
            "orders": asset_validation_manifest.get("orders"),
        },
        "phrase_index": {
            "manifest_path": f"{PHRASE_INDEX_REL}/phrase_index_manifest.json",
            "phrase_index_path": phrase_index_manifest.get("phrase_index_path"),
            "phrase_index_sha256": sha256_file(phrase_index_path) if phrase_index_path.exists() else "",
            "status": phrase_index_manifest.get("status"),
            "asset_mode": asset_mode,
            "full_asset_available": full_asset_available,
            "sample_line_limit_per_order": phrase_index_manifest.get("sample_line_limit_per_order"),
            "phrase_entry_count": phrase_index_manifest.get("phrase_entry_count"),
            "normal_fwd_orders_available": normal_orders,
            "strict_fwd_orders_available": strict_orders,
            "core_fwd_invalid_row_count": phrase_index_manifest.get("core_fwd_invalid_row_count"),
        },
        "latest_scans": {
            "balanced_readout_scanned_cuts": latest_scanned_cuts,
            "balanced_readout_scanned_orders": latest_scanned_orders,
            "balanced_readout_used_sample_index": asset_mode == "sample" and not full_asset_available,
        },
        "counts": {
            "asset_file_count": len(asset_rows),
            "run_scope_row_count": len(run_scope_rows),
        },
    }
    return {
        "manifest": manifest,
        "asset_inventory_rows": asset_rows,
        "run_scope_rows": run_scope_rows,
    }


def write_outputs(payload: dict[str, Any]) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    manifest = payload["manifest"]
    write_json(output_dir / "provenance_manifest.json", manifest)
    write_csv(output_dir / "asset_inventory_rows.csv", payload["asset_inventory_rows"])
    write_csv(output_dir / "run_scope_rows.csv", payload["run_scope_rows"])
    readout = [
        "# PhaseB N-Gram Hamming Asset Provenance Inventory v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- dataset status: `{manifest['dataset_status']}`",
        f"- full raw ngram rebuild confirmed: `{manifest['full_raw_ngram_rebuild_confirmed']}`",
        f"- filtered index run mode: `{manifest['filtered_index']['run_mode']}`",
        f"- sample line limit per order: `{manifest['filtered_index']['sample_line_limit_per_order']}`",
        f"- phrase index asset mode: `{manifest['phrase_index']['asset_mode']}`",
        f"- phrase entries: `{manifest['phrase_index']['phrase_entry_count']}`",
        f"- normal FWD orders available: `{manifest['phrase_index']['normal_fwd_orders_available']}`",
        f"- strict FWD orders available: `{manifest['phrase_index']['strict_fwd_orders_available']}`",
        f"- latest balanced scan cuts: `{manifest['latest_scans']['balanced_readout_scanned_cuts']}`",
        f"- latest balanced scan orders: `{manifest['latest_scans']['balanced_readout_scanned_orders']}`",
        "",
        "## Decision",
        "",
        "The current n-gram Hamming outputs are internally consistent and use the expected sample phrase index.",
        "They do not prove a full raw n-gram rebuild with current dictionary cuts.",
        "Any larger matrix launched from this index must be labelled as sample-index based.",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def run_inventory() -> dict[str, Any]:
    payload = build_inventory()
    write_outputs(payload)
    return payload["manifest"]


def main() -> None:
    manifest = run_inventory()
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] dataset_status={manifest['dataset_status']}")


if __name__ == "__main__":
    main()
