from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.order_dispatch import (
    build_no_wli_order_dispatch_payload,
    normalize_no_wli_order,
    supported_no_wli_orders,
)


pytestmark = pytest.mark.tier_a


def test_no_wli_order_dispatch_supports_both_orders() -> None:
    supported = supported_no_wli_orders()
    assert supported == ("col_then_sub", "sub_then_col")
    assert normalize_no_wli_order("col_then_sub") == "col_then_sub"
    assert normalize_no_wli_order("sub_then_col") == "sub_then_col"


def test_no_wli_order_dispatch_rejects_invalid_order() -> None:
    with pytest.raises(ValueError):
        normalize_no_wli_order("not_an_order")


def test_no_wli_order_dispatch_payload_schema() -> None:
    payload = build_no_wli_order_dispatch_payload(order="sub_then_col")
    assert payload["schema_version"] == "no_wli_order_dispatch_v1"
    assert payload["selected_order"] == "sub_then_col"
    assert payload["dispatcher"] == "unified_internal"
    assert payload["supported_orders"] == ["col_then_sub", "sub_then_col"]


def test_no_wli_run_config_builder_includes_order_dispatch_field() -> None:
    txt = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py"
    ).read_text(encoding="utf-8")
    assert "order_dispatch=" in txt
    assert "build_no_wli_order_dispatch_payload_fn(" in txt

