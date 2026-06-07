from tools.benchmarks.periodic_sub_trans.no_wli.analysis.common.phaseB_damage_levels_contract_v1 import DAMAGE_LEVELS, changed_fraction_bin, damage_level_text, null_class, validate_actual_damage


def test_damage_levels_are_target_range_only():
    assert DAMAGE_LEVELS == (0.10, 0.20, 0.30, 0.40, 0.50)


def test_damage_level_text_rejects_70_percent():
    try:
        damage_level_text(0.70)
    except ValueError:
        pass
    else:
        raise AssertionError("0.70 should not be in the first benchmark ladder")


def test_null_class_separates_block_controls():
    assert null_class("uniform_random") == "ordinary_null"
    assert null_class("block_shuffle_50") == "hard_local_order_control"


def test_damage_tolerance():
    validate_actual_damage(0.30, 0.305)
    try:
        validate_actual_damage(0.50, 0.24)
    except AssertionError:
        pass
    else:
        raise AssertionError("large damage miss should fail")


def test_changed_fraction_bin():
    assert changed_fraction_bin(0.23) == "0.20-0.30"
