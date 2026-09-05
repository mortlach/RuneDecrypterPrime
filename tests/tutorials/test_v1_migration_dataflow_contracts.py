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


def test_interruptor_support_import_is_defined_for_direct_execution() -> None:
    for filename in (
        "vigenere_interruptors_exact.py",
        "vigenere_interruptors_solve.py",
        "vigenere_interruptors_nontrivial.py",
        "vigenere_interruptors_robust.py",
    ):
        source = _source(filename)
        root_setup = source.index("sys.path.insert(0, str(_ROOT))")
        support_import = source.index(
            "from tutorials.v1.data.two_period_cribs_demo import "
            "encrypt_interruptor_fixture"
        )
        assert root_setup < support_import

    exact = _source("vigenere_interruptors_exact.py")
    assert "rune_decrypter_prime.utils.interrupter" not in exact
    assert "rdp.ciphers.interruptors" not in exact
    assert "InterruptorConfig.exact(INTERRUPTORS)" in exact


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
