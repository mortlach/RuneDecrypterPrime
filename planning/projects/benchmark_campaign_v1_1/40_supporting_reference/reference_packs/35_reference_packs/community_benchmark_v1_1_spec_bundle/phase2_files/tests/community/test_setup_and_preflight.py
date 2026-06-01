"""Test scaffolding for the benchmark setup/preflight script.

These tests exercise the public functions in `setup_and_preflight.py`.  They
avoid heavy dependencies and external asset files by mocking parts of the
filesystem.  Developers are expected to expand these tests to cover real
manifests and scoring calls when assets and models are available.

To run these tests:
    pytest -q tests/community/test_setup_and_preflight.py
"""
import json
from pathlib import Path
import tempfile

import pytest

# Import the functions under test
from tools.benchmarks.community.setup_and_preflight import (
    recombine_assets, build_fastlm, run_preflight
)


def test_recombine_manifest_loads(tmp_path):
    # Create a dummy manifest with one tiny asset
    manifest = {
        'assets': [
            {
                'output': 'assets/dummy.txt',
                'size': 11,
                'sha256': '2aae6c35c94fcfb415dbe95f408b9ce91ee846ed',  # sha1 of 'Hello World' (placeholder)
                'parts': [
                    {'path': 'assets_packed/dummy.part1', 'size': 11, 'sha256': '2aae6c35c94fcfb415dbe95f408b9ce91ee846ed'}
                ]
            }
        ]
    }
    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    (repo_root / 'assets_packed').mkdir(parents=True)
    (repo_root / 'assets').mkdir(parents=True)
    # Write manifest
    (repo_root / 'assets_manifest_v1.json').write_text(json.dumps(manifest))
    # Write dummy part
    part_path = repo_root / 'assets_packed/dummy.part1'
    part_path.write_text('Hello World')
    # Run recombination
    issues = recombine_assets(repo_root / 'assets_manifest_v1.json', repo_root, open(os.devnull, 'w'))
    # The dummy checksum will not match our placeholder SHA; expect at least one issue
    assert issues, "Expected checksum mismatch due to placeholder SHA"


def test_build_fastlm_reports_missing(monkeypatch, tmp_path):
    # Simulate missing fastlm by removing any import
    monkeypatch.setitem(sys.modules, 'rune_decrypter_prime._fastlm', None)
    ok = build_fastlm(Path(tmp_path), open(os.devnull, 'w'), no_build=True)
    assert not ok


def test_run_preflight_reports_missing_assets(tmp_path):
    # Repo without assets
    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    report = run_preflight(repo_root, open(os.devnull, 'w'), fastlm_present=False)
    assert not report['success']
    assert 'Assets folder missing' in ' '.join(report['details'])
