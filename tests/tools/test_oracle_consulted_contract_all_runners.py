from __future__ import annotations

from pathlib import Path

import pytest

import rune_decrypter_prime as rdp


pytestmark = pytest.mark.tier_a


def test_runner_configs_do_not_derive_consulted_from_enabled() -> None:
    root = Path(rdp.__file__).resolve().parents[2]
    offenders: list[str] = []
    targets = [
        root / "tools" / "benchmarks" / "periodic_sub_trans" / "col_then_sub" / "runner.py",
        root / "tools" / "benchmarks" / "periodic_sub_trans" / "sub_then_col" / "runner.py",
        root / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli" / "run_config_builder.py",
    ]
    bad = "oracle_consulted_in_decisions=bool(oracle_decision_paths_enabled)"
    for fp in targets:
        text = fp.read_text(encoding="utf-8")
        if bad in text:
            offenders.append(str(fp.relative_to(root)).replace("\\", "/"))
    assert not offenders, (
        "oracle_consulted_in_decisions must represent realized decision usage, "
        "not oracle decision-path capability:\n- " + "\n- ".join(offenders)
    )

