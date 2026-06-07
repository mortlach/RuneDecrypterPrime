from tools.benchmarks.periodic_sub_trans.no_wli.analysis.common.phaseB_joint_rule_grid_reference_v1 import classify_phrase_confidence, rule_flags


def test_strong_confirm_requires_o3_and_o4():
    row = {'o3_hd0_l10_weight': 35, 'o4_selected_nonoverlap_exact_weight': 8}
    assert classify_phrase_confidence(row) == 'strong_confirm'


def test_o4_only_is_inspect():
    row = {'o3_hd0_l10_weight': 0, 'o4_selected_nonoverlap_exact_weight': 8}
    assert classify_phrase_confidence(row) == 'inspect_o4_only'


def test_rule_flags():
    row = {'o3_hd0_l10_weight': 25, 'o4_exact_hit_count': 1, 'o3_hd0_l12_weight': 12}
    flags = rule_flags(row)
    assert flags['rule_b_o3_l10_ge20_o4_present']
    assert flags['rule_c_o3_l12_ge10_o4_present']
