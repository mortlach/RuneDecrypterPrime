from __future__ import annotations

import json

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_reference_smoke_v1 as smoke,
)


def test_reference_smoke_uses_bounded_python_reference_path() -> None:
    manifest = smoke.run_smoke()

    assert manifest["status"] == "pass"
    assert manifest["backend_impl"] == "python_reference"
    assert manifest["broad_python_pilot"] is False
    assert manifest["entry_limit"] == smoke.ENTRY_LIMIT
    assert manifest["loaded_entry_count"] <= smoke.ENTRY_LIMIT
    assert manifest["positive_control"]["phrase_hits"] > 0
    assert manifest["elapsed_seconds"] <= smoke.MAX_WALLCLOCK_SECONDS


def test_reference_smoke_manifest_is_json_serialisable() -> None:
    manifest = smoke.run_smoke()

    json.dumps(manifest, sort_keys=True)
