from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from tools.benchmarks.periodic_sub_trans.common.core_enums import BenchmarkOrder


_DEFAULT_ORDER = BenchmarkOrder.COL_THEN_SUB.value
_SUPPORTED_ORDERS = (
    BenchmarkOrder.COL_THEN_SUB.value,
    BenchmarkOrder.SUB_THEN_COL.value,
)
_DISPATCH_SCHEMA_VERSION = "no_wli_order_dispatch_v1"


def supported_no_wli_orders() -> tuple[str, ...]:
    return tuple(str(x) for x in _SUPPORTED_ORDERS)


def normalize_no_wli_order(order: str | None) -> str:
    raw = "" if order is None else str(order).strip()
    if not raw:
        return str(_DEFAULT_ORDER)
    if raw in _SUPPORTED_ORDERS:
        return str(raw)
    allowed = ", ".join(sorted(_SUPPORTED_ORDERS))
    raise ValueError(f"Unsupported no_wli order={raw!r}; expected one of: {allowed}")


def normalize_state_order(*, state: MutableMapping[str, Any], key: str = "ORDER") -> str:
    value = normalize_no_wli_order(state.get(key))  # type: ignore[arg-type]
    state[key] = str(value)
    return str(value)


def build_no_wli_order_dispatch_payload(*, order: str | None) -> dict[str, Any]:
    selected = normalize_no_wli_order(order)
    return dict(
        schema_version=str(_DISPATCH_SCHEMA_VERSION),
        selected_order=str(selected),
        supported_orders=[str(x) for x in _SUPPORTED_ORDERS],
        dispatcher="unified_internal",
        flavour="no_wli",
    )

