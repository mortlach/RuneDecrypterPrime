from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
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

FASTLM_MODULE = "rune_decrypter_prime.scoring.language_model._fastlm"
FASTLM_BUILD_SCRIPT = Path("src/rune_decrypter_prime/scoring/language_model/setup_fastlm.py")


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


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
    preflight_log,
) -> Dict[str, Any]:
    issues: List[str] = []
    checks: List[Dict[str, Any]] = []

    # Imports check.
    _ensure_import_paths(repo_root)
    try:
        importlib.import_module("rune_decrypter_prime")
        importlib.import_module("rune_decrypter_prime.core.engine.builders")
        importlib.import_module("tools.benchmarks.bench_solve_periodic_columnar_pipeline")
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
        "checks": checks,
        "issues": issues,
        "probe_details": probe_details if probe_ok else {},
    }


def run_setup_and_preflight(repo_root: Path, *, skip_fastlm_build: bool) -> int:
    repo_root = repo_root.resolve()
    setup_log_path = repo_root / SETUP_LOG_FILENAME
    preflight_log_path = repo_root / PREFLIGHT_LOG_FILENAME
    setup_report_path = repo_root / SETUP_REPORT_FILENAME
    preflight_report_path = repo_root / PREFLIGHT_REPORT_FILENAME
    ready_marker_path = repo_root / READY_MARKER_FILENAME
    manifest_path = repo_root / MANIFEST_FILENAME

    ready_marker_path.unlink(missing_ok=True)

    with setup_log_path.open("w", encoding="utf-8", newline="\n") as setup_log:
        setup_log.write(f"[setup] start { _utc_now() }\n")
        setup_log.write(f"[setup] repo_root={repo_root}\n")
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

        fastlm_report = ensure_fastlm(
            repo_root,
            allow_build=not bool(skip_fastlm_build),
            setup_log=setup_log,
        )
        all_issues.extend(fastlm_report["issues"])

        setup_success = len(all_issues) == 0
        setup_report = {
            "timestamp_utc": _utc_now(),
            "success": bool(setup_success),
            "manifest_path": str(manifest_path),
            "assets_root": assets_root,
            "packed_root": packed_root,
            "required_assets_count": int(len(required_assets)),
            "forward_links_count": int(len(forward_links)),
            "recombined_assets_count": int(recombine_report["recombined_assets_count"]),
            "verified_assets_count": int(recombine_report["verified_assets_count"]),
            "already_valid_assets_count": int(recombine_report["already_valid_assets_count"]),
            "asset_details": recombine_report["details"],
            "created_links_count": int(links_report["created_links_count"]),
            "already_linked_count": int(links_report["already_linked_count"]),
            "link_details": links_report["details"],
            "fastlm_present": bool(fastlm_report["fastlm_present"]),
            "fastlm_build_attempted": bool(fastlm_report["build_attempted"]),
            "fastlm_build_succeeded": bool(fastlm_report["build_succeeded"]),
            "issues": all_issues,
        }
        _atomic_write_json(setup_report_path, setup_report)
        setup_log.write(f"[setup] success={setup_success}\n")
        setup_log.write(f"[setup] end { _utc_now() }\n")

    with preflight_log_path.open("w", encoding="utf-8", newline="\n") as preflight_log:
        preflight_log.write(f"[preflight] start { _utc_now() }\n")
        preflight_log.write(f"[preflight] repo_root={repo_root}\n")
        preflight_report = run_preflight(
            repo_root=repo_root,
            assets_root=assets_root,
            required_assets=required_assets,
            fastlm_present=bool(fastlm_report["fastlm_present"]),
            preflight_log=preflight_log,
        )
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
        }
        _atomic_write_json(ready_marker_path, ready_payload)
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
