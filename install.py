from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
MIN_PYTHON = (3, 11)
VERBOSE = os.environ.get("RDP_INSTALL_VERBOSE", "").strip().lower() in {"1", "true", "yes", "on"}
LOG_DIR = ROOT / "output" / "install_logs"
INSTALL_MODE_LABEL = "Full V1 install"

REQUIRED_ASSET_SENTINELS = [
    ROOT / "assets" / "hamming_raw_1g" / "raw1grams_01.csv",
    ROOT / "assets" / "hamming_dictionary_policies_phaseA_v0_14" / "strict" / "hamming_raw_1g" / "raw1grams_14.csv",
    ROOT / "assets" / "hamming_dictionary_policies_phaseA_v0_14" / "normal" / "hamming_raw_1g" / "raw1grams_14.csv",
]
LARGE_ASSET_MANIFEST = ROOT / "assets_manifest_v1.json"
LARGE_ASSET_SET = "v1_lm_runtime_full"
LARGE_ASSET_DOWNLOAD_DIR = ROOT / "downloads"
LARGE_ASSET_ROOT = ROOT / "assets"

REQUIRED_NATIVE_MODULES = [
    "rune_decrypter_prime.scoring.language_model._fastlm",
]

NATIVE_SOURCE_CHECKS = [
    (
        "rune_decrypter_prime.scoring.hamming._hamming",
        [
            ROOT / "src" / "rune_decrypter_prime" / "scoring" / "hamming" / "bindings.cpp",
            ROOT / "src" / "rune_decrypter_prime" / "scoring" / "hamming" / "Hamming.cpp",
            ROOT / "src" / "rune_decrypter_prime" / "scoring" / "hamming" / "Flat2DArray.cpp",
        ],
    ),
    (
        "rune_decrypter_prime.scoring.span_hamming._span_hamming_fast",
        [ROOT / "src" / "rune_decrypter_prime" / "scoring" / "span_hamming" / "fast_bindings.cpp"],
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


def _tail(text: str, *, max_lines: int = 35) -> str:
    lines = text.rstrip().splitlines()
    if not lines:
        return ""
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(["... output truncated; see full log file ...", *lines[-max_lines:]])


def _write_log(label: str, args: list[str], proc: subprocess.CompletedProcess[str]) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = LOG_DIR / f"{stamp}_{_safe_name(label)}.log"
    body = [
        f"label: {label}",
        "command: " + " ".join(args),
        f"returncode: {proc.returncode}",
        "",
        "--- stdout ---",
        proc.stdout or "",
        "",
        "--- stderr ---",
        proc.stderr or "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")
    return path


def _print_failure_output(proc: subprocess.CompletedProcess[str], log_path: Path) -> None:
    print(f"Full log: {log_path}")
    combined = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    if combined:
        print("\n--- output tail ---")
        print(_tail(combined))


def _run(label: str, args: list[str]) -> None:
    print(f"[RUN ] {label}")
    if VERBOSE:
        print("      " + " ".join(args))
    proc = subprocess.run(
        args,
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    log_path = _write_log(label, args, proc)
    if proc.returncode == 0:
        print(f"[PASS] {label}")
        if VERBOSE:
            _print_failure_output(proc, log_path)
        return

    print(f"[FAIL] {label} exited with {proc.returncode}")
    print("Command:", " ".join(args))
    _print_failure_output(proc, log_path)
    raise InstallFailure(label)


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
    _check_module_import("rune_decrypter_prime", label="Check Python package import")

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


def _check_assets() -> None:
    print("[RUN ] Check required V1 asset sentinels")
    missing = [path for path in REQUIRED_ASSET_SENTINELS if not path.is_file()]
    if missing:
        print("[FAIL] Missing required V1 asset sentinels:")
        for path in missing:
            print(" -", path.relative_to(ROOT).as_posix())
        raise InstallFailure("required V1 assets are missing")
    print("[PASS] required V1 asset sentinels present")


def _install_large_lm_assets() -> None:
    print("[RUN ] Install or verify required V1 LM3/LM4 assets")
    try:
        from tools.assets.release_asset_installer import AssetInstallError, install_release_asset_set

        install_release_asset_set(
            LARGE_ASSET_MANIFEST,
            LARGE_ASSET_SET,
            LARGE_ASSET_DOWNLOAD_DIR,
            LARGE_ASSET_ROOT,
        )
    except AssetInstallError as exc:
        print("[FAIL] Required V1 large LM assets are not installed.")
        print("Manual fallback:")
        print("  Download rdp-v1-lm-large-part*.zip from the V1 GitHub Release.")
        print("  Place them under downloads/.")
        print("  Run python install.py again.")
        raise InstallFailure(f"required V1 large LM assets are missing or corrupt: {exc}") from exc
    print("[PASS] required V1 LM3/LM4 assets installed or verified")


def _run_smoke_tests() -> None:
    _run("Run compact V1 smoke tests", [PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider", *SMOKE_TESTS])


def run_install(*, install_large_lm_assets: bool, mode_label: str) -> int:
    print("Rune Decrypter Prime V1 installer")
    print(f"Mode: {mode_label}")
    print(f"Repo root: {ROOT}")
    print("Successful command output is hidden. Set RDP_INSTALL_VERBOSE=1 to show it.")
    print("Full command logs are written under output/install_logs/.")
    print("pip is not upgraded automatically.")
    if install_large_lm_assets:
        print("This full V1 install downloads or verifies the required LM3/LM4 assets.")
    else:
        print("This CI-only light install skips the real large LM download.")
    print()
    try:
        _verify_python()
        _install_package()
        _check_imports()
        _check_assets()
        if install_large_lm_assets:
            _install_large_lm_assets()
        else:
            print("[SKIP] Real LM3/LM4 asset download skipped for CI-light install")
        _run_smoke_tests()
        print(f"[PASS] RDP V1 install smoke complete ({mode_label})")
        return 0
    except InstallFailure as exc:
        print(f"[INSTALL FAILED] {exc}")
        return 1
    except KeyboardInterrupt:
        print("\n[INSTALL FAILED] interrupted")
        return 130


def main() -> int:
    return run_install(install_large_lm_assets=True, mode_label=INSTALL_MODE_LABEL)


if __name__ == "__main__":
    raise SystemExit(main())
