from __future__ import annotations
from pathlib import Path
from rdp.core.config.cipher import CipherConfig
from rdp.core.config.run import RunConfig
from rdp.core.config.scoring import ScoringConfig
from rdp.core.config.solver import SolverConfig
REPO_ROOT = Path(__file__).resolve().parents[2]

def test_split_config_package_is_the_v1_config_surface() -> None:
    assert CipherConfig.__module__ == 'rdp.core.config.cipher'
    assert ScoringConfig.__module__ == 'rdp.core.config.scoring'
    assert SolverConfig.__module__ == 'rdp.core.config.solver'
    assert RunConfig.__module__ == 'rdp.core.config.run'

def test_no_dead_monolithic_core_config_module_file_exists() -> None:
    assert not (REPO_ROOT / 'src' / 'rune_decrypter_prime' / 'core' / 'config.py').exists()
    assert not (REPO_ROOT / 'src' / 'rune_decrypter_prime' / 'core' / 'config').exists()
    assert not (REPO_ROOT / 'src' / 'rune_decrypter_prime' / 'core' / 'problem').exists()
    assert not (REPO_ROOT / 'src' / 'rune_decrypter_prime' / 'core' / 'logging_config.py').exists()
    assert not (REPO_ROOT / 'src' / 'rune_decrypter_prime' / 'core' / 'telemetry.py').exists()

def test_internal_source_does_not_import_dead_config_module_alias() -> None:
    forbidden = {
        'rdp.core.config_legacy',
        'rune_decrypter_prime.core.config',
        'rune_decrypter_prime.core.problem',
        'rune_decrypter_prime.core.logging_config',
        'rune_decrypter_prime.core.telemetry',
    }
    offenders: list[str] = []
    for path in sorted((REPO_ROOT / 'src').rglob('*.py')):
        text = path.read_text(encoding='utf-8-sig')
        for token in forbidden:
            if token in text:
                offenders.append(f'{path.relative_to(REPO_ROOT).as_posix()}: {token}')
    assert not offenders
