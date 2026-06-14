from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

D3_CONTRACT_FILES = [
    ROOT / "src/rune_decrypter_prime/core/engine/builders.py",
    ROOT / "src/rune_decrypter_prime/core/capability_gates.py",
    ROOT / "src/rune_decrypter_prime/scoring/scorer_lane_report.py",
    ROOT / "src/rune_decrypter_prime/api/pipeline_helpers.py",
    ROOT / "src/rune_decrypter_prime/api/run.py",
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_removed_core_config_shim_does_not_exist() -> None:
    assert not (ROOT / "src/rune_decrypter_prime/core/config.py").exists()


def test_d3_contract_paths_do_not_use_hidden_config_helpers() -> None:
    banned = ("_cfg_get", "_config_get", "_get_cfg", "_get_config")
    for path in D3_CONTRACT_FILES:
        text = _text(path)
        for token in banned:
            assert token not in text, f"{token} found in {path.relative_to(ROOT)}"


def test_d3_contract_paths_do_not_score_report_only_lanes() -> None:
    banned = ("report_only_score", "score_report_only", "report_only_bonus")
    for path in D3_CONTRACT_FILES:
        text = _text(path)
        for token in banned:
            assert token not in text, f"{token} found in {path.relative_to(ROOT)}"
