from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import ssl
import tempfile
import urllib.request
import zipfile
from typing import Any


CHUNK_SIZE = 1024 * 1024
SHA256_HEX_LENGTH = 64


class AssetInstallError(RuntimeError):
    """Raised when release assets cannot be installed or verified."""


def _fail(message: str) -> None:
    raise AssetInstallError(message)


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{label} must be a list")
    return value


def _validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != SHA256_HEX_LENGTH:
        _fail(f"{label} must be a SHA256 hex string")
    try:
        int(value, 16)
    except ValueError:
        _fail(f"{label} must be a SHA256 hex string")
    return value.lower()


def _validate_size(value: Any, label: str) -> int:
    if not isinstance(value, int) or value < 0:
        _fail(f"{label} must be a non-negative integer")
    return value


def _has_windows_drive(path_text: str) -> bool:
    return len(path_text) >= 2 and path_text[1] == ":" and path_text[0].isalpha()


def _safe_relpath(path_text: Any, label: str) -> pathlib.PurePosixPath:
    if not isinstance(path_text, str) or not path_text.strip():
        _fail(f"{label} must be a non-empty relative path")
    if "\\" in path_text:
        _fail(f"{label} must use forward slashes")
    if _has_windows_drive(path_text):
        _fail(f"{label} must not include a drive prefix")
    rel = pathlib.PurePosixPath(path_text)
    if rel.is_absolute():
        _fail(f"{label} must not be absolute")
    if any(part in {"", ".", ".."} for part in rel.parts):
        _fail(f"{label} must not contain empty, '.', or '..' parts")
    return rel


def _safe_leaf_name(name: Any, label: str) -> str:
    if not isinstance(name, str) or not name.strip():
        _fail(f"{label} must be non-empty")
    rel = _safe_relpath(name, label)
    if len(rel.parts) != 1:
        _fail(f"{label} must be a single file name")
    return rel.name


def _validate_release_asset_sets(manifest: dict[str, Any]) -> dict[str, Any]:
    sets = _require_mapping(manifest.get("release_asset_sets", {}), "release_asset_sets")
    for set_name, asset_set in sets.items():
        if not isinstance(set_name, str) or not set_name:
            _fail("release asset set names must be non-empty")
        row = _require_mapping(asset_set, f"release_asset_sets.{set_name}")
        included_in = row.get("included_in")
        if included_in is not None and (not isinstance(included_in, str) or not included_in):
            _fail(f"release_asset_sets.{set_name}.included_in must be a non-empty string")
        release_assets = row.get("release_assets", [])
        if release_assets:
            for index, release_asset in enumerate(_require_list(release_assets, f"{set_name}.release_assets")):
                item = _require_mapping(release_asset, f"{set_name}.release_assets[{index}]")
                _safe_leaf_name(item.get("name"), f"{set_name}.release_assets[{index}].name")
                url = item.get("url")
                if not isinstance(url, str) or not url:
                    _fail(f"{set_name}.release_assets[{index}].url must be non-empty")
                item["sha256"] = _validate_sha256(item.get("sha256"), f"{set_name}.release_assets[{index}].sha256")
                item["size_bytes"] = _validate_size(
                    item.get("size_bytes"),
                    f"{set_name}.release_assets[{index}].size_bytes",
                )
        if row.get("required_by_default_install") and included_in is None and not release_assets:
            _fail(f"required release asset set {set_name} must list release_assets")
    return sets


def _validate_installed_assets(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    installed = _require_list(manifest.get("installed_assets", []), "installed_assets")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(installed):
        row = _require_mapping(raw, f"installed_assets[{index}]")
        asset_id = row.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            _fail(f"installed_assets[{index}].asset_id must be non-empty")
        if asset_id in seen_ids:
            _fail(f"duplicate asset_id: {asset_id}")
        seen_ids.add(asset_id)
        relpath = _safe_relpath(row.get("final_relpath"), f"installed_assets[{index}].final_relpath").as_posix()
        if relpath in seen_paths:
            _fail(f"duplicate final_relpath: {relpath}")
        seen_paths.add(relpath)
        required_for = _require_list(row.get("required_for", []), f"installed_assets[{index}].required_for")
        if not required_for or not all(isinstance(item, str) and item for item in required_for):
            _fail(f"installed_assets[{index}].required_for must list asset set names")
        row["sha256"] = _validate_sha256(row.get("sha256"), f"installed_assets[{index}].sha256")
        row["size_bytes"] = _validate_size(row.get("size_bytes"), f"installed_assets[{index}].size_bytes")
        row["final_relpath"] = relpath
        normalized.append(row)
    return normalized


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    _require_mapping(manifest, "manifest")
    if manifest.get("schema_version") != 2:
        _fail("asset release manifest schema_version must be 2")
    assets_root = _safe_relpath(manifest.get("assets_root"), "assets_root").as_posix()
    manifest["assets_root"] = assets_root
    _validate_release_asset_sets(manifest)
    _validate_installed_assets(manifest)
    return manifest


def load_manifest(manifest_path: pathlib.Path | str) -> dict[str, Any]:
    path = pathlib.Path(manifest_path)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"invalid JSON manifest {path}: {exc}")
    return validate_manifest(manifest)


def select_release_asset_set(manifest: dict[str, Any], asset_set_name: str) -> dict[str, Any]:
    manifest = validate_manifest(manifest)
    sets = manifest["release_asset_sets"]
    if asset_set_name not in sets:
        _fail(f"unknown release asset set: {asset_set_name}")
    row = dict(sets[asset_set_name])
    parent = row.get("included_in")
    if parent:
        if parent not in sets:
            _fail(f"asset set {asset_set_name} includes unknown parent {parent}")
        parent_row = dict(sets[parent])
        row["release_assets"] = parent_row.get("release_assets", [])
        row["release_repository"] = parent_row.get("release_repository")
        row["release_tag"] = parent_row.get("release_tag")
    if row.get("required_by_default_install") and not row.get("release_assets"):
        _fail(f"required release asset set {asset_set_name} has no release_assets")
    return row


def installed_assets_for_set(manifest: dict[str, Any], asset_set_name: str) -> list[dict[str, Any]]:
    manifest = validate_manifest(manifest)
    if asset_set_name not in manifest["release_asset_sets"]:
        _fail(f"unknown release asset set: {asset_set_name}")
    rows = [
        row
        for row in manifest["installed_assets"]
        if asset_set_name in set(row.get("required_for", []))
    ]
    if not rows:
        _fail(f"release asset set {asset_set_name} has no installed assets")
    return rows


def sha256_file(path: pathlib.Path | str) -> str:
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: pathlib.Path | str, expected_sha256: str, expected_size: int) -> None:
    file_path = pathlib.Path(path)
    if not file_path.is_file():
        _fail(f"missing required file: {file_path}")
    actual_size = file_path.stat().st_size
    if actual_size != expected_size:
        _fail(f"size mismatch for {file_path}: expected {expected_size}, found {actual_size}")
    actual_sha256 = sha256_file(file_path)
    if actual_sha256 != expected_sha256.lower():
        _fail(f"SHA256 mismatch for {file_path}: expected {expected_sha256}, found {actual_sha256}")


def download_file(url: str, destination: pathlib.Path | str, expected_sha256: str, expected_size: int) -> pathlib.Path:
    destination_path = pathlib.Path(destination)
    if destination_path.exists():
        try:
            verify_file(destination_path, expected_sha256, expected_size)
            print(f"[PASS] Reuse verified download {destination_path.name}")
            return destination_path
        except AssetInstallError:
            destination_path.unlink()

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[RUN ] Download {destination_path.name}")
    context = ssl.create_default_context()
    with tempfile.NamedTemporaryFile(dir=str(destination_path.parent), delete=False) as tmp_handle:
        tmp_path = pathlib.Path(tmp_handle.name)
        try:
            with urllib.request.urlopen(url, context=context) as response:
                shutil.copyfileobj(response, tmp_handle, length=CHUNK_SIZE)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

    try:
        verify_file(tmp_path, expected_sha256, expected_size)
        tmp_path.replace(destination_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    print(f"[PASS] Download verified {destination_path.name}")
    return destination_path


def _safe_destination(root: pathlib.Path, rel: pathlib.PurePosixPath) -> pathlib.Path:
    target = root.joinpath(*rel.parts)
    resolved_root = root.resolve()
    resolved_target_parent = target.parent.resolve()
    if resolved_root != resolved_target_parent and resolved_root not in resolved_target_parent.parents:
        _fail(f"path escapes extraction root: {rel.as_posix()}")
    return target


def safe_extract_zip(zip_path: pathlib.Path | str, destination_root: pathlib.Path | str) -> list[pathlib.Path]:
    root = pathlib.Path(destination_root)
    root.mkdir(parents=True, exist_ok=True)
    extracted: list[pathlib.Path] = []
    with zipfile.ZipFile(zip_path, "r") as archive:
        infos = archive.infolist()
        for info in infos:
            name = info.filename.rstrip("/")
            if not name:
                continue
            rel = _safe_relpath(name, f"zip member {info.filename!r}")
            _safe_destination(root, rel)
        for info in infos:
            name = info.filename.rstrip("/")
            if not name:
                continue
            rel = _safe_relpath(name, f"zip member {info.filename!r}")
            target = _safe_destination(root, rel)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink, length=CHUNK_SIZE)
            extracted.append(target)
    return extracted


def verify_installed_assets(
    manifest: dict[str, Any],
    asset_set_name: str,
    assets_root: pathlib.Path | str,
) -> list[dict[str, Any]]:
    rows = installed_assets_for_set(manifest, asset_set_name)
    root = pathlib.Path(assets_root)
    for row in rows:
        path = root.joinpath(*pathlib.PurePosixPath(row["final_relpath"]).parts)
        try:
            verify_file(path, row["sha256"], row["size_bytes"])
        except AssetInstallError as exc:
            _fail(f"{row['asset_id']}: {exc}")
    print(f"[PASS] {len(rows)} runtime asset files verified")
    return rows


def install_release_asset_set(
    manifest_path: pathlib.Path | str,
    asset_set_name: str,
    download_dir: pathlib.Path | str,
    assets_root: pathlib.Path | str,
) -> None:
    manifest = load_manifest(manifest_path)
    selected = select_release_asset_set(manifest, asset_set_name)
    release_assets = _require_list(selected.get("release_assets", []), f"{asset_set_name}.release_assets")
    if not release_assets:
        _fail(f"release asset set {asset_set_name} has no release assets")

    download_root = pathlib.Path(download_dir)
    for index, release_asset in enumerate(release_assets, start=1):
        name = _safe_leaf_name(release_asset["name"], "release asset name")
        zip_path = download_root / name
        if zip_path.exists():
            try:
                verify_file(zip_path, release_asset["sha256"], release_asset["size_bytes"])
                print(f"[PASS] Reuse verified download {name}")
            except AssetInstallError:
                zip_path.unlink()
                download_file(release_asset["url"], zip_path, release_asset["sha256"], release_asset["size_bytes"])
        else:
            download_file(release_asset["url"], zip_path, release_asset["sha256"], release_asset["size_bytes"])
        print(f"[RUN ] Extract LM asset bundle {index}/{len(release_assets)}")
        safe_extract_zip(zip_path, assets_root)
        print("[PASS] Extracted safely")
    print("[RUN ] Verify V1 LM runtime assets")
    verify_installed_assets(manifest, asset_set_name, assets_root)
