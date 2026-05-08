from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    scan_phaseA_v0_14_span_hamming_uncapped_strict_ladder_v1 as strict_mod,
    scan_phaseA_v0_14_span_hamming_uncapped_strict_normal_ladder_v1 as strict_normal_mod,
)


EXPECTED_HD_LADDER_BY_LENGTH = {
    1: (0,),
    2: (0,),
    3: (0, 1),
    4: (0, 1),
    5: (0, 1),
    6: (0, 1, 2),
    7: (0, 1, 2),
    8: (0, 1, 2, 3),
    9: (0, 1, 2, 3),
    10: (0, 1, 2, 3, 4),
    11: (0, 1, 2, 3, 4),
    12: (0, 1, 2, 3, 4, 5),
    13: (0, 1, 2, 3, 4, 5),
    14: (0, 1, 2, 3, 4, 5),
}


def _assert_exact_ladder(module: object) -> None:
    assert module.HD_LADDER_BY_LENGTH == EXPECTED_HD_LADDER_BY_LENGTH
    assert len(module.SPAN_TEMPLATE_SPECS) == sum(len(v) for v in EXPECTED_HD_LADDER_BY_LENGTH.values())
    for row in module.SPAN_TEMPLATE_SPECS:
        assert row["len_min"] == row["len_max"]
        assert row["template_id"] == f"len{row['len_min']:02d}_hd{row['max_hd']}"


def test_uncapped_strict_ladder_uses_phaseA14_strict_only() -> None:
    ids = [row["dictionary_id"] for row in strict_mod.DICTIONARY_SPECS]
    assert ids == ["phaseA14_strict_selected"]
    assert strict_mod.CANDIDATE_CAPS == (100_000,)
    assert strict_mod.INCLUDE_CAP_2048 is False
    assert strict_mod.EFFECTIVELY_UNCAPPED_CANDIDATE_CAP == 100_000
    assert all(row["require_selected"] is True for row in strict_mod.DICTIONARY_SPECS)
    assert all("old_" not in row["dictionary_id"] for row in strict_mod.DICTIONARY_SPECS)
    assert all("broad" not in row["dictionary_id"] for row in strict_mod.DICTIONARY_SPECS)
    assert all("research" not in row["dictionary_id"] for row in strict_mod.DICTIONARY_SPECS)


def test_uncapped_strict_ladder_matches_v0_3_ladder() -> None:
    _assert_exact_ladder(strict_mod)


def test_uncapped_strict_ladder_apply_config_sets_report_only_run() -> None:
    strict_mod._apply_config()
    assert strict_mod.calibration.RUN_LABEL == strict_mod.RUN_LABEL
    assert strict_mod.calibration.OUTPUT_DIR_REL == strict_mod.OUTPUT_DIR_REL
    assert strict_mod.calibration.DICTIONARY_SPECS == strict_mod.DICTIONARY_SPECS
    assert strict_mod.calibration.SPAN_TEMPLATE_SPECS == strict_mod.SPAN_TEMPLATE_SPECS
    assert strict_mod.calibration.CANDIDATE_CAPS == (100_000,)
    assert strict_mod.PYTHON_PARITY_SPOT_CHECK is True


def test_uncapped_strict_normal_ladder_uses_phaseA14_only() -> None:
    ids = [row["dictionary_id"] for row in strict_normal_mod.DICTIONARY_SPECS]
    assert ids == ["phaseA14_strict_selected", "phaseA14_normal_selected"]
    assert strict_normal_mod.CANDIDATE_CAPS == (100_000,)
    assert strict_normal_mod.INCLUDE_CAP_2048 is False
    assert strict_normal_mod.EFFECTIVELY_UNCAPPED_CANDIDATE_CAP == 100_000
    assert all(row["require_selected"] is True for row in strict_normal_mod.DICTIONARY_SPECS)
    assert all("old_" not in row["dictionary_id"] for row in strict_normal_mod.DICTIONARY_SPECS)
    assert all("broad" not in row["dictionary_id"] for row in strict_normal_mod.DICTIONARY_SPECS)
    assert all("research" not in row["dictionary_id"] for row in strict_normal_mod.DICTIONARY_SPECS)


def test_uncapped_strict_normal_ladder_matches_v0_3_ladder() -> None:
    _assert_exact_ladder(strict_normal_mod)


def test_uncapped_strict_normal_ladder_apply_config_sets_report_only_run() -> None:
    strict_normal_mod._apply_config()
    assert strict_normal_mod.calibration.RUN_LABEL == strict_normal_mod.RUN_LABEL
    assert strict_normal_mod.calibration.OUTPUT_DIR_REL == strict_normal_mod.OUTPUT_DIR_REL
    assert strict_normal_mod.calibration.DICTIONARY_SPECS == strict_normal_mod.DICTIONARY_SPECS
    assert strict_normal_mod.calibration.SPAN_TEMPLATE_SPECS == strict_normal_mod.SPAN_TEMPLATE_SPECS
    assert strict_normal_mod.calibration.CANDIDATE_CAPS == (100_000,)
    assert strict_normal_mod.PYTHON_PARITY_SPOT_CHECK is True
