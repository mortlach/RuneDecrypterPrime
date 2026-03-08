from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


MANIFEST_FILENAME = "assets_manifest_v1.json"
SETUP_LOG_FILENAME = "setup.log"
SETUP_REPORT_FILENAME = "setup_report.json"
PREFLIGHT_LOG_FILENAME = "preflight.log"
PREFLIGHT_REPORT_FILENAME = "preflight_report.json"
READY_MARKER_FILENAME = "benchmark_ready.json"
SETUP_OUTPUT_RELROOT = Path("output") / "tools" / "benchmarks" / "community" / "setup_preflight"
SETUP_LATEST_DIRNAME = "latest"

FASTLM_MODULE = "rune_decrypter_prime.scoring.language_model._fastlm"
FASTLM_BUILD_SCRIPT = Path("src/rune_decrypter_prime/scoring/language_model/setup_fastlm.py")
HAMMING_MODULE = "rune_decrypter_prime.scoring.hamming._hamming"
HAMMING_BUILD_SCRIPT = Path("src/rune_decrypter_prime/scoring/hamming/setup_hamming.py")


@dataclass(frozen=True)
class RequiredAsset:
    final_relpath: str
    sha256: str
    size_bytes: int
    parts: Tuple[str, ...]


@dataclass(frozen=True)
class ForwardLink:
    link_relpath: str
    target_relpath: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _setup_output_root(repo_root: Path) -> Path:
    return (repo_root / SETUP_OUTPUT_RELROOT).resolve()


def _new_setup_run_dir(repo_root: Path) -> Path:
    root = _setup_output_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = root / f"{stamp}__setup_preflight"
    if not base.exists():
        base.mkdir(parents=True, exist_ok=True)
        return base
    suffix = 2
    while True:
        candidate = root / f"{stamp}__setup_preflight_{suffix:02d}"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        suffix += 1


def latest_setup_bundle_dir(repo_root: Path) -> Path | None:
    """
    Return the latest setup/preflight artefact directory when available.

    New location:
      output/tools/benchmarks/community/setup_preflight/latest/

    Legacy fallback:
      repo root (setup_report.json etc directly under root)
    """
    repo_root = repo_root.resolve()
    latest_dir = _setup_output_root(repo_root) / SETUP_LATEST_DIRNAME
    required = (
        SETUP_LOG_FILENAME,
        SETUP_REPORT_FILENAME,
        PREFLIGHT_LOG_FILENAME,
        PREFLIGHT_REPORT_FILENAME,
        READY_MARKER_FILENAME,
    )
    if latest_dir.exists() and all((latest_dir / name).exists() for name in required):
        return latest_dir

    legacy_required = (
        repo_root / SETUP_LOG_FILENAME,
        repo_root / SETUP_REPORT_FILENAME,
        repo_root / PREFLIGHT_LOG_FILENAME,
        repo_root / PREFLIGHT_REPORT_FILENAME,
        repo_root / READY_MARKER_FILENAME,
    )
    if all(path.exists() for path in legacy_required):
        return repo_root
    return None


def _refresh_latest_bundle(run_dir: Path) -> None:
    latest_dir = run_dir.parent / SETUP_LATEST_DIRNAME
    latest_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        SETUP_LOG_FILENAME,
        SETUP_REPORT_FILENAME,
        PREFLIGHT_LOG_FILENAME,
        PREFLIGHT_REPORT_FILENAME,
        READY_MARKER_FILENAME,
    ):
        src = run_dir / name
        if src.exists():
            shutil.copy2(src, latest_dir / name)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _joint_output_from_parts(joint_path: Path, *, setup_log) -> Dict[str, Any]:
    if joint_path.name.endswith(".bin.zst"):
        stem_name = joint_path.name[: -len(".bin.zst")]
        stem_path = joint_path.with_name(stem_name)
    else:
        stem_path = joint_path.with_suffix("")
    part_paths = sorted(stem_path.parent.glob(stem_path.name + "_part*.npz"))
    if not part_paths:
        return {
            "ok": False,
            "issues": [f"missing split parts for {joint_path.name}"],
            "detail": {
                "joint_path": str(joint_path),
                "status": "missing_parts",
                "parts": [],
            },
        }

    # Lazy import: keep setup module import-light when split rebuild is not needed.
    import numpy as np
    import zstandard as zstd

    metadata: List[Dict[str, Any]] = []
    lg_size_val: int | None = None
    total_val: int | None = None
    intervals: List[Tuple[int, int]] = []
    issues: List[str] = []

    for part_path in part_paths:
        with np.load(part_path, allow_pickle=False) as zf:
            required = ("keys", "logp", "cnts", "lg_size", "offset", "total")
            missing = [k for k in required if k not in zf]
            if missing:
                issues.append(f"{part_path}: missing arrays {missing}")
                continue
            keys = np.asarray(zf["keys"], dtype=np.uint64)
            logp = np.asarray(zf["logp"], dtype=np.float32)
            cnts = np.asarray(zf["cnts"], dtype=np.uint64)
            lg_size = int(np.asarray(zf["lg_size"]).reshape(-1)[0])
            offset = int(np.asarray(zf["offset"]).reshape(-1)[0])
            total = int(np.asarray(zf["total"]).reshape(-1)[0])

            if keys.shape != logp.shape or keys.shape != cnts.shape:
                issues.append(f"{part_path}: keys/logp/cnts shape mismatch")
                continue
            if keys.ndim != 1:
                issues.append(f"{part_path}: expected rank-1 arrays")
                continue
            if offset < 0 or total <= 0 or offset + int(keys.size) > total:
                issues.append(f"{part_path}: invalid offset/total range")
                continue

            if lg_size_val is None:
                lg_size_val = lg_size
            elif lg_size != lg_size_val:
                issues.append(f"{part_path}: lg_size mismatch {lg_size} != {lg_size_val}")
                continue
            if total_val is None:
                total_val = total
            elif total != total_val:
                issues.append(f"{part_path}: total mismatch {total} != {total_val}")
                continue

            metadata.append(
                {
                    "part_path": part_path,
                    "offset": offset,
                    "count": int(keys.size),
                }
            )
            intervals.append((offset, offset + int(keys.size)))

    if issues:
        return {
            "ok": False,
            "issues": issues,
            "detail": {
                "joint_path": str(joint_path),
                "status": "invalid_parts",
                "parts": [str(p) for p in part_paths],
            },
        }

    if lg_size_val is None or total_val is None:
        return {
            "ok": False,
            "issues": [f"{stem_path}: no usable split parts"],
            "detail": {
                "joint_path": str(joint_path),
                "status": "invalid_parts",
                "parts": [str(p) for p in part_paths],
            },
        }

    if total_val != (1 << lg_size_val):
        return {
            "ok": False,
            "issues": [f"{stem_path}: total={total_val} does not match 2^lg_size={1 << lg_size_val}"],
            "detail": {
                "joint_path": str(joint_path),
                "status": "invalid_parts",
                "parts": [str(p) for p in part_paths],
            },
        }

    intervals.sort()
    cursor = 0
    for start, end in intervals:
        if start != cursor:
            return {
                "ok": False,
                "issues": [f"{stem_path}: split coverage gap/overlap at {cursor}->{start}"],
                "detail": {
                    "joint_path": str(joint_path),
                    "status": "invalid_parts",
                    "parts": [str(p) for p in part_paths],
                },
            }
        cursor = end
    if cursor != total_val:
        return {
            "ok": False,
            "issues": [f"{stem_path}: split coverage incomplete end={cursor} total={total_val}"],
            "detail": {
                "joint_path": str(joint_path),
                "status": "invalid_parts",
                "parts": [str(p) for p in part_paths],
            },
        }

    header_size = struct.calcsize("<4sBHIff")
    keys_bytes = 8 * total_val
    logp_bytes = 4 * total_val
    cnts_bytes = 8 * total_val
    uncompressed_size = header_size + keys_bytes + logp_bytes + cnts_bytes

    joint_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_raw = joint_path.with_suffix(".bin.tmpraw")
    tmp_out = joint_path.with_suffix(".bin.zst.tmp")
    if tmp_raw.exists():
        tmp_raw.unlink()
    if tmp_out.exists():
        tmp_out.unlink()

    try:
        with tmp_raw.open("w+b") as fh:
            fh.write(struct.pack("<4sBHIff", b"WLI0", 1, int(lg_size_val), 0, 0.0, 1.0))
            fh.truncate(uncompressed_size)

            for item in metadata:
                part_path = Path(item["part_path"])
                offset = int(item["offset"])
                with np.load(part_path, allow_pickle=False) as zf:
                    keys = np.asarray(zf["keys"], dtype="<u8", order="C")
                    logp = np.asarray(zf["logp"], dtype="<f4", order="C")
                    cnts = np.asarray(zf["cnts"], dtype="<u8", order="C")
                count = int(keys.size)
                fh.seek(header_size + 8 * offset)
                fh.write(keys.tobytes(order="C"))
                fh.seek(header_size + keys_bytes + 4 * offset)
                fh.write(logp.tobytes(order="C"))
                fh.seek(header_size + keys_bytes + logp_bytes + 8 * offset)
                fh.write(cnts.tobytes(order="C"))

        cctx = zstd.ZstdCompressor(level=9)
        with tmp_raw.open("rb") as src, tmp_out.open("wb") as dst:
            with cctx.stream_writer(dst) as zf:
                shutil.copyfileobj(src, zf, length=1024 * 1024)

        os.replace(tmp_out, joint_path)
    except Exception:
        tmp_raw.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)
        raise
    finally:
        tmp_raw.unlink(missing_ok=True)

    setup_log.write(
        f"[joint-rebuild] built {joint_path} from {len(part_paths)} parts "
        f"(total={total_val}, lg={lg_size_val})\n"
    )
    return {
        "ok": True,
        "issues": [],
        "detail": {
            "joint_path": str(joint_path),
            "status": "rebuilt",
            "parts_count": int(len(part_paths)),
            "total_entries": int(total_val),
            "lg_size": int(lg_size_val),
            "sha256": _sha256_file(joint_path),
        },
    }


def rebuild_split_joint_assets(
    *,
    repo_root: Path,
    assets_root: str,
    setup_log,
) -> Dict[str, Any]:
    """
    Rebuild missing LM joint .bin.zst tables from local split *_part*.npz shards.

    This is a fallback bridge for slimmed repositories where large joint bins
    are omitted but split shards are present.
    """
    issues: List[str] = []
    details: List[Dict[str, Any]] = []
    rebuilt_count = 0
    existing_count = 0

    lm_roots: List[Path] = []
    canonical = (repo_root / assets_root / "language_model" / "lmp").resolve()
    if canonical.exists():
        lm_roots.append(canonical)

    if not lm_roots:
        return {
            "issues": [],
            "details": [],
            "rebuilt_count": 0,
            "existing_count": 0,
        }

    for lm_root in lm_roots:
        idx_path = lm_root / "index.json"
        if not idx_path.exists():
            issues.append(f"missing LM index.json: {idx_path}")
            details.append({"lm_root": str(lm_root), "status": "missing_index"})
            continue
        try:
            idx = json.loads(idx_path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(f"failed to parse LM index: {idx_path}: {exc}")
            details.append({"lm_root": str(lm_root), "status": "invalid_index", "error": str(exc)})
            continue

        models = idx.get("models")
        if not isinstance(models, dict):
            issues.append(f"LM index missing models object: {idx_path}")
            details.append({"lm_root": str(lm_root), "status": "invalid_models"})
            continue

        for model_name, model_info in sorted(models.items()):
            if not isinstance(model_info, dict):
                continue
            pattern = model_info.get("joint_pattern")
            ns = model_info.get("n")
            if not isinstance(pattern, str) or not pattern:
                continue
            if not isinstance(ns, list):
                continue
            for n_val in ns:
                try:
                    n_int = int(n_val)
                except Exception:
                    continue
                for mode in ("ltr", "rtl"):
                    for pos in ("nose", "wise"):
                        rel = (
                            pattern.replace("%%MODE%%", mode)
                            .replace("%%POS%%", pos)
                            .replace("%%N%%", str(n_int))
                        )
                        joint_path = lm_root / rel
                        record: Dict[str, Any] = {
                            "lm_root": str(lm_root),
                            "model": str(model_name),
                            "mode": mode,
                            "se_mode": pos,
                            "n": int(n_int),
                            "joint_path": str(joint_path),
                        }
                        if joint_path.exists():
                            existing_count += 1
                            record["status"] = "already_present"
                            details.append(record)
                            continue
                        out = _joint_output_from_parts(joint_path, setup_log=setup_log)
                        if out["ok"]:
                            rebuilt_count += 1
                            record.update(out["detail"])
                            details.append(record)
                        else:
                            record.update(out["detail"])
                            details.append(record)
                            issues.extend(str(x) for x in out["issues"])

    return {
        "issues": issues,
        "details": details,
        "rebuilt_count": int(rebuilt_count),
        "existing_count": int(existing_count),
    }


def _ensure_import_paths(repo_root: Path) -> None:
    src = repo_root / "src"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, indent=2, sort_keys=True, ensure_ascii=True)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _read_manifest(manifest_path: Path) -> Tuple[Dict[str, Any], List[str]]:
    issues: List[str] = []
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, [f"manifest missing: {manifest_path}"]
    except Exception as exc:
        return {}, [f"manifest parse failure: {exc}"]

    required_assets = raw.get("required_assets")
    if not isinstance(required_assets, list):
        issues.append("manifest key 'required_assets' must be a list")

    assets_root = raw.get("assets_root", "assets")
    if not isinstance(assets_root, str) or not assets_root.strip():
        issues.append("manifest key 'assets_root' must be a non-empty string")

    packed_root = raw.get("packed_root", "assets_packed")
    if not isinstance(packed_root, str) or not packed_root.strip():
        issues.append("manifest key 'packed_root' must be a non-empty string")

    return raw, issues


def _parse_required_assets(manifest: Dict[str, Any]) -> Tuple[List[RequiredAsset], List[str]]:
    issues: List[str] = []
    out: List[RequiredAsset] = []
    items = manifest.get("required_assets")
    if not isinstance(items, list):
        return out, ["manifest key 'required_assets' must be a list"]

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(f"required_assets[{idx}] must be an object")
            continue
        final_relpath = item.get("final_relpath")
        sha256 = item.get("sha256")
        size_bytes = item.get("size_bytes")
        parts = item.get("parts")
        if not isinstance(final_relpath, str) or not final_relpath.strip():
            issues.append(f"required_assets[{idx}].final_relpath must be a non-empty string")
            continue
        if not isinstance(sha256, str) or len(sha256.strip()) < 8:
            issues.append(f"required_assets[{idx}].sha256 must be a non-empty string")
            continue
        try:
            size_val = int(size_bytes)
            if size_val < 0:
                raise ValueError("size must be non-negative")
        except Exception:
            issues.append(f"required_assets[{idx}].size_bytes must be a non-negative integer")
            continue
        if not isinstance(parts, list) or not parts:
            issues.append(f"required_assets[{idx}].parts must be a non-empty list")
            continue
        part_values: List[str] = []
        bad_parts = False
        for p_idx, part in enumerate(parts):
            if not isinstance(part, str) or not part.strip():
                issues.append(f"required_assets[{idx}].parts[{p_idx}] must be a non-empty string")
                bad_parts = True
                continue
            part_values.append(part)
        if bad_parts:
            continue
        out.append(
            RequiredAsset(
                final_relpath=final_relpath,
                sha256=sha256.strip().lower(),
                size_bytes=size_val,
                parts=tuple(part_values),
            )
        )
    return out, issues


def _parse_forward_links(manifest: Dict[str, Any]) -> Tuple[List[ForwardLink], List[str]]:
    issues: List[str] = []
    out: List[ForwardLink] = []
    items = manifest.get("forward_links", [])
    if items in (None, []):
        return out, issues
    if not isinstance(items, list):
        return out, ["manifest key 'forward_links' must be a list"]
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(f"forward_links[{idx}] must be an object")
            continue
        link_relpath = item.get("link_relpath")
        target_relpath = item.get("target_relpath")
        if not isinstance(link_relpath, str) or not link_relpath.strip():
            issues.append(f"forward_links[{idx}].link_relpath must be a non-empty string")
            continue
        if not isinstance(target_relpath, str) or not target_relpath.strip():
            issues.append(f"forward_links[{idx}].target_relpath must be a non-empty string")
            continue
        out.append(ForwardLink(link_relpath=link_relpath, target_relpath=target_relpath))
    return out, issues


def _paths_equivalent(path_a: Path, path_b: Path) -> bool:
    try:
        return path_a.exists() and path_b.exists() and path_a.samefile(path_b)
    except Exception:
        return False


def _create_link(link_path: Path, target_path: Path) -> None:
    if os.name == "nt" and target_path.is_dir():
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"mklink /J failed: {err}")
        return
    os.symlink(target_path, link_path, target_is_directory=target_path.is_dir())


def apply_forward_links(
    *,
    repo_root: Path,
    assets_root: str,
    links: Sequence[ForwardLink],
    setup_log,
) -> Dict[str, Any]:
    issues: List[str] = []
    details: List[Dict[str, Any]] = []
    created = 0
    already_valid = 0

    assets_base = repo_root / assets_root
    assets_base.mkdir(parents=True, exist_ok=True)

    for link in links:
        link_path = assets_base / link.link_relpath
        target_path = (repo_root / link.target_relpath).resolve()
        record: Dict[str, Any] = {
            "link_relpath": link.link_relpath,
            "target_relpath": link.target_relpath,
            "link_path": str(link_path),
            "target_path": str(target_path),
            "status": "pending",
        }
        setup_log.write(f"[link] {link.link_relpath} -> {link.target_relpath}\n")

        if not target_path.exists():
            msg = f"forward link target missing: {target_path}"
            issues.append(msg)
            record["status"] = "missing_target"
            record["error"] = msg
            details.append(record)
            setup_log.write(f"  -> ERROR {msg}\n")
            continue

        link_path.parent.mkdir(parents=True, exist_ok=True)
        if link_path.exists():
            if _paths_equivalent(link_path, target_path):
                already_valid += 1
                record["status"] = "already_linked"
                details.append(record)
                setup_log.write("  -> already linked\n")
                continue
            if link_path.is_dir() and (link_path / "index.json").exists():
                # Transition-safe mode: an existing materialised LM directory is acceptable.
                # Keep it in place to avoid destructive mutations on developer machines.
                already_valid += 1
                record["status"] = "already_materialized"
                details.append(record)
                setup_log.write("  -> existing materialized directory accepted\n")
                continue
            try:
                if link_path.is_dir():
                    shutil.rmtree(link_path)
                else:
                    link_path.unlink(missing_ok=True)
                setup_log.write("  -> removed stale existing path before link creation\n")
            except Exception as exc:
                msg = (
                    f"forward link path already exists and points elsewhere: {link_path} "
                    f"(target={target_path}); cleanup failed: {exc}"
                )
                issues.append(msg)
                record["status"] = "conflict_existing_path"
                record["error"] = msg
                details.append(record)
                setup_log.write(f"  -> ERROR {msg}\n")
                continue

        try:
            _create_link(link_path, target_path)
            if not _paths_equivalent(link_path, target_path):
                raise RuntimeError("created link does not resolve to target")
            created += 1
            record["status"] = "linked"
            details.append(record)
            setup_log.write("  -> linked\n")
        except Exception as exc:
            msg = f"failed to create forward link {link_path} -> {target_path}: {exc}"
            issues.append(msg)
            record["status"] = "error"
            record["error"] = str(exc)
            details.append(record)
            setup_log.write(f"  -> ERROR {msg}\n")

    return {
        "issues": issues,
        "details": details,
        "created_links_count": int(created),
        "already_linked_count": int(already_valid),
    }


def recombine_required_assets(
    *,
    repo_root: Path,
    assets_root: str,
    packed_root: str,
    required_assets: Sequence[RequiredAsset],
    setup_log,
) -> Dict[str, Any]:
    details: List[Dict[str, Any]] = []
    issues: List[str] = []
    recombined = 0
    verified = 0
    skipped_already_ok = 0

    assets_base = repo_root / assets_root
    packed_base = repo_root / packed_root
    assets_base.mkdir(parents=True, exist_ok=True)

    for asset in required_assets:
        final_path = assets_base / asset.final_relpath
        final_path.parent.mkdir(parents=True, exist_ok=True)
        record: Dict[str, Any] = {
            "final_relpath": asset.final_relpath,
            "final_path": str(final_path),
            "status": "pending",
            "size_bytes_expected": int(asset.size_bytes),
            "sha256_expected": asset.sha256,
            "parts": list(asset.parts),
        }
        setup_log.write(f"[asset] {asset.final_relpath}\n")

        # Fast idempotence path: existing and already valid.
        if final_path.exists():
            actual_size = final_path.stat().st_size
            actual_sha = _sha256_file(final_path)
            if actual_size == asset.size_bytes and actual_sha.lower() == asset.sha256:
                skipped_already_ok += 1
                verified += 1
                record["status"] = "already_valid"
                record["size_bytes_actual"] = int(actual_size)
                record["sha256_actual"] = actual_sha.lower()
                details.append(record)
                setup_log.write("  -> already valid\n")
                continue

        missing_parts = []
        for rel in asset.parts:
            part_path = packed_base / rel
            if not part_path.exists():
                missing_parts.append(rel)
        if missing_parts:
            msg = f"missing parts for {asset.final_relpath}: {missing_parts}"
            issues.append(msg)
            record["status"] = "missing_parts"
            record["missing_parts"] = missing_parts
            details.append(record)
            setup_log.write(f"  -> ERROR {msg}\n")
            continue

        fd, tmp_name = tempfile.mkstemp(prefix=final_path.name + ".", suffix=".tmp", dir=str(final_path.parent))
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as out_f:
                for rel in asset.parts:
                    part_path = packed_base / rel
                    with part_path.open("rb") as in_f:
                        for chunk in iter(lambda: in_f.read(1024 * 1024), b""):
                            out_f.write(chunk)

            actual_size = tmp_path.stat().st_size
            actual_sha = _sha256_file(tmp_path).lower()
            record["size_bytes_actual"] = int(actual_size)
            record["sha256_actual"] = actual_sha
            if actual_size != asset.size_bytes:
                msg = (
                    f"size mismatch for {asset.final_relpath}: "
                    f"expected={asset.size_bytes} actual={actual_size}"
                )
                issues.append(msg)
                record["status"] = "size_mismatch"
                setup_log.write(f"  -> ERROR {msg}\n")
                details.append(record)
                tmp_path.unlink(missing_ok=True)
                continue
            if actual_sha != asset.sha256:
                msg = (
                    f"sha256 mismatch for {asset.final_relpath}: "
                    f"expected={asset.sha256} actual={actual_sha}"
                )
                issues.append(msg)
                record["status"] = "sha_mismatch"
                setup_log.write(f"  -> ERROR {msg}\n")
                details.append(record)
                tmp_path.unlink(missing_ok=True)
                continue

            os.replace(tmp_path, final_path)
            recombined += 1
            verified += 1
            record["status"] = "recombined"
            details.append(record)
            setup_log.write("  -> recombined + verified\n")
        except Exception as exc:
            msg = f"recombine failure for {asset.final_relpath}: {exc}"
            issues.append(msg)
            record["status"] = "error"
            record["error"] = str(exc)
            details.append(record)
            setup_log.write(f"  -> ERROR {msg}\n")
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

    return {
        "issues": issues,
        "details": details,
        "recombined_assets_count": int(recombined),
        "verified_assets_count": int(verified),
        "already_valid_assets_count": int(skipped_already_ok),
    }


def _import_fastlm(repo_root: Path) -> Tuple[bool, str]:
    _ensure_import_paths(repo_root)
    try:
        importlib.import_module(FASTLM_MODULE)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _import_hamming(repo_root: Path) -> Tuple[bool, str]:
    _ensure_import_paths(repo_root)
    try:
        importlib.import_module(HAMMING_MODULE)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def ensure_fastlm(repo_root: Path, *, allow_build: bool, setup_log) -> Dict[str, Any]:
    present, err = _import_fastlm(repo_root)
    build_attempted = False
    build_succeeded = False
    issues: List[str] = []

    if present:
        setup_log.write("[fastlm] import ok\n")
        return {
            "fastlm_present": True,
            "build_attempted": False,
            "build_succeeded": False,
            "issues": [],
        }

    setup_log.write(f"[fastlm] import failed: {err}\n")
    if not allow_build:
        issues.append("fastlm unavailable and build disabled")
        return {
            "fastlm_present": False,
            "build_attempted": False,
            "build_succeeded": False,
            "issues": issues,
        }

    build_script = repo_root / FASTLM_BUILD_SCRIPT
    if not build_script.exists():
        issues.append(f"fastlm build script missing: {build_script}")
        return {
            "fastlm_present": False,
            "build_attempted": False,
            "build_succeeded": False,
            "issues": issues,
        }

    build_attempted = True
    setup_log.write(f"[fastlm] building using {build_script}\n")
    try:
        result = subprocess.run(
            [sys.executable, str(build_script)],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            setup_log.write(result.stdout)
            if not result.stdout.endswith("\n"):
                setup_log.write("\n")
        if result.stderr:
            setup_log.write(result.stderr)
            if not result.stderr.endswith("\n"):
                setup_log.write("\n")
        if result.returncode != 0:
            issues.append(f"fastlm build failed with exit code {result.returncode}")
    except Exception as exc:
        issues.append(f"fastlm build invocation failed: {exc}")

    present_after, err_after = _import_fastlm(repo_root)
    if present_after:
        build_succeeded = True
        setup_log.write("[fastlm] import ok after build\n")
    else:
        issues.append(f"fastlm still unavailable after build: {err_after}")
        setup_log.write(f"[fastlm] still unavailable: {err_after}\n")

    return {
        "fastlm_present": bool(present_after),
        "build_attempted": bool(build_attempted),
        "build_succeeded": bool(build_succeeded),
        "issues": issues,
    }


def ensure_hamming(repo_root: Path, *, allow_build: bool, setup_log) -> Dict[str, Any]:
    present, err = _import_hamming(repo_root)
    build_attempted = False
    build_succeeded = False
    issues: List[str] = []

    if present:
        setup_log.write("[hamming] import ok\n")
        return {
            "hamming_present": True,
            "build_attempted": False,
            "build_succeeded": False,
            "issues": [],
        }

    setup_log.write(f"[hamming] import failed: {err}\n")
    if not allow_build:
        issues.append("hamming unavailable and build disabled")
        return {
            "hamming_present": False,
            "build_attempted": False,
            "build_succeeded": False,
            "issues": issues,
        }

    build_script = repo_root / HAMMING_BUILD_SCRIPT
    if not build_script.exists():
        issues.append(f"hamming build script missing: {build_script}")
        return {
            "hamming_present": False,
            "build_attempted": False,
            "build_succeeded": False,
            "issues": issues,
        }

    build_attempted = True
    setup_log.write(f"[hamming] building using {build_script}\n")
    try:
        result = subprocess.run(
            [sys.executable, str(build_script)],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            setup_log.write(result.stdout)
            if not result.stdout.endswith("\n"):
                setup_log.write("\n")
        if result.stderr:
            setup_log.write(result.stderr)
            if not result.stderr.endswith("\n"):
                setup_log.write("\n")
        if result.returncode != 0:
            issues.append(f"hamming build failed with exit code {result.returncode}")
    except Exception as exc:
        issues.append(f"hamming build invocation failed: {exc}")

    present_after, err_after = _import_hamming(repo_root)
    if present_after:
        build_succeeded = True
        setup_log.write("[hamming] import ok after build\n")
    else:
        issues.append(f"hamming still unavailable after build: {err_after}")
        setup_log.write(f"[hamming] still unavailable: {err_after}\n")

    return {
        "hamming_present": bool(present_after),
        "build_attempted": bool(build_attempted),
        "build_succeeded": bool(build_succeeded),
        "issues": issues,
    }


def _run_tiny_scoring_probe(repo_root: Path, lm_root: Path) -> Tuple[bool, Dict[str, Any], str]:
    _ensure_import_paths(repo_root)
    try:
        import numpy as np

        from rune_decrypter_prime.core.config.cipher import CipherConfig
        from rune_decrypter_prime.core.config.scoring import ScoringConfig
        from rune_decrypter_prime.core.engine.builders import build_scorer
        from rune_decrypter_prime.core.types import Device, Direction, ObjectiveFamily, ObjectiveSpec, ScorerImpl, SeMode, Stat
        from rune_decrypter_prime.utils.runeglish import Runeglish
    except Exception as exc:
        return False, {}, f"import failure during scoring probe: {exc}"

    try:
        text = "EITHER THE WELL WAS VERY DEEP OR SHE FELL VERY SLOWLY"
        pt_idx, wli, _ = Runeglish.encode_english_to_runes(text, direction=Direction.LTR.value)
        pt_u8 = np.asarray(pt_idx, dtype=np.uint8)
        wli_list = [[int(a), int(b)] for a, b in wli]
        if len(wli_list) != int(pt_u8.size):
            return False, {}, "wli length mismatch in probe"

        cipher_cfg = CipherConfig(
            name="periodic_columnar",
            ciphertext=[],
            wli_data=[],
            key_length=30,
            period=1,
            columns=1,
            alphabet_size=29,
            order="col_then_sub",
            encoding_dir=Direction.LTR,
            device=Device.CPU,
        )
        scoring_cfg = ScoringConfig(
            model_root=lm_root,
            objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
            se_mode=SeMode.NOSE,
            encoding_dir=Direction.LTR,
            include_char=True,
            use_word_breaks=True,
            char_weights={3: 0.2, 4: 0.8},
            wli_weights={3: 0.2, 4: 0.8},
            impl=ScorerImpl.NUMPY,
        )
        scorer = build_scorer(cipher_cfg, scoring_cfg)
        score, raw = scorer.score_with_raw(pt_u8, wli_list)
        if not (np.isfinite(float(score)) and np.isfinite(float(raw))):
            return False, {}, f"non-finite scoring outputs score={score} raw={raw}"
        details = {
            "score": float(score),
            "raw": float(raw),
            "tokens": int(pt_u8.size),
            "words": int(max((int(pair[1]) for pair in wli_list), default=0)),
            "lm_root": str(lm_root),
        }
        return True, details, ""
    except Exception as exc:
        return False, {}, f"scoring probe failed: {exc}"


def run_preflight(
    *,
    repo_root: Path,
    assets_root: str,
    required_assets: Sequence[RequiredAsset],
    fastlm_present: bool,
    hamming_present: bool,
    preflight_log,
) -> Dict[str, Any]:
    issues: List[str] = []
    checks: List[Dict[str, Any]] = []

    # Imports check.
    _ensure_import_paths(repo_root)
    try:
        importlib.import_module("rune_decrypter_prime")
        importlib.import_module("rune_decrypter_prime.core.engine.builders")
        importlib.import_module("tools.benchmarks.periodic_sub_trans.col_then_sub.runner")
        checks.append({"name": "required_imports", "passed": True})
        preflight_log.write("[check] required_imports ok\n")
    except Exception as exc:
        msg = f"required imports failed: {exc}"
        issues.append(msg)
        checks.append({"name": "required_imports", "passed": False, "detail": msg})
        preflight_log.write(f"[check] required_imports ERROR {msg}\n")

    # Assets check against manifest contract.
    assets_base = repo_root / assets_root
    missing_assets = []
    for asset in required_assets:
        p = assets_base / asset.final_relpath
        if not p.exists():
            missing_assets.append(asset.final_relpath)
    if missing_assets:
        msg = f"required assets missing under {assets_base}: {missing_assets[:8]}"
        issues.append(msg)
        checks.append({"name": "required_assets_present", "passed": False, "detail": msg})
        preflight_log.write(f"[check] required_assets_present ERROR {msg}\n")
    else:
        checks.append({"name": "required_assets_present", "passed": True})
        preflight_log.write("[check] required_assets_present ok\n")

    # fastlm check.
    if fastlm_present:
        checks.append({"name": "fastlm_present", "passed": True})
        preflight_log.write("[check] fastlm_present ok\n")
    else:
        msg = "fastlm module unavailable"
        issues.append(msg)
        checks.append({"name": "fastlm_present", "passed": False, "detail": msg})
        preflight_log.write(f"[check] fastlm_present ERROR {msg}\n")

    if hamming_present:
        checks.append({"name": "hamming_present", "passed": True})
        preflight_log.write("[check] hamming_present ok\n")
    else:
        msg = "hamming module unavailable"
        issues.append(msg)
        checks.append({"name": "hamming_present", "passed": False, "detail": msg})
        preflight_log.write(f"[check] hamming_present ERROR {msg}\n")

    # Tiny scoring probe (char+wli 3/4 path).
    if required_assets:
        lm_root = assets_base / "language_model" / "lmp"
    else:
        # Defensive fallback for malformed manifests: still run probe with assets root.
        lm_root = assets_base / "language_model" / "lmp"

    probe_ok = False
    probe_details: Dict[str, Any] = {}
    probe_error = ""
    if not issues:
        probe_ok, probe_details, probe_error = _run_tiny_scoring_probe(repo_root, lm_root)
        if probe_ok:
            checks.append({"name": "tiny_cpu_scoring_probe", "passed": True, "detail": probe_details})
            preflight_log.write("[check] tiny_cpu_scoring_probe ok\n")
        else:
            msg = probe_error or "tiny scoring probe failed"
            issues.append(msg)
            checks.append({"name": "tiny_cpu_scoring_probe", "passed": False, "detail": msg})
            preflight_log.write(f"[check] tiny_cpu_scoring_probe ERROR {msg}\n")

    success = len(issues) == 0
    return {
        "timestamp_utc": _utc_now(),
        "success": bool(success),
        "device": "cpu",
        "scoring_backend": "numpy",
        "fastlm_present": bool(fastlm_present),
        "hamming_present": bool(hamming_present),
        "checks": checks,
        "issues": issues,
        "probe_details": probe_details if probe_ok else {},
    }


def run_setup_and_preflight(repo_root: Path, *, skip_fastlm_build: bool) -> int:
    repo_root = repo_root.resolve()
    run_dir = _new_setup_run_dir(repo_root)
    setup_log_path = run_dir / SETUP_LOG_FILENAME
    preflight_log_path = run_dir / PREFLIGHT_LOG_FILENAME
    setup_report_path = run_dir / SETUP_REPORT_FILENAME
    preflight_report_path = run_dir / PREFLIGHT_REPORT_FILENAME
    ready_marker_path = run_dir / READY_MARKER_FILENAME
    manifest_path = repo_root / MANIFEST_FILENAME

    ready_marker_path.unlink(missing_ok=True)

    with setup_log_path.open("w", encoding="utf-8", newline="\n") as setup_log:
        setup_log.write(f"[setup] start { _utc_now() }\n")
        setup_log.write(f"[setup] repo_root={repo_root}\n")
        setup_log.write(f"[setup] run_dir={run_dir}\n")
        setup_log.write(f"[setup] manifest={manifest_path}\n")

        manifest, manifest_issues = _read_manifest(manifest_path)
        assets_root = str(manifest.get("assets_root", "assets"))
        packed_root = str(manifest.get("packed_root", "assets_packed"))
        required_assets, parse_issues = _parse_required_assets(manifest)
        forward_links, forward_link_issues = _parse_forward_links(manifest)
        all_issues: List[str] = []
        all_issues.extend(manifest_issues)
        all_issues.extend(parse_issues)
        all_issues.extend(forward_link_issues)

        recombine_report = {
            "issues": list(all_issues),
            "details": [],
            "recombined_assets_count": 0,
            "verified_assets_count": 0,
            "already_valid_assets_count": 0,
        }
        if not all_issues:
            recombine_report = recombine_required_assets(
                repo_root=repo_root,
                assets_root=assets_root,
                packed_root=packed_root,
                required_assets=required_assets,
                setup_log=setup_log,
            )
            all_issues.extend(recombine_report["issues"])
        else:
            setup_log.write("[setup] manifest validation failed; skipping recombine\n")

        links_report = {
            "issues": [],
            "details": [],
            "created_links_count": 0,
            "already_linked_count": 0,
        }
        if not all_issues and forward_links:
            links_report = apply_forward_links(
                repo_root=repo_root,
                assets_root=assets_root,
                links=forward_links,
                setup_log=setup_log,
            )
            all_issues.extend(links_report["issues"])

        split_rebuild_report = rebuild_split_joint_assets(
            repo_root=repo_root,
            assets_root=assets_root,
            setup_log=setup_log,
        )
        all_issues.extend(split_rebuild_report["issues"])

        fastlm_report = ensure_fastlm(
            repo_root,
            allow_build=not bool(skip_fastlm_build),
            setup_log=setup_log,
        )
        all_issues.extend(fastlm_report["issues"])
        hamming_report = ensure_hamming(
            repo_root,
            allow_build=True,
            setup_log=setup_log,
        )
        all_issues.extend(hamming_report["issues"])

        setup_success = len(all_issues) == 0
        setup_report = {
            "timestamp_utc": _utc_now(),
            "success": bool(setup_success),
            "run_dir": str(run_dir.relative_to(repo_root).as_posix()),
            "manifest_path": MANIFEST_FILENAME,
            "assets_root": assets_root,
            "packed_root": packed_root,
            "required_assets_count": int(len(required_assets)),
            "forward_links_count": int(len(forward_links)),
            "recombined_assets_count": int(recombine_report["recombined_assets_count"]),
            "verified_assets_count": int(recombine_report["verified_assets_count"]),
            "already_valid_assets_count": int(recombine_report["already_valid_assets_count"]),
            "asset_details": recombine_report["details"],
            "joint_assets_rebuilt_count": int(split_rebuild_report["rebuilt_count"]),
            "joint_assets_existing_count": int(split_rebuild_report["existing_count"]),
            "joint_asset_details": split_rebuild_report["details"],
            "created_links_count": int(links_report["created_links_count"]),
            "already_linked_count": int(links_report["already_linked_count"]),
            "link_details": links_report["details"],
            "fastlm_present": bool(fastlm_report["fastlm_present"]),
            "fastlm_build_attempted": bool(fastlm_report["build_attempted"]),
            "fastlm_build_succeeded": bool(fastlm_report["build_succeeded"]),
            "hamming_present": bool(hamming_report["hamming_present"]),
            "hamming_build_attempted": bool(hamming_report["build_attempted"]),
            "hamming_build_succeeded": bool(hamming_report["build_succeeded"]),
            "issues": all_issues,
        }
        _atomic_write_json(setup_report_path, setup_report)
        setup_log.write(f"[setup] success={setup_success}\n")
        setup_log.write(f"[setup] end { _utc_now() }\n")

    with preflight_log_path.open("w", encoding="utf-8", newline="\n") as preflight_log:
        preflight_log.write(f"[preflight] start { _utc_now() }\n")
        preflight_log.write(f"[preflight] repo_root={repo_root}\n")
        preflight_log.write(f"[preflight] run_dir={run_dir}\n")
        preflight_report = run_preflight(
            repo_root=repo_root,
            assets_root=assets_root,
            required_assets=required_assets,
            fastlm_present=bool(fastlm_report["fastlm_present"]),
            hamming_present=bool(hamming_report["hamming_present"]),
            preflight_log=preflight_log,
        )
        preflight_report["run_dir"] = str(run_dir.relative_to(repo_root).as_posix())
        _atomic_write_json(preflight_report_path, preflight_report)
        preflight_log.write(f"[preflight] success={preflight_report['success']}\n")
        preflight_log.write(f"[preflight] end { _utc_now() }\n")

    if setup_report["success"] and preflight_report["success"]:
        ready_payload = {
            "ready": True,
            "timestamp_utc": _utc_now(),
            "setup_report": setup_report_path.name,
            "preflight_report": preflight_report_path.name,
            "manifest": manifest_path.name,
            "run_dir": str(run_dir.relative_to(repo_root).as_posix()),
        }
        _atomic_write_json(ready_marker_path, ready_payload)
        _refresh_latest_bundle(run_dir)
        return 0

    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="RDP community setup + preflight (v1.1)")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root (defaults to current working directory).",
    )
    parser.add_argument(
        "--skip-fastlm-build",
        action="store_true",
        help="Do not attempt to build _fastlm; only verify import.",
    )
    args = parser.parse_args()
    return run_setup_and_preflight(args.repo_root, skip_fastlm_build=bool(args.skip_fastlm_build))


if __name__ == "__main__":
    raise SystemExit(main())
