from __future__ import annotations
import numpy as np
from rune_decrypter_prime.scoring.language_model import language_model_prime_runtime as lm_rt

class _StubLM:

    def _ensure(self, *_args, **_kwargs):
        return self

    def batch_logp_char(self, pt, _n):
        return np.full((pt.shape[0],), 2.0, dtype=np.float32)

    def batch_zsum_char(self, pt, _n):
        return np.full((pt.shape[0],), 4.0, dtype=np.float32)

    def batch_madsum_char(self, pt, _n):
        return np.full((pt.shape[0],), 6.0, dtype=np.float32)

def test_stat_transform_hook_applied(monkeypatch):
    calls: list[str] = []

    def _transform(stat, values):
        calls.append(getattr(stat, 'value', str(stat)))
        return -np.asarray(values, dtype=np.float32)
    monkeypatch.setattr(lm_rt, 'apply_stat_transform', _transform)
    rt = lm_rt.LmPrimeRuntime.__new__(lm_rt.LmPrimeRuntime)
    rt.lm = _StubLM()
    pt = np.asarray([[1, 2, 3, 4]], dtype=np.uint8)
    logp_a, zsum_a, madsum_a = rt._score_batch_char('ltr', 'nose', 2, pt)
    assert len(calls) == 3
    assert np.all(logp_a < 0)
    assert np.all(zsum_a < 0)
    assert np.all(madsum_a < 0)
