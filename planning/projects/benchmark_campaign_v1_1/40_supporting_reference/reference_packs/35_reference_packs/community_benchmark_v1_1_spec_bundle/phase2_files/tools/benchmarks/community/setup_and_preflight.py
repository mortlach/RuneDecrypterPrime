#!/usr/bin/env python3
"""
RDP Community Benchmark setup and preflight script (v1.1).

This script performs the following steps:
 1. Recombine packed assets into the `assets/` folder according to
    `assets_manifest_v1.json` located at the repository root.
 2. Build or verify the `_fastlm` C-extension required for CPU scoring.
 3. Run a series of preflight checks to ensure the solver and scoring
    infrastructure is ready for community benchmark runs.
 4. Write detailed JSON reports and log files.  If all steps succeed,
    a `benchmark_ready.json` marker is written.

The script is intentionally self-contained and makes no assumptions
about environment variables.  All I/O paths are derived relative to
`repo_root`, which defaults to the current working directory.

Notes:
- The asset recombination logic concatenates part files in order.  If
  part filenames end with `.zst`, an attempt is made to decompress
  using the `zstandard` library; if decompression fails, the data is
  concatenated as-is and an error is recorded.
- `_fastlm` build logic attempts to import the extension.  If import
  fails, it looks for a `setup_fastlm.py` script in a few common
  locations and executes it.  If building still fails, the script
  continues but marks `fastlm_present` as false.
- Preflight imports core RDP modules and performs a tiny dummy
  scoring call if possible.  This portion may need adjustment if
  solver APIs change.

Usage:
    python setup_and_preflight.py [--repo-root PATH] [--no-build-fastlm]

The `--no-build-fastlm` flag skips the build attempt and simply
checks for `_fastlm` availability.  This can be useful when using a
prebuilt wheel on Windows.
"""
import argparse
import hashlib
import json
import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file in streaming fashion."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def recombine_assets(manifest_path: Path, repo_root: Path, logf) -> list:
    """Recombine packed assets into the `assets/` folder.

    Returns a list of issues encountered.
    """
    issues = []
    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception as e:
        issues.append(f"Failed to load assets manifest: {e}")
        return issues

    assets = manifest.get('assets') or []
    for asset in assets:
        out_rel = asset.get('output') or asset.get('output_path')
        if not out_rel:
            issues.append("Manifest entry missing output path")
            continue
        output = repo_root / out_rel
        parts = asset.get('parts') or []
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = output.with_suffix(output.suffix + '.tmp')
        # concatenate parts
        with open(tmp_path, 'wb') as out_f:
            for part in parts:
                part_rel = part.get('path') or part.get('relpath')
                if not part_rel:
                    issues.append(f"Part missing path for {out_rel}")
                    continue
                part_path = repo_root / part_rel
                if not part_path.exists():
                    issues.append(f"Missing asset part: {part_rel}")
                    continue
                data = part_path.read_bytes()
                # decompress .zst if possible
                if part_path.suffix == '.zst':
                    try:
                        import zstandard as zstd  # optional
                        dctx = zstd.ZstdDecompressor()
                        data = dctx.decompress(data)
                    except Exception as e:
                        issues.append(f"Failed to decompress {part_rel}: {e}")
                        # fall back to raw bytes
                out_f.write(data)
        # verify size and sha256
        try:
            expected_size = int(asset.get('size'))
        except Exception:
            expected_size = None
        expected_sha = asset.get('sha256')
        try:
            actual_size = tmp_path.stat().st_size
            actual_sha = sha256_file(tmp_path)
        except Exception as e:
            issues.append(f"Cannot compute checksum for {out_rel}: {e}")
            actual_size = None
            actual_sha = None
        if expected_size is not None and actual_size != expected_size:
            issues.append(f"Size mismatch for {out_rel}: expected {expected_size}, got {actual_size}")
        if expected_sha and actual_sha and actual_sha.lower() != expected_sha.lower():
            issues.append(f"SHA mismatch for {out_rel}: expected {expected_sha}, got {actual_sha}")
        # move into place atomically
        try:
            os.replace(tmp_path, output)
        except Exception as e:
            issues.append(f"Failed to move {tmp_path} into {output}: {e}")
    return issues


def build_fastlm(repo_root: Path, logf, no_build: bool = False) -> bool:
    """Attempt to build or verify the `_fastlm` extension.

    Returns True if the extension is available after this function.
    """
    def import_fastlm() -> bool:
        try:
            import importlib
            importlib.import_module('rune_decrypter_prime._fastlm')
            return True
        except Exception:
            return False
    # already present
    if import_fastlm():
        logf.write("_fastlm present.\n")
        return True
    if no_build:
        logf.write("_fastlm missing; build skipped due to --no-build-fastlm.\n")
        return False
    # attempt to run known build scripts
    candidates = [
        repo_root / 'setup_fastlm.py',
        repo_root / 'tools' / 'benchmarks' / 'community' / 'setup_fastlm.py',
        repo_root / 'tools' / 'build_fastlm.py',
    ]
    for script in candidates:
        if script.exists():
            logf.write(f"Building _fastlm using {script}\n")
            try:
                subprocess.check_call([sys.executable, str(script)], cwd=str(repo_root))
            except Exception as e:
                logf.write(f"Failed to build _fastlm: {e}\n")
            break
    # re-import
    if import_fastlm():
        logf.write("_fastlm build succeeded.\n")
        return True
    else:
        logf.write("_fastlm still unavailable after build attempt.\n")
        return False


def run_preflight(repo_root: Path, logf, fastlm_present: bool) -> dict:
    """Run preflight checks and return a report dict."""
    report = {
        'device': 'cpu',
        'scoring_backend': 'numpy',
        'fastlm_present': fastlm_present,
        'success': True,
        'details': []
    }
    # Check imports
    try:
        import importlib
        importlib.import_module('rune_decrypter_prime')
        importlib.import_module('rune_decrypter_prime.scoring.language_model.language_model_prime')
    except Exception as e:
        report['success'] = False
        report['details'].append(f"Import error: {e}")
    # Check assets folder
    assets_dir = repo_root / 'assets'
    if not assets_dir.exists() or not any(assets_dir.iterdir()):
        report['success'] = False
        report['details'].append('Assets folder missing or empty')
    # Dummy scoring call
    if report['success']:
        try:
            from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
            # attempt to load small model; will raise if assets missing
            # Note: this call may take time; catch exceptions
            lm = LanguageModelPrime.load_default(device='cpu')  # type: ignore
            # attempt a trivial score call on a few characters
            _ = lm.score_chars([0, 1, 2])  # type: ignore
            logf.write("Preflight scoring call succeeded.\n")
        except Exception as e:
            report['success'] = False
            report['details'].append(f"Scoring call failed: {e}")
    return report


def main():
    parser = argparse.ArgumentParser(description='RDP benchmark setup and preflight (v1.1)')
    parser.add_argument('--repo-root', type=str, default='.', help='Path to repository root')
    parser.add_argument('--no-build-fastlm', action='store_true', help='Skip attempting to build _fastlm')
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    logs_dir = repo_root / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    setup_log_path = logs_dir / 'setup.log'
    preflight_log_path = logs_dir / 'preflight.log'
    with open(setup_log_path, 'w') as setup_log, open(preflight_log_path, 'w') as preflight_log:
        setup_log.write(f"Setup started {datetime.utcnow().isoformat()}Z\n")
        # Recombine assets
        manifest_path = repo_root / 'assets_manifest_v1.json'
        issues = recombine_assets(manifest_path, repo_root, setup_log)
        if issues:
            setup_log.write("\n".join(issues) + "\n")
        # Build/verify fastlm
        fastlm_ok = build_fastlm(repo_root, setup_log, args.no_build_fastlm)
        setup_success = not issues and fastlm_ok
        setup_report = {
            'success': setup_success,
            'issues': issues,
            'fastlm_present': fastlm_ok
        }
        # Write setup report
        (repo_root / 'setup_report.json').write_text(json.dumps(setup_report, indent=2))
        setup_log.write(f"Setup completed {datetime.utcnow().isoformat()}Z\n")
        # Preflight
        preflight_log.write(f"Preflight started {datetime.utcnow().isoformat()}Z\n")
        preflight_report = run_preflight(repo_root, preflight_log, fastlm_ok)
        (repo_root / 'preflight_report.json').write_text(json.dumps(preflight_report, indent=2))
        preflight_log.write(f"Preflight completed {datetime.utcnow().isoformat()}Z\n")
    # Write success marker if all good
    if setup_report['success'] and preflight_report['success']:
        (repo_root / 'benchmark_ready.json').write_text(json.dumps({'ready': True}))
    return 0 if setup_report['success'] and preflight_report['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
