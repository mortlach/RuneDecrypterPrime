# tests/core_types/test_direction_enum.py
from __future__ import annotations
from rune_decrypter_prime.core.types import Direction, Device, PipelineCfg, SolveCfg

def test_direction_enum_values():
    assert Direction.LTR.value == "ltr"
    assert Direction.RTL.value == "rtl"
    # enum identity is stable
    assert Direction("ltr") is Direction.LTR
    assert Direction("rtl") is Direction.RTL

def test_device_enum_values():
    assert Device.CPU.value == "cpu"
    assert Device.CUDA.value == "cuda"

def test_pipeline_cfg_defaults_and_types():
    p = PipelineCfg()
    assert p.text_encoding_direction is Direction.LTR
    assert p.text_permutation is None or isinstance(p.text_permutation, list)

def test_solve_cfg_defaults_and_nested_pipeline():
    cfg = SolveCfg()
    assert cfg.seed == 42
    assert cfg.device is Device.CPU
    assert cfg.telemetry_on is True
    # budgets are present (wired later)
    assert cfg.eval_budget > 0 and cfg.time_budget_s > 0
    assert cfg.pipeline.text_encoding_direction is Direction.LTR
