from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "release_contracts" / "v1" / "two_period_fixture_manifest.json"
REVIEW_DATE = "2026-07-30"


def local_import_closure(root: Path, entry_point: str) -> set[str]:
    pending = [entry_point]
    closure: set[str] = set()
    while pending:
        relpath = pending.pop()
        if relpath in closure:
            continue
        source = root / relpath
        if not source.is_file():
            raise FileNotFoundError(f"fixture dependency is missing: {relpath}")
        closure.add(relpath)
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=relpath)
        modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
        for module in modules:
            if not module.startswith("cipher_development"):
                continue
            candidate = Path(*module.split(".")).with_suffix(".py").as_posix()
            if (root / candidate).is_file():
                pending.append(candidate)
    return closure


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh_manifest(root: Path = ROOT, manifest_path: Path = MANIFEST_PATH) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry_point = manifest["entry_point"]
    closure = local_import_closure(root, entry_point)
    rows_by_path = {row["path"]: dict(row) for row in manifest["retained_sources"]}
    if set(rows_by_path) != closure:
        missing = sorted(closure - set(rows_by_path))
        stale = sorted(set(rows_by_path) - closure)
        raise RuntimeError(
            "Pack 09 dependency closure changed; review roles before regeneration: "
            f"unmanifested={missing}, no_longer_imported={stale}"
        )

    changed: list[str] = []
    rows: list[dict] = []
    for path in sorted(closure):
        row = rows_by_path[path]
        digest = sha256_file(root / path)
        if row.get("sha256") != digest:
            changed.append(path)
        row["sha256"] = digest
        rows.append(row)
    manifest["retained_sources"] = rows
    previous_review = manifest.get("dependency_review", {})
    reviewed_changed = changed or list(
        previous_review.get("reviewed_changed_dependencies", [])
    )
    manifest["dependency_review"] = {
        "review_date": REVIEW_DATE,
        "closure_changed": False,
        "reviewed_changed_dependencies": reviewed_changed,
        "decision": "retain_current_closure_and_refresh_hashes",
        "production_package_boundary_changed": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    manifest = refresh_manifest()
    print(
        "Pack 09 fixture manifest refreshed: "
        f"{len(manifest['retained_sources'])} files, "
        f"{len(manifest['dependency_review']['reviewed_changed_dependencies'])} reviewed changed dependencies"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
