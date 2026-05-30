from __future__ import annotations

import json

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    inventory_phaseB_ngram_hamming_asset_provenance_v1 as inv,
)


def test_asset_provenance_inventory_confirms_sample_index_status() -> None:
    payload = inv.build_inventory()
    manifest = payload["manifest"]

    assert manifest["status"] == "pass"
    assert manifest["dataset_status"] == "sample_index_confirmed"
    assert manifest["full_raw_ngram_rebuild_confirmed"] is False
    assert manifest["filtered_index"]["run_mode"] == "sample"
    assert manifest["phrase_index"]["asset_mode"] == "sample"
    assert manifest["phrase_index"]["full_asset_available"] is False


def test_asset_provenance_inventory_covers_expected_cut_order_grid() -> None:
    payload = inv.build_inventory()
    manifest = payload["manifest"]
    asset_rows = payload["asset_inventory_rows"]

    assert manifest["counts"]["asset_file_count"] == 16
    assert manifest["phrase_index"]["normal_fwd_orders_available"] == [2, 3, 4, 5]
    assert manifest["phrase_index"]["strict_fwd_orders_available"] == [2, 3, 4, 5]
    assert all(row["exists"] for row in asset_rows)
    assert all(row["sha256"] for row in asset_rows)


def test_asset_provenance_inventory_records_latest_scan_scope() -> None:
    payload = inv.build_inventory()
    manifest = payload["manifest"]

    assert manifest["latest_scans"]["balanced_readout_scanned_cuts"] == ["normal"]
    assert manifest["latest_scans"]["balanced_readout_scanned_orders"] == [2]
    assert manifest["latest_scans"]["balanced_readout_used_sample_index"] is True


def test_asset_provenance_inventory_outputs_are_serialisable() -> None:
    payload = inv.build_inventory()

    assert payload["asset_inventory_rows"]
    assert payload["run_scope_rows"]
    json.dumps(payload, sort_keys=True)
