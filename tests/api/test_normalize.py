import rdp.api.logging_utils
import rdp.api.normalize
import numpy as np
import pytest
from rune_decrypter_prime.core.config.logging_config import LoggingConfig
from rdp.core.types import Channel, Device, Direction, ObjectiveFamily, ScorerImpl, SeMode, SolverName, Stat

def test_normalize_objective_spec_from_string():
    spec = rdp.api.normalize.normalize_objective_spec('pct.logp.win10')
    assert spec.family is ObjectiveFamily.PCT
    assert spec.stat is Stat.LOGP
    assert spec.win == 10

def test_normalize_objective_family_and_stat_enum_passthrough():
    assert rdp.api.normalize.normalize_objective_family(ObjectiveFamily.AVG) is ObjectiveFamily.AVG
    assert rdp.api.normalize.normalize_stat(Stat.MADSUM) is Stat.MADSUM

@pytest.mark.parametrize('value, expected', [('ltr', Direction.LTR), ('rtl', Direction.RTL), ('fwd', Direction.LTR), ('rev', Direction.RTL), (Direction.LTR, Direction.LTR)])
def test_normalize_encoding_dir(value, expected):
    assert rdp.api.normalize.normalize_encoding_dir(value) is expected

def test_normalize_se_mode_and_channel():
    assert rdp.api.normalize.normalize_se_mode('nose') is SeMode.NOSE
    assert rdp.api.normalize.normalize_channel('wli') is Channel.WLI
    with pytest.raises(ValueError):
        rdp.api.normalize.normalize_se_mode('diagonal')

def test_normalize_device_accepts_strings_and_enums():
    assert rdp.api.normalize.normalize_device('cpu') is Device.CPU
    assert rdp.api.normalize.normalize_device('gpu') is Device.CUDA
    assert rdp.api.normalize.normalize_device(Device.CUDA) is Device.CUDA
    with pytest.raises(TypeError):
        rdp.api.normalize.normalize_device('arm64')

def test_normalize_scorer_params_handles_none_and_normalises_members():
    assert rdp.api.normalize.normalize_scorer_params(None) == {}
    params = {'se_mode': 'wise', 'encoding_dir': 'fwd', 'objective': 'pct.logp.win10'}
    out = rdp.api.normalize.normalize_scorer_params(dict(params))
    assert out['se_mode'] is SeMode.WISE
    assert out['encoding_dir'] is Direction.LTR
    assert out['objective'].family is ObjectiveFamily.PCT

def test_normalize_scorer_params_rejects_device_and_channel():
    with pytest.raises(ValueError):
        rdp.api.normalize.normalize_scorer_params({'device': 'cuda'})
    with pytest.raises(ValueError):
        rdp.api.normalize.normalize_scorer_params({'channel': 'char'})

def test_to_indices_accepts_tuple_fast_path():
    data = np.array([1, 2, 3], dtype=np.uint8)
    out = rdp.api.normalize.to_indices((data, []))
    assert out.dtype == np.uint8
    assert out.flags.c_contiguous

def test_to_indices_rejects_out_of_range_values():
    with pytest.raises(ValueError):
        rdp.api.normalize.to_indices([0, 29])
    with pytest.raises(ValueError):
        rdp.api.normalize.to_indices([-1, 0])
    with pytest.raises(ValueError):
        rdp.api.normalize.to_indices(np.array([300], dtype=np.int64))

def test_make_single_word_wli_and_wli_from_text():
    wli = rdp.api.normalize.make_single_word_wli(3)
    assert wli == [[0, 3], [1, 3], [2, 3]]
    rune_wli = rdp.api.normalize.wli_from_text('ᛏᛖ')
    assert rune_wli == [[0, 2], [1, 2]]

def test_normalize_ciphertext_infers_wli_from_string():
    ct, wli = rdp.api.normalize.normalize_ciphertext('ᛏᚻᛖ')
    assert len(ct) == len(wli)
    assert all((len(pair) == 2 for pair in wli))

def test_normalize_ciphertext_tuple_roundtrip_and_assert_core_ready():
    arr = np.array([1, 2], dtype=np.uint8)
    wli = [[0, 2], [1, 2]]
    ct, out_wli = rdp.api.normalize.normalize_ciphertext((arr, wli))
    rdp.api.normalize._assert_core_ready(ct, out_wli)
    with pytest.raises(TypeError):
        rdp.api.normalize._assert_core_ready(arr.astype(np.int32), out_wli)

def test_runes_from_indices_round_trip_with_wli():
    ct, wli = rdp.api.normalize.normalize_ciphertext('ᛏᚻ')
    text = rdp.api.normalize.runes_from_indices(ct, wli)
    assert text.replace(' ', '') == 'ᛏᚻ'

def test_normalize_scorer_impl_and_optimizer_name():
    assert rdp.api.normalize.normalize_scorer_impl('torch') is ScorerImpl.TORCH
    assert rdp.api.normalize.normalize_optimizer_name('ga') is SolverName.GA
    with pytest.raises(ValueError):
        rdp.api.normalize.normalize_scorer_impl('unknown')

def test_normalize_text_permutation_and_helpers():
    perm = rdp.api.normalize.normalize_text_permutation([2, 0, 1], 3)
    assert perm == [2, 0, 1]
    with pytest.raises(ValueError):
        rdp.api.normalize.normalize_text_permutation([0, 0, 1], 3)
    data = ['a', 'b', 'c']
    assert rdp.api.normalize.apply_permutation(data, [2, 1, 0]) == ['c', 'b', 'a']
    assert rdp.api.normalize.invert_permutation([2, 0, 1]) == [1, 2, 0]

def test_normalize_optimizer_spec_flattens_params():
    spec = {'name': 'beam', 'params': {'beam_width': 4, 'plateau_rounds': 1}}
    out = rdp.api.normalize.normalize_optimizer_spec(spec)
    assert out['name'] == 'beam'
    assert out['beam_width'] == 4
    assert out['plateau_rounds'] == 1

def test_normalize_logging_cfg_accepts_canonical_serialized_paths(tmp_path):
    cfg = rdp.api.logging_utils.normalize_logging_cfg(
        {"verbose": False, "output_root": str(tmp_path)}
    )
    assert isinstance(cfg, LoggingConfig)
    assert cfg.verbose is False
    assert cfg.output_root == tmp_path

def test_normalize_logging_cfg_accepts_portable_output_and_redact_identity():
    cfg = rdp.api.logging_utils.normalize_logging_cfg({'portable_output': True, 'redact_identity': True})
    assert cfg.portable_output is True
    assert cfg.redact_identity is True

def test_normalize_logging_cfg_does_not_alias_portable_to_portable_output():
    with pytest.raises(ValueError, match="unsupported LoggingConfig"):
        rdp.api.logging_utils.normalize_logging_cfg({"portable": True})
