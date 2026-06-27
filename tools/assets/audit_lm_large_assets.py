from __future__ import annotations

import json
import pathlib
import zipfile
from typing import Any


PATH_SIGNATURES = (
    b"D" + b":" + b"\\",
    b"D" + b":" + b"/",
    b"C" + b":" + b"\\",
    b"C" + b":" + b"/",
    b"/" + b"home" + b"/",
)
TEXT_SUFFIXES = {".json", ".txt", ".md", ".csv", ".toml", ".yaml", ".yml"}


def _classify_npz_hit(runtime_relpath: str, member_name: str) -> str:
    lower_path = runtime_relpath.lower()
    lower_member = member_name.lower()
    if "_part" in lower_path and lower_path.startswith("wli/"):
        return "excluded_file"
    if any(lower_member.endswith(suffix) for suffix in TEXT_SUFFIXES):
        return "local_metadata"
    if lower_member.endswith(".npy"):
        return "false_positive"
    return "rebuild_required"


def _signature_names(blob: bytes) -> list[str]:
    return [sig.decode("ascii") for sig in PATH_SIGNATURES if sig in blob]


def inspect_npz_for_path_signatures(path: pathlib.Path, runtime_relpath: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(path, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            data = archive.read(info)
            signatures = _signature_names(data)
            if not signatures:
                continue
            suffix = pathlib.PurePosixPath(info.filename).suffix.lower()
            rows.append(
                {
                    "runtime_relpath": runtime_relpath,
                    "zip_member": info.filename,
                    "member_kind": "npy" if suffix == ".npy" else "text" if suffix in TEXT_SUFFIXES else "binary",
                    "signatures": signatures,
                    "classification": _classify_npz_hit(runtime_relpath, info.filename),
                }
            )
    return rows


def inspect_file_for_path_signatures(root: pathlib.Path, path: pathlib.Path) -> list[dict[str, Any]]:
    runtime_relpath = path.relative_to(root).as_posix()
    if path.suffix.lower() == ".npz":
        return inspect_npz_for_path_signatures(path, runtime_relpath)
    data = path.read_bytes()
    signatures = _signature_names(data)
    if not signatures:
        return []
    suffix = path.suffix.lower()
    return [
        {
            "runtime_relpath": runtime_relpath,
            "zip_member": None,
            "member_kind": "text" if suffix in TEXT_SUFFIXES else "binary",
            "signatures": signatures,
            "classification": "local_metadata"
            if suffix in TEXT_SUFFIXES
            else "false_positive"
            if runtime_relpath.lower().endswith(".bin.zst")
            else "rebuild_required",
        }
    ]


def audit_lm_large_assets(source_lmp_root: pathlib.Path | str) -> list[dict[str, Any]]:
    root = pathlib.Path(source_lmp_root)
    rows: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.extend(inspect_file_for_path_signatures(root, path))
    return rows


def write_audit_report(source_lmp_root: pathlib.Path | str, output_path: pathlib.Path | str) -> list[dict[str, Any]]:
    rows = audit_lm_large_assets(source_lmp_root)
    pathlib.Path(output_path).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows
