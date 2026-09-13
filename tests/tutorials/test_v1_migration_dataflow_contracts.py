from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a
TUTORIALS = (
    Path(__file__).resolve().parents[2] / "tutorials" / "v1" / "examples"
)


def _source(filename: str) -> str:
    return (TUTORIALS / filename).read_text(encoding="utf-8")


def test_frequency_seed_pools_cross_the_public_run_boundary() -> None:
    for filename in (
        "mono_substitution_ga_ltr.py",
        "mono_substitution_ga_rtl.py",
    ):
        source = _source(filename)
        assert "make_seeds_from_freq(" in source
        assert "initial_keys=initial_keys" in source

    periodic = _source("periodic_substitution.py")
    assert "initial_keys=initial_keys" in periodic
    assert "initial_keys=retry_initial_keys" in periodic

    periodic_simple = _source("periodic_substitution_p7.py")
    assert "make_periodic_seed_pool(" in periodic_simple
    assert "initial_keys=initial_keys" in periodic_simple


def test_periodic_columnar_uses_the_qualified_public_warm_start() -> None:
    source = _source("periodic_columnar_p7_column_then_substitution.py")
    assert "from rdp import api" in source
    assert "initial_keys=(QUALIFIED_INITIAL_KEY,)" in source
    assert "target_score=None" in source
    assert "result = api.run(" in source
    assert "oracle_stop_score" not in source
    assert "generate_seed_keys_periodic_columnar" not in source


def test_hybrid_mono_frequency_seeds_cross_the_public_run_boundary() -> None:
    source = _source("mono_substitution_hybrid_rtl.py")
    assert "make_seeds_from_freq(" in source
    assert "initial_keys=tuple(" in source
    assert "no true-key seed" in source


def test_previously_silent_acceptance_paths_report_a_match_ratio() -> None:
    for filename in (
        "columnar_transposition.py",
        "vigenere_general_map.py",
        "repeating_multiply.py",
        "mono_substitution_ga_ltr.py",
        "mono_substitution_ga_rtl.py",
        "mono_substitution_ga_robust.py",
        "mono_substitution_hybrid_rtl.py",
        "mono_substitution_sa_ltr.py",
        "vigenere_interruptors_exact.py",
        "vigenere_interruptors_solve.py",
        "vigenere_interruptors_nontrivial.py",
        "vigenere_interruptors_robust.py",
        "scheduled_stream_lookup_p13_sequence.py",
        "scheduled_stream_lookup_p13_primes.py",
        "scheduled_stream_lookup_p13_p31_segmented.py",
        "periodic_substitution.py",
        "periodic_substitution_p7.py",
        "periodic_columnar_p7_column_then_substitution.py",
    ):
        assert "Match ratio:" in _source(filename), filename
