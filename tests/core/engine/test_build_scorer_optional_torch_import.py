from __future__ import annotations

import sys
import types

from rune_decrypter_prime.core.engine.builders import build_scorer


class _FakeRuneScorer:
    def __init__(self, c_cfg, s_cfg):
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg


def test_numpy_scorer_does_not_import_torch(monkeypatch):
    fake_numpy_module = types.ModuleType("rune_decrypter_prime.scoring.rune_scorer")
    fake_numpy_module.RuneScorer = _FakeRuneScorer
    monkeypatch.setitem(sys.modules, "rune_decrypter_prime.scoring.rune_scorer", fake_numpy_module)
    monkeypatch.delitem(sys.modules, "torch", raising=False)

    scorer = build_scorer({"device": "cpu"}, {"impl": "numpy"})

    assert isinstance(scorer, _FakeRuneScorer)
    assert "torch" not in sys.modules
