from tools.benchmarks.periodic_sub_trans.no_wli.analysis.common.phaseB_common_asset_authority_v1 import selected_o4_strict_fwd_files, validate_o4_runtime_manifest


def good_manifest():
    return {
        'asset_id': 'phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_index_v1',
        'runtime_format': 'grouped_npz_by_length_and_word_shape',
        'orders': [4],
        'directions': ['fwd'],
        'cuts': ['strict'],
        'source_compact_validation_status': 'pass',
        'production_scorer_change': False,
        'sample_asset_used': False,
        'old_phrase_index_v1_used': False,
        'full_raw_shards_used_directly_as_runtime': False,
        'files': [{'direction':'fwd','ngram_order':4,'dictionary_cut':'strict','phrase_token_length':12}],
    }


def test_good_o4_manifest():
    assert validate_o4_runtime_manifest(good_manifest()) == []


def test_rejects_o3_orders_for_o4():
    manifest = good_manifest(); manifest['orders'] = [2,3]
    assert validate_o4_runtime_manifest(manifest)


def test_selects_strict_fwd_o4_files():
    rows = selected_o4_strict_fwd_files(good_manifest(), min_phrase_len=10)
    assert len(rows) == 1
