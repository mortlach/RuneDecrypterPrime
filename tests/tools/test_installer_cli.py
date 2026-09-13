"""Installer argument handling without provisioning or starting smoke tests."""
import importlib.util
from pathlib import Path
import sys

import pytest


@pytest.mark.parametrize(
    'arguments, expected_verbose, expected_break_system_packages',
    [([], False, False), (['--verbose'], True, False),
     (['--break-system-packages'], False, True)],
)
def test_installer_options_are_explicit(
    monkeypatch, arguments, expected_verbose, expected_break_system_packages
):
    monkeypatch.setenv('RDP_INSTALL_VERBOSE', '1')
    module = _load_installer()
    assert module.VERBOSE is False
    received = []
    monkeypatch.setattr(module, 'run_install', lambda **kwargs: received.append(kwargs) or 0)
    monkeypatch.setattr(sys, 'argv', ['install.py', *arguments])
    assert module.main() == 0
    assert received == [{'asset_profile_name': 'full_v1',
                         'mode_label': module.INSTALL_MODE_LABEL,
                         'verbose': expected_verbose,
                         'break_system_packages': expected_break_system_packages}]


def test_installer_passes_pep668_override_only_when_requested(monkeypatch):
    module = _load_installer()
    commands = []
    monkeypatch.setattr(module, '_run', lambda _label, args: commands.append(args))

    module._install_package()
    module._install_package(break_system_packages=True)

    assert '--break-system-packages' not in commands[0]
    assert '--break-system-packages' in commands[1]


def test_installer_explains_externally_managed_failure(monkeypatch, capsys):
    module = _load_installer()
    monkeypatch.setattr(
        module,
        '_run',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(module.InstallFailure('pip')),
    )
    monkeypatch.setattr(module, '_uses_externally_managed_python', lambda: True)

    with pytest.raises(module.InstallFailure):
        module._install_package()

    output = capsys.readouterr().out
    assert 'managed by the operating system' in output
    assert 'another Python or from an environment you manage' in output
    assert 'python install.py --break-system-packages' in output
    assert 'does not enable that override automatically' in output


def test_externally_managed_marker_applies_only_to_base_python(monkeypatch, tmp_path):
    module = _load_installer()
    (tmp_path / 'EXTERNALLY-MANAGED').write_text('', encoding='utf-8')
    monkeypatch.setattr(module.sysconfig, 'get_path', lambda _name: str(tmp_path))
    monkeypatch.setattr(module.sys, 'prefix', '/usr')
    monkeypatch.setattr(module.sys, 'base_prefix', '/usr')
    assert module._uses_externally_managed_python() is True

    monkeypatch.setattr(module.sys, 'prefix', '/chosen/environment')
    assert module._uses_externally_managed_python() is False


def _load_installer():
    path = Path(__file__).resolve().parents[2] / 'install.py'
    spec = importlib.util.spec_from_file_location('installer_pep668_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
