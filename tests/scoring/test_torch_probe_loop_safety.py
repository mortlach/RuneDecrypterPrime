from __future__ import annotations

import numpy as np
import pytest


pytestmark = pytest.mark.tier_a
torch = pytest.importorskip("torch")

from rune_decrypter_prime.scoring.torch_rune_scorer import _lookup_logp_linear_probe  # noqa: E402


def test_probe_lookup_finds_matches_without_fallback() -> None:
    h = torch.tensor([[5, 7]], dtype=torch.int64)
    keys = torch.zeros((8,), dtype=torch.int64)
    keys[5] = 5
    keys[7] = 7
    logp = torch.arange(8, dtype=torch.float32)

    out, unresolved, exhausted = _lookup_logp_linear_probe(h, keys, logp, mask=7, fallback_logp=-99.0)

    assert unresolved == 0
    assert exhausted is False
    np.testing.assert_allclose(out.detach().cpu().numpy(), np.asarray([[5.0, 7.0]], dtype=np.float32))


def test_probe_lookup_reports_fallback_hits_on_miss() -> None:
    h = torch.tensor([[9, 9, 9]], dtype=torch.int64)
    keys = torch.zeros((8,), dtype=torch.int64)
    logp = torch.arange(8, dtype=torch.float32)

    out, unresolved, exhausted = _lookup_logp_linear_probe(h, keys, logp, mask=7, fallback_logp=-3.25)

    assert unresolved == 3
    assert exhausted is False
    np.testing.assert_allclose(out.detach().cpu().numpy(), np.asarray([[-3.25, -3.25, -3.25]], dtype=np.float32))


def test_probe_lookup_flags_probe_exhaustion_when_table_is_full() -> None:
    h = torch.tensor([[9, 9]], dtype=torch.int64)
    keys = torch.tensor([1, 2, 3, 4], dtype=torch.int64)  # full table: no empty slots
    logp = torch.tensor([0.1, 0.2, 0.3, 0.4], dtype=torch.float32)

    out, unresolved, exhausted = _lookup_logp_linear_probe(
        h, keys, logp, mask=3, fallback_logp=-7.0, max_probes=2
    )

    assert unresolved == 2
    assert exhausted is True
    np.testing.assert_allclose(out.detach().cpu().numpy(), np.asarray([[-7.0, -7.0]], dtype=np.float32))


def test_probe_lookup_validates_arguments() -> None:
    h = torch.tensor([[1]], dtype=torch.int64)
    keys = torch.tensor([1], dtype=torch.int64)
    logp = torch.tensor([0.0], dtype=torch.float32)

    with pytest.raises(ValueError, match="max_probes"):
        _lookup_logp_linear_probe(h, keys, logp, mask=0, fallback_logp=0.0, max_probes=0)

    with pytest.raises(ValueError, match="mask"):
        _lookup_logp_linear_probe(h, keys, logp, mask=-1, fallback_logp=0.0)
