"""Installer argument handling without provisioning or starting smoke tests."""
import importlib.util
from pathlib import Path
import sys

import pytest


@pytest.mark.parametrize('arguments, expected', [([], False), (['--verbose'], True)])
def test_installer_verbosity_is_explicit(monkeypatch, arguments, expected):
    monkeypatch.setenv('RDP_INSTALL_VERBOSE', '1')
    path = Path(__file__).resolve().parents[2] / 'install.py'
    spec = importlib.util.spec_from_file_location('installer_cli_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.VERBOSE is False
    received = []
    monkeypatch.setattr(module, 'run_install', lambda **kwargs: received.append(kwargs) or 0)
    monkeypatch.setattr(sys, 'argv', ['install.py', *arguments])
    assert module.main() == 0
    assert received == [{'asset_profile_name': 'full_v1',
                         'mode_label': module.INSTALL_MODE_LABEL, 'verbose': expected}]
