from __future__ import annotations

"""Copy legacy benchmark run folders into the periodic_sub_trans output layout.

This script is intentionally non-destructive:
- source folders stay in place
- destination folders are created only when missing
- a manifest is written for auditability
"""

import json
import shutil
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import List


SOURCE_ROOT = Path("output") / "tools" / "benchmarks"
DEST_ROOT = SOURCE_ROOT / "periodic_sub_trans"
MANIFEST_PATH = DEST_ROOT / "legacy_import_manifest.json"
SKIP_NAMES = {"periodic_sub_trans", "community"}


@dataclass(frozen=True)
class MappingRule:
    needle: str
    flavor: str


RULES = (
    MappingRule("__bench_solve_pipeline_no_wli__", "no_wli"),
    MappingRule("__bench_solve_col_then_sub_pipeline__", "col_then_sub"),
    MappingRule("__bench_solve_sub_then_col_pipeline__", "sub_then_col"),
    MappingRule("__bench_solve_pipeline__", "col_then_sub"),
)


def classify_folder(name: str) -> str:
    lowered = str(name).lower()
    for rule in RULES:
        if rule.needle in lowered:
            return rule.flavor
    return "misc_legacy"


def migrate(*, prune_copied: bool = False) -> List[dict]:
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    rows: List[dict] = []

    for src in sorted(SOURCE_ROOT.iterdir()):
        if not src.is_dir():
            continue
        if src.name in SKIP_NAMES:
            continue

        flavor = classify_folder(src.name)
        dst = DEST_ROOT / flavor / "legacy_import" / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)

        row = {
            "source": str(src),
            "destination": str(dst),
            "flavor": flavor,
            "status": "",
            "error": "",
        }

        if dst.exists():
            row["status"] = "skipped_exists"
            rows.append(row)
            continue

        try:
            shutil.copytree(src, dst)
            row["status"] = "copied"
            if bool(prune_copied):
                shutil.rmtree(src)
                row["status"] = "copied_pruned"
        except Exception as exc:  # pragma: no cover - defensive log path
            row["status"] = "error"
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prune-copied",
        action="store_true",
        help="Delete source folders only after successful copy",
    )
    args = parser.parse_args()

    rows = migrate(prune_copied=bool(args.prune_copied))
    copied = sum(1 for row in rows if row["status"] == "copied")
    copied_pruned = sum(1 for row in rows if row["status"] == "copied_pruned")
    skipped = sum(1 for row in rows if row["status"] == "skipped_exists")
    errors = sum(1 for row in rows if row["status"] == "error")
    print(
        f"[legacy-import] done copied={copied} copied_pruned={copied_pruned} skipped_exists={skipped} "
        f"errors={errors} manifest={MANIFEST_PATH}"
    )


if __name__ == "__main__":
    main()

