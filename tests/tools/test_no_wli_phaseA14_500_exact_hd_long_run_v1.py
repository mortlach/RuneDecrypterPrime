from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    scan_phaseA_v0_14_span_hamming_500_exact_hd_all_ladder_full_v1 as all_mod,
    scan_phaseA_v0_14_span_hamming_500_exact_hd_long_ladder_full_v1 as long_mod,
)


EXPECTED_LONG_LENGTHS = (5, 6, 7, 8, 9, 10, 11, 12, 13, 14)
EXPECTED_LONG_MAX_HD_BY_LENGTH = {
    5: 1,
    6: 2,
    7: 2,
    8: 3,
    9: 3,
    10: 4,
    11: 4,
    12: 5,
    13: 5,
    14: 5,
}

EXPECTED_ALL_LENGTHS = tuple(range(1, 15))
EXPECTED_ALL_MAX_HD_BY_LENGTH = {
    1: 0,
    2: 0,
    3: 1,
    4: 1,
    5: 1,
    6: 2,
    7: 2,
    8: 3,
    9: 3,
    10: 4,
    11: 4,
    12: 5,
    13: 5,
    14: 5,
}


def _assert_phaseA14_only(module: object) -> None:
    ids = [row["dictionary_id"] for row in module.SPAN_CONFIG_SPECS]
    assert ids == ["phaseA14_strict_selected", "phaseA14_normal_selected"]
    assert module.MAX_CANDIDATES_PER_WINDOW == 100_000
    assert module.TOKEN_HASH_LIMIT_FOR_CANARY == 0
    assert all(row["require_selected"] is True for row in module.SPAN_CONFIG_SPECS)
    assert all("hamming_dictionary_policies_phaseA_v0_14" in row["wordlist_rel"] for row in module.SPAN_CONFIG_SPECS)
    assert all("old_" not in row["dictionary_id"] for row in module.SPAN_CONFIG_SPECS)
    assert all("broad" not in row["dictionary_id"] for row in module.SPAN_CONFIG_SPECS)
    assert all("research" not in row["dictionary_id"] for row in module.SPAN_CONFIG_SPECS)


def test_long_ladder_run_uses_phaseA14_only_high_cap_full_dataset() -> None:
    _assert_phaseA14_only(long_mod)
    assert long_mod.LENGTHS == EXPECTED_LONG_LENGTHS
    assert long_mod.MAX_HD_BY_LENGTH == EXPECTED_LONG_MAX_HD_BY_LENGTH


def test_long_ladder_apply_config_sets_existing_fingerprint_scanner() -> None:
    long_mod._apply_config()
    assert long_mod.scan.RUN_LABEL == long_mod.RUN_LABEL
    assert long_mod.scan.OUTPUT_DIR_REL == long_mod.OUTPUT_DIR_REL
    assert long_mod.scan.LENGTHS == EXPECTED_LONG_LENGTHS
    assert long_mod.scan.MAX_HD_BY_LENGTH == EXPECTED_LONG_MAX_HD_BY_LENGTH
    assert long_mod.scan.SPAN_CONFIG_SPECS == long_mod.SPAN_CONFIG_SPECS
    assert long_mod.scan.MAX_CANDIDATES_PER_WINDOW == 100_000
    assert long_mod.scan.TOKEN_HASH_LIMIT_FOR_CANARY == 0


def test_all_ladder_run_uses_phaseA14_only_high_cap_full_dataset() -> None:
    _assert_phaseA14_only(all_mod)
    assert all_mod.LENGTHS == EXPECTED_ALL_LENGTHS
    assert all_mod.MAX_HD_BY_LENGTH == EXPECTED_ALL_MAX_HD_BY_LENGTH


def test_all_ladder_apply_config_sets_existing_fingerprint_scanner() -> None:
    all_mod._apply_config()
    assert all_mod.scan.RUN_LABEL == all_mod.RUN_LABEL
    assert all_mod.scan.OUTPUT_DIR_REL == all_mod.OUTPUT_DIR_REL
    assert all_mod.scan.LENGTHS == EXPECTED_ALL_LENGTHS
    assert all_mod.scan.MAX_HD_BY_LENGTH == EXPECTED_ALL_MAX_HD_BY_LENGTH
    assert all_mod.scan.SPAN_CONFIG_SPECS == all_mod.SPAN_CONFIG_SPECS
    assert all_mod.scan.MAX_CANDIDATES_PER_WINDOW == 100_000
    assert all_mod.scan.TOKEN_HASH_LIMIT_FOR_CANARY == 0
