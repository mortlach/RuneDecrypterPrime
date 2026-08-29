from __future__ import annotations
import json
import pathlib
import re
import zipfile
from dataclasses import dataclass
from typing import Any
from tools.assets.audit_lm_large_assets import inspect_file_for_path_signatures
from tools.assets.release_asset_installer import sha256_file

DEFAULT_RELEASE_REPOSITORY = "mortlach/rdp_assets"
DEFAULT_RELEASE_TAG = "rdp-v1.0.0-lm-large"
DEFAULT_TARGET_PART_BYTES = 550 * 1024 * 1024
RUNTIME_PREFIX = pathlib.PurePosixPath("language_model/lmp")
RELEASE_ASSET_PREFIX = "rdp-v1-lm-large"


class AssetBuildError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RuntimeAsset:
    relpath: str
    sha256: str
    size_bytes: int
    required_for: tuple[str, ...]


def _load_index(source_lmp_root: pathlib.Path) -> dict[str, Any]:
    index_path = source_lmp_root / "index.json"
    if not index_path.is_file():
        raise AssetBuildError(f"missing LM root index: {index_path}")
    return json.loads(index_path.read_text(encoding="utf-8"))


def _walk_strings(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, str):
        found.add(value)
    elif isinstance(value, dict):
        for child in value.values():
            found.update(_walk_strings(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_walk_strings(child))
    return found


def _expand_pattern(
    pattern: str, *, mode: str, pos: str, n: int, stat: str | None = None
) -> str:
    expanded = (
        pattern.replace("%%MODE%%", mode)
        .replace("%%POS%%", pos)
        .replace("%%N%%", str(n))
    )
    if stat is not None:
        expanded = expanded.replace("%%STAT%%", stat)
    return expanded


def _derive_pattern_files(index: dict[str, Any]) -> set[str]:
    files = {"index.json"}
    models = index.get("models")
    if not isinstance(models, dict):
        return files
    for model in models.values():
        if not isinstance(model, dict):
            continue
        ns = model.get("n", [])
        stats = model.get("stats", [])
        joint_pattern = model.get("joint_pattern")
        ecdf_pattern = model.get("ecdf_pattern")
        for mode in ("ltr", "rtl"):
            for pos in ("nose", "wise"):
                for n in ns:
                    if isinstance(joint_pattern, str):
                        files.add(
                            _expand_pattern(joint_pattern, mode=mode, pos=pos, n=int(n))
                        )
                    if isinstance(ecdf_pattern, str):
                        for stat in stats:
                            files.add(
                                _expand_pattern(
                                    ecdf_pattern,
                                    mode=mode,
                                    pos=pos,
                                    n=int(n),
                                    stat=str(stat),
                                )
                            )
    return files


def derive_expected_lmp_files(source_lmp_root: pathlib.Path | str) -> list[str]:
    root = pathlib.Path(source_lmp_root)
    index = _load_index(root)
    files = _derive_pattern_files(index)
    files.update(
        {
            item.replace("\\", "/")
            for item in _walk_strings(index)
            if "/" in item and pathlib.PurePosixPath(item).suffix and ("%%" not in item)
        }
    )
    cleaned: list[str] = []
    for item in files:
        rel = pathlib.PurePosixPath(item)
        if rel.is_absolute() or ".." in rel.parts:
            raise AssetBuildError(f"unsafe index path: {item}")
        if not (root / pathlib.Path(*rel.parts)).is_file():
            raise AssetBuildError(f"index references missing file: {item}")
        cleaned.append(rel.as_posix())
    if not cleaned:
        raise AssetBuildError("root index did not reference any runtime files")
    return sorted(cleaned)


def _is_ci_light_required(relpath: str) -> bool:
    lower = relpath.lower()
    if lower == "index.json":
        return True
    if "_nose" not in lower and "/nose_" not in lower:
        return False
    return re.search("(?:_n|_)([12])(?:_|\\.)", lower) is not None


def _is_large_required(relpath: str) -> bool:
    lower = relpath.lower()
    return (
        "_3_" in lower
        or "_4_" in lower
        or "_n3_" in lower
        or ("_n4_" in lower)
        or lower.endswith("_3.bin.zst")
        or lower.endswith("_4.bin.zst")
    )


def _asset_id(relpath: str) -> str:
    stem = relpath.replace("/", ".").replace("-", "_")
    while ".." in stem:
        stem = stem.replace("..", ".")
    return "lm.lmp." + "".join(
        (ch.lower() if ch.isalnum() or ch == "." else "_" for ch in stem)
    )


def collect_runtime_assets(source_lmp_root: pathlib.Path | str) -> list[RuntimeAsset]:
    root = pathlib.Path(source_lmp_root)
    relpaths = derive_expected_lmp_files(root)
    rows: list[RuntimeAsset] = []
    for relpath in relpaths:
        path = root / pathlib.Path(*pathlib.PurePosixPath(relpath).parts)
        hits = inspect_file_for_path_signatures(root, path)
        bad_hits = [
            hit
            for hit in hits
            if hit["classification"] in {"local_metadata", "rebuild_required"}
        ]
        if bad_hits:
            raise AssetBuildError(
                f"local path metadata requires review before release: {relpath}"
            )
        required_for = ["v1_lm_runtime_full"]
        if _is_ci_light_required(relpath):
            required_for.append("v1_lm_ci_light")
        if _is_large_required(relpath):
            required_for.append("v1_lm_large_required")
        rows.append(
            RuntimeAsset(
                relpath=relpath,
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
                required_for=tuple(required_for),
            )
        )
    return rows


def _partition_assets(
    rows: list[RuntimeAsset], target_part_bytes: int
) -> list[list[RuntimeAsset]]:
    parts: list[list[RuntimeAsset]] = []
    current: list[RuntimeAsset] = []
    current_size = 0
    for row in rows:
        if current and current_size + row.size_bytes > target_part_bytes:
            parts.append(current)
            current = []
            current_size = 0
        current.append(row)
        current_size += row.size_bytes
    if current:
        parts.append(current)
    return parts


def _github_release_url(repository: str, tag: str, name: str) -> str:
    return f"https://github.com/{repository}/releases/download/{tag}/{name}"


def _write_zip_part(
    source_lmp_root: pathlib.Path,
    output_dir: pathlib.Path,
    part_index: int,
    rows: list[RuntimeAsset],
) -> pathlib.Path:
    name = f"{RELEASE_ASSET_PREFIX}-part{part_index:03d}.zip"
    zip_path = output_dir / name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for row in rows:
            source = source_lmp_root / pathlib.Path(
                *pathlib.PurePosixPath(row.relpath).parts
            )
            archive_name = (
                RUNTIME_PREFIX / pathlib.PurePosixPath(row.relpath)
            ).as_posix()
            archive.write(source, archive_name)
    return zip_path


def build_lm_large_release_bundle(
    source_lmp_root: pathlib.Path | str,
    output_dir: pathlib.Path | str,
    *,
    target_part_bytes: int = DEFAULT_TARGET_PART_BYTES,
    release_repository: str = DEFAULT_RELEASE_REPOSITORY,
    release_tag: str = DEFAULT_RELEASE_TAG,
) -> dict[str, Any]:
    source_root = pathlib.Path(source_lmp_root)
    release_root = pathlib.Path(output_dir)
    release_root.mkdir(parents=True, exist_ok=True)
    runtime_assets = collect_runtime_assets(source_root)
    parts = _partition_assets(runtime_assets, target_part_bytes)
    release_assets: list[dict[str, Any]] = []
    sums_lines: list[str] = []
    for index, part_rows in enumerate(parts, start=1):
        zip_path = _write_zip_part(source_root, release_root, index, part_rows)
        digest = sha256_file(zip_path)
        release_assets.append(
            {
                "name": zip_path.name,
                "url": _github_release_url(
                    release_repository, release_tag, zip_path.name
                ),
                "sha256": digest,
                "size_bytes": zip_path.stat().st_size,
            }
        )
        sums_lines.append(f"{digest}  {zip_path.name}")
    installed_assets = [
        {
            "asset_id": _asset_id(row.relpath),
            "final_relpath": (
                RUNTIME_PREFIX / pathlib.PurePosixPath(row.relpath)
            ).as_posix(),
            "sha256": row.sha256,
            "size_bytes": row.size_bytes,
            "required_for": list(row.required_for),
            "policy": "required_large_v1_lm_asset"
            if "v1_lm_large_required" in row.required_for
            else "required_v1_lm_runtime_asset",
        }
        for row in runtime_assets
    ]
    manifest = {
        "schema_version": 2,
        "assets_root": "assets",
        "release_asset_sets": {
            "v1_lm_ci_light": {
                "required_by_default_install": False,
                "bundled_with_source": True,
                "description": "Source-bundled LM1/LM2 nose runtime assets for CI-light checks.",
            },
            "v1_lm_runtime_full": {
                "required_by_default_install": True,
                "description": "Full V1 runtime LM asset set implied by root index.json.",
                "release_repository": release_repository,
                "release_tag": release_tag,
                "release_assets": release_assets,
            },
            "v1_lm_large_required": {
                "required_by_default_install": True,
                "description": "Required n=3/n=4 LM assets for full RDP V1.",
                "included_in": "v1_lm_runtime_full",
            },
        },
        "installed_assets": installed_assets,
    }
    manifest_path = release_root / f"{RELEASE_ASSET_PREFIX}-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (release_root / f"{RELEASE_ASSET_PREFIX}-SHA256SUMS.txt").write_text(
        "\n".join(sums_lines) + "\n", encoding="utf-8"
    )
    return manifest
