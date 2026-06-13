from __future__ import annotations

import numpy as np
import pytest


pytestmark = pytest.mark.tier_a
torch = pytest.importorskip("torch")

from rune_decrypter_prime.scoring.torch_rune_scorer import (  # noqa: E402
    _xxh64_u32words_cpu,
    _xxh64_u32words_device,
)


def test_xxh64_cpu_rejects_non_uint32() -> None:
    bad = np.asarray([[1, 2, 3]], dtype=np.int64)
    with pytest.raises(ValueError, match="uint32"):
        _xxh64_u32words_cpu(bad)


def test_xxh64_cpu_rejects_bad_width() -> None:
    bad = np.asarray([[1, 2, 3, 4, 5]], dtype=np.uint32)
    with pytest.raises(ValueError, match="width"):
        _xxh64_u32words_cpu(bad)


def test_xxh64_device_rejects_non_tensor_input() -> None:
    with pytest.raises(TypeError, match="torch.Tensor"):
        _xxh64_u32words_device(np.asarray([[1, 2, 3]], dtype=np.uint32))  # type: ignore[arg-type]


def test_xxh64_device_rejects_non_uint32() -> None:
    bad = torch.tensor([[1, 2, 3]], dtype=torch.int64)
    with pytest.raises(ValueError, match="torch.uint32"):
        _xxh64_u32words_device(bad)


def test_xxh64_device_rejects_bad_width() -> None:
    bad = torch.tensor([[1, 2, 3, 4, 5]], dtype=torch.uint32)
    with pytest.raises(ValueError, match="width"):
        _xxh64_u32words_device(bad)


def test_xxh64_cpu_device_hashes_match_on_cpu() -> None:
    toks = np.asarray(
        [
            [[1, 2, 3], [3, 4, 5]],
            [[9, 8, 7], [6, 5, 4]],
        ],
        dtype=np.uint32,
    )
    cpu = _xxh64_u32words_cpu(toks)
    dev = _xxh64_u32words_device(torch.from_numpy(toks))
    np.testing.assert_array_equal(cpu.view(np.int64), dev.detach().cpu().numpy())
