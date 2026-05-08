from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseA_v0_14_span_hamming_8hour_data_queue_v1 as queue,
    scan_phaseA_v0_14_span_hamming_250_exact_hd_long_ladder_full_v1 as norm250,
    scan_phaseA_v0_14_span_hamming_500_exact_hd_normal_focus_v1 as normal_focus,
    scan_phaseA_v0_14_span_hamming_500_exact_hd_strict_keep_gate_v1 as strict_keep,
    scan_phaseA_v0_14_span_hamming_750_exact_hd_long_ladder_full_v1 as norm750,
    scan_phaseA_v0_14_span_hamming_1000_exact_hd_long_ladder_full_v1 as norm1000,
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


def _assert_phaseA14_long_wrapper(module: object, *, expected_chunk_length: int) -> None:
    assert module.CHUNK_LENGTH == expected_chunk_length
    assert module.CHUNK_KINDS == ("prefix", "middle", "suffix")
    assert module.LENGTHS == EXPECTED_LONG_LENGTHS
    assert module.MAX_HD_BY_LENGTH == EXPECTED_LONG_MAX_HD_BY_LENGTH
    assert module.MAX_CANDIDATES_PER_WINDOW == 100_000
    assert module.TOKEN_HASH_LIMIT_FOR_CANARY == 0
    ids = [row["dictionary_id"] for row in module.SPAN_CONFIG_SPECS]
    assert ids == ["phaseA14_strict_selected", "phaseA14_normal_selected"]
    assert all(row["require_selected"] is True for row in module.SPAN_CONFIG_SPECS)
    assert all("hamming_dictionary_policies_phaseA_v0_14" in row["wordlist_rel"] for row in module.SPAN_CONFIG_SPECS)


def test_chunk_stability_wrappers_use_phaseA14_only_high_cap() -> None:
    _assert_phaseA14_long_wrapper(norm250, expected_chunk_length=250)
    _assert_phaseA14_long_wrapper(norm750, expected_chunk_length=750)
    _assert_phaseA14_long_wrapper(norm1000, expected_chunk_length=1000)


def test_chunk_stability_apply_config_sets_base_chunk_length() -> None:
    norm250._apply_config()
    assert norm250.base.CHUNK_LENGTH == 250
    assert norm250.base.CHUNK_KINDS == ("prefix", "middle", "suffix")
    assert norm250.scan.CHUNK_KINDS == ("prefix", "middle", "suffix")
    assert norm250.scan.RUN_LABEL == norm250.RUN_LABEL
    assert norm250.scan.LENGTHS == EXPECTED_LONG_LENGTHS
    assert norm250.scan.MAX_HD_BY_LENGTH == EXPECTED_LONG_MAX_HD_BY_LENGTH
    assert norm250.scan.MAX_CANDIDATES_PER_WINDOW == 100_000


def test_normal_focus_wrapper_is_normal_only_lengths_5_to_10() -> None:
    assert normal_focus.CHUNK_LENGTH == 500
    assert normal_focus.LENGTHS == (5, 6, 7, 8, 9, 10)
    assert normal_focus.MAX_HD_BY_LENGTH == {5: 1, 6: 2, 7: 2, 8: 3, 9: 3, 10: 4}
    assert normal_focus.MAX_CANDIDATES_PER_WINDOW == 100_000
    assert [row["dictionary_id"] for row in normal_focus.SPAN_CONFIG_SPECS] == ["phaseA14_normal_selected"]
    assert all("normal/hamming_raw_1g" in row["wordlist_rel"] for row in normal_focus.SPAN_CONFIG_SPECS)


def test_strict_keep_gate_wrapper_is_strict_only_long_hd0_to_hd2() -> None:
    assert strict_keep.CHUNK_LENGTH == 500
    assert strict_keep.LENGTHS == (8, 9, 10, 11, 12, 13, 14)
    assert strict_keep.MAX_HD_BY_LENGTH == {8: 2, 9: 2, 10: 2, 11: 2, 12: 2, 13: 2, 14: 2}
    assert strict_keep.MAX_CANDIDATES_PER_WINDOW == 100_000
    assert [row["dictionary_id"] for row in strict_keep.SPAN_CONFIG_SPECS] == ["phaseA14_strict_selected"]
    assert all("strict/hamming_raw_1g" in row["wordlist_rel"] for row in strict_keep.SPAN_CONFIG_SPECS)


def test_queue_is_report_only_phaseA14_sequence() -> None:
    assert queue.CONTINUE_AFTER_FAILURE is False
    script_names = [run.script_name for run in queue.QUEUE_RUNS]
    assert script_names[0] == "scan_phaseA_v0_14_span_hamming_500_exact_hd_long_ladder_full_v1.py"
    assert "scan_phaseA_v0_14_span_hamming_250_exact_hd_long_ladder_full_v1.py" in script_names
    assert "scan_phaseA_v0_14_span_hamming_750_exact_hd_long_ladder_full_v1.py" in script_names
    assert "scan_phaseA_v0_14_span_hamming_1000_exact_hd_long_ladder_full_v1.py" in script_names
    assert "scan_phaseA_v0_14_span_hamming_500_exact_hd_normal_focus_v1.py" in script_names
    assert "scan_phaseA_v0_14_span_hamming_500_exact_hd_strict_keep_gate_v1.py" in script_names
    assert len(script_names) == len(set(script_names))
    assert all("old" not in name for name in script_names)
    assert all("phaseA_v0_14" in name for name in script_names)
