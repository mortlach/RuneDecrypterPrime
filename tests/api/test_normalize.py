import pathlib

import numpy as np
import pytest

from rune_decrypter_prime.api.logging_utils import normalize_logging_cfg
from rune_decrypter_prime.api.normalize import (
    _assert_core_ready,
    apply_permutation,
    invert_permutation,
    make_single_word_wli,
    normalize_channel,
    normalize_ciphertext,
    normalize_device,
    normalize_encoding_dir,
    normalize_objective_family,
    normalize_objective_spec,
    normalize_optimizer_name,
    normalize_optimizer_spec,
    normalize_scorer_impl,
    normalize_scorer_params,
    normalize_se_mode,
    normalize_stat,
    normalize_text_permutation,
    runes_from_indices,
    to_indices,
    wli_from_text,
)
from rune_decrypter_prime.core.config.logging_config import LoggingConfig
from rune_decrypter_prime.core.types import (
    Channel,
    Device,
    Direction,
    ObjectiveFamily,
    ScorerImpl,
    SeMode,
    SolverName,
    Stat,
)


def test_normalize_objective_spec_from_string():
    spec = normalize_objective_spec("pct.logp.win10")
    assert spec.family is ObjectiveFamily.PCT
    assert spec.stat is Stat.LOGP
    assert spec.win == 10


def test_normalize_objective_family_and_stat_enum_passthrough():
    assert normalize_objective_family(ObjectiveFamily.AVG) is ObjectiveFamily.AVG
    assert normalize_stat(Stat.MADSUM) is Stat.MADSUM


@pytest.mark.parametrize(
    "value, expected",
    [
        ("ltr", Direction.LTR),
        ("rtl", Direction.RTL),
        ("fwd", Direction.LTR),
        ("rev", Direction.RTL),
        (Direction.LTR, Direction.LTR),
    ],
)
def test_normalize_encoding_dir(value, expected):
    assert normalize_encoding_dir(value) is expected


def test_normalize_se_mode_and_channel():
    assert normalize_se_mode("nose") is SeMode.NOSE
    assert normalize_channel("wli") is Channel.WLI
    with pytest.raises(ValueError):
        normalize_se_mode("diagonal")


def test_normalize_device_accepts_strings_and_enums():
    assert normalize_device("cpu") is Device.CPU
    assert normalize_device("gpu") is Device.CUDA
    assert normalize_device(Device.CUDA) is Device.CUDA
    with pytest.raises(TypeError):
        normalize_device("arm64")


def test_normalize_scorer_params_handles_none_and_normalises_members():
    assert normalize_scorer_params(None) == {}
    params = {
        "channel": "char",
        "device": "cuda",
        "se_mode": "wise",
        "encoding_dir": "fwd",
        "objective": "pct.logp.win10",
    }
    out = normalize_scorer_params(dict(params))
    assert out["channel"] is Channel.CHAR
    assert out["device"] is Device.CUDA
    assert out["se_mode"] is SeMode.WISE
    assert out["encoding_dir"] is Direction.LTR
    assert out["objective"].family is ObjectiveFamily.PCT


def test_to_indices_accepts_tuple_fast_path():
    data = np.array([1, 2, 3], dtype=np.uint8)
    out = to_indices((data, []))
    assert out.dtype == np.uint8
    assert out.flags.c_contiguous


def test_make_single_word_wli_and_wli_from_text():
    wli = make_single_word_wli(3)
    assert wli == [[0, 3], [1, 3], [2, 3]]
    rune_wli = wli_from_text("ᛏᛖ")
    assert rune_wli == [[0, 2], [0, 2]]


def test_normalize_ciphertext_infers_wli_from_string():
    ct, wli = normalize_ciphertext("ᛏᚻᛖ")
    assert len(ct) == len(wli)
    assert all(len(pair) == 2 for pair in wli)


def test_normalize_ciphertext_tuple_roundtrip_and_assert_core_ready():
    arr = np.array([1, 2], dtype=np.uint8)
    wli = [[0, 2], [0, 2]]
    ct, out_wli = normalize_ciphertext((arr, wli))
    _assert_core_ready(ct, out_wli)
    with pytest.raises(TypeError):
        _assert_core_ready(arr.astype(np.int32), out_wli)


def test_runes_from_indices_round_trip_with_wli():
    ct, wli = normalize_ciphertext("ᛏᚻ")
    text = runes_from_indices(ct, wli)
    assert text.replace(" ", "") == "ᛏᚻ"


def test_normalize_scorer_impl_and_optimizer_name():
    assert normalize_scorer_impl("torch") is ScorerImpl.TORCH
    assert normalize_optimizer_name("ga") is SolverName.GA
    with pytest.raises(ValueError):
        normalize_scorer_impl("unknown")


def test_normalize_text_permutation_and_helpers():
    perm = normalize_text_permutation([2, 0, 1], 3)
    assert perm == [2, 0, 1]
    with pytest.raises(ValueError):
        normalize_text_permutation([0, 0, 1], 3)
    data = ["a", "b", "c"]
    assert apply_permutation(data, [2, 1, 0]) == ["c", "b", "a"]
    assert invert_permutation([2, 0, 1]) == [1, 2, 0]


def test_normalize_optimizer_spec_flattens_params():
    spec = {"name": "beam", "params": {"beam_width": 4, "patience_rounds": 1}}
    out = normalize_optimizer_spec(spec)
    assert out["name"] == "beam"
    assert out["beam_width"] == 4
    assert out["patience_rounds"] == 1


def test_normalize_logging_cfg_filters_and_normalizes_paths(tmp_path):
    cfg = normalize_logging_cfg(
        {
            "verbose": False,
            "out_root": tmp_path,
            "extra": "ignored",
        }
    )
    assert isinstance(cfg, LoggingConfig)
    assert cfg.verbose is False
    assert cfg.out_root == str(tmp_path)
