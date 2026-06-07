from pathlib import Path
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.common.phaseB_common_resume_runner_v1 import config_hash, safe_sample_file_id, validate_resume_config, write_csv


def test_config_hash_stable():
    assert config_hash({'b': 2, 'a': 1}) == config_hash({'a': 1, 'b': 2})


def test_safe_sample_file_id_shortens():
    value = safe_sample_file_id('book|fwd|chunk|' + 'x' * 300)
    assert len(value) < 180
    assert '|' not in value


def test_validate_resume_config_rejects_mismatch(tmp_path: Path):
    summary = tmp_path / 'summary.csv'
    manifest = tmp_path / 'run_manifest.json'
    write_csv(summary, [{'sample_id': 'a', 'config_hash': 'old'}], ['sample_id','config_hash'])
    try:
        validate_resume_config(summary, manifest, 'new')
    except RuntimeError:
        pass
    else:
        raise AssertionError('mismatched config hash should fail')
