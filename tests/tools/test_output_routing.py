from pathlib import Path
import pytest
from rdp.core.config import output_paths as routing


def test_precedence_and_no_environment_mutation(tmp_path, monkeypatch):
    inherited = tmp_path / 'inherited'
    monkeypatch.setenv('RDP_OUTPUT_ROOT', str(inherited))
    monkeypatch.chdir(tmp_path)
    assert routing.resolve_output_root(Path('explicit')) == tmp_path / 'explicit'
    assert routing.resolve_output_root() == inherited
    import os
    assert os.environ['RDP_OUTPUT_ROOT'] == str(inherited)


@pytest.mark.parametrize('value', ['', 'relative/output'])
def test_invalid_inherited_root_fails(value, monkeypatch):
    monkeypatch.setenv('RDP_OUTPUT_ROOT', value)
    with pytest.raises(ValueError, match='absolute'):
        routing.resolve_output_root()


def test_source_default_ignores_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv('RDP_OUTPUT_ROOT', raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(routing, 'source_root', lambda: tmp_path / 'checkout')
    assert routing.resolve_output_root() == tmp_path / 'checkout/output'


def test_installed_default_uses_platform_directory(tmp_path, monkeypatch):
    import platformdirs
    monkeypatch.delenv('RDP_OUTPUT_ROOT', raising=False)
    monkeypatch.setattr(routing, 'source_root', lambda: None)
    monkeypatch.setattr(platformdirs, 'user_data_path', lambda *a, **kw: tmp_path / 'user-data')
    assert routing.resolve_output_root() == tmp_path / 'user-data/output'


def test_unrelated_project_is_not_rdp(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[project]\nname="other"\n')
    assert routing.source_root(tmp_path) is None


def test_destination_failure_does_not_fall_back(tmp_path, monkeypatch):
    blocked = tmp_path / 'file'
    blocked.write_text('keep')
    monkeypatch.setenv('RDP_OUTPUT_ROOT', str(blocked))
    with pytest.raises(FileExistsError):
        routing.resolve_output_root()
    assert blocked.read_text() == 'keep'


def test_cross_drive_paths_remain_usable(tmp_path, monkeypatch):
    def different_drive(*args):
        raise ValueError('different drives')
    monkeypatch.setattr(routing.os.path, 'relpath', different_drive)
    assert routing.path_from(tmp_path, Path('other')) == str(tmp_path)
