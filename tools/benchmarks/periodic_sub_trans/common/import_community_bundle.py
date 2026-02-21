from __future__ import annotations

"""Import community benchmark run bundles into canonical output layout."""

import argparse
import json
import shutil
from pathlib import Path
from typing import List


OUTPUT_ROOT = Path("output") / "tools" / "benchmarks" / "periodic_sub_trans"
VALID_FLAVORS = {"no_wli", "col_then_sub", "sub_then_col"}


def _run_dirs_from_source(source: Path) -> List[Path]:
    if source.is_dir():
        has_run_config = (source / "run_config.json").exists()
        if has_run_config:
            return [source]
        return [p for p in sorted(source.iterdir()) if p.is_dir()]
    return []


def import_bundle(source: Path, flavor: str, contributor: str) -> List[dict]:
    if flavor not in VALID_FLAVORS:
        raise ValueError(f"Invalid flavor={flavor!r}. Choose from {sorted(VALID_FLAVORS)}")

    src = source.resolve()
    runs = _run_dirs_from_source(src)
    if not runs:
        raise ValueError(f"No run directories found in {src}")

    dst_root = OUTPUT_ROOT / flavor / "community_import" / contributor
    dst_root.mkdir(parents=True, exist_ok=True)
    rows: List[dict] = []

    for run_dir in runs:
        dst = dst_root / run_dir.name
        row = {
            "source": str(run_dir),
            "destination": str(dst),
            "status": "",
            "has_run_config": (run_dir / "run_config.json").exists(),
        }
        if dst.exists():
            row["status"] = "skipped_exists"
            rows.append(row)
            continue
        shutil.copytree(run_dir, dst)
        row["status"] = "copied"
        rows.append(row)

    manifest = dst_root / "import_manifest.json"
    manifest.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Folder containing one or more run directories")
    parser.add_argument("--flavor", required=True, choices=sorted(VALID_FLAVORS))
    parser.add_argument("--contributor", required=True, help="Stable contributor id, e.g. discord handle")
    args = parser.parse_args()

    rows = import_bundle(Path(args.source), str(args.flavor), str(args.contributor))
    copied = sum(1 for row in rows if row["status"] == "copied")
    skipped = sum(1 for row in rows if row["status"] == "skipped_exists")
    print(
        f"[community-import] done copied={copied} skipped_exists={skipped} "
        f"target={OUTPUT_ROOT / str(args.flavor) / 'community_import' / str(args.contributor)}"
    )


if __name__ == "__main__":
    main()

