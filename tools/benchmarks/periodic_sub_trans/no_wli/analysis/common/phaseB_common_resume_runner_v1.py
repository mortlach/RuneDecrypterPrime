from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def config_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_csv_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            return [str(item) for item in next(reader)]
        except StopIteration:
            return []


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
            count += 1
    return count


def append_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    count = 0
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
            count += 1
    return count


def ensure_csv_ready(path: Path, fieldnames: Sequence[str], *, resume_mode: bool, force_restart: bool) -> None:
    if force_restart and path.exists():
        path.unlink()
    if path.exists() and resume_mode:
        actual = read_csv_header(path)
        expected = list(fieldnames)
        if actual != expected:
            raise ValueError(f"CSV header mismatch for {path}: expected={expected!r} actual={actual!r}")
        return
    if not path.exists() or not resume_mode:
        write_csv(path, [], fieldnames)


def completed_sample_ids(summary_path: Path, current_config_hash: str) -> set[str]:
    return {
        row["sample_id"]
        for row in read_csv_rows(summary_path)
        if row.get("sample_id") and row.get("config_hash") == current_config_hash
    }


def attempted_sample_ids(sample_path: Path, current_config_hash: str) -> set[str]:
    return {
        row["sample_id"]
        for row in read_csv_rows(sample_path)
        if row.get("sample_id") and row.get("config_hash") == current_config_hash
    }


def safe_sample_file_id(sample_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.=-]+", "_", sample_id).strip("_")
    digest = hashlib.blake2b(sample_id.encode("utf-8"), digest_size=8).hexdigest()
    if len(safe) > 140:
        safe = safe[:140]
    return f"{safe}__{digest}"


def validate_resume_config(summary_path: Path, manifest_path: Path, current_config_hash: str) -> None:
    for row in read_csv_rows(summary_path):
        if not row.get("sample_id"):
            continue
        existing = row.get("config_hash", "")
        if not existing:
            raise RuntimeError("unsafe resume: committed summary row has no config_hash")
        if existing != current_config_hash:
            raise RuntimeError("unsafe resume: committed summary row config_hash differs")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        existing = str(manifest.get("config_hash", ""))
        if existing and existing != current_config_hash:
            raise RuntimeError("unsafe resume: run_manifest config_hash differs")
