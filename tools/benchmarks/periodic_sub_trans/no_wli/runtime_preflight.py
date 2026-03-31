from __future__ import annotations

import importlib
from typing import Any


def run_runtime_preflight(
    *,
    scorer_impl: str,
    scorer_stage3_impl_avg_fulltext: str,
    torch_module: Any | None = None,
) -> dict[str, Any]:
    requires_torch = any(
        str(value).strip().lower() == "torch"
        for value in (scorer_impl, scorer_stage3_impl_avg_fulltext)
    )
    payload: dict[str, Any] = {
        "required": bool(requires_torch),
        "scorer_impl": str(scorer_impl),
        "scorer_stage3_impl_avg_fulltext": str(scorer_stage3_impl_avg_fulltext),
    }
    if not requires_torch:
        payload.update(
            status="not_required",
            cuda_available=False,
            cuda_smoke_ok=False,
        )
        return payload

    try:
        torch = torch_module or importlib.import_module("torch")
    except Exception as exc:
        payload.update(
            status="failed",
            cuda_available=False,
            cuda_smoke_ok=False,
            error_type=str(type(exc).__name__),
            error=str(exc),
        )
        return payload

    payload["torch_version"] = str(getattr(torch, "__version__", "unknown"))
    cuda_mod = getattr(torch, "cuda", None)
    if cuda_mod is None or not hasattr(cuda_mod, "is_available"):
        payload.update(
            status="failed",
            cuda_available=False,
            cuda_smoke_ok=False,
            error_type="RuntimeError",
            error="torch.cuda module is unavailable",
        )
        return payload

    cuda_available = bool(cuda_mod.is_available())
    payload["cuda_available"] = bool(cuda_available)
    if not cuda_available:
        payload.update(
            status="warning",
            cuda_smoke_ok=False,
            reason="torch_cuda_unavailable",
        )
        return payload

    try:
        payload["cuda_device_count"] = int(cuda_mod.device_count())
    except Exception:
        payload["cuda_device_count"] = 0

    try:
        payload["cuda_device_name"] = str(cuda_mod.get_device_name(0))
    except Exception:
        payload["cuda_device_name"] = ""

    try:
        lhs = torch.zeros((8, 8), device="cuda")
        rhs = torch.eye(8, device="cuda")
        _ = lhs + rhs
        if hasattr(cuda_mod, "synchronize"):
            cuda_mod.synchronize()
    except Exception as exc:
        payload.update(
            status="failed",
            cuda_smoke_ok=False,
            error_type=str(type(exc).__name__),
            error=str(exc),
        )
        return payload

    payload.update(
        status="ok",
        cuda_smoke_ok=True,
    )
    return payload
