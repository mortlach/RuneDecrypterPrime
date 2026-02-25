from __future__ import annotations

from types import SimpleNamespace

import pytest

from rune_decrypter_prime.core.engine import builders
from rune_decrypter_prime.core.types import ScorerImpl


pytestmark = pytest.mark.tier_a


class _DummyNumpy:
    def __init__(self, c_cfg, s_cfg):
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg


class _DummyTorch:
    def __init__(self, c_cfg, s_cfg):
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg


class _DummyUnified:
    def __init__(self, c_cfg, s_cfg):
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg


def _patch_scorer_classes(monkeypatch: pytest.MonkeyPatch) -> None:
    import rune_decrypter_prime.scoring.rune_scorer as rs
    import rune_decrypter_prime.scoring.torch_rune_scorer as trs
    import rune_decrypter_prime.scoring.unified_rune_scorer as us

    monkeypatch.setattr(rs, "RuneScorer", _DummyNumpy)
    monkeypatch.setattr(trs, "RuneScorerTorch", _DummyTorch)
    monkeypatch.setattr(us, "UnifiedRuneScorer", _DummyUnified)


def test_build_scorer_reads_impl_from_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scorer_classes(monkeypatch)
    scorer = builders.build_scorer({"device": "cpu"}, {"impl": "torch"})
    assert isinstance(scorer, _DummyTorch)


def test_build_scorer_reads_impl_from_object(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scorer_classes(monkeypatch)
    c_cfg = SimpleNamespace(device="cpu")
    s_cfg = SimpleNamespace(impl=ScorerImpl.UNIFIED)
    scorer = builders.build_scorer(c_cfg, s_cfg)
    assert isinstance(scorer, _DummyUnified)


def test_build_scorer_auto_cpu_defaults_to_numpy(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scorer_classes(monkeypatch)
    scorer = builders.build_scorer({"device": "cpu"}, {"impl": "auto"})
    assert isinstance(scorer, _DummyNumpy)


def test_build_scorer_cuda_unavailable_raises_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builders, "select_backend", lambda _req: ("cpu", object()))
    with pytest.raises(RuntimeError, match="CUDA backend requested but unavailable"):
        builders.build_scorer({"device": "cuda"}, {"impl": "numpy"})
