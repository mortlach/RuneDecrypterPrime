from __future__ import annotations
import pytest

pytestmark = pytest.mark.torch
torch = pytest.importorskip("torch", reason="optional Torch runtime is not installed")


def test_torch_backend_imports_when_optional_runtime_is_available() -> None:
    from rune_decrypter_prime.scoring.torch_rune_scorer import RuneScorerTorch

    assert RuneScorerTorch.__name__ == "RuneScorerTorch"
    assert torch is not None
