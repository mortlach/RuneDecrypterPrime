from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    compare_phaseA_v0_14_span_hamming_policy_cuts_v1 as policy_mod,
    scan_phaseA_v0_14_span_hamming_full_ladder_v1 as ladder_mod,
)


def test_policy_cut_dictionary_specs_are_old_vs_new_only() -> None:
    ids = [row["dictionary_id"] for row in policy_mod.DICTIONARY_SPECS]
    assert ids == [
        "old_strict_selected",
        "old_normal_selected",
        "phaseA14_strict_selected",
        "phaseA14_normal_selected",
    ]
    assert len(ids) == len(set(ids))
    assert all("broad" not in dictionary_id for dictionary_id in ids)
    assert all("research" not in dictionary_id for dictionary_id in ids)
    assert all(row["require_selected"] is True for row in policy_mod.DICTIONARY_SPECS)


def test_policy_cut_templates_focus_on_longer_signal_shapes() -> None:
    template_ids = [row["template_id"] for row in policy_mod.SPAN_TEMPLATE_SPECS]
    assert "len3_14_hd2_s1b_shape" in template_ids
    assert "len8_14_hd2_long_signal" in template_ids
    assert "len10_14_hd2_very_long_signal" in template_ids
    assert policy_mod.CANDIDATE_CAPS == (256, 512)
    assert policy_mod.INCLUDE_CAP_2048 is False
    assert policy_mod.PYTHON_PARITY_SPOT_CHECK is True


def test_policy_cut_run_is_report_only_wrapper() -> None:
    assert policy_mod.RUN_LABEL == "phaseA14_span_hamming_policy_cut_comparison_v1"
    assert "phaseA14_span_hamming_policy_cut_comparison_v1" in policy_mod.OUTPUT_DIR_REL
    policy_mod._apply_config()
    assert policy_mod.calibration.RUN_LABEL == policy_mod.RUN_LABEL
    assert policy_mod.calibration.DICTIONARY_SPECS == policy_mod.DICTIONARY_SPECS


def test_full_ladder_matches_v0_3_enabled_hd_ladder() -> None:
    assert ladder_mod.HD_LADDER_BY_LENGTH[1] == (0,)
    assert ladder_mod.HD_LADDER_BY_LENGTH[2] == (0,)
    assert ladder_mod.HD_LADDER_BY_LENGTH[3] == (0, 1)
    assert ladder_mod.HD_LADDER_BY_LENGTH[6] == (0, 1, 2)
    assert ladder_mod.HD_LADDER_BY_LENGTH[8] == (0, 1, 2, 3)
    assert ladder_mod.HD_LADDER_BY_LENGTH[10] == (0, 1, 2, 3, 4)
    assert ladder_mod.HD_LADDER_BY_LENGTH[12] == (0, 1, 2, 3, 4, 5)
    assert ladder_mod.HD_LADDER_BY_LENGTH[14] == (0, 1, 2, 3, 4, 5)


def test_full_ladder_templates_are_single_length_single_hd() -> None:
    assert len(ladder_mod.SPAN_TEMPLATE_SPECS) == sum(
        len(values) for values in ladder_mod.HD_LADDER_BY_LENGTH.values()
    )
    for row in ladder_mod.SPAN_TEMPLATE_SPECS:
        assert row["len_min"] == row["len_max"]
        assert row["template_id"] == f"len{row['len_min']:02d}_hd{row['max_hd']}"


def test_full_ladder_uses_only_phaseA14_dictionaries() -> None:
    ids = [row["dictionary_id"] for row in ladder_mod.DICTIONARY_SPECS]
    assert ids == ["phaseA14_strict_selected", "phaseA14_normal_selected"]
    assert ladder_mod.CANDIDATE_CAPS == (512,)
    assert ladder_mod.INCLUDE_CAP_2048 is False
    assert ladder_mod.PYTHON_PARITY_SPOT_CHECK is True


def test_full_ladder_apply_config_sets_report_label() -> None:
    ladder_mod._apply_config()
    assert ladder_mod.calibration.RUN_LABEL == ladder_mod.RUN_LABEL
    assert ladder_mod.calibration.DICTIONARY_SPECS == ladder_mod.DICTIONARY_SPECS
    assert ladder_mod.calibration.SPAN_TEMPLATE_SPECS == ladder_mod.SPAN_TEMPLATE_SPECS
