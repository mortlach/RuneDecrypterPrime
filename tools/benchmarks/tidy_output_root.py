from __future__ import annotations

"""Tidy loose root-level benchmark output folders into canonical homes.

Hardcoded switches by repo rule:
- no CLI args
- deterministic routing
- manifest written for auditability

This tool is intentionally selective:
- named canonical roots stay where they are
- recognized legacy timestamped folders are copied into their canonical home
- source folders are removed only after successful copy
"""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


OUTPUT_ROOT = Path("output") / "tools" / "benchmarks"
MANIFEST_PATH = OUTPUT_ROOT / "root_tidy_manifest.json"
ROOT_LAYOUT_NOTE_PATH = OUTPUT_ROOT / "ROOT_LAYOUT.md"

# This script exists specifically to tidy the root output folder. Successful
# copies are pruned from the root so the clutter actually goes away.
PRUNE_AFTER_COPY = True

KEEP_ROOT_NAMES = {
    "analysis",
    "community",
    "periodic_sub_trans",
    "scoring",
    "solve_proof",
    "zip_src_nobloat",
}


@dataclass(frozen=True)
class RouteRule:
    needle: str
    category: str
    destination_parts: tuple[str, ...]


ROUTE_RULES = (
    RouteRule(
        "__bench_solve_pipeline_no_wli__",
        "periodic_sub_trans_no_wli_legacy",
        ("periodic_sub_trans", "no_wli", "legacy_import"),
    ),
    RouteRule(
        "__bench_solve_col_then_sub_pipeline__",
        "periodic_sub_trans_col_then_sub_legacy",
        ("periodic_sub_trans", "col_then_sub", "legacy_import"),
    ),
    RouteRule(
        "__bench_solve_sub_then_col_pipeline__",
        "periodic_sub_trans_sub_then_col_legacy",
        ("periodic_sub_trans", "sub_then_col", "legacy_import"),
    ),
    RouteRule(
        "__bench_solve_pipeline__",
        "periodic_sub_trans_col_then_sub_legacy_generic",
        ("periodic_sub_trans", "col_then_sub", "legacy_import"),
    ),
    RouteRule(
        "__bench_solve_cribs__",
        "solve_proof_legacy_cribs",
        ("solve_proof", "legacy_import"),
    ),
    RouteRule(
        "__bench_solve__",
        "solve_proof_legacy",
        ("solve_proof", "legacy_import"),
    ),
    RouteRule(
        "__solve_proof_plan",
        "solve_proof_plan_legacy",
        ("solve_proof", "legacy_import"),
    ),
    RouteRule(
        "__bench__profile__",
        "analysis_legacy_profile_runs",
        ("analysis", "legacy_profile_runs"),
    ),
    RouteRule(
        "__bench__",
        "analysis_legacy_benchmark_runs",
        ("analysis", "legacy_benchmark_runs"),
    ),
)


def _classify_folder(name: str) -> RouteRule | None:
    lowered = str(name).lower()
    for rule in ROUTE_RULES:
        if rule.needle in lowered:
            return rule
    return None


def _iter_source_dirs(root: Path) -> Iterable[Path]:
    for src in sorted(root.iterdir()):
        if not src.is_dir():
            continue
        if src.name in KEEP_ROOT_NAMES:
            continue
        yield src


def _build_layout_note() -> str:
    lines = [
        "# Benchmark Output Root Layout",
        "",
        "This folder is the canonical top-level home for benchmark outputs.",
        "",
        "## Named roots that should stay here",
        "",
        "- `community/`",
        "- `periodic_sub_trans/`",
        "- `scoring/`",
        "- `zip_src_nobloat/`",
        "- `solve_proof/`",
        "- `analysis/`",
        "",
        "## Where the old loose timestamped folders belong",
        "",
        "- `*__bench_solve_pipeline_no_wli__*`",
        "  - `periodic_sub_trans/no_wli/legacy_import/`",
        "- `*__bench_solve_col_then_sub_pipeline__*`",
        "  - `periodic_sub_trans/col_then_sub/legacy_import/`",
        "- `*__bench_solve_sub_then_col_pipeline__*`",
        "  - `periodic_sub_trans/sub_then_col/legacy_import/`",
        "- `*__bench_solve_pipeline__*`",
        "  - `periodic_sub_trans/col_then_sub/legacy_import/`",
        "- `*__bench_solve__*` and `*__bench_solve_cribs__*`",
        "  - `solve_proof/legacy_import/`",
        "- `*__solve_proof_plan*`",
        "  - `solve_proof/legacy_import/`",
        "- `*__bench__profile__*`",
        "  - `analysis/legacy_profile_runs/`",
        "- `*__bench__*`",
        "  - `analysis/legacy_benchmark_runs/`",
        "",
        "## Audit files",
        "",
        "- `root_tidy_manifest.json`",
        "  - one row per migrated root-level folder with source, destination, category, and status",
        "",
        "The tidy process is non-destructive until copy succeeds. Source folders are only removed from the root after a successful copy.",
        "",
    ]
    return "\n".join(lines)


def _tree_signature(root: Path) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(root).as_posix()
        rows.append((rel, int(path.stat().st_size)))
    return rows


def _looks_like_duplicate_tree(src: Path, dst: Path) -> bool:
    if not src.exists() or not dst.exists():
        return False
    return _tree_signature(src) == _tree_signature(dst)


def tidy_output_root(*, prune_after_copy: bool = PRUNE_AFTER_COPY) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    for src in _iter_source_dirs(OUTPUT_ROOT):
        rule = _classify_folder(src.name)
        row: dict[str, object] = {
            "source": src.as_posix(),
            "category": "",
            "destination": "",
            "status": "",
            "error": "",
        }

        if rule is None:
            row["status"] = "skipped_unclassified"
            rows.append(row)
            continue

        dst = OUTPUT_ROOT.joinpath(*rule.destination_parts, src.name)
        dst.parent.mkdir(parents=True, exist_ok=True)

        row["category"] = rule.category
        row["destination"] = dst.as_posix()

        if dst.exists():
            if bool(prune_after_copy) and _looks_like_duplicate_tree(src, dst):
                shutil.rmtree(src)
                row["status"] = "pruned_existing_duplicate"
            else:
                row["status"] = "skipped_exists"
            rows.append(row)
            continue

        try:
            shutil.copytree(src, dst)
            row["status"] = "copied"
            if bool(prune_after_copy):
                shutil.rmtree(src)
                row["status"] = "copied_pruned"
        except Exception as exc:  # pragma: no cover - defensive manifest path
            row["status"] = "error"
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)

    MANIFEST_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    ROOT_LAYOUT_NOTE_PATH.write_text(_build_layout_note(), encoding="utf-8")
    return rows


def main() -> None:
    rows = tidy_output_root(prune_after_copy=PRUNE_AFTER_COPY)
    copied_pruned = sum(1 for row in rows if row["status"] == "copied_pruned")
    pruned_existing_duplicate = sum(
        1 for row in rows if row["status"] == "pruned_existing_duplicate"
    )
    copied = sum(1 for row in rows if row["status"] == "copied")
    skipped_exists = sum(1 for row in rows if row["status"] == "skipped_exists")
    skipped_unclassified = sum(1 for row in rows if row["status"] == "skipped_unclassified")
    errors = sum(1 for row in rows if row["status"] == "error")
    print(
        "[benchmark-root-tidy] "
        f"copied={copied} copied_pruned={copied_pruned} "
        f"pruned_existing_duplicate={pruned_existing_duplicate} "
        f"skipped_exists={skipped_exists} skipped_unclassified={skipped_unclassified} "
        f"errors={errors} manifest={MANIFEST_PATH.as_posix()}"
    )


if __name__ == "__main__":
    main()
