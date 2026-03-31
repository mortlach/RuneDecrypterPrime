from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.runtime_preflight import (
    run_runtime_preflight,
)


pytestmark = pytest.mark.tier_a


def test_runtime_preflight_not_required_for_non_torch() -> None:
    payload = run_runtime_preflight(
        scorer_impl="numpy",
        scorer_stage3_impl_avg_fulltext="numpy",
    )
    assert bool(payload["required"]) is False
    assert str(payload["status"]) == "not_required"
    assert bool(payload["cuda_available"]) is False
    assert bool(payload["cuda_smoke_ok"]) is False


def test_runtime_preflight_warns_when_cuda_unavailable() -> None:
    fake_torch = SimpleNamespace(
        __version__="fake",
        cuda=SimpleNamespace(
            is_available=lambda: False,
        ),
    )
    payload = run_runtime_preflight(
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        torch_module=fake_torch,
    )
    assert bool(payload["required"]) is True
    assert str(payload["status"]) == "warning"
    assert str(payload["reason"]) == "torch_cuda_unavailable"
    assert bool(payload["cuda_smoke_ok"]) is False


def test_runtime_preflight_fails_on_cuda_smoke_error() -> None:
    class _CudaModule:
        @staticmethod
        def is_available() -> bool:
            return True

        @staticmethod
        def device_count() -> int:
            return 1

        @staticmethod
        def get_device_name(_index: int) -> str:
            return "Fake GPU"

        @staticmethod
        def synchronize() -> None:
            return None

    class _FakeTorch:
        __version__ = "fake"
        cuda = _CudaModule()

        @staticmethod
        def zeros(*_args, **_kwargs):
            raise RuntimeError("boom")

        @staticmethod
        def eye(*_args, **_kwargs):
            raise AssertionError("should not be reached")

    payload = run_runtime_preflight(
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        torch_module=_FakeTorch(),
    )
    assert str(payload["status"]) == "failed"
    assert str(payload["error_type"]) == "RuntimeError"
    assert "boom" in str(payload["error"])


def test_runtime_preflight_passes_on_cuda_smoke_success() -> None:
    class _CudaModule:
        @staticmethod
        def is_available() -> bool:
            return True

        @staticmethod
        def device_count() -> int:
            return 1

        @staticmethod
        def get_device_name(_index: int) -> str:
            return "Fake GPU"

        @staticmethod
        def synchronize() -> None:
            return None

    class _FakeTensor:
        def __add__(self, _other):
            return self

    class _FakeTorch:
        __version__ = "fake"
        cuda = _CudaModule()

        @staticmethod
        def zeros(*_args, **_kwargs):
            return _FakeTensor()

        @staticmethod
        def eye(*_args, **_kwargs):
            return _FakeTensor()

    payload = run_runtime_preflight(
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        torch_module=_FakeTorch(),
    )
    assert str(payload["status"]) == "ok"
    assert bool(payload["cuda_available"]) is True
    assert bool(payload["cuda_smoke_ok"]) is True
