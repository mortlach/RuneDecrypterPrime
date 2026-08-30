from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.tier_a
TUTORIALS = Path(__file__).resolve().parents[2] / "tutorials" / "v1"


def _source(filename: str) -> str:
    return (TUTORIALS / filename).read_text(encoding="utf-8")


def test_frequency_seed_pools_cross_the_public_run_boundary() -> None:
    for filename in (
        "Tutorial_MonoSubstitution_GA_LTR.py",
        "Tutorial_MonoSubstitution_GA_RTL.py",
    ):
        source = _source(filename)
        assert "make_seeds_from_freq(" in source
        assert "initial_keys=initial_keys" in source

    periodic = _source("Tutorial_PeriodicSubstitution.py")
    assert "initial_keys=initial_keys" in periodic
    assert "initial_keys=retry_initial_keys" in periodic

    periodic_simple = _source("Tutorial_PeriodicSubstitution_Simple_P7.py")
    assert "make_periodic_seed_pool(" in periodic_simple
    assert "initial_keys=initial_keys" in periodic_simple


def test_periodic_columnar_preserves_both_stage_handoffs() -> None:
    source = _source("Tutorial_PeriodicColumnar_Simple_P7_ColThenSub.py")
    assert "generate_seed_keys_periodic_columnar(" in source
    assert "initial_keys=stage1_initial_keys" in source
    assert "warm_keys.append(tuple(int(value) for value in stage1.key))" in source
    assert "initial_keys=tuple(warm_keys) if warm_keys else None" in source


def test_long_running_kaeding_tutorials_are_labelled_in_the_manifest() -> None:
    manifest = json.loads(
        (TUTORIALS / "tutorial_manifest_v1.json").read_text(encoding="utf-8")
    )
    entries = {entry["path"]: entry for entry in manifest["tutorials"]}
    for filename in (
        "Tutorial_PeriodicSubstitution.py",
        "Tutorial_PeriodicSubstitution_Simple_P7.py",
        "Tutorial_PeriodicColumnar_Simple_P7_ColThenSub.py",
    ):
        assert "LONG-RUNNING KAEDING QUALIFICATION" in entries[filename]["notes"]


def test_interruptor_support_import_is_defined_for_direct_execution() -> None:
    for filename in (
        "Tutorial_Vigenere_Interruptors_Exact.py",
        "Tutorial_Vigenere_Interruptors_Solve.py",
        "Tutorial_Vigenere_Interruptors_NonTrivial.py",
        "Tutorial_Vigenere_Interruptors_Robust.py",
    ):
        source = _source(filename)
        root_setup = source.index("sys.path.insert(0, str(_ROOT))")
        support_import = source.index(
            "from tutorials.v1.data.two_period_cribs_demo import "
            "encrypt_interruptor_fixture"
        )
        assert root_setup < support_import

    exact = _source("Tutorial_Vigenere_Interruptors_Exact.py")
    assert "rune_decrypter_prime.utils.interrupter" not in exact
    assert "InterruptorConfig.exact(INTERRUPTORS)" in exact


def test_hybrid_mono_frequency_seeds_cross_the_public_run_boundary() -> None:
    source = _source("Tutorial_MonoSubstitution_HYBRID_RTL.py")
    assert "make_seeds_from_freq(" in source
    assert "initial_keys=tuple(" in source
    assert "no true-key seed" in source


def test_previously_silent_acceptance_paths_report_a_match_ratio() -> None:
    for filename in (
        "Tutorial_ColumnarTransposition.py",
        "Tutorial_Vigenere_GeneralMap.py",
        "Tutorial_Repeating_multiply.py",
        "Tutorial_MonoSubstitution_GA_LTR.py",
        "Tutorial_MonoSubstitution_GA_RTL.py",
        "Tutorial_MonoSubstitution_GA_Robust.py",
        "Tutorial_MonoSubstitution_HYBRID_RTL.py",
        "Tutorial_MonoSubstitution_SA_LTR.py",
        "Tutorial_Vigenere_Interruptors_Exact.py",
        "Tutorial_Vigenere_Interruptors_Solve.py",
        "Tutorial_Vigenere_Interruptors_NonTrivial.py",
        "Tutorial_Vigenere_Interruptors_Robust.py",
        "Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py",
        "Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py",
        "Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py",
        "Tutorial_PeriodicSubstitution.py",
        "Tutorial_PeriodicSubstitution_Simple_P7.py",
        "Tutorial_PeriodicColumnar_Simple_P7_ColThenSub.py",
    ):
        assert "Match ratio:" in _source(filename), filename
