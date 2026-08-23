from __future__ import annotations

"""Pack 09-only review-pack generation using the fixture manifest as authority."""

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import numpy as np

REVIEW_PACK_SCHEMA = "rdp.two_period_overlay.pack09_review_pack.v1"
PACK09_EXPERIMENT_ID = "p13_p31_one_word_d30_s2_discovery_panel_v1"
FIXTURE_MANIFEST = Path(
    "docs/release_contracts/v1/two_period_fixture_manifest.json"
)
_FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
_REFERENCE_KEYS = {
    "expected_key",
    "expected_plaintext",
    "ground_truth",
    "known_key",
    "known_plaintext",
    "match_ratio",
    "oracle",
    "oracle_key",
    "reference",
    "reference_evaluation",
    "reference_metrics",
    "test_key",
    "truth",
    "truth_key",
    "truth_metrics",
}
_REFERENCE_PREFIXES = ("oracle_", "reference_", "truth_")
_TERMINAL_ARTIFACTS = {
    "artifacts/experiment_result.json",
    "artifacts/experiment_e/terminal_evaluation.json",
}
_BASE_REQUIRED_ARTIFACTS = (
    "artifacts/experiment_manifest.json",
    "artifacts/experiment_result.json",
    "artifacts/p13_p31_one_word_d30_summary.json",
    "artifacts/execution_timing.json",
    "artifacts/experiment_e/visible_status.json",
    "artifacts/experiment_e/runtime_plan.json",
    "artifacts/experiment_e/contract_preflight.json",
    "artifacts/experiment_e/operational_gate.json",
    "artifacts/experiment_e/attempt_timing.json",
    "artifacts/experiment_e/search_summary.json",
    "artifacts/experiment_e/replay_summary.json",
    "artifacts/experiment_e/terminal_evaluation.json",
    "artifacts/experiment_e/required_artifacts.json",
)


@dataclass(frozen=True, slots=True)
class ReviewPackResult:
    path: Path
    pack_complete: bool
    review_ready: bool
    missing_artifacts: tuple[str, ...]
    missing_sources: tuple[str, ...]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON in {path.name}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _external_root(path: Path, repo_root: Path, name: str) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError(f"{name} must be an absolute external path")
    resolved = path.resolve()
    if resolved == repo_root or resolved.is_relative_to(repo_root):
        raise ValueError(f"{name} must stay outside the repository")
    return resolved


def _safe_relative(value: str, name: str) -> Path:
    path = Path(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in value
        or path.as_posix() != value
    ):
        raise ValueError(f"{name} contains an unsafe path: {value!r}")
    return path


def fixture_source_records(repo_root: Path) -> tuple[dict[str, Any], ...]:
    """Return and verify the exact source closure declared by the Pack 09 manifest."""

    repo_root = repo_root.resolve()
    payload = _read_json(repo_root / FIXTURE_MANIFEST)
    if payload.get("schema") != "rdp_two_period_fixture_manifest.v1":
        raise ValueError("unsupported Pack 09 fixture manifest schema")
    rows = payload.get("retained_sources")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Pack 09 fixture manifest has no retained_sources")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"retained_sources[{index}] must be an object")
        value = str(row.get("path") or "")
        relative = _safe_relative(value, f"retained_sources[{index}].path")
        if value in seen:
            raise ValueError(f"duplicate Pack 09 source path: {value}")
        seen.add(value)
        source = repo_root / relative
        if not source.is_file():
            raise FileNotFoundError(f"required Pack 09 source is missing: {value}")
        data = source.read_bytes()
        expected = str(row.get("sha256") or "").lower()
        actual = _sha256(data)
        if expected != actual:
            raise ValueError(f"Pack 09 source hash mismatch: {value}")
        records.append(
            {
                "path": value,
                "role": str(row.get("role") or "retained source"),
                "size_bytes": len(data),
                "sha256": actual,
            }
        )
    return tuple(records)


def _source_fingerprint(records: tuple[dict[str, Any], ...]) -> str:
    encoded = json.dumps(
        records, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.blake2b(
        encoded, digest_size=20, person=b"rdp-pack09-src"
    ).hexdigest()


def _required_artifacts(run_dir: Path) -> tuple[str, ...]:
    inventory = run_dir / "artifacts/experiment_e/required_artifacts.json"
    if not inventory.is_file():
        return _BASE_REQUIRED_ARTIFACTS
    payload = _read_json(inventory)
    paths = payload.get("paths")
    if not isinstance(paths, list) or any(not isinstance(item, str) for item in paths):
        raise ValueError("Pack 09 required-artifact inventory is invalid")
    dynamic = tuple(
        _safe_relative(item, "Pack 09 required-artifact inventory").as_posix()
        for item in paths
    )
    return tuple(dict.fromkeys((*_BASE_REQUIRED_ARTIFACTS, *dynamic)))


def _contains_reference(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key).strip().lower()
            if token != "truth_policy" and (
                token in _REFERENCE_KEYS or token.startswith(_REFERENCE_PREFIXES)
            ):
                return str(key)
            found = _contains_reference(item)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for item in value:
            found = _contains_reference(item)
            if found is not None:
                return found
    return None


def _guard_run_json(relative: Path, data: bytes) -> None:
    if relative.as_posix() in _TERMINAL_ARTIFACTS or relative.suffix.lower() != ".json":
        return
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return
    found = _contains_reference(value)
    if found is not None:
        raise ValueError(
            f"search-visible run artifact {relative.as_posix()} "
            f"contains reference field {found!r}"
        )


def _git_state(repo_root: Path) -> dict[str, Any]:
    def call(*args: str) -> str | None:
        result = subprocess.run(
            ["git", *args], cwd=repo_root, capture_output=True, text=True, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else None

    return {
        "commit": call("rev-parse", "HEAD"),
        "branch": call("branch", "--show-current"),
        "working_tree_clean": not bool(call("status", "--porcelain")),
    }


def _record(path: str, data: bytes, purpose: str) -> dict[str, Any]:
    return {
        "path": path,
        "size_bytes": len(data),
        "sha256": _sha256(data),
        "purpose": purpose,
    }


def write_review_pack(
    repo_root: Path,
    run_dir: Path,
    *,
    output_root: Path,
) -> ReviewPackResult:
    repo_root = repo_root.resolve()
    run_dir = _external_root(run_dir, repo_root, "run_dir")
    output_root = _external_root(output_root, repo_root, "output_root")
    manifest_path = run_dir / "artifacts/experiment_manifest.json"
    result_path = run_dir / "artifacts/experiment_result.json"
    manifest = _read_json(manifest_path) if manifest_path.is_file() else {}
    result = _read_json(result_path) if result_path.is_file() else {}
    experiment = manifest.get("experiment")
    experiment = experiment if isinstance(experiment, Mapping) else {}
    experiment_id = str(
        experiment.get("experiment_id") or result.get("experiment_id") or "unknown"
    )
    if experiment_id != PACK09_EXPERIMENT_ID:
        raise ValueError(f"review_pack supports only Pack 09, not {experiment_id!r}")

    required = _required_artifacts(run_dir)
    missing_artifacts = tuple(
        sorted(path for path in required if not (run_dir / path).is_file())
    )
    sources = fixture_source_records(repo_root)
    entries: dict[str, bytes] = {}
    run_records: list[dict[str, Any]] = []
    for source in sorted(path for path in run_dir.rglob("*") if path.is_file()):
        relative = source.relative_to(run_dir)
        member = f"run/{relative.as_posix()}"
        data = source.read_bytes()
        _guard_run_json(relative, data)
        entries[member] = data
        run_records.append(_record(member, data, "Pack 09 run evidence"))

    source_records: list[dict[str, Any]] = []
    fixture_manifest_data = (repo_root / FIXTURE_MANIFEST).read_bytes()
    fixture_member = f"source/{FIXTURE_MANIFEST.as_posix()}"
    entries[fixture_member] = fixture_manifest_data
    source_records.append(_record(fixture_member, fixture_manifest_data, "source authority"))
    for row in sources:
        relative = Path(str(row["path"]))
        data = (repo_root / relative).read_bytes()
        member = f"source/{relative.as_posix()}"
        entries[member] = data
        source_records.append(_record(member, data, str(row["role"])))

    source_fingerprint = _source_fingerprint(sources)
    pack_complete = not missing_artifacts
    review_ready = pack_complete and result.get("status") == "completed"
    review_manifest = {
        "schema": REVIEW_PACK_SCHEMA,
        "experiment_id": experiment_id,
        "run_id": run_dir.name,
        "run_status": result.get("status", "unknown"),
        "decision": result.get("decision"),
        "stop_reason": result.get("stop_reason"),
        "required_artifacts": list(required),
        "missing_artifacts": list(missing_artifacts),
        "missing_sources": [],
        "source_authority": FIXTURE_MANIFEST.as_posix(),
        "source_fingerprint": source_fingerprint,
        "git": _git_state(repo_root),
        "environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "numpy_version": np.__version__,
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
            "byteorder": sys.byteorder,
        },
        "run_files": run_records,
        "source_files": source_records,
        "pack_complete": pack_complete,
        "review_ready": review_ready,
    }
    entries["review_manifest.json"] = _json_bytes(review_manifest)
    entries["README_FIRST.md"] = (
        "# Pack 09 review pack\n\n"
        f"Run: `{run_dir.name}`\n\n"
        f"Complete: `{str(pack_complete).lower()}`\n\n"
        f"Review ready: `{str(review_ready).lower()}`\n"
    ).encode("utf-8")
    inventory = [f"{_sha256(data)}  {member}" for member, data in sorted(entries.items())]
    entries["file_inventory.sha256"] = ("\n".join(inventory) + "\n").encode("ascii")

    output_root.mkdir(parents=True, exist_ok=True)
    pack_path = output_root / f"pack09_{run_dir.name}_review_pack.zip"
    if pack_path.exists():
        raise FileExistsError(f"refusing to overwrite Pack 09 review pack: {pack_path}")
    temporary = pack_path.with_name(f".{pack_path.name}.tmp")
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for member in sorted(entries):
                info = ZipInfo(PurePosixPath(member).as_posix(), date_time=_FIXED_ZIP_TIME)
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                info.create_system = 3
                archive.writestr(info, entries[member], compress_type=ZIP_DEFLATED)
        temporary.replace(pack_path)
    finally:
        temporary.unlink(missing_ok=True)
    return ReviewPackResult(
        path=pack_path,
        pack_complete=pack_complete,
        review_ready=review_ready,
        missing_artifacts=missing_artifacts,
        missing_sources=(),
    )


def write_review_pack_after_run(
    repo_root: Path,
    run_dir: Path,
    *,
    output_root: Path,
    original_error: BaseException | None = None,
) -> ReviewPackResult | None:
    try:
        return write_review_pack(repo_root, run_dir, output_root=output_root)
    except Exception as pack_error:
        if original_error is None:
            raise
        add_note = getattr(original_error, "add_note", None)
        if callable(add_note):
            add_note(f"automatic Pack 09 review-pack generation failed: {pack_error}")
        return None


__all__ = [
    "FIXTURE_MANIFEST",
    "PACK09_EXPERIMENT_ID",
    "REVIEW_PACK_SCHEMA",
    "ReviewPackResult",
    "fixture_source_records",
    "write_review_pack",
    "write_review_pack_after_run",
]
