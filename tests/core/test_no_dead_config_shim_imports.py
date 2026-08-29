from __future__ import annotations
from pathlib import Path
from rune_decrypter_prime.core.config import (
    CipherConfig,
    RunConfig,
    ScoringConfig,
    SolverConfig,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_split_config_package_is_the_v1_config_surface() -> None:
    assert CipherConfig.__module__ == "rune_decrypter_prime.core.config.cipher"
    assert ScoringConfig.__module__ == "rune_decrypter_prime.core.config.scoring"
    assert SolverConfig.__module__ == "rune_decrypter_prime.core.config.solver"
    assert RunConfig.__module__ == "rune_decrypter_prime.core.config.run"


def test_no_dead_monolithic_core_config_module_file_exists() -> None:
    assert not (
        REPO_ROOT / "src" / "rune_decrypter_prime" / "core" / "config.py"
    ).exists()


def test_internal_source_does_not_import_dead_config_module_alias() -> None:
    forbidden = "rune_decrypter_prime.core.config_legacy"
    offenders: list[str] = []
    for path in sorted((REPO_ROOT / "src" / "rune_decrypter_prime").rglob("*.py")):
        text = path.read_text(encoding="utf-8-sig")
        if forbidden in text:
            offenders.append(path.relative_to(REPO_ROOT).as_posix())
    assert not offenders
