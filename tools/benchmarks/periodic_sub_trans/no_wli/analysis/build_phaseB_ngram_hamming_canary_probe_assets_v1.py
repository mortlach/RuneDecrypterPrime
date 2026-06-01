from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_canary_probe_assets_v1"
OUTPUT_ROOT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_canary_probe_assets_v1"
)
CHECKED_BUILDER_REL = (
    "tools/benchmarks/scoring/word_ngrams/phaseB_filtered_ngram_index_v1_checked_patch/"
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_filtered_ngram_index_v1.py"
)

ASSET_MODE = "canary_probe"
BUILDER_RUN_MODE = "sample"
FULL_ASSET_AVAILABLE = False
FULL_RAW_NGRAM_REBUILD_CONFIRMED = False
SAMPLE_LINE_LIMIT_PER_ORDER = 25_000
REQUIRED_DIRECTIONS = ("fwd",)
REQUIRED_CUTS = ("normal", "strict")
REQUIRED_ORDERS = (2, 3)
PROGRESS_EVERY_LINES = 5_000


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def posixish(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): posixish(item) for key, item in value.items()}
    if isinstance(value, list):
        return [posixish(item) for item in value]
    if isinstance(value, str):
        return value.replace("\\", "/")
    return value


def load_checked_builder() -> Any:
    builder_path = REPO_ROOT / CHECKED_BUILDER_REL
    if not builder_path.exists():
        raise FileNotFoundError(f"checked builder missing: {CHECKED_BUILDER_REL}")
    spec = importlib.util.spec_from_file_location("phaseB_filtered_ngram_index_builder_checked", builder_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load checked n-gram builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def expected_asset_files(out_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cut in REQUIRED_CUTS:
        for direction in REQUIRED_DIRECTIONS:
            for order in REQUIRED_ORDERS:
                rel = f"{cut}_{direction}/ngram{order}.csv.gz"
                path = out_dir / rel
                rows.append(
                    {
                        "dictionary_cut": cut,
                        "direction": direction,
                        "ngram_order": order,
                        "asset_path": f"{repo_rel(out_dir)}/{rel}",
                        "exists": path.exists(),
                        "bytes": path.stat().st_size if path.exists() else 0,
                    }
                )
    return rows


def normalise_probe_config(out_dir: Path) -> dict[str, Any]:
    config_path = out_dir / "config.json"
    config = read_json(config_path)
    raw_root = Path(str(config.pop("raw_ngram_root", "")))
    config["asset_mode"] = ASSET_MODE
    config["builder_run_mode"] = BUILDER_RUN_MODE
    config["full_asset_available"] = FULL_ASSET_AVAILABLE
    config["full_raw_ngram_rebuild_confirmed"] = FULL_RAW_NGRAM_REBUILD_CONFIRMED
    config["sample_line_limit_per_order"] = SAMPLE_LINE_LIMIT_PER_ORDER
    config["sample_line_limit_per_order_present"] = True
    config["source_raw_ngram_root_name"] = raw_root.name
    config["source_raw_ngram_root_recorded_as_absolute"] = raw_root.is_absolute()
    config["required_directions"] = list(REQUIRED_DIRECTIONS)
    config["required_cuts"] = list(REQUIRED_CUTS)
    config["required_orders"] = list(REQUIRED_ORDERS)
    config["dictionary_dirs_by_cut"] = posixish(config.get("dictionary_dirs_by_cut", {}))
    write_json(config_path, config)
    return config


def write_probe_manifest(out_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    files = expected_asset_files(out_dir)
    missing = [row["asset_path"] for row in files if not row["exists"]]
    summary_path = out_dir / "filtered_ngram_summary.csv"
    inventory_path = out_dir / "raw_ngram_inventory.csv"
    blocked = [f"missing expected probe asset file: {path}" for path in missing]
    if not summary_path.exists():
        blocked.append("missing filtered_ngram_summary.csv")
    if not inventory_path.exists():
        blocked.append("missing raw_ngram_inventory.csv")
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not blocked else "blocked",
        "blocked_reasons": blocked,
        "asset_mode": ASSET_MODE,
        "builder_run_mode": BUILDER_RUN_MODE,
        "full_asset_available": FULL_ASSET_AVAILABLE,
        "full_raw_ngram_rebuild_confirmed": FULL_RAW_NGRAM_REBUILD_CONFIRMED,
        "sample_line_limit_per_order": SAMPLE_LINE_LIMIT_PER_ORDER,
        "sample_line_limit_per_order_present": True,
        "asset_root": repo_rel(out_dir),
        "source_raw_ngram_root_name": config.get("source_raw_ngram_root_name", ""),
        "source_raw_ngram_root_recorded_as_absolute": config.get("source_raw_ngram_root_recorded_as_absolute", ""),
        "dictionary_dirs_by_cut": posixish(config.get("dictionary_dirs_by_cut", {})),
        "required_directions": list(REQUIRED_DIRECTIONS),
        "required_cuts": list(REQUIRED_CUTS),
        "required_orders": list(REQUIRED_ORDERS),
        "asset_files": files,
        "filtered_ngram_summary_path": repo_rel(summary_path) if summary_path.exists() else "",
        "raw_ngram_inventory_path": repo_rel(inventory_path) if inventory_path.exists() else "",
    }
    write_json(out_dir / "canary_probe_asset_manifest.json", manifest)
    return manifest


def build_canary_probe_assets() -> dict[str, Any]:
    builder = load_checked_builder()
    builder.RUN_LABEL = RUN_LABEL
    config = builder.BuildConfig(
        repo_root=REPO_ROOT,
        raw_ngram_root=builder.RAW_NGRAM_ROOT,
        raw_ngram_files_by_order=builder.RAW_NGRAM_FILES_BY_ORDER,
        raw_ngram_globs_by_order=builder.RAW_NGRAM_GLOBS_BY_ORDER,
        dictionary_dirs_by_cut=builder.DICTIONARY_DIRS_BY_CUT,
        output_root=REPO_ROOT / OUTPUT_ROOT_REL,
        enabled_orders=REQUIRED_ORDERS,
        enabled_cuts=REQUIRED_CUTS,
        enabled_directions=REQUIRED_DIRECTIONS,
        run_mode=BUILDER_RUN_MODE,
        create_timestamped_run_dir=True,
        sample_line_limit_per_order=SAMPLE_LINE_LIMIT_PER_ORDER,
        progress_every_lines=PROGRESS_EVERY_LINES,
    )
    out_dir = builder.build_filtered_ngram_indexes(config)
    generated_config = normalise_probe_config(out_dir)
    manifest = write_probe_manifest(out_dir, generated_config)
    print(f"[{RUN_LABEL}] status={manifest['status']}", flush=True)
    print(f"[{RUN_LABEL}] asset_root={manifest['asset_root']}", flush=True)
    return manifest


def main() -> None:
    build_canary_probe_assets()


if __name__ == "__main__":
    main()
