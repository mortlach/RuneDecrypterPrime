from tools.benchmarks.periodic_sub_trans.no_wli.analysis.common.phaseB_joint_feature_contract_v1 import JointFeatureRow, sample_key


def test_joint_class_o3_plus_o4():
    row = JointFeatureRow(sample_key='k', chunk_id='c', source_kind='clean', model_name='none', damage_level='', repeat_index='0', changed_fraction=0, null_class='not_null', o3_hd0_l10_weight=1, o4_selected_nonoverlap_exact_weight=1)
    assert row.joint_class == 'O3_plus_O4'


def test_sample_key():
    assert sample_key({'chunk_id':'c','source_kind':'clean','model_name':'none','damage_level':'','repeat_index':'0'}) == 'c|clean|none||0'
