from __future__ import annotations

import importlib.util
import json
import uuid
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
MIN_PYTHON = (3, 11)
VERBOSE = os.environ.get("RDP_INSTALL_VERBOSE", "").strip().lower() in {"1", "true", "yes", "on"}
LOG_DIR: Path | None = None
INSTALL_MODE_LABEL = "Full V1 install"
ASSET_PROFILE_MANIFEST = ROOT / "asset_profiles_v1.json"
DEFAULT_ASSET_PROFILE = "full_v1"

REQUIRED_ASSET_SENTINELS = [
    ROOT / "assets" / "hamming_raw_1g" / "raw1grams_01.csv",
    ROOT / "assets" / "hamming_dictionary_policies_phaseA_v0_14" / "strict" / "hamming_raw_1g" / "raw1grams_14.csv",
    ROOT / "assets" / "hamming_dictionary_policies_phaseA_v0_14" / "normal" / "hamming_raw_1g" / "raw1grams_14.csv",
]
FULL_ASSET_MANIFEST = ROOT / "assets_manifest_v1.json"
LARGE_ASSET_DOWNLOAD_DIR = ROOT / "downloads"
LARGE_ASSET_ROOT = ROOT / "assets"

REQUIRED_NATIVE_MODULES = [
    "rdp.scoring.language_model._fastlm",
]

NATIVE_SOURCE_CHECKS = [
    (
        "rdp.scoring.hamming._hamming",
        [
            ROOT / "src" / "rdp" / "scoring" / "hamming" / "bindings.cpp",
            ROOT / "src" / "rdp" / "scoring" / "hamming" / "Hamming.cpp",
            ROOT / "src" / "rdp" / "scoring" / "hamming" / "Flat2DArray.cpp",
        ],
    ),
    (
        "rdp.scoring.span_hamming._span_hamming_fast",
        [ROOT / "src" / "rdp" / "scoring" / "span_hamming" / "fast_bindings.cpp"],
    ),
]

SMOKE_TESTS = [
    "tests/contracts",
    "tests/api/test_scheduled_stream_lookup_wrappers.py",
    "tests/ciphers/test_scheduled_stream_lookup_cipher.py",
    "tests/tutorials/test_scheduled_stream_lookup_pipeline_smoke.py",
]


class InstallFailure(RuntimeError):
    pass


def _safe_name(label: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in label).strip("_") or "step"


def _run(label: str, args: list[str]) -> None:
    if LOG_DIR is None:
        raise RuntimeError("Installer output has not been initialized")
    log_path = LOG_DIR / (_safe_name(label) + ".log")
    print(f"[RUN ] {label}", flush=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("command: " + json.dumps(["python", *args[1:]]) + "\n")
        log.flush()
        process = subprocess.Popen(
            args, cwd=ROOT, text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env={**os.environ, "RDP_OUTPUT_ROOT": str(LOG_DIR / "artifacts"),
                 "PYTHONDONTWRITEBYTECODE": "1"}, start_new_session=os.name != "nt")
        tail = []
        try:
            for line in process.stdout:
                log.write(line)
                log.flush()
                tail = (tail + [line])[-35:]
                if VERBOSE:
                    print(line, end="", flush=True)
            code = process.wait()
            log.write(f"\nreturncode: {code}\n")
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    import signal
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            process.stdout.close()
    if code:
        print("".join(tail), end="")
        print(f"[FAIL] {label}; log={log_path.name}")
        raise InstallFailure(label)
    print(f"[PASS] {label}", flush=True)


def _verify_python() -> None:
    print("[RUN ] Check Python version")
    version = sys.version_info
    if (version.major, version.minor) < MIN_PYTHON:
        raise InstallFailure(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required; "
            f"found {version.major}.{version.minor}.{version.micro}"
        )
    print(f"[PASS] Python {version.major}.{version.minor}.{version.micro}")


def _install_package() -> None:
    try:
        _run("Install package and build native extensions", [PYTHON, "-m", "pip", "install", "-e", ".[test]"])
    except InstallFailure:
        print()
        print("RDP did not upgrade pip automatically.")
        print("If this failed because pip/setuptools/wheel are too old, run this yourself and retry:")
        print("  python -m pip install --upgrade pip setuptools wheel")
        raise


def _check_module_import(module_name: str, *, label: str | None = None) -> None:
    """Check imports in a fresh Python interpreter after editable install.

    The installer runs inside the Python process that existed before pip created
    the editable-install .pth file. A fresh interpreter is required to prove that
    the package is genuinely importable from the installed environment.
    """
    script = (
        "import importlib; "
        f"importlib.import_module({module_name!r}); "
        f"print('import {module_name} passed')"
    )
    _run(label or f"Import {module_name}", [PYTHON, "-c", script])


def _check_imports() -> None:
    _check_module_import("rdp", label="Check Python package import")

    print("[RUN ] Check required native extension imports")
    for module_name in REQUIRED_NATIVE_MODULES:
        _check_module_import(module_name, label=f"Import required native extension {module_name}")
    print("[PASS] required native extensions import")

    expected_optional = [
        module_name
        for module_name, sources in NATIVE_SOURCE_CHECKS
        if all(path.is_file() for path in sources)
    ]
    if expected_optional:
        print("[RUN ] Check native extensions whose sources are present")
        for module_name in expected_optional:
            _check_module_import(module_name, label=f"Import source-present native extension {module_name}")
        print("[PASS] source-present native extensions import")


def _check_small_asset_sentinels() -> None:
    print("[RUN ] Check required V1 asset sentinels")
    missing = [path for path in REQUIRED_ASSET_SENTINELS if not path.is_file()]
    if missing:
        print("[FAIL] Missing required V1 asset sentinels:")
        for path in missing:
            print(" -", path.relative_to(ROOT).as_posix())
        raise InstallFailure("required V1 assets are missing")
    print("[PASS] required V1 asset sentinels present")


def _install_or_verify_profile_assets(profile) -> None:
    from tools.assets.release_asset_installer import (
        AssetInstallError,
        install_release_asset_set,
        load_manifest,
        verify_installed_assets,
    )

    verification_manifest = ROOT / profile.verification_manifest
    print(f"[RUN ] Install or verify asset profile {profile.name}")
    print(f"      Verification manifest: {verification_manifest.name}")
    try:
        if profile.download_release_assets:
            if verification_manifest != FULL_ASSET_MANIFEST:
                raise InstallFailure(
                    f"download profile {profile.name!r} must use {FULL_ASSET_MANIFEST.name}"
                )
            install_release_asset_set(
                verification_manifest,
                profile.release_asset_set,
                LARGE_ASSET_DOWNLOAD_DIR,
                LARGE_ASSET_ROOT,
            )
        else:
            manifest = load_manifest(verification_manifest)
            verify_installed_assets(
                manifest,
                profile.release_asset_set,
                LARGE_ASSET_ROOT,
            )
    except AssetInstallError as exc:
        if profile.download_release_assets:
            print("[FAIL] Required V1 full language assets are not installed.")
            print("Manual fallback:")
            print("  Download rdp-v1-lm-large-part*.zip from the V1 GitHub Release.")
            print("  Place them under downloads/.")
            print("  Run python install.py again.")
        raise InstallFailure(
            f"asset profile {profile.name!r} is missing or corrupt: {exc}"
        ) from exc
    print(f"[PASS] asset profile {profile.name} installed or verified")


def _run_smoke_tests() -> None:
    _run("Run compact V1 smoke tests", [PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--basetemp={LOG_DIR / 'pytest_tmp'}", *SMOKE_TESTS])


def run_install(*, asset_profile_name: str, mode_label: str) -> int:
    global LOG_DIR
    # Load the dependency-light canonical owner without importing an uninstalled RDP.
    spec = importlib.util.spec_from_file_location(
        "rdp_install_output_paths", ROOT / "src/rdp/core/config/output_paths.py")
    routing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(routing)
    LOG_DIR = routing.resolve_output_root() / "install" / uuid.uuid4().hex
    LOG_DIR.mkdir(parents=True)
    print("Rune Decrypter Prime V1 installer")
    print(f"Mode: {mode_label}")
    print(f"Repo root: {ROOT}")
    print("Successful command output is hidden. Set RDP_INSTALL_VERBOSE=1 to show it.")
    print(f"Install evidence: {routing.path_from(LOG_DIR, ROOT)}")
    print("pip is not upgraded automatically.")
    from tools.assets.asset_profiles import select_asset_profile

    profile = select_asset_profile(ASSET_PROFILE_MANIFEST, asset_profile_name)
    print(f"Asset profile: {profile.name}")
    print(f"Language-model orders: {', '.join(str(order) for order in profile.language_model_orders)}")
    if profile.download_release_assets:
        print("This profile downloads or verifies the complete supported V1 language assets.")
    else:
        print("This profile verifies only the source-bundled CI-light language assets.")
    print()
    try:
        _verify_python()
        _install_package()
        from tools.torch_runtime import provision_torch
        gpu_report = provision_torch(_run)
        (LOG_DIR / "gpu.json").write_text(json.dumps(gpu_report, indent=2), encoding="utf-8")
        _check_imports()
        _check_small_asset_sentinels()
        _install_or_verify_profile_assets(profile)
        _run_smoke_tests()
        print(f"[PASS] RDP V1 install smoke complete ({mode_label})")
        return 0
    except (InstallFailure, RuntimeError) as exc:
        (LOG_DIR / "failure.json").write_text(
            json.dumps({"status": "failed", "error": str(exc)}, indent=2), encoding="utf-8")
        print(f"[INSTALL FAILED] {exc}")
        return 1
    except KeyboardInterrupt:
        print("\n[INSTALL FAILED] interrupted")
        return 130


def main() -> int:
    return run_install(asset_profile_name=DEFAULT_ASSET_PROFILE, mode_label=INSTALL_MODE_LABEL)


if __name__ == "__main__":
    raise SystemExit(main())
